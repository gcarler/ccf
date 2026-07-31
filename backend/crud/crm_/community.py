"""Community board card CRUD."""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend import models, schemas
from backend.crud._utils import _utcnow
from backend.schemas.operational import CommunityBoardCardUpdate


def get_community_cards(db: Session, column_id: Optional[str] = None) -> List[models.CommunityBoardCard]:
    q = db.query(models.CommunityBoardCard).filter(models.CommunityBoardCard.deleted_at.is_(None))
    q = q.order_by(models.CommunityBoardCard.position.asc())
    if column_id:
        q = q.filter(models.CommunityBoardCard.column_id == column_id)
    return q.all()


def create_community_card(
    db: Session,
    card: schemas.CommunityBoardCardCreate,
    *,
    actor_sede: Optional[UUID] = None,
) -> models.CommunityBoardCard:
    """Crea una tarjeta del tablero comunitario.

    QC-08 (auditoría de calidad 2026-07-25): ahora atribuye ``sede_id``
    server-side desde el JWT del actor (``actor_sede``). Antes la tarjeta
    quedaba con ``sede_id=NULL`` (tablero público anónimo). El schema
    ``CommunityBoardCardCreate`` no acepta ``sede_id`` del caller (defense
    contra field-up-write) — solo el API tiene autoridad para atribuirlo.
    """
    max_pos = db.query(func.max(models.CommunityBoardCard.position)).scalar() or 0
    row = models.CommunityBoardCard(**card.model_dump(), position=max_pos + 1)
    if actor_sede is not None:
        row.sede_id = actor_sede
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_community_card(db: Session, card_id: UUID) -> Optional[models.CommunityBoardCard]:
    return (
        db.query(models.CommunityBoardCard)
        .filter(
            models.CommunityBoardCard.id == card_id,
            models.CommunityBoardCard.deleted_at.is_(None),
        )
        .first()
    )


def update_community_card(
    db: Session, card_id: UUID, payload: CommunityBoardCardUpdate
) -> Optional[models.CommunityBoardCard]:
    row = (
        db.query(models.CommunityBoardCard)
        .filter(
            models.CommunityBoardCard.id == card_id,
            models.CommunityBoardCard.deleted_at.is_(None),
        )
        .first()
    )
    if not row:
        return None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


def delete_community_card(db: Session, card_id: UUID) -> bool:
    row = (
        db.query(models.CommunityBoardCard)
        .filter(
            models.CommunityBoardCard.id == card_id,
            models.CommunityBoardCard.deleted_at.is_(None),
        )
        .first()
    )
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True
