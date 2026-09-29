"""
API ingestion adapter.

Feeds a JSON payload from a (demo/internal) API connector into the SAME
ingestion pipeline used by uploaded files:

    API JSON  ->  parse JSON  ->  DataFrame  ->  pipeline.validate()
                                                  ->  commit.commit_payload()
                                                  ->  run_analytics_for_period()

This module is deliberately format-agnostic: it takes already-fetched
bytes and hands them back as a DataFrame. Network fetching is the
connector router's job (app/routers/connectors.py). Keeping them apart
means the demo connector and a future real connector share identical
validation and persistence paths.
"""

from __future__ import annotations

import json
from typing import Any

import pandas as pd


def read_api_json(blob: bytes) -> pd.DataFrame:
    """
    Parse a JSON payload from an API connector.

    Accepted shapes:
        [ {...}, {...} ]                      -> list of records
        { "records": [ {...}, {...} ] }       -> wrapped list
        { "data":    [ {...}, {...} ] }       -> common API envelope
        { ... }                               -> single record

    Anything else raises ValueError so the router can return a clear 400.
    """
    if not blob:
        raise ValueError("Empty API payload")

    try:
        text = blob.decode("utf-8")
    except UnicodeDecodeError as e:
        raise ValueError(f"API payload is not valid UTF-8: {e}") from e

    try:
        payload: Any = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"API payload is not valid JSON: {e}") from e

    records: list[dict[str, Any]]
    if isinstance(payload, list):
        records = payload
    elif isinstance(payload, dict):
        if isinstance(payload.get("records"), list):
            records = payload["records"]
        elif isinstance(payload.get("data"), list):
            records = payload["data"]
        else:
            records = [payload]
    else:
        raise ValueError(
            f"API payload must be a list or object; got {type(payload).__name__}"
        )

    if not records:
        raise ValueError("API payload contained zero records")

    df = pd.DataFrame(records)
    return df.astype(str).fillna("")