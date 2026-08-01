"""Global blocks admin endpoints (Fase 4 refactor).

Global blocks are ``CmsSection`` rows flagged ``is_global=True`` that live
on a synthetic ``_global_blocks`` page per site, so they can be embedded
across multiple pages. This module holds their CRUD endpoints; the runtime
guard ``get_allowed_section_types`` (consulted by ``create_global_block``)
lives in ``section_types.py``.
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend import crud, models, schemas
from backend.api.cms_v2._shared import (
    CMS_EDITOR_ROLES,
    _assert_role,
    _get_scoped_site_or_404,
)
from backend.api.cms_v2.section_types import get_allowed_section_types
from backend.core.database import get_db
from backend.core.permissions import require_module_access
from backend.exceptions.cms import (
    BlockNotFoundError,
    CmsValidationError,
    UnsupportedSectionTypeError,
)
from backend.models_shared import _utcnow
from backend.schemas._common import PaginatedResponse
from backend.schemas.cms_v2_sections import validate_section_props

logger = logging.getLogger(__name__)

router = APIRouter(tags=["cms_v2_global_blocks"])


@router.get("/global-blocks", response_model=PaginatedResponse[schemas.CmsSectionRead])
def list_global_blocks(
    site_key: str,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_scoped_site_or_404(db, site_key, current_user)
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
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    allowed_types = get_allowed_section_types(db)
    if payload.type not in allowed_types:
        raise UnsupportedSectionTypeError()
    try:
        validated_props = validate_section_props(payload.type, payload.props_json or {})
        payload.props_json = validated_props
    except ValueError as e:
        raise CmsValidationError(str(e))
    site = _get_scoped_site_or_404(db, site_key, current_user)
    page = (
        db.query(models.CmsPage)
        .filter(
            models.CmsPage.site_id == site.id,
            models.CmsPage.slug == "_global_blocks",
        )
        .first()
    )
    if not page:
        page = models.CmsPage(
            site_id=site.id,
            slug="_global_blocks",
            title="Global Blocks",
            status="draft",
        )
        db.add(page)
        db.flush()
    payload.is_global = True
    payload.is_visible = True if payload.is_visible is None else payload.is_visible
    payload.section_key = payload.section_key or f"global_{uuid.uuid4().hex[:8]}"
    block = crud.create_cms_section(db, page.id, payload)
    db.refresh(block)
    return schemas.CmsSectionRead.model_validate(block)


@router.patch("/global-blocks/{section_id}", response_model=schemas.CmsSectionRead)
def patch_global_block(
    site_key: str,
    section_id: uuid.UUID,
    payload: schemas.CmsSectionUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    block = (
        db.query(models.CmsSection)
        .filter(
            models.CmsSection.id == section_id,
            models.CmsSection.is_global,
        )
        .first()
    )
    if not block:
        raise BlockNotFoundError()
    data = payload.model_dump(exclude_unset=True)
    for key in ["type", "props_json", "sort_order", "is_visible", "status", "is_global", "global_key"]:
        if key in data and data[key] is not None:
            setattr(block, key, data[key])
    db.commit()
    db.refresh(block)
    return schemas.CmsSectionRead.model_validate(block)


@router.delete("/global-blocks/{section_id}", status_code=204)
def delete_global_block(
    site_key: str,
    section_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    block = (
        db.query(models.CmsSection)
        .filter(
            models.CmsSection.id == section_id,
            models.CmsSection.is_global,
        )
        .first()
    )
    if not block:
        raise BlockNotFoundError()
    block.deleted_at = _utcnow()
    db.commit()
    return None
