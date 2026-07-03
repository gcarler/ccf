from __future__ import annotations

import logging
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from backend import crud, models, schemas
from backend.api._cms_helpers import (
    _get_scoped_cms_media,
    _get_scoped_persona,
    _scope_cms_pastoral_team_by_user_sede,
)
from backend.core.cache_v2 import cached_public
from backend.core.database import get_db
from backend.core.permissions import normalize_role, require_module_access
from backend.models_shared import _utcnow
from backend.schemas._common import PaginatedResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cms/v2", tags=["cms_v2"])

from backend.core.rate_limit import rate_limiter

from sqlalchemy.orm import Session
from backend import models as cms_models

# ── Section Types (platform-wide catalog admin endpoints) ─────────────────
#
# Counterpart to ``get_allowed_section_types`` above: what the CMS does
# at runtime when an editor builds a page, vs. what the API exposes for
# managing the catalog that backs those decisions.


def _get_section_type_or_404(db: Session, name: str) -> models.CmsSectionType:
    """Look up by name (the public identifier) or raise 404."""
    row = (
        db.query(models.CmsSectionType)
        .filter(models.CmsSectionType.name == name.strip().lower())
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="section type not found")
    return row


@router.get(
    "/section-types",
    response_model=list[schemas.CmsSectionTypeRead],
)
def list_section_types(
    only_active: bool = Query(default=False),
    db: Session = Depends(get_db),
    _: models.User = Depends(require_module_access("cms", "read")),
):
    """List every platform-wide section type.

    Section types are global (no site FK), so the endpoint is mounted
    on the global CMS router. Use ``?only_active=true`` to mirror
    ``get_allowed_section_types()`` semantics — the runtime guard
    consulted by ``create_section``.
    """
    query = db.query(models.CmsSectionType).order_by(models.CmsSectionType.name)
    if only_active:
        query = query.filter(models.CmsSectionType.is_active.is_(True))
    return query.all()


@router.get(
    "/section-types/{name}",
    response_model=schemas.CmsSectionTypeRead,
)
def get_section_type(
    name: str,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_module_access("cms", "read")),
):
    return _get_section_type_or_404(db, name)


@router.post(
    "/section-types",
    response_model=schemas.CmsSectionTypeRead,
    status_code=201,
)
def create_section_type(
    payload: schemas.CmsSectionTypeCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    """Register a new section type. Required role: CMS publisher."""
    _assert_role(current_user, CMS_PUBLISHER_ROLES)
    name = payload.name.strip().lower()
    if not name:
        raise HTTPException(status_code=422, detail="name is required")
    if (
        db.query(models.CmsSectionType)
        .filter(models.CmsSectionType.name == name)
        .first()
    ):
        raise HTTPException(status_code=409, detail="section type already exists")
    row = models.CmsSectionType(
        name=name,
        description=payload.description,
        is_active=payload.is_active,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.patch(
    "/section-types/{name}",
    response_model=schemas.CmsSectionTypeRead,
)
def patch_section_type(
    name: str,
    payload: schemas.CmsSectionTypeUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    """Partially update a section type. ``name`` is immutable by design."""
    _assert_role(current_user, CMS_PUBLISHER_ROLES)
    row = _get_section_type_or_404(db, name)
    # ``CmsSectionTypeUpdate`` excludes ``name`` to protect dangling
    # ``CmsSection.type`` refs (free-string, no FK cascade).
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/section-types/{name}", status_code=204)
def delete_section_type(
    name: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    """Soft-delete a section type by flipping ``is_active=False``.

    Hard-deletes are intentionally disallowed. ``CmsSection.type`` is a
    free-string column, so a hard delete would silently orphan every
    existing section that uses the type. Soft-delete keeps the catalog
    row for audit and aligns with the seed-script policy in
    ``scripts/seed_cms_section_types.py`` (``apply_section_types``
    preserves admin deactivations on re-seed).
    """
    _assert_role(current_user, CMS_PUBLISHER_ROLES)
    row = _get_section_type_or_404(db, name)
    row.is_active = False
    db.commit()
    return None


def get_allowed_section_types(db: Session) -> set[str]:
    """Return set of active section type names from DB, fallback to hardcoded."""
    try:
        rows = db.query(cms_models.CmsSectionType.name).filter(cms_models.CmsSectionType.is_active == True).all()
        types = {row[0] for row in rows}
        if types:
            return types
    except Exception:
        # If table missing or any error, fall back
        pass
    # Fallback hardcoded list (same as previous ALLOWED_SECTION_TYPES)
    return {
        "hero",
        "video_hero",
        "rich_text",
        "rich_text_columns",
        "cards",
        "cta_banner",
        "gallery",
        "faq",
        "embed",
        "testimonials",
        "stats",
        "team",
        "countdown",
        "pricing",
        "image_text",
        "timeline",
        "icon_grid",
        "newsletter",
        "popup_banner",
        "button",
        "toc",
        "divider",
        "collapsible",
        "social_links",
        "spacer",
        "calendar",
        "map",
        "document_upload",
        "content_blocks",
        "accordion",
    }
CMS_EDITOR_ROLES = {"admin", "coordinador", "docente", "pastor"}
CMS_PUBLISHER_ROLES = {"admin", "coordinador", "pastor"}


def _assert_role(
    user: models.User, allowed_roles: set[str], detail: str = "Not enough permissions"
) -> None:
    """Validate that the user belongs to one of the allowed role groups.

    Args:
        user: Authenticated ``User`` model instance.
        allowed_roles: Set of role names (lower‑cased) permitted to perform the action.
        detail: Custom error detail returned in the 403 response.
    """
    # Preserve backward‑compatible behaviour for V3 personas where the role is stored
    # in ``rol_plataforma.nombre``. ``normalize_role`` handles case‑insensitivity and
    # whitespace trimming.
    role = normalize_role(getattr(user, "role", ""))
    if not role and hasattr(user, "rol_plataforma") and user.rol_plataforma:
        role = normalize_role(user.rol_plataforma.nombre)
    if role not in allowed_roles:
        raise HTTPException(status_code=403, detail=detail)


def _slugify(value: str) -> str:
    """Normalize a string into a URL‑safe slug.

    - Trims whitespace, lower‑cases, replaces internal whitespace with hyphens.
    - Removes characters that are not alphanumeric, hyphen, underscore or slash.
    - Strips leading/trailing hyphens.
    """
    value = value.strip().lower()
    value = re.sub(r"\s+", "-", value)
    value = re.sub(r"[^a-z0-9\-_/]", "", value)
    return value.strip("-")


def _get_site_or_404(db: Session, site_key: str) -> models.CmsSite:
    """Retrieve a CMS site by its key or raise a 404 error.

    Args:
        db: SQLAlchemy session.
        site_key: Identifier of the site (case‑insensitive).
    """
    row = crud.get_cms_site_by_key(db, site_key.strip().lower())
    if not row:
        raise HTTPException(status_code=404, detail="site not found")
    return row


def _get_public_site_or_404(db: Session, site_key: str) -> models.CmsSite:
    """Fetch a public‑active CMS site or raise 404.

    Ensures the site exists and ``is_active`` flag is true.
    """
    row = _get_site_or_404(db, site_key)
    if not row.is_active:
        raise HTTPException(status_code=404, detail="site not found")
    return row


def _get_menu_or_404(db: Session, site_id: UUID, menu_key: str) -> models.CmsMenu:
    """Retrieve a CMS menu by its key for a given site or raise 404.

    Args:
        db: Database session.
        site_id: UUID of the site.
        menu_key: Key of the menu (case‑insensitive).
    """
    row = crud.get_cms_menu(db, site_id, menu_key.strip().lower())
    if not row:
        raise HTTPException(status_code=404, detail="menu not found")
    return row


def _get_page_or_404(db: Session, site_id: UUID, slug: str) -> models.CmsPage:
    row = crud.get_cms_page(db, site_id, _slugify(slug))
    if not row:
        raise HTTPException(status_code=404, detail="page not found")
    return row


def _snapshot_section_read(
    section_data: dict[str, Any],
    *,
    page_id: uuid.UUID,
    index: int,
    timestamp: datetime,
) -> schemas.CmsSectionRead:
    section_id = section_data.get("id")
    sort_order = section_data.get("sort_order")
    props_json = section_data.get("props_json")

    import uuid as py_uuid
    valid_id = None
    if section_id:
        if isinstance(section_id, py_uuid.UUID):
            valid_id = section_id
        else:
            try:
                valid_id = py_uuid.UUID(str(section_id))
            except (ValueError, AttributeError):
                pass
    if not valid_id:
        valid_id = py_uuid.uuid5(py_uuid.NAMESPACE_DNS, f"section-fallback-{page_id}-{index}")

    return schemas.CmsSectionRead(
        id=valid_id,
        page_id=page_id,
        section_key=str(section_data.get("section_key") or f"published-{index + 1}"),
        type=str(section_data.get("type") or "rich_text"),
        props_json=props_json if isinstance(props_json, dict) else {},
        sort_order=sort_order if isinstance(sort_order, int) else index,
        is_visible=section_data.get("is_visible", True) is not False,
        status=str(section_data.get("status") or "active"),
        created_at=timestamp,
        updated_at=timestamp,
    )


@router.get("/sites", response_model=list[schemas.CmsSiteRead])
def list_sites(
    only_active: bool = Query(default=False),
    db: Session = Depends(get_db),
    _: models.User = Depends(require_module_access("cms", "read")),
):
    return crud.list_cms_sites(db, only_active=only_active)


@router.post("/sites", response_model=schemas.CmsSiteRead, status_code=201)
def create_site(
    payload: schemas.CmsSiteCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    _assert_role(current_user, CMS_PUBLISHER_ROLES)
    if not payload.site_key.strip():
        raise HTTPException(status_code=422, detail="site_key is required")
    if not payload.base_path.strip().startswith("/"):
        raise HTTPException(status_code=422, detail="base_path must start with '/'")
    if crud.get_cms_site_by_key(db, payload.site_key.strip().lower()):
        raise HTTPException(status_code=409, detail="site_key already exists")
    return crud.create_cms_site(db, payload)


@router.get("/sites/{site_key}", response_model=schemas.CmsSiteRead)
def get_site(
    site_key: str,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_module_access("cms", "read")),
):
    return _get_site_or_404(db, site_key)


@router.patch("/sites/{site_key}", response_model=schemas.CmsSiteRead)
def patch_site(
    site_key: str,
    payload: schemas.CmsSiteUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    _assert_role(current_user, CMS_PUBLISHER_ROLES)
    row = _get_site_or_404(db, site_key)
    return crud.update_cms_site(db, row, payload)


@router.delete("/sites/{site_key}", status_code=204)
def delete_site(
    site_key: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    """Desactiva un sitio CMS sin eliminar su contenido."""
    _assert_role(current_user, CMS_PUBLISHER_ROLES)
    row = _get_site_or_404(db, site_key)
    crud.archive_cms_site(db, row)
    return None


@router.get("/sites/{site_key}/themes", response_model=list[schemas.CmsThemeRead])
def list_themes(
    site_key: str,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_module_access("cms", "read")),
):
    site = _get_site_or_404(db, site_key)
    return crud.list_cms_themes(db, site.id)


@router.post(
    "/sites/{site_key}/themes", response_model=schemas.CmsThemeRead, status_code=201
)
def create_theme(
    site_key: str,
    payload: schemas.CmsThemeCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    if payload.is_active:
        _assert_role(
            current_user,
            CMS_PUBLISHER_ROLES,
            detail="Only publishers can activate a theme",
        )
    site = _get_site_or_404(db, site_key)
    return crud.create_cms_theme(db, site.id, payload, created_by=current_user.id)


@router.patch(
    "/sites/{site_key}/themes/{theme_id}", response_model=schemas.CmsThemeRead
)
def patch_theme(
    site_key: str,
    theme_id: uuid.UUID,
    payload: schemas.CmsThemeUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    if payload.is_active:
        _assert_role(
            current_user,
            CMS_PUBLISHER_ROLES,
            detail="Only publishers can activate a theme",
        )
    site = _get_site_or_404(db, site_key)
    row = crud.get_cms_theme(db, site.id, theme_id)
    if not row:
        raise HTTPException(status_code=404, detail="theme not found")
    return crud.update_cms_theme(db, row, payload)


@router.post(
    "/sites/{site_key}/themes/{theme_id}/activate", response_model=schemas.CmsThemeRead
)
def activate_theme(
    site_key: str,
    theme_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    _assert_role(current_user, CMS_PUBLISHER_ROLES)
    site = _get_site_or_404(db, site_key)
    row = crud.activate_cms_theme(db, site.id, theme_id)
    if not row:
        raise HTTPException(status_code=404, detail="theme not found")
    return row


@router.delete("/sites/{site_key}/themes/{theme_id}", status_code=204)
def delete_theme(
    site_key: str,
    theme_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    """Archiva un tema CMS sin eliminar su historial."""
    _assert_role(current_user, CMS_PUBLISHER_ROLES)
    site = _get_site_or_404(db, site_key)
    row = crud.get_cms_theme(db, site.id, theme_id)
    if not row:
        raise HTTPException(status_code=404, detail="theme not found")
    crud.archive_cms_theme(db, row)
    return None


@router.get("/sites/{site_key}/menus", response_model=list[schemas.CmsMenuRead])
def list_menus(
    site_key: str,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_module_access("cms", "read")),
):
    site = _get_site_or_404(db, site_key)
    return crud.list_cms_menus(db, site.id)


@router.post(
    "/sites/{site_key}/menus", response_model=schemas.CmsMenuRead, status_code=201
)
def create_menu(
    site_key: str,
    payload: schemas.CmsMenuCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_site_or_404(db, site_key)
    if crud.get_cms_menu(db, site.id, payload.menu_key.strip().lower()):
        raise HTTPException(status_code=409, detail="menu_key already exists")
    return crud.create_cms_menu(db, site.id, payload)


@router.get("/sites/{site_key}/menus/{menu_key}", response_model=schemas.CmsMenuRead)
def get_menu(
    site_key: str,
    menu_key: str,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_module_access("cms", "read")),
):
    site = _get_site_or_404(db, site_key)
    return _get_menu_or_404(db, site.id, menu_key)


@router.patch("/sites/{site_key}/menus/{menu_key}", response_model=schemas.CmsMenuRead)
def patch_menu(
    site_key: str,
    menu_key: str,
    payload: schemas.CmsMenuUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_site_or_404(db, site_key)
    row = _get_menu_or_404(db, site.id, menu_key)
    return crud.update_cms_menu(db, row, payload)


@router.delete("/sites/{site_key}/menus/{menu_key}", status_code=204)
def delete_menu(
    site_key: str,
    menu_key: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    """Desactiva un menu CMS sin eliminarlo."""
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_site_or_404(db, site_key)
    row = _get_menu_or_404(db, site.id, menu_key)
    crud.delete_cms_menu(db, row)


@router.get(
    "/sites/{site_key}/menus/{menu_key}/items",
    response_model=list[schemas.CmsMenuItemRead],
)
def list_menu_items(
    site_key: str,
    menu_key: str,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_module_access("cms", "read")),
):
    site = _get_site_or_404(db, site_key)
    menu = _get_menu_or_404(db, site.id, menu_key)
    return crud.list_cms_menu_items(db, menu.id)


@router.post(
    "/sites/{site_key}/menus/{menu_key}/items",
    response_model=schemas.CmsMenuItemRead,
    status_code=201,
)
def create_menu_item(
    site_key: str,
    menu_key: str,
    payload: schemas.CmsMenuItemCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_site_or_404(db, site_key)
    menu = _get_menu_or_404(db, site.id, menu_key)
    return crud.create_cms_menu_item(db, menu.id, payload)


@router.patch(
    "/sites/{site_key}/menus/{menu_key}/items/{item_id}",
    response_model=schemas.CmsMenuItemRead,
)
def patch_menu_item(
    site_key: str,
    menu_key: str,
    item_id: uuid.UUID,
    payload: schemas.CmsMenuItemUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_site_or_404(db, site_key)
    menu = _get_menu_or_404(db, site.id, menu_key)
    item = crud.get_cms_menu_item(db, menu.id, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="menu item not found")
    return crud.update_cms_menu_item(db, item, payload)


@router.delete("/sites/{site_key}/menus/{menu_key}/items/{item_id}", status_code=204)
def delete_menu_item(
    site_key: str,
    menu_key: str,
    item_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    """Oculta un item de menu sin eliminarlo."""
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_site_or_404(db, site_key)
    menu = _get_menu_or_404(db, site.id, menu_key)
    item = crud.get_cms_menu_item(db, menu.id, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="menu item not found")
    crud.delete_cms_menu_item(db, item)


@router.post(
    "/sites/{site_key}/menus/{menu_key}/reorder",
    response_model=list[schemas.CmsMenuItemRead],
)
def reorder_menu_items(
    site_key: str,
    menu_key: str,
    payload: schemas.CmsMenuItemReorderPayload,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_site_or_404(db, site_key)
    menu = _get_menu_or_404(db, site.id, menu_key)
    return crud.reorder_cms_menu_items(db, menu.id, payload.items)


@router.get(
    "/sites/{site_key}/pages",
    response_model=PaginatedResponse[schemas.CmsPageRead],
)
def list_pages(
    site_key: str,
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status: str | None = Query(None),
    _: models.User = Depends(require_module_access("cms", "read")),
):
    site = _get_site_or_404(db, site_key)
    pages, total = crud.list_cms_pages(db, site.id, skip=skip, limit=limit, status=status)
    return PaginatedResponse[schemas.CmsPageRead](
        items=pages, total=total, skip=skip, limit=limit
    )


@router.post(
    "/sites/{site_key}/pages", response_model=schemas.CmsPageRead, status_code=201
)
def create_page(
    site_key: str,
    payload: schemas.CmsPageCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    if payload.status.strip().lower() != "draft":
        raise HTTPException(status_code=422, detail="new pages must start in draft")
    site = _get_site_or_404(db, site_key)
    payload.slug = _slugify(payload.slug)
    if not payload.slug:
        raise HTTPException(status_code=422, detail="slug is required")
    if crud.get_cms_page(db, site.id, payload.slug):
        raise HTTPException(status_code=409, detail="slug already exists")
    return crud.create_cms_page(db, site.id, payload, current_user.id)


@router.get("/sites/{site_key}/pages/{slug}", response_model=schemas.CmsPageRead)
def get_page(
    site_key: str,
    slug: str,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_module_access("cms", "read")),
):
    site = _get_site_or_404(db, site_key)
    return _get_page_or_404(db, site.id, slug)


@router.patch("/sites/{site_key}/pages/{slug}", response_model=schemas.CmsPageRead)
def patch_page(
    site_key: str,
    slug: str,
    payload: schemas.CmsPageUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    if payload.status is not None:
        raise HTTPException(
            status_code=422, detail="use workflow endpoint to change status"
        )
    site = _get_site_or_404(db, site_key)
    row = _get_page_or_404(db, site.id, slug)
    return crud.update_cms_page(db, row, payload, current_user.id)


@router.delete("/sites/{site_key}/pages/{slug}", status_code=204)
def delete_page(
    site_key: str,
    slug: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_site_or_404(db, site_key)
    row = _get_page_or_404(db, site.id, slug)
    crud.delete_cms_page(db, row)


@router.get(
    "/sites/{site_key}/pages/{slug}/sections",
    response_model=PaginatedResponse[schemas.CmsSectionRead],
)
def list_sections(
    site_key: str,
    slug: str,
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    section_type: str | None = Query(None),
    _: models.User = Depends(require_module_access("cms", "read")),
):
    site = _get_site_or_404(db, site_key)
    page = _get_page_or_404(db, site.id, slug)
    items, total = crud.list_cms_sections(db, page.id, skip=skip, limit=limit, section_type=section_type)
    return PaginatedResponse[schemas.CmsSectionRead](
        items=items, total=total, skip=skip, limit=limit
    )




@router.post(
    "/sites/{site_key}/pages/{slug}/sections",
    response_model=schemas.CmsSectionRead,
    status_code=201,
)
def create_section(
    site_key: str,
    slug: str,
    payload: schemas.CmsSectionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    allowed_types = get_allowed_section_types(db)
    if payload.type not in allowed_types:
        raise HTTPException(status_code=422, detail="unsupported section type")
    # Validate props against section type schema
    from backend.schemas.cms_v2_sections import validate_section_props
    try:
        props = payload.props_json or {}
        validated_props = validate_section_props(payload.type, props)
        payload.props_json = validated_props
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    payload.status = (payload.status or "active").strip().lower()
    if payload.status not in {"active", "archived"}:
        raise HTTPException(status_code=422, detail="unsupported section status")
    site = _get_site_or_404(db, site_key)
    page = _get_page_or_404(db, site.id, slug)
    return crud.create_cms_section(db, page.id, payload)


@router.patch(
    "/sites/{site_key}/pages/{slug}/sections/{section_id}",
    response_model=schemas.CmsSectionRead,
)
def patch_section(
    site_key: str,
    slug: str,
    section_id: uuid.UUID,
    payload: schemas.CmsSectionUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    allowed_types = get_allowed_section_types(db)
    if payload.type is not None and payload.type not in allowed_types:
        raise HTTPException(status_code=422, detail="unsupported section type")
    if payload.status is not None:
        payload.status = payload.status.strip().lower()
        if payload.status not in {"active", "archived"}:
            raise HTTPException(status_code=422, detail="unsupported section status")
    site = _get_site_or_404(db, site_key)
    page = _get_page_or_404(db, site.id, slug)
    row = crud.get_cms_section(db, page.id, section_id)
    if not row:
        raise HTTPException(status_code=404, detail="section not found")
    return crud.update_cms_section(db, row, payload)


@router.delete("/sites/{site_key}/pages/{slug}/sections/{section_id}", status_code=204)
def delete_section(
    site_key: str,
    slug: str,
    section_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_site_or_404(db, site_key)
    page = _get_page_or_404(db, site.id, slug)
    row = crud.get_cms_section(db, page.id, section_id)
    if not row:
        raise HTTPException(status_code=404, detail="section not found")
    crud.archive_cms_section(db, row)


@router.post(
    "/sites/{site_key}/pages/{slug}/sections/reorder",
    response_model=list[schemas.CmsSectionRead],
)
def reorder_sections(
    site_key: str,
    slug: str,
    payload: schemas.CmsSectionReorderPayload,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_site_or_404(db, site_key)
    page = _get_page_or_404(db, site.id, slug)
    return crud.reorder_cms_sections(db, page.id, payload.items)
@router.get(
    "/sites/{site_key}/pages/{slug}/versions",
    response_model=PaginatedResponse[schemas.CmsPageVersionRead],
)
def list_versions(
    site_key: str,
    slug: str,
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    _: models.User = Depends(require_module_access("cms", "read")),
):
    site = _get_site_or_404(db, site_key)
    page = _get_page_or_404(db, site.id, slug)
    items, total = crud.list_cms_page_versions(db, page.id, skip=skip, limit=limit)
    return PaginatedResponse[schemas.CmsPageVersionRead](
        items=items, total=total, skip=skip, limit=limit
    )




@router.get(
    "/sites/{site_key}/pages/{slug}/publish-log",
    response_model=PaginatedResponse[schemas.CmsPublishLogRead],
)
def list_publish_log(
    site_key: str,
    slug: str,
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    _: models.User = Depends(require_module_access("cms", "read")),
):
    site = _get_site_or_404(db, site_key)
    page = _get_page_or_404(db, site.id, slug)
    items, total = crud.list_cms_publish_logs(db, site.id, page_id=page.id, skip=skip, limit=limit)
    return PaginatedResponse[schemas.CmsPublishLogRead](
        items=items, total=total, skip=skip, limit=limit
    )




@router.get(
    "/sites/{site_key}/pages/{slug}/preview", response_model=schemas.CmsPublicPageRead
)
def preview_page(
    site_key: str,
    slug: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_site_or_404(db, site_key)
    page = _get_page_or_404(db, site.id, slug)
    sections_list, _ = crud.list_cms_sections(db, page.id)
    sections = [
        section
        for section in sections_list
        if section.is_visible and getattr(section, "status", "active") != "archived"
    ]
    return schemas.CmsPublicPageRead(
        site_key=site.site_key,
        slug=page.slug,
        title=page.title,
        seo_json=page.seo_json or {},
        sections=[
            schemas.CmsSectionRead.model_validate(section) for section in sections
        ],
    )


@router.post(
    "/sites/{site_key}/pages/{slug}/rollback/{version_id}",
    response_model=schemas.CmsPageRead,
)
def rollback_page(
    site_key: str,
    slug: str,
    version_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    _assert_role(current_user, CMS_PUBLISHER_ROLES)
    site = _get_site_or_404(db, site_key)
    page = _get_page_or_404(db, site.id, slug)
    version = crud.get_cms_page_version(db, page.id, version_id)
    if not version:
        raise HTTPException(status_code=404, detail="version not found")
    return crud.restore_cms_page_version(db, page, version, user_id=current_user.id)


@router.post(
    "/sites/{site_key}/pages/{slug}/workflow", response_model=schemas.CmsPageRead
)
def workflow_page(
    site_key: str,
    slug: str,
    payload: schemas.CmsWorkflowAction,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    action = payload.action.strip().lower()
    if action in {"approve", "publish", "archive"}:
        _assert_role(current_user, CMS_PUBLISHER_ROLES)
    else:
        _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_site_or_404(db, site_key)
    page = _get_page_or_404(db, site.id, slug)
    row = crud.transition_cms_page_status(
        db, page, payload.action, current_user.id, notes=payload.notes
    )
    if not row:
        raise HTTPException(status_code=422, detail="invalid workflow action")
    return row


@router.get(
    "/public/sites/{site_key}/theme",
    response_model=schemas.CmsThemeRead,
    dependencies=[Depends(rate_limiter(limit=30, window_seconds=60))],
)
@cached_public(ttl=300)
def public_theme(site_key: str, db: Session = Depends(get_db)):
    site = _get_public_site_or_404(db, site_key)
    row = crud.get_active_cms_theme(db, site.id)
    if not row:
        raise HTTPException(status_code=404, detail="active theme not found")
    return row


@router.get(
    "/public/sites/{site_key}/menus/{menu_key}",
    dependencies=[Depends(rate_limiter(limit=30, window_seconds=60))],
)
@cached_public(ttl=300)
def public_menu(site_key: str, menu_key: str, db: Session = Depends(get_db)):
    site = _get_public_site_or_404(db, site_key)
    menu = _get_menu_or_404(db, site.id, menu_key)
    if not menu.is_active:
        raise HTTPException(status_code=404, detail="menu not found")
    all_items = crud.list_cms_menu_items(db, menu.id)
    public_ids = {item.id for item in all_items if item.visibility == "public"}
    items = [item for item in all_items if item.visibility == "public" and (item.parent_id is None or item.parent_id in public_ids)]
    visible_ids = {item.id for item in items}
    serialized = [
        {
            "id": item.id,
            "parent_id": item.parent_id if item.parent_id in visible_ids else None,
            "label": item.label,
            "href": item.href,
            "target": item.target,
            "is_external": item.is_external,
            "visibility": item.visibility,
            "sort_order": item.sort_order,
            "meta_json": item.meta_json or {},
        }
        for item in items
    ]
    return {
        "site_key": site.site_key,
        "menu_key": menu.menu_key,
        "items": serialized,
    }


import time


_system_var_cache: dict[str, tuple[float, str]] = {}
_SYSTEM_VAR_TTL = 300  # 5 minutes


def _get_system_var(db, site_key: str, var_key: str, default: str = "") -> str:
    """Read a single SystemVariable by key, with optional site_key prefix.
    Cached for 5 minutes per site_key+var_key to avoid repeated DB hits."""
    cache_key = f"{site_key}:{var_key}"
    now = time.monotonic()
    if cache_key in _system_var_cache:
        cached_time, cached_val = _system_var_cache[cache_key]
        if now - cached_time < _SYSTEM_VAR_TTL:
            return cached_val
    row = (
        db.query(models.SystemVariable)
        .filter(models.SystemVariable.key == f"{site_key}_{var_key}")
        .first()
    )
    val = row.value if row and row.value else default
    _system_var_cache[cache_key] = (now, val)
    return val


def _build_section_defaults(
    db: Session, site_key: str, section_type: str, props: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Fill empty section props with data from SystemVariable / DB / hardcoded."""
    # If the section already has meaningful content, skip defaults
    if props and any(
        key in props
        for key in ("title", "subtitle", "body", "content", "items", "personas", "stats", "testimonials", "faqs", "embed_url", "map_url")
    ):
        return props or {}

    church_name = _get_system_var(db, site_key, "church_name", "Nuestra Iglesia")
    mission = _get_system_var(db, site_key, "mission_statement", "Compartir el amor de Dios y hacer discípulos")
    service_time = _get_system_var(db, site_key, "service_time", "Domingos 10:00 AM")
    address = _get_system_var(db, site_key, "address", "Ciudad, País")
    map_embed = _get_system_var(db, site_key, "map_embed_url", "")

    if section_type == "hero":
        welcome = _get_system_var(db, site_key, "welcome_title", "Bienvenidos a {church_name}")
        return {
            "title": welcome.replace("{church_name}", church_name),
            "subtitle": mission,
            "cta_text": _get_system_var(db, site_key, "cta_text", "Conócenos"),
            "cta_link": _get_system_var(db, site_key, "cta_link", "/pastores"),
        }

    if section_type == "cta_banner":
        return {
            "title": _get_system_var(
                db, site_key, "cta_title", "Únete a nuestra comunidad"
            ),
            "description": _get_system_var(
                db, site_key, "cta_description",
                "Te invitamos a ser parte de nuestra familia. Todos son bienvenidos.",
            ),
            "button_text": "Visítanos",
            "button_link": "/contacto",
        }

    if section_type == "stats":
        active_personas = (
            db.query(models.Persona)
            .filter(models.Persona.estado_vital == "ACTIVO")
            .count()
        )
        group_count = db.query(models.GrupoEvangelismo).filter(models.GrupoEvangelismo.status == "Activo").count()
        return {
            "stats": [
                {"label": "Miembros Activos", "value": str(active_personas or 0)},
                {"label": "Grupos de Casa", "value": str(group_count or 0)},
                {"label": "Años de Ministerio", "value": "25+"},
            ]
        }

    if section_type == "team":
        leaders = (
            db.query(models.Persona)
            .filter(models.Persona.is_pastoral_leader.is_(True))
            .order_by(models.Persona.is_main_pastor.desc(), models.Persona.nombre_completo.asc())
            .all()
        )
        personas = []
        for p in leaders:
            name = p.nombre_completo
            slug = _slugify(name)
            personas.append({
                "name": name,
                "role": "Pastor Principal" if p.is_main_pastor else "Pastor",
                "photo_url": p.photo_url or "",
                "slug": slug,
                "bio_short": p.bio_short or "",
            })
        if not personas:
            personas = [{"name": "Pastor", "role": "Pastor Principal", "photo_url": "", "slug": "pastor", "bio_short": ""}]
        return {"personas": personas, "title": "Nuestro Equipo Pastoral"}

    if section_type == "testimonials":
        rows = (
            db.query(models.Testimonial)
            .filter(
                models.Testimonial.is_approved.is_(True),
                models.Testimonial.status == "published",
            )
            .order_by(models.Testimonial.created_at.desc())
            .limit(6)
            .all()
        )
        testimonials = []
        for t in rows:
            author_name = t.author.nombre_completo if t.author else "Anónimo"
            testimonials.append({
                "content": t.content,
                "author": author_name,
                "emotion": t.emotion or "Gratitud",
                "image_url": t.image_url or "",
            })
        if not testimonials:
            testimonials = [
                {"content": "Dios ha sido fiel en cada etapa. Bendigo a esta iglesia por su amor y apoyo.", "author": "Miembro de la Iglesia", "emotion": "Gratitud", "image_url": ""},
            ]
        return {"testimonials": testimonials, "title": "Testimonios"}

    if section_type == "faq":
        return {
            "faqs": [
                {"question": "¿A qué hora son los servicios?", "answer": service_time},
                {"question": "¿Dónde están ubicados?", "answer": address},
                {"question": "¿Qué debo esperar en mi primera visita?", "answer": "Una comunidad cálida que te recibirá con los brazos abiertos. Ven tal como eres."},
                {"question": "¿Tienen grupos de estudio?", "answer": "Sí, tenemos grupos de casa que se reúnen durante la semana. Contáctanos para más información."},
            ],
            "title": "Preguntas Frecuentes",
        }

    if section_type == "embed":
        return {
            "embed_url": map_embed or "",
            "title": church_name,
            "description": address,
        }

    return props or {}


@router.get(
    "/public/sites/{site_key}/pages",
    response_model=PaginatedResponse[schemas.CmsPageRead],
    dependencies=[Depends(rate_limiter(limit=20, window_seconds=60))],
)
@cached_public(ttl=300)
def public_pages_list(
    site_key: str,
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=500),
):
    """Public endpoint: list published CMS pages for sitemap and SEO."""
    site = _get_public_site_or_404(db, site_key)
    pages, total = crud.list_cms_pages(db, site.id, skip=skip, limit=limit, status="published")
    return PaginatedResponse[schemas.CmsPageRead](
        items=pages, total=total, skip=skip, limit=limit
    )


@router.get(
    "/public/sites/{site_key}/pages/{slug}",
    response_model=schemas.CmsPublicPageRead,
    dependencies=[Depends(rate_limiter(limit=30, window_seconds=60))],
)
@cached_public(ttl=300)
def public_page(site_key: str, slug: str, db: Session = Depends(get_db)):
    site = _get_public_site_or_404(db, site_key)
    page = crud.get_public_cms_page(db, site.id, _slugify(slug))
    if not page:
        raise HTTPException(status_code=404, detail="published page not found")
    published_version = None
    if page.published_version_id:
        published_version = crud.get_cms_page_version(
            db, page.id, page.published_version_id
        )

    if published_version:
        snapshot = published_version.snapshot_json or {}
        page_snapshot = snapshot.get("page") if isinstance(snapshot, dict) else {}
        sections_snapshot = (
            snapshot.get("sections") if isinstance(snapshot, dict) else []
        )
        section_rows = [
            _snapshot_section_read(
                section_data,
                page_id=page.id,
                index=index,
                timestamp=published_version.created_at,
            )
            for index, section_data in enumerate(
                sorted(
                    [item for item in sections_snapshot if isinstance(item, dict)],
                    key=lambda item: (
                        item.get("sort_order")
                        if isinstance(item.get("sort_order"), int)
                        else 0
                    ),
                )
            )
            if section_data.get("is_visible", True) is not False
            and section_data.get("status", "active") != "archived"
        ]
        # ── Inject default props for empty sections (published version path) ──
        section_rows = [
            schemas.CmsSectionRead(
                **{
                    **s.model_dump(),
                    "props_json": _build_section_defaults(
                        db, site_key, s.type, s.props_json
                    ),
                }
            )
            for s in section_rows
        ]
        return schemas.CmsPublicPageRead(
            site_key=site.site_key,
            slug=(
                str(page_snapshot.get("slug") or page.slug)
                if isinstance(page_snapshot, dict)
                else page.slug
            ),
            title=(
                str(page_snapshot.get("title") or page.title)
                if isinstance(page_snapshot, dict)
                else page.title
            ),
            seo_json=(
                page_snapshot.get("seo_json")
                if isinstance(page_snapshot, dict)
                and isinstance(page_snapshot.get("seo_json"), dict)
                else {}
            ),
            sections=section_rows,
        )

    sections_list, _ = crud.list_cms_sections(db, page.id)
    sections = [
        section
        for section in sections_list
        if section.is_visible and getattr(section, "status", "active") != "archived"
    ]
    section_reads = []
    for section in sections:
        sr = schemas.CmsSectionRead.model_validate(section)
        sr.props_json = _build_section_defaults(db, site_key, sr.type, sr.props_json)
        section_reads.append(sr)
    return schemas.CmsPublicPageRead(
        site_key=site.site_key,
        slug=page.slug,
        title=page.title,
        seo_json=page.seo_json or {},
        sections=section_reads,
    )


# ── Pastoral Team (public + CMS-managed) ───────────────────────────────────


def _pastoral_role(persona: models.Persona) -> str:
    role = (getattr(persona, "church_role", None) or "").strip()
    if role:
        return role
    return "Pastor Principal" if persona.is_main_pastor else "Pastor"


@router.get(
    "/public/sites/{site_key}/pastoral-team",
    response_model=List[schemas.PastoralProfileRead],
    dependencies=[Depends(rate_limiter(limit=20, window_seconds=60))],
)
@cached_public(ttl=300)
def public_pastoral_team(site_key: str, db: Session = Depends(get_db)):
    """Public endpoint: list pastoral leaders.

    Axioma 3 — Multi-Tenant: las pastoras y pastores listados se acotan
    a la sede del usuario actual. Sin embargo, este endpoint es PÚBLICO,
    por lo que ``get_user_sede_id`` retorna ``None`` cuando el caller no
    está autenticado (visitante anónimo) — en ese caso verá el agregado
    global. Para mantener una experiencia consistente con el resto del
    hold hardening, los uniones se hacen a nivel de la query base y el
    caller decide (admin/visitante) si filtra o no.
    """
    # Verify site exists (no auth required for public)
    _get_public_site_or_404(db, site_key)
    base_query = db.query(models.Persona).filter(
        models.Persona.is_pastoral_leader.is_(True)
    )
    # Para endpoints públicos no se aplica scope (anónimo). El caller
    # autenticado via Authorization header puede recibir respuesta
    # scoped (vía ``get_user_sede_id``); sin embargo, este endpoint no
    # extrae el token actualmente (no existe dep auth en endpoints
    # públicos). El scope aplica al flujo CMS-admin en su contraparte.
    leaders = base_query.order_by(
        models.Persona.is_main_pastor.desc(), models.Persona.nombre_completo.asc()
    ).all()
    result = []
    for p in leaders:
        name = p.nombre_completo
        result.append(
            schemas.PastoralProfileRead(
                id=str(p.id),
                name=name,
                slug=_slugify(name),
                photo_url=p.photo_url,
                bio_short=p.bio_short,
                bio_full=p.bio_full,
                role=_pastoral_role(p),
                social_instagram=p.social_instagram,
                social_facebook=p.social_facebook,
                social_twitter=p.social_twitter,
                is_main_pastor=p.is_main_pastor or False,
            )
        )
    return result


@router.get(
    "/cms/pastoral-team",
    response_model=List[schemas.PastoralProfileRead],
)
def cms_pastoral_team_list(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    """CMS endpoint: list pastoral leaders.

    Axioma 3 — Multi-Tenant: el listado se acota a la sede del staff.
    Sin esta validación, un editor de sede_a veía los perfiles pastorales
    de sede_b y podía editarlos (vector IDOR blindado en
    ``cms_pastoral_profile_update``). El staff sin sede
    (superadmin / anterior) sigue viendo el agregado global.
    """
    _assert_role(current_user, CMS_EDITOR_ROLES)
    base_query = db.query(models.Persona).filter(
        models.Persona.is_pastoral_leader.is_(True)
    )
    base_query = _scope_cms_pastoral_team_by_user_sede(db, current_user, base_query)
    leaders = base_query.order_by(
        models.Persona.is_main_pastor.desc(), models.Persona.nombre_completo.asc()
    ).all()
    result = []
    for p in leaders:
        name = p.nombre_completo
        result.append(
            schemas.PastoralProfileRead(
                id=str(p.id),
                name=name,
                slug=_slugify(name),
                photo_url=p.photo_url,
                bio_short=p.bio_short,
                bio_full=p.bio_full,
                role=_pastoral_role(p),
                social_instagram=p.social_instagram,
                social_facebook=p.social_facebook,
                social_twitter=p.social_twitter,
                is_main_pastor=p.is_main_pastor or False,
            )
        )
    return result


@router.patch(
    "/cms/pastoral-team/{persona_id}",
    response_model=schemas.PastoralProfileRead,
)
def cms_pastoral_profile_update(
    persona_id: str,
    payload: schemas.PastoralProfileUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    """CMS endpoint: update a pastoral leader's profile.

    Axioma 3 — IDOR FIX (CRÍTICO): antes de este fix,
    ``crud.get_persona_by_id(db, persona_id)`` retornaba cualquier
    Persona del platform, sin validar que perteneciera a la sede del
    staff actual. Un editor CMS de sede_a con rol ``cms:edit`` podía
    entonces mutar ``photo_url``, ``bio_full``, ``social_*``,
    ``is_main_pastor`` y ``is_pastoral_leader`` de CUALQUIER pastor de
    CUALQUIER sede — un IDOR ciego, defense in depth insuficiente.

    Ahora usamos el helper existente ``_get_scoped_persona`` (mismo
    pattern que ``/api/crm/personas/{id}``): 404 cross-sede
    (existence-leak safe, no 403). Si la persona es de la propia sede,
    el CRUD aplica la mutación; si es de otra sede, 404.

    Defense-in-depth: ``update_pastoral_profile`` CRUD también valida
    scope pre-commit (param ``actor_user_id`` propagado)."""
    _assert_role(current_user, CMS_EDITOR_ROLES)
    persona = _get_scoped_persona(db, current_user, persona_id)
    persona = crud.update_pastoral_profile(
        db,
        persona,
        payload,
        actor_user_id=str(current_user.id),
    )
    name = persona.nombre_completo
    return schemas.PastoralProfileRead(
        id=str(persona.id),
        name=name,
        slug=_slugify(name),
        photo_url=persona.photo_url,
        bio_short=persona.bio_short,
        bio_full=persona.bio_full,
        role=_pastoral_role(persona),
        social_instagram=persona.social_instagram,
        social_facebook=persona.social_facebook,
        social_twitter=persona.social_twitter,
        is_main_pastor=persona.is_main_pastor or False,
    )


@router.get("/global-blocks", response_model=PaginatedResponse[schemas.CmsSectionRead])
def list_global_blocks(
    site_key: str,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_site_or_404(db, site_key)
    base = (
        db.query(models.CmsSection)
        .join(models.CmsPage, models.CmsSection.page_id == models.CmsPage.id)
        .filter(
            models.CmsPage.site_id == site.id,
            models.CmsSection.is_global,
            models.CmsSection.is_visible,
            models.CmsSection.deleted_at.is_(None),
        )
    )
    total = base.count()
    blocks = base.order_by(models.CmsSection.global_key).offset(skip).limit(limit).all()
    return PaginatedResponse(
        items=[schemas.CmsSectionRead.model_validate(b) for b in blocks],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.post("/global-blocks", response_model=schemas.CmsSectionRead, status_code=201)
def create_global_block(
    site_key: str,
    payload: schemas.CmsSectionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    allowed_types = get_allowed_section_types(db)
    if payload.type not in allowed_types:
        raise HTTPException(status_code=422, detail="unsupported section type")
    from backend.schemas.cms_v2_sections import validate_section_props
    try:
        validated_props = validate_section_props(payload.type, payload.props_json or {})
        payload.props_json = validated_props
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    site = _get_site_or_404(db, site_key)
    page = db.query(models.CmsPage).filter(
        models.CmsPage.site_id == site.id,
        models.CmsPage.slug == "_global_blocks",
    ).first()
    if not page:
        page = models.CmsPage(
            site_id=site.id, slug="_global_blocks", title="Global Blocks", status="draft",
        )
        db.add(page)
        db.flush()
    payload.is_global = True
    payload.section_key = payload.section_key or f"global_{uuid.uuid4().hex[:8]}"
    block = crud.create_cms_section(db, page.id, payload)
    db.commit()
    db.refresh(block)
    return schemas.CmsSectionRead.model_validate(block)


@router.patch("/global-blocks/{section_id}", response_model=schemas.CmsSectionRead)
def patch_global_block(
    site_key: str, section_id: uuid.UUID, payload: schemas.CmsSectionUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    block = db.query(models.CmsSection).filter(
        models.CmsSection.id == section_id, models.CmsSection.is_global,
    ).first()
    if not block:
        raise HTTPException(status_code=404, detail="Global block not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        if hasattr(block, key):
            setattr(block, key, value)
    db.commit()
    db.refresh(block)
    return schemas.CmsSectionRead.model_validate(block)


@router.delete("/global-blocks/{section_id}", response_model=dict)
def delete_global_block(
    site_key: str, section_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    block = db.query(models.CmsSection).filter(
        models.CmsSection.id == section_id, models.CmsSection.is_global,
    ).first()
    if not block:
        raise HTTPException(status_code=404, detail="Global block not found")
    block.deleted_at = _utcnow()
    db.commit()
    return {"ok": True, "deleted": section_id}


# ── PAGE VIEWS TRACKING (Phase 6 Analytics) ────────────────────────────────────

@router.post("/track/{page_key}", response_model=dict)
def track_page_view(page_key: str, request: Request, db: Session = Depends(get_db)):
    """Track a page view for analytics."""
    try:
        page = db.query(models.CmsPage).join(models.CmsSite).filter(
            models.CmsPage.slug == page_key,
        ).first()
        if page:
            db.add(models.CmsPageView(
                page_id=page.id,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent", ""),
                referrer=request.headers.get("referer", ""),
            ))
            db.commit()
    except Exception:
        logger.warning("Analytics tracking failed for page_key=%s", page_key, exc_info=True)
    return {"ok": True}


@router.get("/analytics/{page_key}", response_model=dict)
def get_page_analytics(
    page_key: str, days: int = Query(30, le=365),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    """Get page view analytics."""
    from datetime import timedelta

    from sqlalchemy import func
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    page = db.query(models.CmsPage).join(models.CmsSite).filter(
        models.CmsPage.slug == page_key,
    ).first()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    total = (
        db.query(func.count(models.CmsPageView.id))
        .filter(models.CmsPageView.page_id == page.id, models.CmsPageView.created_at >= cutoff)
        .scalar() or 0
    )
    daily = (
        db.query(
            func.date(models.CmsPageView.created_at).label("date"),
            func.count(models.CmsPageView.id).label("views"),
        )
        .filter(models.CmsPageView.page_id == page.id, models.CmsPageView.created_at >= cutoff)
        .group_by(func.date(models.CmsPageView.created_at))
        .order_by(func.date(models.CmsPageView.created_at))
        .all()
    )
    return {"page_key": page_key, "total_views": total, "days": days,
            "daily_views": [{"date": str(d), "views": v} for d, v in daily]}


# ── SCHEDULED PUBLISHING (Phase 4) ─────────────────────────────────────────────

@router.post("/pages/{page_id}/schedule", response_model=dict)
def schedule_page_publish(
    site_key: str, page_id: uuid.UUID, payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    """Schedule a page for future publication."""
    _assert_role(current_user, CMS_PUBLISHER_ROLES)
    scheduled_at = payload.get("scheduled_at")
    if not scheduled_at:
        raise HTTPException(status_code=400, detail="scheduled_at is required")
    try:
        datetime.fromisoformat(scheduled_at.replace("Z", "+00:00"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid datetime format")
    page = db.query(models.CmsPage).filter(models.CmsPage.id == page_id).first()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    page.status = "scheduled"
    seo = page.seo_json or {}
    seo["_scheduled_at"] = scheduled_at
    page.seo_json = seo
    db.commit()
    return {"ok": True, "scheduled_at": scheduled_at}


# ── IMAGE OPTIMIZATION (Phase 7) ───────────────────────────────────────────────
@router.get(
    "/images/{media_id}/resize",
    response_model=dict,
    dependencies=[Depends(rate_limiter(limit=60, window_seconds=60))],
)
def get_resized_image(
    media_id: uuid.UUID,
    width: int = Query(800, le=2400),
    height: Optional[int] = None,
    quality: int = Query(80, le=100),
    db: Session = Depends(get_db),
):
    """Get a resized version of an uploaded image. Returns base64 or URL.

    Defense-in-depth (Axioma 3): aunque este endpoint es público (la URL
    retornada puede ser consumida por el frontend faro), filtramos los
    media archivados — un media archivado no debe ser público vía API. La
    URL es por defecto del asset original, así que el caller puede
    servirlo desde CDN con ``<img width=...>`` sin pasar por aquí, pero
    mantenerlo scope-archived evita leaks de metadata para medios
    retirados del site público.
    """
    media = db.query(models.CmsMediaItem).filter(
        models.CmsMediaItem.id == media_id,
    ).first()
    if not media or (media.status or "") == "archived":
        raise HTTPException(status_code=404, detail="Media not found")
    # For now return the original URL with resize params
    return {"url": media.url, "width": width, "height": height, "quality": quality}


@router.post("/images/optimize", response_model=dict)
async def optimize_uploaded_image(
    media_id: uuid.UUID,
    max_width: int = Query(1920),
    quality: int = Query(80),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
    background_tasks: BackgroundTasks = None,
):
    """Optimize an uploaded image by resizing and reducing quality.

    Axioma 3 — Multi-Tenant (CRÍTICO, IDOR fix): antes de este fix,
    ``db.query(models.CmsMediaItem).filter(id == media_id)`` retornaba
    cualquier media del platform sin validar que perteneciera a la sede
    del staff actual. Un editor CMS de sede_a con rol ``cms:read`` podía
    entonces invocar ``/images/optimize`` con el ``media_id`` de un asset
    perteneciente a sede_b y forzar la reescritura del archivo JPEG
    optimizado en disco vía ``img.save(opt_path, ...)`` — un IDOR que
    resulta en modificación cross-sede del filesystem uploads_dir, no
    sólo de la fila en DB.

    Ahora usamos ``_get_scoped_cms_media`` (mismo helper que el resto
    del CMS-admin): 404 cross-sede (existence-leak safe, no 403) *antes*
    de tocar PIL o el filesystem. Si el media es de la propia sede, el
    CRUD procede con la optimización y el ``img.save``; si es de otra
    sede, 404 y el filesystem queda intacto.

    Defense-in-depth (lazy PIL import): el ``from PIL import Image`` se
    hace DESPUÉS del scope + archived check para que un entorno sin
    PIL instalado NO bypassee el scope check con un 500 — el cross-sede
    sigue siendo 404 limpio. Si PIL falta y el media es local+active,
    devolvemos 503 con un mensaje actionable (instale ``pillow``).

    Performance: la optimización pesada se ejecuta en background via
    ``BackgroundTasks`` para no bloquear la respuesta HTTP.
    """
    media = _get_scoped_cms_media(db, current_user, media_id)
    if (media.status or "") == "archived":
        raise HTTPException(status_code=404, detail="Media not found")

    try:
        from PIL import Image
    except ImportError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Pillow (PIL) no instalado en el servidor — instale "
                "el paquete ``pillow`` para habilitar /images/optimize."
            ),
        ) from exc
    from backend.core.config import get_settings

    settings = get_settings()
    orig_path = os.path.join(settings.uploads_dir, media.filename)
    if not os.path.exists(orig_path):
        raise HTTPException(status_code=404, detail="File not found")

    def _do_optimize():
        img = Image.open(orig_path)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        if img.width > max_width:
            ratio = max_width / img.width
            new_height = int(img.height * ratio)
            img = img.resize((max_width, new_height), Image.LANCZOS)
        opt_filename = f"opt_{media.filename.rsplit('.', 1)[0]}_{max_width}w.jpg"
        opt_path = os.path.join(settings.uploads_dir, opt_filename)
        img.save(opt_path, "JPEG", quality=quality, optimize=True)

    if background_tasks is not None:
        background_tasks.add_task(_do_optimize)

    opt_filename = f"opt_{media.filename.rsplit('.', 1)[0]}_{max_width}w.jpg"
    return {
        "status": "queued",
        "url": f"/uploads/{opt_filename}",
        "media_id": str(media_id),
        "max_width": max_width,
        "quality": quality,
    }
