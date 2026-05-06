import io
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.shapes import Drawing, Rect
from reportlab.graphics.widgets.markers import makeMarker
from reportlab.lib import colors
from reportlab.lib.colors import Color
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.orm import Session, selectinload

from app.core.auth import get_current_user, get_effective_user_id
from app.db.database import get_db
from app.db.models import Biomarker, Report, ReportResult, SupplementLog, User
from app.schemas.schemas import CustomExportInput
from app.services.unit_converter import convert_to_default_unit, pick_best_result

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

        # Deduplicate per report
        by_report = {}
        for r in results:
            by_report.setdefault(r.report_id, []).append(r)
        deduped = []
        for group in by_report.values():
            chosen = pick_best_result(group, b)
            if chosen:
                deduped.append(chosen)
        if not deduped:
            continue
        deduped.sort(
            key=lambda r: (r.report.sample_date or date.min, r.report.uploaded_at or datetime.min),
            reverse=True,
        )

        latest = deduped[0]
        nv, nu = convert_to_default_unit(latest.value, latest.unit, b)
        zone = _compute_zone(nv, b)
        rows.append((
            b.name,
            b.category or "—",
            f"{nv:.3f} {nu}",
            zone,
            latest.report.sample_date.strftime("%d %b %Y") if latest.report and latest.report.sample_date else "—",
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
        f"User: {current_user.username} &nbsp;&nbsp; Generated: {date.today().strftime('%d %b %Y')}",
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
    filename = f"health-summary-{date.today().strftime('%d %b %Y')}.pdf"
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _build_biomarker_chart(b: Biomarker, values, date_labels, drawing_width=460, drawing_height=140):
    drawing = Drawing(drawing_width, drawing_height)

    all_vals = list(values)
    for attr in ("optimal_min", "optimal_max", "sufficient_min", "sufficient_max"):
        v = getattr(b, attr)
        if v is not None:
            all_vals.append(v)

    if not all_vals:
        all_vals = [0, 1]

    y_min = min(all_vals)
    y_max = max(all_vals)
    pad = (y_max - y_min) * 0.1 if y_max != y_min else 0.1
    y_min -= pad
    y_max += pad
    if y_min == y_max:
        y_min -= 1
        y_max += 1

    left_margin = max(25, int(50 * (drawing_width / 460)))
    bottom_margin = max(15, int(25 * (drawing_height / 140)))
    plot_width = max(140, int(400 * (drawing_width / 460)))
    plot_height = max(55, int(100 * (drawing_height / 140)))

    def val_to_py(v):
        if y_max == y_min:
            return bottom_margin + plot_height / 2
        ratio = (v - y_min) / (y_max - y_min)
        return bottom_margin + ratio * plot_height

    # Sufficient band
    if b.sufficient_min is not None and b.sufficient_max is not None:
        band_bottom = val_to_py(b.sufficient_min)
        band_top = val_to_py(b.sufficient_max)
        if band_top > band_bottom:
            rect = Rect(
                left_margin, band_bottom, plot_width, band_top - band_bottom,
                fillColor=Color(0.024, 0.714, 0.831, alpha=0.15),
                strokeColor=None,
            )
            drawing.add(rect)

    # Optimal band
    if b.optimal_min is not None and b.optimal_max is not None:
        band_bottom = val_to_py(b.optimal_min)
        band_top = val_to_py(b.optimal_max)
        if band_top > band_bottom:
            rect = Rect(
                left_margin, band_bottom, plot_width, band_top - band_bottom,
                fillColor=Color(0.133, 0.773, 0.369, alpha=0.20),
                strokeColor=None,
            )
            drawing.add(rect)

    lp = LinePlot()
    lp.x = left_margin
    lp.y = bottom_margin
    lp.width = plot_width
    lp.height = plot_height
    data_points = list(enumerate(values))
    lp.data = [data_points]
    lp.lines[0].strokeColor = colors.HexColor("#3b82f6")
    lp.lines[0].strokeWidth = 2
    lp.lines[0].symbol = makeMarker("FilledCircle")
    lp.lines[0].symbol.fillColor = colors.HexColor("#3b82f6")
    lp.lines[0].symbol.size = 4

    lp.yValueAxis.valueMin = y_min
    lp.yValueAxis.valueMax = y_max
    lp.xValueAxis.valueMin = 0
    lp.xValueAxis.valueMax = max(len(values) - 1, 1)
    lp.xValueAxis.valueStep = 1

    lp.xValueAxis.labelTextFormat = (
        lambda x: date_labels[int(round(x))] if 0 <= int(round(x)) < len(date_labels) else ""
    )
    lp.xValueAxis.labels.fontSize = 7

    drawing.add(lp)
    return drawing


def _build_supplement_table(s: SupplementLog, styles):
    heading = Paragraph(f"<b>{s.name}</b> ({s.frequency})", styles["Heading3"])
    dose_data = [["Dose", "Started", "Ended", "Days", "Status"]]
    for d in s.doses:
        if d.is_date_approximate:
            days_str = "—"
            started_str = f"~ {d.started_on.strftime('%d %b %Y')}" if d.started_on else "~ —"
            ended_str = f"~ {d.ended_on.strftime('%d %b %Y')}" if d.ended_on else "—"
        else:
            ended = d.ended_on or date.today()
            days = (ended - d.started_on).days + 1
            days_str = str(days)
            started_str = d.started_on.strftime("%d %b %Y")
            ended_str = d.ended_on.strftime("%d %b %Y") if d.ended_on else "—"
        row = [
            f"{d.dose} {s.unit}",
            started_str,
            ended_str,
            days_str,
            "Active" if d.ended_on is None else "Ended",
        ]
        dose_data.append(row)
    t = Table(dose_data, colWidths=[3.5 * cm, 3 * cm, 3 * cm, 2 * cm, 2.5 * cm])
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
    items = [heading, Spacer(1, 0.2 * cm), t]
    # Add date notes for approximate doses as a footnote
    for d in s.doses:
        if d.is_date_approximate and d.date_notes:
            items.append(Paragraph(
                f"<span style='font-size:8px;color:#6b7280;'>~ {d.date_notes}</span>",
                styles["Normal"],
            ))
    items.append(Spacer(1, 0.3 * cm))
    return items


@router.post("/custom-pdf")
def export_custom_pdf(
    body: CustomExportInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    effective_user_id: int = Depends(get_effective_user_id),
):
    if not body.biomarker_ids and not body.supplement_ids:
        raise HTTPException(status_code=400, detail="No biomarkers or supplements selected")

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
    )
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("Health Tracker — Custom Export", styles["Title"]))
    story.append(Paragraph(
        f"User: {current_user.username} &nbsp;&nbsp; Generated: {date.today().strftime('%d %b %Y')}",
        styles["Normal"],
    ))
    story.append(Spacer(1, 0.5 * cm))

    biomarker_sections = []

    for b_id in body.biomarker_ids:
        b = db.query(Biomarker).filter(Biomarker.id == b_id).first()
        if not b:
            continue
        results = (
            db.query(ReportResult)
            .filter(
                ReportResult.biomarker_id == b.id,
                ReportResult.is_flagged_unknown == False,
            )
            .join(Report)
            .filter(Report.user_id == effective_user_id)
            .order_by(Report.sample_date.asc(), Report.uploaded_at.asc())
            .all()
        )

        if not results:
            section_table = Table([
                [Paragraph(f"<b>{b.name}</b>", styles["Heading3"])],
                [Paragraph("No historical data available.", styles["Normal"])],
            ], colWidths=[8 * cm])
            section_table.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]))
            biomarker_sections.append(section_table)
            continue

        # Deduplicate per report
        by_report = {}
        for r in results:
            by_report.setdefault(r.report_id, []).append(r)
        deduped = []
        for group in by_report.values():
            chosen = pick_best_result(group, b)
            if chosen:
                deduped.append(chosen)
        deduped.sort(
            key=lambda r: (r.report.sample_date or date.min, r.report.uploaded_at or datetime.min)
        )

        normalized = []
        for r in deduped:
            nv, nu = convert_to_default_unit(r.value, r.unit, b)
            normalized.append((nv, nu, r.report))

        values = [nv for nv, nu, report in normalized]
        date_labels = [
            report.sample_date.strftime("%d %b %Y") if report and report.sample_date else ""
            for nv, nu, report in normalized
        ]

        chart = _build_biomarker_chart(b, values, date_labels, drawing_width=220, drawing_height=120)

        history_data = [["Date", "Value", "Unit", "Zone"]]
        for nv, nu, report in reversed(normalized):
            zone = _compute_zone(nv, b)
            history_data.append([
                report.sample_date.strftime("%d %b %Y") if report and report.sample_date else "—",
                f"{nv:.3f}",
                nu,
                zone,
            ])

        range_parts = []
        if b.optimal_min is not None and b.optimal_max is not None:
            range_parts.append(f"Optimal {b.optimal_min}–{b.optimal_max} {b.default_unit or ''}")
        if b.sufficient_min is not None and b.sufficient_max is not None:
            range_parts.append(f"Sufficient {b.sufficient_min}–{b.sufficient_max} {b.default_unit or ''}")
        range_text = f"Reference: {' | '.join(range_parts)}" if range_parts else ""

        history_table = Table(history_data, colWidths=[4 * cm, 2.5 * cm, 2.5 * cm, 2.5 * cm])
        history_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e5e7eb")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        for i, (nv, nu, report) in enumerate(reversed(normalized), start=1):
            zone = _compute_zone(nv, b)
            c = ZONE_COLORS.get(zone, colors.gray)
            history_table.setStyle(TableStyle([("TEXTCOLOR", (3, i), (3, i), c)]))

        section_flowables = [
            Paragraph(f"<b>{b.name}</b>", styles["Heading3"]),
        ]
        if range_text:
            section_flowables.append(Paragraph(f"<span style='font-size:8px'>{range_text}</span>", styles["Normal"]))
        section_flowables.append(chart)
        section_flowables.append(Spacer(1, 0.1 * cm))
        section_flowables.append(history_table)

        section_table = Table([[f] for f in section_flowables], colWidths=[8 * cm])
        section_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 1),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ]))
        biomarker_sections.append(section_table)

    if biomarker_sections:
        rows = []
        for i in range(0, len(biomarker_sections), 2):
            row = [biomarker_sections[i]]
            if i + 1 < len(biomarker_sections):
                row.append(biomarker_sections[i + 1])
            else:
                row.append(None)
            rows.append(row)

        main_table = Table(rows, colWidths=[8 * cm, 8 * cm])
        main_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        story.append(main_table)

    if body.supplement_ids:
        supplements = (
            db.query(SupplementLog)
            .options(selectinload(SupplementLog.doses))
            .filter(
                SupplementLog.user_id == effective_user_id,
                SupplementLog.id.in_(body.supplement_ids),
            )
            .order_by(SupplementLog.name)
            .all()
        )
        if supplements:
            story.append(Spacer(1, 0.5 * cm))
            story.append(Paragraph("Supplements", styles["Heading1"]))
            story.append(Spacer(1, 0.3 * cm))
            for s in supplements:
                story.extend(_build_supplement_table(s, styles))

    doc.build(story)

    buf.seek(0)
    filename = f"health-custom-export-{date.today().strftime('%d %b %Y')}.pdf"
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
