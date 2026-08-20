"""Read-only MCP server for the published CCF public website.

This surface intentionally reuses the existing CMS public contract. It never
loads drafts, admin data, people, CRM records, or unpublished revisions.
"""

from __future__ import annotations

import uuid
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.server import Context
from mcp.server.transport_security import TransportSecuritySettings
from sqlalchemy import or_

from backend import crud, models, schemas
from backend.api.cms.public.menus import public_menu
from backend.api.cms.public.pages import public_page, public_pages_list
from backend.api.cms.public.posts import public_post, public_posts_list
from backend.api.cms.section_types import get_allowed_section_types
from backend.api.cms_v2._shared import (
    CMS_EDITOR_ROLES,
    CMS_PUBLISHER_ROLES,
    _assert_role,
    _get_page_or_404,
    _get_scoped_site_or_404,
    _slugify,
)
from backend.core.cache_v2 import _to_jsonable
from backend.core.database import SessionLocal
from backend.exceptions.cms import CmsPermissionError, SlugConflictError
from backend.mcp_auth import authenticated_mcp_app, get_mcp_current_user, require_mcp_permission
from backend.schemas.cms_v2_sections import validate_section_props
from backend.services.cms_search_indexer import delete_from_search_index, index_cms_page
from backend.services.cms_workflow import PageWorkflowService

public_mcp = FastMCP(
    name="CCF Public Content",
    instructions=(
        "Consulta únicamente el contenido publicado del sitio público CCF. "
        "No inventes información que no esté en las respuestas y no expongas "
        "datos privados, administrativos o de personas."
    ),
    streamable_http_path="/",
    stateless_http=True,
    transport_security=TransportSecuritySettings(
        allowed_hosts=[
            "ministerioselfaro.org",
            "www.ministerioselfaro.org",
            "127.0.0.1:*",
            "localhost:*",
        ],
    ),
)

cms_admin_mcp = FastMCP(
    name="CCF CMS",
    instructions=(
        "Gestiona contenido CMS de CCF mediante el JWT CCF del usuario. "
        "Respeta siempre el borrador y el workflow de publicación; no inventes "
        "tipos de sección ni publiques sin una orden explícita."
    ),
    streamable_http_path="/",
    stateless_http=True,
)
cms_admin_mcp_app = authenticated_mcp_app(cms_admin_mcp)


def _json(value: Any) -> Any:
    return _to_jsonable(value)


def _site_exists(db: Any, site_key: str) -> bool:
    return (
        db.query(models.CmsSite.id)
        .filter(
            models.CmsSite.site_key == site_key.strip().lower(),
            models.CmsSite.is_active.is_(True),
        )
        .first()
        is not None
    )


def _mcp_user(*, publisher: bool = False) -> models.User:
    """Resolve the authenticated CCF user and enforce the CMS RBAC contract."""
    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "cms:edit")
        _assert_role(user, CMS_PUBLISHER_ROLES if publisher else CMS_EDITOR_ROLES)
        # Detach the object before closing the short-lived auth session. The
        # editing operations open their own session and only need the identity.
        db.expunge(user)
        return user
    finally:
        db.close()


def _mcp_db_page(ctx: Context, site_key: str, slug: str, *, publisher: bool = False):
    user = _mcp_user(publisher=publisher)
    db = SessionLocal()
    try:
        site = _get_scoped_site_or_404(db, site_key, user)
        page = _get_page_or_404(db, site.id, slug)
        return db, site, page, user
    except Exception:
        db.close()
        raise


@public_mcp.tool()
def list_public_pages(site_key: str = "ccf", limit: int = 50) -> dict[str, Any]:
    """Lista páginas CMS publicadas del sitio público CCF."""
    safe_limit = max(1, min(int(limit), 100))
    db = SessionLocal()
    try:
        result = public_pages_list(site_key=site_key, db=db, skip=0, limit=safe_limit)
        return _json(result)
    finally:
        db.close()


@public_mcp.tool()
def get_public_page(slug: str, site_key: str = "ccf") -> dict[str, Any]:
    """Obtiene una página publicada, sus secciones, SEO y datos estructurados."""
    db = SessionLocal()
    try:
        result = public_page(site_key=site_key, slug=slug, db=db)
        return _json(result)
    finally:
        db.close()


@public_mcp.tool()
def get_public_menu(menu_key: str = "main", site_key: str = "ccf") -> dict[str, Any]:
    """Obtiene los enlaces visibles de un menú público publicado."""
    db = SessionLocal()
    try:
        result = public_menu(site_key=site_key, menu_key=menu_key, db=db)
        return _json(result)
    finally:
        db.close()


@public_mcp.tool()
def list_public_posts(site_key: str = "ccf", limit: int = 20) -> dict[str, Any]:
    """Lista publicaciones y sermones publicados del sitio CCF."""
    safe_limit = max(1, min(int(limit), 50))
    db = SessionLocal()
    try:
        result = public_posts_list(site_key=site_key, db=db, skip=0, limit=safe_limit)
        return _json(result)
    finally:
        db.close()


@public_mcp.tool()
def get_public_post(slug: str, site_key: str = "ccf") -> dict[str, Any]:
    """Obtiene una publicación o sermón publicado por su slug."""
    db = SessionLocal()
    try:
        result = public_post(site_key=site_key, slug=slug, db=db)
        return _json(result)
    finally:
        db.close()


@cms_admin_mcp.tool()
def list_manageable_pages(site_key: str = "ccf", limit: int = 100, ctx: Context | None = None) -> dict[str, Any]:
    """Lista páginas CMS de todos los estados para un editor autenticado."""
    if ctx is None:
        raise CmsPermissionError("Esta operación requiere autenticación CCF.")
    user = _mcp_user()
    safe_limit = max(1, min(int(limit), 200))
    db = SessionLocal()
    try:
        site = _get_scoped_site_or_404(db, site_key, user)
        pages, total = crud.list_cms_pages(db, site.id, skip=0, limit=safe_limit, status=None)
        return _json({"items": pages, "total": total, "site_key": site.site_key})
    finally:
        db.close()


@cms_admin_mcp.tool()
def create_public_page(
    slug: str,
    title: str,
    site_key: str = "ccf",
    seo_json: dict[str, Any] | None = None,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Crea una página CMS como borrador; nunca la publica automáticamente."""
    if ctx is None:
        raise CmsPermissionError("Esta operación requiere autenticación CCF.")
    user = _mcp_user()
    db = SessionLocal()
    try:
        site = _get_scoped_site_or_404(db, site_key, user)
        normalized_slug = _slugify(slug)
        if not normalized_slug:
            raise ValueError("El slug no puede estar vacío.")
        if crud.get_cms_page(db, site.id, normalized_slug):
            raise SlugConflictError()
        payload = schemas.CmsPageCreate(slug=normalized_slug, title=title, status="draft", seo_json=seo_json or {})
        page = crud.create_cms_page(db, site.id, payload, user.id, commit_with_conflict_check=True)
        if page is None:
            raise SlugConflictError()
        index_cms_page(db, page)
        return _json(page)
    finally:
        db.close()


@cms_admin_mcp.tool()
def update_public_page(
    slug: str,
    site_key: str = "ccf",
    new_slug: str | None = None,
    title: str | None = None,
    seo_json: dict[str, Any] | None = None,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Edita metadatos de una página sin cambiar su estado de publicación."""
    if ctx is None:
        raise CmsPermissionError("Esta operación requiere autenticación CCF.")
    db, site, page, user = _mcp_db_page(ctx, site_key, slug)
    try:
        normalized_slug = _slugify(new_slug) if new_slug is not None else None
        if normalized_slug and normalized_slug != page.slug and crud.get_cms_page(db, site.id, normalized_slug):
            raise SlugConflictError()
        payload = schemas.CmsPageUpdate(slug=normalized_slug, title=title, seo_json=seo_json)
        updated = crud.update_cms_page(db, page, payload, user.id)
        index_cms_page(db, updated)
        return _json(updated)
    finally:
        db.close()


@cms_admin_mcp.tool()
def upsert_public_page_section(
    slug: str,
    section_type: str,
    props_json: dict[str, Any],
    site_key: str = "ccf",
    section_id: str | None = None,
    sort_order: int = 0,
    is_visible: bool = True,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Crea o actualiza una sección usando el catálogo y validadores CMS."""
    if ctx is None:
        raise CmsPermissionError("Esta operación requiere autenticación CCF.")
    db, site, page, _user = _mcp_db_page(ctx, site_key, slug)
    try:
        allowed_types = get_allowed_section_types(db)
        if section_type not in allowed_types:
            raise ValueError(f"Tipo de sección no permitido: {section_type}")
        validated_props = validate_section_props(section_type, props_json or {})
        if section_id:
            row = crud.get_cms_section(db, page.id, uuid.UUID(section_id), site_id=site.id)
            if row is None:
                raise ValueError("Sección no encontrada.")
            payload = schemas.CmsSectionUpdate(
                type=section_type,
                props_json=validated_props,
                sort_order=sort_order,
                is_visible=is_visible,
            )
            row = crud.update_cms_section(db, row, payload)
        else:
            payload = schemas.CmsSectionCreate(
                type=section_type,
                props_json=validated_props,
                sort_order=sort_order,
                is_visible=is_visible,
                status="active",
            )
            row = crud.create_cms_section(db, page.id, payload, commit_with_conflict_check=True)
        if row is None:
            raise ValueError("No se pudo guardar la sección.")
        index_cms_page(db, page)
        return _json(row)
    finally:
        db.close()


@cms_admin_mcp.tool()
def publish_public_page(
    slug: str,
    action: str = "publish",
    site_key: str = "ccf",
    notes: str | None = None,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Ejecuta el workflow CMS: publicar, despublicar, archivar o volver a borrador."""
    if ctx is None:
        raise CmsPermissionError("Esta operación requiere autenticación CCF.")
    normalized_action = action.strip().lower()
    if normalized_action not in {"publish", "unpublish", "archive", "revert_draft", "submit_review", "approve"}:
        raise ValueError("Acción CMS no permitida.")
    db, site, page, user = _mcp_db_page(
        ctx,
        site_key,
        slug,
        publisher=normalized_action in {"publish", "unpublish", "archive", "approve"},
    )
    try:
        workflow = PageWorkflowService(db)
        updated = workflow.transition(page, normalized_action, user.id, notes=notes)
        if updated is None:
            raise ValueError("Transición CMS inválida para el estado actual.")
        if normalized_action in {"unpublish", "archive"} or updated.status != "published":
            delete_from_search_index(db, site_key, "page", str(updated.id))
        else:
            index_cms_page(db, updated)
        return _json(updated)
    finally:
        db.close()


@public_mcp.tool()
def search_public_content(query: str, site_key: str = "ccf", limit: int = 10) -> dict[str, Any]:
    """Busca coincidencias en títulos y contenido publicado de páginas y posts."""
    term = query.strip()
    if len(term) < 2:
        return {"items": [], "total": 0, "message": "La búsqueda requiere al menos 2 caracteres."}
    safe_limit = max(1, min(int(limit), 20))
    pattern = f"%{term}%"
    db = SessionLocal()
    try:
        site = (
            db.query(models.CmsSite)
            .filter(
                models.CmsSite.site_key == site_key.strip().lower(),
                models.CmsSite.is_active.is_(True),
            )
            .first()
        )
        if not site:
            return {"items": [], "total": 0}

        pages = (
            db.query(models.CmsPage)
            .filter(
                models.CmsPage.site_id == site.id,
                models.CmsPage.status == "published",
                or_(models.CmsPage.title.ilike(pattern), models.CmsPage.slug.ilike(pattern)),
            )
            .order_by(models.CmsPage.updated_at.desc())
            .limit(safe_limit)
            .all()
        )
        posts = (
            db.query(models.CmsPost)
            .filter(
                models.CmsPost.site_id == site.id,
                models.CmsPost.status == "published",
                or_(
                    models.CmsPost.title.ilike(pattern),
                    models.CmsPost.excerpt.ilike(pattern),
                    models.CmsPost.content.ilike(pattern),
                    models.CmsPost.slug.ilike(pattern),
                ),
            )
            .order_by(models.CmsPost.published_at.desc().nullslast())
            .limit(safe_limit)
            .all()
        )
        items = [
            {"kind": "page", "slug": page.slug, "title": page.title, "href": f"/{page.slug}"}
            for page in pages
        ] + [
            {"kind": "post", "slug": post.slug, "title": post.title, "href": f"/blog/{post.slug}"}
            for post in posts
        ]
        return {"items": items[:safe_limit], "total": len(items)}
    finally:
        db.close()
