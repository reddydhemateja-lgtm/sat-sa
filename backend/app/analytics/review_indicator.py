"""
Supervisory Review Indicator.

Combines the contributions of execution-gap, negative-space, anomaly, and
peer-deviation findings into a 0–100 indicator per entity, plus an
evidence-completeness component.

This is NOT a security risk score. It prioritizes supervisory review —
nothing more.
"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from app.analytics.config_loader import get as cfg_get
from app.analytics.framework import FindingDraft
from app.models.analytics import FindingCategoryEnum


def compute_entity_indicator(
    drafts: list[FindingDraft], cfg: dict
) -> dict:
    """
    Given all finding drafts for one entity+period, return:
        {
            "score": 0-100,
            "contributions": {
                "execution_gap": float,
                "negative_space": float,
                "anomaly": float,
                "peer_deviation": float,
                "evidence_completeness": float,
            },
            "counts": {"EXECUTION_GAP": n, "NEGATIVE_SPACE": n, ...},
        }
    """
    # Per-category raw sums of the draft `indicator` values
    raw: dict[FindingCategoryEnum, float] = defaultdict(float)
    counts: dict[str, int] = defaultdict(int)
    for d in drafts:
        raw[d.category] += float(d.indicator)
        counts[d.category.value] += 1

    eg = raw.get(FindingCategoryEnum.EXECUTION_GAP, 0.0)
    ns = raw.get(FindingCategoryEnum.NEGATIVE_SPACE, 0.0)
    an = raw.get(FindingCategoryEnum.ANOMALY, 0.0)
    pd = raw.get(FindingCategoryEnum.PEER_DEVIATION, 0.0)

    # Evidence completeness: fraction of findings that have at least one evidence row.
    # Entities with findings but no evidence get a small penalty.
    with_evidence = sum(1 for d in drafts if d.evidence)
    completeness_penalty = 0.0
    if drafts:
        completeness_ratio = with_evidence / len(drafts)
        # 100% coverage → 0 penalty; 0% coverage → up to 10 penalty
        completeness_penalty = (1.0 - completeness_ratio) * 10.0

    weights = {
        "execution_gap": cfg_get(cfg, "indicator.weight_execution_gap", 0.35),
        "negative_space": cfg_get(cfg, "indicator.weight_negative_space", 0.25),
        "anomaly": cfg_get(cfg, "indicator.weight_anomaly", 0.20),
        "peer_deviation": cfg_get(cfg, "indicator.weight_peer_deviation", 0.10),
    }

    # Raw contribution before normalization
    contributions = {
        "execution_gap": eg * weights["execution_gap"],
        "negative_space": ns * weights["negative_space"],
        "anomaly": an * weights["anomaly"],
        "peer_deviation": pd * weights["peer_deviation"],
        "evidence_completeness": completeness_penalty,
    }

    # Normalize to 0–100 with saturating scale.
    # Reference maximum: 100. Beyond that, clip.
    raw_total = sum(contributions.values())
    score = min(100.0, raw_total)

    return {
        "score": round(score, 2),
        "raw_total": round(raw_total, 2),
        "contributions": {k: round(v, 2) for k, v in contributions.items()},
        "counts": dict(counts),
    }