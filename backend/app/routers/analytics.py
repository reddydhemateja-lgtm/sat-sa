"""
Analytics + findings HTTP surface.

Endpoints:
    POST /api/v1/analytics/run?period_id=N          Run the pipeline
    GET  /api/v1/analytics/summary?period_id=N      Dashboard counters
    GET  /api/v1/findings                           List findings (filters)
    GET  /api/v1/findings/{finding_id}              Full detail + evidence
    GET  /api/v1/findings/{finding_id}/evidence     Evidence rows only
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.orchestrator import run_analytics_for_period
from app.database import get_db
from app.deps import get_current_user, require_roles
from app.models.analytics import (
    Evidence,
    Finding,
    FindingCategoryEnum,
    PriorityEnum,
)
from app.models.cse import CSEEntity
from app.models.operational import Alert, Case, Escalation, Investigation
from app.models.period import AssessmentPeriod
from app.models.review import ReviewDecision
from app.models.user import RoleEnum, User

router = APIRouter(tags=["analytics"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _finding_to_dict(f: Finding, entity_code: str | None = None) -> dict[str, Any]:
    return {
        "id": f.id,
        "code": f.code,
        "entity_id": f.entity_id,
        "entity_code": entity_code,
        "period_id": f.period_id,
        "category": f.category.value,
        "rule_id": f.rule_id,
        "title": f.title,
        "narrative": f.narrative,
        "expected_behavior": f.expected_behavior,
        "observed_pattern": f.observed_pattern,
        "analytical_basis": f.analytical_basis,
        "priority": f.priority.value,
        "confidence": float(f.confidence) if isinstance(f.confidence, Decimal) else f.confidence,
        "review_indicator": float(f.review_indicator)
        if isinstance(f.review_indicator, Decimal)
        else f.review_indicator,
        "metrics": f.metrics,
        "status": f.status,
        "created_at": f.created_at.isoformat() if isinstance(f.created_at, datetime) else f.created_at,
        "updated_at": f.updated_at.isoformat() if isinstance(f.updated_at, datetime) else f.updated_at,
    }


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
@router.post(
    "/analytics/run",
    dependencies=[Depends(require_roles(RoleEnum.ADMIN, RoleEnum.ANALYST))],
)
async def run_analytics(
    period_id: int = Query(..., description="Assessment period id"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    try:
        summary = await run_analytics_for_period(
            db, period_id=period_id, actor_user_id=current_user.id
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Analytics run failed: {exc}")
    return summary


# ---------------------------------------------------------------------------
# Summary — dashboard counters
# ---------------------------------------------------------------------------
@router.get(
    "/analytics/summary",
    dependencies=[Depends(require_roles(RoleEnum.ADMIN, RoleEnum.ANALYST, RoleEnum.SUPERVISOR))],
)
async def analytics_summary(
    period_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
) -> dict:
    period = (
        await db.execute(select(AssessmentPeriod).where(AssessmentPeriod.id == period_id))
    ).scalar_one_or_none()
    if period is None:
        raise HTTPException(status_code=404, detail="Period not found")

    entities_count = (
        await db.execute(select(func.count(CSEEntity.id)).where(CSEEntity.is_active == True))  # noqa: E712
    ).scalar_one()

    findings_count = (
        await db.execute(
            select(func.count(Finding.id)).where(Finding.period_id == period_id)
        )
    ).scalar_one()

    pending_reviews = (
        await db.execute(
            select(func.count(Finding.id)).where(
                Finding.period_id == period_id, Finding.status == "OPEN"
            )
        )
    ).scalar_one()

    high_priority = (
        await db.execute(
            select(func.count(Finding.id)).where(
                Finding.period_id == period_id,
                Finding.priority == PriorityEnum.HIGH,
            )
        )
    ).scalar_one()

    alerts_count = (
        await db.execute(
            select(func.count(Alert.id)).where(Alert.period_id == period_id)
        )
    ).scalar_one()

    cases_count = (
        await db.execute(
            select(func.count(Case.id)).where(Case.period_id == period_id)
        )
    ).scalar_one()

    # category distribution
    cat_rows = await db.execute(
        select(Finding.category, func.count(Finding.id))
        .where(Finding.period_id == period_id)
        .group_by(Finding.category)
    )
    by_category = {c.value: n for c, n in cat_rows.all()}

    # priority distribution
    pri_rows = await db.execute(
        select(Finding.priority, func.count(Finding.id))
        .where(Finding.period_id == period_id)
        .group_by(Finding.priority)
    )
    by_priority = {p.value: n for p, n in pri_rows.all()}

    # per-entity counts + indicator (indicator is recomputed at fetch time)
    ent_rows = await db.execute(
        select(
            CSEEntity.id,
            CSEEntity.code,
            CSEEntity.name,
            CSEEntity.sector,
            CSEEntity.peer_group,
            func.count(Finding.id),
        )
        .select_from(CSEEntity)
        .outerjoin(
            Finding,
            (Finding.entity_id == CSEEntity.id) & (Finding.period_id == period_id),
        )
        .group_by(CSEEntity.id)
        .order_by(CSEEntity.id)
    )
    entities_out: list[dict[str, Any]] = []
    for eid, code, name, sector, peer_group, count in ent_rows.all():
        # indicator = sum of the review_indicator contribution on this entity's findings
        ind = (
            await db.execute(
                select(func.sum(Finding.review_indicator)).where(
                    Finding.entity_id == eid, Finding.period_id == period_id
                )
            )
        ).scalar_one()
        score = float(ind) if ind is not None else 0.0
        score = min(100.0, score)
        entities_out.append(
            {
                "entity_id": eid,
                "code": code,
                "name": name,
                "sector": sector,
                "peer_group": peer_group,
                "findings": int(count or 0),
                "indicator": round(score, 2),
            }
        )

    return {
        "period_id": period_id,
        "period_label": period.label,
        "entities_assessed": int(entities_count),
        "findings_total": int(findings_count),
        "pending_reviews": int(pending_reviews),
        "high_priority": int(high_priority),
        "alerts_total": int(alerts_count),
        "cases_total": int(cases_count),
        "by_category": by_category,
        "by_priority": by_priority,
        "entities": entities_out,
    }


# ---------------------------------------------------------------------------
# Findings list
# ---------------------------------------------------------------------------
@router.get(
    "/findings",
    dependencies=[Depends(require_roles(RoleEnum.ADMIN, RoleEnum.ANALYST, RoleEnum.SUPERVISOR))],
)
async def list_findings(
    period_id: int | None = None,
    entity_id: int | None = None,
    category: str | None = None,
    priority: str | None = None,
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> dict:
    stmt = select(Finding).order_by(Finding.created_at.desc())
    if period_id is not None:
        stmt = stmt.where(Finding.period_id == period_id)
    if entity_id is not None:
        stmt = stmt.where(Finding.entity_id == entity_id)
    if category is not None:
        try:
            stmt = stmt.where(Finding.category == FindingCategoryEnum(category))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid category: {category}")
    if priority is not None:
        try:
            stmt = stmt.where(Finding.priority == PriorityEnum(priority))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid priority: {priority}")
    if status_filter is not None:
        stmt = stmt.where(Finding.status == status_filter)

    total = (
        await db.execute(select(func.count()).select_from(stmt.subquery()))
    ).scalar_one()

    rows = (await db.execute(stmt.limit(limit).offset(offset))).scalars().all()

    entity_codes = {
        eid: code
        for (eid, code) in (
            await db.execute(select(CSEEntity.id, CSEEntity.code))
        ).all()
    }

    return {
        "total": int(total),
        "limit": limit,
        "offset": offset,
        "items": [_finding_to_dict(f, entity_codes.get(f.entity_id)) for f in rows],
    }


# ---------------------------------------------------------------------------
# Finding detail
# ---------------------------------------------------------------------------
@router.get(
    "/findings/{finding_id}",
    dependencies=[Depends(require_roles(RoleEnum.ADMIN, RoleEnum.ANALYST, RoleEnum.SUPERVISOR))],
)
async def get_finding(finding_id: int, db: AsyncSession = Depends(get_db)) -> dict:
    f = (
        await db.execute(select(Finding).where(Finding.id == finding_id))
    ).scalar_one_or_none()
    if f is None:
        raise HTTPException(status_code=404, detail="Finding not found")

    entity = (
        await db.execute(select(CSEEntity).where(CSEEntity.id == f.entity_id))
    ).scalar_one_or_none()

    evidence_rows = (
        await db.execute(
            select(Evidence).where(Evidence.finding_id == finding_id).order_by(Evidence.id)
        )
    ).scalars().all()

    decisions = (
        await db.execute(
            select(ReviewDecision)
            .where(ReviewDecision.finding_id == finding_id)
            .order_by(ReviewDecision.decided_at.desc())
        )
    ).scalars().all()

    return {
        "finding": _finding_to_dict(f, entity.code if entity else None),
        "entity": {
            "id": entity.id,
            "code": entity.code,
            "name": entity.name,
            "sector": entity.sector,
            "criticality": entity.criticality,
            "peer_group": entity.peer_group,
        }
        if entity
        else None,
        "evidence": [
            {
                "id": ev.id,
                "record_type": ev.record_type,
                "record_id": ev.record_id,
                "snippet": ev.snippet,
                "weight": float(ev.weight) if isinstance(ev.weight, Decimal) else ev.weight,
            }
            for ev in evidence_rows
        ],
        "review_decisions": [
            {
                "id": d.id,
                "decision": d.decision.value,
                "comment": d.comment,
                "previous_decision": d.previous_decision,
                "decided_at": d.decided_at.isoformat() if isinstance(d.decided_at, datetime) else d.decided_at,
            }
            for d in decisions
        ],
    }


@router.get(
    "/findings/{finding_id}/evidence",
    dependencies=[Depends(require_roles(RoleEnum.ADMIN, RoleEnum.ANALYST, RoleEnum.SUPERVISOR))],
)
async def get_finding_evidence(
    finding_id: int, db: AsyncSession = Depends(get_db)
) -> list[dict]:
    f = (
        await db.execute(select(Finding.id).where(Finding.id == finding_id))
    ).scalar_one_or_none()
    if f is None:
        raise HTTPException(status_code=404, detail="Finding not found")
    rows = (
        await db.execute(
            select(Evidence).where(Evidence.finding_id == finding_id).order_by(Evidence.id)
        )
    ).scalars().all()
    return [
        {
            "id": ev.id,
            "record_type": ev.record_type,
            "record_id": ev.record_id,
            "snippet": ev.snippet,
            "weight": float(ev.weight) if isinstance(ev.weight, Decimal) else ev.weight,
        }
        for ev in rows
    ]