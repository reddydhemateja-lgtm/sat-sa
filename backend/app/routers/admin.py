"""
Admin endpoints used by the Data page and Settings page.

    DELETE /admin/datasets/{submission_id}        — remove a submission and its records
    POST   /admin/datasets/reset                  — delete all operational records
    POST   /admin/seed-synthetic                  — ingest the bundled synthetic CSVs
    POST   /admin/datasets/{id}/preference        — set included/deleted flags
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import record_audit
from app.database import get_db
from app.deps import get_current_user, require_roles
from app.models.cse import CSEEntity
from app.models.ingestion import DataSubmission
from app.models.operational import (
    Alert,
    AlertDisposition,
    Case,
    Escalation,
    Investigation,
)
from app.models.period import AssessmentPeriod
from app.models.preferences import DatasetPreference
from app.models.user import RoleEnum, User

router = APIRouter(prefix="/admin", tags=["admin"])


# ---------------------------------------------------------------------------
# Delete one submission
# ---------------------------------------------------------------------------
@router.delete(
    "/datasets/{submission_id}",
    dependencies=[Depends(require_roles(RoleEnum.ADMIN))],
)
async def delete_submission(
    submission_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    sub = (
        await db.execute(
            select(DataSubmission).where(DataSubmission.id == submission_id)
        )
    ).scalar_one_or_none()
    if sub is None:
        raise HTTPException(status_code=404, detail="Submission not found")

    entity_id = sub.entity_id
    period_id = sub.period_id

    sub_alert_ids = [
        aid
        for (aid,) in (
            await db.execute(
                select(Alert.id).where(Alert.submission_id == submission_id)
            )
        ).all()
    ]
    if sub_alert_ids:
        await db.execute(
            delete(AlertDisposition).where(
                AlertDisposition.alert_id.in_(sub_alert_ids)
            )
        )
        sub_case_ids = [
            cid
            for (cid,) in (
                await db.execute(
                    select(Case.id).where(Case.alert_id.in_(sub_alert_ids))
                )
            ).all()
        ]
        if sub_case_ids:
            await db.execute(
                delete(Escalation).where(Escalation.case_id.in_(sub_case_ids))
            )
            await db.execute(
                delete(Investigation).where(Investigation.case_id.in_(sub_case_ids))
            )
            await db.execute(delete(Case).where(Case.id.in_(sub_case_ids)))
        await db.execute(delete(Alert).where(Alert.id.in_(sub_alert_ids)))

    if sub.payload_type == "investigations":
        await db.execute(
            delete(Investigation).where(Investigation.entity_id == entity_id)
        )
    if sub.payload_type == "escalations":
        await db.execute(
            delete(Escalation).where(Escalation.entity_id == entity_id)
        )

    await db.execute(
        delete(DataSubmission).where(DataSubmission.id == submission_id)
    )

    await record_audit(
        db,
        user_id=current_user.id,
        action="DATASET_DELETE",
        target_type="data_submission",
        target_id=submission_id,
        previous_value={
            "file_name": sub.file_name,
            "payload_type": sub.payload_type,
            "entity_id": entity_id,
            "period_id": period_id,
        },
    )

    await db.commit()
    return {"status": "deleted", "submission_id": submission_id}


# ---------------------------------------------------------------------------
# Reset all operational data
# ---------------------------------------------------------------------------
@router.post(
    "/datasets/reset",
    dependencies=[Depends(require_roles(RoleEnum.ADMIN))],
)
async def reset_all_operational(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    counts: dict[str, int] = {}
    for model, name in [
        (AlertDisposition, "alert_dispositions"),
        (Escalation, "escalations"),
        (Investigation, "investigations"),
        (Case, "cases"),
        (Alert, "alerts"),
        (DataSubmission, "data_submissions"),
    ]:
        result = await db.execute(delete(model))
        counts[name] = result.rowcount

    await record_audit(
        db,
        user_id=current_user.id,
        action="DATASET_RESET",
        target_type="global",
        new_value=counts,
    )
    await db.commit()
    return {"status": "reset", "deleted": counts}


# ---------------------------------------------------------------------------
# Seed synthetic data from bundled CSVs
# ---------------------------------------------------------------------------
@router.post(
    "/seed-synthetic",
    dependencies=[Depends(require_roles(RoleEnum.ADMIN))],
)
async def seed_synthetic(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    from app.ingestion.batch import COMMIT_ORDER
    from app.ingestion.commit import commit_payload
    from app.ingestion.pipeline import read_file, validate

    # Path: backend/app/routers/admin.py → go up 4 levels → project root
    BASE = Path(__file__).resolve().parent.parent.parent.parent

    DATA_DIR = BASE / "data" / "sample" / "full"
    if not DATA_DIR.exists():
        DATA_DIR = BASE / "data" / "sample"

    if not DATA_DIR.exists():
        raise HTTPException(
            status_code=400,
            detail=f"Synthetic data folder not found at {DATA_DIR}",
        )

    period = (
        await db.execute(
            select(AssessmentPeriod).where(AssessmentPeriod.is_active == True)  # noqa: E712
        )
    ).scalar_one_or_none()
    if period is None:
        raise HTTPException(status_code=400, detail="No active assessment period")

    entities = (await db.execute(select(CSEEntity))).scalars().all()
    entity_by_code = {e.code: e for e in entities}

    PAYLOAD_KEYS = [
        "investigations",
        "dispositions",
        "escalations",
        "entities",
        "assets",
        "alerts",
        "cases",
    ]

    def infer_payload(name: str) -> str | None:
        lower = name.lower()
        for p in PAYLOAD_KEYS:
            key = p[:-1] if p.endswith("s") else p
            if key in lower or p in lower:
                return p
        return None

    files_by_entity: dict[str, list[tuple[str, bytes, str]]] = {}
    for path in sorted(DATA_DIR.glob("*.csv")):
        name = path.name
        if name in ("entities.csv", "assets.csv"):
            continue
        parts = name.rsplit("_", 1)
        if len(parts) != 2:
            continue
        code = parts[1].replace(".csv", "")
        if code not in entity_by_code:
            continue
        payload = infer_payload(name)
        if not payload:
            continue
        files_by_entity.setdefault(code, []).append(
            (name, path.read_bytes(), payload)
        )

    if not files_by_entity:
        raise HTTPException(
            status_code=400,
            detail=f"No usable CSVs found in {DATA_DIR}",
        )

    total_inserted = 0
    per_entity: dict[str, int] = {}

    for code in sorted(files_by_entity.keys()):
        entity = entity_by_code[code]
        clean_by_type: dict[str, pd.DataFrame] = {}
        for filename, blob, payload in files_by_entity[code]:
            try:
                df = read_file(blob, "csv")
                clean_df, _ = validate(df, payload, known_entity_codes={code})
                if clean_df.empty:
                    continue
                if payload in clean_by_type:
                    clean_by_type[payload] = pd.concat(
                        [clean_by_type[payload], clean_df], ignore_index=True
                    )
                else:
                    clean_by_type[payload] = clean_df
            except Exception:
                continue

        if not clean_by_type:
            continue

        per_file_subs: list[DataSubmission] = []
        for filename, blob, payload in files_by_entity[code]:
            if payload not in clean_by_type:
                continue
            sub = DataSubmission(
                entity_id=entity.id,
                period_id=period.id,
                submitted_by=current_user.username,
                file_name=filename,
                file_hash="",
                file_size=len(blob),
                format="csv",
                payload_type=payload,
                status="PROCESSING",
                records_received=len(clean_by_type[payload]),
                records_valid=0,
                records_warning=0,
                records_error=0,
                validation_report=None,
            )
            db.add(sub)
            await db.flush()
            per_file_subs.append(sub)

        if not per_file_subs:
            continue

        parent = per_file_subs[0]
        for payload_type in COMMIT_ORDER:
            df = clean_by_type.get(payload_type)
            if df is None or df.empty:
                continue
            try:
                n_ins, _ = await commit_payload(
                    db,
                    payload_type=payload_type,
                    clean_df=df,
                    entity_id=entity.id,
                    period_id=period.id,
                    submission=parent,
                    submitted_by=current_user.username,
                )
                total_inserted += n_ins
                per_entity[code] = per_entity.get(code, 0) + n_ins
            except Exception:
                continue

        for sub in per_file_subs:
            sub.status = "COMMITTED"
        await db.flush()

    analytics_summary: dict | None = None
    try:
        from app.analytics.orchestrator import run_analytics_for_period

        analytics_summary = await run_analytics_for_period(
            db, period_id=period.id, actor_user_id=current_user.id
        )
    except Exception as e:
        analytics_summary = {"error": str(e)}

    await record_audit(
        db,
        user_id=current_user.id,
        action="SYNTHETIC_SEED",
        target_type="global",
        new_value={
            "inserted": total_inserted,
            "by_entity": per_entity,
            "source_dir": str(DATA_DIR),
        },
    )
    await db.commit()

    return {
        "status": "seeded",
        "inserted": total_inserted,
        "by_entity": per_entity,
        "analytics": analytics_summary,
    }


# ---------------------------------------------------------------------------
# Dataset preference endpoints
# ---------------------------------------------------------------------------
class PreferenceUpdate(BaseModel):
    included: bool | None = None
    deleted: bool | None = None


@router.post(
    "/datasets/{submission_id}/preference",
    dependencies=[Depends(require_roles(RoleEnum.ADMIN))],
)
async def update_preference(
    submission_id: int,
    payload: PreferenceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    sub = (
        await db.execute(
            select(DataSubmission).where(DataSubmission.id == submission_id)
        )
    ).scalar_one_or_none()
    if sub is None:
        raise HTTPException(status_code=404, detail="Submission not found")

    pref = (
        await db.execute(
            select(DatasetPreference).where(
                DatasetPreference.submission_id == submission_id
            )
        )
    ).scalar_one_or_none()

    if pref is None:
        pref = DatasetPreference(
            submission_id=submission_id,
            included=True,
            deleted=False,
        )
        db.add(pref)
        await db.flush()

    previous = {"included": pref.included, "deleted": pref.deleted}

    if payload.included is not None:
        pref.included = payload.included
    if payload.deleted is not None:
        pref.deleted = payload.deleted

    await record_audit(
        db,
        user_id=current_user.id,
        action="DATASET_PREFERENCE",
        target_type="data_submission",
        target_id=submission_id,
        previous_value=previous,
        new_value={"included": pref.included, "deleted": pref.deleted},
    )

    await db.commit()
    return {
        "submission_id": submission_id,
        "included": pref.included,
        "deleted": pref.deleted,
    }