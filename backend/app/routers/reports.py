"""
Reports endpoints.

    GET /api/v1/reports/pdf?period_id=N        → download full PDF
    GET /api/v1/reports/findings.csv?period_id=N  → findings CSV
    GET /api/v1/reports/decisions.csv?period_id=N → decisions CSV
    GET /api/v1/reports/available?period_id=N  → JSON summary of what's available

Every download is recorded in the audit log.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import record_audit
from app.database import get_db
from app.deps import get_current_user, require_roles
from app.models.user import RoleEnum, User
from app.reports.generator import (
    collect_period_data,
    generate_decisions_csv,
    generate_findings_csv,
    generate_pdf,
)

router = APIRouter(prefix="/reports", tags=["reports"])


async def _audit_download(
    db: AsyncSession,
    *,
    user: User,
    period_id: int,
    report_type: str,
    filename: str,
) -> None:
    await record_audit(
        db,
        user_id=user.id,
        action="REPORT_DOWNLOAD",
        target_type="assessment_period",
        target_id=period_id,
        new_value={"report_type": report_type, "file_name": filename},
    )
    await db.commit()


# ---------------------------------------------------------------------------
# Availability summary
# ---------------------------------------------------------------------------
@router.get(
    "/available",
    dependencies=[Depends(require_roles(RoleEnum.ADMIN, RoleEnum.ANALYST, RoleEnum.SUPERVISOR))],
)
async def available(
    period_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
) -> dict:
    data = await collect_period_data(db, period_id)
    return {
        "period_id": period_id,
        "period_label": data["period"].label,
        "entities": len(data["entities"]),
        "findings": data["totals"]["findings"],
        "decisions": data["totals"]["decisions"],
        "audits": len(data["audits"]),
        "formats": [
            {"id": "pdf", "label": "Supervisory Report (PDF)"},
            {"id": "findings_csv", "label": "Findings (CSV)"},
            {"id": "decisions_csv", "label": "Supervisor Decisions (CSV)"},
        ],
    }


# ---------------------------------------------------------------------------
# PDF download
# ---------------------------------------------------------------------------
@router.get(
    "/pdf",
    dependencies=[Depends(require_roles(RoleEnum.ADMIN, RoleEnum.ANALYST, RoleEnum.SUPERVISOR))],
)
async def download_pdf(
    period_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    try:
        data = await collect_period_data(db, period_id)
        pdf_bytes = generate_pdf(data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {e}")

    ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    filename = f"SAT-SA-Supervisory-Report-{data['period'].label}-{ts}.pdf"

    await _audit_download(
        db,
        user=current_user,
        period_id=period_id,
        report_type="pdf",
        filename=filename,
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# Findings CSV
# ---------------------------------------------------------------------------
@router.get(
    "/findings.csv",
    dependencies=[Depends(require_roles(RoleEnum.ADMIN, RoleEnum.ANALYST, RoleEnum.SUPERVISOR))],
)
async def download_findings_csv(
    period_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    try:
        data = await collect_period_data(db, period_id)
        csv_bytes = generate_findings_csv(data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CSV generation failed: {e}")

    ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    filename = f"SAT-SA-Findings-{data['period'].label}-{ts}.csv"

    await _audit_download(
        db,
        user=current_user,
        period_id=period_id,
        report_type="findings_csv",
        filename=filename,
    )

    return Response(
        content=csv_bytes,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# Decisions CSV
# ---------------------------------------------------------------------------
@router.get(
    "/decisions.csv",
    dependencies=[Depends(require_roles(RoleEnum.ADMIN, RoleEnum.ANALYST, RoleEnum.SUPERVISOR))],
)
async def download_decisions_csv(
    period_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    try:
        data = await collect_period_data(db, period_id)
        csv_bytes = generate_decisions_csv(data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CSV generation failed: {e}")

    ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    filename = f"SAT-SA-Decisions-{data['period'].label}-{ts}.csv"

    await _audit_download(
        db,
        user=current_user,
        period_id=period_id,
        report_type="decisions_csv",
        filename=filename,
    )

    return Response(
        content=csv_bytes,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )