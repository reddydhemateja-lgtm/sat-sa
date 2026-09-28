"""
Dataset endpoints.

Exposes uploaded submission files and their stored records so a supervisor
can inspect exactly what a CSE submitted.

Also provides a fallback: if no DataSubmission rows exist but the operational
tables (alerts, cases, investigations, escalations) have data, synthesise
one dataset row per entity + payload type so the Data page always reflects
what's in the database.

View modes:
    complete  — everything (default)
    modified  — only datasets with preference.included=True and
                preference.deleted=False
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import require_roles
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
from app.models.user import RoleEnum

router = APIRouter(prefix="/datasets", tags=["datasets"])


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if isinstance(dt, datetime) else dt


PAYLOAD_TO_MODEL = {
    "alerts": Alert,
    "cases": Case,
    "investigations": Investigation,
    "escalations": Escalation,
    "dispositions": AlertDisposition,
}


# ---------------------------------------------------------------------------
# List all datasets
# ---------------------------------------------------------------------------
@router.get(
    "",
    dependencies=[
        Depends(require_roles(RoleEnum.ADMIN, RoleEnum.ANALYST, RoleEnum.SUPERVISOR))
    ],
)
async def list_datasets(
    entity_id: int | None = None,
    period_id: int | None = None,
    mode: str = Query("complete", pattern="^(complete|modified)$"),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> dict:
    entity_map = {
        eid: {"code": code, "name": name, "sector": sector}
        for (eid, code, name, sector) in (
            await db.execute(
                select(CSEEntity.id, CSEEntity.code, CSEEntity.name, CSEEntity.sector)
            )
        ).all()
    }
    period_map = {
        pid: label
        for (pid, label) in (
            await db.execute(select(AssessmentPeriod.id, AssessmentPeriod.label))
        ).all()
    }

    # ---- Real submissions ----
    stmt = select(DataSubmission).order_by(DataSubmission.created_at.desc())
    if entity_id is not None:
        stmt = stmt.where(DataSubmission.entity_id == entity_id)
    if period_id is not None:
        stmt = stmt.where(DataSubmission.period_id == period_id)

    total = (
        await db.execute(select(func.count()).select_from(stmt.subquery()))
    ).scalar_one()
    rows = (await db.execute(stmt)).scalars().all()

    pref_map: dict[int, DatasetPreference] = {}
    if rows:
        pref_rows = (
            await db.execute(
                select(DatasetPreference).where(
                    DatasetPreference.submission_id.in_([r.id for r in rows])
                )
            )
        ).scalars().all()
        pref_map = {p.submission_id: p for p in pref_rows}

    items: list[dict] = []
    for r in rows:
        pref = pref_map.get(r.id)
        items.append(
            {
                "id": r.id,
                "entity_id": r.entity_id,
                "entity_code": entity_map.get(r.entity_id, {}).get("code"),
                "entity_name": entity_map.get(r.entity_id, {}).get("name"),
                "period_id": r.period_id,
                "period_label": period_map.get(r.period_id),
                "file_name": r.file_name,
                "format": r.format,
                "payload_type": r.payload_type,
                "file_size": r.file_size,
                "file_hash": r.file_hash,
                "status": r.status,
                "submitted_by": r.submitted_by,
                "records_received": r.records_received,
                "records_valid": r.records_valid,
                "records_warning": r.records_warning,
                "records_error": r.records_error,
                "created_at": _iso(r.created_at),
                "synthetic": False,
                "included": pref.included if pref else True,
                "deleted": pref.deleted if pref else False,
            }
        )

    # ---- Fallback: synthesise from raw records ----
    if not items:
        synthesised = await _synthesise_datasets_from_records(
            db, entity_id=entity_id, period_id=period_id
        )
        items = synthesised

    # ---- Apply view mode ----
    if mode == "modified":
        items = [i for i in items if i.get("included") and not i.get("deleted")]

    total = len(items)
    items = items[offset : offset + limit]

    return {
        "total": int(total),
        "limit": limit,
        "offset": offset,
        "mode": mode,
        "items": items,
    }


async def _synthesise_datasets_from_records(
    db: AsyncSession,
    *,
    entity_id: int | None = None,
    period_id: int | None = None,
) -> list[dict]:
    entities = (
        await db.execute(select(CSEEntity).order_by(CSEEntity.id))
    ).scalars().all()
    if entity_id is not None:
        entities = [e for e in entities if e.id == entity_id]

    periods = (
        await db.execute(select(AssessmentPeriod).order_by(AssessmentPeriod.id))
    ).scalars().all()
    if period_id is not None:
        periods = [p for p in periods if p.id == period_id]

    out: list[dict] = []

    for entity in entities:
        for payload_type, model in PAYLOAD_TO_MODEL.items():
            count = (
                await db.execute(
                    select(func.count(model.id)).where(model.entity_id == entity.id)
                )
            ).scalar_one()
            if count == 0:
                continue

            entity_period_id: int | None = None
            if hasattr(model, "period_id"):
                period_rows = (
                    await db.execute(
                        select(model.period_id, func.count(model.id))
                        .where(model.entity_id == entity.id)
                        .group_by(model.period_id)
                        .order_by(func.count(model.id).desc())
                    )
                ).all()
                if period_rows:
                    entity_period_id = period_rows[0][0]

            if entity_period_id is None and periods:
                entity_period_id = periods[0].id

            period_label = None
            for p in periods:
                if p.id == entity_period_id:
                    period_label = p.label
                    break

            out.append(
                {
                    "id": f"raw-{entity.id}-{payload_type}",
                    "entity_id": entity.id,
                    "entity_code": entity.code,
                    "entity_name": entity.name,
                    "period_id": entity_period_id,
                    "period_label": period_label,
                    "file_name": f"{payload_type}_{entity.code}.csv",
                    "format": "csv",
                    "payload_type": payload_type,
                    "file_size": 0,
                    "file_hash": "",
                    "status": "COMMITTED",
                    "submitted_by": "seed_data",
                    "records_received": int(count),
                    "records_valid": int(count),
                    "records_warning": 0,
                    "records_error": 0,
                    "created_at": entity.created_at.isoformat()
                    if isinstance(entity.created_at, datetime)
                    else entity.created_at,
                    "synthetic": True,
                    "included": True,
                    "deleted": False,
                }
            )

    return out


# ---------------------------------------------------------------------------
# Single submission metadata
# ---------------------------------------------------------------------------
@router.get(
    "/{submission_id}",
    dependencies=[
        Depends(require_roles(RoleEnum.ADMIN, RoleEnum.ANALYST, RoleEnum.SUPERVISOR))
    ],
)
async def get_dataset(
    submission_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    if submission_id.startswith("raw-"):
        return await _synthetic_dataset_detail(db, submission_id)

    try:
        sid_int = int(submission_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid submission id")

    sub = (
        await db.execute(select(DataSubmission).where(DataSubmission.id == sid_int))
    ).scalar_one_or_none()
    if sub is None:
        raise HTTPException(status_code=404, detail="Submission not found")

    entity = (
        await db.execute(select(CSEEntity).where(CSEEntity.id == sub.entity_id))
    ).scalar_one_or_none()
    period = (
        await db.execute(
            select(AssessmentPeriod).where(AssessmentPeriod.id == sub.period_id)
        )
    ).scalar_one_or_none()

    return {
        "id": str(sub.id),
        "entity": (
            {
                "id": entity.id,
                "code": entity.code,
                "name": entity.name,
                "sector": entity.sector,
                "criticality": entity.criticality,
            }
            if entity
            else None
        ),
        "period": (
            {"id": period.id, "label": period.label} if period else None
        ),
        "file_name": sub.file_name,
        "format": sub.format,
        "payload_type": sub.payload_type,
        "file_size": sub.file_size,
        "file_hash": sub.file_hash,
        "status": sub.status,
        "submitted_by": sub.submitted_by,
        "records_received": sub.records_received,
        "records_valid": sub.records_valid,
        "records_warning": sub.records_warning,
        "records_error": sub.records_error,
        "validation_report": sub.validation_report,
        "created_at": _iso(sub.created_at),
        "synthetic": False,
    }


async def _synthetic_dataset_detail(db: AsyncSession, sid: str) -> dict:
    parts = sid.split("-", 2)
    if len(parts) != 3:
        raise HTTPException(status_code=400, detail="Invalid synthetic id")
    try:
        entity_id = int(parts[1])
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid entity id")
    payload_type = parts[2]

    if payload_type not in PAYLOAD_TO_MODEL:
        raise HTTPException(status_code=404, detail="Unknown payload type")

    entity = (
        await db.execute(select(CSEEntity).where(CSEEntity.id == entity_id))
    ).scalar_one_or_none()
    if entity is None:
        raise HTTPException(status_code=404, detail="Entity not found")

    model = PAYLOAD_TO_MODEL[payload_type]
    count = (
        await db.execute(
            select(func.count(model.id)).where(model.entity_id == entity_id)
        )
    ).scalar_one()

    period = (
        await db.execute(
            select(AssessmentPeriod).order_by(AssessmentPeriod.id).limit(1)
        )
    ).scalar_one_or_none()

    return {
        "id": sid,
        "entity": {
            "id": entity.id,
            "code": entity.code,
            "name": entity.name,
            "sector": entity.sector,
            "criticality": entity.criticality,
        },
        "period": (
            {"id": period.id, "label": period.label} if period else None
        ),
        "file_name": f"{payload_type}_{entity.code}.csv",
        "format": "csv",
        "payload_type": payload_type,
        "file_size": 0,
        "file_hash": "",
        "status": "COMMITTED",
        "submitted_by": "seed_data",
        "records_received": int(count),
        "records_valid": int(count),
        "records_warning": 0,
        "records_error": 0,
        "validation_report": None,
        "created_at": entity.created_at.isoformat()
        if isinstance(entity.created_at, datetime)
        else entity.created_at,
        "synthetic": True,
    }


# ---------------------------------------------------------------------------
# Serializers
# ---------------------------------------------------------------------------
def _serialize_alert(a: Alert) -> dict[str, Any]:
    return {
        "id": a.id,
        "external_id": a.external_id,
        "title": a.title,
        "severity": a.severity.value,
        "category": a.category,
        "status": a.status.value,
        "source_system": a.source_system,
        "detected_at": _iso(a.detected_at),
        "acknowledged_at": _iso(a.acknowledged_at),
        "closed_at": _iso(a.closed_at),
    }


def _serialize_case(c: Case) -> dict[str, Any]:
    return {
        "id": c.id,
        "external_id": c.external_id,
        "title": c.title,
        "severity": c.severity.value,
        "status": c.status,
        "opened_at": _iso(c.opened_at),
        "closed_at": _iso(c.closed_at),
        "assigned_to": c.assigned_to,
    }


def _serialize_investigation(i: Investigation) -> dict[str, Any]:
    return {
        "id": i.id,
        "case_id": i.case_id,
        "investigator": i.investigator,
        "summary": i.summary[:200] if i.summary else None,
        "artifacts_count": i.artifacts_count,
        "content_hash": i.content_hash,
        "started_at": _iso(i.started_at),
        "ended_at": _iso(i.ended_at),
    }


def _serialize_escalation(e: Escalation) -> dict[str, Any]:
    return {
        "id": e.id,
        "case_id": e.case_id,
        "escalated_to": e.escalated_to,
        "level": e.level,
        "reason": e.reason,
        "escalated_at": _iso(e.escalated_at),
        "acknowledged_at": _iso(e.acknowledged_at),
    }


def _serialize_disposition(d: AlertDisposition) -> dict[str, Any]:
    return {
        "id": d.id,
        "alert_id": d.alert_id,
        "disposition": d.disposition,
        "rationale": d.rationale,
        "closed_by": d.closed_by,
        "closure_seconds": d.closure_seconds,
    }


@router.get(
    "/{submission_id}/records",
    dependencies=[
        Depends(require_roles(RoleEnum.ADMIN, RoleEnum.ANALYST, RoleEnum.SUPERVISOR))
    ],
)
async def get_dataset_records(
    submission_id: str,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if submission_id.startswith("raw-"):
        parts = submission_id.split("-", 2)
        if len(parts) != 3:
            raise HTTPException(status_code=400, detail="Invalid synthetic id")
        try:
            entity_id = int(parts[1])
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid entity id")
        payload_type = parts[2]

        if payload_type not in PAYLOAD_TO_MODEL:
            raise HTTPException(status_code=404, detail="Unknown payload type")

        model = PAYLOAD_TO_MODEL[payload_type]
        stmt = select(model).where(model.entity_id == entity_id)
        if payload_type == "alerts":
            stmt = stmt.order_by(Alert.detected_at.desc())
        elif payload_type == "cases":
            stmt = stmt.order_by(Case.opened_at.desc())
        elif payload_type == "investigations":
            stmt = stmt.order_by(Investigation.started_at.desc())
        elif payload_type == "escalations":
            stmt = stmt.order_by(Escalation.escalated_at.desc())

        total = (
            await db.execute(select(func.count()).select_from(stmt.subquery()))
        ).scalar_one()
        rows = (await db.execute(stmt.limit(limit).offset(offset))).scalars().all()

        if payload_type == "alerts":
            records = [_serialize_alert(r) for r in rows if isinstance(r, Alert)]
        elif payload_type == "cases":
            records = [_serialize_case(r) for r in rows if isinstance(r, Case)]
        elif payload_type == "investigations":
            records = [
                _serialize_investigation(r)
                for r in rows
                if isinstance(r, Investigation)
            ]
        elif payload_type == "escalations":
            records = [
                _serialize_escalation(r) for r in rows if isinstance(r, Escalation)
            ]
        elif payload_type == "dispositions":
            records = [
                _serialize_disposition(r)
                for r in rows
                if isinstance(r, AlertDisposition)
            ]
        else:
            records = []

        return {
            "payload_type": payload_type,
            "kind": "records",
            "total": int(total),
            "limit": limit,
            "offset": offset,
            "records": records,
        }

    try:
        sid_int = int(submission_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid submission id")

    sub = (
        await db.execute(select(DataSubmission).where(DataSubmission.id == sid_int))
    ).scalar_one_or_none()
    if sub is None:
        raise HTTPException(status_code=404, detail="Submission not found")

    payload_type = sub.payload_type

    if payload_type == "batch":
        return {
            "payload_type": "batch",
            "kind": "summary",
            "records": [],
            "total": 0,
            "limit": limit,
            "offset": offset,
            "message": "This is a batch submission. Records are grouped by type.",
        }

    if payload_type == "alerts":
        stmt = (
            select(Alert)
            .where(Alert.submission_id == sid_int)
            .order_by(Alert.detected_at.desc())
        )
        total = (
            await db.execute(select(func.count()).select_from(stmt.subquery()))
        ).scalar_one()
        rows = (await db.execute(stmt.limit(limit).offset(offset))).scalars().all()
        return {
            "payload_type": "alerts",
            "kind": "records",
            "total": int(total),
            "limit": limit,
            "offset": offset,
            "records": [_serialize_alert(a) for a in rows],
        }

    if payload_type == "cases":
        sub_alert_ids = [
            aid
            for (aid,) in (
                await db.execute(
                    select(Alert.id).where(Alert.submission_id == sid_int)
                )
            ).all()
        ]
        if sub_alert_ids:
            stmt = (
                select(Case)
                .where(Case.alert_id.in_(sub_alert_ids))
                .order_by(Case.opened_at.desc())
            )
        else:
            stmt = (
                select(Case)
                .where(Case.entity_id == sub.entity_id, Case.period_id == sub.period_id)
                .order_by(Case.opened_at.desc())
            )
        total = (
            await db.execute(select(func.count()).select_from(stmt.subquery()))
        ).scalar_one()
        rows = (await db.execute(stmt.limit(limit).offset(offset))).scalars().all()
        return {
            "payload_type": "cases",
            "kind": "records",
            "total": int(total),
            "limit": limit,
            "offset": offset,
            "records": [_serialize_case(c) for c in rows],
        }

    if payload_type == "investigations":
        stmt = (
            select(Investigation)
            .where(Investigation.entity_id == sub.entity_id)
            .order_by(Investigation.started_at.desc())
        )
        total = (
            await db.execute(select(func.count()).select_from(stmt.subquery()))
        ).scalar_one()
        rows = (await db.execute(stmt.limit(limit).offset(offset))).scalars().all()
        return {
            "payload_type": "investigations",
            "kind": "records",
            "total": int(total),
            "limit": limit,
            "offset": offset,
            "records": [_serialize_investigation(i) for i in rows],
        }

    if payload_type == "escalations":
        stmt = (
            select(Escalation)
            .where(Escalation.entity_id == sub.entity_id)
            .order_by(Escalation.escalated_at.desc())
        )
        total = (
            await db.execute(select(func.count()).select_from(stmt.subquery()))
        ).scalar_one()
        rows = (await db.execute(stmt.limit(limit).offset(offset))).scalars().all()
        return {
            "payload_type": "escalations",
            "kind": "records",
            "total": int(total),
            "limit": limit,
            "offset": offset,
            "records": [_serialize_escalation(e) for e in rows],
        }

    if payload_type == "dispositions":
        stmt = (
            select(AlertDisposition)
            .where(AlertDisposition.entity_id == sub.entity_id)
            .order_by(AlertDisposition.id.desc())
        )
        total = (
            await db.execute(select(func.count()).select_from(stmt.subquery()))
        ).scalar_one()
        rows = (await db.execute(stmt.limit(limit).offset(offset))).scalars().all()
        return {
            "payload_type": "dispositions",
            "kind": "records",
            "total": int(total),
            "limit": limit,
            "offset": offset,
            "records": [_serialize_disposition(d) for d in rows],
        }

    return {
        "payload_type": payload_type,
        "kind": "records",
        "total": 0,
        "limit": limit,
        "offset": offset,
        "records": [],
        "message": f"No viewer defined for payload type '{payload_type}'.",
    }