"""A/B Testing of Sections API endpoints (R3-BE). Admin CRUD, Event Recording, Results, Apply Winner."""

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
from backend.exceptions.cms import AbTestNotFoundError

logger = logging.getLogger(__name__)

router = APIRouter(tags=["cms_v2_ab_testing"])


def _get_ab_test_or_404(db: Session, site_id: UUID, test_id: UUID) -> models.CmsAbTest:
    row = crud.get_cms_ab_test(db, site_id, test_id)
    if not row:
        raise AbTestNotFoundError()
    return row


# ── Public Endpoints ─────────────────────────────────────────────────────────


@router.get(
    "/public/sites/{site_key}/ab-tests/active",
    response_model=List[schemas.CmsAbTestRead],
    dependencies=[Depends(rate_limiter(limit=PUBLIC_CMS_RATE_LIMIT, window_seconds=60))],
)
def get_public_active_ab_tests(
    site_key: str,
    page_id: Optional[UUID] = Query(None, description="Optional page ID filter"),
    db: Session = Depends(get_db),
):
    site = _get_public_site_or_404(db, site_key)
    return crud.list_cms_ab_tests(db, site.id, page_id=page_id, status="active")


# ── Event Recording ──────────────────────────────────────────────────────────


@router.post(
    "/sites/{site_key}/ab-tests/{id}/record-event",
    response_model=schemas.CmsAbTestEventRead,
    status_code=201,
    dependencies=[Depends(rate_limiter(limit=PUBLIC_CMS_RATE_LIMIT, window_seconds=60))],
)
def record_ab_test_event(
    site_key: str,
    id: UUID,
    payload: schemas.CmsAbTestEventCreate,
    db: Session = Depends(get_db),
):
    # Verify test exists for site
    site = _get_public_site_or_404(db, site_key)
    test = _get_ab_test_or_404(db, site.id, id)
    return crud.record_cms_ab_test_event(db, test.id, payload)


# ── Admin CRUD Endpoints ─────────────────────────────────────────────────────


@router.get("/sites/{site_key}/ab-tests", response_model=List[schemas.CmsAbTestRead])
def list_ab_tests(
    site_key: str,
    page_id: Optional[UUID] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    site = _get_scoped_site_or_404(db, site_key, current_user)
    return crud.list_cms_ab_tests(db, site.id, page_id=page_id, status=status)


@router.post(
    "/sites/{site_key}/ab-tests",
    response_model=schemas.CmsAbTestRead,
    status_code=201,
)
def create_ab_test(
    site_key: str,
    payload: schemas.CmsAbTestCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_scoped_site_or_404(db, site_key, current_user)
    return crud.create_cms_ab_test(db, site.id, payload, actor_user_id=current_user.id)


@router.get("/sites/{site_key}/ab-tests/{id}", response_model=schemas.CmsAbTestRead)
def get_ab_test(
    site_key: str,
    id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    site = _get_scoped_site_or_404(db, site_key, current_user)
    return _get_ab_test_or_404(db, site.id, id)


@router.patch("/sites/{site_key}/ab-tests/{id}", response_model=schemas.CmsAbTestRead)
def update_ab_test(
    site_key: str,
    id: UUID,
    payload: schemas.CmsAbTestUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_scoped_site_or_404(db, site_key, current_user)
    test = _get_ab_test_or_404(db, site.id, id)
    return crud.update_cms_ab_test(db, test, payload, actor_user_id=current_user.id)


@router.delete("/sites/{site_key}/ab-tests/{id}")
def delete_ab_test(
    site_key: str,
    id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_scoped_site_or_404(db, site_key, current_user)
    test = _get_ab_test_or_404(db, site.id, id)
    crud.delete_cms_ab_test(db, test, actor_user_id=current_user.id)
    return {"message": "A/B test deleted"}


@router.get(
    "/sites/{site_key}/ab-tests/{id}/results",
    response_model=schemas.CmsAbTestResults,
)
def get_ab_test_results(
    site_key: str,
    id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    site = _get_scoped_site_or_404(db, site_key, current_user)
    test = _get_ab_test_or_404(db, site.id, id)
    return crud.get_cms_ab_test_results(db, test.id)


@router.post(
    "/sites/{site_key}/ab-tests/{id}/apply-winner",
    response_model=schemas.CmsAbTestRead,
)
def apply_ab_test_winner(
    site_key: str,
    id: UUID,
    payload: Optional[schemas.CmsAbTestApplyWinner] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_scoped_site_or_404(db, site_key, current_user)
    test = _get_ab_test_or_404(db, site.id, id)
    return crud.apply_cms_ab_test_winner(
        db, site.id, test.id, payload, actor_user_id=current_user.id
    )
