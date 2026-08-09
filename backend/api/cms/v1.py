from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from backend import crud, models, schemas
from backend.api._cms_helpers import (
    _actor_sede_or_none,
    _get_scoped_cms_media,
    _scope_cms_media_by_user_sede,
    collect_section_media_ids,
)
from backend.api.cms_v2._shared import CMS_EDITOR_ROLES, CMS_PUBLISHER_ROLES, _assert_role
from backend.core.config import get_settings
from backend.core.database import get_db
from backend.core.permissions import require_module_access
from backend.schemas import PaginatedResponse
from backend.services.cms_media_service import (
    delete_cms_media as _delete_cms_media,
)
from backend.services.cms_media_service import (
    optimize_cms_media as _optimize_cms_media,
)
from backend.services.cms_media_service import (
    upload_cms_media as _upload_cms_media,
)

# CMS endpoints — preferir /cms/v2/* en integraciones nuevas.
router = APIRouter(tags=["cms"])
logger = logging.getLogger(__name__)

settings = get_settings()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── CMS Media ───────────────────────────────────────────


@router.get("/cms/media", response_model=PaginatedResponse[schemas.CmsMediaRead])
def list_cms_media(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=500),
    query: str | None = Query(default=None),
    section: str | None = Query(default=None),
    include_archived: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    base_query = db.query(models.CmsMediaItem)
    base_query = _scope_cms_media_by_user_sede(db, current_user, base_query)
    if not include_archived:
        base_query = base_query.filter(models.CmsMediaItem.status != "archived")
    if section:
        base_query = base_query.filter(models.CmsMediaItem.section == section)
    if query:
        from sqlalchemy import or_ as _or

        like = f"%{query.strip()}%"
        base_query = base_query.filter(
            _or(
                models.CmsMediaItem.url.ilike(like),
                models.CmsMediaItem.alt_text.ilike(like),
                models.CmsMediaItem.filename.ilike(like),
            )
        )
    total = base_query.count()
    items = base_query.order_by(models.CmsMediaItem.updated_at.desc()).offset(skip).limit(limit).all()
    return PaginatedResponse(
        items=[schemas.CmsMediaRead.model_validate(i) for i in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.post("/cms/media", response_model=schemas.CmsMediaRead, status_code=201)
def create_cms_media(
    payload: schemas.CmsMediaCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    return crud.create_cms_media_item(

        db,
        url=payload.url,
        alt_text=payload.alt_text,
        section=payload.section,
        tags=payload.tags,
        created_by=current_user.id,
        filename=payload.filename,
        mime_type=payload.mime_type,
        file_size=payload.file_size,
        width=payload.width,
        height=payload.height,
        dimensions=payload.dimensions,
        status=payload.status,
        actor_user_id=str(current_user.id),
    )


@router.get("/cms/media/{item_id}", response_model=schemas.CmsMediaRead)
def get_cms_media(
    item_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    return _get_scoped_cms_media(db, current_user, item_id)


@router.patch("/cms/media/{item_id}", response_model=schemas.CmsMediaRead)
def patch_cms_media(
    item_id: uuid.UUID,
    payload: schemas.CmsMediaUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    row = _get_scoped_cms_media(db, current_user, item_id)
    return crud.update_cms_media_item(
        db,
        row.id,
        url=payload.url,
        alt_text=payload.alt_text,
        section=payload.section,
        tags=payload.tags,
        filename=payload.filename,
        mime_type=payload.mime_type,
        file_size=payload.file_size,
        width=payload.width,
        height=payload.height,
        dimensions=payload.dimensions,
        status=payload.status,
        actor_user_id=str(current_user.id),
    )


@router.delete("/cms/media/{item_id}", status_code=204)
def delete_cms_media(
    item_id: uuid.UUID,
    permanent: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_PUBLISHER_ROLES if permanent else CMS_EDITOR_ROLES)
    row = _get_scoped_cms_media(db, current_user, item_id)
    try:
        _delete_cms_media(db, row, permanent=permanent, actor_user_id=str(current_user.id))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/cms/media/{item_id}/optimize", response_model=schemas.CmsMediaRead)
def optimize_cms_media(
    item_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    row = _get_scoped_cms_media(db, current_user, item_id)
    try:
        return _optimize_cms_media(db, row, actor_user_id=str(current_user.id))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/cms/media/upload", response_model=schemas.CmsMediaRead, status_code=201)
async def upload_cms_media(
    file: UploadFile = File(...),
    section: str = Form(default="general"),
    alt_text: str = Form(default=""),
    tags: str = Form(default=""),
    optimize: bool = Form(default=True),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    content = await file.read()
    parsed_tags = [tag.strip() for tag in tags.split(",") if tag.strip()]
    try:
        return _upload_cms_media(
            db,
            content=content,
            filename=file.filename or "asset.bin",
            content_type=file.content_type,
            section=section,
            alt_text=alt_text or file.filename or "",
            tags=parsed_tags,
            optimize=optimize,
            actor_user_id=str(current_user.id),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/cms/media/{item_id}/edit", response_model=schemas.CmsMediaRead, status_code=201)
async def edit_cms_media(
    item_id: uuid.UUID,
    file: UploadFile = File(...),
    alt_text: str | None = Form(default=None),
    section: str | None = Form(default=None),
    tags: str | None = Form(default=None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    row = _get_scoped_cms_media(db, current_user, item_id)
    content = await file.read()

    original_name = row.filename or file.filename or "image.png"
    base_name, ext = os.path.splitext(original_name)
    if not ext:
        c_type = file.content_type or row.mime_type or "image/png"
        if "jpeg" in c_type or "jpg" in c_type:
            ext = ".jpg"
        elif "webp" in c_type:
            ext = ".webp"
        else:
            ext = ".png"

    if base_name.endswith("_edited"):
        edited_filename = f"{base_name}{ext}"
    else:
        edited_filename = f"{base_name}_edited{ext}"

    parsed_tags = [tag.strip() for tag in tags.split(",") if tag.strip()] if tags is not None else (row.tags or [])

    if alt_text is not None and alt_text.strip():
        final_alt = alt_text.strip()
    else:
        orig_alt = row.alt_text or base_name
        if orig_alt.endswith("_edited"):
            final_alt = orig_alt
        else:
            final_alt = f"{orig_alt}_edited"

    final_section = section if section is not None else (row.section or "general")

    try:
        return _upload_cms_media(
            db,
            content=content,
            filename=edited_filename,
            content_type=file.content_type or row.mime_type,
            section=final_section,
            alt_text=final_alt,
            tags=parsed_tags,
            optimize=False,
            actor_user_id=str(current_user.id),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/cms/metrics", response_model=schemas.CmsMetrics)
def get_cms_metrics(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    actor_sede = _actor_sede_or_none(db, current_user)

    def _cms_posts_by_category(slug: str) -> list[models.CmsPost]:
        q = db.query(models.CmsPost).join(models.CmsPost.categories).filter(models.CmsCategory.slug == slug)
        if actor_sede is not None:
            q = q.join(models.CmsSite).filter(models.CmsSite.sede_id == actor_sede)
        return q.distinct().order_by(models.CmsPost.created_at.desc()).all()

    cms_testimonials = _cms_posts_by_category("testimonials")
    cms_announcements = _cms_posts_by_category("announcements")

    m_query = db.query(models.CmsMediaItem)
    m_query = _scope_cms_media_by_user_sede(db, current_user, m_query)
    media = m_query.all()

    return schemas.CmsMetrics(
        testimonials_total=len(cms_testimonials),
        testimonials_approved=sum(1 for p in cms_testimonials if p.status == "published"),
        announcements_total=len(cms_announcements),
        announcements_active=sum(1 for p in cms_announcements if p.status == "published"),
        media_total=len(media),
        media_images=sum(1 for row in media if (row.mime_type or "").startswith("image/")),
        media_videos=sum(1 for row in media if (row.mime_type or "").startswith("video/")),
        media_audio=sum(1 for row in media if (row.mime_type or "").startswith("audio/")),
    )


@router.post("/cms/media/cleanup")
def cleanup_orphan_cms_media_endpoint(
    dry_run: bool = Query(default=False),
    permanent: bool = Query(default=False, description="Hard-delete files + rows (default: soft-archive)"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    # Orphan cleanup is an operational/destructive action, not ordinary editorial mutation.
    _assert_role(current_user, CMS_PUBLISHER_ROLES)
    actor_sede = _actor_sede_or_none(db, current_user)
    if actor_sede is None:
        if dry_run:
            return {"purged": 0, "dry_run": True, "reason": "platform-scope disallowed"}
        raise HTTPException(
            status_code=400,
            detail="Cleanup requiere scope por sede; el superadmin sin sede no puede limpiar a nivel plataforma",
        )

    sites = db.query(models.CmsSite).filter(models.CmsSite.sede_id == actor_sede).all()
    referenced_ids: set[str] = set()
    for site in sites:
        sections = (
            db.query(models.CmsSection)
            .join(models.CmsPage, models.CmsPage.id == models.CmsSection.page_id)
            .filter(models.CmsPage.site_id == site.id)
            .filter(models.CmsSection.status != "archived")
            .filter(models.CmsSection.deleted_at.is_(None))
            .all()
        )
        for mid in collect_section_media_ids(sections):
            referenced_ids.add(mid)

    purged = crud.cleanup_orphan_cms_media(
        db,
        sede_id=actor_sede,
        referenced_media_ids=referenced_ids,
        actor_user_id=str(current_user.id),
        dry_run=dry_run,
        permanent=permanent,
    )
    return {"purged": purged, "dry_run": dry_run, "permanent": permanent}
