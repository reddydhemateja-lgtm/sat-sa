"""
Column mapping for real CSE submissions.

A CSE's CSV/JSON may not use our canonical column names. This module:
    - Detects likely matches between incoming columns and our schema.
    - Produces a suggested mapping the supervisor can accept or override.
    - Applies a mapping by renaming the dataframe's columns.

The alias tables below cover common SIEM / case-management / ticket-system
column names we expect to see in the wild.
"""

from __future__ import annotations

import re
from typing import Any

import pandas as pd

from app.ingestion.schemas import PAYLOAD_SCHEMAS, ColumnSpec


# ---------------------------------------------------------------------------
# Alias tables — one entry per canonical column, listing common synonyms
# ---------------------------------------------------------------------------
ALIASES: dict[str, set[str]] = {
    "code": {"code", "entity_code", "org_code", "organization_code", "cse_code", "short_code"},
    "name": {"name", "entity_name", "org_name", "organization_name", "cse_name", "full_name"},
    "sector": {"sector", "industry", "vertical"},
    "sub_sector": {"sub_sector", "subsector", "sub_industry"},
    "region": {"region", "zone", "geography", "geo"},
    "criticality": {"criticality", "criticality_level", "critical_level", "importance"},
    "peer_group": {"peer_group", "peergroup", "peer", "group"},

    "asset_code": {"asset_code", "asset_id", "host_id", "device_id", "system_id", "machine_id"},
    "hostname": {"hostname", "host", "host_name", "device_name", "machine_name"},
    "asset_type": {"asset_type", "device_type", "host_type", "system_type", "kind"},
    "tags": {"tags", "labels", "attributes"},

    "external_id": {
        "external_id", "alert_id", "id", "alert_ref", "ticket_id",
        "incident_id", "case_id_external", "event_id", "alert_key",
    },
    "title": {"title", "summary", "short_description", "name", "alert_name", "headline"},
    "description": {"description", "long_description", "details", "message", "notes"},
    "severity": {
        "severity", "severity_level", "priority", "risk_level", "impact",
        "urgency", "criticallity", "level",
    },
    "category": {
        "category", "alert_type", "rule_name", "classification", "event_type",
        "type", "attack_type", "signature",
    },
    "source_system": {
        "source_system", "source", "sensor", "detection_system", "product", "tool",
    },
    "detected_at": {
        "detected_at", "detected", "created_at", "event_time", "timestamp",
        "first_seen", "occurred_at", "start_time", "date_created",
    },
    "acknowledged_at": {
        "acknowledged_at", "acknowledged", "ack_time", "assigned_at",
        "first_response_at", "acknowledged_on",
    },
    "closed_at": {
        "closed_at", "closed", "resolved_at", "close_time", "date_closed",
        "end_time", "resolution_time",
    },
    "status": {
        "status", "state", "alert_status", "resolution", "case_status",
        "current_state",
    },

    "alert_external_id": {
        "alert_external_id", "alert_id", "linked_alert", "parent_alert", "origin_alert",
    },
    "opened_at": {"opened_at", "opened", "open_time", "date_opened", "started_at"},
    "assigned_to": {
        "assigned_to", "analyst", "owner", "handler", "investigator",
        "assigned_analyst",
    },

    "case_external_id": {"case_external_id", "case_id", "linked_case", "parent_case"},
    "investigator": {"investigator", "analyst", "owner", "handler", "author"},
    "started_at": {"started_at", "started", "start_time", "begin_time"},
    "ended_at": {"ended_at", "ended", "end_time", "completed_at", "finished_at"},
    "summary": {"summary", "findings", "notes", "conclusion", "narrative"},
    "evidence_notes": {"evidence_notes", "evidence", "artifacts_notes"},
    "artifacts_count": {"artifacts_count", "artifact_count", "num_artifacts"},
    "content_hash": {"content_hash", "hash", "signature_hash"},

    "escalated_at": {"escalated_at", "escalation_time", "escalated_on"},
    "escalated_to": {"escalated_to", "escalated_team", "escalated_group", "assigned_team"},
    "level": {"level", "escalation_level", "tier"},

    "disposition": {"disposition", "resolution", "outcome", "classification_result"},
    "rationale": {"rationale", "reason", "justification", "comment"},
    "closed_by": {"closed_by", "resolver", "closer", "handled_by"},
    "closure_seconds": {"closure_seconds", "seconds_to_close", "handle_time"},
}


def _norm(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[\s\-\.]+", "_", s)
    s = re.sub(r"[^a-z0-9_]", "", s)
    return s


def _score(incoming: str, canonical: str) -> int:
    a = _norm(incoming)
    b = _norm(canonical)

    if a == b:
        return 100

    aliases = ALIASES.get(canonical, set())
    if a in {_norm(x) for x in aliases}:
        return 90

    if len(a) >= 4 and a in b:
        return 70
    if len(b) >= 4 and b in a:
        return 65

    a_tokens = set(a.split("_"))
    b_tokens = set(b.split("_"))
    if a_tokens & b_tokens:
        return 55

    return 0


def suggest_mapping(
    incoming_columns: list[str], payload_type: str
) -> dict[str, str | None]:
    schema = PAYLOAD_SCHEMAS[payload_type]
    canonical_specs: list[ColumnSpec] = schema["columns"]

    mapping: dict[str, str | None] = {}
    used_incoming: set[str] = set()

    ordered = sorted(canonical_specs, key=lambda c: (not c.required, c.name))

    for spec in ordered:
        best_col: str | None = None
        best_score = 0
        for incoming in incoming_columns:
            if incoming in used_incoming:
                continue
            sc = _score(incoming, spec.name)
            if sc > best_score:
                best_score = sc
                best_col = incoming
        if best_score >= 55:
            mapping[spec.name] = best_col
            if best_col:
                used_incoming.add(best_col)
        else:
            mapping[spec.name] = None

    return mapping


def apply_mapping(
    df: pd.DataFrame, mapping: dict[str, str | None]
) -> pd.DataFrame:
    reverse: dict[str, str] = {
        v: k for k, v in mapping.items() if v is not None
    }
    keep_cols = [c for c in df.columns if c in reverse]
    renamed = df[keep_cols].rename(columns=reverse)

    for canonical in mapping.keys():
        if canonical not in renamed.columns:
            renamed[canonical] = ""
    return renamed