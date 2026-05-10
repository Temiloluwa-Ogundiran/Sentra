from pathlib import Path


def classify_artifact(file_path: Path, mime_type: str) -> str:
    lower_name = file_path.name.lower()
    if mime_type == "application/pdf":
        return "receipt_pdf_render"
    if "sms" in lower_name:
        return "sms_alert_screenshot"
    if "receipt" in lower_name:
        return "payment_receipt_screenshot"
    return "bank_alert_screenshot"
