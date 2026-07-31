"""Themes admin endpoints (Fase 4 refactor).

CRUD of themes + theme activation.
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
    _get_scoped_site_or_404,
)
from backend.core.database import get_db
from backend.core.permissions import require_module_access
from backend.exceptions.cms import ThemeNotFoundError

logger = logging.getLogger(__name__)

router = APIRouter(tags=["cms_v2_themes"])


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
    _assert_role(current_user, CMS_PUBLISHER_ROLES)
    site = _get_scoped_site_or_404(db, site_key, current_user)
    row = crud.get_cms_theme(db, site.id, theme_id)
    if not row:
        raise ThemeNotFoundError()
    crud.archive_cms_theme(db, row)
    return None
