"""
Persist validated ingestion rows into the database.

Called by the ingestion router after a preview has been confirmed.

Behaviour on duplicates:
    For rows whose natural key already exists in the DB, the row is SKIPPED
    (not inserted, not counted as an error). The number of skipped rows is
    returned separately so the caller can display it.
"""

from __future__ import annotations

import hashlib
import math
from typing import Any

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cse import Asset, CSEEntity
from app.models.ingestion import DataSubmission
from app.models.operational import (
    Alert,
    AlertDisposition,
    AlertStatusEnum,
    Case,
    Escalation,
    Investigation,
    SeverityEnum,
)


# ---------------------------------------------------------------------------
# Safety helpers
# ---------------------------------------------------------------------------
def _safe_int(v: Any) -> int | None:
    if v is None:
        return None
    try:
        if isinstance(v, float) and math.isnan(v):
            return None
    except (TypeError, ValueError):
        pass
    try:
        if pd.isna(v):
            return None
    except (TypeError, ValueError):
        pass
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def _safe_dt(v: Any) -> Any | None:
    if v is None:
        return None
    try:
        if pd.isna(v):
            return None
    except (TypeError, ValueError):
        pass
    return v


def _safe_str(v: Any) -> str | None:
    if v is None:
        return None
    try:
        if pd.isna(v):
            return None
    except (TypeError, ValueError):
        pass
    s = str(v)
    return s if s else None


# ---------------------------------------------------------------------------
# Lookup helpers
# ---------------------------------------------------------------------------
async def _entity_map(db: AsyncSession) -> dict[str, int]:
    result = await db.execute(select(CSEEntity.code, CSEEntity.id))
    return {code: pk for code, pk in result.all()}


async def _asset_map(db: AsyncSession, entity_id: int) -> dict[str, int]:
    result = await db.execute(
        select(Asset.asset_code, Asset.id).where(Asset.entity_id == entity_id)
    )
    return {code: pk for code, pk in result.all()}


async def _alert_map(db: AsyncSession, entity_id: int) -> dict[str, int]:
    result = await db.execute(
        select(Alert.external_id, Alert.id).where(Alert.entity_id == entity_id)
    )
    return {ext: pk for ext, pk in result.all()}


async def _case_map(db: AsyncSession, entity_id: int) -> dict[str, int]:
    result = await db.execute(
        select(Case.external_id, Case.id).where(Case.entity_id == entity_id)
    )
    return {ext: pk for ext, pk in result.all()}


async def _existing_investigation_keys(db: AsyncSession, entity_id: int) -> set[str]:
    result = await db.execute(
        select(Investigation.content_hash).where(
            Investigation.entity_id == entity_id,
            Investigation.content_hash.isnot(None),
        )
    )
    return {h for (h,) in result.all() if h}


async def _existing_escalation_keys(db: AsyncSession, entity_id: int) -> set[tuple]:
    """Return set of (case_id, escalated_at) tuples."""
    result = await db.execute(
        select(Escalation.case_id, Escalation.escalated_at).where(
            Escalation.entity_id == entity_id
        )
    )
    return set(result.all())


def _hash_file(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def _md5_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Commit — returns (inserted, skipped)
# ---------------------------------------------------------------------------
async def commit_payload(
    db: AsyncSession,
    *,
    payload_type: str,
    clean_df: pd.DataFrame,
    entity_id: int,
    period_id: int,
    submission: DataSubmission,
    submitted_by: str | None = None,
) -> tuple[int, int]:
    """
    Persist rows. Returns (inserted, skipped).

    Skipped = rows whose natural key already exists in the DB. They are not
    treated as errors — a re-upload should not fail because the same data
    was previously committed.
    """
    if clean_df.empty:
        return 0, 0

    inserted = 0
    skipped = 0

    result = await db.execute(select(CSEEntity.code).where(CSEEntity.id == entity_id))
    entity_code = result.scalar_one_or_none()
    if entity_code is None:
        raise ValueError(f"Entity id {entity_id} not found")

    # ------------------------------------------------------------------ alerts
    if payload_type == "alerts":
        existing = await _alert_map(db, entity_id)   # external_id -> id
        assets_by_code = await _asset_map(db, entity_id)

        # Track newly-inserted IDs within this batch so self-collisions don't insert twice
        inserted_ext: set[str] = set()

        for _, r in clean_df.iterrows():
            ext_id = str(r["external_id"])
            if ext_id in existing or ext_id in inserted_ext:
                skipped += 1
                continue

            asset_code = _safe_str(r.get("asset_code"))
            asset_id = assets_by_code.get(asset_code) if asset_code else None

            db.add(Alert(
                entity_id=entity_id,
                period_id=period_id,
                submission_id=submission.id,
                external_id=ext_id,
                title=str(r["title"]),
                description=_safe_str(r.get("description")),
                severity=SeverityEnum(str(r["severity"]).upper()),
                category=str(r["category"]),
                source_system=_safe_str(r.get("source_system")),
                asset_id=_safe_int(asset_id),
                detected_at=_safe_dt(r["detected_at"]),
                acknowledged_at=_safe_dt(r.get("acknowledged_at")),
                closed_at=_safe_dt(r.get("closed_at")),
                status=AlertStatusEnum(str(r["status"]).upper()),
                raw=None,
            ))
            inserted_ext.add(ext_id)
            inserted += 1
        await db.flush()

    # ------------------------------------------------------------------- cases
    elif payload_type == "cases":
        existing = await _case_map(db, entity_id)
        alerts_by_ext = await _alert_map(db, entity_id)
        inserted_ext: set[str] = set()

        for _, r in clean_df.iterrows():
            ext_id = str(r["external_id"])
            if ext_id in existing or ext_id in inserted_ext:
                skipped += 1
                continue
            alert_ext = _safe_str(r.get("alert_external_id"))
            alert_id = alerts_by_ext.get(alert_ext) if alert_ext else None
            db.add(Case(
                entity_id=entity_id,
                period_id=period_id,
                external_id=ext_id,
                alert_id=_safe_int(alert_id),
                title=str(r["title"]),
                severity=SeverityEnum(str(r["severity"]).upper()),
                status=str(r["status"]),
                opened_at=_safe_dt(r["opened_at"]),
                closed_at=_safe_dt(r.get("closed_at")),
                assigned_to=_safe_str(r.get("assigned_to")),
                raw=None,
            ))
            inserted_ext.add(ext_id)
            inserted += 1
        await db.flush()

    # ---------------------------------------------------------- investigations
    elif payload_type == "investigations":
        cases_by_ext = await _case_map(db, entity_id)
        existing_hashes = await _existing_investigation_keys(db, entity_id)
        new_hashes_in_batch: set[str] = set()

        for _, r in clean_df.iterrows():
            case_ext = _safe_str(r.get("case_external_id"))
            case_id = cases_by_ext.get(case_ext) if case_ext else None
            if case_id is None:
                skipped += 1
                continue
            summary = _safe_str(r.get("summary"))
            content_hash = _safe_str(r.get("content_hash")) or (
                _md5_text(summary) if summary else None
            )
            if content_hash and (
                content_hash in existing_hashes or content_hash in new_hashes_in_batch
            ):
                skipped += 1
                continue
            db.add(Investigation(
                case_id=case_id,
                entity_id=entity_id,
                investigator=_safe_str(r.get("investigator")),
                started_at=_safe_dt(r["started_at"]),
                ended_at=_safe_dt(r.get("ended_at")),
                summary=summary,
                evidence_notes=_safe_str(r.get("evidence_notes")),
                artifacts_count=_safe_int(r.get("artifacts_count")) or 0,
                content_hash=content_hash,
                content_length=len(summary) if summary else 0,
                raw=None,
            ))
            if content_hash:
                new_hashes_in_batch.add(content_hash)
            inserted += 1
        await db.flush()

    # ------------------------------------------------------------ escalations
    elif payload_type == "escalations":
        cases_by_ext = await _case_map(db, entity_id)
        existing = await _existing_escalation_keys(db, entity_id)
        new_keys: set[tuple] = set()

        for _, r in clean_df.iterrows():
            case_ext = _safe_str(r.get("case_external_id"))
            case_id = cases_by_ext.get(case_ext) if case_ext else None
            if case_id is None:
                skipped += 1
                continue
            esc_at = _safe_dt(r["escalated_at"])
            key = (case_id, esc_at)
            if key in existing or key in new_keys:
                skipped += 1
                continue
            db.add(Escalation(
                entity_id=entity_id,
                case_id=case_id,
                escalated_at=esc_at,
                escalated_to=str(r["escalated_to"]),
                level=_safe_int(r.get("level")) or 1,
                reason=_safe_str(r.get("reason")),
                acknowledged_at=_safe_dt(r.get("acknowledged_at")),
            ))
            new_keys.add(key)
            inserted += 1
        await db.flush()

    # ---------------------------------------------------------- dispositions
    elif payload_type == "dispositions":
        alerts_by_ext = await _alert_map(db, entity_id)
        existing_rows = await db.execute(
            select(AlertDisposition.alert_id).where(AlertDisposition.entity_id == entity_id)
        )
        existing_alert_ids = {aid for (aid,) in existing_rows.all()}
        new_alert_ids: set[int] = set()

        for _, r in clean_df.iterrows():
            alert_ext = _safe_str(r.get("alert_external_id"))
            alert_id = alerts_by_ext.get(alert_ext) if alert_ext else None
            if alert_id is None:
                skipped += 1
                continue
            if alert_id in existing_alert_ids or alert_id in new_alert_ids:
                skipped += 1
                continue
            db.add(AlertDisposition(
                alert_id=alert_id,
                entity_id=entity_id,
                disposition=str(r["disposition"]),
                rationale=_safe_str(r.get("rationale")),
                closed_by=_safe_str(r.get("closed_by")),
                closure_seconds=_safe_int(r.get("closure_seconds")),
            ))
            new_alert_ids.add(alert_id)
            inserted += 1
        await db.flush()

    # -------------------------------------------------------------- entities
    elif payload_type == "entities":
        existing_codes = set((await _entity_map(db)).keys())
        for _, r in clean_df.iterrows():
            code = _safe_str(r.get("code"))
            if not code:
                skipped += 1
                continue
            if code in existing_codes:
                skipped += 1
                continue
            db.add(CSEEntity(
                code=code,
                name=str(r["name"]),
                sector=str(r["sector"]),
                sub_sector=_safe_str(r.get("sub_sector")),
                region=_safe_str(r.get("region")),
                criticality=_safe_str(r.get("criticality")) or "HIGH",
                peer_group=_safe_str(r.get("peer_group")),
                is_active=True,
            ))
            existing_codes.add(code)
            inserted += 1
        await db.flush()

    # ------------------------------------------------------------------ assets
    elif payload_type == "assets":
        existing_codes = set((await _asset_map(db, entity_id)).keys())
        for _, r in clean_df.iterrows():
            ac = _safe_str(r.get("asset_code"))
            if not ac or ac in existing_codes:
                skipped += 1
                continue
            db.add(Asset(
                entity_id=entity_id,
                asset_code=ac,
                hostname=_safe_str(r.get("hostname")),
                asset_type=str(r["asset_type"]),
                criticality=_safe_str(r.get("criticality")) or "MEDIUM",
                tags=None,
            ))
            existing_codes.add(ac)
            inserted += 1
        await db.flush()

    else:
        raise ValueError(f"Unsupported payload_type for commit: {payload_type}")

    submission.records_valid = inserted
    submission.status = "COMMITTED"
    await db.flush()
    return inserted, skipped