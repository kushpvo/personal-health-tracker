import os
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Report, ReportResult
from app.schemas.schemas import ReportListItem, ReportStatus, ReportUploadResponse
from app.services.pipeline import run_pipeline

router = APIRouter(prefix="/api/reports", tags=["reports"])

DATA_DIR = os.getenv("DATA_DIR", "./data")
UPLOADS_DIR = os.path.join(DATA_DIR, "uploads")
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "50"))
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp"}


def _uploads_dir() -> str:
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    return UPLOADS_DIR


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
