"""Volunteer shift CRUD."""

from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from backend import models, schemas
from backend.crud._utils import _utcnow


def get_volunteer_shifts(
    db: Session,
    persona_id: Optional[str] = None,
    *,
    sede_id: Optional[UUID] = None,
) -> List[models.VolunteerShift]:
    """Lista shifts no borrados.

    ``sede_id`` aplica el filtro Multi-Tenant (Axioma 3) cuando se pasa
    explícito. ``None`` (superadmin sin sede) retorna todas las filas no
    borradas — defense-in-depth en la API layer garantiza que el ``None``
    sólo llega aquí desde un actor autenticado sin sede asignada.
    """
    query = db.query(models.VolunteerShift).filter(models.VolunteerShift.deleted_at.is_(None))
    if sede_id is not None:
        query = query.filter(models.VolunteerShift.sede_id == sede_id)
    if persona_id:
        query = query.filter(models.VolunteerShift.persona_id == persona_id)
    return query.order_by(models.VolunteerShift.shift_start.asc()).all()


def create_volunteer_shift(
    db: Session,
    payload: schemas.VolunteerShiftCreate,
    *,
    sede_id: Optional[UUID] = None,
) -> models.VolunteerShift:
    data = payload.model_dump()
    if sede_id is not None:
        data["sede_id"] = sede_id
    row = models.VolunteerShift(**data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_volunteer_shift(
    db: Session,
    shift_id: UUID,
    *,
    sede_id: Optional[UUID] = None,
) -> Optional[models.VolunteerShift]:
    q = (
        db.query(models.VolunteerShift)
        .filter(
            models.VolunteerShift.id == shift_id,
            models.VolunteerShift.deleted_at.is_(None),
        )
    )
    if sede_id is not None:
        q = q.filter(models.VolunteerShift.sede_id == sede_id)
    return q.first()


def update_volunteer_shift(
    db: Session,
    shift_id: UUID,
    payload: schemas.VolunteerShiftUpdate,
    *,
    sede_id: Optional[UUID] = None,
) -> Optional[models.VolunteerShift]:
    q = db.query(models.VolunteerShift).filter(models.VolunteerShift.id == shift_id)
    if sede_id is not None:
        q = q.filter(models.VolunteerShift.sede_id == sede_id)
    row = q.first()
    if not row:
        return None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


def delete_volunteer_shift(
    db: Session,
    shift_id: UUID,
    *,
    sede_id: Optional[UUID] = None,
) -> bool:
    q = db.query(models.VolunteerShift).filter(models.VolunteerShift.id == shift_id)
    if sede_id is not None:
        q = q.filter(models.VolunteerShift.sede_id == sede_id)
    row = q.first()
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True
