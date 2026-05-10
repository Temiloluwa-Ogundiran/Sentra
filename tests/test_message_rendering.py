from app.schemas.common import CanonicalResult, ExtractedFields
from app.services.messaging import render_whatsapp_message


def test_message_contains_verdict():
    result = CanonicalResult(
        request_id=1,
        artifact_type="bank_alert_screenshot",
        verdict="Suspicious",
        recommended_action="Do not release goods yet.",
        extracted_fields=ExtractedFields(amount="₦25,000"),
        reasons=["Edited amount region detected."],
        quality_flags=[],
        annotated_artifact_path=None,
        processing_time_ms=300,
        expected_amount=None,
    )
    message = render_whatsapp_message(result)
    assert "Verdict: Suspicious" in message
    assert "Amount: ₦25,000" in message
