from pathlib import Path
from mimetypes import guess_type

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.integrations.gowa import GowaClient
from app.models.analysis_result import AnalysisResult
from app.models.artifact import Artifact
from app.models.extraction import Extraction
from app.models.user import User
from app.models.verification_request import VerificationRequest
from app.schemas.common import CanonicalResult
from app.services.storage import persist_bytes, persist_upload
from app.services.wallets import consume_verification_credit, get_or_create_wallet

SUPPORTED_MIME_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "application/pdf",
}


def _create_request_record(
    db: Session,
    whatsapp_id: str,
    caption: str | None,
    expected_amount: str | None = None,
) -> VerificationRequest:
    user = get_or_create_user(db, whatsapp_id)
    request = VerificationRequest(
        user_id=user.id,
        status="received",
        caption=caption,
        expected_amount=float(expected_amount) if expected_amount else None,
    )
    db.add(request)
    db.commit()
    db.refresh(request)
    return request


def _create_artifact_record(
    db: Session,
    request_id: int,
    source_path: Path,
    mime_type: str,
    original_filename: str,
    file_size: int,
) -> Artifact:
    artifact = Artifact(
        request_id=request_id,
        source_path=str(source_path),
        mime_type=mime_type,
        original_filename=original_filename,
        file_size=file_size,
    )
    db.add(artifact)
    db.commit()
    db.refresh(artifact)
    return artifact


def _guess_mime_type(filename: str, fallback: str | None = None) -> str:
    guessed, _ = guess_type(filename)
    return (fallback or guessed or "application/octet-stream").lower()


def _extract_media_candidate(payload: dict) -> tuple[str, str, str, str | None] | None:
    body = payload.get("body")
    media_fields = ("image", "document")

    for field in media_fields:
        media_value = payload.get(field)
        if not media_value:
            continue

        if isinstance(media_value, str):
            filename = Path(media_value).name or f"{field}.bin"
            mime_type = _guess_mime_type(filename)
            if mime_type not in SUPPORTED_MIME_TYPES:
                continue
            return media_value, mime_type, filename, body

        if isinstance(media_value, dict):
            media_url = media_value.get("url") or media_value.get("path")
            if not media_url:
                continue
            filename = media_value.get("filename") or Path(media_url).name or f"{field}.bin"
            mime_type = _guess_mime_type(filename, media_value.get("mime_type"))
            if mime_type not in SUPPORTED_MIME_TYPES:
                continue
            caption = media_value.get("caption") or body
            return media_url, mime_type, filename, caption

    return None


def get_or_create_user(db: Session, whatsapp_id: str) -> User:
    user = db.query(User).filter(User.whatsapp_id == whatsapp_id).one_or_none()
    if user:
        return user
    user = User(whatsapp_id=whatsapp_id)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


async def create_request_from_upload(
    db: Session,
    whatsapp_id: str,
    upload_file: UploadFile,
    expected_amount: str | None,
    caption: str | None,
) -> int:
    user = get_or_create_user(db, whatsapp_id)
    wallet = get_or_create_wallet(db, user.id)
    consume_verification_credit(db, wallet, cost=1, auto_seed_dev=whatsapp_id == "dev-user")
    path, size = await persist_upload(upload_file, prefix="dev_")
    request = _create_request_record(
        db=db,
        whatsapp_id=whatsapp_id,
        caption=caption,
        expected_amount=expected_amount,
    )
    _create_artifact_record(
        db=db,
        request_id=request.id,
        source_path=path,
        mime_type=upload_file.content_type or "application/octet-stream",
        original_filename=upload_file.filename or path.name,
        file_size=size,
    )
    return request.id


async def create_request_from_gowa_event(db: Session, payload: dict) -> int | None:
    if payload.get("event") != "message":
        return None
    message_payload = payload.get("payload", {})
    media_candidate = _extract_media_candidate(message_payload)
    if media_candidate is None:
        return None

    whatsapp_id = message_payload["from"]
    media_url, mime_type, filename, caption = media_candidate
    user = get_or_create_user(db, whatsapp_id)
    wallet = get_or_create_wallet(db, user.id)
    consume_verification_credit(db, wallet, cost=1)
    client = GowaClient()
    content = await client.fetch_media_bytes(media_url)
    path, size = persist_bytes(content, filename)
    request = _create_request_record(
        db=db,
        whatsapp_id=whatsapp_id,
        caption=caption,
    )
    _create_artifact_record(
        db=db,
        request_id=request.id,
        source_path=path,
        mime_type=mime_type,
        original_filename=filename,
        file_size=size,
    )
    return request.id


def save_pipeline_result(db: Session, request_id: int, result: CanonicalResult, debug: dict) -> None:
    request = db.get(VerificationRequest, request_id)
    artifact = db.query(Artifact).filter(Artifact.request_id == request_id).one()
    artifact.detected_artifact_type = result.artifact_type
    artifact.annotated_path = result.annotated_artifact_path
    extraction = Extraction(
        request_id=request_id,
        raw_text=debug["raw_text"],
        normalized_fields=result.extracted_fields.model_dump(),
    )
    analysis = AnalysisResult(
        request_id=request_id,
        verdict=result.verdict,
        recommended_action=result.recommended_action,
        reasons=result.reasons,
        quality_flags=result.quality_flags,
        internal_rule_hits=debug["rule_hits"],
        internal_model_scores=debug["model_scores"],
    )
    request.status = "completed"
    request.processing_time_ms = result.processing_time_ms
    db.add(extraction)
    db.add(analysis)
    db.commit()


def mark_failed(db: Session, request_id: int, reason: str) -> None:
    request = db.get(VerificationRequest, request_id)
    request.status = "failed"
    request.failure_reason = reason
    db.commit()


def fetch_result_payload(db: Session, request_id: int) -> dict:
    request = db.get(VerificationRequest, request_id)
    artifact = db.query(Artifact).filter(Artifact.request_id == request_id).one_or_none()
    extraction = db.query(Extraction).filter(Extraction.request_id == request_id).one_or_none()
    analysis = db.query(AnalysisResult).filter(AnalysisResult.request_id == request_id).one_or_none()
    return {
        "request_id": request_id,
        "status": request.status,
        "failure_reason": request.failure_reason,
        "artifact": {
            "type": artifact.detected_artifact_type if artifact else None,
            "source_path": artifact.source_path if artifact else None,
            "annotated_path": artifact.annotated_path if artifact else None,
        },
        "extraction": extraction.normalized_fields if extraction else None,
        "analysis": {
            "verdict": analysis.verdict,
            "recommended_action": analysis.recommended_action,
            "reasons": analysis.reasons,
            "quality_flags": analysis.quality_flags,
        }
        if analysis
        else None,
    }
