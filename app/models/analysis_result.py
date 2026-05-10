from sqlalchemy import ForeignKey, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("verification_requests.id"), index=True)
    verdict: Mapped[str] = mapped_column(Text)
    recommended_action: Mapped[str] = mapped_column(Text)
    reasons: Mapped[list] = mapped_column(JSON, default=list)
    quality_flags: Mapped[list] = mapped_column(JSON, default=list)
    internal_rule_hits: Mapped[list] = mapped_column(JSON, default=list)
    internal_model_scores: Mapped[dict] = mapped_column(JSON, default=dict)
