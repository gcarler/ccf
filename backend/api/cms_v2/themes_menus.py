"""Themes and menus admin endpoints (Fase 4 refactor).

Extracted from the monolithic ``cms_v2/__init__.py`` to reduce module size.
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend import crud, models, schemas
from backend.api.cms_v2._shared import (
    CMS_EDITOR_ROLES,
    CMS_PUBLISHER_ROLES,
    _assert_role,
    _get_menu_or_404,
    _get_scoped_site_or_404,
)
from backend.core.database import get_db
from backend.core.permissions import require_module_access
from backend.exceptions.cms import (
    MenuItemConflictError,
    MenuItemNotFoundError,
    MenuKeyConflictError,
    ThemeNotFoundError,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["cms_v2_themes_menus"])


# ── Themes CRUD ──────────────────────────────────────────────────────────────


@router.get("/sites/{site_key}/themes", response_model=list[schemas.CmsThemeRead])
def list_themes(
    site_key: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    site = _get_scoped_site_or_404(db, site_key, current_user)
    return crud.list_cms_themes(db, site.id)


@router.get("/sites/{site_key}/themes/{theme_id}", response_model=schemas.CmsThemeRead)
def get_theme(
    site_key: str,
    theme_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    site = _get_scoped_site_or_404(db, site_key, current_user)
    row = crud.get_cms_theme(db, site.id, theme_id)
    if not row:
        raise ThemeNotFoundError()
    return row


@router.post("/sites/{site_key}/themes", response_model=schemas.CmsThemeRead, status_code=201)
def create_theme(
    site_key: str,
    payload: schemas.CmsThemeCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    if payload.is_active:
        _assert_role(current_user, CMS_PUBLISHER_ROLES, detail="Only publishers can activate a theme")
    site = _get_scoped_site_or_404(db, site_key, current_user)
    return crud.create_cms_theme(db, site.id, payload, created_by=current_user.id)


@router.patch("/sites/{site_key}/themes/{theme_id}", response_model=schemas.CmsThemeRead)
def patch_theme(
    site_key: str,
    theme_id: uuid.UUID,
    payload: schemas.CmsThemeUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    if payload.is_active:
        _assert_role(current_user, CMS_PUBLISHER_ROLES, detail="Only publishers can activate a theme")
    site = _get_scoped_site_or_404(db, site_key, current_user)
    row = crud.get_cms_theme(db, site.id, theme_id)
    if not row:
        raise ThemeNotFoundError()
    return crud.update_cms_theme(db, row, payload)


@router.post("/sites/{site_key}/themes/{theme_id}/activate", response_model=schemas.CmsThemeRead)
def activate_theme(
    site_key: str,
    theme_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_PUBLISHER_ROLES)
    site = _get_scoped_site_or_404(db, site_key, current_user)
    row = crud.activate_cms_theme(db, site.id, theme_id)
    if not row:
        raise ThemeNotFoundError()
    return row


@router.delete("/sites/{site_key}/themes/{theme_id}", status_code=204)
def delete_theme(
    site_key: str,
    theme_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    """Archiva un tema CMS sin eliminar su historial."""
    _assert_role(current_user, CMS_PUBLISHER_ROLES)
    site = _get_scoped_site_or_404(db, site_key, current_user)
    row = crud.get_cms_theme(db, site.id, theme_id)
    if not row:
        raise ThemeNotFoundError()
    crud.archive_cms_theme(db, row)
    return None


# ── Menus CRUD ───────────────────────────────────────────────────────────────


@router.get("/sites/{site_key}/menus", response_model=list[schemas.CmsMenuRead])
def list_menus(
    site_key: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    site = _get_scoped_site_or_404(db, site_key, current_user)
    return crud.list_cms_menus(db, site.id)


@router.post("/sites/{site_key}/menus", response_model=schemas.CmsMenuRead, status_code=201)
def create_menu(
    site_key: str,
    payload: schemas.CmsMenuCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_scoped_site_or_404(db, site_key, current_user)
    if crud.get_cms_menu(db, site.id, payload.menu_key.strip().lower()):
        raise MenuKeyConflictError()
    row = crud.create_cms_menu(db, site.id, payload, commit_with_conflict_check=True)
    if row is None:
        raise MenuKeyConflictError()
    return row


@router.get("/sites/{site_key}/menus/{menu_key}", response_model=schemas.CmsMenuRead)
def get_menu(
    site_key: str,
    menu_key: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    site = _get_scoped_site_or_404(db, site_key, current_user)
    return _get_menu_or_404(db, site.id, menu_key)


@router.patch("/sites/{site_key}/menus/{menu_key}", response_model=schemas.CmsMenuRead)
def patch_menu(
    site_key: str,
    menu_key: str,
    payload: schemas.CmsMenuUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_scoped_site_or_404(db, site_key, current_user)
    row = _get_menu_or_404(db, site.id, menu_key)
    return crud.update_cms_menu(db, row, payload)


@router.delete("/sites/{site_key}/menus/{menu_key}", status_code=204)
def delete_menu(
    site_key: str,
    menu_key: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    """Desactiva un menu CMS sin eliminarlo."""
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_scoped_site_or_404(db, site_key, current_user)
    row = _get_menu_or_404(db, site.id, menu_key)
    crud.delete_cms_menu(db, row)


# ── Menu Items CRUD ──────────────────────────────────────────────────────────


@router.get(
    "/sites/{site_key}/menus/{menu_key}/items",
    response_model=list[schemas.CmsMenuItemRead],
)
def list_menu_items(
    site_key: str,
    menu_key: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    site = _get_scoped_site_or_404(db, site_key, current_user)
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
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_scoped_site_or_404(db, site_key, current_user)
    menu = _get_menu_or_404(db, site.id, menu_key)
    row = crud.create_cms_menu_item(db, menu.id, payload, commit_with_conflict_check=True)
    if row is None:
        raise MenuItemConflictError()
    return row


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
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_scoped_site_or_404(db, site_key, current_user)
    menu = _get_menu_or_404(db, site.id, menu_key)
    item = crud.get_cms_menu_item(db, menu.id, item_id, site_id=site.id)
    if not item:
        raise MenuItemNotFoundError()
    return crud.update_cms_menu_item(db, item, payload)


@router.delete("/sites/{site_key}/menus/{menu_key}/items/{item_id}", status_code=204)
def delete_menu_item(
    site_key: str,
    menu_key: str,
    item_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    """Oculta un item de menu sin eliminarlo."""
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_scoped_site_or_404(db, site_key, current_user)
    menu = _get_menu_or_404(db, site.id, menu_key)
    item = crud.get_cms_menu_item(db, menu.id, item_id, site_id=site.id)
    if not item:
        raise MenuItemNotFoundError()
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
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_scoped_site_or_404(db, site_key, current_user)
    menu = _get_menu_or_404(db, site.id, menu_key)
    return crud.reorder_cms_menu_items(db, menu.id, payload.items)
