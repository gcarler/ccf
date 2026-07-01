"""Family CRUD and family personas."""
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from backend import models
from backend.crud._utils import _utcnow


def get_families(db: Session, skip: int = 0, limit: int = 100):
    families = db.query(models.Family).offset(skip).limit(limit).all()
    for f in families:
        f.personas_count = db.query(models.Persona).filter(models.Persona.family_id == f.id).count()
    return families


def create_family(db: Session, name: str):
    fam = models.Family(name=name)
    db.add(fam)
    db.commit()
    db.refresh(fam)
    return fam


def get_family(db: Session, family_id: UUID) -> Optional[models.Family]:
    return db.query(models.Family).filter(models.Family.id == family_id).first()


def update_family(db: Session, family_id: UUID, name: str) -> Optional[models.Family]:
    row = db.query(models.Family).filter(models.Family.id == family_id).first()
    if not row:
        return None
    row.name = name
    db.commit()
    db.refresh(row)
    return row


def delete_family(db: Session, family_id: UUID) -> bool:
    row = db.query(models.Family).filter(models.Family.id == family_id).first()
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True


def get_family_personas(db: Session, family_id: UUID):
    return (
        db.query(models.Persona)
        .filter(models.Persona.family_id == family_id)
        .order_by(models.Persona.nombre_completo.asc())
        .all()
    )
