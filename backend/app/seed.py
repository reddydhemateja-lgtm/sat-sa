"""
Idempotent seed script.

Creates the SQLite database (if needed), all tables, and a default admin user.

Usage (from the backend folder, venv active):
    python -m app.seed
"""

import asyncio
from datetime import datetime, timedelta

from sqlalchemy import select

import app.models  # noqa: F401  -- ensures every model is registered
from app.config import settings
from app.database import Base, SessionLocal, engine
from app.models.period import AssessmentPeriod
from app.models.user import RoleEnum, User
from app.security import hash_password


async def create_schema() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def upsert_admin() -> None:
    async with SessionLocal() as db:
        result = await db.execute(
            select(User).where(User.username == settings.admin_username)
        )
        existing = result.scalar_one_or_none()
        if existing is not None:
            print(f"[seed] admin user '{existing.username}' already exists (id={existing.id})")
            return

        admin = User(
            username=settings.admin_username,
            email=settings.admin_email,
            full_name="Default Administrator",
            role=RoleEnum.ADMIN,
            password_hash=hash_password(settings.admin_password),
            is_active=True,
        )
        db.add(admin)
        await db.commit()
        await db.refresh(admin)
        print(
            f"[seed] created admin user '{admin.username}' "
            f"(id={admin.id}, email={admin.email})"
        )


async def upsert_current_period() -> None:
    now = datetime.utcnow()
    quarter = (now.month - 1) // 3 + 1
    label = f"Q{quarter}-{now.year}"
    start = datetime(now.year, (quarter - 1) * 3 + 1, 1)
    end = start + timedelta(days=92)

    async with SessionLocal() as db:
        result = await db.execute(
            select(AssessmentPeriod).where(AssessmentPeriod.label == label)
        )
        existing = result.scalar_one_or_none()
        if existing is not None:
            print(f"[seed] assessment period '{label}' already exists (id={existing.id})")
            return

        period = AssessmentPeriod(
            label=label, start_date=start, end_date=end, is_active=True
        )
        db.add(period)
        await db.commit()
        await db.refresh(period)
        print(f"[seed] created assessment period '{period.label}' (id={period.id})")


async def main() -> None:
    print(f"[seed] database: {settings.database_url}")
    await create_schema()
    print("[seed] schema ensured")
    await upsert_admin()
    await upsert_current_period()
    await engine.dispose()
    print("[seed] done")


if __name__ == "__main__":
    asyncio.run(main())