"""CRM event and event attendance CRUD."""
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from backend import models, schemas
from backend.crud._utils import _utcnow


def _active_events_query(db: Session):
    return db.query(models.CrmEvent).filter(models.CrmEvent.deleted_at.is_(None))


def get_crm_events(db: Session, sede_id: str | None = None, skip: int = 0, limit: int = 100) -> List[models.CrmEvent]:
    q = _active_events_query(db)
    if sede_id:
        q = q.filter(models.CrmEvent.sede_id == sede_id)
    return q.order_by(models.CrmEvent.event_date.desc()).offset(skip).limit(limit).all()


def create_crm_event(db: Session, payload: schemas.CrmEventCreate) -> models.CrmEvent:
    try:
        payload_data = payload.model_dump()
        role_ids = payload_data.get("target_role_ids") or []
        payload_data["target_role_ids"] = [str(role_id) for role_id in role_ids] or None
        if payload_data.get("target_audience") == "ROLE":
            payload_data["target_role_id"] = role_ids[0] if role_ids else payload_data.get("target_role_id")
        else:
            payload_data["target_role_id"] = None
            payload_data["target_role_ids"] = None
        row = models.CrmEvent(**payload_data)
        db.add(row)
        db.commit()
        db.refresh(row)
        return row
    except Exception as e:
        db.rollback()
        raise ValueError(f"Error al crear evento: {str(e)}")


def get_crm_event(db: Session, event_id: UUID) -> Optional[models.CrmEvent]:
    return _active_events_query(db).filter(models.CrmEvent.id == event_id).first()


def update_crm_event(
    db: Session, event_id: UUID, payload: schemas.CrmEventUpdate
) -> Optional[models.CrmEvent]:
    """Actualiza un evento mediante el contrato Pydantic canónico."""
    row = _active_events_query(db).filter(models.CrmEvent.id == event_id).first()
    if not row:
        return None
    changes = payload.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


def delete_crm_event(db: Session, event_id: UUID) -> bool:
    row = _active_events_query(db).filter(models.CrmEvent.id == event_id).first()
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True


def get_event_attendance(db: Session, event_id: UUID) -> List[models.EventAttendance]:
    return db.query(models.EventAttendance).filter(models.EventAttendance.event_id == event_id).all()


def create_event_attendance(db: Session, payload: schemas.EventAttendanceCreate) -> models.EventAttendance:
    try:
        row = models.EventAttendance(**payload.model_dump())
        db.add(row)
        db.commit()
        db.refresh(row)
        return row
    except Exception as e:
        db.rollback()
        raise ValueError(f"Error al registrar asistencia: {str(e)}")


def delete_event_attendance(db: Session, attendance_id: UUID) -> bool:
    row = db.query(models.EventAttendance).filter(models.EventAttendance.id == attendance_id).first()
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True
