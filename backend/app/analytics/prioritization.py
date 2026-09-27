"""
Prioritization.

Ranks findings for supervisory review. The rank is a review priority —
NOT a final security verdict.
"""

from __future__ import annotations

from app.analytics.config_loader import get as cfg_get
from app.analytics.framework import FindingDraft
from app.models.analytics import PriorityEnum


# Base score per category, weighted by confidence.
_CATEGORY_BASE = {
    "EXECUTION_GAP": 40.0,
    "NEGATIVE_SPACE": 30.0,
    "ANOMALY": 20.0,
    "PEER_DEVIATION": 15.0,
    "DATA_QUALITY": 10.0,
}


def score_finding(d: FindingDraft) -> float:
    """Compute a raw review-priority score for a single finding."""
    base = _CATEGORY_BASE.get(d.category.value, 20.0)
    # indicator already reflects severity; confidence reflects how strong the signal is
    raw = base + float(d.indicator) * (0.5 + 0.5 * float(d.confidence))
    # evidence volume gives a small boost
    raw += min(len(d.evidence), 10) * 1.0
    return raw


def prioritize(d: FindingDraft, cfg: dict) -> PriorityEnum:
    """
    Return the assigned priority for a finding, taking into account both
    the raw score and the configured cutoffs.
    """
    raw = score_finding(d)
    high = cfg_get(cfg, "priority.high_threshold", 70.0)
    medium = cfg_get(cfg, "priority.medium_threshold", 40.0)

    if raw >= high:
        return PriorityEnum.HIGH
    if raw >= medium:
        return PriorityEnum.MEDIUM
    if raw >= 20.0:
        return PriorityEnum.LOW
    return PriorityEnum.INFORMATIONAL


def apply_priorities(drafts: list[FindingDraft], cfg: dict) -> None:
    """Mutate each draft in place, setting priority from its score."""
    for d in drafts:
        d.priority = prioritize(d, cfg)