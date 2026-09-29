"""
Database-export ingestion adapter.

Handles CSE submissions that arrive as database exports rather than flat
CSV/JSON:

    .sqlite / .db  -> SQLite database file (one table = one payload)
    .parquet       -> columnar export (single table)

The adapter's only job is to return a pandas DataFrame shaped like the
CSV/JSON path would produce. It does NOT validate or write to the DB —
that still happens in app.ingestion.pipeline.validate() and
app.ingestion.commit.commit_payload().

Payload-type auto-detection:
    If the export contains a table named after a known payload type
    (alerts, cases, investigations, escalations, dispositions, assets,
    entities), that table is returned. If multiple such tables exist,
    the caller should pass a hint via the `payload_hint` kwarg (future).
    If no matching table is found, the first table is returned — the
    validator will then reject it with clear column errors.
"""

from __future__ import annotations

import io
import sqlite3
from typing import Any

import pandas as pd

KNOWN_TABLES = (
    "alerts",
    "cases",
    "investigations",
    "escalations",
    "dispositions",
    "assets",
    "entities",
)


def _pick_table(con: sqlite3.Connection) -> str:
    """Choose which table to read from a SQLite export."""
    rows = con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    names = [r[0] for r in rows if not r[0].startswith("sqlite_")]
    if not names:
        raise ValueError("SQLite export contains no user tables")

    for known in KNOWN_TABLES:
        if known in names:
            return known

    # Fall back to the first table (sorted) so the validator produces
    # clear "missing required column" errors rather than a 500.
    return names[0]


def _read_sqlite(blob: bytes) -> pd.DataFrame:
    # sqlite3 needs a file on disk or a connection string.
    # Write to a temp file (binary safe, works with file-backed SQLite).
    import tempfile, os

    fd, path = tempfile.mkstemp(suffix=".sqlite")
    os.close(fd)
    try:
        with open(path, "wb") as f:
            f.write(blob)
        con = sqlite3.connect(path)
        try:
            table = _pick_table(con)
            df = pd.read_sql_query(f'SELECT * FROM "{table}"', con, dtype=str)
        finally:
            con.close()
    finally:
        try:
            os.remove(path)
        except OSError:
            pass

    if df is None:
        df = pd.DataFrame()
    return df.fillna("")


def _read_parquet(blob: bytes) -> pd.DataFrame:
    df = pd.read_parquet(io.BytesIO(blob))
    return df.astype(str).fillna("")


def read_db_export(blob: bytes, fmt: str) -> pd.DataFrame:
    """
    Entry point used by pipeline.read_file().

    Raises ValueError for unsupported formats or unusable exports so the
    ingestion router can return a 400 instead of a 500.
    """
    if fmt in ("sqlite", "db"):
        return _read_sqlite(blob)
    if fmt == "parquet":
        try:
            return _read_parquet(blob)
        except ImportError as e:
            raise ValueError(
                "Parquet support requires pyarrow or fastparquet. "
                "Install with: pip install pyarrow"
            ) from e
    raise ValueError(f"Unsupported DB export format: {fmt}")