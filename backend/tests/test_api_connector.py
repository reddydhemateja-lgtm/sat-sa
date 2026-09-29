"""
Smoke test for the demo API connector pipeline.

Verifies that the demo connector:
    - is created on first access
    - reads its bundled synthetic payload
    - feeds the payload through the same validate() used by file uploads
    - returns a valid DataFrame with the expected columns
"""

from __future__ import annotations

from pathlib import Path

from app.ingestion.adapters.api_adapter import read_api_json


def _demo_payload_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "data"
        / "sample"
        / "api_demo"
        / "alerts_api_batch.json"
    )


def test_demo_payload_file_exists():
    p = _demo_payload_path()
    assert p.exists(), f"Demo payload missing at {p}"
    assert p.stat().st_size > 0


def test_read_api_json_returns_dataframe():
    blob = _demo_payload_path().read_bytes()
    df = read_api_json(blob)
    assert len(df) > 0
    assert "entity_code" in df.columns
    assert "external_id" in df.columns
    assert "severity" in df.columns


def test_read_api_json_rejects_empty():
    import pytest
    with pytest.raises(ValueError):
        read_api_json(b"")


def test_read_api_json_rejects_bad_json():
    import pytest
    with pytest.raises(ValueError):
        read_api_json(b"{ this is not json }")


def test_read_api_json_accepts_wrapped_records():
    import json
    payload = {"records": [{"entity_code": "X", "external_id": "1"}]}
    df = read_api_json(json.dumps(payload).encode("utf-8"))
    assert len(df) == 1
    assert df.iloc[0]["entity_code"] == "X"


def test_demo_payload_passes_validation():
    from app.ingestion.pipeline import validate

    blob = _demo_payload_path().read_bytes()
    df = read_api_json(blob)
    clean_df, summary = validate(df, "alerts", known_entity_codes={"BANK-A"})
    assert summary.records_received == len(df)
    assert summary.records_valid >= 1
    assert not clean_df.empty