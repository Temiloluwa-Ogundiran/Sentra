from app.inference.fusion import fuse_result
from app.schemas.common import ExtractedFields


def test_fuse_result_review_on_low_quality():
    result = fuse_result(
        request_id=1,
        artifact_type="sms_alert_screenshot",
        extracted_fields=ExtractedFields(),
        reasons=["Low confidence"],
        quality_flags=["low_resolution"],
        processing_time_ms=100,
    )
    assert result.verdict == "Review"


def test_fuse_result_match_when_clean():
    result = fuse_result(
        request_id=2,
        artifact_type="payment_receipt_screenshot",
        extracted_fields=ExtractedFields(),
        reasons=[],
        quality_flags=[],
        processing_time_ms=100,
    )
    assert result.verdict == "High-confidence pattern match"
