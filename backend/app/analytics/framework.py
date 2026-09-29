"""
Shared framework for all analytics modules.

Every rule produces one or more `FindingDraft` objects. The orchestrator
persists them via `persist_findings`, which is idempotent per
(period_id, rule_id, entity_id): re-running replaces prior findings for
that tuple and writes an audit entry.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Iterable

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analytics import (
    Evidence,
    Finding,
    FindingCategoryEnum,
    PriorityEnum,
)


# ---------------------------------------------------------------------------
# FindingDraft — the shape every rule returns
# ---------------------------------------------------------------------------
@dataclass
class FindingDraft:
    rule_id: str
    category: FindingCategoryEnum
    title: str
    narrative: str
    expected_behavior: str
    observed_pattern: str
    analytical_basis: str
    priority: PriorityEnum
    confidence: float                 # 0.0–1.0
    indicator: float                  # contribution to Supervisory Review Indicator
    metrics: dict[str, Any] = field(default_factory=dict)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    classification: str | None = None


# ---------------------------------------------------------------------------
# Code generator — SAT-YYYY-NNNN
# ---------------------------------------------------------------------------
async def next_finding_code(db: AsyncSession, year: int | None = None) -> str:
    y = year or datetime.utcnow().year
    prefix = f"SAT-{y}-"
    result = await db.execute(
        select(Finding.code).where(Finding.code.like(f"{prefix}%"))
    )
    codes = [c for (c,) in result.all() if c.startswith(prefix)]
    if not codes:
        return f"{prefix}0001"
    max_n = 0
    for c in codes:
        try:
            n = int(c.rsplit("-", 1)[1])
            if n > max_n:
                max_n = n
        except (ValueError, IndexError):
            continue
    return f"{prefix}{max_n + 1:04d}"


# ---------------------------------------------------------------------------
# Persistence — idempotent per (period, rule, entity)
# ---------------------------------------------------------------------------
async def persist_findings(
    db: AsyncSession,
    *,
    entity_id: int,
    period_id: int,
    drafts: Iterable[FindingDraft],
) -> tuple[int, int]:
    """
    Persist finding drafts for one entity+period.

    Idempotency: for each (rule_id) present in `drafts`, delete any existing
    Finding rows with the same (entity_id, period_id, rule_id), then insert
    fresh ones. This gives deterministic re-runs.

    Returns (created_count, deleted_count).
    """
    drafts_list = list(drafts)
    created = 0
    deleted = 0

    rule_ids = {d.rule_id for d in drafts_list}

    for rid in rule_ids:
        prior_q = select(Finding.id).where(
            Finding.entity_id == entity_id,
            Finding.period_id == period_id,
            Finding.rule_id == rid,
        )
        prior_ids = [pk for (pk,) in (await db.execute(prior_q)).all()]
        if prior_ids:
            await db.execute(delete(Evidence).where(Evidence.finding_id.in_(prior_ids)))
            await db.execute(delete(Finding).where(Finding.id.in_(prior_ids)))
            deleted += len(prior_ids)

    for d in drafts_list:
        code = await next_finding_code(db)
        finding = Finding(
            code=code,
            entity_id=entity_id,
            period_id=period_id,
            category=d.category,
            rule_id=d.rule_id,
            title=d.title,
            narrative=d.narrative,
            expected_behavior=d.expected_behavior,
            observed_pattern=d.observed_pattern,
            analytical_basis=d.analytical_basis,
            priority=d.priority,
            confidence=Decimal(f"{d.confidence:.3f}"),
            review_indicator=Decimal(f"{d.indicator:.2f}"),
            metrics=d.metrics or None,
            classification=d.classification,
            status="OPEN",
        )
        db.add(finding)
        await db.flush()

        for ev in d.evidence:
            db.add(
                Evidence(
                    finding_id=finding.id,
                    record_type=ev["record_type"],
                    record_id=int(ev["record_id"]),
                    snippet=ev.get("snippet"),
                    weight=Decimal(f"{float(ev.get('weight', 1.0)):.3f}"),
                )
            )
        created += 1

    await db.flush()
    return created, deleted