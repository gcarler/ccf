"""Permission helpers for evangelism events."""
from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend import models
from backend.auth import normalize_role
from backend.core.tenant import require_user_sede_id


def is_event_admin_or_pastor(user: models.User) -> bool:
    """Check if user has admin or pastor role (normalized comparison)."""
    role = normalize_role(str(user.role))
    return role in {"admin", "pastor"}


def is_event_assignee(db: Session, user: models.User, event_id: int) -> bool:
    """Check if user is assigned to this event (MC, preacher, offering, etc.)."""
    if is_event_admin_or_pastor(user):
        return True
    persona = db.query(models.Persona).filter(models.Persona.user_id == user.id).first()
    if not persona:
        return False
    assignment = (
        db.query(models.EventAssignment)
        .filter(
            models.EventAssignment.event_id == event_id,
            models.EventAssignment.persona_id == persona.id,
        )
        .first()
    )
    return assignment is not None


def require_event_access(db: Session, user: models.User, event_id: int) -> None:
    """Raise 403 if user lacks access to the event (checks sede + role + assignment)."""
    event_sede = db.query(models.CrmEvent.sede_id).filter(models.CrmEvent.id == event_id).scalar()
    user_sede = require_user_sede_id(db, user)
    if event_sede and str(event_sede) != str(user_sede):
        raise HTTPException(status_code=403, detail="Evento no pertenece a tu sede")
    if is_event_admin_or_pastor(user):
        return
    if is_event_assignee(db, user, event_id):
        return
    raise HTTPException(
        status_code=403,
        detail="Permisos insuficientes. Solo admin, pastor o asignados al evento.",
    )
