from pathlib import Path

from app.core.logging import get_logger
from app.integrations.gowa import GowaClient
from app.schemas.common import CanonicalResult

logger = get_logger(__name__)

PROCESSING_STAGE_TEXT = {
    "preparing": "We are preparing your payment document for checking.",
    "reading_proof": "We are reading the payment document now.",
    "checking_details": "We are checking the payment details.",
    "reviewing_changes": "We are reviewing the payment document for unusual changes.",
    "finalizing": "We are finishing your result.",
    "failed": "We hit a delay while checking your payment document. We will send the final status shortly.",
}

ARTIFACT_TYPE_LABELS = {
    "bank_alert_screenshot": "Bank alert screenshot",
    "sms_alert_screenshot": "SMS alert screenshot",
    "payment_receipt_screenshot": "Payment receipt screenshot",
    "receipt_pdf_render": "Receipt PDF render",
}


def _format_artifact_type(artifact_type: str) -> str:
    return ARTIFACT_TYPE_LABELS.get(artifact_type, artifact_type.replace("_", " ").strip().title())


def _sanitize_user_reason(reason: str) -> str | None:
    normalized = reason.strip()
    lowered = normalized.lower()

    if "temporarily unavailable" in lowered or "fallback checks" in lowered:
        return None
    if "image-integrity check raised a caution flag" in lowered:
        return "This payment document may have been edited."
    return normalized


def _render_reason_lines(result: CanonicalResult) -> list[str]:
    if "synthetic_render_signal" in result.quality_flags:
        return ["• Image appears to be AI generated."]
    sanitized = [cleaned for reason in result.reasons if (cleaned := _sanitize_user_reason(reason))]
    if sanitized:
        return [f"• {reason}" for reason in sanitized]
    return ["• We found unusual signs in this payment document."]


def render_whatsapp_message(result: CanonicalResult) -> str:
    fields = result.extracted_fields
    return "\n".join(
        [
            "🧾 Sentra check result",
            "",
            f"• Verdict: {result.verdict}",
            f"• Payment document type: {_format_artifact_type(result.artifact_type)}",
            "",
            "Detected details",
            f"• Amount: {fields.amount or 'Not detected'}",
            f"• Currency: {fields.currency or 'Not detected'}",
            f"• Date: {fields.date or 'Not detected'}",
            f"• Time: {fields.time or 'Not detected'}",
            f"• Reference: {fields.reference or 'Not detected'}",
            f"• Provider: {fields.provider or 'Not detected'}",
            f"• Recipient: {fields.recipient_label or 'Not detected'}",
            "",
            "Why we said this",
            *_render_reason_lines(result),
            "",
            f"Advise: {result.recommended_action}",
        ]
    )


def _should_send_visual_preview(result: CanonicalResult) -> bool:
    return "edited_overlay_signal" in result.quality_flags


async def send_typing_indicator(whatsapp_id: str) -> None:
    logger.info("sending typing indicator", extra={"extra_payload": {"whatsapp_id": whatsapp_id}})
    try:
        await GowaClient().send_chat_presence(whatsapp_id, presence="composing", media_type="text")
    except Exception:
        logger.exception(
            "typing indicator request failed",
            extra={"extra_payload": {"whatsapp_id": whatsapp_id}},
        )


async def send_processing_update(whatsapp_id: str, stage: str) -> None:
    message = PROCESSING_STAGE_TEXT.get(stage)
    if not message:
        return
    await send_typing_indicator(whatsapp_id)
    logger.info(
        "sending processing update",
        extra={"extra_payload": {"whatsapp_id": whatsapp_id, "stage": stage}},
    )
    await GowaClient().send_text(whatsapp_id, message)


async def send_payment_success_message(whatsapp_id: str, text: str) -> None:
    await send_typing_indicator(whatsapp_id)
    logger.info("sending payment success message", extra={"extra_payload": {"whatsapp_id": whatsapp_id}})
    await GowaClient().send_text(whatsapp_id, text)


async def send_result(whatsapp_id: str, result: CanonicalResult) -> None:
    client = GowaClient()
    message = render_whatsapp_message(result)
    await send_typing_indicator(whatsapp_id)
    logger.info(
        "sending final result",
        extra={"extra_payload": {"whatsapp_id": whatsapp_id, "request_id": result.request_id}},
    )
    await client.send_text(whatsapp_id, message)
    if _should_send_visual_preview(result) and result.annotated_artifact_path and Path(result.annotated_artifact_path).exists():
        try:
            await client.send_image(whatsapp_id, Path(result.annotated_artifact_path), caption="Sentra analysis preview")
        except Exception:
            logger.exception(
                "sending annotated preview failed",
                extra={"extra_payload": {"whatsapp_id": whatsapp_id, "request_id": result.request_id}},
            )
