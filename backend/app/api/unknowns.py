from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.auth import get_effective_user_id
from app.db.database import get_db
from app.db.models import Biomarker, Report, ReportResult, UnknownBiomarker
from app.schemas.schemas import ResolveUnknownInput, UnknownBiomarkerItem

router = APIRouter(prefix="/api/unknowns", tags=["unknowns"])


@router.get("", response_model=List[UnknownBiomarkerItem])
def list_unknowns(
    db: Session = Depends(get_db),
    effective_user_id: int = Depends(get_effective_user_id),
):
    """Return unknown biomarker names seen in this user's reports, unresolved only."""
    user_raw_names = (
        db.query(ReportResult.raw_name)
        .join(Report)
        .filter(
            Report.user_id == effective_user_id,
            ReportResult.is_flagged_unknown == True,
        )
        .distinct()
        .all()
    )
    names = {row[0] for row in user_raw_names}
    if not names:
        return []

    unknowns = (
        db.query(UnknownBiomarker)
        .filter(
            UnknownBiomarker.raw_name.in_(names),
            UnknownBiomarker.resolved_biomarker_id.is_(None),
        )
        .order_by(UnknownBiomarker.times_seen.desc())
        .all()
    )
    return unknowns


@router.patch("/{unknown_id}/resolve", response_model=UnknownBiomarkerItem)
def resolve_unknown(
    unknown_id: int,
    body: ResolveUnknownInput,
    db: Session = Depends(get_db),
    effective_user_id: int = Depends(get_effective_user_id),
):
    unknown = db.query(UnknownBiomarker).filter(UnknownBiomarker.id == unknown_id).first()
    if not unknown:
        raise HTTPException(status_code=404, detail="Unknown biomarker not found.")

    biomarker = db.query(Biomarker).filter(Biomarker.id == body.biomarker_id).first()
    if not biomarker:
        raise HTTPException(status_code=404, detail="Biomarker not found.")

    unknown.resolved_biomarker_id = body.biomarker_id

    aliases = list(biomarker.aliases or [])
    normalized = unknown.raw_name.lower().strip()
    if normalized not in aliases:
        aliases.append(normalized)
        biomarker.aliases = aliases

    # Collect result IDs to update (join then update not supported in SQLAlchemy legacy query API)
    user_report_ids = (
        db.query(Report.id)
        .filter(Report.user_id == effective_user_id)
        .scalar_subquery()
    )
    result_ids = [
        r.id for r in db.query(ReportResult.id)
        .filter(
            ReportResult.report_id.in_(user_report_ids),
            ReportResult.raw_name == unknown.raw_name,
            ReportResult.is_flagged_unknown == True,
        )
        .all()
    ]
    if result_ids:
        db.query(ReportResult).filter(ReportResult.id.in_(result_ids)).update(
            {
                ReportResult.biomarker_id: body.biomarker_id,
                ReportResult.is_flagged_unknown: False,
                ReportResult.human_matched: True,
            },
            synchronize_session=False,
        )

    db.commit()
    db.refresh(unknown)
    return unknown
