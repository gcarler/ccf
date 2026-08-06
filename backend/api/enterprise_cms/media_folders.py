"""Media Folders — CRUD de ``MediaFolder`` enterprise CMS.

Sub-router movido desde ``backend/api/enterprise_cms.py`` (split del
monolito, deuda estructural 🟠#4, 2026-08-05).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.api.enterprise_cms.__common import _log_audit, require_cms_manage, require_cms_read
from backend.core.database import get_db
from backend.models_enterprise import MediaFolder
from backend.models_identity import User

router = APIRouter()


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
    user: User = Depends(require_cms_manage),
):
    path = f"/{body.slug}/"
    if body.parent_id:
        parent = db.query(MediaFolder).filter(MediaFolder.id == body.parent_id).first()
        if parent:
            path = f"{parent.path}{body.slug}/"
    folder = MediaFolder(
        site_key=body.site_key,
        name=body.name,
        slug=body.slug,
        parent_id=body.parent_id,
        path=path,
        created_by_persona_id=getattr(user, "persona_id", None),
    )
    db.add(folder)
    _log_audit(
        db,
        user,
        "media_folder.create",
        "media_folder",
        str(folder.id),
        entity_slug=body.slug,
        site_key=body.site_key,
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    return {"id": str(folder.id), "path": path, "status": "created"}


@router.get("/media-folders")
def list_media_folders(
    site_key: str,
    parent_id: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_cms_read),
):
    q = db.query(MediaFolder).filter(MediaFolder.site_key == site_key)
    if parent_id:
        q = q.filter(MediaFolder.parent_id == parent_id)
    else:
        q = q.filter(MediaFolder.parent_id.is_(None))
    folders = q.order_by(MediaFolder.sort_order, MediaFolder.name).all()
    return [
        {
            "id": str(f.id),
            "name": f.name,
            "slug": f.slug,
            "path": f.path,
            "parent_id": str(f.parent_id) if f.parent_id else None,
        }
        for f in folders
    ]
