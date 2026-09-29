"""
DB-export ingestion adapter tests.
"""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

import pytest

from app.ingestion.pipeline import detect_format, read_file


def _make_sqlite_bytes() -> bytes:
    fd, path = tempfile.mkstemp(suffix=".sqlite")
    import os
    os.close(fd)
    con = sqlite3.connect(path)
    con.execute(
        "CREATE TABLE alerts ("
        "entity_code TEXT, external_id TEXT, severity TEXT, category TEXT, "
        "detected_at TEXT, status TEXT)"
    )
    con.execute(
        "INSERT INTO alerts VALUES "
        "('BANK-A','ALT-1','HIGH','MALWARE','2026-09-01 10:00:00','CLOSED')"
    )
    con.commit()
    con.close()
    blob = Path(path).read_bytes()
    os.remove(path)
    return blob


def test_detect_format_sqlite():
    assert detect_format("export.sqlite") == "sqlite"


def test_detect_format_db():
    assert detect_format("dump.db") == "db"


def test_detect_format_parquet():
    assert detect_format("table.parquet") == "parquet"


def test_read_sqlite_roundtrip():
    blob = _make_sqlite_bytes()
    df = read_file(blob, "sqlite")
    assert len(df) == 1
    assert list(df.columns) == [
        "entity_code",
        "external_id",
        "severity",
        "category",
        "detected_at",
        "status",
    ]
    assert df.iloc[0]["entity_code"] == "BANK-A"


def test_read_unknown_format_raises():
    with pytest.raises(ValueError):
        detect_format("file.xyz")