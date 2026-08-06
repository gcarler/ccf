"""Enterprise CMS API — paquete modular por dominio.

Sustituye al monolito histórico ``backend/api/enterprise_cms.py`` (1.670
LOC, 39 endpoints, sin segmentación por dominio). Split del monolito
realizado el 2026-08-05 como cierre de la deuda estructural 🟠#4
documentada en ``docs/ESTADO_DEUDA_TECNICA_BACKEND_CMS.md``.

Router público preservado: ``enterprise_cms.router`` con
``prefix="/cms/v2"`` y ``tags=["Enterprise CMS"]``. La app continúa
montándolo en ``backend/app.py`` bajo ``/api`` sin cambios.

Distribución por dominio:

| Sub-router          | Dominio                                          |
|---------------------|--------------------------------------------------|
| audit               | list_audit_logs                                  |
| content_permissions | create/list/delete ContentPermission             |
| notifications       | list / mark read / mark all read                 |
| webhooks            | CRUD Webhook + list WebhookDelivery             |
| custom_types        | CRUD CmsCustomType                              |
| custom_entries      | CRUD CmsCustomEntry + versions + rollback        |
| glossary            | CRUD CmsGlossaryTerm                             |
| search              | execute + reindex + SearchPromotion CRUD         |
| sessions            | list / revoke / revoke-all UserSession          |
| media_folders       | CRUD MediaFolder                                 |
| redirects           | CRUD CmsRedirect + resolve-redirect + helpers    |
| broken_links        | list + resolve BrokenLinkCheck                   |

Helpers compartidos en ``__common.py``: ``require_cms_read``,
``require_cms_manage``, ``_log_audit``, ``_notify``, ``_fire_webhooks``.

Audit Trail, Content Permissions, Notifications, Webhooks, Custom Post
Types, Search, Session Management, Media Folders, Redirects, Broken Link
Check — todos los endpoints requieren autenticación. Role-based access
donde se aplique ``require_cms_manage``.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/cms/v2", tags=["Enterprise CMS"])

# ── Sub-routers por dominio ────────────────────────────────────────────────────

from backend.api.enterprise_cms import (  # noqa: E402
    audit,
    broken_links,
    content_permissions,
    custom_entries,
    custom_types,
    glossary,
    media_folders,
    notifications,
    redirects,
    search,
    sessions,
    webhooks,
)

_SUB_ROUTERS = (
    audit.router,
    content_permissions.router,
    notifications.router,
    webhooks.router,
    custom_types.router,
    custom_entries.router,
    glossary.router,
    search.router,
    sessions.router,
    media_folders.router,
    redirects.router,
    broken_links.router,
)

for sub in _SUB_ROUTERS:
    router.include_router(sub)


# ── Re-exports públicos preservados para retrocompatibilidad ───────────────────
# Tests y callers externos importaban del monolito ``enterprise_cms.py``;
# se conservan aquí para no romper contratos ya existentes.

from backend.api.enterprise_cms.redirects import resolve_redirect  # noqa: E402
from backend.api.enterprise_cms.search import execute_search  # noqa: E402

__all__ = ["router", "resolve_redirect", "execute_search"]
