"""CRUD for standalone wiki pages (WikiPage model)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from backend import models


def list_wiki_pages(
    db: Session,
    sede_id: UUID | None,
    search: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[models.WikiPage]:
    """List active wiki pages for a sede, ordered by most recently updated."""
    query = db.query(models.WikiPage).filter(
        models.WikiPage.deleted_at.is_(None),
        models.WikiPage.sede_id == sede_id,
    )
    if search:
        term = f"%{search.strip()}%"
        query = query.filter(
            models.WikiPage.title.ilike(term) | models.WikiPage.page_key.ilike(term)
        )
    if category:
        query = query.filter(models.WikiPage.category == category)
    return query.order_by(models.WikiPage.updated_at.desc()).offset(offset).limit(limit).all()


def count_wiki_pages(
    db: Session,
    sede_id: UUID | None,
    search: Optional[str] = None,
) -> int:
    """Count active wiki pages for a sede (used for pagination metadata)."""
    query = db.query(models.WikiPage).filter(
        models.WikiPage.deleted_at.is_(None),
        models.WikiPage.sede_id == sede_id,
    )
    if search:
        term = f"%{search.strip()}%"
        query = query.filter(
            models.WikiPage.title.ilike(term) | models.WikiPage.page_key.ilike(term)
        )
    return query.count()


def get_wiki_page(
    db: Session, page_key: str, sede_id: UUID | None
) -> models.WikiPage | None:
    """Get a single active (not deleted) wiki page by key and sede."""
    return (
        db.query(models.WikiPage)
        .filter(
            models.WikiPage.page_key == page_key,
            models.WikiPage.sede_id == sede_id,
            models.WikiPage.deleted_at.is_(None),
        )
        .first()
    )


def get_wiki_page_including_deleted(
    db: Session, page_key: str, sede_id: UUID | None
) -> models.WikiPage | None:
    """Get a wiki page by key and sede, including soft-deleted ones."""
    return (
        db.query(models.WikiPage)
        .filter(
            models.WikiPage.page_key == page_key,
            models.WikiPage.sede_id == sede_id,
        )
        .first()
   )


def create_wiki_page(
    db: Session,
    page_key: str,
    title: str,
    content: str,
    sede_id: UUID | None,
    author_id: UUID | None = None,
) -> models.WikiPage:
    """Create a new wiki page with version 1."""
    row = models.WikiPage(
        page_key=page_key,
        title=title,
        content=content,
        version=1,
        sede_id=sede_id,
        author_id=author_id,
    )
    db.add(row)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise ValueError(f"page_key '{page_key}' already exists for this sede")
    db.refresh(row)
    return row


def _create_version_snapshot(
    db: Session, wiki_page: models.WikiPage, author_id: UUID | None
) -> None:
    """Snapshot the current state of a wiki page into its version history."""
    version = models.WikiPageVersion(
        wiki_page_id=wiki_page.id,
        version_number=wiki_page.version,
        title=wiki_page.title,
        content=wiki_page.content,
        created_by_persona_id=author_id,
    )
    db.add(version)


def update_wiki_page(
    db: Session,
    row: models.WikiPage,
    title: str | None = None,
    content: str | None = None,
    category: str | None = None,
    tags: list[str] | None = None,
    author_id: UUID | None = None,
) -> models.WikiPage:
    """Partially update an existing wiki page. Snapshots version before change."""
    # Snapshot current state before modifying
    _create_version_snapshot(db, row, author_id)
    if title is not None:
        row.title = title
    if content is not None:
        row.content = content
    if category is not None:
        row.category = category if category else None
    if tags is not None:
        row.tags = tags
    row.version = (row.version or 1) + 1
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return row


def list_wiki_categories(
    db: Session,
    sede_id: UUID | None,
) -> list[str]:
    """List distinct non-null categories used by wiki pages in a sede."""
    results = (
        db.query(models.WikiPage.category)
        .filter(
            models.WikiPage.deleted_at.is_(None),
            models.WikiPage.sede_id == sede_id,
            models.WikiPage.category.isnot(None),
        )
        .distinct()
        .order_by(models.WikiPage.category)
        .all()
    )
    return [r[0] for r in results if r[0]]


def soft_delete_wiki_page(db: Session, row: models.WikiPage) -> None:
    """Soft-delete a wiki page."""
    row.deleted_at = datetime.now(timezone.utc)
    db.commit()


def list_wiki_page_versions(
    db: Session, wiki_page_id: UUID
) -> List[models.WikiPageVersion]:
    """List all versions for a wiki page, newest first."""
    return (
        db.query(models.WikiPageVersion)
        .filter(models.WikiPageVersion.wiki_page_id == wiki_page_id)
        .order_by(models.WikiPageVersion.version_number.desc())
        .all()
    )
