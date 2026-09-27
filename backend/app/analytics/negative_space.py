"""
Negative Space Detection.

Rules NS-001 … NS-005 identify what expected evidence is *missing* from
an entity's operational picture. These are NOT automatic security
failures — they are indicators for supervisory review, presented with
explicit Expected / Observed / Missing structure.

UI contract: for every NS finding, the three fields
    expected_behavior, observed_pattern, narrative
are rendered as three separate columns in the finding-detail view.
"""

from __future__ import annotations

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.config_loader import get as cfg_get
from app.analytics.framework import FindingDraft
from app.models.analytics import FindingCategoryEnum, PriorityEnum
from app.models.cse import Asset, CSEEntity
from app.models.operational import (
    Alert,
    Case,
    Escalation,
    Investigation,
    SeverityEnum,
)


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------
async def _load(db: AsyncSession, entity_id: int, period_id: int) -> dict:
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

    assets = (
        await db.execute(select(Asset).where(Asset.entity_id == entity_id))
    ).scalars().all()

    return {
        "alerts": alerts,
        "cases": cases,
        "investigations": investigations,
        "escalations": escalations,
        "assets": assets,
    }


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------
def ns_001_critical_assets_without_alerts(data: dict, cfg: dict) -> list[FindingDraft]:
    """NS-001: Critical/High assets with zero alerts in the period."""
    assets: list[Asset] = data["assets"]
    alerts: list[Alert] = data["alerts"]
    seen_asset_ids = {a.asset_id for a in alerts if a.asset_id}

    out: list[FindingDraft] = []
    for asset in assets:
        if asset.criticality not in ("CRITICAL", "HIGH"):
            continue
        if asset.id in seen_asset_ids:
            continue
        out.append(
            FindingDraft(
                rule_id="NS-001",
                category=FindingCategoryEnum.NEGATIVE_SPACE,
                title="No telemetry observed for critical asset",
                narrative=(
                    f"Asset {asset.asset_code} ({asset.asset_type}, "
                    f"criticality={asset.criticality}) produced zero alerts during "
                    f"the period. This may indicate a monitoring blind spot."
                ),
                expected_behavior=(
                    "Critical and high assets are expected to generate baseline "
                    "monitoring activity."
                ),
                observed_pattern="0 alerts",
                analytical_basis="Expected Telemetry Coverage (rule NS-001)",
                priority=PriorityEnum.MEDIUM,
                confidence=0.6,
                indicator=6.0,
                metrics={
                    "asset_code": asset.asset_code,
                    "asset_type": asset.asset_type,
                    "criticality": asset.criticality,
                },
                evidence=[
                    {"record_type": "asset", "record_id": asset.id,
                     "snippet": f"{asset.asset_code} ({asset.asset_type})",
                     "weight": 1.0},
                ],
            )
        )
        if len(out) >= 5:
            break
    return out


def ns_002_missing_category_vs_peers(data: dict, cfg: dict) -> list[FindingDraft]:
    """NS-002: A category that peers see commonly is absent here."""
    # This rule needs the peer context, which the orchestrator injects via cfg
    # under the key "_peer_category_distribution": {peer_group: {cat: count}}
    peer_dist = cfg.get("_peer_category_distribution")
    if not peer_dist:
        return []

    alerts: list[Alert] = data["alerts"]
    entity_peer_group = cfg.get("_entity_peer_group")
    if not entity_peer_group:
        return []

    peer_group_data = peer_dist.get(entity_peer_group, {})
    if len(peer_group_data) < cfg_get(cfg, "ns_002.min_peer_volume", 20):
        # Not enough peers to compare reliably
        pass

    entity_counts: dict[str, int] = defaultdict(int)
    for a in alerts:
        entity_counts[a.category] += 1

    out: list[FindingDraft] = []
    ratio_threshold = cfg_get(cfg, "ns_002.category_gap_ratio", 0.3)
    for cat, peer_count in peer_group_data.items():
        if peer_count < 5:
            continue
        # expected here: peer_median ratio scaled by this entity's alert volume
        # simple version: entity should have at least `ratio_threshold` fraction
        # of its peer's relative presence
        entity_count = entity_counts.get(cat, 0)
        peer_avg = peer_count / max(1, len(peer_dist))
        if entity_count < peer_avg * ratio_threshold:
            out.append(
                FindingDraft(
                    rule_id="NS-002",
                    category=FindingCategoryEnum.NEGATIVE_SPACE,
                    title=f"Alert category '{cat}' underrepresented vs peers",
                    narrative=(
                        f"This entity produced {entity_count} alerts in category "
                        f"'{cat}', while peer entities in the same group produced "
                        f"~{peer_avg:.1f} on average. This may indicate a detection "
                        f"gap or an undisclosed change in monitoring."
                    ),
                    expected_behavior=(
                        f"Category '{cat}' should appear at a rate comparable to "
                        f"peer entities."
                    ),
                    observed_pattern=f"{entity_count} alerts vs peer average ~{peer_avg:.1f}",
                    analytical_basis="Peer Category Coverage (rule NS-002)",
                    priority=PriorityEnum.MEDIUM,
                    confidence=0.55,
                    indicator=5.0,
                    metrics={
                        "category": cat,
                        "entity_count": entity_count,
                        "peer_average": round(peer_avg, 2),
                    },
                    evidence=[],
                )
            )
        if len(out) >= 3:
            break
    return out


def ns_003_critical_without_investigation(data: dict, cfg: dict) -> list[FindingDraft]:
    """NS-003: Critical alerts whose linked case has no investigation record."""
    if not cfg_get(cfg, "ns_003.critical_without_investigation"):
        return []

    alerts: list[Alert] = data["alerts"]
    cases: list[Case] = data["cases"]
    investigations: list[Investigation] = data["investigations"]

    inv_case_ids = {i.case_id for i in investigations}
    case_by_alert = {c.alert_id: c for c in cases if c.alert_id}

    out: list[FindingDraft] = []
    for a in alerts:
        if a.severity != SeverityEnum.CRITICAL:
            continue
        case = case_by_alert.get(a.id)
        if case is None:
            continue
        if case.id in inv_case_ids:
            continue
        out.append(
            FindingDraft(
                rule_id="NS-003",
                category=FindingCategoryEnum.NEGATIVE_SPACE,
                title="Critical alert without investigation evidence",
                narrative=(
                    f"Alert {a.external_id} (CRITICAL) is linked to case "
                    f"{case.external_id} but no investigation record exists for that case."
                ),
                expected_behavior=(
                    "Critical alerts should have investigation evidence attached "
                    "to their case."
                ),
                observed_pattern="0 investigation records for linked case",
                analytical_basis="Critical Investigation Coverage (rule NS-003)",
                priority=PriorityEnum.HIGH,
                confidence=0.75,
                indicator=9.0,
                metrics={"severity": "CRITICAL"},
                evidence=[
                    {"record_type": "alert", "record_id": a.id,
                     "snippet": a.external_id, "weight": 1.0},
                    {"record_type": "case", "record_id": case.id,
                     "snippet": case.external_id, "weight": 1.0},
                ],
            )
        )
        if len(out) >= 15:
            break
    return out


def ns_004_critical_without_escalation(data: dict, cfg: dict) -> list[FindingDraft]:
    """NS-004: Critical cases without escalation evidence."""
    if not cfg_get(cfg, "ns_004.critical_without_escalation"):
        return []

    cases: list[Case] = data["cases"]
    escalations: list[Escalation] = data["escalations"]
    escal_by_case = {e.case_id for e in escalations}

    out: list[FindingDraft] = []
    for c in cases:
        if c.severity != SeverityEnum.CRITICAL:
            continue
        if c.id in escal_by_case:
            continue
        out.append(
            FindingDraft(
                rule_id="NS-004",
                category=FindingCategoryEnum.NEGATIVE_SPACE,
                title="Missing escalation evidence for critical case",
                narrative=(
                    f"Case {c.external_id} is CRITICAL but has no escalation record. "
                    f"Expected evidence of escalation to senior reviewer is missing."
                ),
                expected_behavior="Escalation record for critical case.",
                observed_pattern="No escalation record.",
                analytical_basis="Critical Escalation Coverage (rule NS-004)",
                priority=PriorityEnum.HIGH,
                confidence=0.8,
                indicator=10.0,
                metrics={"severity": "CRITICAL"},
                evidence=[
                    {"record_type": "case", "record_id": c.id,
                     "snippet": c.external_id, "weight": 1.0},
                ],
            )
        )
        if len(out) >= 15:
            break
    return out


def ns_005_low_activity_vs_history(data: dict, cfg: dict) -> list[FindingDraft]:
    """NS-005: Activity level far below the entity's own historical mean."""
    # In this first pass, "history" is approximated by the group's overall mean.
    # When multi-period data exists, replace this with a per-entity query.
    threshold = cfg_get(cfg, "ns_005.activity_ratio_threshold", 0.4)
    alerts: list[Alert] = data["alerts"]
    if not alerts:
        return []

    # Simplified: if entity is the smallest contributor and has < threshold * group mean
    # The orchestrator will inject "_group_mean_volume" when it has that.
    group_mean = cfg.get("_group_mean_volume")
    if group_mean is None or group_mean <= 0:
        return []

    this_count = len(alerts)
    ratio = this_count / group_mean
    if ratio >= threshold:
        return []

    return [
        FindingDraft(
            rule_id="NS-005",
            category=FindingCategoryEnum.NEGATIVE_SPACE,
            title="Monitoring activity below expected baseline",
            narrative=(
                f"This entity reported {this_count} alerts, which is {ratio:.0%} of "
                f"the peer-group mean ({group_mean:.0f}). Lower-than-expected activity "
                f"may indicate a monitoring reduction rather than a genuine decrease in "
                f"security events."
            ),
            expected_behavior="Activity near peer-group mean.",
            observed_pattern=f"{this_count} alerts ({ratio:.0%} of group mean)",
            analytical_basis="Activity-vs-Baseline Check (rule NS-005)",
            priority=PriorityEnum.MEDIUM,
            confidence=0.55,
            indicator=5.0,
            metrics={
                "entity_count": this_count,
                "group_mean": round(group_mean, 1),
                "ratio": round(ratio, 3),
            },
            evidence=[],
        )
    ]


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------
ALL_RULES = [
    ns_001_critical_assets_without_alerts,
    ns_002_missing_category_vs_peers,
    ns_003_critical_without_investigation,
    ns_004_critical_without_escalation,
    ns_005_low_activity_vs_history,
]


async def run_all(
    db: AsyncSession, *, entity_id: int, period_id: int, cfg: dict
) -> list[FindingDraft]:
    data = await _load(db, entity_id, period_id)
    drafts: list[FindingDraft] = []
    for rule in ALL_RULES:
        try:
            drafts.extend(rule(data, cfg))
        except Exception as exc:
            print(f"[negative_space] rule {rule.__name__} failed: {exc}")
    return drafts