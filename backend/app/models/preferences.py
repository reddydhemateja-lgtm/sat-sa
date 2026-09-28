"""
Dataset preferences — used by the Settings > Data Source feature.

Each row tracks how a supervisor wants to view a specific submission:
    - included: shown in "Modified Data" mode
    - deleted:  hidden from "Modified Data" mode (but always visible in "Complete Data")

The underlying records are never modified by these flags.
"""

from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin


class DatasetPreference(Base, TimestampMixin):
    __tablename__ = "dataset_preferences"

    id: Mapped[int] = mapped_column(primary_key=True)
    submission_id: Mapped[int] = mapped_column(
        ForeignKey("data_submissions.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    included: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)