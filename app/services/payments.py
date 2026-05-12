import hmac
from datetime import UTC, datetime
from hashlib import sha512
from uuid import uuid4

from sqlalchemy.orm import Session

from app.integrations.squad import SquadClient
from app.models.payment_transaction import PaymentTransaction
from app.models.user import User
from app.services.wallets import apply_credit_recharge, get_or_create_wallet


def create_payment_reference(prefix: str = "sentra") -> str:
    return f"{prefix}_{uuid4().hex}"


def create_recharge_transaction(
    db: Session,
    *,
    user: User,
    customer_email: str,
    amount_kobo: int,
    credits_to_add: int,
) -> PaymentTransaction:
    transaction = PaymentTransaction(
        user_id=user.id,
        transaction_ref=create_payment_reference(),
        customer_email=customer_email,
        amount_kobo=amount_kobo,
        credits_to_add=credits_to_add,
        status="pending",
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


async def initiate_recharge_checkout(
    db: Session,
    *,
    user: User,
    customer_email: str,
    amount_kobo: int,
    credits_to_add: int,
) -> tuple[PaymentTransaction, dict]:
    transaction = create_recharge_transaction(
        db,
        user=user,
        customer_email=customer_email,
        amount_kobo=amount_kobo,
        credits_to_add=credits_to_add,
    )
    checkout = await SquadClient().create_credit_checkout(
        customer_email=customer_email,
        amount_kobo=amount_kobo,
        credits_to_add=credits_to_add,
        user_id=user.id,
        transaction_ref=transaction.transaction_ref,
    )
    checkout_data = checkout.get("data", {}) if isinstance(checkout, dict) else {}
    transaction.checkout_url = checkout_data.get("checkout_url") or checkout_data.get("checkoutLink")
    db.commit()
    db.refresh(transaction)
    return transaction, checkout


def verify_squad_signature(raw_body: bytes, header_signature: str | None, secret_key: str) -> bool:
    if not header_signature or not secret_key:
        return False
    computed = hmac.new(secret_key.encode("utf-8"), raw_body, sha512).hexdigest().upper()
    return hmac.compare_digest(computed, header_signature.upper())


async def verify_transaction_status(transaction_ref: str) -> dict:
    return await SquadClient().verify_transaction(transaction_ref)


def apply_successful_recharge(
    db: Session,
    *,
    transaction: PaymentTransaction,
    squad_status: str,
) -> PaymentTransaction:
    if transaction.applied_at is not None:
        return transaction

    wallet = get_or_create_wallet(db, transaction.user_id)
    apply_credit_recharge(
        db,
        wallet,
        credits_to_add=transaction.credits_to_add,
        payment_reference=transaction.transaction_ref,
    )
    transaction.status = "applied"
    transaction.squad_transaction_status = squad_status
    transaction.verified_at = datetime.now(UTC)
    transaction.applied_at = datetime.now(UTC)
    db.commit()
    db.refresh(transaction)
    return transaction


async def process_squad_webhook(
    db: Session,
    *,
    raw_body: bytes,
    payload: dict,
    header_signature: str | None,
    secret_key: str,
) -> tuple[int, dict]:
    if not verify_squad_signature(raw_body, header_signature, secret_key):
        return 401, {"status": "invalid_signature"}

    body = payload.get("Body", {})
    transaction_ref = body.get("transaction_ref") or payload.get("TransactionRef")
    if not transaction_ref:
        return 400, {"status": "missing_transaction_ref"}

    transaction = db.query(PaymentTransaction).filter(PaymentTransaction.transaction_ref == transaction_ref).one_or_none()
    if transaction is None:
        return 404, {"status": "unknown_transaction", "transaction_ref": transaction_ref}

    verified = await verify_transaction_status(transaction_ref)
    verified_body = verified.get("data", {}) if isinstance(verified, dict) else {}
    squad_status = str(verified_body.get("transaction_status", "")).lower()
    transaction.status = squad_status or transaction.status
    transaction.squad_transaction_status = squad_status or transaction.squad_transaction_status
    transaction.verified_at = datetime.now(UTC)
    db.commit()

    if squad_status == "success":
        transaction = apply_successful_recharge(db, transaction=transaction, squad_status=squad_status)
        return 200, {"status": "applied", "transaction_ref": transaction.transaction_ref}

    return 202, {"status": squad_status or "pending", "transaction_ref": transaction.transaction_ref}
