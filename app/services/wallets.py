from sqlalchemy.orm import Session

from app.models.credit_wallet import CreditWallet


class InsufficientCreditsError(Exception):
    pass


def get_or_create_wallet(db: Session, user_id: int, *, initial_balance: int = 0) -> CreditWallet:
    wallet = db.query(CreditWallet).filter(CreditWallet.user_id == user_id).one_or_none()
    if wallet:
        return wallet
    wallet = CreditWallet(user_id=user_id, balance=initial_balance)
    db.add(wallet)
    db.commit()
    db.refresh(wallet)
    return wallet


def apply_credit_recharge(
    db: Session,
    wallet: CreditWallet,
    *,
    credits_to_add: int,
    payment_reference: str,
) -> CreditWallet:
    wallet.balance += credits_to_add
    wallet.last_payment_reference = payment_reference
    db.commit()
    db.refresh(wallet)
    return wallet


def consume_verification_credit(
    db: Session,
    wallet: CreditWallet,
    *,
    cost: int = 1,
    auto_seed_dev: bool = False,
) -> CreditWallet:
    if auto_seed_dev and wallet.balance <= 0:
        wallet.balance = 10

    if wallet.balance < cost:
        raise InsufficientCreditsError("Insufficient verification credits.")

    wallet.balance -= cost
    db.commit()
    db.refresh(wallet)
    return wallet
