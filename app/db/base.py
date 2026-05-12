from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    pass


engine_kwargs = {"future": True}
if settings.database_url.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(settings.database_url, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_db() -> None:
    from app.models.analysis_result import AnalysisResult
    from app.models.artifact import Artifact
    from app.models.extraction import Extraction
    from app.models.credit_wallet import CreditWallet
    from app.models.payment_transaction import PaymentTransaction
    from app.models.user import User
    from app.models.verification_request import VerificationRequest

    Base.metadata.create_all(bind=engine)
