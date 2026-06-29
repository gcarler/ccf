"""Axioma 3 — CMS scope helpers (package re-exports).

Re-exporta los símbolos definidos en ``_shared.py`` para permitir
``from backend.api._cms_helpers import (...)`` como estilo DRY.

NOTA sobre naming: este módulo existe como package (directorio) para
evitar un conflicto de resolución Python con ``backend/api/cms.py``
(archivo) que existía antes y se mantiene.
"""

from backend.api._cms_helpers._shared import (
    _actor_sede_or_none,
    _get_scoped_cms_announcement,
    _get_scoped_cms_media,
    _get_scoped_cms_testimonial,
    _get_scoped_persona,
    _scope_cms_announcements_by_user_sede,
    _scope_cms_media_by_user_sede,
    _scope_cms_pastoral_team_by_user_sede,
    _scope_cms_testimonials_by_user_sede,
)

__all__ = (
    "_actor_sede_or_none",
    "_get_scoped_cms_announcement",
    "_get_scoped_cms_media",
    "_get_scoped_cms_testimonial",
    "_get_scoped_persona",
    "_scope_cms_announcements_by_user_sede",
    "_scope_cms_media_by_user_sede",
    "_scope_cms_pastoral_team_by_user_sede",
    "_scope_cms_testimonials_by_user_sede",
)
