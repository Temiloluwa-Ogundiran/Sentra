from pathlib import Path

import pytest

from app.schemas.common import CanonicalResult, ExtractedFields
from app.services.messaging import send_result


@pytest.mark.asyncio
async def test_send_result_sends_text_and_optional_file(monkeypatch, tmp_path):
    annotated = tmp_path / "annotated.png"
    annotated.write_bytes(b"fake-image")

    sent_calls: list[tuple[str, str, str | None]] = []

    async def fake_send_text(self, to: str, text: str) -> None:
        sent_calls.append(("text", to, text))

    async def fake_send_file(self, to: str, file_path: Path, caption: str | None = None) -> None:
        sent_calls.append(("file", to, caption))
        assert file_path == annotated

    monkeypatch.setattr("app.services.messaging.GowaClient.send_text", fake_send_text)
    monkeypatch.setattr("app.services.messaging.GowaClient.send_file", fake_send_file)

    result = CanonicalResult(
        request_id=1,
        artifact_type="bank_alert_screenshot",
        verdict="Review",
        recommended_action="Ask for a clearer screenshot or original receipt document.",
        extracted_fields=ExtractedFields(amount="25000", currency="NGN"),
        reasons=["Low confidence in amount region."],
        quality_flags=["low_resolution"],
        annotated_artifact_path=str(annotated),
        processing_time_ms=120,
    )

    await send_result("2348012345678", result)

    assert sent_calls[0][0] == "text"
    assert sent_calls[0][1] == "2348012345678"
    assert sent_calls[1] == ("file", "2348012345678", "Sentra analysis preview")
