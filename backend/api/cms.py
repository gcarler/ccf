from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend import crud, models, schemas
from backend.auth import require_active_user
from backend.core.database import get_db


router = APIRouter(tags=["cms"])

TESTIMONIALS_KEY = "faro_testimonials_feed"
ANNOUNCEMENTS_KEY = "faro_announcements_feed"


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
