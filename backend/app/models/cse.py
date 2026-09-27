from typing import Any

from sqlalchemy import Boolean, ForeignKey, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin


class CSEEntity(Base, TimestampMixin):
    __tablename__ = "cse_entities"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    sector: Mapped[str] = mapped_column(String(64), index=True)
    sub_sector: Mapped[str | None] = mapped_column(String(64), nullable=True)
    region: Mapped[str | None] = mapped_column(String(64), nullable=True)
    criticality: Mapped[str] = mapped_column(String(16), default="HIGH")
    peer_group: Mapped[str | None] = mapped_column(
        String(64), index=True, nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Asset(Base, TimestampMixin):
    __tablename__ = "assets"
    __table_args__ = (
        UniqueConstraint("entity_id", "asset_code", name="uq_asset_entity_code"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(
        ForeignKey("cse_entities.id", ondelete="CASCADE"), index=True
    )
    asset_code: Mapped[str] = mapped_column(String(64), index=True)
    hostname: Mapped[str | None] = mapped_column(String(255), nullable=True)
    asset_type: Mapped[str] = mapped_column(String(32))
    criticality: Mapped[str] = mapped_column(String(16), default="MEDIUM")
    tags: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)