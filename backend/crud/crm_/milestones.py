"""Spiritual milestone CRUD."""
import uuid
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from backend import models
from backend.crud._utils import _utcnow


def get_milestones(db: Session, persona_id) -> List[models.SpiritualMilestone]:
    persona_uuid = uuid.UUID(str(persona_id))
    return (
        db.query(models.SpiritualMilestone)
        .filter(
            models.SpiritualMilestone.persona_id == persona_uuid,
            models.SpiritualMilestone.deleted_at.is_(None),
        )
        .order_by(models.SpiritualMilestone.event_date.desc())
        .all()
    )


def create_milestone(
    db: Session,
    persona_id,
    type: str,
    event_date,
    minister_id: Optional[str] = None,
) -> models.SpiritualMilestone:
    persona_uuid = uuid.UUID(str(persona_id))
    minister_uuid = uuid.UUID(str(minister_id)) if minister_id else None
    row = models.SpiritualMilestone(
        persona_id=persona_uuid,
        type=type,
        event_date=event_date,
        minister_id=minister_uuid,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_milestone(db: Session, milestone_id: UUID, **kwargs) -> Optional[models.SpiritualMilestone]:
    row = db.query(models.SpiritualMilestone).filter(models.SpiritualMilestone.id == milestone_id).first()
    if not row:
        return None
    for key, value in kwargs.items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


def delete_milestone(db: Session, milestone_id: UUID) -> bool:
    row = (
        db.query(models.SpiritualMilestone)
        .filter(
            models.SpiritualMilestone.id == milestone_id,
            models.SpiritualMilestone.deleted_at.is_(None),
        )
        .first()
    )
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True
