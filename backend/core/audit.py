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
    actor_id = getattr(actor, "id", None)
    if not actor_id:
        return
    crud.create_admin_audit_log(
        db,
        actor_persona_id=str(actor_id),
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id is not None else None,
        metadata=metadata,
        ip_address=ip_address,
    )
