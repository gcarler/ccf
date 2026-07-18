"""Permission helpers for evangelism events."""
import uuid
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend import models
from backend.core.permissions import normalize_role
from backend.core.tenant import require_user_sede_id


def _get_user_role(user: models.User) -> str:
    role = normalize_role(str(getattr(user, "role", "")))
    if not role and hasattr(user, "rol_plataforma") and user.rol_plataforma:
        role = normalize_role(user.rol_plataforma.nombre)
    return role


def is_event_reader_role(user: models.User) -> bool:
    """Check if user has a role with broad read visibility over events."""
    role = _get_user_role(user)
    return role in {"admin", "administrador", "pastor", "coordinador"}


def is_event_manager_role(user: models.User) -> bool:
    """Check if user has a role with broad operational control over events."""
    role = _get_user_role(user)
    return role in {"admin", "administrador", "pastor"}


def _get_persona_for_user(db: Session, user_id):
    if user_id is None:
        return None
    try:
        user_uuid = uuid.UUID(str(user_id))
    except (TypeError, ValueError, AttributeError):
        return None
    return db.query(models.Persona).filter(models.Persona.id == user_uuid).first()


def is_event_assignee(db: Session, user: models.User, event_id: UUID) -> bool:
    """Check if user is assigned to this event (MC, preacher, offering, etc.)."""
    if is_event_manager_role(user):
        return True
    persona = _get_persona_for_user(db, user.id)
    if not persona:
        return False
    assignment = (
        db.query(models.EventAssignment)
        .filter(
            models.EventAssignment.event_id == event_id,
            models.EventAssignment.persona_id == persona.id,
            models.EventAssignment.deleted_at.is_(None),
        )
        .first()
    )
    return assignment is not None


def require_event_access(db: Session, user: models.User, event_id: UUID | str) -> models.CrmEvent:
    """Return an active event in the user's sede or raise a scoped error.

    Authorization level is enforced by the endpoint's canonical
    ``require_evangelism_*`` dependency. This helper deliberately owns only
    resource scope (sede + soft delete), so a granular permission cannot be
    contradicted later by a legacy list of role names.
    """
    event = db.query(models.CrmEvent).filter(models.CrmEvent.id == event_id).first()
    if not event or event.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Event not found")
    user_sede = require_user_sede_id(db, user)
    if event.sede_id and str(event.sede_id) != str(user_sede):
        raise HTTPException(status_code=403, detail="Evento no pertenece a tu sede")
    return event
