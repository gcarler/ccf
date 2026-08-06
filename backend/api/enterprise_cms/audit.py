"""Audit Trail — listado de entradas del ``AuditLog`` enterprise CMS.

Sub-router movido desde ``backend/api/enterprise_cms.py`` (split del
monolito, deuda estructural 🟠#4, 2026-08-05). Sin ``prefix`` aquí — el
``prefix="/cms/v2"`` lo agrega ``enterprise_cms/__init__.py`` al
``include_router``.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.orm import Session

from backend.api.enterprise_cms.__common import require_cms_read
from backend.core.database import get_db
from backend.models_enterprise import AuditLog
from backend.models_identity import User

router = APIRouter()


class AuditLogResponse(BaseModel):
    id: str
    actor_email: str | None
    actor_role: str | None
    action: str
    entity_type: str
    entity_id: str | None
    entity_slug: str | None
    changes_json: dict | None
    ip_address: str | None
    severity: str
    created_at: str


@router.get("/audit-logs", response_model=list[AuditLogResponse])
def list_audit_logs(
    site_key: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    actor_email: str | None = None,
    action: str | None = None,
    severity: str | None = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db),
    user: User = Depends(require_cms_read),
):
    q = db.query(AuditLog)
    if site_key:
        q = q.filter(AuditLog.site_key == site_key)
    if entity_type:
        q = q.filter(AuditLog.entity_type == entity_type)
    if entity_id:
        q = q.filter(AuditLog.entity_id == entity_id)
    if actor_email:
        q = q.filter(AuditLog.actor_email.ilike(f"%{actor_email}%"))
    if action:
        q = q.filter(AuditLog.action == action)
    if severity:
        q = q.filter(AuditLog.severity == severity)
    logs = q.order_by(desc(AuditLog.created_at)).offset(offset).limit(limit).all()
    return [
        AuditLogResponse(
            id=str(log.id),
            actor_email=log.actor_email,
            actor_role=log.actor_role,
            action=log.action,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            entity_slug=log.entity_slug,
            changes_json=log.changes_json,
            ip_address=log.ip_address,
            severity=log.severity,
            created_at=log.created_at.isoformat() if log.created_at else "",
        )
        for log in logs
    ]
