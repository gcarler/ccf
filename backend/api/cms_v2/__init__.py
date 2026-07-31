"""
CMS v2 API — thin orchestrator (Fase 4 refactor).

Each domain has been extracted to its own submodule under ``backend/api/cms_v2/``.
This ``__init__.py`` re-exports shared helpers for backward-compatibility and
wires all sub-routers onto the main ``/cms/v2`` APIRouter.

Submodules:
  _shared        — constants, role helpers, site/menu/page lookups, system var cache
  section_types  — section type catalog CRUD + get_allowed_section_types
  global_blocks  — global blocks CRUD
  sites          — CmsSite CRUD
  themes_menus   — themes + menus + menu items CRUD
  pages          — pages + sections + SEO audit + preview + workflow + readiness
  public         — /public/sites/{site_key}/... endpoints (sitemap, posts, menus)
  pastoral       — CMS pastoral team list + profile update
  posts          — categories + tags + posts admin CRUD
  analytics_ops  — tracking, analytics, scheduling, image ops
  forms          — contact forms
  newsletter     — newsletter + subscribers
  popups         — native popups
  presence       — real-time presence
  ab_testing     — A/B testing
  post_comments  — public post comments
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException  # noqa: F401 — HTTPException re-exported

from backend.core.database import get_db  # noqa: F401
from backend.core.rate_limit import rate_limiter

logger = logging.getLogger(__name__)

# ── Main router (600 req/min; public sub-routers declare their own limits) ───
router = APIRouter(
    prefix="/cms/v2",
    tags=["cms_v2"],
    dependencies=[Depends(rate_limiter(limit=600, window_seconds=60))],
)

# ── Re-export shared helpers (backward-compat for existing call-sites) ────────
from backend.api.cms_v2._shared import (  # noqa: E402, F401
    CMS_EDITOR_ROLES, CMS_PUBLISHER_ROLES, PUBLIC_CMS_RATE_LIMIT,
    _actor_sede_from_user, _assert_role, _assert_site_sede_scope,
    _build_section_defaults, _commit_or_raise_conflict,
    _get_category_or_404, _get_main_site, _get_menu_or_404,
    _get_page_or_404, _get_post_or_404, _get_public_site_or_404,
    _get_scoped_site_or_404, _get_site_or_404, _get_system_var,
    _get_system_vars_batch, _get_tag_or_404, _is_global_admin,
    _pastoral_role, _slugify, _snapshot_section_read, _validate_canonical_category,
)
from backend.api.cms_v2.section_types import get_allowed_section_types  # noqa: E402, F401

# ── Mount sub-routers (order mirrors original file's section ordering) ────────
from backend.api.cms_v2 import (  # noqa: E402
    ab_testing as _ab, analytics_ops as _analytics, forms as _forms,
    global_blocks as _blocks, newsletter as _newsletter, pages as _pages,
    pastoral as _pastoral, popups as _popups, post_comments as _comments,
    posts as _posts, presence as _presence, public as _public,
    section_types as _section_types, sites as _sites, themes_menus as _themes,
)

for _mod in (
    _section_types, _blocks, _sites, _themes, _pages, _public,
    _pastoral, _posts, _analytics, _popups, _forms, _newsletter,
    _presence, _ab, _comments,
):
    router.include_router(_mod.router)
