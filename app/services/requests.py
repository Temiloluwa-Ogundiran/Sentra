from pathlib import Path

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
    path, size = await persist_upload(upload_file, prefix="dev_")
    request = VerificationRequest(
        user_id=user.id,
        status="received",
        caption=caption,
        expected_amount=float(expected_amount) if expected_amount else None,
    )
    db.add(request)
    db.commit()
    db.refresh(request)
    artifact = Artifact(
        request_id=request.id,
        source_path=str(path),
        mime_type=upload_file.content_type or "application/octet-stream",
        original_filename=upload_file.filename or path.name,
        file_size=size,
    )
    db.add(artifact)
    db.commit()
    return request.id


async def create_request_from_gowa_event(db: Session, payload: dict) -> int | None:
    if payload.get("type") != "media":
        return None
    whatsapp_id = payload["from"]
    media_url = payload["media_url"]
    mime_type = payload.get("mime_type", "application/octet-stream")
    filename = payload.get("file_name", "artifact.bin")
    client = GowaClient()
    content = await client.fetch_media_bytes(media_url)
    path, size = persist_bytes(content, filename)
    user = get_or_create_user(db, whatsapp_id)
    request = VerificationRequest(user_id=user.id, status="received", caption=payload.get("caption"))
    db.add(request)
    db.commit()
    db.refresh(request)
    artifact = Artifact(
        request_id=request.id,
        source_path=str(path),
        mime_type=mime_type,
        original_filename=filename,
        file_size=size,
    )
    db.add(artifact)
    db.commit()
    return request.id


def save_pipeline_result(db: Session, request_id: int, result: CanonicalResult, debug: dict) -> None:
    request = db.query(VerificationRequest).get(request_id)
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
    request = db.query(VerificationRequest).get(request_id)
    request.status = "failed"
    request.failure_reason = reason
    db.commit()


def fetch_result_payload(db: Session, request_id: int) -> dict:
    request = db.query(VerificationRequest).get(request_id)
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
