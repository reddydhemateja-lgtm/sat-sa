"""
Report generation.

Produces supervisory reports in PDF and CSV formats from the current
state of the database for a given assessment period.

PDF via reportlab (pure-Python, offline).
CSV via pandas (already a project dependency).
"""

from __future__ import annotations

import io
from collections import Counter
from datetime import datetime
from decimal import Decimal
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analytics import Evidence, Finding
from app.models.audit import AuditLog
from app.models.cse import CSEEntity
from app.models.operational import Alert, Case, Escalation, Investigation
from app.models.period import AssessmentPeriod
from app.models.review import ReviewDecision
from app.models.user import User


# ---------------------------------------------------------------------------
# Data collection
# ---------------------------------------------------------------------------
async def collect_period_data(
    db: AsyncSession, period_id: int
) -> dict[str, Any]:
    """Gather everything needed for a period report."""

    period = (
        await db.execute(select(AssessmentPeriod).where(AssessmentPeriod.id == period_id))
    ).scalar_one_or_none()
    if period is None:
        raise ValueError(f"Period {period_id} not found")

    entities = (
        await db.execute(select(CSEEntity).order_by(CSEEntity.id))
    ).scalars().all()

    findings = (
        await db.execute(
            select(Finding).where(Finding.period_id == period_id).order_by(Finding.id)
        )
    ).scalars().all()

    decisions = (
        await db.execute(
            select(ReviewDecision).order_by(ReviewDecision.decided_at.desc()).limit(500)
        )
    ).scalars().all()

    audits = (
        await db.execute(
            select(AuditLog).order_by(AuditLog.created_at.desc()).limit(500)
        )
    ).scalars().all()

    total_alerts = (
        await db.execute(select(func.count(Alert.id)).where(Alert.period_id == period_id))
    ).scalar_one()
    total_cases = (
        await db.execute(select(func.count(Case.id)).where(Case.period_id == period_id))
    ).scalar_one()
    total_investigations = (
        await db.execute(select(func.count(Investigation.id)))
    ).scalar_one()
    total_escalations = (await db.execute(select(func.count(Escalation.id)))).scalar_one()

    # aggregate findings by entity
    findings_by_entity: dict[int, list[Finding]] = {}
    for f in findings:
        findings_by_entity.setdefault(f.entity_id, []).append(f)

    # aggregate findings by category
    by_category = Counter(f.category.value for f in findings)

    # aggregate decisions by type
    by_decision = Counter(d.decision.value for d in decisions)

    return {
        "period": period,
        "entities": entities,
        "findings": findings,
        "findings_by_entity": findings_by_entity,
        "by_category": dict(by_category),
        "by_decision": dict(by_decision),
        "decisions": decisions,
        "audits": audits,
        "totals": {
            "alerts": int(total_alerts),
            "cases": int(total_cases),
            "investigations": int(total_investigations),
            "escalations": int(total_escalations),
            "findings": len(findings),
            "decisions": len(decisions),
        },
    }


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------
NAVY = colors.HexColor("#0e1a30")
SLATE = colors.HexColor("#475569")
LIGHT = colors.HexColor("#f1f5f9")
ACCENT = colors.HexColor("#2563eb")
RED = colors.HexColor("#dc2626")
AMBER = colors.HexColor("#d97706")


def _styles() -> dict[str, ParagraphStyle]:
    ss = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "Title",
            parent=ss["Title"],
            fontSize=22,
            leading=26,
            textColor=NAVY,
            spaceAfter=4,
        ),
        "subtitle": ParagraphStyle(
            "Subtitle",
            parent=ss["Normal"],
            fontSize=10,
            leading=14,
            textColor=SLATE,
            spaceAfter=18,
        ),
        "h2": ParagraphStyle(
            "H2",
            parent=ss["Heading2"],
            fontSize=13,
            leading=16,
            textColor=NAVY,
            spaceBefore=16,
            spaceAfter=8,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=ss["BodyText"],
            fontSize=9.5,
            leading=13,
            textColor=colors.black,
        ),
        "small": ParagraphStyle(
            "Small",
            parent=ss["BodyText"],
            fontSize=8,
            leading=11,
            textColor=SLATE,
        ),
        "cell": ParagraphStyle(
            "Cell",
            parent=ss["BodyText"],
            fontSize=8,
            leading=11,
        ),
        "cellHeader": ParagraphStyle(
            "CellHeader",
            parent=ss["BodyText"],
            fontSize=8,
            leading=11,
            textColor=colors.white,
        ),
    }


def _header_row(texts: list[str], s: dict[str, ParagraphStyle]) -> list[Paragraph]:
    return [Paragraph(t, s["cellHeader"]) for t in texts]


def _table(data: list[list[Any]], col_widths: list[float]) -> Table:
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return t


def generate_pdf(data: dict[str, Any]) -> bytes:
    """Return PDF bytes for the given collected report data."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=1.6 * cm,
        rightMargin=1.6 * cm,
        topMargin=1.6 * cm,
        bottomMargin=1.6 * cm,
        title=f"SAT-SA Supervisory Report — {data['period'].label}",
    )

    s = _styles()
    story: list[Any] = []

    # ---------- Cover ----------
    story.append(Paragraph("SAT-SA", s["title"]))
    story.append(
        Paragraph(
            f"Supervisory Report &mdash; Assessment Period {data['period'].label}",
            s["subtitle"],
        )
    )
    story.append(
        Paragraph(
            f"Generated on {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')} "
            f"&middot; NTRO / NCIIPC &middot; Supervisory Analytics Tool for SOC Assessment",
            s["small"],
        )
    )
    story.append(Spacer(1, 14))

    # ---------- Executive summary ----------
    totals = data["totals"]
    story.append(Paragraph("Executive Summary", s["h2"]))
    summary_data = [
        _header_row(["Metric", "Value"], s),
        [Paragraph("Entities assessed", s["cell"]), Paragraph(str(len(data["entities"])), s["cell"])],
        [Paragraph("Alerts ingested", s["cell"]), Paragraph(f"{totals['alerts']:,}", s["cell"])],
        [Paragraph("Cases ingested", s["cell"]), Paragraph(f"{totals['cases']:,}", s["cell"])],
        [Paragraph("Investigations", s["cell"]), Paragraph(f"{totals['investigations']:,}", s["cell"])],
        [Paragraph("Escalations", s["cell"]), Paragraph(f"{totals['escalations']:,}", s["cell"])],
        [Paragraph("Findings raised", s["cell"]), Paragraph(str(totals["findings"]), s["cell"])],
        [Paragraph("Supervisor decisions recorded", s["cell"]), Paragraph(str(totals["decisions"]), s["cell"])],
    ]
    story.append(_table(summary_data, [8 * cm, 5 * cm]))

    # ---------- Findings by category ----------
    story.append(Paragraph("Findings by Category", s["h2"]))
    if data["by_category"]:
        cat_data = [_header_row(["Category", "Count"], s)]
        for cat, count in sorted(data["by_category"].items(), key=lambda x: -x[1]):
            cat_data.append(
                [
                    Paragraph(cat.replace("_", " ").title(), s["cell"]),
                    Paragraph(str(count), s["cell"]),
                ]
            )
        story.append(_table(cat_data, [8 * cm, 5 * cm]))
    else:
        story.append(Paragraph("No findings recorded for this period.", s["body"]))

    story.append(PageBreak())

    # ---------- Entities ----------
    story.append(Paragraph("Entities Assessed", s["h2"]))
    if data["entities"]:
        ent_data = [
            _header_row(
                ["Code", "Name", "Sector", "Criticality", "Peer group", "Findings"],
                s,
            )
        ]
        for e in data["entities"]:
            ent_data.append(
                [
                    Paragraph(e.code, s["cell"]),
                    Paragraph(e.name, s["cell"]),
                    Paragraph(e.sector, s["cell"]),
                    Paragraph(e.criticality, s["cell"]),
                    Paragraph(e.peer_group or "—", s["cell"]),
                    Paragraph(str(len(data["findings_by_entity"].get(e.id, []))), s["cell"]),
                ]
            )
        story.append(_table(ent_data, [2.4 * cm, 4.5 * cm, 2.4 * cm, 2.2 * cm, 3.2 * cm, 1.7 * cm]))

    # ---------- Top findings ----------
    story.append(Paragraph("Findings (top 50 by review indicator)", s["h2"]))
    findings_sorted = sorted(
        data["findings"], key=lambda f: float(f.review_indicator or 0), reverse=True
    )[:50]
    if findings_sorted:
        f_data = [
            _header_row(["Code", "Entity", "Category", "Priority", "Title"], s)
        ]
        for f in findings_sorted:
            entity_code = next(
                (e.code for e in data["entities"] if e.id == f.entity_id), "—"
            )
            f_data.append(
                [
                    Paragraph(f.code, s["cell"]),
                    Paragraph(entity_code, s["cell"]),
                    Paragraph(f.category.value.replace("_", " ").title(), s["cell"]),
                    Paragraph(f.priority.value, s["cell"]),
                    Paragraph(f.title[:90], s["cell"]),
                ]
            )
        story.append(_table(f_data, [2.4 * cm, 2.0 * cm, 2.6 * cm, 1.8 * cm, 8.0 * cm]))
    else:
        story.append(Paragraph("No findings recorded.", s["body"]))

    story.append(PageBreak())

    # ---------- Review decisions ----------
    story.append(Paragraph("Supervisory Decisions (recent 50)", s["h2"]))
    if data["decisions"]:
        d_data = [_header_row(["When", "Finding", "Decision", "Comment"], s)]
        for d in data["decisions"][:50]:
            d_data.append(
                [
                    Paragraph(d.decided_at.strftime("%Y-%m-%d %H:%M"), s["cell"]),
                    Paragraph(f"#{d.finding_id}", s["cell"]),
                    Paragraph(d.decision.value, s["cell"]),
                    Paragraph((d.comment or "")[:80], s["cell"]),
                ]
            )
        story.append(_table(d_data, [3.0 * cm, 2.0 * cm, 3.0 * cm, 8.4 * cm]))
    else:
        story.append(Paragraph("No supervisor decisions recorded.", s["body"]))

    # ---------- Audit trail ----------
    story.append(Paragraph("Audit Trail (recent 40 events)", s["h2"]))
    if data["audits"]:
        a_data = [_header_row(["When", "Action", "Target"], s)]
        for a in data["audits"][:40]:
            target = f"{a.target_type or ''} #{a.target_id or ''}".strip()
            a_data.append(
                [
                    Paragraph(a.created_at.strftime("%Y-%m-%d %H:%M"), s["cell"]),
                    Paragraph(a.action, s["cell"]),
                    Paragraph(target, s["cell"]),
                ]
            )
        story.append(_table(a_data, [3.0 * cm, 5.0 * cm, 8.4 * cm]))
    else:
        story.append(Paragraph("No audit events.", s["body"]))

    story.append(Spacer(1, 12))
    story.append(
        Paragraph(
            "This report is generated by SAT-SA, a supervisory analytics tool. "
            "It supports human supervisors and does not constitute a final "
            "security verdict.",
            s["small"],
        )
    )

    doc.build(story)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------------
def generate_findings_csv(data: dict[str, Any]) -> bytes:
    """CSV export of findings for the period. Opens in Excel."""
    import csv

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "finding_code",
            "entity_code",
            "category",
            "rule_id",
            "priority",
            "confidence",
            "review_indicator",
            "status",
            "title",
            "narrative",
            "expected_behavior",
            "observed_pattern",
            "analytical_basis",
            "created_at",
        ]
    )
    entity_by_id = {e.id: e.code for e in data["entities"]}
    for f in data["findings"]:
        writer.writerow(
            [
                f.code,
                entity_by_id.get(f.entity_id, ""),
                f.category.value,
                f.rule_id,
                f.priority.value,
                float(f.confidence) if isinstance(f.confidence, Decimal) else f.confidence,
                float(f.review_indicator) if isinstance(f.review_indicator, Decimal) else f.review_indicator,
                f.status,
                f.title,
                f.narrative,
                f.expected_behavior or "",
                f.observed_pattern or "",
                f.analytical_basis,
                f.created_at.isoformat() if isinstance(f.created_at, datetime) else f.created_at,
            ]
        )
    return buf.getvalue().encode("utf-8-sig")   # BOM so Excel opens it cleanly


def generate_decisions_csv(data: dict[str, Any]) -> bytes:
    """CSV export of supervisor decisions."""
    import csv

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        ["decision_id", "finding_id", "reviewer_id", "decision", "comment", "previous_decision", "decided_at"]
    )
    for d in data["decisions"]:
        writer.writerow(
            [
                d.id,
                d.finding_id,
                d.reviewer_id,
                d.decision.value,
                d.comment or "",
                d.previous_decision or "",
                d.decided_at.isoformat() if isinstance(d.decided_at, datetime) else d.decided_at,
            ]
        )
    return buf.getvalue().encode("utf-8-sig")