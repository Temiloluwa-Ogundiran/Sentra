from app.inference.fusion import fuse_result
from app.schemas.common import ExtractedFields


def test_single_tamper_signal_only_reviews_not_suspicious():
    result = fuse_result(
        request_id=1,
        artifact_type="bank_alert_screenshot",
        extracted_fields=ExtractedFields(amount="4000.00", currency="NGN", reference="TRF123456"),
        reasons=["One image-integrity check raised a caution flag on this proof."],
        quality_flags=["tamper_signal"],
        processing_time_ms=120,
    )

    assert result.verdict == "Review"
    assert "Do not rely on this payment document alone" in result.recommended_action
