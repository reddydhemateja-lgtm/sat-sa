 
"""Full reset: delete all ingested operational data and submissions."""
import asyncio

from sqlalchemy import delete, func, select

from app.database import SessionLocal
from app.models.ingestion import DataSubmission
from app.models.operational import (
    Alert, AlertDisposition, Case, Escalation, Investigation,
)


async def main() -> None:
    async with SessionLocal() as db:
        for model, name in [
            (AlertDisposition, "alert_dispositions"),
            (Escalation, "escalations"),
            (Investigation, "investigations"),
            (Case, "cases"),
            (Alert, "alerts"),
            (DataSubmission, "data_submissions"),
        ]:
            r = await db.execute(delete(model))
            print(f"deleted {name:20s}: {r.rowcount}")
        await db.commit()

        for model, name in [
            (Alert, "alerts"),
            (Case, "cases"),
            (Investigation, "investigations"),
            (Escalation, "escalations"),
        ]:
            r = await db.execute(select(func.count(model.id)))
            print(f"remaining {name:20s}: {r.scalar_one()}")


if __name__ == "__main__":
    asyncio.run(main())