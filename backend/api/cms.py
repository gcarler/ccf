from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from backend import crud, models, schemas
from backend.api._cms_helpers import (
    _actor_sede_or_none,
    _get_scoped_cms_media,
    _scope_cms_media_by_user_sede,
    collect_section_media_ids,
)
from backend.core.config import get_settings
from backend.core.database import get_db
from backend.core.permissions import require_module_access
from backend.schemas import PaginatedResponse
from backend.services.cms_media_service import (
    delete_cms_media as _delete_cms_media,
)
from backend.services.cms_media_service import (
    optimize_cms_media as _optimize_cms_media,
)
from backend.services.cms_media_service import (
    upload_cms_media as _upload_cms_media,
)

# CMS endpoints — preferir /cms/v2/* en integraciones nuevas.
router = APIRouter(tags=["cms"])
logger = logging.getLogger(__name__)

settings = get_settings()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# NOTE: v1 testimonials and announcements endpoints removed.
# The frontend was fully migrated to the v2 API.
# Legacy schemas (TestimonialRead, AnnouncementRead, etc.) were deleted.


# ── CMS Media ───────────────────────────────────────────
# Axioma 3 — Multi-Tenant: CmsMediaItem tiene sede_id propio (migration
# 2026-07-01). Endpoints admin filtran estrictamente por sede. CmsImage
# upload deriva ``sede_id`` server-side desde el current_user.
