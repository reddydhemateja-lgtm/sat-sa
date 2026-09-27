"""
Anomaly Detection.

Statistical, explainable rules — no black-box models.

Rules:
    AN-001  Alert volume vs entity's own historical baseline (robust z-score)
    AN-002  Percent-change vs prior-period volume
    AN-003  IQR-based outlier on closure time
    AN-004  Trend deviation in weekly alert volume
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from statistics import median, mean

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.config_loader import get as cfg_get
from app.analytics.framework import FindingDraft
from app.models.analytics import FindingCategoryEnum, PriorityEnum
from app.models.operational import Alert


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------
async def _load(db: AsyncSession, entity_id: int, period_id: int) -> list[Alert]:
    return (
        await db.execute(
            select(Alert).where(
                Alert.entity_id == entity_id, Alert.period_id == period_id
            )
        )
    ).scalars().all()


async def _historical_period_counts(
    db: AsyncSession, entity_id: int, current_period_id: int
) -> list[int]:
    """
    Count alerts for the same entity in prior periods.
    Returns a list of counts, oldest-first, excluding the current period.
    """
    from app.models.period import AssessmentPeriod

    periods = (
        await db.execute(select(AssessmentPeriod).order_by(AssessmentPeriod.start_date))
    ).scalars().all()
    counts: list[int] = []
    for p in periods:
        if p.id == current_period_id:
            continue
        c = (
            await db.execute(
                select(Alert).where(
                    Alert.entity_id == entity_id, Alert.period_id == p.id
                )
            )
        ).scalars().all()
        counts.append(len(c))
    return counts


# ---------------------------------------------------------------------------
# Utilities
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


def _iqr_bounds(series: list[float]) -> tuple[float, float, float, float]:
    """Return (q1, q3, iqr, lower_fence, upper_fence)."""
    s = sorted(series)
    n = len(s)

    def pct(p: float) -> float:
        k = (n - 1) * p
        f = int(k)
        c = min(f + 1, n - 1)
        if f == c:
            return s[f]
        return s[f] + (s[c] - s[f]) * (k - f)

    q1 = pct(0.25)
    q3 = pct(0.75)
    iqr = q3 - q1
    return q1, q3, iqr, q1 - 1.5 * iqr, q3 + 1.5 * iqr


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------
async def an_001_volume_zscore(
    db: AsyncSession, *, entity_id: int, period_id: int, cfg: dict
) -> list[FindingDraft]:
    """AN-001: Current alert volume vs entity's own history (robust z-score)."""
    z_thr = cfg_get(cfg, "anomaly.zscore_threshold", 3.0)
    min_periods = cfg_get(cfg, "anomaly.min_periods", 3)

    alerts = await _load(db, entity_id, period_id)
    current = len(alerts)
    history = await _historical_period_counts(db, entity_id, period_id)

    if len(history) < min_periods:
        return []

    z = _robust_zscore(current, history)
    if abs(z) < z_thr:
        return []

    med = median(history)
    direction = "above" if current > med else "below"
    pct = (current - med) / (med or 1)

    return [
        FindingDraft(
            rule_id="AN-001",
            category=FindingCategoryEnum.ANOMALY,
            title=f"Alert volume significantly {direction} historical baseline",
            narrative=(
                f"Current period alert volume ({current}) is {abs(z):.2f} robust "
                f"standard deviations {direction} the entity's historical baseline "
                f"(median={med:.0f}). Percent change vs median: {pct:+.1%}."
            ),
            expected_behavior=(
                "Alert volume should fall within the entity's historical range "
                "unless a documented change in operations has occurred."
            ),
            observed_pattern=f"Volume={current}, z={z:.2f}, median={med:.0f}",
            analytical_basis="Robust z-score on alert volume (rule AN-001)",
            priority=PriorityEnum.MEDIUM,
            confidence=0.6,
            indicator=6.0,
            metrics={
                "current": current,
                "median_history": med,
                "z_score": round(z, 3),
                "percent_change": round(pct, 3),
                "history_periods": len(history),
            },
            evidence=[],
        )
    ]


async def an_002_percent_change(
    db: AsyncSession, *, entity_id: int, period_id: int, cfg: dict
) -> list[FindingDraft]:
    """AN-002: Percent change vs prior period volume."""
    pct_thr = cfg_get(cfg, "anomaly.percent_change_threshold", 0.5)
    min_periods = cfg_get(cfg, "anomaly.min_periods", 3)

    alerts = await _load(db, entity_id, period_id)
    current = len(alerts)
    history = await _historical_period_counts(db, entity_id, period_id)
    if len(history) < min_periods:
        return []

    avg = mean(history)
    pct = (current - avg) / (avg or 1)
    if abs(pct) < pct_thr:
        return []

    direction = "increase" if pct > 0 else "decrease"
    return [
        FindingDraft(
            rule_id="AN-002",
            category=FindingCategoryEnum.ANOMALY,
            title=f"Alert volume {direction} of {abs(pct):.0%} vs historical mean",
            narrative=(
                f"Current period volume ({current}) is {abs(pct):.1%} "
                f"{'higher' if pct > 0 else 'lower'} than the entity's historical "
                f"mean ({avg:.0f})."
            ),
            expected_behavior="Volume within historical variance.",
            observed_pattern=f"Current={current}, mean={avg:.0f}, change={pct:+.1%}",
            analytical_basis="Percent-change vs historical mean (rule AN-002)",
            priority=PriorityEnum.LOW,
            confidence=0.55,
            indicator=4.0,
            metrics={
                "current": current,
                "historical_mean": round(avg, 1),
                "percent_change": round(pct, 3),
            },
            evidence=[],
        )
    ]


async def an_003_closure_iqr_outlier(
    db: AsyncSession, *, entity_id: int, period_id: int, cfg: dict
) -> list[FindingDraft]:
    """AN-003: Closure times outside 1.5×IQR fences."""
    alerts = await _load(db, entity_id, period_id)
    samples: list[tuple[Alert, float]] = []
    for a in alerts:
        if a.closed_at and a.detected_at:
            m = (a.closed_at - a.detected_at).total_seconds() / 60.0
            samples.append((a, m))

    if len(samples) < 20:
        return []

    series = [m for _, m in samples]
    q1, q3, iqr, lo, hi = _iqr_bounds(series)

    out: list[FindingDraft] = []
    for a, m in samples:
        if m < lo or m > hi:
            side = "below" if m < lo else "above"
            out.append(
                FindingDraft(
                    rule_id="AN-003",
                    category=FindingCategoryEnum.ANOMALY,
                    title=f"Closure time {side} expected IQR range",
                    narrative=(
                        f"Alert {a.external_id} closed in {m:.1f} minutes, outside "
                        f"the entity's expected range [{lo:.1f}, {hi:.1f}] "
                        f"(IQR-based)."
                    ),
                    expected_behavior="Closure time within IQR fences.",
                    observed_pattern=f"{m:.1f} min (fences: {lo:.1f}–{hi:.1f})",
                    analytical_basis="IQR outlier on closure time (rule AN-003)",
                    priority=PriorityEnum.LOW,
                    confidence=0.5,
                    indicator=3.0,
                    metrics={
                        "closure_minutes": round(m, 2),
                        "lower_fence": round(lo, 2),
                        "upper_fence": round(hi, 2),
                        "iqr": round(iqr, 2),
                    },
                    evidence=[
                        {"record_type": "alert", "record_id": a.id,
                         "snippet": a.external_id, "weight": 1.0},
                    ],
                )
            )
        if len(out) >= 8:
            break
    return out


async def an_004_weekly_trend_deviation(
    db: AsyncSession, *, entity_id: int, period_id: int, cfg: dict
) -> list[FindingDraft]:
    """AN-004: Weekly volume trend deviates from historical pattern."""
    alerts = await _load(db, entity_id, period_id)
    if len(alerts) < 30:
        return []

    weeks: dict[tuple[int, int], int] = defaultdict(int)
    for a in alerts:
        iso_year, iso_week, _ = a.detected_at.isocalendar()
        weeks[(iso_year, iso_week)] += 1

    # sort by (year, week)
    ordered = [count for _, count in sorted(weeks.items())]
    if len(ordered) < 4:
        return []

    overall_avg = mean(ordered)
    # flag any week below 30% of the average
    out: list[FindingDraft] = []
    for i, count in enumerate(ordered):
        if count >= overall_avg * 0.3:
            continue
        out.append(
            FindingDraft(
                rule_id="AN-004",
                category=FindingCategoryEnum.ANOMALY,
                title="Weekly alert volume dropped significantly",
                narrative=(
                    f"During week index {i + 1}, this entity produced {count} alerts — "
                    f"far below its own weekly average of {overall_avg:.1f}. This may "
                    f"indicate reduced monitoring, a sensor outage, or a genuine lull."
                ),
                expected_behavior="Weekly volume near the entity's own average.",
                observed_pattern=f"Week {i + 1}: {count} alerts (avg {overall_avg:.1f})",
                analytical_basis="Weekly trend deviation (rule AN-004)",
                priority=PriorityEnum.MEDIUM,
                confidence=0.5,
                indicator=4.0,
                metrics={
                    "week_index": i + 1,
                    "count": count,
                    "avg": round(overall_avg, 1),
                },
                evidence=[],
            )
        )
        if len(out) >= 4:
            break
    return out


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------
ALL_RULES = [
    an_001_volume_zscore,
    an_002_percent_change,
    an_003_closure_iqr_outlier,
    an_004_weekly_trend_deviation,
]


async def run_all(
    db: AsyncSession, *, entity_id: int, period_id: int, cfg: dict
) -> list[FindingDraft]:
    drafts: list[FindingDraft] = []
    for rule in ALL_RULES:
        try:
            drafts.extend(
                await rule(db, entity_id=entity_id, period_id=period_id, cfg=cfg)
            )
        except Exception as exc:
            print(f"[anomaly_detection] rule {rule.__name__} failed: {exc}")
    return drafts