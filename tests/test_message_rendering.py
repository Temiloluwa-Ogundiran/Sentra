from app.schemas.common import CanonicalResult, ExtractedFields
from app.services.messaging import render_whatsapp_message


def test_message_contains_polished_labels():
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
    assert "Payment document type: Bank alert screenshot" in message
    assert "Advise: Do not release goods yet." in message


def test_message_simplifies_ai_generated_reason():
    result = CanonicalResult(
        request_id=2,
        artifact_type="bank_alert_screenshot",
        verdict="Suspicious",
        recommended_action="Do not release goods yet.",
        extracted_fields=ExtractedFields(),
        reasons=["This payment document has unusually smooth rendered text and surfaces, which can indicate AI generation."],
        quality_flags=["synthetic_render_signal"],
        annotated_artifact_path=None,
        processing_time_ms=300,
        expected_amount=None,
    )

    message = render_whatsapp_message(result)

    assert "Image appears to be AI generated." in message
    assert "smooth rendered text and surfaces" not in message


def test_message_hides_internal_fallback_wording():
    result = CanonicalResult(
        request_id=3,
        artifact_type="bank_alert_screenshot",
        verdict="Review",
        recommended_action="Ask for another payment document.",
        extracted_fields=ExtractedFields(),
        reasons=[
            "Artifact reasoning is temporarily unavailable, so this result uses fallback checks.",
            "One image-integrity check raised a caution flag on this payment document.",
        ],
        quality_flags=["tamper_signal"],
        annotated_artifact_path=None,
        processing_time_ms=300,
        expected_amount=None,
    )

    message = render_whatsapp_message(result)

    assert "temporarily unavailable" not in message
    assert "fallback checks" not in message
    assert "This payment document may have been edited." in message
