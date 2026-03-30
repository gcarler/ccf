from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
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


def _load_json_list(db: Session, page_key: str) -> list[dict[str, Any]]:
    row = crud.get_or_create_page_content(db, page_key)
    if not row.content:
        return []
    try:
        parsed = json.loads(row.content)
        if isinstance(parsed, list):
            return [item for item in parsed if isinstance(item, dict)]
        return []
    except json.JSONDecodeError:
        return []


def _save_json_list(db: Session, page_key: str, rows: list[dict[str, Any]]) -> None:
    crud.update_page_content(
        db,
        page_key,
        schemas.PageContentUpdate(title=None, content=json.dumps(rows, ensure_ascii=False, indent=2)),
    )


def _next_numeric_id(rows: list[dict[str, Any]]) -> int:
    max_id = 0
    for row in rows:
        row_id = row.get("id")
        if isinstance(row_id, int) and row_id > max_id:
            max_id = row_id
    return max_id + 1


@router.get("/cms/testimonials")
def list_cms_testimonials(db: Session = Depends(get_db)):
    rows = _load_json_list(db, TESTIMONIALS_KEY)
    rows.sort(key=lambda item: item.get("created_at", ""), reverse=True)
    return rows


@router.post("/cms/testimonials", status_code=201)
def create_cms_testimonial(
    payload: dict[str, Any],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    rows = _load_json_list(db, TESTIMONIALS_KEY)
    content = str(payload.get("content") or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="content is required")

    item = {
        "id": _next_numeric_id(rows),
        "content": content,
        "emotion": str(payload.get("emotion") or "General"),
        "is_approved": bool(payload.get("is_approved", False)),
        "show_on_home": bool(payload.get("show_on_home", False)),
        "author_id": int(payload.get("author_id") or current_user.id),
        "author": {
            "id": current_user.id,
            "username": current_user.username,
        },
        "created_at": _now_iso(),
    }
    rows.append(item)
    _save_json_list(db, TESTIMONIALS_KEY, rows)
    return item


@router.get("/testimonials")
def list_testimonials_alias(db: Session = Depends(get_db)):
    rows = list_cms_testimonials(db)
    return [item for item in rows if item.get("is_approved")]


@router.post("/testimonials", status_code=201)
def create_testimonial_alias(
    payload: dict[str, Any],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    return create_cms_testimonial(payload, db, current_user)


@router.get("/admin/testimonials")
def list_admin_testimonials(
    db: Session = Depends(get_db),
    _: models.User = Depends(require_active_user),
):
    return list_cms_testimonials(db)


@router.patch("/admin/testimonials/{testimonial_id}")
def patch_admin_testimonial(
    testimonial_id: int,
    payload: dict[str, Any],
    db: Session = Depends(get_db),
    _: models.User = Depends(require_active_user),
):
    rows = _load_json_list(db, TESTIMONIALS_KEY)
    target = None
    for item in rows:
        if item.get("id") == testimonial_id:
            target = item
            break
    if not target:
        raise HTTPException(status_code=404, detail="testimonial not found")

    for key in ["content", "emotion", "is_approved", "show_on_home"]:
        if key in payload:
            target[key] = payload[key]

    _save_json_list(db, TESTIMONIALS_KEY, rows)
    return target


@router.get("/cms/announcements")
def list_cms_announcements(db: Session = Depends(get_db)):
    rows = _load_json_list(db, ANNOUNCEMENTS_KEY)
    rows.sort(key=lambda item: item.get("created_at", ""), reverse=True)
    return rows


@router.post("/cms/announcements", status_code=201)
def create_cms_announcement(
    payload: dict[str, Any],
    db: Session = Depends(get_db),
    _: models.User = Depends(require_active_user),
):
    rows = _load_json_list(db, ANNOUNCEMENTS_KEY)
    title = str(payload.get("title") or "").strip()
    content = str(payload.get("content") or "").strip()
    if not title or not content:
        raise HTTPException(status_code=400, detail="title and content are required")

    item = {
        "id": _next_numeric_id(rows),
        "title": title,
        "content": content,
        "category": str(payload.get("category") or "General"),
        "is_active": bool(payload.get("is_active", True)),
        "created_at": _now_iso(),
    }
    rows.append(item)
    _save_json_list(db, ANNOUNCEMENTS_KEY, rows)
    return item


@router.get("/announcements")
def list_announcements_alias(db: Session = Depends(get_db)):
    rows = list_cms_announcements(db)
    return [item for item in rows if item.get("is_active", True)]


@router.get("/admin/announcements")
def list_admin_announcements(
    db: Session = Depends(get_db),
    _: models.User = Depends(require_active_user),
):
    return list_cms_announcements(db)


@router.get("/cms/media", response_model=list[schemas.CmsMediaRead])
def list_cms_media(
    query: str | None = Query(default=None),
    section: str | None = Query(default=None),
    limit: int = Query(default=250, ge=1, le=500),
    db: Session = Depends(get_db),
    _: models.User = Depends(require_active_user),
):
    return crud.list_cms_media_items(db, query=query, section=section, limit=limit)


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
    )


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
    section: str = Query(default="general"),
    alt_text: str = Query(default=""),
    tags: str = Query(default=""),
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
        alt_text=alt_text or None,
        section=section,
        tags=parsed_tags,
        created_by=current_user.id,
    )


@router.get("/cms/metrics", response_model=schemas.CmsMetrics)
def get_cms_metrics(
    db: Session = Depends(get_db),
    _: models.User = Depends(require_active_user),
):
    publications = crud.list_content_publications(db)
    status_counter = {"draft": 0, "in_review": 0, "approved": 0, "published": 0, "archived": 0}
    for item in publications:
        status_counter[item.status] = status_counter.get(item.status, 0) + 1

    testimonials = _load_json_list(db, TESTIMONIALS_KEY)
    announcements = _load_json_list(db, ANNOUNCEMENTS_KEY)

    return schemas.CmsMetrics(
        total_blocks=len(crud.list_page_contents(db, limit=500)),
        draft_blocks=status_counter.get("draft", 0),
        in_review_blocks=status_counter.get("in_review", 0),
        approved_blocks=status_counter.get("approved", 0),
        published_blocks=status_counter.get("published", 0),
        archived_blocks=status_counter.get("archived", 0),
        testimonials_total=len(testimonials),
        testimonials_approved=sum(1 for row in testimonials if row.get("is_approved")),
        announcements_total=len(announcements),
        announcements_active=sum(1 for row in announcements if row.get("is_active", True)),
    )
