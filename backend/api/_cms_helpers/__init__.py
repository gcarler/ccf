"""Axioma 3 — CMS scope helpers (package re-exports).

Re-exporta los símbolos definidos en ``_shared.py`` para permitir
``from backend.api._cms_helpers import (...)`` como estilo DRY.

NOTA sobre naming: este módulo existe como package (directorio) para
evitar un conflicto de resolución Python con ``backend/api/cms.py``
(archivo) que existía antes y se mantiene.

Las scope helpers (``_underscore_prefixed``) son internas pero se
re-exportan por consistencia con el resto del axioma 3 — son consumidas
por ``backend/api/cms_v2.py`` y los tests estruturales vía el path
público. El SEO audit exports son parte del API público del paquete.
"""

from backend.api._cms_helpers._shared import (
    # ── Multi-tenant scope helpers (internals; re-exported aquí­ por
    # consistencia con el resto del axioma 3) ──
    _actor_sede_or_none,
    _get_scoped_cms_announcement,
    _get_scoped_cms_media,
    _get_scoped_cms_testimonial,
    _get_scoped_persona,
    _scope_cms_announcements_by_user_sede,
    _scope_cms_media_by_user_sede,
    _scope_cms_pastoral_team_by_user_sede,
    _scope_cms_testimonials_by_user_sede,
    # ── SEO audit helpers (merged from seo_audit.py per Gate 6) ──
    audit_pages,
    build_media_alt_lookup,
    collect_section_media_ids,
    group_sections_by_page,
)

__all__ = (
    # ── Scope helpers (internals) ──
    "_actor_sede_or_none",
    "_get_scoped_cms_announcement",
    "_get_scoped_cms_media",
    "_get_scoped_cms_testimonial",
    "_get_scoped_persona",
    "_scope_cms_announcements_by_user_sede",
    "_scope_cms_media_by_user_sede",
    "_scope_cms_pastoral_team_by_user_sede",
    "_scope_cms_testimonials_by_user_sede",
    # ── SEO audit exports (public) ──
    "audit_pages",
    "build_media_alt_lookup",
    "collect_section_media_ids",
    "group_sections_by_page",
)
