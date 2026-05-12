from pathlib import Path
from tempfile import TemporaryDirectory

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.artifact import Artifact
from app.models.credit_wallet import CreditWallet
from app.models.user import User
from app.models.verification_request import VerificationRequest
from app.schemas.common import CanonicalResult, ExtractedFields
from app.workers.queue import WorkerQueue


def _make_session():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def test_process_request_sends_stage_updates(monkeypatch):
    session_local = _make_session()
    sent_updates: list[tuple[str, str]] = []
    sent_typing: list[str] = []
    sent_results: list[str] = []

    with TemporaryDirectory() as temp_dir:
        proof_path = Path(temp_dir) / "proof.png"
        proof_path.write_bytes(b"fake-proof")
        annotated_path = Path(temp_dir) / "annotated.png"
        annotated_path.write_bytes(b"fake-annotated")

        with session_local() as db:
            user = User(whatsapp_id="2349025283155@s.whatsapp.net")
            db.add(user)
            db.commit()
            db.refresh(user)
            db.add(CreditWallet(user_id=user.id, balance=2))
            request = VerificationRequest(user_id=user.id, status="received", caption="proof")
            db.add(request)
            db.commit()
            db.refresh(request)
            db.add(
                Artifact(
                    request_id=request.id,
                    source_path=str(proof_path),
                    mime_type="image/png",
                    original_filename="proof.png",
                    file_size=proof_path.stat().st_size,
                )
            )
            db.commit()
            request_id = request.id

        def fake_run_pipeline(request_id, file_path, mime_type, expected_amount=None, stage_callback=None):
            assert stage_callback is not None
            for stage in ("preparing", "reading_proof", "checking_details", "reviewing_changes", "finalizing"):
                stage_callback(stage)
            return (
                CanonicalResult(
                    request_id=request_id,
                    artifact_type="bank_alert_screenshot",
                    verdict="Review",
                    recommended_action="Ask for confirmation.",
                    extracted_fields=ExtractedFields(amount="25000", currency="NGN"),
                    reasons=["Low confidence in amount region."],
                    quality_flags=[],
                    annotated_artifact_path=str(annotated_path),
                    processing_time_ms=120,
                ),
                {"raw_text": "proof", "rule_hits": [], "model_scores": {}},
            )

        async def fake_send_processing_update(whatsapp_id: str, stage: str) -> None:
            sent_updates.append((whatsapp_id, stage))

        async def fake_send_typing_indicator(whatsapp_id: str) -> None:
            sent_typing.append(whatsapp_id)

        async def fake_send_result(whatsapp_id: str, result) -> None:
            sent_results.append(whatsapp_id)

        monkeypatch.setattr("app.workers.queue.SessionLocal", session_local)
        monkeypatch.setattr("app.workers.queue.run_pipeline", fake_run_pipeline)
        monkeypatch.setattr("app.workers.queue.send_processing_update", fake_send_processing_update)
        monkeypatch.setattr("app.workers.queue.send_typing_indicator", fake_send_typing_indicator)
        monkeypatch.setattr("app.workers.queue.send_result", fake_send_result)

        queue = WorkerQueue()
        queue.process_request(request_id)

    assert sent_typing[0] == "2349025283155@s.whatsapp.net"
    assert sent_updates == [
        ("2349025283155@s.whatsapp.net", "preparing"),
        ("2349025283155@s.whatsapp.net", "reading_proof"),
        ("2349025283155@s.whatsapp.net", "checking_details"),
        ("2349025283155@s.whatsapp.net", "reviewing_changes"),
        ("2349025283155@s.whatsapp.net", "finalizing"),
    ]
    assert sent_results == ["2349025283155@s.whatsapp.net"]
