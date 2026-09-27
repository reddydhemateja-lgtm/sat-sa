"""
Seed demo entities for the live deployment.

This script is idempotent — running it repeatedly creates nothing new.

Only entities are seeded here. Alerts, cases, investigations, escalations,
and findings are expected to arrive via the ingestion page.

Usage:
    python -m app.seed_demo
"""

import asyncio

from sqlalchemy import select

from app.database import SessionLocal
from app.models.cse import CSEEntity


DEMO_ENTITIES = [
    dict(
        code="BANK-A",
        name="National Banking Entity A",
        sector="Banking",
        sub_sector="Retail Banking",
        region="North",
        criticality="HIGH",
        peer_group="Banking-Large",
    ),
    dict(
        code="POWER-B",
        name="Regional Power Grid Operator B",
        sector="Power",
        sub_sector="Transmission",
        region="West",
        criticality="CRITICAL",
        peer_group="Power-Transmission",
    ),
    dict(
        code="TELEC-C",
        name="Telecom Service Provider C",
        sector="Telecom",
        sub_sector="Mobile Network",
        region="South",
        criticality="HIGH",
        peer_group="Telecom-National",
    ),
    dict(
        code="BANK-X",
        name="Commercial Bank X",
        sector="Banking",
        sub_sector="Retail",
        region="East",
        criticality="HIGH",
        peer_group="Banking-Large",
    ),
    dict(
        code="BANK-Y",
        name="Cooperative Bank Y",
        sector="Banking",
        sub_sector="Retail",
        region="South",
        criticality="HIGH",
        peer_group="Banking-Large",
    ),
    dict(
        code="GRID-M",
        name="Metro Grid Operator M",
        sector="Power",
        sub_sector="Distribution",
        region="North",
        criticality="CRITICAL",
        peer_group="Power-Transmission",
    ),
    dict(
        code="GRID-N",
        name="Northern Grid Operator N",
        sector="Power",
        sub_sector="Transmission",
        region="North",
        criticality="CRITICAL",
        peer_group="Power-Transmission",
    ),
    dict(
        code="TELEC-P",
        name="Telecom Provider P",
        sector="Telecom",
        sub_sector="Fixed Line",
        region="West",
        criticality="HIGH",
        peer_group="Telecom-National",
    ),
    dict(
        code="TELEC-Q",
        name="Telecom Provider Q",
        sector="Telecom",
        sub_sector="Mobile",
        region="East",
        criticality="HIGH",
        peer_group="Telecom-National",
    ),
]


async def main() -> None:
    async with SessionLocal() as db:
        existing = {
            code for (code,) in (await db.execute(select(CSEEntity.code))).all()
        }
        print(f"[seed_demo] existing entities: {sorted(existing)}")

        created = 0
        for e in DEMO_ENTITIES:
            if e["code"] in existing:
                continue
            db.add(CSEEntity(is_active=True, **e))
            created += 1

        if created:
            await db.commit()
            print(f"[seed_demo] created {created} entities")
        else:
            print("[seed_demo] nothing to create (all present)")

        final = (await db.execute(select(CSEEntity))).scalars().all()
        print(f"[seed_demo] entities now: {[(e.id, e.code) for e in final]}")


if __name__ == "__main__":
    asyncio.run(main())