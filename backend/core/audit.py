from __future__ import annotations

import uuid as _uuid
from typing import Any, Optional

from sqlalchemy.orm import Session

from backend import crud, models
from backend.crud.crm import resolve_persona_id_for_user


def _legacy_user_id(db: Session, actor_id: Any) -> Optional[int]:
    """Resolve a legacy integer user_id from a UUID actor_id.

    AdminAuditLog.actor_user_id is Integer (FK to legacy users.id).
    Actors authenticated via auth_v2/v3 carry a UUID id (Usuario.id == Persona.id).
    This helper resolves the legacy integer user_id via Persona.user_id -> users.id.
    Returns None when no legacy mapping exists (the column is nullable).
    """
    if actor_id is None:
        return None
    if not isinstance(actor_id, (_uuid.UUID, str)):
        return int(actor_id) if actor_id else None
    try:
        user_uuid = _uuid.UUID(str(actor_id))
    except (ValueError, TypeError, AttributeError):
        return int(actor_id) if actor_id else None
    persona = (
        db.query(models.Persona.user_id)
        .filter(models.Persona.id == user_uuid)
        .first()
    )
    if persona and persona.user_id is not None:
        return int(persona.user_id)
    return None


def record_admin_action(
    db: Session,
    actor: models.User,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
    ip_address: Optional[str] = None,
) -> None:
    actor_user_id = getattr(actor, "id", None)
    if not actor_user_id:
        return
    actor_persona_id = resolve_persona_id_for_user(db, actor_user_id)
    crud.create_admin_audit_log(
        db,
        actor_persona_id=str(actor_persona_id) if actor_persona_id else None,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id is not None else None,
        metadata=metadata,
        ip_address=ip_address,
    )
