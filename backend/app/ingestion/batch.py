"""
Batch folder ingestion.

Accepts a set of files (a "batch") belonging to one CSE entity and one
assessment period, validates each file independently, and produces a
consolidated report. Does NOT write to the database in scan mode.

Commit mode writes valid rows in dependency order so foreign keys resolve:
    entities → assets → alerts → cases → investigations → escalations → dispositions
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from app.ingestion.column_mapping import suggest_mapping
from app.ingestion.pipeline import detect_format, read_file, validate


# ---------------------------------------------------------------------------
# Payload-type inference
# ---------------------------------------------------------------------------
PAYLOAD_KEYS = [
    ("investigations", ["investigation"]),
    ("dispositions",   ["disposition"]),
    ("escalations",    ["escalation"]),
    ("entities",       ["entit", "cse"]),
    ("assets",         ["asset", "device", "host"]),
    ("alerts",         ["alert"]),
    ("cases",          ["case", "ticket", "incident"]),
]

COLUMN_HINTS = {
    "alerts":         {"external_id", "severity", "detected_at", "status", "category"},
    "cases":          {"external_id", "opened_at", "status", "assigned_to"},
    "investigations": {"case_external_id", "started_at", "summary"},
    "escalations":    {"case_external_id", "escalated_at", "escalated_to"},
    "dispositions":   {"alert_external_id", "disposition"},
    "assets":         {"asset_code", "asset_type", "criticality"},
    "entities":       {"code", "name", "sector"},
}


def infer_payload_type(filename: str, df: pd.DataFrame) -> str | None:
    """Best-effort guess from filename first, then columns."""
    name = filename.lower()
    for payload, keys in PAYLOAD_KEYS:
        if any(k in name for k in keys):
            return payload

    cols = {c.lower() for c in df.columns}
    best_payload: str | None = None
    best_score = 0
    for payload, hints in COLUMN_HINTS.items():
        score = len(cols & hints)
        if score > best_score:
            best_score = score
            best_payload = payload
    return best_payload if best_score >= 2 else None


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
@dataclass
class FileReport:
    file_name: str
    payload_type: str | None
    detected_payload_type: str | None
    format: str | None
    records_received: int = 0
    records_valid: int = 0
    records_warning: int = 0
    records_error: int = 0
    inferred_by: str = "filename"
    error: str | None = None
    suggested_mapping: dict[str, str | None] | None = None
    issues: list[dict[str, Any]] = field(default_factory=list)
    preview: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_name": self.file_name,
            "payload_type": self.payload_type,
            "detected_payload_type": self.detected_payload_type,
            "format": self.format,
            "records_received": self.records_received,
            "records_valid": self.records_valid,
            "records_warning": self.records_warning,
            "records_error": self.records_error,
            "inferred_by": self.inferred_by,
            "error": self.error,
            "suggested_mapping": self.suggested_mapping,
            "issues": self.issues[:500],
            "preview": self.preview[:20],
        }


@dataclass
class BatchReport:
    entity_code: str
    period_label: str
    file_count: int
    total_received: int
    total_valid: int
    total_warning: int
    total_error: int
    files: list[FileReport]

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_code": self.entity_code,
            "period_label": self.period_label,
            "file_count": self.file_count,
            "total_received": self.total_received,
            "total_valid": self.total_valid,
            "total_warning": self.total_warning,
            "total_error": self.total_error,
            "files": [f.to_dict() for f in self.files],
        }


# ---------------------------------------------------------------------------
# Scan
# ---------------------------------------------------------------------------
async def scan_batch(
    files: list[tuple[str, bytes]],
    *,
    payload_overrides: dict[str, str] | None = None,
    known_entity_codes: set[str] | None = None,
    entity_code: str = "",
    period_label: str = "",
) -> tuple[BatchReport, dict[str, pd.DataFrame]]:
    report_files: list[FileReport] = []
    clean_by_type: dict[str, pd.DataFrame] = {}
    payload_overrides = payload_overrides or {}

    for filename, blob in files:
        fr = FileReport(
            file_name=filename,
            payload_type=payload_overrides.get(filename),
            detected_payload_type=None,
            format=None,
        )

        lower = filename.lower()
        if lower.endswith((".txt", ".log", ".md", ".py", ".json.lock")):
            fr.error = "Skipped: unsupported file type"
            report_files.append(fr)
            continue

        try:
            fmt = detect_format(filename)
            fr.format = fmt
        except ValueError as e:
            fr.error = str(e)
            report_files.append(fr)
            continue

        try:
            df = read_file(blob, fmt)
        except Exception as e:
            fr.error = f"Could not parse file: {e}"
            report_files.append(fr)
            continue

        inferred = infer_payload_type(filename, df)
        fr.detected_payload_type = inferred
        payload = fr.payload_type or inferred
        if not payload:
            fr.error = "Could not determine payload type from filename or columns"
            report_files.append(fr)
            continue
        fr.payload_type = payload

        fr.suggested_mapping = suggest_mapping(list(df.columns), payload)

        try:
            clean_df, summary = validate(
                df,
                payload,
                known_entity_codes=known_entity_codes if payload != "entities" else None,
            )
        except Exception as e:
            fr.error = f"Validation failed: {e}"
            report_files.append(fr)
            continue

        fr.records_received = summary.records_received
        fr.records_valid = summary.records_valid
        fr.records_warning = summary.records_warning
        fr.records_error = summary.records_error
        fr.issues = [
            {
                "row": i.row,
                "severity": i.severity,
                "field": i.field,
                "message": i.message,
            }
            for i in summary.issues
        ]
        fr.preview = summary.preview

        if not clean_df.empty:
            if payload in clean_by_type and not clean_by_type[payload].empty:
                # Only concat when both sides are non-empty
                clean_by_type[payload] = pd.concat(
                    [clean_by_type[payload], clean_df], ignore_index=True
                )
            else:
                clean_by_type[payload] = clean_df

        report_files.append(fr)

    report = BatchReport(
        entity_code=entity_code,
        period_label=period_label,
        file_count=len(report_files),
        total_received=sum(f.records_received for f in report_files),
        total_valid=sum(f.records_valid for f in report_files),
        total_warning=sum(f.records_warning for f in report_files),
        total_error=sum(f.records_error for f in report_files),
        files=report_files,
    )
    return report, clean_by_type


# ---------------------------------------------------------------------------
# Dependency order for commit
# ---------------------------------------------------------------------------
COMMIT_ORDER = [
    "entities",
    "assets",
    "alerts",
    "cases",
    "investigations",
    "escalations",
    "dispositions",
]