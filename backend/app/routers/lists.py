"""
List endpoints for entities, alerts, cases, investigations, escalations.

These expose the raw operational data that the analytics engine works on,
so supervisors can drill into the underlying records.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import require_roles
from app.models.analytics import Finding
from app.models.cse import CSEEntity
from app.models.operational import (
    Alert,
    Case,
    Escalation,
    Investigation,
)
from app.models.user import RoleEnum

router = APIRouter(tags=["lists"])


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if isinstance(dt, datetime) else dt


# ---------------------------------------------------------------------------
# Entities
# ---------------------------------------------------------------------------
@router.get(
    "/entities",
    dependencies=[Depends(require_roles(RoleEnum.ADMIN, RoleEnum.ANALYST, RoleEnum.SUPERVISOR))],
)
async def list_entities(
    period_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    entities = (
        await db.execute(select(CSEEntity).order_by(CSEEntity.id))
    ).scalars().all()

    out: list[dict[str, Any]] = []
    for e in entities:
        alerts = (
            await db.execute(
                select(func.count(Alert.id)).where(
                    Alert.entity_id == e.id,
                    *((Alert.period_id == period_id,) if period_id else ()),
                )
            )
        ).scalar_one()

        cases = (
            await db.execute(
                select(func.count(Case.id)).where(
                    Case.entity_id == e.id,
                    *((Case.period_id == period_id,) if period_id else ()),
                )
            )
        ).scalar_one()

        findings = (
            await db.execute(
                select(func.count(Finding.id)).where(
                    Finding.entity_id == e.id,
                    *((Finding.period_id == period_id,) if period_id else ()),
                )
            )
        ).scalar_one()

        indicator = (
            await db.execute(
                select(func.sum(Finding.review_indicator)).where(
                    Finding.entity_id == e.id,
                    *((Finding.period_id == period_id,) if period_id else ()),
                )
            )
        ).scalar_one()
        indicator = float(indicator) if indicator is not None else 0.0
        indicator = min(100.0, indicator)

        out.append(
            {
                "id": e.id,
                "code": e.code,
                "name": e.name,
                "sector": e.sector,
                "sub_sector": e.sub_sector,
                "region": e.region,
                "criticality": e.criticality,
                "peer_group": e.peer_group,
                "is_active": e.is_active,
                "alerts": int(alerts),
                "cases": int(cases),
                "findings": int(findings),
                "indicator": round(indicator, 2),
            }
        )
    return out


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------
@router.get(
    "/alerts",
    dependencies=[Depends(require_roles(RoleEnum.ADMIN, RoleEnum.ANALYST, RoleEnum.SUPERVISOR))],
)
async def list_alerts(
    entity_id: int | None = None,
    period_id: int | None = None,
    severity: str | None = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> dict:
    stmt = select(Alert).order_by(Alert.detected_at.desc())
    if entity_id is not None:
        stmt = stmt.where(Alert.entity_id == entity_id)
    if period_id is not None:
        stmt = stmt.where(Alert.period_id == period_id)
    if severity:
        stmt = stmt.where(Alert.severity == severity)

    total = (
        await db.execute(select(func.count()).select_from(stmt.subquery()))
    ).scalar_one()
    rows = (await db.execute(stmt.limit(limit).offset(offset))).scalars().all()

    codes = {
        eid: code for (eid, code) in (await db.execute(select(CSEEntity.id, CSEEntity.code))).all()
    }

    return {
        "total": int(total),
        "limit": limit,
        "offset": offset,
        "items": [
            {
                "id": a.id,
                "entity_id": a.entity_id,
                "entity_code": codes.get(a.entity_id),
                "external_id": a.external_id,
                "title": a.title,
                "severity": a.severity.value,
                "category": a.category,
                "source_system": a.source_system,
                "detected_at": _iso(a.detected_at),
                "acknowledged_at": _iso(a.acknowledged_at),
                "closed_at": _iso(a.closed_at),
                "status": a.status.value,
            }
            for a in rows
        ],
    }


# ---------------------------------------------------------------------------
# Cases
# ---------------------------------------------------------------------------
@router.get(
    "/cases",
    dependencies=[Depends(require_roles(RoleEnum.ADMIN, RoleEnum.ANALYST, RoleEnum.SUPERVISOR))],
)
async def list_cases(
    entity_id: int | None = None,
    period_id: int | None = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> dict:
    stmt = select(Case).order_by(Case.opened_at.desc())
    if entity_id is not None:
        stmt = stmt.where(Case.entity_id == entity_id)
    if period_id is not None:
        stmt = stmt.where(Case.period_id == period_id)

    total = (
        await db.execute(select(func.count()).select_from(stmt.subquery()))
    ).scalar_one()
    rows = (await db.execute(stmt.limit(limit).offset(offset))).scalars().all()

    codes = {
        eid: code for (eid, code) in (await db.execute(select(CSEEntity.id, CSEEntity.code))).all()
    }

    return {
        "total": int(total),
        "limit": limit,
        "offset": offset,
        "items": [
            {
                "id": c.id,
                "entity_id": c.entity_id,
                "entity_code": codes.get(c.entity_id),
                "external_id": c.external_id,
                "title": c.title,
                "severity": c.severity.value,
                "status": c.status,
                "opened_at": _iso(c.opened_at),
                "closed_at": _iso(c.closed_at),
                "assigned_to": c.assigned_to,
            }
            for c in rows
        ],
    }


# ---------------------------------------------------------------------------
# Investigations
# ---------------------------------------------------------------------------
@router.get(
    "/investigations",
    dependencies=[Depends(require_roles(RoleEnum.ADMIN, RoleEnum.ANALYST, RoleEnum.SUPERVISOR))],
)
async def list_investigations(
    entity_id: int | None = None,
    period_id: int | None = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> dict:
    stmt = select(Investigation).order_by(Investigation.started_at.desc())
    if entity_id is not None:
        stmt = stmt.where(Investigation.entity_id == entity_id)
    # period filter: investigations don't carry period_id, so filter by case's period
    if period_id is not None:
        stmt = stmt.join(Case, Case.id == Investigation.case_id).where(Case.period_id == period_id)

    total = (
        await db.execute(select(func.count()).select_from(stmt.subquery()))
    ).scalar_one()
    rows = (await db.execute(stmt.limit(limit).offset(offset))).scalars().all()

    codes = {
        eid: code for (eid, code) in (await db.execute(select(CSEEntity.id, CSEEntity.code))).all()
    }

    return {
        "total": int(total),
        "limit": limit,
        "offset": offset,
        "items": [
            {
                "id": i.id,
                "entity_id": i.entity_id,
                "entity_code": codes.get(i.entity_id),
                "case_id": i.case_id,
                "investigator": i.investigator,
                "started_at": _iso(i.started_at),
                "ended_at": _iso(i.ended_at),
                "summary": (i.summary[:200] if i.summary else None),
                "artifacts_count": i.artifacts_count,
                "content_hash": i.content_hash,
            }
            for i in rows
        ],
    }


# ---------------------------------------------------------------------------
# Escalations
# ---------------------------------------------------------------------------
@router.get(
    "/escalations",
    dependencies=[Depends(require_roles(RoleEnum.ADMIN, RoleEnum.ANALYST, RoleEnum.SUPERVISOR))],
)
async def list_escalations(
    entity_id: int | None = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> dict:
    stmt = select(Escalation).order_by(Escalation.escalated_at.desc())
    if entity_id is not None:
        stmt = stmt.where(Escalation.entity_id == entity_id)

    total = (
        await db.execute(select(func.count()).select_from(stmt.subquery()))
    ).scalar_one()
    rows = (await db.execute(stmt.limit(limit).offset(offset))).scalars().all()

    codes = {
        eid: code for (eid, code) in (await db.execute(select(CSEEntity.id, CSEEntity.code))).all()
    }

    return {
        "total": int(total),
        "limit": limit,
        "offset": offset,
        "items": [
            {
                "id": e.id,
                "entity_id": e.entity_id,
                "entity_code": codes.get(e.entity_id),
                "case_id": e.case_id,
                "escalated_at": _iso(e.escalated_at),
                "escalated_to": e.escalated_to,
                "level": e.level,
                "reason": e.reason,
                "acknowledged_at": _iso(e.acknowledged_at),
            }
            for e in rows
        ],
    }