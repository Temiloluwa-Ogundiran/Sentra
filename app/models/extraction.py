from sqlalchemy import ForeignKey, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Extraction(Base):
    __tablename__ = "extractions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("verification_requests.id"), index=True)
    raw_text: Mapped[str] = mapped_column(Text, default="")
    normalized_fields: Mapped[dict] = mapped_column(JSON, default=dict)
