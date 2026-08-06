"""Custom Entries — CRUD + versioning + rollback de ``CmsCustomEntry``.

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
from backend.models_enterprise import CmsCustomEntry, CmsCustomEntryVersion
from backend.models_identity import User

router = APIRouter()


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
    user: User = Depends(require_cms_manage),
):
    entry = CmsCustomEntry(
        site_key=body.site_key,
        type_key=body.type_key,
        slug=body.slug,
        title=body.title,
        content_html=body.content_html,
        excerpt=body.excerpt,
        fields_json=body.fields_json,
        status=body.status,
        featured_image_url=body.featured_image_url,
        owner_persona_id=body.owner_persona_id,
        review_date=body.review_date,
        expiry_date=body.expiry_date,
        parent_id=body.parent_id,
        seo_json=body.seo_json,
        author_persona_id=getattr(user, "persona_id", None),
    )
    db.add(entry)
    db.flush()
    ver = CmsCustomEntryVersion(
        entry_id=entry.id,
        version_number=1,
        snapshot_json={"title": body.title, "content_html": body.content_html},
        created_by_persona_id=getattr(user, "persona_id", None),
    )
    db.add(ver)
    _log_audit(
        db,
        user,
        "custom_entry.create",
        "custom_entry",
        str(entry.id),
        entity_slug=body.slug,
        site_key=body.site_key,
        ip_address=request.client.host if request.client else None,
    )
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
    user: User = Depends(require_cms_read),
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
            "id": str(e.id),
            "type_key": e.type_key,
            "slug": e.slug,
            "title": e.title,
            "excerpt": e.excerpt,
            "status": e.status,
            "featured_image_url": e.featured_image_url,
            "parent_id": str(e.parent_id) if e.parent_id else None,
            "version": e.version,
            "view_count": e.view_count,
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
    user: User = Depends(require_cms_read),
):
    entry = db.query(CmsCustomEntry).filter(CmsCustomEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(404, "Entry not found")
    return {
        "id": str(entry.id),
        "type_key": entry.type_key,
        "slug": entry.slug,
        "title": entry.title,
        "content_html": entry.content_html,
        "excerpt": entry.excerpt,
        "fields_json": entry.fields_json,
        "status": entry.status,
        "featured_image_url": entry.featured_image_url,
        "owner_persona_id": entry.owner_persona_id,
        "parent_id": str(entry.parent_id) if entry.parent_id else None,
        "version": entry.version,
        "view_count": entry.view_count,
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
    user: User = Depends(require_cms_manage),
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
        entry_id=entry.id,
        version_number=entry.version,
        snapshot_json={"title": entry.title, "content_html": entry.content_html, "fields": entry.fields_json},
        created_by_persona_id=getattr(user, "persona_id", None),
    )
    db.add(ver)
    _log_audit(
        db,
        user,
        "custom_entry.update",
        "custom_entry",
        entry_id,
        entity_slug=entry.slug,
        changes=changes,
        site_key=entry.site_key,
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    return {"status": "updated", "version": entry.version}


@router.delete("/custom-entries/{entry_id}")
def delete_custom_entry(
    entry_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_cms_manage),
):
    entry = db.query(CmsCustomEntry).filter(CmsCustomEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(404, "Entry not found")
    entry.deleted_at = datetime.now(timezone.utc)
    entry.status = "archived"
    _log_audit(
        db,
        user,
        "custom_entry.delete",
        "custom_entry",
        entry_id,
        entity_slug=entry.slug,
        site_key=entry.site_key,
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    return {"status": "archived"}


@router.get("/custom-entries/{entry_id}/versions")
def list_entry_versions(
    entry_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_cms_read),
):
    versions = (
        db.query(CmsCustomEntryVersion)
        .filter(CmsCustomEntryVersion.entry_id == entry_id)
        .order_by(desc(CmsCustomEntryVersion.version_number))
        .all()
    )
    return [
        {
            "id": str(v.id),
            "version_number": v.version_number,
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
    user: User = Depends(require_cms_manage),
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
        entry_id=entry.id,
        version_number=entry.version,
        snapshot_json=snapshot,
        notes=f"Rollback to version {version.version_number}",
        created_by_persona_id=getattr(user, "persona_id", None),
    )
    db.add(new_ver)
    _log_audit(
        db,
        user,
        "custom_entry.rollback",
        "custom_entry",
        entry_id,
        entity_slug=entry.slug,
        changes={"rollback_to": version.version_number},
        site_key=entry.site_key,
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    return {"status": "rolled_back", "new_version": entry.version}
