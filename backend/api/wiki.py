"""Wiki API — standalone knowledge-base documents.

Documents are keyed by ``page_key`` (e.g. ``wiki_intro``) and scoped by
the user's sede for multi-tenant isolation. Every PATCH snapshots the
previous version for history.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import List, Optional
from uuid import NAMESPACE_URL, UUID, uuid5

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend import models
from backend.core.database import get_db
from backend.core.permissions import get_current_active_user, require_module_access
from backend.crud import wiki as crud_wiki
from backend.crud._utils import _slugify
from backend.crud.crm import get_user_sede_id
from backend.schemas.wiki import (
    WikiGraphData,
    WikiGraphLink,
    WikiGraphNode,
    WikiPageCreate,
    WikiPageRead,
    WikiPageUpdate,
    WikiPageVersionRead,
)

router = APIRouter(prefix="/wiki", tags=["wiki"])



def _normalize_page_key(value: str) -> str:
    """Ensure wiki keys have one prefix while preserving canonical underscores.

    ``_slugify`` is shared with URL-like CMS values and intentionally turns
    underscores into dashes. Wiki ``page_key`` is a stable identifier,
    however, so keys such as ``wiki_my_doc`` must remain unchanged and an
    already-prefixed key must not become ``wiki_wiki-*``.
    """
    raw = str(value or "").strip().lower()
    while raw.startswith(("wiki_", "wiki-")):
        raw = raw[5:]
    body = "_".join(_slugify(part) for part in raw.split("_"))
    body = body.strip("_")
    key = f"wiki_{body}" if body else "wiki_page"
    return key


def _page_key_candidates(value: str) -> list[str]:
    """Return canonical and backward-compatible keys without broadening the lookup scope.

    Older deployments generated keys such as ``wiki-my-doc`` while the
    current contract stores ``wiki_my_doc``. Keep the canonical key first so
    a newly-created page always wins, then try only the exact compat alias.
    The caller still supplies the user's ``sede_id`` to every database lookup.
    """
    raw = str(value or "").strip().lower()
    canonical = _normalize_page_key(raw)
    candidates = [canonical]
    if raw.startswith("wiki-") and raw not in candidates:
        candidates.append(raw)
    if canonical.startswith("wiki_"):
        compat_key = "wiki-" + canonical[5:].replace("_", "-")
        if compat_key not in candidates:
            candidates.append(compat_key)
    return candidates


def _get_compatible_page(db: Session, page_key: str, sede_id: UUID | None):
    """Find a current or backward-compatible page key, always constrained to one sede."""
    for candidate in _page_key_candidates(page_key):
        row = crud_wiki.get_wiki_page(db, candidate, sede_id)
        if row:
            return row
    return None


def _get_compatible_page_including_deleted(db: Session, page_key: str, sede_id: UUID | None):
    """Find a current or backward-compatible page including soft-deleted rows."""
    for candidate in _page_key_candidates(page_key):
        row = crud_wiki.get_wiki_page_including_deleted(db, candidate, sede_id)
        if row:
            return row
    return None


def _resolve_sede(db: Session, current_user) -> UUID | None:
    """Resolve the user's sede ID (None for cross-sede roles).

    ``get_user_sede_id`` (reexportado vía ``backend.crud.crm``) retorna
    ``uuid.UUID | None`` desde el fix M-01 (2026-07-25) — antes devolvía ``str``.
    Idempotente: si el upstream cambia de vuelta a ``str`` o sigue retornando
    ``UUID``, este helper sigue funcionando sin re-wrap incorrecto.
    """
    result = get_user_sede_id(db, current_user.id)
    if result is None:
        return None
    return result if isinstance(result, UUID) else UUID(str(result))


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
    row = _get_compatible_page(db, page_key, sede_id)
    if not row:
        # Si la página existe pero está soft-deleted, retornar 404
        deleted = _get_compatible_page_including_deleted(db, page_key, sede_id)
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
    sede_id = _resolve_sede(db, current_user)
    row = _get_compatible_page(db, page_key, sede_id)
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

    existing = _get_compatible_page(db, page_key, sede_id)
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
    except ValueError:  # pragma: no cover
        raise HTTPException(  # pragma: no cover
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
    sede_id = _resolve_sede(db, current_user)
    row = _get_compatible_page(db, page_key, sede_id)
    if not row:
        raise HTTPException(status_code=404, detail="wiki page not found")
    persona_id = _resolve_persona(db, current_user)
    return crud_wiki.update_wiki_page(
        db, row, title=data.title, content=data.content, category=data.category, tags=data.tags, author_id=persona_id
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
    sede_id = _resolve_sede(db, current_user)
    row = _get_compatible_page(db, page_key, sede_id)
    if not row:
        raise HTTPException(status_code=404, detail="wiki page not found")
    crud_wiki.soft_delete_wiki_page(db, row)
    return None


@router.get("/graph-data", response_model=WikiGraphData)
def get_wiki_graph_data(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
    _: models.User = Depends(require_module_access("wiki", "read")),
):
    """Returns knowledge graph nodes and bidirectional links extracted from wiki documents."""
    sede_id = _resolve_sede(db, current_user)
    pages = crud_wiki.list_wiki_pages(db, sede_id, limit=1000)

    # Index by page_key and normalized title
    key_map = {}
    title_map = {}
    for p in pages:
        key_map[p.page_key] = p
        normalized_key = _normalize_page_key(p.page_key)
        key_map[normalized_key] = p
        if p.title:
            title_map[p.title.strip().lower()] = p.page_key

    nodes_dict = {
        p.page_key: WikiGraphNode(
            id=p.page_key,
            title=p.title,
            category=p.category or "General",
            links_count=0,
        )
        for p in pages
    }

    links_set = set()
    links_list: list[WikiGraphLink] = []

    wiki_link_bracket_pattern = re.compile(r"\[\[(.*?)\]\]")
    wiki_link_tag_pattern = re.compile(r'data-page-key=["\']([^"\']+)["\']')
    wiki_link_href_pattern = re.compile(r'href=["\'][^"\']*/wiki/docs/([^"\'#?]+)["\']')

    for page in pages:
        src = page.page_key
        content = page.content or ""
        targets_found = set()

        # 1. Bracket syntax [[Target]] or [[key|label]]
        for match in wiki_link_bracket_pattern.findall(content):
            target_str = match.split("|")[0].strip()
            norm_key = _normalize_page_key(target_str)
            if norm_key in key_map:
                targets_found.add(key_map[norm_key].page_key)
            elif target_str.lower() in title_map:
                targets_found.add(title_map[target_str.lower()])
            elif target_str in key_map:
                targets_found.add(key_map[target_str].page_key)

        # 2. Tag data-page-key="..."
        for match in wiki_link_tag_pattern.findall(content):
            target_str = match.strip()
            norm_key = _normalize_page_key(target_str)
            if norm_key in key_map:
                targets_found.add(key_map[norm_key].page_key)
            elif target_str in key_map:
                targets_found.add(key_map[target_str].page_key)

        # 3. Href links
        for match in wiki_link_href_pattern.findall(content):
            target_str = match.strip()
            norm_key = _normalize_page_key(target_str)
            if norm_key in key_map:
                targets_found.add(key_map[norm_key].page_key)
            elif target_str in key_map:
                targets_found.add(key_map[target_str].page_key)

        for tgt in targets_found:
            if tgt != src:
                link_key = (src, tgt)
                if link_key not in links_set:
                    links_set.add(link_key)
                    links_list.append(WikiGraphLink(source=src, target=tgt))
                    if src in nodes_dict:
                        nodes_dict[src].links_count += 1
                    if tgt in nodes_dict:
                        nodes_dict[tgt].links_count += 1

    return WikiGraphData(nodes=list(nodes_dict.values()), links=links_list)

