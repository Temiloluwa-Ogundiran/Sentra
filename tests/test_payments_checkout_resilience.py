from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.user import User
from app.services.payments import initiate_recharge_checkout


def _make_session():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


async def test_initiate_recharge_checkout_marks_transaction_failed_when_provider_rejects(monkeypatch):
    session_local = _make_session()

    async def fake_create_credit_checkout(self, **kwargs):
        raise RuntimeError("forbidden")

    monkeypatch.setattr("app.services.payments.SquadClient.create_credit_checkout", fake_create_credit_checkout)

    with session_local() as db:
        user = User(whatsapp_id="2349025283155@s.whatsapp.net")
        db.add(user)
        db.commit()
        db.refresh(user)

        try:
            await initiate_recharge_checkout(
                db,
                user=user,
                customer_email="temi@example.com",
                amount_kobo=500000,
                credits_to_add=20,
            )
        except RuntimeError:
            pass

        transactions = db.execute(__import__("sqlalchemy").select(__import__("app.models.payment_transaction", fromlist=["PaymentTransaction"]).PaymentTransaction)).scalars().all()

    assert len(transactions) == 1
    assert transactions[0].status == "failed"
    assert transactions[0].checkout_url is None
    assert transactions[0].squad_transaction_status == "checkout_failed"
