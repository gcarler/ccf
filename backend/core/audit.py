from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.orm import Session

from backend import crud, models
from backend.crud.crm import resolve_persona_id_for_user


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
        actor_user_id=actor_user_id,
    )
