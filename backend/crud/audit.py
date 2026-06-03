"""Admin audit log CRUD."""

import datetime as dt
import uuid

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
    actor_user_id: int | None = None,
):
    # If actor_persona_id is not a valid UUID, treat it as a legacy user_id
    # and resolve the linked persona UUID.
    resolved_persona_id = actor_persona_id
    if actor_persona_id:
        try:
            uuid.UUID(actor_persona_id)
        except ValueError:
            try:
                user_id = int(actor_persona_id)
                persona = db.query(models.Persona).filter(models.Persona.user_id == user_id).first()
                resolved_persona_id = str(persona.id) if persona else None
            except ValueError:
                resolved_persona_id = None
    now = dt.datetime.now(dt.UTC).replace(tzinfo=None)
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
