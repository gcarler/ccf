"""Notifications — bandeja in-app de ``CmsNotification`` enterprise CMS.

Sub-router movido desde ``backend/api/enterprise_cms.py`` (split del
monolito, deuda estructural 🟠#4, 2026-08-05).
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from backend.api.enterprise_cms.__common import require_cms_manage, require_cms_read
from backend.core.database import get_db
from backend.models_enterprise import CmsNotification
from backend.models_identity import User

router = APIRouter()


@router.get("/notifications")
def list_notifications(
    unread_only: bool = False,
    limit: int = Query(30, le=100),
    offset: int = 0,
    db: Session = Depends(get_db),
    user: User = Depends(require_cms_read),
):
    persona_id = getattr(user, "persona_id", None)
    if not persona_id:
        return {"items": [], "total_unread": 0}
    q = db.query(CmsNotification).filter(CmsNotification.recipient_persona_id == persona_id)
    if unread_only:
        q = q.filter(CmsNotification.is_read == False)
    notifs = q.order_by(desc(CmsNotification.created_at)).offset(offset).limit(limit).all()
    total_unread = (
        db.query(func.count(CmsNotification.id))
        .filter(
            CmsNotification.recipient_persona_id == persona_id,
            CmsNotification.is_read == False,
        )
        .scalar()
    )
    return {
        "items": [
            {
                "id": str(n.id),
                "type": n.notification_type,
                "title": n.title,
                "body": n.body,
                "entity_type": n.entity_type,
                "entity_slug": n.entity_slug,
                "is_read": n.is_read,
                "action_url": n.action_url,
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
    user: User = Depends(require_cms_manage),
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
    user: User = Depends(require_cms_manage),
):
    persona_id = getattr(user, "persona_id", None)
    if not persona_id:
        return {"count": 0}
    count = (
        db.query(CmsNotification)
        .filter(
            CmsNotification.recipient_persona_id == persona_id,
            CmsNotification.is_read == False,
        )
        .update({"is_read": True, "read_at": datetime.now(timezone.utc)})
    )
    db.commit()
    return {"count": count}
