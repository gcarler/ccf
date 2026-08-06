"""Webhooks + deliveries — CRUD de ``Webhook`` y listado de ``WebhookDelivery``.

Sub-router movido desde ``backend/api/enterprise_cms.py`` (split del
monolito, deuda estructural 🟠#4, 2026-08-05).
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.orm import Session

from backend.api.enterprise_cms.__common import _log_audit, require_cms_manage, require_cms_read
from backend.core.database import get_db
from backend.models_enterprise import Webhook, WebhookDelivery
from backend.models_identity import User

router = APIRouter()


class WebhookCreate(BaseModel):
    site_key: str
    name: str
    url: str
    secret: str | None = None
    events: list[str] = []


class WebhookUpdate(BaseModel):
    name: str | None = None
    url: str | None = None
    events: list[str] | None = None
    is_active: bool | None = None


@router.post("/webhooks")
def create_webhook(
    body: WebhookCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_cms_manage),
):
    hook = Webhook(
        site_key=body.site_key,
        name=body.name,
        url=body.url,
        secret=body.secret,
        events=body.events,
        created_by_persona_id=getattr(user, "persona_id", None),
    )
    db.add(hook)
    _log_audit(
        db,
        user,
        "webhook.create",
        "webhook",
        str(hook.id),
        site_key=body.site_key,
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    return {"id": str(hook.id), "status": "created"}


@router.get("/webhooks")
def list_webhooks(
    site_key: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_cms_read),
):
    hooks = (
        db.query(Webhook)
        .filter(
            Webhook.site_key == site_key,
            Webhook.deleted_at.is_(None),
        )
        .order_by(desc(Webhook.created_at))
        .all()
    )
    return [
        {
            "id": str(h.id),
            "name": h.name,
            "url": h.url,
            "events": h.events,
            "is_active": h.is_active,
            "last_triggered_at": h.last_triggered_at.isoformat() if h.last_triggered_at else None,
            "failure_count": h.failure_count,
        }
        for h in hooks
    ]


@router.patch("/webhooks/{hook_id}")
def update_webhook(
    hook_id: str,
    body: WebhookUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_cms_manage),
):
    hook = db.query(Webhook).filter(Webhook.id == hook_id).first()
    if not hook:
        raise HTTPException(404, "Webhook not found")
    changes = {}
    if body.name is not None:
        hook.name = body.name
        changes["name"] = body.name
    if body.url is not None:
        hook.url = body.url
        changes["url"] = body.url
    if body.events is not None:
        hook.events = body.events
        changes["events"] = body.events
    if body.is_active is not None:
        hook.is_active = body.is_active
        changes["is_active"] = body.is_active
    _log_audit(
        db,
        user,
        "webhook.update",
        "webhook",
        hook_id,
        changes=changes,
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    return {"status": "updated"}


@router.delete("/webhooks/{hook_id}")
def delete_webhook(
    hook_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_cms_manage),
):
    hook = db.query(Webhook).filter(Webhook.id == hook_id).first()
    if not hook:
        raise HTTPException(404, "Webhook not found")
    hook.deleted_at = datetime.now(timezone.utc)
    hook.is_active = False
    _log_audit(
        db, user, "webhook.delete", "webhook", hook_id, ip_address=request.client.host if request.client else None
    )
    db.commit()
    return {"status": "deleted"}


@router.get("/webhooks/{hook_id}/deliveries")
def list_webhook_deliveries(
    hook_id: str,
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(require_cms_read),
):
    deliveries = (
        db.query(WebhookDelivery)
        .filter(WebhookDelivery.webhook_id == hook_id)
        .order_by(desc(WebhookDelivery.created_at))
        .limit(limit)
        .all()
    )
    return [
        {
            "id": str(d.id),
            "event": d.event,
            "response_status": d.response_status,
            "success": d.success,
            "duration_ms": d.duration_ms,
            "created_at": d.created_at.isoformat() if d.created_at else "",
        }
        for d in deliveries
    ]
