"""
Enterprise CMS API — Audit Trail, Content Permissions, Notifications,
Webhooks, Custom Post Types, Search, Session Management, Media Folders,
File Versions, Redirects, Broken Link Check.

All endpoints require authentication. Role-based access where noted.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import and_, desc, func, or_, text
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.core.permissions import get_current_user
from backend.models_enterprise import (
    AuditLog, BrokenLinkCheck, CmsCustomEntry, CmsCustomEntryVersion,
    CmsCustomType, CmsGlossaryTerm, CmsNotification, CmsRedirect,
    ContentPermission, MediaFileVersion, MediaFolder, SearchIndex,
    SearchPromotion, UserSession, Webhook, WebhookDelivery,
)
from backend.models_identity import User

router = APIRouter(prefix="/cms/v2", tags=["Enterprise CMS"])


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _log_audit(
    db: Session,
    user: User,
    action: str,
    entity_type: str,
    entity_id: str | None = None,
    entity_slug: str | None = None,
    site_key: str | None = None,
    changes: dict | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
):
    log = AuditLog(
        actor_persona_id=getattr(user, "persona_id", None),
        actor_email=getattr(user, "email", None),
        actor_role=getattr(user, "role", None),
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        entity_slug=entity_slug,
        site_key=site_key,
        changes_json=changes,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(log)
    db.flush()
    return log


def _notify(
    db: Session,
    recipient_id,
    actor_id,
    notification_type: str,
    title: str,
    body: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    entity_slug: str | None = None,
    site_key: str | None = None,
    action_url: str | None = None,
):
    notif = CmsNotification(
        recipient_persona_id=recipient_id,
        actor_persona_id=actor_id,
        notification_type=notification_type,
        title=title,
        body=body,
        entity_type=entity_type,
        entity_id=entity_id,
        entity_slug=entity_slug,
        site_key=site_key,
        action_url=action_url,
    )
    db.add(notif)
    db.flush()
    return notif


def _fire_webhooks(db: Session, site_key: str, event: str, payload: dict):
    hooks = db.query(Webhook).filter(
        Webhook.site_key == site_key,
        Webhook.is_active == True,
    ).all()
    for hook in hooks:
        if event in (hook.events or []) or "*" in (hook.events or []):
            delivery = WebhookDelivery(
                webhook_id=hook.id,
                event=event,
                payload_json=payload,
                success=False,
            )
            db.add(delivery)
            hook.last_triggered_at = datetime.now(timezone.utc)
    db.flush()


# ═══════════════════════════════════════════════════════════════════════════════
# 1. AUDIT TRAIL
# ═══════════════════════════════════════════════════════════════════════════════

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
    user: User = Depends(get_current_user),
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
            id=str(l.id), actor_email=l.actor_email, actor_role=l.actor_role,
            action=l.action, entity_type=l.entity_type, entity_id=l.entity_id,
            entity_slug=l.entity_slug, changes_json=l.changes_json,
            ip_address=l.ip_address, severity=l.severity,
            created_at=l.created_at.isoformat() if l.created_at else "",
        )
        for l in logs
    ]


# ═══════════════════════════════════════════════════════════════════════════════
# 2. CONTENT PERMISSIONS
# ═══════════════════════════════════════════════════════════════════════════════

class ContentPermCreate(BaseModel):
    site_key: str
    entity_type: str
    entity_id: str
    permission_type: str
    grant_type: str
    grant_target: str
    is_denied: bool = False


@router.post("/content-permissions")
def create_content_permission(
    body: ContentPermCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    perm = ContentPermission(
        site_key=body.site_key, entity_type=body.entity_type,
        entity_id=body.entity_id, permission_type=body.permission_type,
        grant_type=body.grant_type, grant_target=body.grant_target,
        is_denied=body.is_denied,
        created_by_persona_id=getattr(user, "persona_id", None),
    )
    db.add(perm)
    _log_audit(db, user, "permission.create", "content_permission",
               str(perm.id), site_key=body.site_key,
               ip_address=request.client.host if request.client else None)
    db.commit()
    return {"id": str(perm.id), "status": "created"}


@router.get("/content-permissions")
def list_content_permissions(
    site_key: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = db.query(ContentPermission).filter(
        ContentPermission.site_key == site_key,
        ContentPermission.deleted_at.is_(None),
    )
    if entity_type:
        q = q.filter(ContentPermission.entity_type == entity_type)
    if entity_id:
        q = q.filter(ContentPermission.entity_id == entity_id)
    perms = q.order_by(desc(ContentPermission.created_at)).all()
    return [
        {
            "id": str(p.id), "entity_type": p.entity_type, "entity_id": p.entity_id,
            "permission_type": p.permission_type, "grant_type": p.grant_type,
            "grant_target": p.grant_target, "is_denied": p.is_denied,
        }
        for p in perms
    ]


@router.delete("/content-permissions/{perm_id}")
def delete_content_permission(
    perm_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    perm = db.query(ContentPermission).filter(ContentPermission.id == perm_id).first()
    if not perm:
        raise HTTPException(404, "Permission not found")
    perm.deleted_at = datetime.now(timezone.utc)
    _log_audit(db, user, "permission.delete", "content_permission", perm_id,
               ip_address=request.client.host if request.client else None)
    db.commit()
    return {"status": "deleted"}


# ═══════════════════════════════════════════════════════════════════════════════
# 3. NOTIFICATIONS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/notifications")
def list_notifications(
    unread_only: bool = False,
    limit: int = Query(30, le=100),
    offset: int = 0,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    persona_id = getattr(user, "persona_id", None)
    if not persona_id:
        return {"items": [], "total_unread": 0}
    q = db.query(CmsNotification).filter(CmsNotification.recipient_persona_id == persona_id)
    if unread_only:
        q = q.filter(CmsNotification.is_read == False)
    notifs = q.order_by(desc(CmsNotification.created_at)).offset(offset).limit(limit).all()
    total_unread = db.query(func.count(CmsNotification.id)).filter(
        CmsNotification.recipient_persona_id == persona_id,
        CmsNotification.is_read == False,
    ).scalar()
    return {
        "items": [
            {
                "id": str(n.id), "type": n.notification_type,
                "title": n.title, "body": n.body,
                "entity_type": n.entity_type, "entity_slug": n.entity_slug,
                "is_read": n.is_read, "action_url": n.action_url,
                "created_at": n.created_at.isoformat() if n.created_at else "",
            }
            for n in notifs
        ],
        "total_unread": total_unread,
    }


@router.post("/notifications/{notif_id}/read")
def mark_notification_read(
    notif_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    notif = db.query(CmsNotification).filter(CmsNotification.id == notif_id).first()
    if not notif:
        raise HTTPException(404, "Notification not found")
    notif.is_read = True
    notif.read_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "read"}


@router.post("/notifications/read-all")
def mark_all_notifications_read(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    persona_id = getattr(user, "persona_id", None)
    if not persona_id:
        return {"count": 0}
    count = db.query(CmsNotification).filter(
        CmsNotification.recipient_persona_id == persona_id,
        CmsNotification.is_read == False,
    ).update({"is_read": True, "read_at": datetime.now(timezone.utc)})
    db.commit()
    return {"count": count}


# ═══════════════════════════════════════════════════════════════════════════════
# 4. WEBHOOKS
# ═══════════════════════════════════════════════════════════════════════════════

class WebhookCreate(BaseModel):
    site_key: str
    name: str
    url: str
    secret: str | None = None
    events: list[str] = []


@router.post("/webhooks")
def create_webhook(
    body: WebhookCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    hook = Webhook(
        site_key=body.site_key, name=body.name, url=body.url,
        secret=body.secret, events=body.events,
        created_by_persona_id=getattr(user, "persona_id", None),
    )
    db.add(hook)
    _log_audit(db, user, "webhook.create", "webhook", str(hook.id),
               site_key=body.site_key,
               ip_address=request.client.host if request.client else None)
    db.commit()
    return {"id": str(hook.id), "status": "created"}


@router.get("/webhooks")
def list_webhooks(
    site_key: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    hooks = db.query(Webhook).filter(
        Webhook.site_key == site_key,
        Webhook.deleted_at.is_(None),
    ).order_by(desc(Webhook.created_at)).all()
    return [
        {
            "id": str(h.id), "name": h.name, "url": h.url,
            "events": h.events, "is_active": h.is_active,
            "last_triggered_at": h.last_triggered_at.isoformat() if h.last_triggered_at else None,
            "failure_count": h.failure_count,
        }
        for h in hooks
    ]


class WebhookUpdate(BaseModel):
    name: str | None = None
    url: str | None = None
    events: list[str] | None = None
    is_active: bool | None = None


@router.patch("/webhooks/{hook_id}")
def update_webhook(
    hook_id: str,
    body: WebhookUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
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
    _log_audit(db, user, "webhook.update", "webhook", hook_id,
               changes=changes,
               ip_address=request.client.host if request.client else None)
    db.commit()
    return {"status": "updated"}


@router.delete("/webhooks/{hook_id}")
def delete_webhook(
    hook_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    hook = db.query(Webhook).filter(Webhook.id == hook_id).first()
    if not hook:
        raise HTTPException(404, "Webhook not found")
    hook.deleted_at = datetime.now(timezone.utc)
    hook.is_active = False
    _log_audit(db, user, "webhook.delete", "webhook", hook_id,
               ip_address=request.client.host if request.client else None)
    db.commit()
    return {"status": "deleted"}


@router.get("/webhooks/{hook_id}/deliveries")
def list_webhook_deliveries(
    hook_id: str,
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    deliveries = db.query(WebhookDelivery).filter(
        WebhookDelivery.webhook_id == hook_id
    ).order_by(desc(WebhookDelivery.created_at)).limit(limit).all()
    return [
        {
            "id": str(d.id), "event": d.event,
            "response_status": d.response_status,
            "success": d.success, "duration_ms": d.duration_ms,
            "created_at": d.created_at.isoformat() if d.created_at else "",
        }
        for d in deliveries
    ]


# ═══════════════════════════════════════════════════════════════════════════════
# 5. CUSTOM POST TYPES
# ═══════════════════════════════════════════════════════════════════════════════

class CustomTypeCreate(BaseModel):
    site_key: str
    type_key: str
    label: str
    label_plural: str | None = None
    icon: str | None = None
    supports: list[str] = ["title", "editor"]
    fields_schema: dict = {}


@router.post("/custom-types")
def create_custom_type(
    body: CustomTypeCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    existing = db.query(CmsCustomType).filter(
        CmsCustomType.site_key == body.site_key,
        CmsCustomType.type_key == body.type_key,
    ).first()
    if existing:
        raise HTTPException(409, "Custom type already exists")
    ct = CmsCustomType(
        site_key=body.site_key, type_key=body.type_key,
        label=body.label, label_plural=body.label_plural,
        icon=body.icon, supports=body.supports,
        fields_schema=body.fields_schema,
    )
    db.add(ct)
    _log_audit(db, user, "custom_type.create", "custom_type", str(ct.id),
               entity_slug=body.type_key, site_key=body.site_key,
               ip_address=request.client.host if request.client else None)
    db.commit()
    return {"id": str(ct.id), "status": "created"}


@router.get("/custom-types")
def list_custom_types(
    site_key: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    types = db.query(CmsCustomType).filter(
        CmsCustomType.site_key == site_key,
        CmsCustomType.is_active == True,
    ).all()
    return [
        {
            "id": str(t.id), "type_key": t.type_key,
            "label": t.label, "label_plural": t.label_plural,
            "icon": t.icon, "supports": t.supports,
            "fields_schema": t.fields_schema,
        }
        for t in types
    ]


class CustomEntryCreate(BaseModel):
    site_key: str
    type_key: str
    slug: str
    title: str
    content_html: str | None = None
    excerpt: str | None = None
    fields_json: dict = {}
    status: str = "draft"
    featured_image_url: str | None = None
    owner_persona_id: str | None = None
    review_date: str | None = None
    expiry_date: str | None = None
    parent_id: str | None = None
    seo_json: dict = {}


@router.post("/custom-entries")
def create_custom_entry(
    body: CustomEntryCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    entry = CmsCustomEntry(
        site_key=body.site_key, type_key=body.type_key,
        slug=body.slug, title=body.title,
        content_html=body.content_html, excerpt=body.excerpt,
        fields_json=body.fields_json, status=body.status,
        featured_image_url=body.featured_image_url,
        owner_persona_id=body.owner_persona_id,
        review_date=body.review_date, expiry_date=body.expiry_date,
        parent_id=body.parent_id, seo_json=body.seo_json,
        author_persona_id=getattr(user, "persona_id", None),
    )
    db.add(entry)
    db.flush()
    ver = CmsCustomEntryVersion(
        entry_id=entry.id, version_number=1,
        snapshot_json={"title": body.title, "content_html": body.content_html},
        created_by_persona_id=getattr(user, "persona_id", None),
    )
    db.add(ver)
    _log_audit(db, user, "custom_entry.create", "custom_entry",
               str(entry.id), entity_slug=body.slug, site_key=body.site_key,
               ip_address=request.client.host if request.client else None)
    db.commit()
    return {"id": str(entry.id), "status": "created"}


@router.get("/custom-entries")
def list_custom_entries(
    site_key: str,
    type_key: str | None = None,
    status: str | None = None,
    parent_id: str | None = None,
    search: str | None = None,
    limit: int = Query(30, le=100),
    offset: int = 0,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = db.query(CmsCustomEntry).filter(
        CmsCustomEntry.site_key == site_key,
        CmsCustomEntry.deleted_at.is_(None),
    )
    if type_key:
        q = q.filter(CmsCustomEntry.type_key == type_key)
    if status:
        q = q.filter(CmsCustomEntry.status == status)
    if parent_id:
        q = q.filter(CmsCustomEntry.parent_id == parent_id)
    if search:
        q = q.filter(CmsCustomEntry.title.ilike(f"%{search}%"))
    entries = q.order_by(CmsCustomEntry.sort_order, desc(CmsCustomEntry.created_at)).offset(offset).limit(limit).all()
    return [
        {
            "id": str(e.id), "type_key": e.type_key, "slug": e.slug,
            "title": e.title, "excerpt": e.excerpt, "status": e.status,
            "featured_image_url": e.featured_image_url,
            "parent_id": str(e.parent_id) if e.parent_id else None,
            "version": e.version, "view_count": e.view_count,
            "review_date": e.review_date.isoformat() if e.review_date else None,
            "expiry_date": e.expiry_date.isoformat() if e.expiry_date else None,
            "created_at": e.created_at.isoformat() if e.created_at else "",
        }
        for e in entries
    ]


@router.get("/custom-entries/{entry_id}")
def get_custom_entry(
    entry_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    entry = db.query(CmsCustomEntry).filter(CmsCustomEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(404, "Entry not found")
    return {
        "id": str(entry.id), "type_key": entry.type_key, "slug": entry.slug,
        "title": entry.title, "content_html": entry.content_html,
        "excerpt": entry.excerpt, "fields_json": entry.fields_json,
        "status": entry.status, "featured_image_url": entry.featured_image_url,
        "owner_persona_id": entry.owner_persona_id,
        "parent_id": str(entry.parent_id) if entry.parent_id else None,
        "version": entry.version, "view_count": entry.view_count,
        "review_date": entry.review_date.isoformat() if entry.review_date else None,
        "expiry_date": entry.expiry_date.isoformat() if entry.expiry_date else None,
        "seo_json": entry.seo_json,
        "created_at": entry.created_at.isoformat() if entry.created_at else "",
        "updated_at": entry.updated_at.isoformat() if entry.updated_at else "",
    }


@router.patch("/custom-entries/{entry_id}")
def update_custom_entry(
    entry_id: str,
    request: Request,
    title: str | None = None,
    content_html: str | None = None,
    status: str | None = None,
    fields_json: dict | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    entry = db.query(CmsCustomEntry).filter(CmsCustomEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(404, "Entry not found")
    changes = {}
    if title is not None:
        changes["title"] = {"old": entry.title, "new": title}
        entry.title = title
    if content_html is not None:
        changes["content_html"] = {"changed": True}
        entry.content_html = content_html
    if status is not None:
        changes["status"] = {"old": entry.status, "new": status}
        entry.status = status
    if fields_json is not None:
        changes["fields_json"] = {"changed": True}
        entry.fields_json = fields_json
    entry.version += 1
    ver = CmsCustomEntryVersion(
        entry_id=entry.id, version_number=entry.version,
        snapshot_json={"title": entry.title, "content_html": entry.content_html, "fields": entry.fields_json},
        created_by_persona_id=getattr(user, "persona_id", None),
    )
    db.add(ver)
    _log_audit(db, user, "custom_entry.update", "custom_entry", entry_id,
               entity_slug=entry.slug, changes=changes, site_key=entry.site_key,
               ip_address=request.client.host if request.client else None)
    db.commit()
    return {"status": "updated", "version": entry.version}


@router.delete("/custom-entries/{entry_id}")
def delete_custom_entry(
    entry_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    entry = db.query(CmsCustomEntry).filter(CmsCustomEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(404, "Entry not found")
    entry.deleted_at = datetime.now(timezone.utc)
    entry.status = "archived"
    _log_audit(db, user, "custom_entry.delete", "custom_entry", entry_id,
               entity_slug=entry.slug, site_key=entry.site_key,
               ip_address=request.client.host if request.client else None)
    db.commit()
    return {"status": "archived"}


@router.get("/custom-entries/{entry_id}/versions")
def list_entry_versions(
    entry_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    versions = db.query(CmsCustomEntryVersion).filter(
        CmsCustomEntryVersion.entry_id == entry_id
    ).order_by(desc(CmsCustomEntryVersion.version_number)).all()
    return [
        {
            "id": str(v.id), "version_number": v.version_number,
            "notes": v.notes,
            "created_at": v.created_at.isoformat() if v.created_at else "",
        }
        for v in versions
    ]


@router.post("/custom-entries/{entry_id}/rollback/{version_id}")
def rollback_entry_version(
    entry_id: str,
    version_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    entry = db.query(CmsCustomEntry).filter(CmsCustomEntry.id == entry_id).first()
    version = db.query(CmsCustomEntryVersion).filter(CmsCustomEntryVersion.id == version_id).first()
    if not entry or not version:
        raise HTTPException(404, "Entry or version not found")
    snapshot = version.snapshot_json or {}
    if "title" in snapshot:
        entry.title = snapshot["title"]
    if "content_html" in snapshot:
        entry.content_html = snapshot["content_html"]
    entry.version += 1
    new_ver = CmsCustomEntryVersion(
        entry_id=entry.id, version_number=entry.version,
        snapshot_json=snapshot,
        notes=f"Rollback to version {version.version_number}",
        created_by_persona_id=getattr(user, "persona_id", None),
    )
    db.add(new_ver)
    _log_audit(db, user, "custom_entry.rollback", "custom_entry", entry_id,
               entity_slug=entry.slug, changes={"rollback_to": version.version_number},
               site_key=entry.site_key,
               ip_address=request.client.host if request.client else None)
    db.commit()
    return {"status": "rolled_back", "new_version": entry.version}


# ═══════════════════════════════════════════════════════════════════════════════
# 6. GLOSSARY
# ═══════════════════════════════════════════════════════════════════════════════

class GlossaryTermCreate(BaseModel):
    site_key: str
    term: str
    definition: str
    aliases: list[str] = []
    category: str | None = None
    language: str = "es"


@router.post("/glossary")
def create_glossary_term(
    body: GlossaryTermCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    t = CmsGlossaryTerm(
        site_key=body.site_key, term=body.term, definition=body.definition,
        aliases=body.aliases, category=body.category, language=body.language,
        created_by_persona_id=getattr(user, "persona_id", None),
    )
    db.add(t)
    _log_audit(db, user, "glossary.create", "glossary_term", str(t.id),
               entity_slug=body.term, site_key=body.site_key,
               ip_address=request.client.host if request.client else None)
    db.commit()
    return {"id": str(t.id), "status": "created"}


@router.get("/glossary")
def list_glossary_terms(
    site_key: str,
    search: str | None = None,
    category: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = db.query(CmsGlossaryTerm).filter(
        CmsGlossaryTerm.site_key == site_key,
        CmsGlossaryTerm.is_published == True,
    )
    if search:
        q = q.filter(or_(
            CmsGlossaryTerm.term.ilike(f"%{search}%"),
            CmsGlossaryTerm.definition.ilike(f"%{search}%"),
        ))
    if category:
        q = q.filter(CmsGlossaryTerm.category == category)
    terms = q.order_by(CmsGlossaryTerm.term).all()
    return [
        {
            "id": str(t.id), "term": t.term, "definition": t.definition,
            "aliases": t.aliases, "category": t.category, "language": t.language,
        }
        for t in terms
    ]


# ═══════════════════════════════════════════════════════════════════════════════
# 7. SEARCH
# ═══════════════════════════════════════════════════════════════════════════════

class SearchRequest(BaseModel):
    site_key: str
    query: str
    entity_type: str | None = None
    category: str | None = None
    limit: int = 20


@router.post("/search")
def search_content(
    body: SearchRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = db.query(SearchIndex).filter(
        SearchIndex.site_key == body.site_key,
        SearchIndex.is_published == True,
    )
    if body.entity_type:
        q = q.filter(SearchIndex.entity_type == body.entity_type)
    if body.category:
        q = q.filter(SearchIndex.category == body.category)
    # Full-text search using PostgreSQL ILIKE (upgrade to tsvector for production)
    search_term = f"%{body.query}%"
    q = q.filter(or_(
        SearchIndex.title.ilike(search_term),
        SearchIndex.body_text.ilike(search_term),
    ))
    # Check for promoted results first
    promoted = db.query(SearchPromotion).filter(
        SearchPromotion.site_key == body.site_key,
        SearchPromotion.query_text.ilike(f"%{body.query}%"),
        SearchPromotion.is_active == True,
    ).all()
    results = q.order_by(desc(SearchIndex.boost_score), desc(SearchIndex.updated_at)).limit(body.limit).all()
    return {
        "query": body.query,
        "promoted": [
            {"entity_type": p.entity_type, "entity_id": p.entity_id,
             "entity_slug": p.entity_slug, "title": p.title}
            for p in promoted
        ],
        "results": [
            {"entity_type": r.entity_type, "entity_id": r.entity_id,
             "entity_slug": r.entity_slug, "title": r.title,
             "category": r.category, "boost_score": r.boost_score}
            for r in results
        ],
        "total": len(results),
    }


class SearchPromotionCreate(BaseModel):
    site_key: str
    query_text: str
    entity_type: str
    entity_id: str
    entity_slug: str | None = None
    title: str | None = None
    boost_score: int = 100


@router.post("/search/promotions")
def create_search_promotion(
    body: SearchPromotionCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    promo = SearchPromotion(
        site_key=body.site_key, query_text=body.query_text,
        entity_type=body.entity_type, entity_id=body.entity_id,
        entity_slug=body.entity_slug, title=body.title,
        boost_score=body.boost_score,
        created_by_persona_id=getattr(user, "persona_id", None),
    )
    db.add(promo)
    _log_audit(db, user, "search.promotion.create", "search_promotion",
               str(promo.id), site_key=body.site_key,
               ip_address=request.client.host if request.client else None)
    db.commit()
    return {"id": str(promo.id), "status": "created"}


# ═══════════════════════════════════════════════════════════════════════════════
# 8. SESSION MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/sessions")
def list_user_sessions(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    persona_id = getattr(user, "persona_id", None)
    if not persona_id:
        return []
    sessions = db.query(UserSession).filter(
        UserSession.persona_id == persona_id,
        UserSession.is_active == True,
    ).order_by(desc(UserSession.last_activity_at)).all()
    return [
        {
            "id": str(s.id), "browser": s.browser, "os": s.os,
            "is_mobile": s.is_mobile, "ip_address": s.ip_address,
            "last_activity_at": s.last_activity_at.isoformat() if s.last_activity_at else "",
            "created_at": s.created_at.isoformat() if s.created_at else "",
        }
        for s in sessions
    ]


@router.post("/sessions/{session_id}/revoke")
def revoke_session(
    session_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    session = db.query(UserSession).filter(UserSession.id == session_id).first()
    if not session:
        raise HTTPException(404, "Session not found")
    persona_id = getattr(user, "persona_id", None)
    if str(session.persona_id) != str(persona_id) and getattr(user, "role", None) != "admin":
        raise HTTPException(403, "Cannot revoke other users' sessions")
    session.is_active = False
    session.revoked_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "revoked"}


@router.post("/sessions/revoke-all")
def revoke_all_sessions(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    persona_id = getattr(user, "persona_id", None)
    if not persona_id:
        return {"count": 0}
    count = db.query(UserSession).filter(
        UserSession.persona_id == persona_id,
        UserSession.is_active == True,
    ).update({"is_active": False, "revoked_at": datetime.now(timezone.utc)})
    db.commit()
    return {"count": count}


# ═══════════════════════════════════════════════════════════════════════════════
# 9. MEDIA FOLDERS
# ═══════════════════════════════════════════════════════════════════════════════

class MediaFolderCreate(BaseModel):
    site_key: str
    name: str
    slug: str
    parent_id: str | None = None


@router.post("/media-folders")
def create_media_folder(
    body: MediaFolderCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    path = f"/{body.slug}/"
    if body.parent_id:
        parent = db.query(MediaFolder).filter(MediaFolder.id == body.parent_id).first()
        if parent:
            path = f"{parent.path}{body.slug}/"
    folder = MediaFolder(
        site_key=body.site_key, name=body.name, slug=body.slug,
        parent_id=body.parent_id, path=path,
        created_by_persona_id=getattr(user, "persona_id", None),
    )
    db.add(folder)
    _log_audit(db, user, "media_folder.create", "media_folder", str(folder.id),
               entity_slug=body.slug, site_key=body.site_key,
               ip_address=request.client.host if request.client else None)
    db.commit()
    return {"id": str(folder.id), "path": path, "status": "created"}


@router.get("/media-folders")
def list_media_folders(
    site_key: str,
    parent_id: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = db.query(MediaFolder).filter(MediaFolder.site_key == site_key)
    if parent_id:
        q = q.filter(MediaFolder.parent_id == parent_id)
    else:
        q = q.filter(MediaFolder.parent_id.is_(None))
    folders = q.order_by(MediaFolder.sort_order, MediaFolder.name).all()
    return [
        {"id": str(f.id), "name": f.name, "slug": f.slug, "path": f.path,
         "parent_id": str(f.parent_id) if f.parent_id else None}
        for f in folders
    ]


# ═══════════════════════════════════════════════════════════════════════════════
# 10. REDIRECTS
# ═══════════════════════════════════════════════════════════════════════════════

class RedirectCreate(BaseModel):
    site_key: str
    from_path: str
    to_path: str
    status_code: int = 301


@router.post("/redirects")
def create_redirect(
    body: RedirectCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    redir = CmsRedirect(
        site_key=body.site_key, from_path=body.from_path,
        to_path=body.to_path, status_code=body.status_code,
        created_by_persona_id=getattr(user, "persona_id", None),
    )
    db.add(redir)
    _log_audit(db, user, "redirect.create", "redirect", str(redir.id),
               site_key=body.site_key,
               ip_address=request.client.host if request.client else None)
    db.commit()
    return {"id": str(redir.id), "status": "created"}


@router.get("/redirects")
def list_redirects(
    site_key: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    redirs = db.query(CmsRedirect).filter(
        CmsRedirect.site_key == site_key,
        CmsRedirect.is_active == True,
    ).order_by(CmsRedirect.from_path).all()
    return [
        {"id": str(r.id), "from_path": r.from_path, "to_path": r.to_path,
         "status_code": r.status_code, "hit_count": r.hit_count}
        for r in redirs
    ]


@router.delete("/redirects/{redirect_id}")
def delete_redirect(
    redirect_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    redir = db.query(CmsRedirect).filter(CmsRedirect.id == redirect_id).first()
    if not redir:
        raise HTTPException(404, "Redirect not found")
    redir.is_active = False
    db.commit()
    return {"status": "deactivated"}


# ═══════════════════════════════════════════════════════════════════════════════
# 11. BROKEN LINK CHECK
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/broken-links")
def list_broken_links(
    site_key: str,
    resolved: bool | None = None,
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = db.query(BrokenLinkCheck).filter(BrokenLinkCheck.site_key == site_key)
    if resolved is not None:
        if resolved:
            q = q.filter(BrokenLinkCheck.resolved_at.isnot(None))
        else:
            q = q.filter(BrokenLinkCheck.resolved_at.is_(None))
    links = q.order_by(desc(BrokenLinkCheck.checked_at)).limit(limit).all()
    return [
        {
            "id": str(l.id), "source_url": l.source_url,
            "target_url": l.target_url, "status_code": l.status_code,
            "error_message": l.error_message, "is_broken": l.is_broken,
            "resolved_at": l.resolved_at.isoformat() if l.resolved_at else None,
            "checked_at": l.checked_at.isoformat() if l.checked_at else "",
        }
        for l in links
    ]


@router.post("/broken-links/{check_id}/resolve")
def resolve_broken_link(
    check_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    check = db.query(BrokenLinkCheck).filter(BrokenLinkCheck.id == check_id).first()
    if not check:
        raise HTTPException(404, "Check not found")
    check.resolved_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "resolved"}
