import os
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Biomarker, Report, ReportResult, UnknownBiomarker
from app.schemas.schemas import (
    BiomarkerInfo, BiomarkerSummary,
    ReportListItem, ReportResultItem, ReportStatus, ReportUploadResponse,
    ReviewReportInput,
)
from app.services.pipeline import run_pipeline
from app.services.unit_converter import convert_to_default_unit

router = APIRouter(prefix="/api/reports", tags=["reports"])

DATA_DIR = os.getenv("DATA_DIR", "./data")
UPLOADS_DIR = os.path.join(DATA_DIR, "uploads")
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "50"))
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp"}


def _uploads_dir() -> str:
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    return UPLOADS_DIR


def _compute_zone(value: float, b: Biomarker) -> str:
    opt_min = b.optimal_min
    opt_max = b.optimal_max
    suf_min = b.sufficient_min
    suf_max = b.sufficient_max

    if opt_min is not None and opt_max is not None:
        if opt_min <= value <= opt_max:
            return "optimal"
    if suf_min is not None and suf_max is not None:
        if suf_min <= value <= suf_max:
            return "sufficient"
    return "out_of_range"


@router.post("", response_model=ReportUploadResponse, status_code=201)
async def upload_report(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported file type '{suffix}'. Allowed: {sorted(ALLOWED_EXTENSIONS)}",
        )

    content = await file.read()
    if len(content) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File exceeds {MAX_UPLOAD_MB} MB limit.")

    stored_name = f"{uuid.uuid4()}{suffix}"
    file_path = os.path.join(_uploads_dir(), stored_name)
    with open(file_path, "wb") as f:
        f.write(content)

    report = Report(
        filename=stored_name,
        original_filename=file.filename or stored_name,
        file_path=file_path,
        status="pending",
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    background_tasks.add_task(run_pipeline, report.id, db)

    return ReportUploadResponse(id=report.id, status=report.status)


@router.get("", response_model=list[ReportListItem])
def list_reports(db: Session = Depends(get_db)):
    reports = db.query(Report).order_by(Report.uploaded_at.desc()).all()
    items = []
    for r in reports:
        count = db.query(ReportResult).filter(ReportResult.report_id == r.id).count()
        items.append(
            ReportListItem(
                id=r.id,
                report_name=r.report_name,
                original_filename=r.original_filename,
                sample_date=r.sample_date,
                uploaded_at=r.uploaded_at,
                status=r.status,
                result_count=count,
            )
        )
    return items


@router.get("/{report_id}/status", response_model=ReportStatus)
def get_report_status(report_id: int, db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    return ReportStatus(
        id=report.id, status=report.status, error_message=report.error_message
    )


@router.get("/{report_id}/download")
def download_report(report_id: int, db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    if not os.path.exists(report.file_path):
        raise HTTPException(status_code=404, detail="File not found on disk.")
    return FileResponse(
        path=report.file_path,
        filename=report.original_filename,
        media_type="application/octet-stream",
    )


@router.delete("/{report_id}", status_code=204)
def delete_report(report_id: int, db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    if os.path.exists(report.file_path):
        os.remove(report.file_path)
    db.delete(report)
    db.commit()


@router.get("/{report_id}/results", response_model=list[ReportResultItem])
def get_report_results(report_id: int, db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    results = (
        db.query(ReportResult)
        .filter(ReportResult.report_id == report_id)
        .order_by(ReportResult.sort_order.asc().nullslast())
        .all()
    )
    return [
        ReportResultItem(
            id=r.id,
            raw_name=r.raw_name,
            value=r.value,
            unit=r.unit,
            is_flagged_unknown=r.is_flagged_unknown,
            human_matched=r.human_matched or False,
            sort_order=r.sort_order,
            biomarker_id=r.biomarker_id,
            biomarker_name=r.biomarker.name if r.biomarker else None,
        )
        for r in results
    ]


@router.get("/{report_id}/summary", response_model=list[BiomarkerSummary])
def get_report_summary(report_id: int, db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    results = (
        db.query(ReportResult)
        .filter(
            ReportResult.report_id == report_id,
            ReportResult.biomarker_id.isnot(None),
            ReportResult.is_flagged_unknown == False,
        )
        .order_by(ReportResult.sort_order.asc().nullslast())
        .all()
    )

    seen = set()
    summaries = []
    for r in results:
        if r.biomarker_id in seen:
            continue
        seen.add(r.biomarker_id)
        b = r.biomarker
        if not b:
            continue
        zone = _compute_zone(r.value, b)
        summaries.append(
            BiomarkerSummary(
                biomarker=BiomarkerInfo(
                    id=b.id,
                    name=b.name,
                    category=b.category,
                    default_unit=b.default_unit,
                    optimal_min=b.optimal_min,
                    optimal_max=b.optimal_max,
                    sufficient_min=b.sufficient_min,
                    sufficient_max=b.sufficient_max,
                    alternate_units=b.alternate_units or [],
                ),
                latest_value=r.value,
                latest_unit=r.unit,
                latest_date=report.sample_date,
                latest_zone=zone,
                result_count=1,
            )
        )
    return summaries


@router.put("/{report_id}/review", response_model=ReportStatus)
def submit_review(report_id: int, body: ReviewReportInput, db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")

    report.report_name = body.report_name
    if body.sample_date:
        report.sample_date = body.sample_date

    for item in body.results:
        result = db.query(ReportResult).filter(ReportResult.id == item.id).first()
        if not result:
            continue

        result.value = item.value
        result.unit = item.unit

        if item.biomarker_id and result.biomarker_id != item.biomarker_id:
            biomarker = db.query(Biomarker).filter(Biomarker.id == item.biomarker_id).first()
            if biomarker:
                converted_value, used_unit = convert_to_default_unit(
                    item.value, item.unit, biomarker
                )
                result.value = converted_value
                result.unit = used_unit
                result.biomarker_id = item.biomarker_id
                result.is_flagged_unknown = False
                result.human_matched = True

                unknown = (
                    db.query(UnknownBiomarker)
                    .filter(UnknownBiomarker.raw_name == result.raw_name)
                    .first()
                )
                if unknown:
                    unknown.resolved_biomarker_id = item.biomarker_id

    db.commit()
    return ReportStatus(
        id=report.id, status=report.status, error_message=report.error_message
    )
