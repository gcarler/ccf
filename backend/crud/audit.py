"""Admin audit log CRUD."""

import datetime as dt
import uuid

from sqlalchemy.orm import Session

from backend import models
from backend.crud.crm import resolve_persona_id_for_user


def create_admin_audit_log(
    db: Session,
    action: str,
    actor_persona_id: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    metadata: dict | None = None,
    ip_address: str | None = None,
    actor_user_id: int | None = None,
):
    resolved_persona_id = actor_persona_id
    if not resolved_persona_id and actor_user_id is not None:
        resolved_persona_id = (
            str(resolve_persona_id_for_user(db, actor_user_id))
            if resolve_persona_id_for_user(db, actor_user_id)
            else None
        )
    if actor_persona_id:
        try:
            uuid.UUID(actor_persona_id)
        except ValueError:
            resolved_persona_id = None
    now = dt.datetime.now(dt.timezone.utc)
    row = models.AdminAuditLog(
        actor_persona_id=resolved_persona_id,
        actor_user_id=actor_user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip_address,
        metadata_json=metadata or {},
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_admin_audit_logs(
    db: Session,
    limit: int = 100,
    actor_persona_id: str | None = None,
    resource_type: str | None = None,
):
    query = db.query(models.AdminAuditLog)
    if actor_persona_id is not None:
        query = query.filter(models.AdminAuditLog.actor_persona_id == actor_persona_id)
    if resource_type is not None:
        query = query.filter(models.AdminAuditLog.resource_type == resource_type)
    return query.order_by(models.AdminAuditLog.created_at.desc()).limit(limit).all()
