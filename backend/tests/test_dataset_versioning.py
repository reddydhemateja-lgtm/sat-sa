"""
Dataset versioning behaviour.

Re-uploading the same filename for the same entity+period must NOT
overwrite — it must increment version.
"""

from __future__ import annotations

import asyncio

import pytest
from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.models.cse import CSEEntity
from app.models.ingestion import DataSubmission
from app.models.period import AssessmentPeriod
from app.routers.ingestion import _next_dataset_version


@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
def setup_db():
    async def _setup():
        async with engine.begin() as conn:
            import app.models  # noqa
            await conn.run_sync(Base.metadata.create_all)
    asyncio.new_event_loop().run_until_complete(_setup())


@pytest.mark.asyncio
async def test_versioning_increments(setup_db):
    async with SessionLocal() as db:
        entity = (
            await db.execute(select(CSEEntity).limit(1))
        ).scalar_one_or_none()
        period = (
            await db.execute(select(AssessmentPeriod).limit(1))
        ).scalar_one_or_none()
        if entity is None or period is None:
            pytest.skip("Seed data not present; run seed first")

        filename = "_pytest_version_test.csv"

        # Clean any leftovers from previous runs
        prior = (
            await db.execute(
                select(DataSubmission).where(
                    DataSubmission.entity_id == entity.id,
                    DataSubmission.period_id == period.id,
                    DataSubmission.file_name == filename,
                )
            )
        ).scalars().all()
        for row in prior:
            await db.delete(row)
        await db.commit()

        v1 = await _next_dataset_version(
            db,
            entity_id=entity.id,
            period_id=period.id,
            file_name=filename,
        )
        assert v1 == 1

        db.add(
            DataSubmission(
                entity_id=entity.id,
                period_id=period.id,
                file_name=filename,
                file_hash="x",
                format="csv",
                payload_type="alerts",
                version=v1,
            )
        )
        await db.commit()

        v2 = await _next_dataset_version(
            db,
            entity_id=entity.id,
            period_id=period.id,
            file_name=filename,
        )
        assert v2 == 2

        # Cleanup
        prior = (
            await db.execute(
                select(DataSubmission).where(
                    DataSubmission.entity_id == entity.id,
                    DataSubmission.period_id == period.id,
                    DataSubmission.file_name == filename,
                )
            )
        ).scalars().all()
        for row in prior:
            await db.delete(row)
        await db.commit()