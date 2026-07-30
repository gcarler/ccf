"""Native Popups API endpoints (R3-BE). Admin CRUD & Public active popups listing."""
from __future__ import annotations

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend import crud, models, schemas
from backend.api.cms_v2._shared import (
    CMS_EDITOR_ROLES,
    PUBLIC_CMS_RATE_LIMIT,
    _assert_role,
    _get_public_site_or_404,
    _get_scoped_site_or_404,
)
from backend.core.database import get_db
from backend.core.permissions import require_module_access
from backend.core.rate_limit import rate_limiter
from backend.exceptions.cms import PopupNotFoundError

logger = logging.getLogger(__name__)

router = APIRouter(tags=["cms_v2_popups"])


def _get_popup_or_404(db: Session, site_id: UUID, popup_id: UUID) -> models.CmsPopup:
    row = crud.get_cms_popup(db, site_id, popup_id)
    if not row:
        raise PopupNotFoundError()
    return row


# ── Public Endpoint ─────────────────────────────────────────────────────────

@router.get(
    "/public/popups",
    response_model=List[schemas.CmsPopupRead],
    dependencies=[Depends(rate_limiter(limit=PUBLIC_CMS_RATE_LIMIT, window_seconds=60))],
)
def get_public_popups(
    site_key: str = Query(..., description="CMS site key"),
    page_slug: Optional[str] = Query(None, description="Optional page slug filter"),
    db: Session = Depends(get_db),
):
    site = _get_public_site_or_404(db, site_key)
    popups = crud.list_cms_popups(db, site.id, only_active=True)

    if page_slug is not None:
        clean_slug = page_slug.strip()
        popups = [
            p for p in popups
            if not p.show_on_pages or clean_slug in p.show_on_pages
        ]

    return popups


# ── Admin CRUD Endpoints ─────────────────────────────────────────────────────

@router.get("/sites/{site_key}/popups", response_model=List[schemas.CmsPopupRead])
def list_popups(
    site_key: str,
    only_active: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    site = _get_scoped_site_or_404(db, site_key, current_user)
    return crud.list_cms_popups(db, site.id, only_active=only_active)


@router.post(
    "/sites/{site_key}/popups",
    response_model=schemas.CmsPopupRead,
    status_code=201,
)
def create_popup(
    site_key: str,
    payload: schemas.CmsPopupCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_scoped_site_or_404(db, site_key, current_user)
    return crud.create_cms_popup(db, site.id, payload)


@router.get("/sites/{site_key}/popups/{id}", response_model=schemas.CmsPopupRead)
def get_popup(
    site_key: str,
    id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    site = _get_scoped_site_or_404(db, site_key, current_user)
    return _get_popup_or_404(db, site.id, id)


@router.patch("/sites/{site_key}/popups/{id}", response_model=schemas.CmsPopupRead)
def update_popup(
    site_key: str,
    id: UUID,
    payload: schemas.CmsPopupUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_scoped_site_or_404(db, site_key, current_user)
    popup = _get_popup_or_404(db, site.id, id)
    return crud.update_cms_popup(db, popup, payload)


@router.delete("/sites/{site_key}/popups/{id}", status_code=204)
def delete_popup(
    site_key: str,
    id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):

    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_scoped_site_or_404(db, site_key, current_user)
    popup = _get_popup_or_404(db, site.id, id)
    crud.delete_cms_popup(db, popup)
