from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, get_effective_user_id
from app.db.database import get_db
from app.db.models import Biomarker, Report, ReportResult, User
from app.schemas.schemas import (
    BiomarkerDetail, BiomarkerInfo, BiomarkerListItem, BiomarkerSummary, ResultPoint,
    ChangeDefaultUnitInput,
)
from app.services.unit_converter import normalize_unit
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
def list_all_biomarkers(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
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
def get_dashboard_summary(
    db: Session = Depends(get_db),
    effective_user_id: int = Depends(get_effective_user_id),
):
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
            .filter(Report.user_id == effective_user_id)
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
                    alternate_units=b.alternate_units or [],
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
def get_biomarker_detail(
    biomarker_id: int,
    db: Session = Depends(get_db),
    effective_user_id: int = Depends(get_effective_user_id),
):
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
        .filter(Report.user_id == effective_user_id)
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
            alternate_units=b.alternate_units or [],
        ),
        results=[_to_result_point(r) for r in results],
    )


@router.patch("/{biomarker_id}/default-unit", response_model=BiomarkerInfo)
def change_default_unit(
    biomarker_id: int,
    body: ChangeDefaultUnitInput,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    b = db.query(Biomarker).filter(Biomarker.id == biomarker_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Biomarker not found.")

    new_unit = normalize_unit(body.unit)
    current_unit = normalize_unit(b.default_unit or "")

    if new_unit == current_unit:
        return BiomarkerInfo(
            id=b.id, name=b.name, category=b.category, default_unit=b.default_unit,
            optimal_min=b.optimal_min, optimal_max=b.optimal_max,
            sufficient_min=b.sufficient_min, sufficient_max=b.sufficient_max,
            alternate_units=b.alternate_units or [],
        )

    valid_units = {normalize_unit(u) for u in (b.alternate_units or [])}
    if new_unit not in valid_units:
        raise HTTPException(status_code=400, detail=f"Unit '{new_unit}' is not a known alternate unit.")

    conversions = b.unit_conversions or {}
    factor = conversions.get(current_unit, {}).get(new_unit)
    if factor is None:
        raise HTTPException(status_code=400, detail=f"No conversion factor from '{current_unit}' to '{new_unit}'.")

    def _conv(v):
        return round(v * factor, 4) if v is not None else None

    b.optimal_min = _conv(b.optimal_min)
    b.optimal_max = _conv(b.optimal_max)
    b.sufficient_min = _conv(b.sufficient_min)
    b.sufficient_max = _conv(b.sufficient_max)

    old_unit = b.default_unit
    b.default_unit = new_unit
    # Keep alternate_units consistent: remove new default, add old default
    alts = [u for u in (b.alternate_units or []) if normalize_unit(u) != new_unit]
    if old_unit and normalize_unit(old_unit) not in {normalize_unit(u) for u in alts}:
        alts.append(old_unit)
    b.alternate_units = alts

    results = (
        db.query(ReportResult)
        .filter(ReportResult.biomarker_id == biomarker_id, ReportResult.is_flagged_unknown == False)
        .all()
    )
    for r in results:
        r_factor = conversions.get(normalize_unit(r.unit), {}).get(new_unit)
        if r_factor is not None:
            r.value = round(r.value * r_factor, 6)
            r.unit = new_unit

    db.commit()
    db.refresh(b)
    return BiomarkerInfo(
        id=b.id, name=b.name, category=b.category, default_unit=b.default_unit,
        optimal_min=b.optimal_min, optimal_max=b.optimal_max,
        sufficient_min=b.sufficient_min, sufficient_max=b.sufficient_max,
        alternate_units=b.alternate_units or [],
    )
