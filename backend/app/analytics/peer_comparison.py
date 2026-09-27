"""
Peer Comparison.

Compares entities within configured peer groups using normalized
indicators. Deviations are presented as review signals, not judgments.

Injects the peer-category distribution and group-mean volume into the
config dict so downstream rules (NS-002, NS-005) can use them.
"""

from __future__ import annotations

from collections import defaultdict
from statistics import median

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.config_loader import get as cfg_get
from app.analytics.framework import FindingDraft
from app.models.analytics import FindingCategoryEnum, PriorityEnum
from app.models.cse import CSEEntity
from app.models.operational import Alert, Case, Escalation, Investigation


# ---------------------------------------------------------------------------
# Aggregated metrics for one entity
# ---------------------------------------------------------------------------
async def _entity_metrics(
    db: AsyncSession, *, entity_id: int, period_id: int
) -> dict:
    alerts = (
        await db.execute(
            select(Alert).where(
                Alert.entity_id == entity_id, Alert.period_id == period_id
            )
        )
    ).scalars().all()

    cases = (
        await db.execute(
            select(Case).where(
                Case.entity_id == entity_id, Case.period_id == period_id
            )
        )
    ).scalars().all()

    case_ids = [c.id for c in cases]
    investigations = []
    escalations = []
    if case_ids:
        investigations = (
            await db.execute(
                select(Investigation).where(Investigation.case_id.in_(case_ids))
            )
        ).scalars().all()
        escalations = (
            await db.execute(
                select(Escalation).where(Escalation.case_id.in_(case_ids))
            )
        ).scalars().all()

    total_alerts = len(alerts)
    total_cases = len(cases)
    closed_alerts = [a for a in alerts if a.closed_at and a.detected_at]

    closure_minutes = [
        (a.closed_at - a.detected_at).total_seconds() / 60.0 for a in closed_alerts
    ]
    mean_closure = sum(closure_minutes) / len(closure_minutes) if closure_minutes else 0.0

    metrics = {
        "alerts": total_alerts,
        "cases": total_cases,
        "investigations": len(investigations),
        "escalations": len(escalations),
        "alert_to_case_rate": (total_cases / total_alerts) if total_alerts else 0.0,
        "case_to_investigation_rate": (
            len(investigations) / total_cases if total_cases else 0.0
        ),
        "case_to_escalation_rate": (
            len(escalations) / total_cases if total_cases else 0.0
        ),
        "mean_closure_minutes": mean_closure,
    }

    # category distribution
    cats: dict[str, int] = defaultdict(int)
    for a in alerts:
        cats[a.category] += 1
    metrics["category_counts"] = dict(cats)

    return metrics


# ---------------------------------------------------------------------------
# z-score helper
# ---------------------------------------------------------------------------
def _zscore(value: float, peers: list[float]) -> float:
    if len(peers) < 3:
        return 0.0
    med = median(peers)
    devs = [abs(x - med) for x in peers]
    mad = median(devs)
    if mad == 0:
        return 0.0
    return 0.6745 * (value - med) / mad


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
async def compute_peer_context(
    db: AsyncSession, *, period_id: int, cfg: dict
) -> dict:
    """
    Compute peer-group aggregates for the period. Returns a dict with:
        groups: {peer_group: {entity_id: metrics}}
        group_medians: {peer_group: {metric: median}}
        category_distribution: {peer_group: {category: total_count_across_group}}
        group_mean_volume: {peer_group: float}
    """
    entities = (
        await db.execute(select(CSEEntity).where(CSEEntity.is_active == True))  # noqa: E712
    ).scalars().all()

    by_group: dict[str, dict[int, dict]] = defaultdict(dict)
    for e in entities:
        group = e.peer_group or "UNGROUPED"
        by_group[group][e.id] = await _entity_metrics(
            db, entity_id=e.id, period_id=period_id
        )

    medians: dict[str, dict[str, float]] = {}
    cats_by_group: dict[str, dict[str, int]] = {}
    mean_volume: dict[str, float] = {}

    for group, members in by_group.items():
        metric_names = [
            "alerts",
            "cases",
            "investigations",
            "escalations",
            "alert_to_case_rate",
            "case_to_investigation_rate",
            "case_to_escalation_rate",
            "mean_closure_minutes",
        ]
        group_medians: dict[str, float] = {}
        for m in metric_names:
            series = [members[eid][m] for eid in members]
            group_medians[m] = float(median(series)) if series else 0.0
        medians[group] = group_medians

        # aggregate category counts across the group
        cat_totals: dict[str, int] = defaultdict(int)
        for eid, m in members.items():
            for c, n in m["category_counts"].items():
                cat_totals[c] += n
        cats_by_group[group] = dict(cat_totals)

        volumes = [members[eid]["alerts"] for eid in members]
        mean_volume[group] = float(sum(volumes) / len(volumes)) if volumes else 0.0

    return {
        "groups": {g: dict(m) for g, m in by_group.items()},
        "group_medians": medians,
        "category_distribution": cats_by_group,
        "group_mean_volume": mean_volume,
    }


async def run_all(
    db: AsyncSession, *, entity_id: int, period_id: int, cfg: dict
) -> list[FindingDraft]:
    """
    Produce PEER-DEVIATION findings for one entity, and inject peer context
    into cfg as side-effect keys (_peer_category_distribution, _entity_peer_group,
    _group_mean_volume). The orchestrator calls this before running NS rules.
    """
    z_thr = cfg_get(cfg, "peer.z_score_threshold", 2.0)
    min_size = cfg_get(cfg, "peer.min_sample_size", 3)

    entity = (
        await db.execute(select(CSEEntity).where(CSEEntity.id == entity_id))
    ).scalar_one_or_none()
    if entity is None:
        return []

    peer_group = entity.peer_group or "UNGROUPED"
    context = await compute_peer_context(db, period_id=period_id, cfg=cfg)

    # side-channel injections for other rules
    cfg["_peer_category_distribution"] = context["category_distribution"]
    cfg["_entity_peer_group"] = peer_group
    cfg["_group_mean_volume"] = context["group_mean_volume"].get(peer_group, 0.0)

    group_members = context["groups"].get(peer_group, {})
    if len(group_members) < min_size:
        return []

    medians = context["group_medians"].get(peer_group, {})
    this = group_members.get(entity_id)
    if this is None:
        return []

    findings: list[FindingDraft] = []
    metric_labels = {
        "alert_to_case_rate": "Alert-to-Case conversion rate",
        "case_to_investigation_rate": "Case-to-Investigation rate",
        "case_to_escalation_rate": "Case-to-Escalation rate",
        "mean_closure_minutes": "Mean alert closure time",
    }
    for metric, label in metric_labels.items():
        series = [group_members[eid][metric] for eid in group_members]
        value = this[metric]
        z = _zscore(value, series)
        if abs(z) < z_thr:
            continue
        direction = "above" if z > 0 else "below"
        findings.append(
            FindingDraft(
                rule_id="PEER-001",
                category=FindingCategoryEnum.PEER_DEVIATION,
                title=f"{label} deviates from peer group",
                narrative=(
                    f"Entity's {label.lower()} is {value:.3f}, which is "
                    f"{abs(z):.2f} robust standard deviations {direction} the "
                    f"median of its peer group '{peer_group}' "
                    f"({medians.get(metric, 0):.3f})."
                ),
                expected_behavior=(
                    f"Peer group '{peer_group}' median: {medians.get(metric, 0):.3f}"
                ),
                observed_pattern=f"Entity value: {value:.3f} (z={z:.2f})",
                analytical_basis=f"Peer comparison on {metric} (rule PEER-001)",
                priority=PriorityEnum.MEDIUM,
                confidence=0.6,
                indicator=5.0,
                metrics={
                    "metric": metric,
                    "entity_value": round(value, 4),
                    "peer_median": round(medians.get(metric, 0), 4),
                    "z_score": round(z, 3),
                    "peer_group": peer_group,
                    "peer_sample_size": len(group_members),
                },
                evidence=[],
            )
        )

    return findings