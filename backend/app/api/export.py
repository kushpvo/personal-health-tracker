import io
from datetime import date

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, get_effective_user_id
from app.db.database import get_db
from app.db.models import Biomarker, Report, ReportResult, User

router = APIRouter(prefix="/api/export", tags=["export"])

ZONE_COLORS = {
    "optimal": colors.HexColor("#22c55e"),
    "sufficient": colors.HexColor("#06b6d4"),
    "out_of_range": colors.HexColor("#f97316"),
}


def _compute_zone(value: float, b: Biomarker) -> str:
    if b.optimal_min is not None and b.optimal_max is not None:
        if b.optimal_min <= value <= b.optimal_max:
            return "optimal"
    if b.sufficient_min is not None and b.sufficient_max is not None:
        if b.sufficient_min <= value <= b.sufficient_max:
            return "sufficient"
    return "out_of_range"


@router.get("/pdf")
def export_pdf(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    effective_user_id: int = Depends(get_effective_user_id),
):
    biomarkers = db.query(Biomarker).all()
    rows = []
    for b in biomarkers:
        results = (
            db.query(ReportResult)
            .filter(
                ReportResult.biomarker_id == b.id,
                ReportResult.is_flagged_unknown == False,
            )
            .join(Report)
            .filter(Report.user_id == effective_user_id)
            .order_by(Report.sample_date.desc(), Report.uploaded_at.desc())
            .all()
        )
        if not results:
            continue
        latest = results[0]
        zone = _compute_zone(latest.value, b)
        rows.append((
            b.name,
            b.category or "—",
            f"{latest.value} {latest.unit}",
            zone,
            str(latest.report.sample_date) if latest.report and latest.report.sample_date else "—",
        ))

    rows.sort(key=lambda r: r[1])  # sort by category

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
    )
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("Health Tracker — Latest Results", styles["Title"]))
    story.append(Paragraph(
        f"User: {current_user.username} &nbsp;&nbsp; Generated: {date.today()}",
        styles["Normal"],
    ))
    story.append(Spacer(1, 0.5 * cm))

    table_data = [["Biomarker", "Category", "Value", "Zone", "Sample Date"]] + [list(r) for r in rows]
    t = Table(table_data, colWidths=[5 * cm, 3.5 * cm, 3.5 * cm, 3 * cm, 3 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e5e7eb")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    for i, row in enumerate(rows, start=1):
        zone = row[3]
        c = ZONE_COLORS.get(zone, colors.gray)
        t.setStyle(TableStyle([("TEXTCOLOR", (3, i), (3, i), c)]))

    story.append(t)
    doc.build(story)

    buf.seek(0)
    filename = f"health-summary-{date.today()}.pdf"
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
