"""API connector configuration model.

Connectors describe WHERE periodic CSE submissions can be pulled from when
an entity has an internal REST API rather than a flat-file drop. In this
prototype only demo/internal connectors are supported; real CSE endpoints
are out of scope. Every connector row carries `is_demo=True` unless an
operator deliberately sets otherwise, and the UI must surface that label.
"""

from __future__ import annotations

from sqlalchemy import Boolean, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin


class APIConnector(Base, TimestampMixin):
    __tablename__ = "api_connectors"

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str] = mapped_column(String(128), nullable=False)

    # e.g. "DEMO_SOC_API", "INTERNAL_REST", "DB_ADAPTER"
    connector_type: Mapped[str] = mapped_column(String(32), nullable=False)

    # Not required for demo connectors; kept for future real integrations.
    base_url: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # "PERIODIC_PULL" | "MANUAL_PULL"
    mode: Mapped[str] = mapped_column(String(32), nullable=False, default="PERIODIC_PULL")

    # Demo connectors are always True in this prototype.
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # "CONFIGURED" | "TESTED" | "ERROR"
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="CONFIGURED")

    # Comma-separated payload types this connector is expected to deliver.
    payload_types: Mapped[str | None] = mapped_column(String(255), nullable=True)

    last_run_at: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_run_summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)