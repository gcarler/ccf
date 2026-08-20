"""Gateway MCP común para todos los módulos de la plataforma CCF.

Los módulos que tienen una superficie especializada (CMS, Evangelismo, CRM,
Academia y Calendario) conservan sus herramientas de dominio. Los demás usan
este gateway tipado: cada módulo tiene su propio endpoint MCP, catálogo de
rutas y una herramienta de proxy REST con allowlist de prefijos. La operación
se ejecuta dentro de la aplicación usando el mismo Bearer JWT, por lo que los
guards REST, validaciones, auditoría y aislamiento por sede siguen siendo la
fuente de verdad.
"""

from __future__ import annotations

from contextlib import AsyncExitStack, asynccontextmanager
from dataclasses import dataclass
from typing import Any

import httpx
from mcp.server.auth.middleware.auth_context import auth_context_var
from mcp.server.fastmcp import FastMCP

from backend.mcp_auth import authenticated_mcp_app, get_mcp_current_user, require_mcp_permission


@dataclass(frozen=True)
class ModuleSpec:
    slug: str
    label: str
    prefixes: tuple[str, ...]
    read_permission: str | None
    write_permission: str | None
    dedicated_route: str | None = None
    read_only: bool = False


# Every functional router has a catalog entry. Prefixes are deliberately
# allowlisted instead of accepting arbitrary URLs from an MCP client.
MODULE_SPECS: tuple[ModuleSpec, ...] = (
    ModuleSpec("auth", "Autenticación y sesiones", ("/api/v3/auth/me", "/api/v3/auth/sessions"), "profile:manage", "profile:manage"),
    ModuleSpec("projects", "Proyectos y tareas", ("/api/projects",), "projects:read", "projects:edit"),
    ModuleSpec("kernel", "Identidad y vida ministerial", ("/api/kernel",), "profile:manage", "system:config"),
    ModuleSpec("public", "Servicios públicos", ("/api/public",), "profile:manage", None, read_only=True),
    ModuleSpec("workspace", "Workspace y configuración", ("/api/workspace",), "profile:manage", "system:config"),
    ModuleSpec("system", "Sistema y operación", ("/api/system",), "system:config", "system:config"),
    ModuleSpec("agents", "Agentes y conocimiento", ("/api/agents",), "system:config", "system:config"),
    ModuleSpec("admin", "Administración", ("/api/admin",), "system:config", "system:config"),
    ModuleSpec("finance", "Finanzas y donaciones", ("/api/finance",), "finance:read", "finance:edit"),
    ModuleSpec("finance-suite", "Suite financiera", ("/api/finance-suite",), "finance:read", "finance:manage"),
    ModuleSpec("donations", "Donaciones", ("/api/donations",), "finance:read", "finance:edit"),
    ModuleSpec("governance", "Gobernanza y auditoría", ("/api/governance",), "system:config", "system:config"),
    ModuleSpec("chat", "Chat", ("/api/chat",), "messaging:read", "messaging:edit"),
    ModuleSpec("messaging", "Mensajería", ("/api/messaging",), "messaging:read", "messaging:edit"),
    ModuleSpec("support", "Soporte", ("/api/support",), "support:read", "support:edit"),
    ModuleSpec("support-kb", "Base de conocimiento de soporte", ("/api/support/kb",), "support:read", None, read_only=True),
    ModuleSpec("spiritual-life", "Vida espiritual", ("/api/spiritual-life",), "spiritual_life:read", "spiritual_life:edit"),
    ModuleSpec("graph", "Grafo de conocimiento", ("/api/graph",), "analytics:read", None, read_only=True),
    ModuleSpec("community", "Comunidad", ("/api/community",), "community:read", "community:edit"),
    ModuleSpec("prayer", "Oración", ("/api/prayer",), "spiritual_life:read", "spiritual_life:edit"),
    ModuleSpec("analytics", "Analítica", ("/api/analytics",), "analytics:read", "analytics:manage"),
    ModuleSpec("dashboard", "Dashboards", ("/api/dashboard",), "dashboard:read", "dashboard:manage"),
    ModuleSpec("tables", "Vistas y tablas", ("/api/tables",), "system:config", "system:config"),
    ModuleSpec("youtube", "YouTube", ("/api/youtube",), "cms:read", "cms:edit"),
    ModuleSpec("enterprise-cms", "Enterprise CMS", ("/api/cms/v2",), "cms:read", "cms:edit"),
    ModuleSpec("wiki", "Wiki", ("/api/wiki",), "wiki:read", "wiki:edit"),
    ModuleSpec("comments", "Comentarios transversales", ("/api/comments",), "community:read", "community:edit"),
    # Dedicated domain MCPs are included in the same catalog for discovery.
    ModuleSpec("cms", "CMS editorial", ("/api/cms",), "cms:read", "cms:edit", dedicated_route="/mcp/cms"),
    ModuleSpec("evangelism", "Evangelismo", ("/api/evangelism",), "evangelism:read", "evangelism:edit", dedicated_route="/mcp/evangelism"),
    ModuleSpec("crm", "CRM", ("/api/crm",), "crm:read", "crm:edit", dedicated_route="/mcp/crm"),
    ModuleSpec("academy", "Academia", ("/api/academy",), "academy:read", "academy:edit", dedicated_route="/mcp/academy"),
    ModuleSpec("calendar", "Calendario", ("/api/agenda",), "spiritual_life:read", "spiritual_life:edit", dedicated_route="/mcp/calendar"),
)

MODULE_BY_SLUG = {spec.slug: spec for spec in MODULE_SPECS}
DEDICATED_MODULES = {spec.slug for spec in MODULE_SPECS if spec.dedicated_route}


platform_mcp = FastMCP(
    name="CCF Plataforma",
    instructions=(
        "Descubre los módulos MCP de CCF. Cada módulo usa su endpoint REST "
        "canónico, JWT Auth v3, permisos RBAC y aislamiento por sede. Nunca "
        "inventes rutas ni envíes sede_id para intentar cambiar de tenant."
    ),
    streamable_http_path="/",
    stateless_http=True,
)


@platform_mcp.tool()
def list_platform_modules() -> dict[str, Any]:
    """Devuelve el catálogo completo de módulos MCP de CCF."""
    return {
        "items": [
            {
                "slug": spec.slug,
                "label": spec.label,
                "route": spec.dedicated_route or f"/mcp/{spec.slug}",
                "transport": "streamable-http",
                "authentication": "Bearer JWT Auth v3",
                "read_permission": spec.read_permission,
                "write_permission": spec.write_permission,
                "read_only": spec.read_only,
                "dedicated_tools": bool(spec.dedicated_route),
            }
            for spec in MODULE_SPECS
        ],
        "count": len(MODULE_SPECS),
    }


@platform_mcp.tool()
def get_platform_module(module: str) -> dict[str, Any]:
    """Obtiene capacidades y ruta MCP de un módulo concreto."""
    spec = MODULE_BY_SLUG.get(module.strip().lower())
    if spec is None:
        raise ValueError("Módulo MCP no encontrado")
    return {
        "slug": spec.slug,
        "label": spec.label,
        "route": spec.dedicated_route or f"/mcp/{spec.slug}",
        "api_prefixes": list(spec.prefixes),
        "read_permission": spec.read_permission,
        "write_permission": spec.write_permission,
        "read_only": spec.read_only,
        "dedicated_tools": bool(spec.dedicated_route),
    }


platform_mcp_app = authenticated_mcp_app(platform_mcp)


def _token_from_context() -> str:
    authenticated = auth_context_var.get()
    access_token = getattr(authenticated, "access_token", None)
    token = getattr(access_token, "token", None)
    if not token:
        raise PermissionError("Se requiere autenticación Bearer para este MCP")
    return str(token)


def _normalize_path(path: str) -> str:
    normalized = "/" + str(path or "").strip().lstrip("/")
    if "?" in normalized or "#" in normalized:
        raise ValueError("Use query para parámetros; path no puede incluir ? ni #")
    if ".." in normalized.split("/"):
        raise ValueError("Ruta inválida")
    return normalized.rstrip("/") or "/"


def _is_allowed_path(spec: ModuleSpec, path: str) -> bool:
    return any(path == prefix or path.startswith(prefix + "/") for prefix in spec.prefixes)


def _safe_response(response: httpx.Response) -> dict[str, Any]:
    if len(response.content) > 4 * 1024 * 1024:
        raise ValueError("La respuesta excede el límite MCP de 4 MB")
    content_type = response.headers.get("content-type", "")
    if "json" in content_type:
        try:
            data = response.json()
        except ValueError:
            data = response.text[:10000]
    else:
        data = response.text[:10000]
    return {
        "status_code": response.status_code,
        "ok": response.is_success,
        "data": data,
    }


def _build_module_server(spec: ModuleSpec) -> tuple[FastMCP, Any]:
    server = FastMCP(
        name=f"CCF {spec.label}",
        instructions=(
            f"MCP del módulo {spec.label}. Usa la herramienta de API únicamente "
            "con rutas allowlisted del módulo. El backend aplica JWT, RBAC, "
            "validación y sede; no intentes modificar esos límites."
        ),
        streamable_http_path="/",
        stateless_http=True,
    )

    @server.tool()
    def module_info() -> dict[str, Any]:
        """Describe el contrato MCP de este módulo."""
        return get_platform_module(spec.slug)

    @server.tool()
    def list_module_routes() -> dict[str, Any]:
        """Lista los prefijos REST que este MCP puede invocar."""
        return {
            "module": spec.slug,
            "prefixes": list(spec.prefixes),
            "allowed_methods": ["GET", "HEAD"] if spec.read_only else ["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE"],
            "read_permission": spec.read_permission,
            "write_permission": spec.write_permission,
        }

    @server.tool()
    async def module_api_request(
        method: str,
        path: str,
        query: dict[str, Any] | None = None,
        body: dict[str, Any] | list[Any] | None = None,
    ) -> dict[str, Any]:
        """Invoca un endpoint REST allowlisted del módulo con el JWT actual.

        GET/HEAD requieren permiso de lectura; POST/PUT/PATCH/DELETE requieren
        permiso de escritura. La sede y la identidad nunca son argumentos
        confiables del MCP: las vuelve a resolver la API canónica.
        """
        normalized_method = str(method or "").upper()
        if normalized_method not in {"GET", "HEAD", "POST", "PUT", "PATCH", "DELETE"}:
            raise ValueError("Método no permitido por MCP")
        if spec.read_only and normalized_method not in {"GET", "HEAD"}:
            raise PermissionError("Este módulo MCP es de solo lectura")
        normalized_path = _normalize_path(path)
        if not _is_allowed_path(spec, normalized_path):
            raise PermissionError("La ruta no pertenece al módulo MCP solicitado")
        # Never expose credential issuance, token rotation, webhooks or sockets
        # through a generic proxy. Those flows need dedicated contracts.
        blocked_fragments = ("/login", "/refresh", "/logout", "/forgot-password", "/reset-password", "/webhook", "/ws")
        if any(fragment in normalized_path for fragment in blocked_fragments):
            raise PermissionError("Esta operación requiere un contrato MCP especializado")

        db_user = None
        from backend.core.database import SessionLocal

        db = SessionLocal()
        try:
            db_user = get_mcp_current_user(db)
            permission = spec.read_permission if normalized_method in {"GET", "HEAD"} else spec.write_permission
            if permission is None:
                raise PermissionError("Este módulo no expone esa operación")
            require_mcp_permission(db, db_user, permission)
        finally:
            db.close()

        from backend.app import app

        headers = {"Authorization": f"Bearer {_token_from_context()}"}
        params = query or {}
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://ccf-mcp.internal",
            follow_redirects=False,
        ) as client:
            response = await client.request(
                normalized_method,
                normalized_path,
                params=params,
                json=body if normalized_method not in {"GET", "HEAD"} else None,
                headers=headers,
            )
        return _safe_response(response)

    return server, authenticated_mcp_app(server)


GENERIC_MODULE_SERVERS: dict[str, tuple[FastMCP, Any]] = {
    spec.slug: _build_module_server(spec)
    for spec in MODULE_SPECS
    if spec.slug not in DEDICATED_MODULES
}


def all_mcp_servers() -> list[FastMCP]:
    """Retorna todos los servidores, incluidos los dedicados, para lifecycle."""
    from backend.mcp_academy import academy_mcp
    from backend.mcp_agenda import agenda_mcp
    from backend.mcp_crm import crm_mcp
    from backend.mcp_evangelism import mass_event_mcp
    from backend.mcp_public import cms_admin_mcp, public_mcp

    return [platform_mcp, public_mcp, cms_admin_mcp, mass_event_mcp, crm_mcp, academy_mcp, agenda_mcp] + [
        server for server, _app in GENERIC_MODULE_SERVERS.values()
    ]


@asynccontextmanager
async def run_all_mcp_sessions():
    """Context manager usado por el lifecycle principal para todos los MCP."""
    stack = AsyncExitStack()
    await stack.__aenter__()
    try:
        for server in all_mcp_servers():
            await stack.enter_async_context(server.session_manager.run())
        yield
    finally:
        await stack.__aexit__(None, None, None)
