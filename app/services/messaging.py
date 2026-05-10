from pathlib import Path

from app.integrations.gowa import GowaClient
from app.schemas.common import CanonicalResult


def render_whatsapp_message(result: CanonicalResult) -> str:
    fields = result.extracted_fields
    return "\n".join(
        [
            f"Verdict: {result.verdict}",
            f"Artifact type: {result.artifact_type}",
            "Extracted fields:",
            f"- Amount: {fields.amount or 'Not detected'}",
            f"- Currency: {fields.currency or 'Not detected'}",
            f"- Date: {fields.date or 'Not detected'}",
            f"- Time: {fields.time or 'Not detected'}",
            f"- Reference: {fields.reference or 'Not detected'}",
            f"- Provider: {fields.provider or 'Not detected'}",
            f"- Recipient label: {fields.recipient_label or 'Not detected'}",
            "Why:",
            *[f"- {reason}" for reason in result.reasons],
            f"Recommended action: {result.recommended_action}",
        ]
    )


async def send_result(whatsapp_id: str, result: CanonicalResult) -> None:
    client = GowaClient()
    message = render_whatsapp_message(result)
    await client.send_text(whatsapp_id, message)
    if result.annotated_artifact_path and Path(result.annotated_artifact_path).exists():
        await client.send_file(whatsapp_id, Path(result.annotated_artifact_path), caption="Sentra analysis preview")
