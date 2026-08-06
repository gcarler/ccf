"""Broken Links — listado + resolve de ``BrokenLinkCheck`` enterprise CMS.

Sub-router movido desde ``backend/api/enterprise_cms.py`` (split del
monolito, deuda estructural 🟠#4, 2026-08-05).
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from backend.api.enterprise_cms.__common import require_cms_manage, require_cms_read
from backend.core.database import get_db
from backend.models_enterprise import BrokenLinkCheck
from backend.models_identity import User

router = APIRouter()


@router.get("/broken-links")
def list_broken_links(
    site_key: str,
    resolved: bool | None = None,
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(require_cms_read),
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
            "id": str(link.id),
            "source_url": link.source_url,
            "target_url": link.target_url,
            "status_code": link.status_code,
            "error_message": link.error_message,
            "is_broken": link.is_broken,
            "resolved_at": link.resolved_at.isoformat() if link.resolved_at else None,
            "checked_at": link.checked_at.isoformat() if link.checked_at else "",
        }
        for link in links
    ]


@router.post("/broken-links/{check_id}/resolve")
def resolve_broken_link(
    check_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_cms_manage),
):
    check = db.query(BrokenLinkCheck).filter(BrokenLinkCheck.id == check_id).first()
    if not check:
        raise HTTPException(404, "Check not found")
    check.resolved_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "resolved"}
