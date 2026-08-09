from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend import crud, models, schemas
from backend.core.database import get_db
from backend.core.permissions import (
    get_user_effective_permissions,
    normalize_role,
    require_active_user,
)
from backend.crud.crm import resolve_persona_id_for_user

router = APIRouter()


def _is_support_platform_admin(db: Session, current_user: models.User) -> bool:
    """Return whether the actor may use Support's global unscoped path.

    A seated ``ADMIN`` remains an administrator for ticket mutations, but it
    is still constrained to its own sede. Global visibility is reserved for
    the explicit platform role/permission, matching the Finance hardening.
    """
    role = normalize_role(str(getattr(current_user, "role", "")))
    if not role and getattr(current_user, "rol_plataforma", None):
        role = normalize_role(current_user.rol_plataforma.nombre)
    if role in {"super administrador", "superadmin", "platform_admin"}:
        return True
    permissions = get_user_effective_permissions(db, current_user)
    return permissions.get("system:config") == "allow" and role not in {"admin", "administrador"}


def _is_support_admin(db: Session, current_user: models.User) -> bool:
    """Return whether the actor may update support tickets."""
    role = normalize_role(str(getattr(current_user, "role", "")))
    if not role and getattr(current_user, "rol_plataforma", None):
        role = normalize_role(current_user.rol_plataforma.nombre)
    return role in {"admin", "administrador"} or _is_support_platform_admin(db, current_user)


def _actor_sede_uuid(db: Session, current_user: models.User, persona_id: UUID) -> UUID | None:
    """Resolve the actor's Support scope as a UUID.

    A platform administrator with an explicitly unscoped Persona may use the
    global unscoped path. A platform administrator who is assigned to a sede is
    still scoped to that sede, just like every other seated administrator.
    """
    persona_sede = db.query(models.Persona.sede_id).filter(models.Persona.id == persona_id).scalar()
    if persona_sede is None and _is_support_platform_admin(db, current_user):
        return None

    try:
        return UUID(str(persona_sede))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=403, detail="Usuario sin sede asignada") from exc


@router.post("", response_model=schemas.SupportTicket)
def create_support_ticket(
    ticket: schemas.SupportTicketCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    persona_id = resolve_persona_id_for_user(db, current_user.id)
    if not persona_id:
        raise HTTPException(status_code=404, detail="Persona not found for current user")
    ticket.user_id = persona_id
    sede_id = _actor_sede_uuid(db, current_user, persona_id)
    return crud.create_support_ticket(db=db, ticket=ticket, sede_id=sede_id)


@router.get("", response_model=List[schemas.SupportTicket])
def read_support_tickets(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    persona_id = resolve_persona_id_for_user(db, current_user.id)
    persona = db.query(models.Persona).filter(models.Persona.id == persona_id).first() if persona_id else None
    is_admin = _is_support_admin(db, current_user)
    sede_id = _actor_sede_uuid(db, current_user, persona_id)
    # Non-admin: restrict to own tickets (persona_id), still scope by sede.
    persona_filter_id = None if is_admin else persona.id if persona else None
    return crud.get_support_tickets(
        db=db,
        user_id=persona_filter_id,
        skip=skip,
        limit=limit,
        sede_id=sede_id,
    )


@router.patch("/{ticket_id}", response_model=schemas.SupportTicket)
def patch_support_ticket(
    ticket_id: str,
    status_update: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    persona_id = resolve_persona_id_for_user(db, current_user.id)
    if not persona_id:
        raise HTTPException(status_code=404, detail="Persona not found")

    is_admin = _is_support_admin(db, current_user)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Not authorized to update tickets")

    new_status = status_update.get("status")
    if not new_status:
        raise HTTPException(status_code=400, detail="Status is required")

    sede_id = _actor_sede_uuid(db, current_user, persona_id)
    updated = crud.update_support_ticket(db, ticket_id, new_status, sede_id=sede_id)
    if not updated:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return updated
