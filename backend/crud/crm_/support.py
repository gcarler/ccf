"""Support ticket CRUD."""
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from backend import models, schemas
from backend.crud._utils import _utcnow


def create_support_ticket(db: Session, ticket: schemas.SupportTicketCreate) -> models.SupportTicket:
    row = models.SupportTicket(**ticket.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_support_tickets(
    db: Session, user_id: Optional[UUID] = None, skip: int = 0, limit: int = 100
) -> List[models.SupportTicket]:
    q = db.query(models.SupportTicket).order_by(models.SupportTicket.created_at.desc())
    if user_id is not None:
        q = q.filter(models.SupportTicket.user_id == user_id)
    return q.offset(skip).limit(limit).all()


def update_support_ticket(db: Session, ticket_id: str, new_status: str):
    ticket = db.query(models.SupportTicket).filter(models.SupportTicket.id == ticket_id).first()
    if not ticket:
        return None
    ticket.status = new_status
    db.commit()
    db.refresh(ticket)
    return ticket


def get_support_ticket(db: Session, ticket_id: str) -> Optional[models.SupportTicket]:
    return db.query(models.SupportTicket).filter(models.SupportTicket.id == ticket_id).first()


def delete_support_ticket(db: Session, ticket_id: str) -> bool:
    row = db.query(models.SupportTicket).filter(models.SupportTicket.id == ticket_id).first()
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True
