"""CMS tools exposed through the CCF MCP server."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import Context, FastMCP
from mcp.types import ToolAnnotations

from backend import schemas
from backend.api.cms_v2 import pages, sites, themes_menus
from backend.api.cms_v2._shared import CMS_EDITOR_ROLES, CMS_PUBLISHER_ROLES
from backend.api.mcp.auth import authorized_cms_context

READ = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True)
WRITE = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False)
DESTRUCTIVE = ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=False)


def _dump(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [_dump(item) for item in value]
    if isinstance(value, dict):
        return {key: _dump(item) for key, item in value.items()}
    return value


def register_cms_tools(mcp: FastMCP) -> None:
    @mcp.tool(
        name="list_sites",
        description="Lista los sitios CMS visibles para el usuario autenticado, respetando su sede.",
        annotations=READ,
    )
    async def list_sites(ctx: Context, only_active: bool = False) -> list[dict[str, Any]]:
        async with authorized_cms_context(ctx) as (db, user):
            result = sites.list_sites(only_active=only_active, db=db, current_user=user)
            return _dump(result)

    @mcp.tool(
        name="list_pages",
        description="Lista páginas CMS de un sitio, incluyendo borradores si el usuario tiene acceso.",
        annotations=READ,
    )
    async def list_pages(
        ctx: Context,
        site_key: str,
        status: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> dict[str, Any]:
        async with authorized_cms_context(ctx) as (db, user):
            result = pages.list_pages(
                site_key=site_key,
                db=db,
                skip=skip,
                limit=limit,
                status=status,
                current_user=user,
            )
            return _dump(result)

    @mcp.tool(
        name="get_page",
        description="Obtiene una página CMS por sitio y slug, respetando el scope de sede.",
        annotations=READ,
    )
    async def get_page(ctx: Context, site_key: str, slug: str) -> dict[str, Any]:
        async with authorized_cms_context(ctx) as (db, user):
            result = pages.get_page(site_key=site_key, slug=slug, db=db, current_user=user)
            return _dump(result)

    @mcp.tool(
        name="preview_page",
        description="Genera la vista previa de una página CMS usando el contenido draft actual.",
        annotations=READ,
    )
    async def preview_page(ctx: Context, site_key: str, slug: str) -> dict[str, Any]:
        async with authorized_cms_context(ctx, allowed_roles=CMS_EDITOR_ROLES) as (db, user):
            result = pages.preview_page(site_key=site_key, slug=slug, db=db, current_user=user)
            return _dump(result)

    @mcp.tool(
        name="list_themes",
        description="Lista los temas del sitio CMS visible para el usuario.",
        annotations=READ,
    )
    async def list_themes(ctx: Context, site_key: str) -> list[dict[str, Any]]:
        async with authorized_cms_context(ctx) as (db, user):
            result = themes_menus.list_themes(site_key=site_key, db=db, current_user=user)
            return _dump(result)

    @mcp.tool(
        name="list_menus",
        description="Lista los menús del sitio CMS visible para el usuario.",
        annotations=READ,
    )
    async def list_menus(ctx: Context, site_key: str) -> list[dict[str, Any]]:
        async with authorized_cms_context(ctx) as (db, user):
            result = themes_menus.list_menus(site_key=site_key, db=db, current_user=user)
            return _dump(result)

    @mcp.tool(
        name="create_page_draft",
        description="Crea una página CMS en estado draft. Nunca publica contenido.",
        annotations=WRITE,
    )
    async def create_page_draft(
        ctx: Context,
        site_key: str,
        slug: str,
        title: str,
        seo_json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        async with authorized_cms_context(ctx, permission="cms:edit", allowed_roles=CMS_EDITOR_ROLES) as (db, user):
            payload = schemas.CmsPageCreate(slug=slug, title=title, status="draft", seo_json=seo_json or {})
            result = pages.create_page(site_key=site_key, payload=payload, db=db, current_user=user)
            return _dump(result)

    @mcp.tool(
        name="update_page_draft",
        description="Actualiza el contenido editable de una página sin cambiar su estado de publicación.",
        annotations=WRITE,
    )
    async def update_page_draft(
        ctx: Context,
        site_key: str,
        slug: str,
        title: str | None = None,
        new_slug: str | None = None,
        seo_json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        async with authorized_cms_context(ctx, permission="cms:edit", allowed_roles=CMS_EDITOR_ROLES) as (db, user):
            payload = schemas.CmsPageUpdate(slug=new_slug, title=title, seo_json=seo_json)
            result = pages.patch_page(site_key=site_key, slug=slug, payload=payload, db=db, current_user=user)
            return _dump(result)

    @mcp.tool(
        name="publish_page",
        description="Publica o despublica una página mediante el workflow CMS. Requiere rol publisher y confirmación del cliente.",
        annotations=DESTRUCTIVE,
    )
    async def publish_page(
        ctx: Context,
        site_key: str,
        slug: str,
        action: str,
        notes: str | None = None,
    ) -> dict[str, Any]:
        async with authorized_cms_context(ctx, permission="cms:edit", allowed_roles=CMS_PUBLISHER_ROLES) as (db, user):
            payload = schemas.CmsWorkflowAction(action=action, notes=notes)
            result = pages.workflow_page(site_key=site_key, slug=slug, payload=payload, db=db, current_user=user)
            return _dump(result)


__all__ = ["register_cms_tools"]
