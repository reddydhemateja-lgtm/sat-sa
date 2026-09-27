"""
Ingestion endpoints.

Flow:
    POST /ingestion/headers              → detect columns, suggest mapping
    POST /ingestion/preview              → validate one file
    POST /ingestion/commit               → validate + persist one file
    POST /ingestion/batch/scan           → validate a folder of files (dry run)
    POST /ingestion/batch/commit         → validate + persist a folder, then run analytics
    GET  /ingestion/submissions          → list past submissions
    GET  /ingestion/submissions/{id}     → inspect one submission
"""

from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.orchestrator import run_analytics_for_period
from app.audit import record_audit
from app.database import get_db
from app.deps import get_current_user, require_roles
from app.ingestion.batch import COMMIT_ORDER, scan_batch
from app.ingestion.column_mapping import suggest_mapping
from app.ingestion.commit import _hash_file, commit_payload
from app.ingestion.pipeline import detect_format, read_file, validate
from app.models.cse import CSEEntity
from app.models.ingestion import DataSubmission
from app.models.period import AssessmentPeriod
from app.models.user import RoleEnum, User

router = APIRouter(prefix="/ingestion", tags=["ingestion"])

SUPPORTED_PAYLOADS = {
    "entities", "assets", "alerts", "cases",
    "investigations", "escalations", "dispositions",
}


async def _resolve_entity_period(
    db: AsyncSession, entity_id: int, period_id: int
) -> tuple[CSEEntity, AssessmentPeriod]:
    ent = (
        await db.execute(select(CSEEntity).where(CSEEntity.id == entity_id))
    ).scalar_one_or_none()
    per = (
        await db.execute(
            select(AssessmentPeriod).where(AssessmentPeriod.id == period_id)
        )
    ).scalar_one_or_none()
    if ent is None:
        raise HTTPException(status_code=404, detail=f"Entity id {entity_id} not found")
    if per is None:
        raise HTTPException(status_code=404, detail=f"Period id {period_id} not found")
    return ent, per


async def _known_entity_codes(db: AsyncSession) -> set[str]:
    result = await db.execute(select(CSEEntity.code))
    return {c for (c,) in result.all()}


# ---------------------------------------------------------------------------
# Headers / auto-mapping
# ---------------------------------------------------------------------------
@router.post(
    "/headers",
    dependencies=[Depends(require_roles(RoleEnum.ADMIN, RoleEnum.ANALYST))],
)
async def inspect_headers(
    file: UploadFile = File(...),
    payload_type: str = Form(...),
) -> dict:
    if payload_type not in SUPPORTED_PAYLOADS:
        raise HTTPException(
            status_code=400, detail=f"Unsupported payload_type: {payload_type}"
        )

    blob = await file.read()
    if not blob:
        raise HTTPException(status_code=400, detail="Empty file")

    try:
        fmt = detect_format(file.filename or "")
        df = read_file(blob, fmt)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not parse file: {e}")

    incoming = list(df.columns)
    suggested = suggest_mapping(incoming, payload_type)

    return {
        "payload_type": payload_type,
        "incoming_columns": incoming,
        "canonical_columns": list(suggested.keys()),
        "suggested_mapping": suggested,
        "sample_rows": df.head(5).fillna("").astype(str).to_dict(orient="records"),
    }


# ---------------------------------------------------------------------------
# Preview (single file)
# ---------------------------------------------------------------------------
@router.post(
    "/preview",
    dependencies=[Depends(require_roles(RoleEnum.ADMIN, RoleEnum.ANALYST))],
)
async def preview(
    file: UploadFile = File(...),
    entity_id: int = Form(...),
    period_id: int = Form(...),
    payload_type: str = Form(...),
    column_mapping: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await _resolve_entity_period(db, entity_id, period_id)

    if payload_type not in SUPPORTED_PAYLOADS:
        raise HTTPException(
            status_code=400, detail=f"Unsupported payload_type: {payload_type}"
        )

    blob = await file.read()
    if not blob:
        raise HTTPException(status_code=400, detail="Empty file")

    try:
        fmt = detect_format(file.filename or "")
        df = read_file(blob, fmt)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not parse file: {e}")

    mapping: dict[str, str | None] | None = None
    if column_mapping:
        try:
            mapping = json.loads(column_mapping)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid column_mapping JSON")

    known_codes = await _known_entity_codes(db) if payload_type != "entities" else None
    _, summary = validate(
        df, payload_type, known_entity_codes=known_codes, column_mapping=mapping
    )

    return {
        "file_name": file.filename,
        "file_hash": _hash_file(blob),
        "file_size": len(blob),
        "format": fmt,
        "column_mapping_applied": mapping is not None,
        "summary": summary.to_dict(),
    }


# ---------------------------------------------------------------------------
# Commit (single file)
# ---------------------------------------------------------------------------
@router.post(
    "/commit",
    dependencies=[Depends(require_roles(RoleEnum.ADMIN, RoleEnum.ANALYST))],
)
async def commit(
    file: UploadFile = File(...),
    entity_id: int = Form(...),
    period_id: int = Form(...),
    payload_type: str = Form(...),
    column_mapping: str | None = Form(None),
    run_analytics: bool = Form(True),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    await _resolve_entity_period(db, entity_id, period_id)

    if payload_type not in SUPPORTED_PAYLOADS:
        raise HTTPException(
            status_code=400, detail=f"Unsupported payload_type: {payload_type}"
        )

    blob = await file.read()
    if not blob:
        raise HTTPException(status_code=400, detail="Empty file")

    try:
        fmt = detect_format(file.filename or "")
        df = read_file(blob, fmt)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not parse file: {e}")

    mapping: dict[str, str | None] | None = None
    if column_mapping:
        try:
            mapping = json.loads(column_mapping)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid column_mapping JSON")

    known_codes = await _known_entity_codes(db) if payload_type != "entities" else None
    clean_df, summary = validate(
        df, payload_type, known_entity_codes=known_codes, column_mapping=mapping
    )

    if clean_df.empty:
        raise HTTPException(
            status_code=400, detail="No valid rows to commit. Fix the errors and retry."
        )

    submission = DataSubmission(
        entity_id=entity_id,
        period_id=period_id,
        submitted_by=current_user.username,
        file_name=file.filename or "upload.bin",
        file_hash=_hash_file(blob),
        file_size=len(blob),
        format=fmt,
        payload_type=payload_type,
        status="PROCESSING",
        records_received=summary.records_received,
        records_valid=0,
        records_warning=summary.records_warning,
        records_error=summary.records_error,
        validation_report=summary.to_dict(),
    )
    db.add(submission)
    await db.flush()

    try:
        inserted, skipped = await commit_payload(
            db,
            payload_type=payload_type,
            clean_df=clean_df,
            entity_id=entity_id,
            period_id=period_id,
            submission=submission,
            submitted_by=current_user.username,
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Commit failed: {e}")

    await record_audit(
        db,
        user_id=current_user.id,
        action="INGEST_COMMIT",
        target_type="data_submission",
        target_id=submission.id,
        new_value={
            "entity_id": entity_id,
            "period_id": period_id,
            "payload_type": payload_type,
            "file_name": file.filename,
            "records_received": summary.records_received,
            "records_inserted": inserted,
            "records_skipped": skipped,
            "column_mapping_applied": mapping is not None,
        },
    )

    await db.commit()
    await db.refresh(submission)

    analytics_summary: dict | None = None
    if run_analytics:
        try:
            analytics_summary = await run_analytics_for_period(
                db, period_id=period_id, actor_user_id=current_user.id
            )
        except Exception as e:
            analytics_summary = {"error": str(e)}

    return {
        "submission_id": submission.id,
        "status": submission.status,
        "records_received": summary.records_received,
        "records_inserted": inserted,
        "records_skipped": skipped,
        "warnings": summary.records_warning,
        "errors": summary.records_error,
        "analytics": analytics_summary,
    }


# ---------------------------------------------------------------------------
# Batch scan (folder)
# ---------------------------------------------------------------------------
@router.post(
    "/batch/scan",
    dependencies=[Depends(require_roles(RoleEnum.ADMIN, RoleEnum.ANALYST))],
)
async def batch_scan(
    files: list[UploadFile] = File(...),
    entity_id: int = Form(...),
    period_id: int = Form(...),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Validate a folder of files. No database writes."""
    entity, period = await _resolve_entity_period(db, entity_id, period_id)

    if not files:
        raise HTTPException(status_code=400, detail="No files received")

    payloads: list[tuple[str, bytes]] = []
    for f in files:
        blob = await f.read()
        if not blob:
            continue
        payloads.append((f.filename or "unnamed", blob))

    if not payloads:
        raise HTTPException(status_code=400, detail="All files were empty")

    known_codes = await _known_entity_codes(db)
    report, _clean = await scan_batch(
        payloads,
        known_entity_codes=known_codes,
        entity_code=entity.code,
        period_label=period.label,
    )
    return report.to_dict()


# ---------------------------------------------------------------------------
# Batch commit (folder) — with auto-analytics and skip-duplicates
# ---------------------------------------------------------------------------
@router.post(
    "/batch/commit",
    dependencies=[Depends(require_roles(RoleEnum.ADMIN, RoleEnum.ANALYST))],
)
async def batch_commit(
    files: list[UploadFile] = File(...),
    entity_id: int = Form(...),
    period_id: int = Form(...),
    run_analytics: bool = Form(True),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Validate then persist a folder of files, in dependency order.

    Duplicates (rows whose natural key already exists) are skipped — a
    re-upload of the same folder will succeed and simply report how many
    rows were skipped.

    By default, the analytics pipeline runs immediately after the commit.
    """
    entity, period = await _resolve_entity_period(db, entity_id, period_id)

    if not files:
        raise HTTPException(status_code=400, detail="No files received")

    payloads: list[tuple[str, bytes]] = []
    for f in files:
        blob = await f.read()
        if not blob:
            continue
        payloads.append((f.filename or "unnamed", blob))

    if not payloads:
        raise HTTPException(status_code=400, detail="All files were empty")

    known_codes = await _known_entity_codes(db)
    report, clean_by_type = await scan_batch(
        payloads,
        known_entity_codes=known_codes,
        entity_code=entity.code,
        period_label=period.label,
    )

    if not clean_by_type:
        raise HTTPException(status_code=400, detail="No valid rows found in any file")

    batch_file_name = f"BATCH:{entity.code}:{period.label}:{len(payloads)} files"
    submission = DataSubmission(
        entity_id=entity_id,
        period_id=period_id,
        submitted_by=current_user.username,
        file_name=batch_file_name,
        file_hash="",
        file_size=sum(len(b) for _, b in payloads),
        format="batch",
        payload_type="batch",
        status="PROCESSING",
        records_received=report.total_received,
        records_valid=0,
        records_warning=report.total_warning,
        records_error=report.total_error,
        validation_report=report.to_dict(),
    )
    db.add(submission)
    await db.flush()

    inserted: dict[str, int] = {}
    skipped: dict[str, int] = {}
    try:
        for payload_type in COMMIT_ORDER:
            df = clean_by_type.get(payload_type)
            if df is None or df.empty:
                continue
            n_inserted, n_skipped = await commit_payload(
                db,
                payload_type=payload_type,
                clean_df=df,
                entity_id=entity_id,
                period_id=period_id,
                submission=submission,
                submitted_by=current_user.username,
            )
            inserted[payload_type] = n_inserted
            skipped[payload_type] = n_skipped
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Batch commit failed: {e}")

    total_inserted = sum(inserted.values())
    total_skipped = sum(skipped.values())

    submission.records_valid = total_inserted
    submission.status = "COMMITTED"
    await db.flush()

    await record_audit(
        db,
        user_id=current_user.id,
        action="INGEST_BATCH_COMMIT",
        target_type="data_submission",
        target_id=submission.id,
        new_value={
            "entity_id": entity_id,
            "period_id": period_id,
            "file_count": len(payloads),
            "records_received": report.total_received,
            "records_inserted": total_inserted,
            "records_skipped": total_skipped,
            "by_payload": inserted,
            "by_payload_skipped": skipped,
        },
    )

    await db.commit()
    await db.refresh(submission)

    # Auto-run analytics — wrapped so a failure doesn't fail the ingestion
    analytics_summary: dict | None = None
    if run_analytics:
        try:
            analytics_summary = await run_analytics_for_period(
                db, period_id=period_id, actor_user_id=current_user.id
            )
        except Exception as e:
            analytics_summary = {"error": str(e)}

    return {
        "submission_id": submission.id,
        "status": submission.status,
        "records_received": report.total_received,
        "records_inserted": total_inserted,
        "records_skipped_total": total_skipped,
        "warnings": report.total_warning,
        "errors": report.total_error,
        "by_payload": inserted,
        "by_payload_skipped": skipped,
        "analytics": analytics_summary,
    }


# ---------------------------------------------------------------------------
# Listing
# ---------------------------------------------------------------------------
@router.get(
    "/submissions",
    dependencies=[
        Depends(require_roles(RoleEnum.ADMIN, RoleEnum.ANALYST, RoleEnum.SUPERVISOR))
    ],
)
async def list_submissions(
    entity_id: int | None = None,
    period_id: int | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    stmt = select(DataSubmission).order_by(DataSubmission.created_at.desc()).limit(500)
    if entity_id is not None:
        stmt = stmt.where(DataSubmission.entity_id == entity_id)
    if period_id is not None:
        stmt = stmt.where(DataSubmission.period_id == period_id)

    rows = (await db.execute(stmt)).scalars().all()
    return [
        {
            "id": r.id,
            "entity_id": r.entity_id,
            "period_id": r.period_id,
            "submitted_by": r.submitted_by,
            "file_name": r.file_name,
            "format": r.format,
            "payload_type": r.payload_type,
            "status": r.status,
            "records_received": r.records_received,
            "records_valid": r.records_valid,
            "records_warning": r.records_warning,
            "records_error": r.records_error,
            "created_at": r.created_at.isoformat()
            if isinstance(r.created_at, datetime)
            else r.created_at,
        }
        for r in rows
    ]


@router.get(
    "/submissions/{submission_id}",
    dependencies=[
        Depends(require_roles(RoleEnum.ADMIN, RoleEnum.ANALYST, RoleEnum.SUPERVISOR))
    ],
)
async def get_submission(
    submission_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    sub = (
        await db.execute(select(DataSubmission).where(DataSubmission.id == submission_id))
    ).scalar_one_or_none()
    if sub is None:
        raise HTTPException(status_code=404, detail="Submission not found")
    return {
        "id": sub.id,
        "entity_id": sub.entity_id,
        "period_id": sub.period_id,
        "submitted_by": sub.submitted_by,
        "file_name": sub.file_name,
        "format": sub.format,
        "payload_type": sub.payload_type,
        "status": sub.status,
        "records_received": sub.records_received,
        "records_valid": sub.records_valid,
        "records_warning": sub.records_warning,
        "records_error": sub.records_error,
        "validation_report": sub.validation_report,
        "created_at": sub.created_at.isoformat()
        if isinstance(sub.created_at, datetime)
        else sub.created_at,
    }