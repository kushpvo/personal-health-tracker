from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Biomarker, Report, ReportResult
from app.schemas.schemas import (
    BiomarkerDetail, BiomarkerInfo, BiomarkerListItem, BiomarkerSummary, ResultPoint,
)

router = APIRouter(prefix="/api/biomarkers", tags=["biomarkers"])


def _compute_zone(value: float, b: Biomarker) -> str:
    """Return zone string based on value vs biomarker reference ranges."""
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


def _to_result_point(result: ReportResult) -> ResultPoint:
    zone = "unknown"
    if result.biomarker and not result.is_flagged_unknown:
        zone = _compute_zone(result.value, result.biomarker)
    return ResultPoint(
        id=result.id,
        report_id=result.report_id,
        report_name=result.report.report_name if result.report else None,
        sample_date=result.report.sample_date if result.report else None,
        value=result.value,
        unit=result.unit,
        zone=zone,
    )


@router.get("/list", response_model=List[BiomarkerListItem])
def list_all_biomarkers(db: Session = Depends(get_db)):
    """All biomarkers alphabetically — for dropdowns. Must be before /{biomarker_id}."""
    biomarkers = db.query(Biomarker).order_by(Biomarker.name.asc()).all()
    return [
        BiomarkerListItem(
            id=b.id,
            name=b.name,
            category=b.category,
            default_unit=b.default_unit,
            alternate_units=b.alternate_units or [],
        )
        for b in biomarkers
    ]


@router.get("/summary", response_model=List[BiomarkerSummary])
def get_dashboard_summary(db: Session = Depends(get_db)):
    """
    Returns one entry per biomarker the user has data for.
    Each entry has the latest result and zone.
    """
    biomarkers = db.query(Biomarker).all()
    summaries = []

    for b in biomarkers:
        results = (
            db.query(ReportResult)
            .filter(
                ReportResult.biomarker_id == b.id,
                ReportResult.is_flagged_unknown == False,
            )
            .join(Report)
            .order_by(Report.sample_date.desc(), Report.uploaded_at.desc())
            .all()
        )
        if not results:
            continue

        latest = results[0]
        zone = _compute_zone(latest.value, b)

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
                ),
                latest_value=latest.value,
                latest_unit=latest.unit,
                latest_date=latest.report.sample_date if latest.report else None,
                latest_zone=zone,
                result_count=len(results),
            )
        )

    return sorted(summaries, key=lambda s: s.biomarker.category or "")


@router.get("/{biomarker_id}", response_model=BiomarkerDetail)
def get_biomarker_detail(biomarker_id: int, db: Session = Depends(get_db)):
    b = db.query(Biomarker).filter(Biomarker.id == biomarker_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Biomarker not found.")

    results = (
        db.query(ReportResult)
        .filter(
            ReportResult.biomarker_id == b.id,
            ReportResult.is_flagged_unknown == False,
        )
        .join(Report)
        .order_by(Report.sample_date.asc())
        .all()
    )

    return BiomarkerDetail(
        biomarker=BiomarkerInfo(
            id=b.id,
            name=b.name,
            category=b.category,
            default_unit=b.default_unit,
            optimal_min=b.optimal_min,
            optimal_max=b.optimal_max,
            sufficient_min=b.sufficient_min,
            sufficient_max=b.sufficient_max,
        ),
        results=[_to_result_point(r) for r in results],
    )
