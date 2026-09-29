"""
Tests for negative-space classification logic (spec §16).

Missing data must NOT be treated as a cybersecurity failure without
first ruling out a submission problem.
"""

from __future__ import annotations

from app.analytics.negative_space import _classify_ns


def test_no_data_means_submission_quality():
    result = _classify_ns({"alerts": [], "cases": []}, {}, "NS-003")
    assert result == "SUBMISSION_QUALITY"


def test_no_alerts_and_no_cases_means_submission_quality():
    result = _classify_ns({"alerts": [], "cases": []}, {}, "NS-004")
    assert result == "SUBMISSION_QUALITY"


def test_data_present_means_evidence_gap():
    result = _classify_ns(
        {"alerts": [object()], "cases": [object()]}, {}, "NS-003"
    )
    assert result == "EVIDENCE_GAP"


def test_low_completeness_overrides():
    cfg = {"_entity_submission_completeness": 0.3}
    result = _classify_ns(
        {"alerts": [object()], "cases": [object()]}, cfg, "NS-003"
    )
    assert result == "SUBMISSION_QUALITY"


def test_persistent_pattern_escalates():
    cfg = {"_entity_persistent_rules": {"NS-003"}}
    result = _classify_ns(
        {"alerts": [object()], "cases": [object()]}, cfg, "NS-003"
    )
    assert result == "SUPERVISORY_FINDING"


def test_non_asset_rule_defaults_to_evidence_gap():
    # NS-002 (peer-based) should not be classified as submission quality
    # just because alerts list is empty.
    result = _classify_ns({"alerts": [object()], "cases": [object()]}, {}, "NS-002")
    assert result == "EVIDENCE_GAP"