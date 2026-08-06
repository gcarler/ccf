"""Content Permissions — CRUD de ``ContentPermission`` enterprise CMS.

Sub-router movido desde ``backend/api/enterprise_cms.py`` (split del
monolito, deuda estructural 🟠#4, 2026-08-05).
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.orm import Session

from backend.api.enterprise_cms.__common import _log_audit, require_cms_manage, require_cms_read
from backend.core.database import get_db
from backend.models_enterprise import ContentPermission
from backend.models_identity import User

router = APIRouter()


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
    user: User = Depends(require_cms_manage),
):
    perm = ContentPermission(
        site_key=body.site_key,
        entity_type=body.entity_type,
        entity_id=body.entity_id,
        permission_type=body.permission_type,
        grant_type=body.grant_type,
        grant_target=body.grant_target,
        is_denied=body.is_denied,
        created_by_persona_id=getattr(user, "persona_id", None),
    )
    db.add(perm)
    _log_audit(
        db,
        user,
        "permission.create",
        "content_permission",
        str(perm.id),
        site_key=body.site_key,
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    return {"id": str(perm.id), "status": "created"}


@router.get("/content-permissions")
def list_content_permissions(
    site_key: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_cms_read),
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
            "id": str(p.id),
            "entity_type": p.entity_type,
            "entity_id": p.entity_id,
            "permission_type": p.permission_type,
            "grant_type": p.grant_type,
            "grant_target": p.grant_target,
            "is_denied": p.is_denied,
        }
        for p in perms
    ]


@router.delete("/content-permissions/{perm_id}")
def delete_content_permission(
    perm_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_cms_manage),
):
    perm = db.query(ContentPermission).filter(ContentPermission.id == perm_id).first()
    if not perm:
        raise HTTPException(404, "Permission not found")
    perm.deleted_at = datetime.now(timezone.utc)
    _log_audit(
        db,
        user,
        "permission.delete",
        "content_permission",
        perm_id,
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    return {"status": "deleted"}
