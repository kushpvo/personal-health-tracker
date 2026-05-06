from datetime import date, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session, selectinload

from app.core.auth import get_effective_user_id
from app.db.database import get_db
from app.db.models import SupplementDose, SupplementLog
from app.schemas.schemas import (
    AddDoseInput,
    CreateSupplementInput,
    SupplementDoseItem,
    SupplementLogItem,
    UpdateDoseInput,
    UpdateSupplementInput,
)

router = APIRouter(prefix="/api/supplements", tags=["supplements"])


def _dose_item(d: SupplementDose) -> SupplementDoseItem:
    return SupplementDoseItem(
        id=d.id,
        dose=d.dose,
        started_on=d.started_on,
        ended_on=d.ended_on,
        is_active=d.ended_on is None,
        date_notes=d.date_notes,
        is_date_approximate=d.is_date_approximate or False,
    )


def _log_item(s: SupplementLog) -> SupplementLogItem:
    return SupplementLogItem(
        id=s.id,
        name=s.name,
        unit=s.unit,
        frequency=s.frequency,
        notes=s.notes,
        created_at=s.created_at,
        doses=[_dose_item(d) for d in s.doses],
    )


def _get_supplement_or_404(
    supplement_id: int, user_id: int, db: Session
) -> SupplementLog:
    s = (
        db.query(SupplementLog)
        .options(selectinload(SupplementLog.doses))
        .filter(SupplementLog.id == supplement_id, SupplementLog.user_id == user_id)
        .first()
    )
    if not s:
        raise HTTPException(status_code=404, detail="Supplement not found")
    return s


@router.get("", response_model=List[SupplementLogItem])
def list_supplements(
    user_id: int = Depends(get_effective_user_id),
    db: Session = Depends(get_db),
):
    supplements = (
        db.query(SupplementLog)
        .options(selectinload(SupplementLog.doses))
        .filter(SupplementLog.user_id == user_id)
        .order_by(SupplementLog.created_at.desc())
        .all()
    )
    return [_log_item(s) for s in supplements]


@router.post("", response_model=SupplementLogItem)
def create_supplement(
    body: CreateSupplementInput,
    user_id: int = Depends(get_effective_user_id),
    db: Session = Depends(get_db),
):
    supplement = SupplementLog(
        user_id=user_id,
        name=body.name,
        unit=body.unit,
        frequency=body.frequency,
        notes=body.notes,
    )
    db.add(supplement)
    db.flush()  # get supplement.id without committing

    dose = SupplementDose(
        supplement_id=supplement.id,
        dose=body.dose,
        started_on=body.started_on,
        ended_on=None,
        date_notes=body.date_notes,
        is_date_approximate=body.is_date_approximate or False,
    )
    db.add(dose)
    db.commit()
    db.refresh(supplement)
    return _log_item(supplement)


@router.patch("/{supplement_id}", response_model=SupplementLogItem)
def update_supplement(
    supplement_id: int,
    body: UpdateSupplementInput,
    user_id: int = Depends(get_effective_user_id),
    db: Session = Depends(get_db),
):
    s = _get_supplement_or_404(supplement_id, user_id, db)
    if body.name is not None:
        s.name = body.name
    if body.unit is not None:
        s.unit = body.unit
    if body.frequency is not None:
        s.frequency = body.frequency
    if body.notes is not None:
        s.notes = body.notes
    db.commit()
    db.refresh(s)
    return _log_item(s)


@router.delete("/{supplement_id}", status_code=204)
def delete_supplement(
    supplement_id: int,
    user_id: int = Depends(get_effective_user_id),
    db: Session = Depends(get_db),
):
    s = _get_supplement_or_404(supplement_id, user_id, db)
    db.delete(s)
    db.commit()


@router.post("/{supplement_id}/doses", response_model=SupplementLogItem)
def add_dose(
    supplement_id: int,
    body: AddDoseInput,
    user_id: int = Depends(get_effective_user_id),
    db: Session = Depends(get_db),
):
    s = _get_supplement_or_404(supplement_id, user_id, db)

    # Auto-close the current open dose
    open_dose = next((d for d in s.doses if d.ended_on is None), None)
    if open_dose:
        open_dose.ended_on = body.started_on - timedelta(days=1)

    new_dose = SupplementDose(
        supplement_id=s.id,
        dose=body.dose,
        started_on=body.started_on,
        ended_on=None,
        date_notes=body.date_notes,
        is_date_approximate=body.is_date_approximate or False,
    )
    db.add(new_dose)
    db.commit()
    db.refresh(s)
    return _log_item(s)


@router.patch("/{supplement_id}/doses/{dose_id}", response_model=SupplementLogItem)
def update_dose(
    supplement_id: int,
    dose_id: int,
    body: UpdateDoseInput,
    user_id: int = Depends(get_effective_user_id),
    db: Session = Depends(get_db),
):
    s = _get_supplement_or_404(supplement_id, user_id, db)
    dose = next((d for d in s.doses if d.id == dose_id), None)
    if not dose:
        raise HTTPException(status_code=404, detail="Dose not found")
    if body.dose is not None:
        dose.dose = body.dose
    if body.started_on is not None:
        dose.started_on = body.started_on
    if body.ended_on is not None:
        dose.ended_on = body.ended_on
    if body.date_notes is not None:
        dose.date_notes = body.date_notes
    if body.is_date_approximate is not None:
        dose.is_date_approximate = body.is_date_approximate
    db.commit()
    db.refresh(s)
    return _log_item(s)


@router.delete("/{supplement_id}/doses/{dose_id}", response_model=SupplementLogItem)
def delete_dose(
    supplement_id: int,
    dose_id: int,
    user_id: int = Depends(get_effective_user_id),
    db: Session = Depends(get_db),
):
    s = _get_supplement_or_404(supplement_id, user_id, db)
    dose = next((d for d in s.doses if d.id == dose_id), None)
    if not dose:
        raise HTTPException(status_code=404, detail="Dose not found")
    db.delete(dose)
    db.commit()
    db.refresh(s)
    return _log_item(s)


@router.get("/active-during", response_model=List[SupplementLogItem])
def active_during(
    from_date: date,
    to_date: date,
    user_id: int = Depends(get_effective_user_id),
    db: Session = Depends(get_db),
):
    """Return supplements that have at least one dose period overlapping [from_date, to_date]."""
    dose_overlap = and_(
        SupplementDose.started_on <= to_date,
        or_(
            SupplementDose.ended_on.is_(None),
            SupplementDose.ended_on >= from_date,
        ),
    )
    supplements = (
        db.query(SupplementLog)
        .options(selectinload(SupplementLog.doses))
        .join(SupplementLog.doses)
        .filter(SupplementLog.user_id == user_id, dose_overlap)
        .distinct()
        .all()
    )
    return [_log_item(s) for s in supplements]
