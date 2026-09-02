"""Section type catalog admin endpoints (Fase 4 refactor).

Section types are platform-wide (no site FK) — they define the catalog of
section types available to all sites when building pages. This module
holds the CRUD endpoints and the runtime guard ``get_allowed_section_types``
consulted by ``create_section`` and ``patch_section``.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend import models, schemas
from backend.api.cms.section_catalog import FALLBACK_SECTION_TYPES
from backend.api.cms_v2._shared import (
    CMS_PUBLISHER_ROLES,
    _assert_role,
    _commit_or_raise_conflict,
)
from backend.core.audit import record_admin_action
from backend.core.database import get_db
from backend.core.permissions import require_module_access
from backend.exceptions.cms import (
    CmsValidationError,
    SectionTypeAlreadyExistsError,
    SectionTypeNotFoundError,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["cms_v2_section_types"])


def _get_section_type_or_404(db: Session, name: str) -> models.CmsSectionType:
    """Look up by name (the public identifier) or raise 404."""
    row = db.query(models.CmsSectionType).filter(models.CmsSectionType.name == name.strip().lower()).first()
    if not row:
        raise SectionTypeNotFoundError()
    return row


@router.get(
    "/section-types",
    response_model=list[schemas.CmsSectionTypeRead],
)
def list_section_types(
    only_active: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
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
    current_user: models.User = Depends(require_module_access("cms", "read")),
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
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_PUBLISHER_ROLES)
    name = payload.name.strip().lower()
    if not name:
        raise CmsValidationError("Name is required", error_code="name_required")
    if db.query(models.CmsSectionType).filter(models.CmsSectionType.name == name).first():
        raise SectionTypeAlreadyExistsError()
    row = models.CmsSectionType(
        name=name,
        description=payload.description,
        is_active=payload.is_active,
    )
    db.add(row)
    _commit_or_raise_conflict(db, detail="section type already exists")
    db.refresh(row)
    record_admin_action(db, current_user, "cms.section_type.create", "cms_section_type", str(row.id))
    return row


@router.patch(
    "/section-types/{name}",
    response_model=schemas.CmsSectionTypeRead,
)
def patch_section_type(
    name: str,
    payload: schemas.CmsSectionTypeUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_PUBLISHER_ROLES)
    row = _get_section_type_or_404(db, name)
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    record_admin_action(db, current_user, "cms.section_type.update", "cms_section_type", str(row.id))
    return row


@router.delete("/section-types/{name}", status_code=204)
def delete_section_type(
    name: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_PUBLISHER_ROLES)
    row = _get_section_type_or_404(db, name)
    row.is_active = False
    db.commit()
    record_admin_action(db, current_user, "cms.section_type.archive", "cms_section_type", str(row.id))
    return None


def get_allowed_section_types(db: Session) -> set[str]:
    """Return set of active section type names from DB, fallback to hardcoded."""
    try:
        rows = db.query(models.CmsSectionType.name).filter(models.CmsSectionType.is_active.is_(True)).all()
        types = {row[0] for row in rows}
        if types:
            return types
    except Exception as exc:
        logger.debug("Section type catalog query failed, using hardcoded fallback: %s", exc)
    return set(FALLBACK_SECTION_TYPES)
