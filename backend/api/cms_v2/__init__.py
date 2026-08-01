"""
CMS v2 API — thin orchestrator (Fase 4 refactor).

Wires all specialized CMS sub-routers onto the main ``/cms/v2`` APIRouter.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException  # noqa: F401

from backend.api.cms import (
    section_types as _section_types,
)
from backend.api.cms import (
    seo as _seo,
)
from backend.api.cms import (
    workflow as _workflow,
)
from backend.api.cms.admin import (
    menus as _admin_menus,
)
from backend.api.cms.admin import (
    pages as _admin_pages,
)
from backend.api.cms.admin import (
    sites as _admin_sites,
)
from backend.api.cms.admin import (
    themes as _admin_themes,
)
from backend.api.cms.public import (
    menus as _public_menus,
)
from backend.api.cms.public import (
    pages as _public_pages,
)
from backend.api.cms.public import (
    pastoral as _public_pastoral,
)
from backend.api.cms.public import (
    posts as _public_posts,
)
from backend.api.cms.public import (
    themes as _public_themes,
)
from backend.api.cms.section_types import get_allowed_section_types  # noqa: E402, F401
from backend.api.cms_v2 import (  # noqa: E402
    ab_testing as _ab,
)
from backend.api.cms_v2 import (
    analytics_ops as _analytics,
)
from backend.api.cms_v2 import (
    forms as _forms,
)
from backend.api.cms_v2 import (
    global_blocks as _blocks,
)
from backend.api.cms_v2 import (
    newsletter as _newsletter,
)
from backend.api.cms_v2 import (
    pastoral as _pastoral,
)
from backend.api.cms_v2 import (
    popups as _popups,
)
from backend.api.cms_v2 import (
    post_comments as _comments,
)
from backend.api.cms_v2 import (
    posts as _posts,
)
from backend.api.cms_v2 import (
    presence as _presence,
)
from backend.api.cms_v2._shared import (  # noqa: E402, F401
    CMS_EDITOR_ROLES,
    CMS_PUBLISHER_ROLES,
    PUBLIC_CMS_RATE_LIMIT,
    _actor_sede_from_user,
    _assert_role,
    _assert_site_sede_scope,
    _build_section_defaults,
    _commit_or_raise_conflict,
    _get_category_or_404,
    _get_main_site,
    _get_menu_or_404,
    _get_page_or_404,
    _get_post_or_404,
    _get_public_site_or_404,
    _get_scoped_site_or_404,
    _get_site_or_404,
    _get_system_var,
    _get_system_vars_batch,
    _get_tag_or_404,
    _is_global_admin,
    _pastoral_role,
    _slugify,
    _snapshot_section_read,
    _validate_canonical_category,
)
from backend.core.database import get_db  # noqa: F401
from backend.core.rate_limit import rate_limiter

logger = logging.getLogger(__name__)

# ── Main router (600 req/min; public sub-routers declare their own limits) ───
router = APIRouter(
    prefix="/cms/v2",
    tags=["cms_v2"],
    dependencies=[Depends(rate_limiter(limit=600, window_seconds=60))],
)

# ── Mount sub-routers ────────────────────────────────────────────────────────
SUBROUTERS = (
    _section_types,
    _blocks,
    _admin_sites,
    _admin_themes,
    _admin_menus,
    _admin_pages,
    _public_pages,
    _public_menus,
    _public_posts,
    _seo,
    _workflow,
    _pastoral,
    _posts,
    _analytics,
    _popups,
    _forms,
    _newsletter,
    _presence,
    _ab,
    _comments,
    _public_themes,
    _public_pastoral,
)

for _mod in SUBROUTERS:
    router.include_router(_mod.router)
