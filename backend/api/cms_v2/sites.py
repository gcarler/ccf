"""Sites admin endpoints (Fase 4 refactor).

Sites are the top-level tenant root of the CMS: every page, section, menu,
theme, post and media object hangs off a ``CmsSite`` owned by a ``sede``.
This module holds the site CRUD endpoints; the scoping helper
``_get_scoped_site_or_404`` consulted by every nested resource lives in
``_shared`` so the rest of the package can keep importing it directly.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend import crud, models, schemas
from backend.api.cms_v2._shared import (
    CMS_PUBLISHER_ROLES,
    _actor_sede_from_user,
    _assert_role,
    _get_scoped_site_or_404,
)
from backend.core.database import get_db
from backend.core.permissions import require_module_access
from backend.exceptions.cms import (
    CmsValidationError,
    SiteKeyAlreadyExistsError,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["cms_v2_sites"])


@router.get("/sites", response_model=list[schemas.CmsSiteRead])
def list_sites(
    only_active: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    """Listar sites CMS. Axioma 3 — Multi-Tenant: staff con sede solo
    ve sites de su sede; superadmin sin sede ve todos."""
    actor_sede = _actor_sede_from_user(db, current_user)
    sites = crud.list_cms_sites(db, only_active=only_active, sede_id=actor_sede)
    return sites


@router.post("/sites", response_model=schemas.CmsSiteRead, status_code=201)
def create_site(
    payload: schemas.CmsSiteCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_PUBLISHER_ROLES)
    if not payload.site_key.strip():
        raise CmsValidationError("Site key is required", error_code="site_key_required")
    if not payload.base_path.strip().startswith("/"):
        raise CmsValidationError("base_path must start with '/'")
    if crud.get_cms_site_by_key(db, payload.site_key.strip().lower()):
        raise SiteKeyAlreadyExistsError()
    # Axioma 3 — Multi-Tenant: si el actor tiene sede asignada, se fuerza
    # su sede_id (ignorando cualquier valor cross-sede del cliente). Si
    # el actor NO tiene sede (superadmin / anterior path), se respeta el
    # sede_id opcional del payload para permitir asignación administrativa.
    actor_sede = _actor_sede_from_user(db, current_user)
    if actor_sede is not None:
        if payload.sede_id is not None and payload.sede_id != actor_sede:
            payload.sede_id = actor_sede
        elif payload.sede_id is None:
            payload.sede_id = actor_sede
    row = crud.create_cms_site(db, payload, commit_with_conflict_check=True)
    if row is None:
        raise SiteKeyAlreadyExistsError()
    return row


@router.get("/sites/{site_key}", response_model=schemas.CmsSiteRead)
def get_site(
    site_key: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    site = _get_scoped_site_or_404(db, site_key, current_user)
    return site


@router.patch("/sites/{site_key}", response_model=schemas.CmsSiteRead)
def patch_site(
    site_key: str,
    payload: schemas.CmsSiteUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_PUBLISHER_ROLES)
    row = _get_scoped_site_or_404(db, site_key, current_user)
    # Axioma 3 — Multi-Tenant: bloquear movimiento cross-sede. El
    # sede_id de un site no debe cambiar via API para evitar que un
    # editor de sede_a "adopte" o "mueva" un site de sede_b.
    if payload.sede_id is not None:
        raise CmsValidationError(
            "sede_id cannot be changed via site update; create a new site instead",
            error_code="sede_id_immutable",
        )
    return crud.update_cms_site(db, row, payload)


@router.delete("/sites/{site_key}", status_code=204)
def delete_site(
    site_key: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    """Desactiva un sitio CMS sin eliminar su contenido."""
    _assert_role(current_user, CMS_PUBLISHER_ROLES)
    row = _get_scoped_site_or_404(db, site_key, current_user)
    crud.archive_cms_site(db, row)
    return None
