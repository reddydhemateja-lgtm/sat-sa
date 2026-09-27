"""
Execution Gap Detection.

Rules EG-001 … EG-007 identify operational patterns where the expected
investigation, escalation, or documentation evidence appears to be
missing or superficial — indicators for supervisory review, not verdicts.

Terminology: every finding is phrased as a "potential execution gap",
"indicator identified", or "requires supervisory review". No blame is
assigned to the entity.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from statistics import median

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.config_loader import get as cfg_get
from app.analytics.framework import FindingDraft
from app.models.analytics import FindingCategoryEnum, PriorityEnum
from app.models.operational import (
    Alert,
    AlertDisposition,
    Case,
    Escalation,
    Investigation,
    SeverityEnum,
)


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------
async def _load_entity_data(db: AsyncSession, entity_id: int, period_id: int) -> dict:
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

    alert_ids = [a.id for a in alerts]
    dispositions = []
    if alert_ids:
        dispositions = (
            await db.execute(
                select(AlertDisposition).where(AlertDisposition.alert_id.in_(alert_ids))
            )
        ).scalars().all()

    return {
        "alerts": alerts,
        "cases": cases,
        "investigations": investigations,
        "escalations": escalations,
        "dispositions": dispositions,
    }


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------
def _robust_zscore(value: float, series: list[float]) -> float:
    if len(series) < 3:
        return 0.0
    med = median(series)
    deviations = [abs(x - med) for x in series]
    mad = median(deviations)
    if mad == 0:
        return 0.0
    return 0.6745 * (value - med) / mad


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------
def eg_001_critical_fast_closure_without_escalation(
    data: dict, cfg: dict
) -> list[FindingDraft]:
    """EG-001: Critical alerts closed faster than threshold with no escalation."""
    threshold_min = cfg_get(cfg, "eg_001.critical_closure_minutes")
    alerts: list[Alert] = data["alerts"]
    cases: list[Case] = data["cases"]
    escalations: list[Escalation] = data["escalations"]

    # map alert_id -> case -> any escalation?
    escal_by_case = {e.case_id for e in escalations}
    case_by_alert = {c.alert_id: c for c in cases if c.alert_id}

    out: list[FindingDraft] = []
    for a in alerts:
        if a.severity != SeverityEnum.CRITICAL or not a.closed_at:
            continue
        delta_min = (a.closed_at - a.detected_at).total_seconds() / 60.0
        if delta_min >= threshold_min:
            continue
        case = case_by_alert.get(a.id)
        has_escalation = case is not None and case.id in escal_by_case
        if has_escalation:
            continue

        out.append(
            FindingDraft(
                rule_id="EG-001",
                category=FindingCategoryEnum.EXECUTION_GAP,
                title="Critical alert closed unusually quickly without escalation evidence",
                narrative=(
                    f"Alert {a.external_id} ({a.category}) was closed in "
                    f"{delta_min:.1f} minutes with no escalation record. "
                    f"Configured threshold: {threshold_min} minutes."
                ),
                expected_behavior=(
                    "Critical alerts closed within the fast-closure window "
                    "should contain escalation evidence."
                ),
                observed_pattern=f"Closure time {delta_min:.1f} min; escalations=0",
                analytical_basis="Critical Alert Escalation Check (rule EG-001)",
                priority=PriorityEnum.HIGH,
                confidence=0.85,
                indicator=12.0,
                metrics={
                    "closure_minutes": round(delta_min, 2),
                    "threshold_minutes": threshold_min,
                    "severity": a.severity.value,
                },
                evidence=[
                    {
                        "record_type": "alert",
                        "record_id": a.id,
                        "snippet": f"{a.external_id} — {a.title}",
                        "weight": 1.0,
                    }
                ],
            )
        )
    return out


def eg_002_acknowledged_without_investigation(
    data: dict, cfg: dict
) -> list[FindingDraft]:
    """EG-002: Alerts acknowledged but no investigation record within window."""
    window_min = cfg_get(cfg, "eg_002.investigation_window_minutes")
    alerts: list[Alert] = data["alerts"]
    cases: list[Case] = data["cases"]
    investigations: list[Investigation] = data["investigations"]

    inv_by_case = {i.case_id: i for i in investigations}
    case_by_alert = {c.alert_id: c for c in cases if c.alert_id}

    out: list[FindingDraft] = []
    for a in alerts:
        if a.severity not in (SeverityEnum.CRITICAL, SeverityEnum.HIGH):
            continue
        if not a.acknowledged_at:
            continue
        case = case_by_alert.get(a.id)
        if case is None:
            continue
        inv = inv_by_case.get(case.id)
        if inv is None:
            out.append(
                FindingDraft(
                    rule_id="EG-002",
                    category=FindingCategoryEnum.EXECUTION_GAP,
                    title="High-severity alert acknowledged without investigation record",
                    narrative=(
                        f"Alert {a.external_id} ({a.severity.value}) was acknowledged "
                        f"and linked to case {case.external_id}, but no investigation "
                        f"record exists for the case."
                    ),
                    expected_behavior=(
                        "High and critical severity alerts should have an associated "
                        "investigation record."
                    ),
                    observed_pattern="0 investigation records for case",
                    analytical_basis="Acknowledgement-to-Investigation Check (rule EG-002)",
                    priority=PriorityEnum.HIGH,
                    confidence=0.8,
                    indicator=10.0,
                    metrics={"severity": a.severity.value},
                    evidence=[
                        {"record_type": "alert", "record_id": a.id,
                         "snippet": a.external_id, "weight": 1.0},
                        {"record_type": "case", "record_id": case.id,
                         "snippet": case.external_id, "weight": 1.0},
                    ],
                )
            )
    return out


def eg_003_critical_case_without_escalation(
    data: dict, cfg: dict
) -> list[FindingDraft]:
    """EG-003: Critical cases without any escalation record."""
    if not cfg_get(cfg, "eg_003.require_escalation_for_critical"):
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
                rule_id="EG-003",
                category=FindingCategoryEnum.EXECUTION_GAP,
                title="Critical case without escalation record",
                narrative=(
                    f"Case {c.external_id} is marked CRITICAL but has no escalation "
                    f"record. Expected behaviour for critical severity is documented "
                    f"escalation to a senior reviewer."
                ),
                expected_behavior="Critical cases should have an escalation record.",
                observed_pattern="Escalation count = 0",
                analytical_basis="Critical Case Escalation Check (rule EG-003)",
                priority=PriorityEnum.HIGH,
                confidence=0.9,
                indicator=14.0,
                metrics={"severity": c.severity.value},
                evidence=[
                    {"record_type": "case", "record_id": c.id,
                     "snippet": c.external_id, "weight": 1.0},
                ],
            )
        )
    return out


def eg_004_repeated_category_without_investigation(
    data: dict, cfg: dict
) -> list[FindingDraft]:
    """EG-004: Same category repeats on same asset without investigations."""
    min_occ = cfg_get(cfg, "eg_004.repeat_category_min_occurrences")
    alerts: list[Alert] = data["alerts"]
    cases: list[Case] = data["cases"]
    investigations: list[Investigation] = data["investigations"]

    inv_case_ids = {i.case_id for i in investigations}
    case_by_alert = {c.alert_id: c for c in cases if c.alert_id}

    groups: dict[tuple[int | None, str], list[Alert]] = defaultdict(list)
    for a in alerts:
        if a.severity not in (SeverityEnum.CRITICAL, SeverityEnum.HIGH):
            continue
        groups[(a.asset_id, a.category)].append(a)

    out: list[FindingDraft] = []
    for (asset_id, category), group in groups.items():
        if len(group) < min_occ:
            continue
        with_inv = sum(
            1 for a in group
            if (c := case_by_alert.get(a.id)) and c.id in inv_case_ids
        )
        if with_inv > 0:
            continue
        out.append(
            FindingDraft(
                rule_id="EG-004",
                category=FindingCategoryEnum.EXECUTION_GAP,
                title="Repeated alert category without corresponding investigation",
                narrative=(
                    f"{len(group)} alerts of category '{category}' were observed on "
                    f"the same asset, none of which led to an investigation record."
                ),
                expected_behavior=(
                    "Repeated high-severity alerts of the same category should "
                    "trigger investigation activity."
                ),
                observed_pattern=f"{len(group)} alerts; 0 investigations",
                analytical_basis="Repeated-Category Investigation Check (rule EG-004)",
                priority=PriorityEnum.MEDIUM,
                confidence=0.7,
                indicator=8.0,
                metrics={
                    "category": category,
                    "asset_id": asset_id,
                    "occurrences": len(group),
                },
                evidence=[
                    {"record_type": "alert", "record_id": a.id,
                     "snippet": a.external_id, "weight": 1.0}
                    for a in group[:10]
                ],
            )
        )
    return out


def eg_005_template_investigations(data: dict, cfg: dict) -> list[FindingDraft]:
    """EG-005: Investigations sharing an identical content hash."""
    min_group = cfg_get(cfg, "eg_005.template_min_group")
    investigations: list[Investigation] = data["investigations"]

    groups: dict[str, list[Investigation]] = defaultdict(list)
    for i in investigations:
        if i.content_hash:
            groups[i.content_hash].append(i)

    out: list[FindingDraft] = []
    for h, items in groups.items():
        if len(items) < min_group:
            continue
        out.append(
            FindingDraft(
                rule_id="EG-005",
                category=FindingCategoryEnum.EXECUTION_GAP,
                title="Repetitive investigation records detected",
                narrative=(
                    f"{len(items)} investigation records share identical content "
                    f"(hash {h[:12]}…). This may indicate template-driven "
                    f"documentation rather than case-specific investigation."
                ),
                expected_behavior=(
                    "Investigation records should contain case-specific analysis, "
                    "not identical boilerplate."
                ),
                observed_pattern=f"{len(items)} records with identical content_hash",
                analytical_basis="Template-Content Detection (rule EG-005)",
                priority=PriorityEnum.MEDIUM if len(items) < 10 else PriorityEnum.HIGH,
                confidence=0.7,
                indicator=8.0,
                metrics={"group_size": len(items), "content_hash": h},
                evidence=[
                    {"record_type": "investigation", "record_id": i.id,
                     "snippet": (i.summary or "")[:160], "weight": 1.0}
                    for i in items[:20]
                ],
            )
        )
    return out


def eg_006_closure_time_outlier(data: dict, cfg: dict) -> list[FindingDraft]:
    """EG-006: Closure time is a robust-z outlier vs entity's own alerts."""
    z_thr = cfg_get(cfg, "eg_006.closure_z_threshold")
    min_history = cfg_get(cfg, "eg_006.min_history")
    alerts: list[Alert] = data["alerts"]

    # compute entity baseline of closure minutes for CLOSED alerts
    samples: list[tuple[Alert, float]] = []
    for a in alerts:
        if a.closed_at and a.detected_at:
            delta_min = (a.closed_at - a.detected_at).total_seconds() / 60.0
            samples.append((a, delta_min))

    if len(samples) < min_history:
        return []

    series = [m for _, m in samples]
    out: list[FindingDraft] = []
    for a, m in samples:
        z = _robust_zscore(m, series)
        if abs(z) < z_thr:
            continue
        direction = "above" if z > 0 else "below"
        out.append(
            FindingDraft(
                rule_id="EG-006",
                category=FindingCategoryEnum.EXECUTION_GAP,
                title=f"Alert closure time significantly {direction} entity baseline",
                narrative=(
                    f"Alert {a.external_id} closed in {m:.1f} minutes, which is "
                    f"{abs(z):.2f} robust standard deviations {direction} the entity's "
                    f"own closure baseline."
                ),
                expected_behavior=(
                    "Alert closure times should fall within the entity's own "
                    "statistical distribution of closure times."
                ),
                observed_pattern=f"Closure time {m:.1f} min; z={z:.2f}",
                analytical_basis="Robust z-score on closure time (rule EG-006)",
                priority=PriorityEnum.MEDIUM,
                confidence=0.65,
                indicator=6.0,
                metrics={"closure_minutes": round(m, 2), "z_score": round(z, 3)},
                evidence=[
                    {"record_type": "alert", "record_id": a.id,
                     "snippet": a.external_id, "weight": 1.0},
                ],
            )
        )
        if len(out) >= 10:      # cap to avoid flooding
            break
    return out


def eg_007_true_positive_fast_close(data: dict, cfg: dict) -> list[FindingDraft]:
    """EG-007: TRUE_POSITIVE disposition closed faster than threshold."""
    threshold_min = cfg_get(cfg, "eg_007.true_positive_fast_close_minutes")
    alerts: list[Alert] = data["alerts"]
    dispositions: list[AlertDisposition] = data["dispositions"]

    disp_by_alert = {d.alert_id: d for d in dispositions}
    out: list[FindingDraft] = []
    for a in alerts:
        d = disp_by_alert.get(a.id)
        if d is None:
            continue
        if d.disposition.upper() != "TRUE_POSITIVE":
            continue
        if not a.closed_at:
            continue
        delta_min = (a.closed_at - a.detected_at).total_seconds() / 60.0
        if delta_min >= threshold_min:
            continue
        out.append(
            FindingDraft(
                rule_id="EG-007",
                category=FindingCategoryEnum.EXECUTION_GAP,
                title="TRUE_POSITIVE disposition closed unusually quickly",
                narrative=(
                    f"Alert {a.external_id} was dispositioned as TRUE_POSITIVE but "
                    f"closed in {delta_min:.1f} minutes, below the threshold of "
                    f"{threshold_min} minutes for meaningful remediation."
                ),
                expected_behavior=(
                    "TRUE_POSITIVE dispositions typically require investigation "
                    "and remediation that exceed the fast-closure window."
                ),
                observed_pattern=f"Closure {delta_min:.1f} min; disposition=TRUE_POSITIVE",
                analytical_basis="TRUE_POSITIVE Fast-Closure Check (rule EG-007)",
                priority=PriorityEnum.HIGH,
                confidence=0.75,
                indicator=9.0,
                metrics={"closure_minutes": round(delta_min, 2)},
                evidence=[
                    {"record_type": "alert", "record_id": a.id,
                     "snippet": a.external_id, "weight": 1.0},
                ],
            )
        )
    return out


# ---------------------------------------------------------------------------
# Rule runner
# ---------------------------------------------------------------------------
ALL_RULES = [
    eg_001_critical_fast_closure_without_escalation,
    eg_002_acknowledged_without_investigation,
    eg_003_critical_case_without_escalation,
    eg_004_repeated_category_without_investigation,
    eg_005_template_investigations,
    eg_006_closure_time_outlier,
    eg_007_true_positive_fast_close,
]


async def run_all(
    db: AsyncSession, *, entity_id: int, period_id: int, cfg: dict
) -> list[FindingDraft]:
    data = await _load_entity_data(db, entity_id, period_id)
    drafts: list[FindingDraft] = []
    for rule in ALL_RULES:
        try:
            drafts.extend(rule(data, cfg))
        except Exception as exc:      # never let one rule break the batch
            print(f"[execution_gaps] rule {rule.__name__} failed: {exc}")
    return drafts