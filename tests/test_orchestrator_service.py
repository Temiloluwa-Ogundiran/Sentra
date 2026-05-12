from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.credit_wallet import CreditWallet
from app.models.payment_transaction import PaymentTransaction
from app.models.user import User
from app.services.orchestrator import decide_inbound_action


def _make_session():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


async def test_decide_inbound_action_replies_with_help_for_greeting():
    session_local = _make_session()

    with session_local() as db:
        decision = await decide_inbound_action(
            db,
            payload={
                "event": "message",
                "payload": {
                    "from": "2349025283155@s.whatsapp.net",
                    "body": "Hi there",
                },
            },
        )

    assert decision.action == "reply_help"
    assert decision.start_verification is False
    assert "Send one payment proof" in (decision.reply_text or "")


async def test_decide_inbound_action_blocks_media_when_wallet_is_empty():
    session_local = _make_session()

    with session_local() as db:
        user = User(whatsapp_id="2349025283155@s.whatsapp.net")
        db.add(user)
        db.commit()
        db.refresh(user)
        db.add(CreditWallet(user_id=user.id, balance=0))
        db.commit()

        decision = await decide_inbound_action(
            db,
            payload={
                "event": "message",
                "payload": {
                    "from": "2349025283155@s.whatsapp.net",
                    "image": {
                        "url": "/media/proof.png",
                        "filename": "proof.png",
                    },
                    "body": "check this proof",
                },
            },
        )

    assert decision.action == "reply_recharge_required"
    assert decision.start_verification is False
    assert "recharge" in (decision.reply_text or "").lower()


async def test_decide_inbound_action_initiates_recharge_from_email_message(monkeypatch):
    session_local = _make_session()
    checkout_calls: list[tuple[str, str, int, int]] = []

    async def fake_initiate_recharge_checkout(db, *, user, customer_email, amount_kobo, credits_to_add):
        checkout_calls.append((user.whatsapp_id, customer_email, amount_kobo, credits_to_add))

        class Transaction:
            transaction_ref = "sentra_ref"
            status = "pending"
            checkout_url = "https://checkout.example/pay"

        return Transaction(), {"data": {"checkout_url": "https://checkout.example/pay"}}

    monkeypatch.setattr("app.services.orchestrator.initiate_recharge_checkout", fake_initiate_recharge_checkout)

    with session_local() as db:
        user = User(whatsapp_id="2349025283155@s.whatsapp.net")
        db.add(user)
        db.commit()
        db.refresh(user)
        db.add(CreditWallet(user_id=user.id, balance=0))
        db.commit()

        decision = await decide_inbound_action(
            db,
            payload={
                "event": "message",
                "payload": {
                    "from": "2349025283155@s.whatsapp.net",
                    "body": "recharge me with temi@example.com",
                },
            },
        )

    assert decision.action == "reply_recharge_checkout"
    assert decision.start_verification is False
    assert decision.checkout_url == "https://checkout.example/pay"
    assert "https://checkout.example/pay" in (decision.reply_text or "")
    assert checkout_calls == [("2349025283155@s.whatsapp.net", "temi@example.com", 500000, 20)]


async def test_decide_inbound_action_handles_recharge_checkout_failure(monkeypatch):
    session_local = _make_session()

    async def fake_initiate_recharge_checkout(db, *, user, customer_email, amount_kobo, credits_to_add):
        raise RuntimeError("Squad rejected request")

    monkeypatch.setattr("app.services.orchestrator.initiate_recharge_checkout", fake_initiate_recharge_checkout)

    with session_local() as db:
        user = User(whatsapp_id="2349025283155@s.whatsapp.net")
        db.add(user)
        db.commit()
        db.refresh(user)
        db.add(CreditWallet(user_id=user.id, balance=0))
        db.commit()

        decision = await decide_inbound_action(
            db,
            payload={
                "event": "message",
                "payload": {
                    "from": "2349025283155@s.whatsapp.net",
                    "body": "recharge me with temi@example.com",
                },
            },
        )

    assert decision.action == "reply_recharge_required"
    assert decision.start_verification is False
    assert "could not create a recharge link" in (decision.reply_text or "").lower()


async def test_decide_inbound_action_ignores_stale_pending_without_checkout_url():
    session_local = _make_session()

    with session_local() as db:
        user = User(whatsapp_id="2349025283155@s.whatsapp.net")
        db.add(user)
        db.commit()
        db.refresh(user)
        db.add(CreditWallet(user_id=user.id, balance=0))
        db.add(
            PaymentTransaction(
                user_id=user.id,
                transaction_ref="sentra_stale_ref",
                customer_email="temi@example.com",
                amount_kobo=500000,
                credits_to_add=20,
                status="pending",
                checkout_url=None,
            )
        )
        db.commit()

        decision = await decide_inbound_action(
            db,
            payload={
                "event": "message",
                "payload": {
                    "from": "2349025283155@s.whatsapp.net",
                    "body": "hello again",
                },
            },
        )

    assert decision.action == "reply_help"


async def test_decide_inbound_action_starts_verification_when_wallet_has_credit():
    session_local = _make_session()

    with session_local() as db:
        user = User(whatsapp_id="2349025283155@s.whatsapp.net")
        db.add(user)
        db.commit()
        db.refresh(user)
        db.add(CreditWallet(user_id=user.id, balance=3))
        db.commit()

        decision = await decide_inbound_action(
            db,
            payload={
                "event": "message",
                "payload": {
                    "from": "2349025283155@s.whatsapp.net",
                    "image": {
                        "url": "/media/proof.png",
                        "filename": "proof.png",
                    },
                    "body": "please check this",
                },
            },
        )

    assert decision.action == "start_verification"
    assert decision.start_verification is True
    assert "checking your proof" in (decision.reply_text or "").lower()


async def test_decide_inbound_action_reports_pending_payment():
    session_local = _make_session()

    with session_local() as db:
        user = User(whatsapp_id="2349025283155@s.whatsapp.net")
        db.add(user)
        db.commit()
        db.refresh(user)
        db.add(CreditWallet(user_id=user.id, balance=0))
        db.add(
            PaymentTransaction(
                user_id=user.id,
                transaction_ref="sentra_test_ref",
                customer_email="temi@example.com",
                amount_kobo=500000,
                credits_to_add=20,
                status="pending",
                checkout_url="https://checkout.example/pending",
            )
        )
        db.commit()

        decision = await decide_inbound_action(
            db,
            payload={
                "event": "message",
                "payload": {
                    "from": "2349025283155@s.whatsapp.net",
                    "body": "hello again",
                },
            },
        )

    assert decision.action == "reply_payment_pending"
    assert "pending" in (decision.reply_text or "").lower()
