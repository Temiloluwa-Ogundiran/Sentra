import hmac
import json
from hashlib import sha512

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.payment_transaction import PaymentTransaction
from app.models.user import User
from app.services.payments import (
    create_recharge_transaction,
    process_squad_webhook,
    verify_squad_signature,
)


def _make_session():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def test_verify_squad_signature_matches_header():
    body = b'{"Event":"charge_successful"}'
    secret = "sandbox_sk_testsecret"
    signature = hmac.new(secret.encode("utf-8"), body, sha512).hexdigest().upper()

    assert verify_squad_signature(body, signature, secret) is True


async def test_process_squad_webhook_applies_credits_once(monkeypatch):
    session_local = _make_session()
    secret = "sandbox_sk_testsecret"
    payload = {
        "Event": "charge_successful",
        "TransactionRef": "sentra_test_ref",
        "Body": {
            "transaction_ref": "sentra_test_ref",
            "transaction_status": "Success",
            "amount": 500000,
            "email": "dev@example.com",
        },
    }
    raw_body = json.dumps(payload).encode("utf-8")
    signature = hmac.new(secret.encode("utf-8"), raw_body, sha512).hexdigest().upper()

    async def fake_verify(transaction_ref: str) -> dict:
        return {"data": {"transaction_status": "Success", "transaction_ref": transaction_ref}}

    monkeypatch.setattr("app.services.payments.verify_transaction_status", fake_verify)

    with session_local() as db:
        user = User(whatsapp_id="2348012345678")
        db.add(user)
        db.commit()
        db.refresh(user)

        transaction = create_recharge_transaction(
            db,
            user=user,
            customer_email="dev@example.com",
            amount_kobo=500000,
            credits_to_add=20,
        )
        transaction.transaction_ref = "sentra_test_ref"
        db.commit()

        status_code, response = await process_squad_webhook(
            db,
            raw_body=raw_body,
            payload=payload,
            header_signature=signature,
            secret_key=secret,
        )

        updated = db.query(PaymentTransaction).filter(PaymentTransaction.transaction_ref == "sentra_test_ref").one()

    assert status_code == 200
    assert response["status"] == "applied"
    assert updated.status == "applied"
    assert updated.applied_at is not None
