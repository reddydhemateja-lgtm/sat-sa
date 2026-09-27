"""
Boot-time demo data seeder.

Reads every CSV in data/sample/full/ and ingests them into the database,
then runs the analytics pipeline. Idempotent — running twice changes
nothing because duplicate rows are skipped.

Called from the Render start command after app.seed and app.seed_demo.

Usage:
    python -m app.seed_data
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from sqlalchemy import select

from app.analytics.orchestrator import run_analytics_for_period
from app.database import SessionLocal
from app.ingestion.batch import COMMIT_ORDER
from app.ingestion.column_mapping import suggest_mapping
from app.ingestion.commit import commit_payload
from app.ingestion.pipeline import read_file, validate
from app.models.cse import CSEEntity
from app.models.ingestion import DataSubmission
from app.models.period import AssessmentPeriod


# Path is relative to backend/ — CSVs live two levels up
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "sample" / "full"


PAYLOAD_TYPE_BY_PREFIX = {
    "alerts": "alerts",
    "cases": "cases",
    "investigations": "investigations",
    "escalations": "escalations",
    "dispositions": "dispositions",
    "assets": "assets",
    "entities": "entities",
}


def infer_payload_type(filename: str) -> str | None:
    """alerts_BANK-A.csv → alerts"""
    base = filename.split("_", 1)[0].replace(".csv", "").lower()
    return PAYLOAD_TYPE_BY_PREFIX.get(base)


async def main() -> None:
    if not DATA_DIR.exists():
        print(f"[seed_data] demo folder not found: {DATA_DIR} — skipping")
        return

    print(f"[seed_data] reading from: {DATA_DIR}")

    async with SessionLocal() as db:
        # Get entity id map
        entities = (await db.execute(select(CSEEntity))).scalars().all()
        entity_by_code = {e.code: e for e in entities}
        print(f"[seed_data] {len(entities)} entities available")

        # Get current period
        period = (
            await db.execute(
                select(AssessmentPeriod).where(AssessmentPeriod.is_active == True)  # noqa: E712
            )
        ).scalar_one_or_none()
        if period is None:
            print("[seed_data] no active period — run app.seed first")
            return
        print(f"[seed_data] active period: {period.id} ({period.label})")

        # Collect files grouped by entity code
        files_by_entity: dict[str, list[tuple[str, bytes, str]]] = {}
        for csv_path in sorted(DATA_DIR.glob("*.csv")):
            name = csv_path.name
            if name in ("entities.csv", "assets.csv"):
                continue  # skip global files
            parts = name.rsplit("_", 1)
            if len(parts) != 2:
                continue
            code = parts[1].replace(".csv", "")
            payload = infer_payload_type(name)
            if not payload:
                continue
            if code not in entity_by_code:
                continue
            files_by_entity.setdefault(code, []).append(
                (name, csv_path.read_bytes(), payload)
            )

        print(f"[seed_data] {sum(len(v) for v in files_by_entity.values())} files across {len(files_by_entity)} entities")

        # Ingest per entity
        total_inserted = 0
        for code in sorted(files_by_entity.keys()):
            entity = entity_by_code[code]
            files = files_by_entity[code]

            # Build clean dataframes per payload type
            clean_by_type: dict = {}
            for filename, blob, payload in files:
                try:
                    df = read_file(blob, "csv")
                    clean_df, summary = validate(df, payload, known_entity_codes={code})
                    if not clean_df.empty:
                        if payload in clean_by_type:
                            import pandas as pd
                            clean_by_type[payload] = pd.concat(
                                [clean_by_type[payload], clean_df], ignore_index=True
                            )
                        else:
                            clean_by_type[payload] = clean_df
                except Exception as e:
                    print(f"[seed_data]   {filename} validate failed: {e}")
                    continue

            if not clean_by_type:
                print(f"[seed_data] {code}: no valid rows to commit")
                continue

            # Create a submission record
            submission = DataSubmission(
                entity_id=entity.id,
                period_id=period.id,
                submitted_by="seed_data",
                file_name=f"BOOT:{code}:{len(files)} files",
                file_hash="",
                file_size=sum(len(b) for _, b, _ in files),
                format="batch",
                payload_type="batch",
                status="PROCESSING",
                records_received=sum(len(df) for df in clean_by_type.values()),
                records_valid=0,
                records_warning=0,
                records_error=0,
                validation_report=None,
            )
            db.add(submission)
            await db.flush()

            inserted = 0
            skipped = 0
            for payload_type in COMMIT_ORDER:
                df = clean_by_type.get(payload_type)
                if df is None or df.empty:
                    continue
                try:
                    n_ins, n_skip = await commit_payload(
                        db,
                        payload_type=payload_type,
                        clean_df=df,
                        entity_id=entity.id,
                        period_id=period.id,
                        submission=submission,
                        submitted_by="seed_data",
                    )
                    inserted += n_ins
                    skipped += n_skip
                except Exception as e:
                    print(f"[seed_data]   {code} {payload_type} commit failed: {e}")
                    continue

            submission.records_valid = inserted
            submission.status = "COMMITTED"
            await db.flush()

            total_inserted += inserted
            print(f"[seed_data] {code}: inserted={inserted} skipped={skipped}")

        await db.commit()
        print(f"[seed_data] total inserted: {total_inserted}")

    # ---- Run analytics ----
    async with SessionLocal() as db:
        period = (
            await db.execute(
                select(AssessmentPeriod).where(AssessmentPeriod.is_active == True)  # noqa: E712
            )
        ).scalar_one_or_none()
        if period is None:
            return

        try:
            summary = await run_analytics_for_period(
                db, period_id=period.id, actor_user_id=None
            )
            print(f"[seed_data] analytics created {summary.get('total_created', 0)} findings")
        except Exception as e:
            print(f"[seed_data] analytics failed: {e}")

    print("[seed_data] done")


if __name__ == "__main__":
    asyncio.run(main())