"""
Threshold configuration for analytics rules.

Values come from the AnalyticsConfig table when present, otherwise from
the DEFAULTS dict below. This keeps Phase 3 self-contained while leaving
the door open for Phase 7 (admin UI on top of the same table).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reporting import AnalyticsConfig


# ---------------------------------------------------------------------------
# Hardcoded fallback defaults
# ---------------------------------------------------------------------------
DEFAULTS: dict[str, Any] = {
    # --- Execution gap rules ---
    "eg_001.critical_closure_minutes": 15,       # critical alerts closed faster than this w/o escalation
    "eg_002.investigation_window_minutes": 240,  # max acceptable gap between ack and investigation
    "eg_003.require_escalation_for_critical": True,
    "eg_004.repeat_category_min_occurrences": 5, # same category on same asset, no investigations
    "eg_005.template_min_group": 3,              # min content-hash collisions to flag
    "eg_006.closure_z_threshold": 2.5,           # robust z-score
    "eg_006.min_history": 10,                    # minimum alerts to compute entity baseline
    "eg_007.true_positive_fast_close_minutes": 5,

    # --- Negative space rules ---
    "ns_001.critical_assets_min": 1,             # apply to assets with criticality in {CRITICAL,HIGH}
    "ns_002.min_peer_volume": 20,                # require min peers to compare categories
    "ns_002.category_gap_ratio": 0.3,            # flag if entity ratio < peer_median * ratio
    "ns_003.critical_without_investigation": True,
    "ns_004.critical_without_escalation": True,
    "ns_005.activity_ratio_threshold": 0.4,      # flag if entity activity < 40% of its own historical mean

    # --- Anomaly detection ---
    "anomaly.zscore_threshold": 3.0,             # |z| >= this -> flag
    "anomaly.percent_change_threshold": 0.5,     # |pct| >= this -> flag
    "anomaly.min_periods": 3,                    # need at least N prior periods

    # --- Peer comparison ---
    "peer.min_sample_size": 3,                   # require at least N peers
    "peer.z_score_threshold": 2.0,

    # --- Review indicator weights ---
    "indicator.weight_execution_gap": 0.35,
    "indicator.weight_negative_space": 0.25,
    "indicator.weight_anomaly": 0.20,
    "indicator.weight_peer_deviation": 0.10,
    "indicator.weight_evidence_completeness": 0.10,

    # --- Prioritization cutoffs ---
    "priority.high_threshold": 70.0,
    "priority.medium_threshold": 40.0,
}


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------
async def load_config(db: AsyncSession) -> dict[str, Any]:
    """
    Return the merged config: DB values override DEFAULTS.
    """
    config = dict(DEFAULTS)
    result = await db.execute(select(AnalyticsConfig))
    for row in result.scalars().all():
        config[row.key] = row.value
    return config


def get(cfg: dict[str, Any], key: str, fallback: Any | None = None) -> Any:
    """Helper with a per-key fallback (falls back to DEFAULTS, then to `fallback`)."""
    if key in cfg:
        return cfg[key]
    if key in DEFAULTS:
        return DEFAULTS[key]
    return fallback