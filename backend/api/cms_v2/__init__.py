"""
CMS v2 API — thin orchestrator (Fase 4 refactor).

Each domain has been extracted to its own module; this ``__init__.py``
re-exports shared helpers for backward-compatibility and wires sub-routers
via ``include_router``.

Modules:
  - ``_shared`` — constants, role helpers, site/menu/page lookups, system var cache
  - ``section_types`` — section type catalog CRUD + ``get_allowed_section_types``
  - ``global_blocks`` — global blocks CRUD
  - ``sites`` — sites CRUD
  - ``themes_menus`` — themes + menus + menu items CRUD
  - ``pages`` — pages + sections + SEO audit + preview + workflow + readiness
  - ``public`` — all ``/public/sites/{site_key}/...`` endpoints
  - ``pastoral`` — CMS pastoral team list + profile update
  - ``posts`` — categories + tags + posts admin CRUD + posts-by-category
  - ``analytics_ops`` — tracking, analytics, scheduling, image ops
"""
from __future__ import annotations

import logging

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,  # noqa: F401 — re-export in case callers import from here
)

from backend.core.database import get_db
from backend.core.rate_limit import rate_limiter

logger = logging.getLogger(__name__)

# ── Main router ──────────────────────────────────────────────────────────────
#
# All admin endpoints under ``/cms/v2`` are subject to a default rate limit of
# 600 req/min. Public endpoints (under ``/public/sites/...``) declare their own
# stricter limits.

router = APIRouter(
    prefix="/cms/v2",
    tags=["cms_v2"],
    dependencies=[Depends(rate_limiter(limit=600, window_seconds=60))],
)

# ── Re-export shared helpers for backward compatibility ─────────────────────
# Existing call-sites (``cms_v2._assert_role``) and test imports
# (``from backend.api.cms_v2 import _commit_or_raise_conflict``) keep working.

# ── Mount sub-routers ────────────────────────────────────────────────────────
# Each sub-module declares its own APIRouter() with no prefix (routes are
# relative to the parent's ``/cms/v2`` prefix). The order below mimics the
# original file's section ordering.
from backend.api.cms_v2 import section_types as _section_types_mod  # noqa: E402
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
from backend.api.cms_v2.section_types import get_allowed_section_types  # noqa: E402, F401

router.include_router(_section_types_mod.router)

from backend.api.cms_v2 import global_blocks as _global_blocks_mod  # noqa: E402

router.include_router(_global_blocks_mod.router)

from backend.api.cms_v2 import sites as _sites_mod  # noqa: E402

router.include_router(_sites_mod.router)

from backend.api.cms_v2 import themes_menus as _themes_menus_mod  # noqa: E402

router.include_router(_themes_menus_mod.router)

from backend.api.cms_v2 import pages as _pages_mod  # noqa: E402

router.include_router(_pages_mod.router)

from backend.api.cms_v2 import public as _public_mod  # noqa: E402

router.include_router(_public_mod.router)

from backend.api.cms_v2 import pastoral as _pastoral_mod  # noqa: E402

router.include_router(_pastoral_mod.router)

from backend.api.cms_v2 import posts as _posts_mod  # noqa: E402

router.include_router(_posts_mod.router)

from backend.api.cms_v2 import analytics_ops as _analytics_ops_mod  # noqa: E402

router.include_router(_analytics_ops_mod.router)
