from io import BytesIO
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.artifact import Artifact
from app.models.analysis_result import AnalysisResult
from app.models.extraction import Extraction
from app.models.user import User
from app.models.verification_request import VerificationRequest
from app.schemas.common import CanonicalResult, ExtractedFields
from app.services.requests import create_request_from_upload
from app.workers.queue import WorkerQueue


def _make_session():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


async def test_create_request_from_upload_sets_received_status(monkeypatch, tmp_path):
    session_local = _make_session()
    upload = UploadFile(filename="proof.png", file=BytesIO(b"fake-image-bytes"))
    upload.headers = {}
    upload.size = len(b"fake-image-bytes")

    monkeypatch.setattr("app.services.storage.settings.storage_root", tmp_path)
    monkeypatch.setattr(
        "app.services.requests.consume_verification_credit",
        lambda db, wallet, cost=1, auto_seed_dev=False: wallet,
    )

    with session_local() as db:
        request_id = await create_request_from_upload(
            db=db,
            whatsapp_id="2348012345678",
            upload_file=upload,
            expected_amount="25000",
            caption="check this proof",
        )
        request = db.get(VerificationRequest, request_id)
        artifact = db.query(Artifact).filter(Artifact.request_id == request_id).one()

    assert request is not None
    assert request.status == "received"
    assert artifact.original_filename == "proof.png"
    assert Path(artifact.source_path).exists()


def test_worker_process_request_completes_lifecycle(monkeypatch, tmp_path):
    session_local = _make_session()
    monkeypatch.setattr("app.services.storage.settings.storage_root", tmp_path)
    monkeypatch.setattr("app.workers.queue.SessionLocal", session_local)

    with session_local() as db:
        user = User(whatsapp_id="2348012345678")
        db.add(user)
        db.commit()
        db.refresh(user)

        request = VerificationRequest(user_id=user.id, status="received", caption="proof")
        db.add(request)
        db.commit()
        db.refresh(request)

        artifact = Artifact(
            request_id=request.id,
            source_path=str(tmp_path / "uploads" / "proof.png"),
            mime_type="image/png",
            original_filename="proof.png",
            file_size=16,
        )
        Path(artifact.source_path).parent.mkdir(parents=True, exist_ok=True)
        Path(artifact.source_path).write_bytes(b"fake-image-bytes")
        db.add(artifact)
        db.commit()

    result = CanonicalResult(
        request_id=1,
        artifact_type="bank_alert_screenshot",
        verdict="Review",
        recommended_action="Ask for a clearer screenshot or original receipt document.",
        extracted_fields=ExtractedFields(amount="25000", currency="NGN"),
        reasons=["Low confidence in amount region."],
        quality_flags=["low_resolution"],
        annotated_artifact_path=None,
        processing_time_ms=120,
    )

    async def fake_send_result(whatsapp_id: str, payload: CanonicalResult) -> None:
        assert whatsapp_id == "2348012345678"
        assert payload.request_id == 1

    monkeypatch.setattr(
        "app.workers.queue.run_pipeline",
        lambda **kwargs: (
            result,
            {
                "raw_text": "NGN 25000",
                "rule_hits": ["missing_reference"],
                "model_scores": {"artifact_reasoner": {"summary": "Low confidence in amount region."}},
            },
        ),
    )
    monkeypatch.setattr("app.workers.queue.send_result", fake_send_result)

    queue = WorkerQueue()
    queue.process_request(1)

    with session_local() as db:
        stored_request = db.get(VerificationRequest, 1)
        extraction = db.query(Extraction).filter(Extraction.request_id == 1).one()
        analysis = db.query(AnalysisResult).filter(AnalysisResult.request_id == 1).one()

    assert stored_request.status == "completed"
    assert extraction.normalized_fields["amount"] == "25000"
    assert analysis.verdict == "Review"
