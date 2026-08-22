"""MCP dedicado para la gestión de contenidos CMS de CCF.

Permite listar, consultar, crear, editar, publicar y archivar publicaciones,
páginas y taxonomías editoriales con aislamiento por sitio y sede.
"""

from __future__ import annotations

import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from mcp.server.fastmcp import FastMCP

from backend import models, schemas
from backend.core.database import SessionLocal
from backend.crud.cms import pages as crud_pages
from backend.crud.cms import posts as crud_posts
from backend.crud.cms import sites as crud_sites
from backend.mcp_auth import authenticated_mcp_app, get_mcp_current_user, require_mcp_permission

cms_mcp = FastMCP(
    name="CCF CMS",
    instructions=(
        "Gestiona publicaciones, páginas y categorías del CMS editorial de CCF. "
        "Requiere permisos de CMS (cms:read para consulta, cms:edit/cms:manage para mutaciones) "
        "y respeta los estados de borrador, publicación y archivo."
    ),
    streamable_http_path="/",
    stateless_http=True,
)


def _resolve_site(db, site_key: str = "ccf") -> models.CmsSite:
    site = crud_sites.get_cms_site_by_key(db, site_key.strip().lower())
    if not site:
        # Fallback to first active site if default key not matched
        site = db.query(models.CmsSite).filter(models.CmsSite.is_active.is_(True)).first()
    if not site:
        raise ValueError(f"Sitio CMS '{site_key}' no encontrado")
    return site


def _safe_post(post: models.CmsPost) -> Dict[str, Any]:
    return {
        "id": str(post.id),
        "site_id": str(post.site_id),
        "slug": post.slug,
        "title": post.title,
        "excerpt": post.excerpt,
        "content": post.content,
        "featured_image_url": post.featured_image_url,
        "status": post.status,
        "published_at": post.published_at.isoformat() if post.published_at else None,
        "created_at": post.created_at.isoformat() if post.created_at else None,
        "updated_at": post.updated_at.isoformat() if post.updated_at else None,
    }


def _safe_page(page: models.CmsPage) -> Dict[str, Any]:
    return {
        "id": str(page.id),
        "site_id": str(page.site_id),
        "slug": page.slug,
        "title": page.title,
        "status": page.status,
        "seo_json": page.seo_json or {},
        "created_at": page.created_at.isoformat() if page.created_at else None,
        "updated_at": page.updated_at.isoformat() if page.updated_at else None,
    }


@cms_mcp.tool()
def list_cms_posts(
    site_key: str = "ccf",
    limit: int = 50,
    offset: int = 0,
    status: Optional[str] = None,
    category_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Lista artículos y publicaciones del blog/noticias CMS."""
    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "cms:read")
        site = _resolve_site(db, site_key)
        cat_uuid = UUID(category_id) if category_id else None
        posts, total = crud_posts.list_cms_posts(
            db,
            site_id=site.id,
            skip=max(0, int(offset)),
            limit=max(1, min(int(limit), 200)),
            status=status,
            category_id=cat_uuid,
        )
        return {
            "items": [_safe_post(p) for p in posts],
            "total": total,
            "site_key": site.site_key,
        }
    finally:
        db.close()


@cms_mcp.tool()
def get_cms_post(slug: str, site_key: str = "ccf") -> Dict[str, Any]:
    """Obtiene una publicación específica por slug."""
    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "cms:read")
        site = _resolve_site(db, site_key)
        post = crud_posts.get_cms_post(db, site_id=site.id, slug=slug.strip().lower())
        if not post:
            raise ValueError(f"Publicación con slug '{slug}' no encontrada")
        return _safe_post(post)
    finally:
        db.close()


@cms_mcp.tool()
def create_cms_post(
    title: str,
    slug: str,
    content: str,
    excerpt: Optional[str] = None,
    site_key: str = "ccf",
    status: str = "draft",
    featured_image_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Crea una nueva publicación en estado borrador o publicado."""
    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "cms:edit")
        site = _resolve_site(db, site_key)
        payload = schemas.CmsPostCreate(
            title=title.strip(),
            slug=slug.strip().lower(),
            content=content,
            excerpt=excerpt,
            status=status,
            featured_image_url=featured_image_url,
            published_at=datetime.datetime.now(datetime.timezone.utc) if status == "published" else None,
        )
        post = crud_posts.create_cms_post(db, site.id, payload, user.id, actor_user_id=user.id)
        return _safe_post(post)
    finally:
        db.close()


@cms_mcp.tool()
def update_cms_post(
    slug: str,
    changes: Dict[str, Any],
    site_key: str = "ccf",
) -> Dict[str, Any]:
    """Actualiza una publicación existente (título, contenido, estado, extracto)."""
    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "cms:edit")
        site = _resolve_site(db, site_key)
        post = crud_posts.get_cms_post(db, site_id=site.id, slug=slug.strip().lower())
        if not post:
            raise ValueError(f"Publicación con slug '{slug}' no encontrada")
        payload = schemas.CmsPostUpdate(**changes)
        updated = crud_posts.update_cms_post(db, post, payload, user.id, actor_user_id=user.id)
        return _safe_post(updated)
    finally:
        db.close()


@cms_mcp.tool()
def delete_cms_post(slug: str, site_key: str = "ccf") -> Dict[str, Any]:
    """Archiva lógicamente una publicación CMS."""
    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "cms:edit")
        site = _resolve_site(db, site_key)
        post = crud_posts.get_cms_post(db, site_id=site.id, slug=slug.strip().lower())
        if not post:
            raise ValueError(f"Publicación con slug '{slug}' no encontrada")
        crud_posts.delete_cms_post(db, post, actor_user_id=user.id)
        return {"status": "archived", "slug": slug}
    finally:
        db.close()


@cms_mcp.tool()
def publish_cms_post(slug: str, site_key: str = "ccf") -> Dict[str, Any]:
    """Publica inmediatamente una publicación que estaba en borrador."""
    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "cms:edit")
        site = _resolve_site(db, site_key)
        post = crud_posts.get_cms_post(db, site_id=site.id, slug=slug.strip().lower())
        if not post:
            raise ValueError(f"Publicación con slug '{slug}' no encontrada")
        payload = schemas.CmsPostUpdate(
            status="published",
            published_at=datetime.datetime.now(datetime.timezone.utc),
        )
        updated = crud_posts.update_cms_post(db, post, payload, user.id, actor_user_id=user.id)
        return _safe_post(updated)
    finally:
        db.close()


@cms_mcp.tool()
def list_cms_categories(site_key: str = "ccf") -> Dict[str, Any]:
    """Lista las categorías de contenido editorial del sitio CMS."""
    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "cms:read")
        site = _resolve_site(db, site_key)
        categories = (
            db.query(models.CmsCategory)
            .filter(models.CmsCategory.site_id == site.id)
            .order_by(models.CmsCategory.name.asc())
            .all()
        )
        return {
            "items": [
                {
                    "id": str(c.id),
                    "name": c.name,
                    "slug": c.slug,
                    "description": c.description,
                }
                for c in categories
            ],
            "total": len(categories),
        }
    finally:
        db.close()


@cms_mcp.tool()
def list_cms_pages(
    site_key: str = "ccf",
    limit: int = 50,
    offset: int = 0,
) -> Dict[str, Any]:
    """Lista páginas estáticas y dinámicas del CMS."""
    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "cms:read")
        site = _resolve_site(db, site_key)
        pages, total = crud_pages.list_cms_pages(
            db,
            site.id,
            skip=max(0, int(offset)),
            limit=max(1, min(int(limit), 200)),
        )
        return {
            "items": [_safe_page(p) for p in pages],
            "total": total,
            "site_key": site.site_key,
        }
    finally:
        db.close()


@cms_mcp.tool()
def get_cms_page(slug: str, site_key: str = "ccf") -> Dict[str, Any]:
    """Obtiene una página CMS por su slug."""
    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "cms:read")
        site = _resolve_site(db, site_key)
        page = crud_pages.get_cms_page(db, site.id, slug.strip().lower())
        if not page:
            raise ValueError(f"Página CMS con slug '{slug}' no encontrada")
        return _safe_page(page)
    finally:
        db.close()


@cms_mcp.tool()
def create_cms_page(
    slug: str,
    title: str,
    site_key: str = "ccf",
    seo_json: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Crea una nueva página CMS en borrador."""
    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "cms:edit")
        site = _resolve_site(db, site_key)
        payload = schemas.CmsPageCreate(
            slug=slug.strip().lower(),
            title=title.strip(),
            status="draft",
            seo_json=seo_json or {},
        )
        page = crud_pages.create_cms_page(db, site.id, payload, user.id, commit_with_conflict_check=True)
        return _safe_page(page)
    finally:
        db.close()


cms_mcp_app = authenticated_mcp_app(cms_mcp)


def create_cms_mcp_app():
    return cms_mcp_app
