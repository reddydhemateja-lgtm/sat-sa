import enum
from datetime import datetime
from typing import Any

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin


class SeverityEnum(str, enum.Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class AlertStatusEnum(str, enum.Enum):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    INVESTIGATING = "INVESTIGATING"
    ESCALATED = "ESCALATED"
    CLOSED = "CLOSED"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    SUPPRESSED = "SUPPRESSED"


class Alert(Base, TimestampMixin):
    __tablename__ = "alerts"
    __table_args__ = (
        UniqueConstraint("entity_id", "external_id", name="uq_alert_entity_external"),
        Index("ix_alert_entity_period", "entity_id", "period_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(
        ForeignKey("cse_entities.id", ondelete="CASCADE"), index=True
    )
    period_id: Mapped[int] = mapped_column(
        ForeignKey("assessment_periods.id", ondelete="CASCADE"), index=True
    )
    submission_id: Mapped[int | None] = mapped_column(
        ForeignKey("data_submissions.id", ondelete="SET NULL"), nullable=True
    )
    external_id: Mapped[str] = mapped_column(String(128), index=True)
    title: Mapped[str] = mapped_column(String(512))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[SeverityEnum] = mapped_column(Enum(SeverityEnum), index=True)
    category: Mapped[str] = mapped_column(String(64), index=True)
    source_system: Mapped[str | None] = mapped_column(String(64), nullable=True)
    asset_id: Mapped[int | None] = mapped_column(
        ForeignKey("assets.id", ondelete="SET NULL"), nullable=True
    )
    detected_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[AlertStatusEnum] = mapped_column(Enum(AlertStatusEnum), index=True)
    raw: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)


class Case(Base, TimestampMixin):
    __tablename__ = "cases"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(
        ForeignKey("cse_entities.id", ondelete="CASCADE"), index=True
    )
    period_id: Mapped[int] = mapped_column(
        ForeignKey("assessment_periods.id", ondelete="CASCADE"), index=True
    )
    external_id: Mapped[str] = mapped_column(String(128), index=True)
    alert_id: Mapped[int | None] = mapped_column(
        ForeignKey("alerts.id", ondelete="SET NULL"), index=True, nullable=True
    )
    title: Mapped[str] = mapped_column(String(512))
    severity: Mapped[SeverityEnum] = mapped_column(Enum(SeverityEnum))
    status: Mapped[str] = mapped_column(String(32), index=True)
    opened_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    assigned_to: Mapped[str | None] = mapped_column(String(128), nullable=True)
    raw: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)


class Investigation(Base, TimestampMixin):
    __tablename__ = "investigations"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(
        ForeignKey("cases.id", ondelete="CASCADE"), index=True
    )
    entity_id: Mapped[int] = mapped_column(
        ForeignKey("cse_entities.id", ondelete="CASCADE"), index=True
    )
    investigator: Mapped[str | None] = mapped_column(String(128), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    artifacts_count: Mapped[int] = mapped_column(Integer, default=0)
    content_hash: Mapped[str | None] = mapped_column(
        String(64), index=True, nullable=True
    )
    content_length: Mapped[int] = mapped_column(Integer, default=0)
    raw: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)


class Escalation(Base, TimestampMixin):
    __tablename__ = "escalations"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(
        ForeignKey("cse_entities.id", ondelete="CASCADE"), index=True
    )
    case_id: Mapped[int] = mapped_column(
        ForeignKey("cases.id", ondelete="CASCADE"), index=True
    )
    escalated_at: Mapped[datetime] = mapped_column(DateTime)
    escalated_to: Mapped[str] = mapped_column(String(128))
    level: Mapped[int] = mapped_column(Integer, default=1)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class AlertDisposition(Base, TimestampMixin):
    __tablename__ = "alert_dispositions"

    id: Mapped[int] = mapped_column(primary_key=True)
    alert_id: Mapped[int] = mapped_column(
        ForeignKey("alerts.id", ondelete="CASCADE"), unique=True
    )
    entity_id: Mapped[int] = mapped_column(
        ForeignKey("cse_entities.id", ondelete="CASCADE"), index=True
    )
    disposition: Mapped[str] = mapped_column(String(64))
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    closed_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    closure_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)