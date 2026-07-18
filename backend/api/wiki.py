"""Wiki API — standalone knowledge-base documents.

Documents are keyed by ``page_key`` (e.g. ``wiki_intro``) and scoped by
the user's sede for multi-tenant isolation. Every PATCH snapshots the
previous version for history.
"""
from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import List, Optional
from uuid import UUID, uuid5, NAMESPACE_URL

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend import models
from backend.core.database import get_db
from backend.core.permissions import require_module_access, get_current_active_user
from backend.crud.crm import get_user_sede_id
from backend.crud import wiki as crud_wiki
from backend.schemas.wiki import WikiPageCreate, WikiPageRead, WikiPageUpdate, WikiPageVersionRead

router = APIRouter(prefix="/wiki", tags=["wiki"])


def _slugify(value: str) -> str:
    """Duplicate of api.cms_v2._slugify — TODO: extract to shared util."""
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


def _resolve_sede(db: Session, current_user) -> UUID | None:
    """Resolve the user's sede ID (None for cross-sede roles)."""
    result = get_user_sede_id(db, current_user.id)
    return UUID(result) if result else None


def _resolve_persona(db: Session, current_user) -> UUID | None:
    """Resolve the user's persona ID for author tracking."""
    from backend.crud.crm import resolve_persona_id_for_user
    return resolve_persona_id_for_user(db, current_user.id)


def _build_virtual_wiki_page(page_key: str, sede_id: UUID | None) -> WikiPageRead:
    """Return an empty virtual wiki page for collaborative surfaces.

    CRM and similar modules mount shared notes lazily. Returning an empty
    document keeps the contract stable without requiring pre-seeded rows.
    """
    now = datetime.now(timezone.utc)
    scope = str(sede_id) if sede_id else "global"
    return WikiPageRead(
        id=uuid5(NAMESPACE_URL, f"wiki:{scope}:{page_key}"),
        page_key=page_key,
        title=page_key.replace("wiki_", "").replace("-", " ").replace("_", " ").title(),
        content="",
        version=0,
        category=None,
        tags=[],
        sede_id=sede_id,
        author_id=None,
        created_at=now,
        updated_at=now,
    )


@router.get("/pages", response_model=List[WikiPageRead])
def list_wiki_pages(
    search: Optional[str] = Query(None, description="Filtrar por título o page_key"),
    category: Optional[str] = Query(None, description="Filtrar por categoría"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0, description="Desplazamiento para paginación"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
    _: models.User = Depends(require_module_access("wiki", "read")),
):
    """List active wiki pages for the current sede, with pagination support."""
    sede_id = _resolve_sede(db, current_user)
    return crud_wiki.list_wiki_pages(db, sede_id, search=search, category=category, limit=limit, offset=offset)


@router.get("/pages/count", response_model=dict)
def count_wiki_pages(
    search: Optional[str] = Query(None, description="Filtrar por título o page_key"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
    _: models.User = Depends(require_module_access("wiki", "read")),
):
    """Count of active wiki pages for pagination metadata."""
    sede_id = _resolve_sede(db, current_user)
    total = crud_wiki.count_wiki_pages(db, sede_id, search=search)
    return {"total": total}


@router.get("/pages/{page_key}", response_model=WikiPageRead)
def get_wiki_page(
    page_key: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
    _: models.User = Depends(require_module_access("wiki", "read")),
):
    """Get a single wiki page by key.

    Missing collaborative notes return an empty virtual document so module
    surfaces can bootstrap shared wiki content without API runtime failures.
    """
    key = _normalize_page_key(page_key)
    sede_id = _resolve_sede(db, current_user)
    row = crud_wiki.get_wiki_page(db, key, sede_id)
    if not row:
        # Si la página existe pero está soft-deleted, retornar 404
        deleted = crud_wiki.get_wiki_page_including_deleted(db, key, sede_id)
        if deleted:
            raise HTTPException(status_code=404, detail="wiki page not found (deleted)")
        return _build_virtual_wiki_page(key, sede_id)
    return row


@router.get("/pages/{page_key}/versions", response_model=List[WikiPageVersionRead])
def list_wiki_page_versions(
    page_key: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
    _: models.User = Depends(require_module_access("wiki", "read")),
):
    """List all versions of a wiki page."""
    key = _normalize_page_key(page_key)
    sede_id = _resolve_sede(db, current_user)
    row = crud_wiki.get_wiki_page(db, key, sede_id)
    if not row:
        raise HTTPException(status_code=404, detail="wiki page not found")
    return crud_wiki.list_wiki_page_versions(db, row.id)


@router.post("/pages/{page_key}", response_model=WikiPageRead, status_code=status.HTTP_201_CREATED)
def create_wiki_page(
    page_key: str,
    data: WikiPageCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
    _: models.User = Depends(require_module_access("wiki", "edit")),
):
    """Create a new wiki page. Returns 409 if a page with the same key already exists."""
    key = _normalize_page_key(page_key)
    sede_id = _resolve_sede(db, current_user)

    existing = crud_wiki.get_wiki_page(db, key, sede_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"wiki page '{key}' already exists for this sede",
        )

    persona_id = _resolve_persona(db, current_user)
    try:
        return crud_wiki.create_wiki_page(
            db,
            page_key=key,
            title=data.title or key.replace("wiki_", "").replace("-", " ").title(),
            content=data.content or "",
            sede_id=sede_id,
            author_id=persona_id,
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"wiki page '{key}' already exists for this sede",
        )


@router.patch("/pages/{page_key}", response_model=WikiPageRead)
def patch_wiki_page(
    page_key: str,
    data: WikiPageUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
    _: models.User = Depends(require_module_access("wiki", "edit")),
):
    """Partially update a wiki page (title and/or content). Snapshots previous version."""
    key = _normalize_page_key(page_key)
    sede_id = _resolve_sede(db, current_user)
    row = crud_wiki.get_wiki_page(db, key, sede_id)
    if not row:
        raise HTTPException(status_code=404, detail="wiki page not found")
    persona_id = _resolve_persona(db, current_user)
    return crud_wiki.update_wiki_page(
        db, row, title=data.title, content=data.content,
        category=data.category, tags=data.tags, author_id=persona_id
    )


@router.get("/categories", response_model=List[str])
def list_wiki_categories(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
    _: models.User = Depends(require_module_access("wiki", "read")),
):
    """List distinct categories used by wiki pages in the current sede."""
    sede_id = _resolve_sede(db, current_user)
    return crud_wiki.list_wiki_categories(db, sede_id)


@router.delete("/pages/{page_key}", status_code=status.HTTP_204_NO_CONTENT)
def delete_wiki_page(
    page_key: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
    _: models.User = Depends(require_module_access("wiki", "edit")),
):
    """Soft-delete a wiki page."""
    key = _normalize_page_key(page_key)
    sede_id = _resolve_sede(db, current_user)
    row = crud_wiki.get_wiki_page(db, key, sede_id)
    if not row:
        raise HTTPException(status_code=404, detail="wiki page not found")
    crud_wiki.soft_delete_wiki_page(db, row)
    return None
