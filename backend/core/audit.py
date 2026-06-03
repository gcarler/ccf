from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.orm import Session

from backend import crud, models


def record_admin_action(
    db: Session,
    actor: models.User,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
    ip_address: Optional[str] = None,
) -> None:
    from backend.crud.crm import get_user_sede_id  # noqa: F401 — keep import local to avoid circular
    from backend import models as _models
    actor_user_id = getattr(actor, "id", None)
    if not actor_user_id:
        return
    # Resolve persona UUID from user — pass None if user has no linked persona
    persona = db.query(_models.Persona).filter(_models.Persona.user_id == actor_user_id).first()
    actor_persona_id = str(persona.id) if persona else None
    crud.create_admin_audit_log(
        db,
        actor_persona_id=actor_persona_id,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id is not None else None,
        metadata=metadata,
        ip_address=ip_address,
        actor_user_id=actor_user_id,
    )
