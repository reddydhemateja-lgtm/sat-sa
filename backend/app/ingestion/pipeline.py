"""
File reading, validation, and normalization for CSE submissions.

Nothing here touches the database. Every function returns plain Python data
so the same pipeline can serve both the dry-run preview endpoint and the
final commit endpoint.
"""

from __future__ import annotations

import io
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

import pandas as pd

from app.ingestion.column_mapping import apply_mapping
from app.ingestion.schemas import PAYLOAD_SCHEMAS, ColumnSpec


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------
@dataclass
class ValidationIssue:
    row: int | None
    severity: Literal["ERROR", "WARNING", "INFO"]
    field: str | None
    message: str


@dataclass
class ValidationSummary:
    payload_type: str
    records_received: int
    records_valid: int
    records_warning: int
    records_error: int
    issues: list[ValidationIssue] = field(default_factory=list)
    preview: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "payload_type": self.payload_type,
            "records_received": self.records_received,
            "records_valid": self.records_valid,
            "records_warning": self.records_warning,
            "records_error": self.records_error,
            "issues": [
                {
                    "row": i.row,
                    "severity": i.severity,
                    "field": i.field,
                    "message": i.message,
                }
                for i in self.issues[:200]
            ],
            "preview": self.preview,
        }


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------
SUPPORTED_FORMATS = {"csv", "json", "xlsx", "xls", "sqlite", "db", "parquet"}

# DB-export formats route through db_export_adapter.read_db_export()
DB_EXPORT_FORMATS = {"sqlite", "db", "parquet"}


def detect_format(filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in SUPPORTED_FORMATS:
        raise ValueError(
            f"Unsupported file format '{ext}'. "
            f"Supported: {', '.join(sorted(SUPPORTED_FORMATS))}"
        )
    return ext


def read_file(blob: bytes, fmt: str) -> pd.DataFrame:
    buf = io.BytesIO(blob)

    if fmt == "csv":
        try:
            return pd.read_csv(buf, dtype=str, keep_default_na=False)
        except UnicodeDecodeError:
            buf.seek(0)
            return pd.read_csv(buf, dtype=str, keep_default_na=False, encoding="latin-1")

    if fmt == "json":
        raw = blob.decode("utf-8")
        data = json.loads(raw)
        if isinstance(data, dict):
            if "records" in data and isinstance(data["records"], list):
                data = data["records"]
            else:
                data = [data]
        return pd.DataFrame(data).astype(str)

    if fmt in ("xlsx", "xls"):
        return pd.read_excel(buf, dtype=str).fillna("")

    if fmt in DB_EXPORT_FORMATS:
        from app.ingestion.adapters.db_export_adapter import read_db_export

        return read_db_export(blob, fmt)

    raise ValueError(f"Unsupported format: {fmt}")


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------
DATETIME_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%d",
    "%d-%m-%Y %H:%M:%S",
    "%d/%m/%Y %H:%M:%S",
    "%Y/%m/%d %H:%M:%S",
)


def _is_blank(value: Any) -> bool:
    """True for None, empty strings, NaN, NaT, and any pandas null."""
    if value is None:
        return True
    if isinstance(value, str):
        s = value.strip().lower()
        if s == "" or s in {"nan", "none", "null", "nat"}:
            return True
    try:
        result = pd.isna(value)
        if isinstance(result, bool) and result:
            return True
    except (TypeError, ValueError):
        pass
    return False


def _parse_datetime(value: Any) -> datetime | None:
    if _is_blank(value):
        return None
    s = str(value).strip()
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    for fmt in DATETIME_FORMATS:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    try:
        ts = pd.to_datetime(s, errors="raise")
        if pd.isna(ts):
            return None
        return ts.to_pydatetime()
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Validate
# ---------------------------------------------------------------------------
def validate(
    df: pd.DataFrame,
    payload_type: str,
    *,
    known_entity_codes: set[str] | None = None,
    column_mapping: dict[str, str | None] | None = None,
) -> tuple[pd.DataFrame, ValidationSummary]:
    """
    Validate a dataframe against the schema for payload_type.

    Any row containing a value that would break DB commit (unknown enum,
    invalid datetime, missing required, NaN in int column) is rejected as
    an ERROR. clean_df is guaranteed safe to commit.
    """
    if column_mapping is not None:
        df = apply_mapping(df, column_mapping)

    schema = PAYLOAD_SCHEMAS[payload_type]
    columns: list[ColumnSpec] = schema["columns"]
    required = {c.name for c in columns if c.required}

    issues: list[ValidationIssue] = []
    received = len(df)

    present = set(df.columns)
    missing_cols = [c for c in required if c not in present]
    if missing_cols:
        issues.append(
            ValidationIssue(
                row=None,
                severity="ERROR",
                field=None,
                message=f"Missing required column(s): {', '.join(sorted(missing_cols))}",
            )
        )
        return pd.DataFrame(), ValidationSummary(
            payload_type=payload_type,
            records_received=received,
            records_valid=0,
            records_warning=0,
            records_error=received,
            issues=issues,
            preview=[],
        )

    spec_by_name = {c.name: c for c in columns}
    valid_rows: list[dict[str, Any]] = []
    error_count = 0
    warning_count = 0

    seen_natural_keys: dict[tuple, int] = {}
    natural_key_cols: list[str] = schema.get("natural_key", [])

    for idx, row in df.iterrows():
        row_number = int(idx) + 2
        row_errors: list[ValidationIssue] = []
        row_warnings: list[ValidationIssue] = []
        normalized: dict[str, Any] = {}

        for col_name, spec in spec_by_name.items():
            raw = row.get(col_name, "")

            if _is_blank(raw):
                normalized[col_name] = None
                if spec.required:
                    row_errors.append(
                        ValidationIssue(
                            row_number, "ERROR", col_name, "Missing required value"
                        )
                    )
                continue

            value = raw if not isinstance(raw, str) else raw.strip()

            # Enum check first
            if spec.enum is not None:
                upper = str(value).upper()
                if upper not in spec.enum:
                    row_errors.append(
                        ValidationIssue(
                            row_number,
                            "ERROR",
                            col_name,
                            f"Unrecognized value '{value}'. Allowed: {sorted(spec.enum)}",
                        )
                    )
                    continue
                value = upper

            if spec.kind == "datetime":
                parsed = _parse_datetime(value)
                if parsed is None:
                    row_errors.append(
                        ValidationIssue(
                            row_number, "ERROR", col_name, f"Invalid datetime: '{value}'"
                        )
                    )
                    continue
                normalized[col_name] = parsed

            elif spec.kind == "int":
                try:
                    f = float(value)
                    if pd.isna(f):
                        raise ValueError("nan")
                    normalized[col_name] = int(f)
                except (TypeError, ValueError):
                    row_errors.append(
                        ValidationIssue(
                            row_number, "ERROR", col_name, f"Expected integer, got '{value}'"
                        )
                    )
                    continue

            elif spec.kind == "float":
                try:
                    f = float(value)
                    if pd.isna(f):
                        raise ValueError("nan")
                    normalized[col_name] = f
                except (TypeError, ValueError):
                    row_errors.append(
                        ValidationIssue(
                            row_number, "ERROR", col_name, f"Expected number, got '{value}'"
                        )
                    )
                    continue

            else:
                normalized[col_name] = value

        if known_entity_codes is not None and "entity_code" in normalized:
            code = normalized.get("entity_code")
            if code and code not in known_entity_codes:
                row_errors.append(
                    ValidationIssue(
                        row_number, "ERROR", "entity_code", f"Unknown entity code '{code}'"
                    )
                )

        if natural_key_cols and all(
            normalized.get(k) is not None for k in natural_key_cols
        ):
            key = tuple(str(normalized[k]) for k in natural_key_cols)
            if key in seen_natural_keys:
                row_warnings.append(
                    ValidationIssue(
                        row_number,
                        "WARNING",
                        natural_key_cols[0],
                        f"Duplicate of row {seen_natural_keys[key]} in this batch",
                    )
                )
            else:
                seen_natural_keys[key] = row_number

        if row_errors:
            error_count += 1
            issues.extend(row_errors)
        else:
            valid_rows.append(normalized)
            issues.extend(row_warnings)
            if row_warnings:
                warning_count += 1

    clean_df = pd.DataFrame(valid_rows) if valid_rows else pd.DataFrame()

    preview_cols = [
        c
        for c in ("entity_code", "external_id", "title", "severity", "status", "detected_at")
        if c in clean_df.columns
    ]
    if not preview_cols and not clean_df.empty:
        preview_cols = list(clean_df.columns[:6])
    preview = (
        clean_df[preview_cols].head(20).astype(str).to_dict(orient="records")
        if not clean_df.empty
        else []
    )

    summary = ValidationSummary(
        payload_type=payload_type,
        records_received=received,
        records_valid=len(clean_df),
        records_warning=warning_count,
        records_error=error_count,
        issues=issues,
        preview=preview,
    )
    return clean_df, summary