import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.user import User
from app.services.wallets import (
    InsufficientCreditsError,
    apply_credit_recharge,
    consume_verification_credit,
    get_or_create_wallet,
)


def _make_session():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def test_apply_credit_recharge_updates_balance_and_reference():
    session_local = _make_session()
    with session_local() as db:
        user = User(whatsapp_id="2348012345678")
        db.add(user)
        db.commit()
        db.refresh(user)

        wallet = get_or_create_wallet(db, user.id)
        updated = apply_credit_recharge(db, wallet, credits_to_add=20, payment_reference="ref_123")

    assert updated.balance == 20
    assert updated.last_payment_reference == "ref_123"


def test_consume_verification_credit_raises_when_balance_is_low():
    session_local = _make_session()
    with session_local() as db:
        user = User(whatsapp_id="2348012345678")
        db.add(user)
        db.commit()
        db.refresh(user)

        wallet = get_or_create_wallet(db, user.id)

        with pytest.raises(InsufficientCreditsError):
            consume_verification_credit(db, wallet, cost=1)


def test_consume_verification_credit_seeds_dev_wallet_once():
    session_local = _make_session()
    with session_local() as db:
        user = User(whatsapp_id="dev-user")
        db.add(user)
        db.commit()
        db.refresh(user)

        wallet = get_or_create_wallet(db, user.id)
        updated = consume_verification_credit(db, wallet, cost=1, auto_seed_dev=True)

    assert updated.balance == 9
