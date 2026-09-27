import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin


class ReviewDecisionEnum(str, enum.Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"
    FURTHER_REVIEW = "FURTHER_REVIEW"


class ReviewDecision(Base, TimestampMixin):
    __tablename__ = "review_decisions"

    id: Mapped[int] = mapped_column(primary_key=True)
    finding_id: Mapped[int] = mapped_column(
        ForeignKey("findings.id", ondelete="CASCADE"), index=True
    )
    reviewer_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    decision: Mapped[ReviewDecisionEnum] = mapped_column(Enum(ReviewDecisionEnum))
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    previous_decision: Mapped[str | None] = mapped_column(String(24), nullable=True)
    decided_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )