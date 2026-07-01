"""Volunteer shift CRUD."""
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from backend import models, schemas
from backend.crud._utils import _utcnow


def get_volunteer_shifts(db: Session, persona_id: Optional[str] = None) -> List[models.VolunteerShift]:
    query = db.query(models.VolunteerShift)
    if persona_id:
        query = query.filter(models.VolunteerShift.persona_id == persona_id)
    return query.order_by(models.VolunteerShift.shift_start.asc()).all()


def create_volunteer_shift(db: Session, payload: schemas.VolunteerShiftCreate) -> models.VolunteerShift:
    row = models.VolunteerShift(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_volunteer_shift(db: Session, shift_id: UUID) -> Optional[models.VolunteerShift]:
    return db.query(models.VolunteerShift).filter(models.VolunteerShift.id == shift_id).first()


def update_volunteer_shift(
    db: Session, shift_id: UUID, payload: schemas.VolunteerShiftUpdate
) -> Optional[models.VolunteerShift]:
    row = db.query(models.VolunteerShift).filter(models.VolunteerShift.id == shift_id).first()
    if not row:
        return None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


def delete_volunteer_shift(db: Session, shift_id: UUID) -> bool:
    row = db.query(models.VolunteerShift).filter(models.VolunteerShift.id == shift_id).first()
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True
