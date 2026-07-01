"""Prayer request CRUD."""
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from backend import models, schemas
from backend.crud._utils import _utcnow


def get_prayer_requests(
    db: Session, status: str | None = None, skip: int = 0, limit: int = 100
) -> List[models.PrayerRequest]:
    query = db.query(models.PrayerRequest)
    if status:
        query = query.filter(models.PrayerRequest.status == status)
    return query.order_by(models.PrayerRequest.created_at.desc()).offset(skip).limit(limit).all()


def create_prayer_request(db: Session, payload: schemas.PrayerRequestCreate) -> models.PrayerRequest:
    try:
        row = models.PrayerRequest(**payload.model_dump())
        db.add(row)
        db.commit()
        db.refresh(row)
        return row
    except Exception as e:
        db.rollback()
        raise ValueError(f"Error al registrar petición de oración: {str(e)}")


def get_prayer_request(db: Session, request_id: UUID) -> Optional[models.PrayerRequest]:
    return db.query(models.PrayerRequest).filter(models.PrayerRequest.id == request_id).first()


def update_prayer_request(
    db: Session, request_id: UUID, payload: schemas.PrayerRequestUpdate
) -> Optional[models.PrayerRequest]:
    row = db.query(models.PrayerRequest).filter(models.PrayerRequest.id == request_id).first()
    if not row:
        return None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


def delete_prayer_request(db: Session, request_id: UUID) -> bool:
    row = db.query(models.PrayerRequest).filter(models.PrayerRequest.id == request_id).first()
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True
