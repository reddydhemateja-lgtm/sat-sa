"""
Supervisory review endpoints.

    POST /api/v1/findings/{id}/review      record a decision
    GET  /api/v1/findings/{id}/decisions   decision history
    GET  /api/v1/review-queue              prioritized queue for a period
    GET  /api/v1/audit-log                 full audit trail with filters
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import record_audit
from app.database import get_db
from app.deps import get_current_user, require_roles
from app.models.analytics import Finding, PriorityEnum
from app.models.audit import AuditLog
from app.models.cse import CSEEntity
from app.models.review import ReviewDecision, ReviewDecisionEnum
from app.models.user import RoleEnum, User
from app.schemas.review import ReviewDecisionCreate, ReviewDecisionOut

router = APIRouter(tags=["reviews"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _finding_status_for_decision(d: ReviewDecisionEnum) -> str:
    return {
        ReviewDecisionEnum.CONFIRMED: "CONFIRMED",
        ReviewDecisionEnum.REJECTED: "REJECTED",
        ReviewDecisionEnum.FURTHER_REVIEW: "FURTHER_REVIEW",
        ReviewDecisionEnum.PENDING: "OPEN",
    }[d]


def _dec_to_dict(d: ReviewDecision) -> dict[str, Any]:
    return {
        "id": d.id,
        "finding_id": d.finding_id,
        "reviewer_id": d.reviewer_id,
        "decision": d.decision.value,
        "comment": d.comment,
        "previous_decision": d.previous_decision,
        "decided_at": d.decided_at.isoformat()
        if isinstance(d.decided_at, datetime)
        else d.decided_at,
        "created_at": d.created_at.isoformat()
        if isinstance(d.created_at, datetime)
        else d.created_at,
    }


# ---------------------------------------------------------------------------
# Submit a decision
# ---------------------------------------------------------------------------
@router.post(
    "/findings/{finding_id}/review",
    dependencies=[Depends(require_roles(RoleEnum.ADMIN, RoleEnum.SUPERVISOR))],
)
async def submit_review(
    finding_id: int,
    payload: ReviewDecisionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    finding = (
        await db.execute(select(Finding).where(Finding.id == finding_id))
    ).scalar_one_or_none()
    if finding is None:
        raise HTTPException(status_code=404, detail="Finding not found")

    previous_status = finding.status
    previous_decision = (
        await db.execute(
            select(ReviewDecision)
            .where(ReviewDecision.finding_id == finding_id)
            .order_by(desc(ReviewDecision.decided_at))
            .limit(1)
        )
    ).scalar_one_or_none()
    previous_decision_value = (
        previous_decision.decision.value if previous_decision else None
    )

    new_status = _finding_status_for_decision(payload.decision)
    finding.status = new_status

    decision = ReviewDecision(
        finding_id=finding_id,
        reviewer_id=current_user.id,
        decision=payload.decision,
        comment=payload.comment,
        previous_decision=previous_decision_value,
        decided_at=datetime.utcnow(),
    )
    db.add(decision)
    await db.flush()

    await record_audit(
        db,
        user_id=current_user.id,
        action="REVIEW_DECISION",
        target_type="finding",
        target_id=finding_id,
        previous_value={
            "status": previous_status,
            "decision": previous_decision_value,
        },
        new_value={
            "status": new_status,
            "decision": payload.decision.value,
            "comment_present": bool(payload.comment),
        },
    )

    await db.commit()
    await db.refresh(decision)
    await db.refresh(finding)

    return {
        "finding_id": finding_id,
        "finding_code": finding.code,
        "new_status": finding.status,
        "decision": _dec_to_dict(decision),
    }


# ---------------------------------------------------------------------------
# Decision history
# ---------------------------------------------------------------------------
@router.get(
    "/findings/{finding_id}/decisions",
    response_model=list[ReviewDecisionOut],
    dependencies=[
        Depends(require_roles(RoleEnum.ADMIN, RoleEnum.SUPERVISOR, RoleEnum.ANALYST))
    ],
)
async def list_decisions(
    finding_id: int,
    db: AsyncSession = Depends(get_db),
) -> list[ReviewDecisionOut]:
    rows = (
        await db.execute(
            select(ReviewDecision)
            .where(ReviewDecision.finding_id == finding_id)
            .order_by(desc(ReviewDecision.decided_at))
        )
    ).scalars().all()
    return [ReviewDecisionOut.model_validate(r) for r in rows]


# ---------------------------------------------------------------------------
# Review queue
# ---------------------------------------------------------------------------
@router.get(
    "/review-queue",
    dependencies=[
        Depends(require_roles(RoleEnum.ADMIN, RoleEnum.SUPERVISOR, RoleEnum.ANALYST))
    ],
)
async def review_queue(
    period_id: int = Query(...),
    include_decided: bool = Query(
        False, description="Include findings with a decision already recorded"
    ),
    limit: int = Query(200, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
) -> dict:
    stmt = (
        select(Finding)
        .where(Finding.period_id == period_id)
        .order_by(
            case(
                (Finding.priority == PriorityEnum.HIGH, 1),
                (Finding.priority == PriorityEnum.MEDIUM, 2),
                (Finding.priority == PriorityEnum.LOW, 3),
                else_=4,
            ),
            desc(Finding.review_indicator),
            desc(Finding.created_at),
        )
    )
    if not include_decided:
        stmt = stmt.where(Finding.status == "OPEN")
    stmt = stmt.limit(limit)

    rows = (await db.execute(stmt)).scalars().all()

    entity_codes = {
        eid: code
        for (eid, code) in (
            await db.execute(select(CSEEntity.id, CSEEntity.code))
        ).all()
    }

    items = []
    for f in rows:
        items.append(
            {
                "id": f.id,
                "code": f.code,
                "entity_id": f.entity_id,
                "entity_code": entity_codes.get(f.entity_id),
                "period_id": f.period_id,
                "category": f.category.value,
                "rule_id": f.rule_id,
                "title": f.title,
                "priority": f.priority.value,
                "confidence": float(f.confidence)
                if isinstance(f.confidence, Decimal)
                else f.confidence,
                "review_indicator": float(f.review_indicator)
                if isinstance(f.review_indicator, Decimal)
                else f.review_indicator,
                "status": f.status,
                "created_at": f.created_at.isoformat()
                if isinstance(f.created_at, datetime)
                else f.created_at,
            }
        )

    buckets = {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFORMATIONAL": 0}
    for f in rows:
        buckets[f.priority.value] = buckets.get(f.priority.value, 0) + 1

    return {
        "period_id": period_id,
        "total": len(items),
        "buckets": buckets,
        "items": items,
    }


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------
@router.get(
    "/audit-log",
    dependencies=[Depends(require_roles(RoleEnum.ADMIN, RoleEnum.SUPERVISOR))],
)
async def audit_log(
    action: str | None = None,
    target_type: str | None = None,
    user_id: int | None = None,
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> dict:
    stmt = select(AuditLog).order_by(desc(AuditLog.created_at))
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if target_type:
        stmt = stmt.where(AuditLog.target_type == target_type)
    if user_id:
        stmt = stmt.where(AuditLog.user_id == user_id)

    total = (
        await db.execute(select(func.count()).select_from(stmt.subquery()))
    ).scalar_one()
    rows = (await db.execute(stmt.limit(limit).offset(offset))).scalars().all()

    user_map = {
        uid: uname
        for (uid, uname) in (
            await db.execute(select(User.id, User.username))
        ).all()
    }

    return {
        "total": int(total),
        "limit": limit,
        "offset": offset,
        "items": [
            {
                "id": r.id,
                "user_id": r.user_id,
                "username": user_map.get(r.user_id),
                "action": r.action,
                "target_type": r.target_type,
                "target_id": r.target_id,
                "previous_value": r.previous_value,
                "new_value": r.new_value,
                "ip_address": r.ip_address,
                "created_at": r.created_at.isoformat()
                if isinstance(r.created_at, datetime)
                else r.created_at,
            }
            for r in rows
        ],
    }