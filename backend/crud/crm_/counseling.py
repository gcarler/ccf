"""Counseling ticket CRUD."""
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from backend import models, schemas
from backend.core.security import decrypt_data, encrypt_data
from backend.crud._utils import _utcnow
from backend.crud.crm_.shared import resolve_persona_id_from_identity


def get_counseling_tickets(
    db: Session,
    status: str | None = None,
    persona_id: str | None = None,
    sede_id: UUID | None = None,
    skip: int = 0,
    limit: int = 100,
) -> List[models.CounselingTicket]:
    query = db.query(models.CounselingTicket).filter(models.CounselingTicket.deleted_at.is_(None))
    if sede_id is not None:
        query = query.join(models.Persona, models.CounselingTicket.persona_id == models.Persona.id).filter(
            models.Persona.sede_id == sede_id
        )
    if status:
        query = query.filter(models.CounselingTicket.status == status)
    if persona_id:
        query = query.filter(models.CounselingTicket.persona_id == persona_id)
    tickets = query.order_by(models.CounselingTicket.created_at.desc()).offset(skip).limit(limit).all()

    for t in tickets:
        if t.notes:
            try:
                t.notes = decrypt_data(t.notes)
            except Exception:
                pass

    return tickets


def create_counseling_ticket(db: Session, payload: schemas.CounselingTicketCreate) -> models.CounselingTicket:
    from backend.crud._utils import analyze_pastoral_priority, analyze_pastoral_sentiment

    try:
        data = payload.model_dump()
        pastor_identity = data.pop("pastor_id", None)
        data["pastor_id"] = resolve_persona_id_from_identity(db, pastor_identity)
        raw_notes = data.get("notes", "")

        data["priority_level"] = analyze_pastoral_priority(raw_notes)
        score, label = analyze_pastoral_sentiment(raw_notes)
        data["sentiment_score"] = score
        data["sentiment_label"] = label

        if raw_notes:
            data["notes"] = encrypt_data(raw_notes)

        row = models.CounselingTicket(**data)
        db.add(row)
        db.commit()
        db.refresh(row)

        try:
            row.notes = decrypt_data(row.notes)
        except Exception:
            pass
        return row
    except Exception as e:
        db.rollback()
        raise ValueError(f"Error al crear ticket de consejería: {str(e)}")


def get_counseling_ticket(db: Session, ticket_id: UUID) -> Optional[models.CounselingTicket]:
    row = (
        db.query(models.CounselingTicket)
        .filter(
            models.CounselingTicket.id == ticket_id,
            models.CounselingTicket.deleted_at.is_(None),
        )
        .first()
    )
    if row and row.notes:
        try:
            row.notes = decrypt_data(row.notes)
        except Exception:
            pass
    return row


def update_counseling_ticket(
    db: Session, ticket_id: UUID, payload: schemas.CounselingTicketUpdate
) -> Optional[models.CounselingTicket]:
    row = (
        db.query(models.CounselingTicket)
        .filter(
            models.CounselingTicket.id == ticket_id,
            models.CounselingTicket.deleted_at.is_(None),
        )
        .first()
    )
    if not row:
        return None
    data = payload.model_dump(exclude_unset=True)
    if "pastor_id" in data:
        pastor_identity = data.pop("pastor_id")
        row.pastor_id = resolve_persona_id_from_identity(db, pastor_identity)
    for key, value in data.items():
        if key == "notes" and value:
            setattr(row, key, encrypt_data(value))
        else:
            setattr(row, key, value)
    db.commit()
    db.refresh(row)
    if row.notes:
        try:
            row.notes = decrypt_data(row.notes)
        except Exception:
            pass
    return row


def delete_counseling_ticket(db: Session, ticket_id: UUID) -> bool:
    row = (
        db.query(models.CounselingTicket)
        .filter(
            models.CounselingTicket.id == ticket_id,
            models.CounselingTicket.deleted_at.is_(None),
        )
        .first()
    )
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True
