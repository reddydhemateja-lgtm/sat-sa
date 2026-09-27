"""
Payload schemas for ingestion.

Each entry describes one CSV/JSON/XLSX payload type:
    - required columns
    - which columns carry datetimes
    - value restrictions (enums, non-negative integers, ...)

The pipeline reads these definitions and applies them uniformly.
"""

from __future__ import annotations

from typing import Any, Literal

PayloadType = Literal[
    "entities",
    "assets",
    "alerts",
    "cases",
    "investigations",
    "escalations",
    "dispositions",
]


class ColumnSpec:
    __slots__ = ("name", "required", "kind", "enum")

    def __init__(
        self,
        name: str,
        *,
        required: bool = False,
        kind: Literal["str", "int", "float", "datetime", "bool"] = "str",
        enum: set[str] | None = None,
    ) -> None:
        self.name = name
        self.required = required
        self.kind = kind
        self.enum = enum


PAYLOAD_SCHEMAS: dict[str, dict[str, Any]] = {
    # ---------------------------------------------------------------- entities
    "entities": {
        "description": "CSE organisation master data",
        "columns": [
            ColumnSpec("code", required=True),
            ColumnSpec("name", required=True),
            ColumnSpec("sector", required=True),
            ColumnSpec("sub_sector"),
            ColumnSpec("region"),
            ColumnSpec("criticality", enum={"CRITICAL", "HIGH", "MEDIUM", "LOW"}),
            ColumnSpec("peer_group"),
        ],
        "natural_key": ["code"],
    },

    # ------------------------------------------------------------------ assets
    "assets": {
        "description": "Asset / system inventory per entity",
        "columns": [
            ColumnSpec("entity_code", required=True),
            ColumnSpec("asset_code", required=True),
            ColumnSpec("hostname"),
            ColumnSpec("asset_type", required=True),
            ColumnSpec("criticality", enum={"CRITICAL", "HIGH", "MEDIUM", "LOW"}),
        ],
        "natural_key": ["entity_code", "asset_code"],
        "foreign_keys": [("entity_code", "entities", "code")],
    },

    # ------------------------------------------------------------------ alerts
    "alerts": {
        "description": "Alert metadata exported from the entity's SOC",
        "columns": [
            ColumnSpec("entity_code", required=True),
            ColumnSpec("external_id", required=True),
            ColumnSpec("title", required=True),
            ColumnSpec("description"),
            ColumnSpec(
                "severity",
                required=True,
                enum={"CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"},
            ),
            ColumnSpec("category", required=True),
            ColumnSpec("source_system"),
            ColumnSpec("asset_code"),
            ColumnSpec("detected_at", required=True, kind="datetime"),
            ColumnSpec("acknowledged_at", kind="datetime"),
            ColumnSpec("closed_at", kind="datetime"),
            ColumnSpec(
                "status",
                required=True,
                enum={
                    "OPEN",
                    "ACKNOWLEDGED",
                    "INVESTIGATING",
                    "ESCALATED",
                    "CLOSED",
                    "FALSE_POSITIVE",
                    "SUPPRESSED",
                },
            ),
        ],
        "natural_key": ["entity_code", "external_id"],
        "foreign_keys": [
            ("entity_code", "entities", "code"),
            ("asset_code", "assets", "asset_code"),
        ],
    },

    # ------------------------------------------------------------------- cases
    "cases": {
        "description": "Case-management records linked to alerts",
        "columns": [
            ColumnSpec("entity_code", required=True),
            ColumnSpec("external_id", required=True),
            ColumnSpec("alert_external_id"),
            ColumnSpec("title", required=True),
            ColumnSpec(
                "severity",
                required=True,
                enum={"CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"},
            ),
            ColumnSpec("status", required=True),
            ColumnSpec("opened_at", required=True, kind="datetime"),
            ColumnSpec("closed_at", kind="datetime"),
            ColumnSpec("assigned_to"),
        ],
        "natural_key": ["entity_code", "external_id"],
        "foreign_keys": [
            ("entity_code", "entities", "code"),
            ("alert_external_id", "alerts", "external_id"),
        ],
    },

    # ---------------------------------------------------------- investigations
    "investigations": {
        "description": "Investigation records attached to cases",
        "columns": [
            ColumnSpec("entity_code", required=True),
            ColumnSpec("case_external_id", required=True),
            ColumnSpec("investigator"),
            ColumnSpec("started_at", required=True, kind="datetime"),
            ColumnSpec("ended_at", kind="datetime"),
            ColumnSpec("summary"),
            ColumnSpec("evidence_notes"),
            ColumnSpec("artifacts_count", kind="int"),
            ColumnSpec("content_hash"),
        ],
        "natural_key": ["entity_code", "case_external_id", "started_at"],
        "foreign_keys": [
            ("entity_code", "entities", "code"),
            ("case_external_id", "cases", "external_id"),
        ],
    },

    # ------------------------------------------------------------ escalations
    "escalations": {
        "description": "Escalation records attached to cases",
        "columns": [
            ColumnSpec("entity_code", required=True),
            ColumnSpec("case_external_id", required=True),
            ColumnSpec("escalated_at", required=True, kind="datetime"),
            ColumnSpec("escalated_to", required=True),
            ColumnSpec("level", kind="int"),
            ColumnSpec("reason"),
            ColumnSpec("acknowledged_at", kind="datetime"),
        ],
        "natural_key": ["entity_code", "case_external_id", "escalated_at"],
        "foreign_keys": [
            ("entity_code", "entities", "code"),
            ("case_external_id", "cases", "external_id"),
        ],
    },

    # ---------------------------------------------------------- dispositions
    "dispositions": {
        "description": "Alert dispositions / closure rationale",
        "columns": [
            ColumnSpec("entity_code", required=True),
            ColumnSpec("alert_external_id", required=True),
            ColumnSpec("disposition", required=True),
            ColumnSpec("rationale"),
            ColumnSpec("closed_by"),
            ColumnSpec("closure_seconds", kind="int"),
        ],
        "natural_key": ["entity_code", "alert_external_id"],
        "foreign_keys": [
            ("entity_code", "entities", "code"),
            ("alert_external_id", "alerts", "external_id"),
        ],
    },
}


def get_schema(payload_type: str) -> dict[str, Any]:
    if payload_type not in PAYLOAD_SCHEMAS:
        raise ValueError(f"Unknown payload type: {payload_type}")
    return PAYLOAD_SCHEMAS[payload_type]