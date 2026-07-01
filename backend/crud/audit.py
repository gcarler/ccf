"""Admin audit log CRUD."""

import datetime as dt
import uuid as _uuid

from sqlalchemy.orm import Session

from backend import models


def create_admin_audit_log(
    db: Session,
    action: str,
    actor_persona_id: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    metadata: dict | None = None,
    ip_address: str | None = None,
):
    resolved_persona_id = actor_persona_id
    if actor_persona_id:
        try:
            _uuid.UUID(actor_persona_id)
        except ValueError:
            resolved_persona_id = None
    now = dt.datetime.now(dt.timezone.utc)
    row = models.AdminAuditLog(
        actor_persona_id=resolved_persona_id,
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
