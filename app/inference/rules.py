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

    upper_text = raw_text.upper()
    if artifact_type == "sms_alert_screenshot" and "BALANCE" not in upper_text:
        rule_hits.append("sms.missing_balance")
        reasons.append("The SMS proof is missing a balance-style structural cue.")
    if (
        "REF" not in upper_text
        and "REFERENCE" not in upper_text
        and (extracted_fields.reference or "Not detected") == "Not detected"
    ):
        rule_hits.append("common.reference_missing")
        reasons.append("A clear transaction reference was not detected.")

    return rule_hits, reasons
