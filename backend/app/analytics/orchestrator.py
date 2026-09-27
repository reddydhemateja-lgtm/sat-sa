"""
Orchestrator — runs every analytics module for a period and persists results.

Entry point: `run_analytics_for_period(db, period_id, current_user_id)`.

Responsibilities:
    - Load threshold config
    - For each active entity:
        - Run execution-gap, negative-space, anomaly, peer rules
        - Apply prioritization
        - Persist Finding + Evidence rows (idempotent per rule/entity/period)
        - Persist PeerComparison rows for the entity
    - Compute the entity-level Supervisory Review Indicator (stored on the
      dashboard's summary endpoint on demand, not persisted)
    - Write a single audit-log entry summarizing the run
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.anomaly_detection import run_all as run_anomaly
from app.analytics.config_loader import load_config
from app.analytics.execution_gaps import run_all as run_execution_gaps
from app.analytics.framework import persist_findings
from app.analytics.negative_space import run_all as run_negative_space
from app.analytics.peer_comparison import run_all as run_peer
from app.analytics.prioritization import apply_priorities
from app.analytics.review_indicator import compute_entity_indicator
from app.audit import record_audit
from app.models.analytics import PeerComparison
from app.models.cse import CSEEntity
from app.models.period import AssessmentPeriod


# ---------------------------------------------------------------------------
# Persist peer comparison rows
# ---------------------------------------------------------------------------
async def _persist_peer_comparisons(
    db: AsyncSession, *, entity_id: int, period_id: int, cfg: dict
) -> int:
    """
    Rebuild PeerComparison rows for one entity from current period metrics.

    Requires the peer context to have been computed already and injected into
    cfg under `_peer_group_*` keys. The orchestrator runs peer_comparison.run_all
    before this to populate those.
    """
    from app.models.cse import CSEEntity

    entity = (
        await db.execute(select(CSEEntity).where(CSEEntity.id == entity_id))
    ).scalar_one_or_none()
    if entity is None:
        return 0

    peer_group = entity.peer_group or "UNGROUPED"

    # fetch previously computed peer context out of cfg (set by peer_comparison.run_all)
    groups = cfg.get("_peer_groups") or {}
    medians = cfg.get("_peer_medians") or {}
    members = groups.get(peer_group) or {}
    this = members.get(entity_id)
    group_med = medians.get(peer_group) or {}

    if this is None or not group_med:
        return 0

    # wipe existing rows for this entity+period
    await db.execute(
        delete(PeerComparison).where(
            PeerComparison.entity_id == entity_id,
            PeerComparison.period_id == period_id,
        )
    )

    # compute per-metric p25/p75 and z-score against peer group
    from statistics import median
    metrics = [
        "alert_to_case_rate",
        "case_to_investigation_rate",
        "case_to_escalation_rate",
        "mean_closure_minutes",
    ]
    inserted = 0
    for metric in metrics:
        series = [members[eid][metric] for eid in members]
        if len(series) < 3:
            continue
        series_sorted = sorted(series)
        n = len(series_sorted)

        def pct(p: float) -> float:
            k = (n - 1) * p
            f = int(k)
            c = min(f + 1, n - 1)
            if f == c:
                return series_sorted[f]
            return series_sorted[f] + (series_sorted[c] - series_sorted[f]) * (k - f)

        p25 = pct(0.25)
        p75 = pct(0.75)
        med = median(series)
        devs = [abs(x - med) for x in series]
        mad = median(devs)
        z = 0.0 if mad == 0 else 0.6745 * (this[metric] - med) / mad

        db.add(
            PeerComparison(
                entity_id=entity_id,
                period_id=period_id,
                peer_group=peer_group,
                metric=metric,
                entity_value=Decimal(f"{this[metric]:.6f}"),
                peer_median=Decimal(f"{med:.6f}"),
                peer_p25=Decimal(f"{p25:.6f}"),
                peer_p75=Decimal(f"{p75:.6f}"),
                z_score=Decimal(f"{z:.4f}"),
                sample_size=len(series),
            )
        )
        inserted += 1

    return inserted


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
async def run_analytics_for_period(
    db: AsyncSession, *, period_id: int, actor_user_id: int | None
) -> dict:
    """
    Run the full analytics pipeline for one period, for every active entity.

    Returns a summary dict with per-entity counts and overall totals.
    """
    period = (
        await db.execute(select(AssessmentPeriod).where(AssessmentPeriod.id == period_id))
    ).scalar_one_or_none()
    if period is None:
        raise ValueError(f"Period id {period_id} not found")

    cfg = await load_config(db)

    entities = (
        await db.execute(select(CSEEntity).where(CSEEntity.is_active == True))  # noqa: E712
    ).scalars().all()

    summary: dict = {
        "period_id": period_id,
        "period_label": period.label,
        "entities": [],
        "total_created": 0,
        "total_deleted": 0,
        "total_peer_rows": 0,
    }

    # First pass: compute peer context once (populates cfg side-channel keys)
    # We run peer_comparison.run_all for each entity; it computes context each
    # time. To avoid redundant queries, we do it for the first entity, then
    # rely on the injected keys for the rest.
    peer_context_ready = False

    for entity in entities:
        drafts = []
        # 1. execution gaps
        drafts += await run_execution_gaps(
            db, entity_id=entity.id, period_id=period_id, cfg=cfg
        )
        # 2. negative space — needs peer context injected
        if not peer_context_ready:
            # run_peer both computes context and returns findings for this entity
            peer_drafts = await run_peer(
                db, entity_id=entity.id, period_id=period_id, cfg=cfg
            )
            peer_context_ready = True
            # cache the computed groups/medians for _persist_peer_comparisons
            from app.analytics.peer_comparison import compute_peer_context

            ctx = await compute_peer_context(db, period_id=period_id, cfg=cfg)
            cfg["_peer_groups"] = ctx["groups"]
            cfg["_peer_medians"] = ctx["group_medians"]
        else:
            peer_drafts = await run_peer(
                db, entity_id=entity.id, period_id=period_id, cfg=cfg
            )
        drafts += peer_drafts
        # 3. negative space (uses injected keys from peer step)
        drafts += await run_negative_space(
            db, entity_id=entity.id, period_id=period_id, cfg=cfg
        )
        # 4. anomalies
        drafts += await run_anomaly(
            db, entity_id=entity.id, period_id=period_id, cfg=cfg
        )

        # 5. prioritize
        apply_priorities(drafts, cfg)

        # 6. persist findings
        created, deleted = await persist_findings(
            db, entity_id=entity.id, period_id=period_id, drafts=drafts
        )

        # 7. persist peer comparison rows
        peer_rows = await _persist_peer_comparisons(
            db, entity_id=entity.id, period_id=period_id, cfg=cfg
        )

        # 8. compute the entity-level Supervisory Review Indicator
        indicator = compute_entity_indicator(drafts, cfg)

        summary["entities"].append(
            {
                "entity_id": entity.id,
                "entity_code": entity.code,
                "findings_created": created,
                "findings_deleted": deleted,
                "peer_rows": peer_rows,
                "indicator": indicator["score"],
                "counts": indicator["counts"],
            }
        )
        summary["total_created"] += created
        summary["total_deleted"] += deleted
        summary["total_peer_rows"] += peer_rows

    # audit entry — one row per run
    await record_audit(
        db,
        user_id=actor_user_id,
        action="ANALYTICS_RUN",
        target_type="assessment_period",
        target_id=period_id,
        new_value={
            "entities": len(entities),
            "findings_created": summary["total_created"],
            "findings_deleted": summary["total_deleted"],
            "peer_rows": summary["total_peer_rows"],
        },
    )

    await db.commit()
    return summary