"""Donation CRUD."""
from typing import List, Optional
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend import models, schemas
from backend.crud._utils import _utcnow


def create_donation(db: Session, payload: schemas.DonationCreate) -> models.Donation:
    row = models.Donation(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_donations(db: Session, skip: int = 0, limit: int = 100, sede_id: str | None = None) -> List[models.Donation]:
    q = db.query(models.Donation).filter(models.Donation.deleted_at.is_(None))
    if sede_id:
        q = q.filter(models.Donation.sede_id == sede_id)
    return q.order_by(models.Donation.created_at.desc()).offset(skip).limit(limit).all()


def get_total_donations_amount(db: Session, sede_id: str | None = None) -> float:
    q = db.query(func.sum(models.Donation.amount)).filter(models.Donation.deleted_at.is_(None))
    if sede_id:
        q = q.filter(models.Donation.sede_id == sede_id)
    return q.scalar() or 0


def get_donation(db: Session, donation_id: UUID) -> Optional[models.Donation]:
    return (
        db.query(models.Donation)
        .filter(
            models.Donation.id == donation_id,
            models.Donation.deleted_at.is_(None),
        )
        .first()
    )


def update_donation(db: Session, donation_id: UUID, payload: schemas.DonationUpdate) -> Optional[models.Donation]:
    row = db.query(models.Donation).filter(models.Donation.id == donation_id).first()
    if not row:
        return None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


def delete_donation(db: Session, donation_id: UUID) -> bool:
    row = (
        db.query(models.Donation)
        .filter(
            models.Donation.id == donation_id,
            models.Donation.deleted_at.is_(None),
        )
        .first()
    )
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True
