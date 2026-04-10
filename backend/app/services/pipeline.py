import os
import re
import shutil
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.db.models import Biomarker, Report, ReportResult, UnknownBiomarker
from app.services.ocr.base import OCRBackend
from app.services.ocr.tesseract import TesseractBackend
from app.services.preprocessor import prepare_images
from app.services.parser import extract_biomarkers, extract_metadata
from app.services.unit_converter import convert_to_default_unit, normalize_unit


def _get_ocr_backend() -> OCRBackend:
    backend_name = os.getenv("OCR_BACKEND", "tesseract").lower()
    if backend_name == "tesseract":
        return TesseractBackend()
    raise ValueError(f"Unknown OCR_BACKEND: {backend_name}")


def _match_biomarker(raw_name: str, db: Session) -> Optional[Biomarker]:
    """Find a biomarker by matching raw_name against name and aliases."""
    normalized = raw_name.lower().strip()
    normalized = re.sub(r"\s+", " ", normalized)
    simplified = re.sub(r"\s*\([^)]*\)", "", normalized).strip()
    biomarkers = db.query(Biomarker).all()
    for b in biomarkers:
        names = [b.name.lower(), *((b.aliases or []))]
        normalized_names = [re.sub(r"\s+", " ", name.strip().lower()) for name in names]
        if normalized in normalized_names or simplified in normalized_names:
            return b
    return None


def _upsert_unknown(raw_name: str, raw_unit: str, db: Session) -> None:
    existing = (
        db.query(UnknownBiomarker)
        .filter(UnknownBiomarker.raw_name == raw_name)
        .first()
    )
    now = datetime.utcnow()
    if existing:
        existing.times_seen += 1
        existing.last_seen_at = now
    else:
        db.add(
            UnknownBiomarker(
                raw_name=raw_name,
                raw_unit=raw_unit,
                first_seen_at=now,
                last_seen_at=now,
            )
        )


def run_pipeline(report_id: int, db: Session) -> None:
    """Full OCR → parse → match → store pipeline for a report."""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        return

    report.status = "processing"
    db.commit()

    tmp_images = []
    try:
        ocr = _get_ocr_backend()
        tmp_images = prepare_images(report.file_path)

        if not tmp_images:
            raise RuntimeError("No pages extracted from file.")

        # Concatenate text from all pages
        full_text = "\n".join(ocr.extract_text(p) for p in tmp_images)
        report.ocr_raw_text = full_text

        if not full_text.strip():
            raise RuntimeError("OCR produced no text. Try a higher-quality scan.")

        # Extract metadata
        meta = extract_metadata(full_text)
        if meta.get("sample_date"):
            report.sample_date = meta["sample_date"]
        if not report.report_name:
            report.report_name = os.path.splitext(report.original_filename)[0]

        db.query(ReportResult).filter(ReportResult.report_id == report.id).delete()

        # Extract and persist biomarker results
        parsed = extract_biomarkers(full_text)
        if not parsed:
            raise RuntimeError("OCR completed, but no biomarker rows could be parsed from the report.")

        for item in parsed:
            biomarker = _match_biomarker(item.raw_name, db)
            is_unknown = biomarker is None

            if is_unknown:
                _upsert_unknown(item.raw_name, item.unit, db)
                result = ReportResult(
                    report_id=report.id,
                    biomarker_id=None,
                    raw_name=item.raw_name,
                    value=item.value,
                    unit=item.unit,
                    is_flagged_unknown=True,
                )
            else:
                converted_value, used_unit = convert_to_default_unit(
                    item.value, item.unit, biomarker
                )
                result = ReportResult(
                    report_id=report.id,
                    biomarker_id=biomarker.id,
                    raw_name=item.raw_name,
                    value=converted_value,
                    unit=used_unit,
                    is_flagged_unknown=False,
                )
            db.add(result)

        report.status = "done"
        db.commit()

    except Exception as exc:
        report.status = "failed"
        report.error_message = str(exc)
        db.commit()
        raise

    finally:
        # Clean up temp images (all pages share the same tmpdir)
        for p in tmp_images:
            try:
                shutil.rmtree(os.path.dirname(p), ignore_errors=True)
                break
            except Exception:
                pass
