"""Support ticket CRUD."""

from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from backend import models, schemas
from backend.crud._utils import _utcnow


def create_support_ticket(
    db: Session,
    ticket: schemas.SupportTicketCreate,
    *,
    sede_id: Optional[UUID] = None,
) -> models.SupportTicket:
    data = ticket.model_dump()
    if sede_id is not None:
        data["sede_id"] = sede_id
    row = models.SupportTicket(**data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_support_tickets(
    db: Session,
    user_id: Optional[UUID] = None,
    skip: int = 0,
    limit: int = 100,
    *,
    sede_id: Optional[UUID] = None,
) -> List[models.SupportTicket]:
    """Lista tickets no borrados.

    ``sede_id`` aplica el filtro Multi-Tenant (Axioma 3). ``None`` sólo
    desde un superadmin sin sede (defense-in-depth en la API layer).
    """
    # QC-06: respetar soft-delete — no retornar tickets con deleted_at seteado.
    q = (
        db.query(models.SupportTicket)
        .filter(models.SupportTicket.deleted_at.is_(None))
        .order_by(models.SupportTicket.created_at.desc())
    )
    if sede_id is not None:
        q = q.filter(models.SupportTicket.sede_id == sede_id)
    if user_id is not None:
        q = q.filter(models.SupportTicket.user_id == user_id)
    return q.offset(skip).limit(limit).all()


def update_support_ticket(
    db: Session,
    ticket_id: str,
    new_status: str,
    *,
    sede_id: Optional[UUID] = None,
):
    # QC-06: no revivir/un-update un ticket soft-deleted (defense-in-depth).
    q = db.query(models.SupportTicket).filter(
        models.SupportTicket.id == ticket_id,
        models.SupportTicket.deleted_at.is_(None),
    )
    if sede_id is not None:
        q = q.filter(models.SupportTicket.sede_id == sede_id)
    ticket = q.first()
    if not ticket:
        return None
    ticket.status = new_status
    db.commit()
    db.refresh(ticket)
    return ticket


def get_support_ticket(
    db: Session,
    ticket_id: str,
    *,
    sede_id: Optional[UUID] = None,
) -> Optional[models.SupportTicket]:
    # QC-06: respetar soft-delete.
    q = db.query(models.SupportTicket).filter(
        models.SupportTicket.id == ticket_id,
        models.SupportTicket.deleted_at.is_(None),
    )
    if sede_id is not None:
        q = q.filter(models.SupportTicket.sede_id == sede_id)
    return q.first()


def delete_support_ticket(
    db: Session,
    ticket_id: str,
    *,
    sede_id: Optional[UUID] = None,
) -> bool:
    # QC-06: el soft-delete se persiste en ``deleted_at``.
    q = db.query(models.SupportTicket).filter(
        models.SupportTicket.id == ticket_id,
        models.SupportTicket.deleted_at.is_(None),
    )
    if sede_id is not None:
        q = q.filter(models.SupportTicket.sede_id == sede_id)
    row = q.first()
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True
