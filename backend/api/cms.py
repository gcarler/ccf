from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from backend import crud, models, schemas
from backend.auth import require_active_user
from backend.core.config import get_settings
from backend.core.database import get_db
from backend.core.uploads import sanitize_filename, save_upload

router = APIRouter(tags=["cms"])

TESTIMONIALS_KEY = "faro_testimonials_feed"
ANNOUNCEMENTS_KEY = "faro_announcements_feed"
settings = get_settings()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Testimonials (SQLAlchemy models) ────────────────────


@router.get("/cms/testimonials", response_model=list[schemas.TestimonialRead])
def list_cms_testimonials(db: Session = Depends(get_db)):
    return crud.list_testimonials(db, approved_only=True)


@router.post(
    "/cms/testimonials", response_model=schemas.TestimonialRead, status_code=201
)
def create_cms_testimonial(
    payload: schemas.TestimonialCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    if not payload.author_id:
        payload.author_id = current_user.id
    return crud.create_testimonial(db, payload)


@router.get("/admin/testimonials", response_model=list[schemas.TestimonialRead])
def list_admin_testimonials(
    db: Session = Depends(get_db),
    _: models.User = Depends(require_active_user),
):
    return crud.list_testimonials(db)


@router.get(
    "/cms/testimonials/{testimonial_id}", response_model=schemas.TestimonialRead
)
def get_cms_testimonial(
    testimonial_id: int,
    db: Session = Depends(get_db),
):
    row = crud.get_testimonial(db, testimonial_id)
    if not row or not row.is_approved or row.status == "archived":
        raise HTTPException(status_code=404, detail="testimonial not found")
    return row


@router.get(
    "/admin/testimonials/{testimonial_id}", response_model=schemas.TestimonialRead
)
def get_admin_testimonial(
    testimonial_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_active_user),
):
    row = crud.get_testimonial(db, testimonial_id)
    if not row:
        raise HTTPException(status_code=404, detail="testimonial not found")
    return row


@router.patch(
    "/admin/testimonials/{testimonial_id}", response_model=schemas.TestimonialRead
)
def patch_admin_testimonial(
    testimonial_id: int,
    payload: schemas.TestimonialUpdate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_active_user),
):
    row = crud.get_testimonial(db, testimonial_id)
    if not row:
        raise HTTPException(status_code=404, detail="testimonial not found")
    return crud.update_testimonial(db, row, payload)


@router.delete("/admin/testimonials/{testimonial_id}", status_code=204)
def delete_admin_testimonial(
    testimonial_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_active_user),
):
    row = crud.get_testimonial(db, testimonial_id)
    if not row:
        raise HTTPException(status_code=404, detail="testimonial not found")
    crud.delete_testimonial(db, row)


# ── Announcements (SQLAlchemy models) ───────────────────


@router.get("/cms/announcements", response_model=list[schemas.AnnouncementRead])
def list_cms_announcements(db: Session = Depends(get_db)):
    return crud.list_announcements(db, public_only=True)


@router.post(
    "/cms/announcements", response_model=schemas.AnnouncementRead, status_code=201
)
def create_cms_announcement(
    payload: schemas.AnnouncementCreate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_active_user),
):
    return crud.create_announcement(db, payload)


@router.get("/admin/announcements", response_model=list[schemas.AnnouncementRead])
def list_admin_announcements(
    db: Session = Depends(get_db),
    _: models.User = Depends(require_active_user),
):
    return crud.list_announcements(db)


@router.get(
    "/cms/announcements/{announcement_id}", response_model=schemas.AnnouncementRead
)
def get_cms_announcement(
    announcement_id: int,
    db: Session = Depends(get_db),
):
    row = crud.get_announcement(db, announcement_id)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if (
        not row
        or row.status != "published"
        or (row.published_at and row.published_at > now)
    ):
        raise HTTPException(status_code=404, detail="announcement not found")
    return row


@router.get(
    "/admin/announcements/{announcement_id}", response_model=schemas.AnnouncementRead
)
def get_admin_announcement(
    announcement_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_active_user),
):
    row = crud.get_announcement(db, announcement_id)
    if not row:
        raise HTTPException(status_code=404, detail="announcement not found")
    return row


@router.patch(
    "/admin/announcements/{announcement_id}", response_model=schemas.AnnouncementRead
)
def patch_admin_announcement(
    announcement_id: int,
    payload: schemas.AnnouncementUpdate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_active_user),
):
    row = crud.get_announcement(db, announcement_id)
    if not row:
        raise HTTPException(status_code=404, detail="announcement not found")
    return crud.update_announcement(db, row, payload)


@router.delete("/admin/announcements/{announcement_id}", status_code=204)
def delete_admin_announcement(
    announcement_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_active_user),
):
    row = crud.get_announcement(db, announcement_id)
    if not row:
        raise HTTPException(status_code=404, detail="announcement not found")
    crud.delete_announcement(db, row)


# ── CMS Media ───────────────────────────────────────────


@router.get("/cms/media", response_model=list[schemas.CmsMediaRead])
def list_cms_media(
    query: str | None = Query(default=None),
    section: str | None = Query(default=None),
    limit: int = Query(default=250, ge=1, le=500),
    include_archived: bool = Query(default=False),
    db: Session = Depends(get_db),
    _: models.User = Depends(require_active_user),
):
    return crud.list_cms_media_items(
        db, query=query, section=section, limit=limit, include_archived=include_archived
    )


@router.post("/cms/media", response_model=schemas.CmsMediaRead, status_code=201)
def create_cms_media(
    payload: schemas.CmsMediaCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
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
        status=payload.status,
    )


@router.get("/cms/media/{item_id}", response_model=schemas.CmsMediaRead)
def get_cms_media(
    item_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_active_user),
):
    row = (
        db.query(models.CmsMediaItem).filter(models.CmsMediaItem.id == item_id).first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="media item not found")
    return row


@router.patch("/cms/media/{item_id}", response_model=schemas.CmsMediaRead)
def patch_cms_media(
    item_id: int,
    payload: schemas.CmsMediaUpdate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_active_user),
):
    row = crud.update_cms_media_item(
        db,
        item_id,
        url=payload.url,
        alt_text=payload.alt_text,
        section=payload.section,
        tags=payload.tags,
        filename=payload.filename,
        mime_type=payload.mime_type,
        file_size=payload.file_size,
        status=payload.status,
    )
    if not row:
        raise HTTPException(status_code=404, detail="media item not found")
    return row


@router.delete("/cms/media/{item_id}", status_code=204)
def delete_cms_media(
    item_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_active_user),
):
    ok = crud.delete_cms_media_item(db, item_id)
    if not ok:
        raise HTTPException(status_code=404, detail="media item not found")


@router.post("/cms/media/upload", response_model=schemas.CmsMediaRead, status_code=201)
async def upload_cms_media(
    file: UploadFile = File(...),
    section: str = Form(default="general"),
    alt_text: str = Form(default=""),
    tags: str = Form(default=""),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    original_name = sanitize_filename(file.filename or "asset.bin")
    unique_name = f"cms_{uuid.uuid4().hex}_{original_name}"
    content = await file.read()
    try:
        save_upload(content, unique_name, settings.uploads_dir)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    url = f"/api/static/{unique_name}"
    parsed_tags = [tag.strip() for tag in tags.split(",") if tag.strip()]
    return crud.create_cms_media_item(
        db,
        url=url,
        alt_text=alt_text or file.filename,
        section=section,
        tags=parsed_tags,
        created_by=current_user.id,
        filename=file.filename,
        mime_type=file.content_type,
        file_size=len(content),
    )


# ── CMS Metrics ─────────────────────────────────────────


@router.get("/cms/metrics", response_model=schemas.CmsMetrics)
def get_cms_metrics(
    db: Session = Depends(get_db),
    _: models.User = Depends(require_active_user),
):
    publications = crud.list_content_publications(db)
    status_counter = {
        "draft": 0,
        "in_review": 0,
        "approved": 0,
        "published": 0,
        "archived": 0,
    }
    for item in publications:
        status_counter[item.status] = status_counter.get(item.status, 0) + 1

    testimonials = crud.list_testimonials(db)
    announcements = crud.list_announcements(db)
    media = crud.list_cms_media_items(db, limit=500)

    return schemas.CmsMetrics(
        total_blocks=len(crud.list_page_contents(db, limit=500)),
        draft_blocks=status_counter.get("draft", 0),
        in_review_blocks=status_counter.get("in_review", 0),
        approved_blocks=status_counter.get("approved", 0),
        published_blocks=status_counter.get("published", 0),
        archived_blocks=status_counter.get("archived", 0),
        testimonials_total=len(testimonials),
        testimonials_approved=sum(1 for row in testimonials if row.is_approved),
        announcements_total=len(announcements),
        announcements_active=sum(
            1 for row in announcements if row.status == "published"
        ),
        media_total=len(media),
        media_images=sum(
            1 for row in media if (row.mime_type or "").startswith("image/")
        ),
        media_videos=sum(
            1 for row in media if (row.mime_type or "").startswith("video/")
        ),
        media_audio=sum(
            1 for row in media if (row.mime_type or "").startswith("audio/")
        ),
    )


# ── CMS Pages (PageContent CRUD) ────────────────────────


@router.get("/cms/pages", response_model=list[schemas.PageContentRead])
def list_cms_pages(
    limit: int = 200,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_active_user),
):
    return crud.list_page_contents(db, limit=limit)


@router.get("/cms/pages/{page_key}", response_model=schemas.PageContentRead)
def get_cms_page(
    page_key: str,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_active_user),
):
    return crud.get_or_create_page_content(db, page_key)


@router.post("/cms/pages", response_model=schemas.PageContentRead, status_code=201)
def create_cms_page(
    payload: dict[str, Any],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    title = str(payload.get("title") or "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="title is required")
    page_key = str(payload.get("page_key") or "").strip()
    if not page_key:
        import re

        page_key = re.sub(r"[^\w-]", "", title.lower().replace(" ", "-"))
    content = str(payload.get("content") or f"# {title}\n\nNueva pagina creada.")
    row = crud.get_or_create_page_content(db, page_key)
    row.title = title
    row.content = content
    db.commit()
    db.refresh(row)
    return row


@router.patch("/cms/pages/{page_key}", response_model=schemas.PageContentRead)
def patch_cms_page(
    page_key: str,
    payload: schemas.PageContentUpdate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_active_user),
):
    return crud.update_page_content(db, page_key, payload)


@router.delete("/cms/pages/{page_key}", status_code=204)
def delete_cms_page(
    page_key: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    crud.update_content_publication(
        db,
        page_key,
        status="archived",
        updated_by=current_user.id,
    )
