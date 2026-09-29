from typing import Any

from sqlalchemy import ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin


class DataSubmission(Base, TimestampMixin):
    __tablename__ = "data_submissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(
        ForeignKey("cse_entities.id", ondelete="CASCADE"), index=True
    )
    period_id: Mapped[int] = mapped_column(
        ForeignKey("assessment_periods.id", ondelete="CASCADE"), index=True
    )
    submitted_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    file_name: Mapped[str] = mapped_column(String(255))
    file_hash: Mapped[str] = mapped_column(String(64), index=True)
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    format: Mapped[str] = mapped_column(String(16))
    payload_type: Mapped[str] = mapped_column(String(32), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(24), default="PENDING")
    records_received: Mapped[int] = mapped_column(Integer, default=0)
    records_valid: Mapped[int] = mapped_column(Integer, default=0)
    records_warning: Mapped[int] = mapped_column(Integer, default=0)
    records_error: Mapped[int] = mapped_column(Integer, default=0)
    validation_report: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)