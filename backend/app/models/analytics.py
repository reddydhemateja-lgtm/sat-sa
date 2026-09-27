import enum
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Enum,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin


class FindingCategoryEnum(str, enum.Enum):
    EXECUTION_GAP = "EXECUTION_GAP"
    NEGATIVE_SPACE = "NEGATIVE_SPACE"
    ANOMALY = "ANOMALY"
    PEER_DEVIATION = "PEER_DEVIATION"
    DATA_QUALITY = "DATA_QUALITY"


class PriorityEnum(str, enum.Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFORMATIONAL = "INFORMATIONAL"


class Finding(Base, TimestampMixin):
    __tablename__ = "findings"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    entity_id: Mapped[int] = mapped_column(
        ForeignKey("cse_entities.id", ondelete="CASCADE"), index=True
    )
    period_id: Mapped[int] = mapped_column(
        ForeignKey("assessment_periods.id", ondelete="CASCADE"), index=True
    )
    category: Mapped[FindingCategoryEnum] = mapped_column(
        Enum(FindingCategoryEnum), index=True
    )
    rule_id: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(255))
    narrative: Mapped[str] = mapped_column(Text)
    expected_behavior: Mapped[str | None] = mapped_column(Text, nullable=True)
    observed_pattern: Mapped[str | None] = mapped_column(Text, nullable=True)
    analytical_basis: Mapped[str] = mapped_column(Text)
    priority: Mapped[PriorityEnum] = mapped_column(Enum(PriorityEnum), index=True)
    confidence: Mapped[Decimal] = mapped_column(Numeric(4, 3))
    review_indicator: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    metrics: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="OPEN")


class Evidence(Base, TimestampMixin):
    __tablename__ = "evidence"

    id: Mapped[int] = mapped_column(primary_key=True)
    finding_id: Mapped[int] = mapped_column(
        ForeignKey("findings.id", ondelete="CASCADE"), index=True
    )
    record_type: Mapped[str] = mapped_column(String(32))
    record_id: Mapped[int] = mapped_column(Integer, index=True)
    snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    weight: Mapped[Decimal] = mapped_column(Numeric(4, 3), default=Decimal("1.0"))


class PeerComparison(Base, TimestampMixin):
    __tablename__ = "peer_comparisons"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(
        ForeignKey("cse_entities.id", ondelete="CASCADE"), index=True
    )
    period_id: Mapped[int] = mapped_column(
        ForeignKey("assessment_periods.id", ondelete="CASCADE"), index=True
    )
    peer_group: Mapped[str] = mapped_column(String(64), index=True)
    metric: Mapped[str] = mapped_column(String(64), index=True)
    entity_value: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    peer_median: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    peer_p25: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    peer_p75: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    z_score: Mapped[Decimal] = mapped_column(Numeric(8, 4))
    sample_size: Mapped[int] = mapped_column(Integer)