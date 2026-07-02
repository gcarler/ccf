"""Wiki API — standalone knowledge-base documents.

Replaces the retired ``/cms/content`` storage used by the platform wiki.
Documents are keyed by ``page_key`` (e.g. ``wiki_intro``) and are editable by
users with CMS read/write access.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend import models
from backend.core.database import get_db
from backend.core.permissions import require_module_access
from backend.schemas.wiki import WikiPageCreate, WikiPageRead, WikiPageUpdate

router = APIRouter(prefix="/wiki", tags=["wiki"])


def _slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"\s+", "-", value)
    value = re.sub(r"[^a-z0-9_-]", "", value)
    return value.strip("-")


def _normalize_page_key(value: str) -> str:
    """Ensure wiki page keys always start with the ``wiki_`` prefix."""
    key = _slugify(value)
    if not key.startswith("wiki_"):
        key = f"wiki_{key}"
    return key


@router.get("/pages", response_model=List[WikiPageRead])
def list_wiki_pages(
    search: Optional[str] = Query(None, description="Filtrar por título o page_key"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: models.User = Depends(require_module_access("cms", "read")),
):
    """List active wiki pages ordered by most recently updated."""
    query = db.query(models.WikiPage).filter(models.WikiPage.deleted_at.is_(None))
    if search:
        term = f"%{search.strip()}%"
        query = query.filter(
            (models.WikiPage.title.ilike(term)) | (models.WikiPage.page_key.ilike(term))
        )
    return query.order_by(models.WikiPage.updated_at.desc()).limit(limit).all()


@router.get("/pages/{page_key}", response_model=WikiPageRead)
def get_wiki_page(
    page_key: str,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_module_access("cms", "read")),
):
    """Get a single wiki page by key, creating an empty skeleton if missing."""
    key = _normalize_page_key(page_key)
    row = (
        db.query(models.WikiPage)
        .filter(models.WikiPage.page_key == key, models.WikiPage.deleted_at.is_(None))
        .first()
    )
    if not row:
        title = key.replace("wiki_", "").replace("-", " ").title() or "Wiki"
        row = models.WikiPage(page_key=key, title=title, content="")
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


@router.post("/pages/{page_key}", response_model=WikiPageRead, status_code=status.HTTP_201_CREATED)
def upsert_wiki_page(
    page_key: str,
    data: WikiPageCreate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_module_access("cms", "edit")),
):
    """Create or fully replace a wiki page."""
    key = _normalize_page_key(page_key)
    row = (
        db.query(models.WikiPage)
        .filter(models.WikiPage.page_key == key, models.WikiPage.deleted_at.is_(None))
        .first()
    )
    if row:
        row.title = data.title or row.title
        row.content = data.content if data.content is not None else row.content
        row.updated_at = datetime.now(timezone.utc)
    else:
        row = models.WikiPage(
            page_key=key,
            title=data.title or key.replace("wiki_", "").replace("-", " ").title(),
            content=data.content or "",
        )
        db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.patch("/pages/{page_key}", response_model=WikiPageRead)
def patch_wiki_page(
    page_key: str,
    data: WikiPageUpdate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_module_access("cms", "edit")),
):
    """Partially update a wiki page (title and/or content)."""
    key = _normalize_page_key(page_key)
    row = (
        db.query(models.WikiPage)
        .filter(models.WikiPage.page_key == key, models.WikiPage.deleted_at.is_(None))
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="wiki page not found")
    if data.title is not None:
        row.title = data.title
    if data.content is not None:
        row.content = data.content
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/pages/{page_key}", status_code=status.HTTP_204_NO_CONTENT)
def delete_wiki_page(
    page_key: str,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_module_access("cms", "edit")),
):
    """Soft-delete a wiki page."""
    key = _normalize_page_key(page_key)
    row = (
        db.query(models.WikiPage)
        .filter(models.WikiPage.page_key == key, models.WikiPage.deleted_at.is_(None))
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="wiki page not found")
    row.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return None
