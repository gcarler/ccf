"""Page workflow service and state transition endpoints (Fase 4 refactor).

PageWorkflowService encapsula la máquina de estados del CMS (draft -> in_review -> published/scheduled -> archived).
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend import models, schemas
from backend.api.cms_v2._shared import (
    CMS_EDITOR_ROLES,
    CMS_PUBLISHER_ROLES,
    _assert_role,
    _get_page_or_404,
    _get_scoped_site_or_404,
)
from backend.core.database import get_db
from backend.core.permissions import require_module_access
from backend.exceptions.cms import (
    InvalidWorkflowActionError,
    VersionNotFoundError,
)
from backend.services.cms_search_indexer import delete_from_search_index, index_cms_page
from backend.services.cms_workflow import PageWorkflowService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["cms_v2_workflow"])


@router.post("/sites/{site_key}/pages/{slug}/rollback/{version_id}", response_model=schemas.CmsPageRead)
def rollback_page(
    site_key: str,
    slug: str,
    version_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_PUBLISHER_ROLES)
    site = _get_scoped_site_or_404(db, site_key, current_user)
    page = _get_page_or_404(db, site.id, slug)
    wf = PageWorkflowService(db)
    result = wf.rollback(page, version_id, user_id=current_user.id)
    if not result:
        raise VersionNotFoundError()
    index_cms_page(db, result)
    return result


@router.post("/sites/{site_key}/pages/{slug}/workflow", response_model=schemas.CmsPageRead)
def workflow_page(
    site_key: str,
    slug: str,
    payload: schemas.CmsWorkflowAction,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    action = payload.action.strip().lower()
    wf = PageWorkflowService(db)
    if wf.requires_publisher_role(action):
        _assert_role(current_user, CMS_PUBLISHER_ROLES)
    else:
        _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_scoped_site_or_404(db, site_key, current_user)
    page = _get_page_or_404(db, site.id, slug)
    row = wf.transition(page, action, current_user.id, notes=payload.notes)
    if not row:
        raise InvalidWorkflowActionError()
    if action in {"unpublish", "archive"} or row.status != "published":
        delete_from_search_index(db, site_key, "page", str(row.id))
    else:
        index_cms_page(db, row)
    return row
