"""
API connector endpoints.

Demonstrates the API ingestion path end-to-end using a clearly-labelled
DEMO/INTERNAL connector. There is no real CSE or government endpoint — the
"fetch" action reads a bundled synthetic JSON payload and feeds it through
the same validate + commit pipeline used by uploaded files.

Flow demonstrated:
    Demo SOC API  ->  fetch (this router)  ->  read_api_json (adapter)
                  ->  pipeline.validate()  ->  commit_payload()
                  ->  run_analytics_for_period()

The primary, fully-real ingestion modes remain CSV, JSON, and DB exports.
This router exists to prove API ingestion is architecturally supported.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.orchestrator import run_analytics_for_period
from app.audit import record_audit
from app.database import get_db
from app.deps import get_current_user, require_roles
from app.ingestion.adapters.api_adapter import read_api_json
from app.ingestion.commit import _hash_file, commit_payload
from app.ingestion.pipeline import validate
from app.models.connectors import APIConnector
from app.models.cse import CSEEntity
from app.models.ingestion import DataSubmission
from app.models.period import AssessmentPeriod
from app.models.user import RoleEnum, User
from app.routers.ingestion import _next_dataset_version

router = APIRouter(prefix="/connectors", tags=["connectors"])


# Where the bundled demo payload lives, relative to backend/.
_DEMO_PAYLOAD_PATH = (
    Path(__file__).resolve().parents[3]
    / "data"
    / "sample"
    / "api_demo"
    / "alerts_api_batch.json"
)

DEMO_CONNECTOR_NAME = "Demo/Internal SOC API"


async def _ensure_demo_connector(db: AsyncSession) -> APIConnector:
    """Create the demo connector row on first access, return it either way."""
    existing = (
        await db.execute(
            select(APIConnector).where(APIConnector.name == DEMO_CONNECTOR_NAME)
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    connector = APIConnector(
        name=DEMO_CONNECTOR_NAME,
        connector_type="DEMO_SOC_API",
        base_url=None,
        mode="PERIODIC_PULL",
        is_demo=True,
        status="CONFIGURED",
        payload_types="alerts,cases",
        notes=(
            "Bundled synthetic payload. Demonstrates API ingestion end-to-end. "
            "Not connected to any real CSE or government system."
        ),
    )
    db.add(connector)
    await db.flush()
    await db.commit()
    await db.refresh(connector)
    return connector


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------
@router.get(
    "",
    dependencies=[Depends(require_roles(RoleEnum.ADMIN, RoleEnum.ANALYST, RoleEnum.SUPERVISOR))],
)
async def list_connectors(db: AsyncSession = Depends(get_db)) -> dict:
    await _ensure_demo_connector(db)

    rows = (
        await db.execute(select(APIConnector).order_by(APIConnector.id))
    ).scalars().all()

    return {
        "items": [
            {
                "id": c.id,
                "name": c.name,
                "connector_type": c.connector_type,
                "base_url": c.base_url,
                "mode": c.mode,
                "is_demo": bool(c.is_demo),
                "status": c.status,
                "payload_types": (c.payload_types or "").split(",")
                if c.payload_types
                else [],
                "last_run_at": c.last_run_at,
                "last_run_summary": c.last_run_summary,
                "notes": c.notes,
            }
            for c in rows
        ],
        "available_types": [
            {
                "type": "DEMO_SOC_API",
                "label": "Demo/Internal SOC API",
                "description": "Bundled synthetic SOC payload, demo only.",
            },
            {
                "type": "INTERNAL_REST",
                "label": "Internal REST API",
                "description": "For CSEs that expose an internal periodic export API.",
            },
            {
                "type": "DB_ADAPTER",
                "label": "Database/API Adapter",
                "description": "Adapter layer over a database export endpoint.",
            },
        ],
    }


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------
@router.post(
    "/{connector_id}/test",
    dependencies=[Depends(require_roles(RoleEnum.ADMIN, RoleEnum.ANALYST))],
)
async def test_connector(
    connector_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    connector = (
        await db.execute(select(APIConnector).where(APIConnector.id == connector_id))
    ).scalar_one_or_none()
    if connector is None:
        raise HTTPException(status_code=404, detail="Connector not found")

    reachable = _DEMO_PAYLOAD_PATH.exists()
    connector.status = "TESTED" if reachable else "ERROR"
    await db.commit()

    return {
        "connector_id": connector.id,
        "name": connector.name,
        "is_demo": bool(connector.is_demo),
        "reachable": reachable,
        "mode": connector.mode,
        "payload_path": str(_DEMO_PAYLOAD_PATH),
        "message": (
            "Demo payload is available locally."
            if reachable
            else "Demo payload file is missing."
        ),
    }


# ---------------------------------------------------------------------------
# Fetch (demo) — feeds the real ingestion + analytics pipeline
# ---------------------------------------------------------------------------
@router.post(
    "/{connector_id}/fetch",
    dependencies=[Depends(require_roles(RoleEnum.ADMIN, RoleEnum.ANALYST))],
)
async def fetch_from_connector(
    connector_id: int,
    entity_id: int,
    period_id: int,
    payload_type: str = "alerts",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    connector = (
        await db.execute(select(APIConnector).where(APIConnector.id == connector_id))
    ).scalar_one_or_none()
    if connector is None:
        raise HTTPException(status_code=404, detail="Connector not found")
    if not connector.is_demo:
        raise HTTPException(
            status_code=400,
            detail="Only demo connectors are supported in this prototype.",
        )

    if not _DEMO_PAYLOAD_PATH.exists():
        raise HTTPException(
            status_code=500,
            detail=f"Demo payload not found at {_DEMO_PAYLOAD_PATH}",
        )

    entity = (
        await db.execute(select(CSEEntity).where(CSEEntity.id == entity_id))
    ).scalar_one_or_none()
    if entity is None:
        raise HTTPException(status_code=404, detail="Entity not found")

    period = (
        await db.execute(
            select(AssessmentPeriod).where(AssessmentPeriod.id == period_id)
        )
    ).scalar_one_or_none()
    if period is None:
        raise HTTPException(status_code=404, detail="Period not found")

    blob = _DEMO_PAYLOAD_PATH.read_bytes()

    try:
        df = read_api_json(blob)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    known_codes = set(
        (await db.execute(select(CSEEntity.code))).scalars().all()
    )

    clean_df, summary = validate(df, payload_type, known_entity_codes=known_codes)

    if clean_df.empty:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "No valid rows in demo payload.",
                "summary": summary.to_dict(),
            },
        )

    resolved_filename = f"{connector.name.replace('/', '_')}.json"
    version = await _next_dataset_version(
        db, entity_id=entity_id, period_id=period_id, file_name=resolved_filename
    )

    submission = DataSubmission(
        entity_id=entity_id,
        period_id=period_id,
        submitted_by=f"connector:{connector.name}",
        file_name=resolved_filename,
        file_hash=_hash_file(blob),
        file_size=len(blob),
        format="json",
        payload_type=payload_type,
        version=version,
        status="PROCESSING",
        records_received=summary.records_received,
        records_valid=0,
        records_warning=summary.records_warning,
        records_error=summary.records_error,
        validation_report=summary.to_dict(),
    )
    db.add(submission)
    await db.flush()

    try:
        inserted, skipped = await commit_payload(
            db,
            payload_type=payload_type,
            clean_df=clean_df,
            entity_id=entity_id,
            period_id=period_id,
            submission=submission,
            submitted_by=current_user.username,
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Commit failed: {e}")

    submission.status = "COMMITTED"
    submission.records_valid = inserted

    await record_audit(
        db,
        user_id=current_user.id,
        action="CONNECTOR_FETCH",
        target_type="data_submission",
        target_id=submission.id,
        new_value={
            "connector_id": connector.id,
            "connector_name": connector.name,
            "is_demo": True,
            "entity_id": entity_id,
            "period_id": period_id,
            "payload_type": payload_type,
            "version": version,
            "records_received": summary.records_received,
            "records_inserted": inserted,
            "records_skipped": skipped,
        },
    )

    connector.last_run_at = datetime.utcnow().isoformat(timespec="seconds")
    connector.last_run_summary = {
        "submission_id": submission.id,
        "version": version,
        "records_received": summary.records_received,
        "records_inserted": inserted,
        "records_skipped": skipped,
        "payload_type": payload_type,
        "entity_code": entity.code,
        "period_label": period.label,
    }

    await db.commit()
    await db.refresh(submission)

    analytics_summary: dict | None = None
    try:
        analytics_summary = await run_analytics_for_period(
            db, period_id=period_id, actor_user_id=current_user.id
        )
    except Exception as e:
        analytics_summary = {"error": str(e)}

    return {
        "connector": {
            "id": connector.id,
            "name": connector.name,
            "is_demo": True,
        },
        "submission_id": submission.id,
        "version": version,
        "records_received": summary.records_received,
        "records_inserted": inserted,
        "records_skipped": skipped,
        "warnings": summary.records_warning,
        "errors": summary.records_error,
        "validation_summary": summary.to_dict(),
        "analytics": analytics_summary,
    }