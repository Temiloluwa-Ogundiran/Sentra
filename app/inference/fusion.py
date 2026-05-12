from app.schemas.common import CanonicalResult, ExtractedFields


SUSPICIOUS_ACTION = "Do not release goods yet. Request another proof or confirm payment through a safer channel."
REVIEW_ACTION = "Do not rely on this proof alone. Ask for a clearer screenshot or original receipt document."
MATCH_ACTION = "This proof matches known patterns with no major issues detected. Proceed at your discretion."


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        normalized = value.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered


def fuse_result(
    request_id: int,
    artifact_type: str,
    extracted_fields: ExtractedFields,
    reasons: list[str],
    quality_flags: list[str],
    processing_time_ms: int,
    expected_amount: str | None = None,
    annotated_artifact_path: str | None = None,
) -> CanonicalResult:
    strong_signal_count = sum(
        flag in quality_flags for flag in ("synthetic_artifact_signal", "tamper_signal", "reasoner_suspicious_signal")
    )
    has_missing_reasons = any("missing" in reason.lower() or "not detected" in reason.lower() for reason in reasons)

    if "unreadable_artifact" in quality_flags or "low_resolution" in quality_flags:
        verdict = "Review"
        action = REVIEW_ACTION
    elif strong_signal_count >= 2:
        verdict = "Suspicious"
        action = SUSPICIOUS_ACTION
    elif strong_signal_count == 1 or has_missing_reasons:
        verdict = "Review"
        action = REVIEW_ACTION
    else:
        verdict = "High-confidence pattern match"
        action = MATCH_ACTION

    if not reasons:
        if verdict == "High-confidence pattern match":
            reasons = ["No major anomaly or tamper signals were detected in this proof format."]
        elif verdict == "Review":
            reasons = ["The system could not confidently assess this upload."]
        else:
            reasons = ["The system found unusual structure or missing proof signals."]

    return CanonicalResult(
        request_id=request_id,
        artifact_type=artifact_type,
        verdict=verdict,
        recommended_action=action,
        extracted_fields=extracted_fields,
        reasons=_dedupe(reasons)[:5],
        quality_flags=quality_flags,
        annotated_artifact_path=annotated_artifact_path,
        processing_time_ms=processing_time_ms,
        expected_amount=expected_amount,
    )
