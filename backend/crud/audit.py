"""Admin audit log CRUD."""

import datetime as dt

from sqlalchemy.orm import Session

from backend import models


def create_admin_audit_log(
    db: Session,
    actor_user_id: int | None,
    action: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    metadata: dict | None = None,
    ip_address: str | None = None,
):
    now = dt.datetime.now(dt.UTC).replace(tzinfo=None)
    row = models.AdminAuditLog(
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
    actor_user_id: int | None = None,
    resource_type: str | None = None,
):
    query = db.query(models.AdminAuditLog)
    if actor_user_id is not None:
        query = query.filter(models.AdminAuditLog.actor_user_id == actor_user_id)
    if resource_type is not None:
        query = query.filter(models.AdminAuditLog.resource_type == resource_type)
    return query.order_by(models.AdminAuditLog.created_at.desc()).limit(limit).all()
