from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("verification_requests.id"), index=True)
    source_path: Mapped[str] = mapped_column(String(255))
    annotated_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mime_type: Mapped[str] = mapped_column(String(64))
    original_filename: Mapped[str] = mapped_column(String(255))
    detected_artifact_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    file_size: Mapped[int] = mapped_column(Integer)
