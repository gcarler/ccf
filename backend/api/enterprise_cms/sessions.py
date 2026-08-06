"""User Sessions — listado + revocación de ``UserSession`` enterprise CMS.

Sub-router movido desde ``backend/api/enterprise_cms.py`` (split del
monolito, deuda estructural 🟠#4, 2026-08-05).
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from backend.api.enterprise_cms.__common import require_cms_manage, require_cms_read
from backend.core.database import get_db
from backend.models_enterprise import UserSession
from backend.models_identity import User

router = APIRouter()


@router.get("/sessions")
def list_user_sessions(
    db: Session = Depends(get_db),
    user: User = Depends(require_cms_read),
):
    persona_id = getattr(user, "persona_id", None)
    if not persona_id:
        return []
    sessions = (
        db.query(UserSession)
        .filter(
            UserSession.persona_id == persona_id,
            UserSession.is_active == True,
        )
        .order_by(desc(UserSession.last_activity_at))
        .all()
    )
    return [
        {
            "id": str(s.id),
            "browser": s.browser,
            "os": s.os,
            "is_mobile": s.is_mobile,
            "ip_address": s.ip_address,
            "last_activity_at": s.last_activity_at.isoformat() if s.last_activity_at else "",
            "created_at": s.created_at.isoformat() if s.created_at else "",
        }
        for s in sessions
    ]


@router.post("/sessions/{session_id}/revoke")
def revoke_session(
    session_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_cms_manage),
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
    user: User = Depends(require_cms_manage),
):
    persona_id = getattr(user, "persona_id", None)
    if not persona_id:
        return {"count": 0}
    count = (
        db.query(UserSession)
        .filter(
            UserSession.persona_id == persona_id,
            UserSession.is_active == True,
        )
        .update({"is_active": False, "revoked_at": datetime.now(timezone.utc)})
    )
    db.commit()
    return {"count": count}
