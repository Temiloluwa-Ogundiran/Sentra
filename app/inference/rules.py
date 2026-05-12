from app.schemas.common import ExtractedFields


def run_rules(
    artifact_type: str,
    raw_text: str,
    extracted_fields: ExtractedFields,
    quality_flags: list[str],
) -> tuple[list[str], list[str]]:
    rule_hits: list[str] = []
    reasons: list[str] = []

    if "low_resolution" in quality_flags:
        rule_hits.append("quality.low_resolution")
        reasons.append("The upload quality is too low for a confident check.")
    if "edited_overlay_signal" in quality_flags:
        rule_hits.append("quality.edited_overlay")
        reasons.append("A visible marker, paint-over, or edited overlay was detected on this payment document.")
    if "reference_clone_signal" in quality_flags:
        rule_hits.append("quality.reference_clone")
        reasons.append("This payment document is nearly identical to a known sample layout, which can indicate cloning or AI regeneration.")

    upper_text = raw_text.upper()
    if "EDITED" in upper_text or "ALTERED" in upper_text:
        rule_hits.append("common.edited_marker_detected")
        reasons.append("Visible edited markers or altered labels were detected on this payment document.")
    if artifact_type == "sms_alert_screenshot" and "BALANCE" not in upper_text:
        rule_hits.append("sms.missing_balance")
        reasons.append("The SMS payment document is missing a balance-style structural cue.")
    if (
        "REF" not in upper_text
        and "REFERENCE" not in upper_text
        and (extracted_fields.reference or "Not detected") == "Not detected"
    ):
        rule_hits.append("common.reference_missing")
        reasons.append("A clear transaction reference was not detected.")

    return rule_hits, reasons
