from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend import crud, models, schemas
from backend.auth import require_active_user
from backend.crud.crm import get_user_sede_id
from backend.core.database import get_db

router = APIRouter()


@router.post("", response_model=schemas.SupportTicket)
def create_support_ticket(
    ticket: schemas.SupportTicketCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    # Ensure user can only create for themselves
    if ticket.user_id != current_user.id:
        ticket.user_id = current_user.id
    return crud.create_support_ticket(db=db, ticket=ticket)


@router.get("", response_model=List[schemas.SupportTicket])
def read_support_tickets(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    # Axioma 3: Admin filtrado por sede, usuarios ven solo los suyos
    get_user_sede_id(db, current_user.id)
    user_id = None if current_user.role in ["admin", "staff"] else current_user.id
    return crud.get_support_tickets(db=db, user_id=user_id, skip=skip, limit=limit)


@router.patch("/{ticket_id}", response_model=schemas.SupportTicket)
def patch_support_ticket(
    ticket_id: int,
    status_update: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    # Only staff/admin can change status for now
    if current_user.role not in ["admin", "staff"]:
        raise HTTPException(status_code=403, detail="Not authorized to update tickets")

    new_status = status_update.get("status")
    if not new_status:
        raise HTTPException(status_code=400, detail="Status is required")

    updated = crud.update_support_ticket(db, ticket_id, new_status)
    if not updated:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return updated
