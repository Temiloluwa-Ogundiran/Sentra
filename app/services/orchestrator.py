import re
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.integrations.openai_orchestrator import choose_orchestrator_action
from app.models.payment_transaction import PaymentTransaction
from app.models.verification_request import VerificationRequest
from app.services.payments import initiate_recharge_checkout
from app.services.requests import _extract_media_candidate, get_or_create_user
from app.services.wallets import get_or_create_wallet

logger = get_logger(__name__)

HELP_KEYWORDS = {"hi", "hello", "help", "hey", "what do you do", "how does this work", "start"}
RECHARGE_KEYWORDS = {"recharge", "credit", "credits", "pay", "payment", "top up", "topup", "fund"}
EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)


@dataclass(slots=True)
class OrchestratorDecision:
    action: str
    reply_text: str | None = None
    start_verification: bool = False
    checkout_url: str | None = None


def _normalize_text(message_payload: dict) -> str:
    return str(message_payload.get("body") or "").strip()


def _infer_email(text: str) -> str | None:
    match = EMAIL_PATTERN.search(text)
    return match.group(0) if match else None


def _is_help_message(text: str) -> bool:
    lowered = text.lower().strip()
    return any(keyword in lowered for keyword in HELP_KEYWORDS)


def _is_recharge_message(text: str) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in RECHARGE_KEYWORDS)


def _find_pending_payment(db: Session, user_id: int) -> PaymentTransaction | None:
    return (
        db.query(PaymentTransaction)
        .filter(PaymentTransaction.user_id == user_id, PaymentTransaction.status == "pending")
        .order_by(PaymentTransaction.created_at.desc())
        .first()
    )


def _find_active_request(db: Session, user_id: int) -> VerificationRequest | None:
    return (
        db.query(VerificationRequest)
        .filter(VerificationRequest.user_id == user_id, VerificationRequest.status.in_(("received", "processing")))
        .order_by(VerificationRequest.created_at.desc())
        .first()
    )


def _default_reply(action: str, *, has_supported_media: bool, pending_payment: PaymentTransaction | None) -> str | None:
    if action == "reply_help":
        return (
            "Hi — Sentra checks one payment proof screenshot or PDF at a time. "
            "Send one payment proof as a JPG, PNG, or PDF file. Verification uses credits, and if you have none left, "
            "reply with your email address to get a recharge link."
        )
    if action == "reply_waiting_for_proof":
        return "Send one payment proof screenshot or PDF in JPG, PNG, or PDF format and we will check it for you."
    if action == "reply_recharge_required":
        base = (
            "you do not have any Sentra credits right now. Reply with your email address to get a recharge link for "
            f"{settings.recharge_credits_to_add} credits."
        )
        return f"We received your proof, but {base}" if has_supported_media else base.capitalize()
    if action == "reply_payment_pending":
        if pending_payment and pending_payment.checkout_url:
            return (
                "Your recharge is still pending. Complete the payment with this link, then send your proof after it "
                f"succeeds: {pending_payment.checkout_url}"
            )
        return "Your recharge is still pending. Complete the payment first, then send your proof again."
    if action == "reply_recharge_checkout":
        return "Your recharge link is ready. Complete payment from the link we just sent, then upload your proof."
    if action == "start_verification":
        return "We are checking your proof now. I will keep you updated while it runs."
    if action == "reply_processing_in_progress":
        return "We are already working on your last proof. I will send your result as soon as it is ready."
    if action == "reply_unsupported_input":
        return "Please send a payment proof as a JPG, PNG, or PDF file so I can check it properly."
    return None


async def decide_inbound_action(db: Session, payload: dict) -> OrchestratorDecision:
    event_name = payload.get("event")
    message_payload = payload.get("payload", {})
    sender = message_payload.get("from")
    if event_name != "message" or not sender:
        return OrchestratorDecision(action="ignore")

    text = _normalize_text(message_payload)
    inferred_email = _infer_email(text)
    has_supported_media = _extract_media_candidate(message_payload) is not None

    user = get_or_create_user(db, sender)
    wallet = get_or_create_wallet(db, user.id)
    pending_payment = _find_pending_payment(db, user.id)
    active_request = _find_active_request(db, user.id)

    if active_request is not None:
        action = "reply_processing_in_progress"
    elif wallet.balance <= 0 and pending_payment is not None:
        action = "reply_payment_pending"
    elif _is_help_message(text) and not has_supported_media:
        action = "reply_help"
    elif wallet.balance <= 0 and inferred_email:
        transaction, checkout = await initiate_recharge_checkout(
            db,
            user=user,
            customer_email=inferred_email,
            amount_kobo=settings.recharge_amount_kobo,
            credits_to_add=settings.recharge_credits_to_add,
        )
        checkout_data = checkout.get("data", {}) if isinstance(checkout, dict) else {}
        checkout_url = checkout_data.get("checkout_url") or checkout_data.get("checkoutLink") or transaction.checkout_url
        logger.info(
            "orchestrator created recharge checkout",
            extra={
                "extra_payload": {
                    "sender": sender,
                    "user_id": user.id,
                    "wallet_balance": wallet.balance,
                    "transaction_ref": transaction.transaction_ref,
                }
            },
        )
        return OrchestratorDecision(
            action="reply_recharge_checkout",
            reply_text=(
                f"Recharge link ready for {settings.recharge_credits_to_add} credits. Complete payment here: {checkout_url}"
                if checkout_url
                else "Recharge started. Complete the payment from the link we just created for you."
            ),
            checkout_url=checkout_url,
        )
    elif wallet.balance <= 0:
        action = "reply_recharge_required"
    elif has_supported_media:
        action = "start_verification"
    elif message_payload.get("image") or message_payload.get("document") or message_payload.get("video"):
        action = "reply_unsupported_input"
    else:
        action = "reply_waiting_for_proof"

    context = {
        "sender": sender,
        "message_text": text,
        "wallet_balance": wallet.balance,
        "has_supported_media": has_supported_media,
        "has_pending_payment": pending_payment is not None,
        "active_request_status": active_request.status if active_request else None,
        "inferred_email": inferred_email,
    }
    allowed_actions = list(
        dict.fromkeys(
            [
                action,
                "reply_help",
                "reply_waiting_for_proof",
                "reply_recharge_required",
                "reply_payment_pending",
                "reply_processing_in_progress",
                "reply_unsupported_input",
                "start_verification",
            ]
        )
    )
    model_response = await choose_orchestrator_action(context, allowed_actions)
    selected_action = model_response.action if model_response else action
    reply_text = model_response.reply_text if model_response and model_response.reply_text else _default_reply(
        selected_action,
        has_supported_media=has_supported_media,
        pending_payment=pending_payment,
    )
    logger.info(
        "orchestrator decision",
        extra={
            "extra_payload": {
                "sender": sender,
                "wallet_balance": wallet.balance,
                "has_supported_media": has_supported_media,
                "pending_payment": pending_payment is not None,
                "active_request": active_request.status if active_request else None,
                "action": selected_action,
            }
        },
    )
    return OrchestratorDecision(
        action=selected_action,
        reply_text=reply_text,
        start_verification=selected_action == "start_verification",
    )
