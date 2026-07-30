"""Public CMS endpoints (Fase 4 refactor).

All ``/public/sites/{site_key}/...`` endpoints plus the pastoral team
endpoints that serve the public frontend. No auth — only rate-limited.
"""
from __future__ import annotations

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session, lazyload

from backend import crud, models, schemas
from backend.api.cms_v2._shared import (
    PUBLIC_CMS_RATE_LIMIT,
    _build_section_defaults,
    _get_menu_or_404,
    _get_public_site_or_404,
    _get_system_var,
    _pastoral_role,
    _slugify,
    _snapshot_section_read,
)
from backend.core.cache_v2 import cached_public
from backend.core.config import get_settings
from backend.core.database import get_db
from backend.core.rate_limit import rate_limiter
from backend.core.seo import (
    auto_json_ld_for_page,
    build_breadcrumb_items_from_slug,
    build_breadcrumb_list_json_ld,
    build_robots_txt,
    build_sitemap_xml,
)
from backend.schemas._common import PaginatedResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["cms_v2_public"])


# ── Public Theme & Menu ──────────────────────────────────────────────────────


@router.get(
    "/public/sites/{site_key}/theme",
    response_model=schemas.CmsThemeRead,
    dependencies=[Depends(rate_limiter(limit=PUBLIC_CMS_RATE_LIMIT, window_seconds=60))],
)
@cached_public(ttl=300)
def public_theme(site_key: str, db: Session = Depends(get_db)):
    site = _get_public_site_or_404(db, site_key)
    row = (
        db.query(models.CmsTheme)
        .options(lazyload("*"))
        .filter(models.CmsTheme.site_id == site.id, models.CmsTheme.is_active.is_(True), models.CmsTheme.status != "archived")
        .order_by(models.CmsTheme.updated_at.desc()).first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="active theme not found")
    return schemas.CmsThemeRead.model_validate(row)


@router.get(
    "/public/sites/{site_key}/menus/{menu_key}",
    dependencies=[Depends(rate_limiter(limit=PUBLIC_CMS_RATE_LIMIT, window_seconds=60))],
)
@cached_public(ttl=300)
def public_menu(site_key: str, menu_key: str, db: Session = Depends(get_db)):
    site = _get_public_site_or_404(db, site_key)
    menu = _get_menu_or_404(db, site.id, menu_key)
    if not menu.is_active:
        raise HTTPException(status_code=404, detail="menu not found")
    all_items = (
        db.query(models.CmsMenuItem)
        .options(lazyload("*"))
        .filter(models.CmsMenuItem.menu_id == menu.id)
        .order_by(models.CmsMenuItem.sort_order.asc(), models.CmsMenuItem.id.asc()).all()
    )
    public_ids = {item.id for item in all_items if item.visibility == "public"}
    items = [item for item in all_items if item.visibility == "public" and (item.parent_id is None or item.parent_id in public_ids)]
    visible_ids = {item.id for item in items}
    serialized = [
        {"id": item.id, "parent_id": item.parent_id if item.parent_id in visible_ids else None,
         "label": item.label, "href": item.href, "target": item.target,
         "is_external": item.is_external, "visibility": item.visibility,
         "sort_order": item.sort_order, "meta_json": item.meta_json or {}}
        for item in items
    ]
    return {"site_key": site.site_key, "menu_key": menu.menu_key, "items": serialized}


# ── Public Pages ─────────────────────────────────────────────────────────────


@router.get(
    "/public/sites/{site_key}/pages",
    response_model=PaginatedResponse[schemas.CmsPageRead],
    dependencies=[Depends(rate_limiter(limit=PUBLIC_CMS_RATE_LIMIT, window_seconds=60))],
)
@cached_public(ttl=300)
def public_pages_list(
    site_key: str,
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=500),
):
    site = _get_public_site_or_404(db, site_key)
    query = db.query(models.CmsPage).options(lazyload("*")).filter(models.CmsPage.site_id == site.id, models.CmsPage.status == "published")
    total = query.count()
    pages = query.order_by(models.CmsPage.updated_at.desc()).offset(skip).limit(limit).all()
    return PaginatedResponse[schemas.CmsPageRead](items=pages, total=total, skip=skip, limit=limit)


@router.get(
    "/public/sites/{site_key}/pages/{slug}",
    response_model=schemas.CmsPublicPageRead,
    dependencies=[Depends(rate_limiter(limit=PUBLIC_CMS_RATE_LIMIT, window_seconds=60))],
)
@cached_public(ttl=300)
def public_page(site_key: str, slug: str, db: Session = Depends(get_db)):
    site = _get_public_site_or_404(db, site_key)
    page = (
        db.query(models.CmsPage).options(lazyload("*"))
        .filter(models.CmsPage.site_id == site.id, models.CmsPage.slug == _slugify(slug), models.CmsPage.status == "published")
        .first()
    )
    if not page:
        raise HTTPException(status_code=404, detail="published page not found")

    published_version = None
    if page.published_version_id:
        published_version = db.query(models.CmsPageVersion).options(lazyload("*")).filter(models.CmsPageVersion.page_id == page.id, models.CmsPageVersion.id == page.published_version_id).first()

    settings = get_settings()
    base_url = settings.frontend_url.rstrip("/")

    if published_version:
        snapshot = published_version.snapshot_json or {}
        page_snapshot = snapshot.get("page") if isinstance(snapshot, dict) else {}
        sections_snapshot = snapshot.get("sections") if isinstance(snapshot, dict) else []
        section_rows = [
            _snapshot_section_read(section_data, page_id=page.id, index=index, timestamp=published_version.created_at)
            for index, section_data in enumerate(
                sorted([item for item in sections_snapshot if isinstance(item, dict)],
                       key=lambda item: item.get("sort_order") if isinstance(item.get("sort_order"), int) else 0)
            )
            if section_data.get("is_visible", True) is not False and section_data.get("status", "active") != "archived"
        ]
        section_rows = [
            schemas.CmsSectionRead(**{**s.model_dump(), "props_json": _build_section_defaults(db, site_key, s.type, s.props_json)})
            for s in section_rows
        ]
        slug_val = str(page_snapshot.get("slug") or page.slug) if isinstance(page_snapshot, dict) else page.slug
        title_val = str(page_snapshot.get("title") or page.title) if isinstance(page_snapshot, dict) else page.title
        breadcrumb_items = build_breadcrumb_items_from_slug(slug_val, title_val, base_url=base_url, site_name=site.name or "Home")
        breadcrumb_json_ld = build_breadcrumb_list_json_ld(breadcrumb_items, base_url=base_url)
        page_url = f"{base_url}/{slug_val.lstrip('/')}"
        canonical = page_snapshot.get("canonical_url") if isinstance(page_snapshot, dict) and page_snapshot.get("canonical_url") else None
        json_ld_data = auto_json_ld_for_page(page, site, sections=section_rows, base_url=base_url, site_name=_get_system_var(db, site_key, "church_name", site.name))
        snapshot_seo = page_snapshot.get("seo_json") if isinstance(page_snapshot, dict) and isinstance(page_snapshot.get("seo_json"), dict) else {}
        if snapshot_seo.get("json_ld"):
            json_ld_data = snapshot_seo["json_ld"]
        return schemas.CmsPublicPageRead(
            site_key=site.site_key, slug=slug_val, title=title_val, seo_json=snapshot_seo,
            sections=section_rows, json_ld=json_ld_data, canonical_url=canonical or page_url,
            breadcrumbs=breadcrumb_items, breadcrumb_json_ld=breadcrumb_json_ld,
        )

    sections_list, _ = crud.list_cms_sections(db, page.id)
    sections = [section for section in sections_list if section.is_visible and getattr(section, "status", "active") != "archived"]
    section_reads = []
    for section in sections:
        sr = schemas.CmsSectionRead.model_validate(section)
        sr.props_json = _build_section_defaults(db, site_key, sr.type, sr.props_json)
        section_reads.append(sr)
    page_url = f"{base_url}/{page.slug.lstrip('/')}"
    canonical = (page.seo_json or {}).get("canonical_url") if isinstance(page.seo_json, dict) else None
    json_ld_data = auto_json_ld_for_page(page, site, sections=sections, base_url=base_url, site_name=_get_system_var(db, site_key, "church_name", site.name))
    if isinstance(page.seo_json, dict) and page.seo_json.get("json_ld"):
        json_ld_data = page.seo_json["json_ld"]
    breadcrumb_items = build_breadcrumb_items_from_slug(page.slug, page.title, base_url=base_url, site_name=site.name or "Home")
    breadcrumb_json_ld = build_breadcrumb_list_json_ld(breadcrumb_items, base_url=base_url)
    return schemas.CmsPublicPageRead(
        site_key=site.site_key, slug=page.slug, title=page.title, seo_json=page.seo_json or {},
        sections=section_reads, json_ld=json_ld_data, canonical_url=canonical or page_url,
        breadcrumbs=breadcrumb_items, breadcrumb_json_ld=breadcrumb_json_ld,
    )


# ── Sitemap & Robots ─────────────────────────────────────────────────────────


@router.get(
    "/public/sites/{site_key}/sitemap.xml",
    dependencies=[Depends(rate_limiter(limit=10, window_seconds=60))],
)
@cached_public(ttl=300)
def public_sitemap(site_key: str, db: Session = Depends(get_db)):
    site = _get_public_site_or_404(db, site_key)
    pages = (
        db.query(models.CmsPage).options(lazyload("*"))
        .filter(models.CmsPage.site_id == site.id, models.CmsPage.status == "published")
        .order_by(models.CmsPage.updated_at.desc()).limit(500).all()
    )
    settings = get_settings()
    base_url = settings.frontend_url.rstrip("/")
    xml = build_sitemap_xml(pages, base_url, include_images=True)
    return Response(content=xml, media_type="application/xml")


@router.get(
    "/public/sites/{site_key}/robots.txt",
    dependencies=[Depends(rate_limiter(limit=10, window_seconds=60))],
)
@cached_public(ttl=300)
def public_robots(site_key: str, db: Session = Depends(get_db)):
    _get_public_site_or_404(db, site_key)
    settings = get_settings()
    base_url = settings.frontend_url.rstrip("/")
    sitemap_url = f"{base_url.rstrip('/')}/api/cms/v2/public/sites/{site_key}/sitemap.xml"
    txt = build_robots_txt(base_url, sitemap_url=sitemap_url)
    return Response(content=txt, media_type="text/plain")


# ── Public Pastoral Team ─────────────────────────────────────────────────────


@router.get(
    "/public/sites/{site_key}/pastoral-team",
    response_model=List[schemas.PastoralProfileRead],
    dependencies=[Depends(rate_limiter(limit=20, window_seconds=60))],
)
@cached_public(ttl=300)
def public_pastoral_team(site_key: str, db: Session = Depends(get_db)):
    _get_public_site_or_404(db, site_key)
    base_query = db.query(models.Persona).options(lazyload("*")).filter(models.Persona.is_pastoral_leader.is_(True), models.Persona.is_pastoral_published.is_(True))
    leaders = base_query.order_by(models.Persona.pastoral_sort_order.asc(), models.Persona.is_main_pastor.desc(), models.Persona.nombre_completo.asc()).all()
    result = []
    for p in leaders:
        name = p.nombre_completo
        result.append(schemas.PastoralProfileRead(
            id=str(p.id), name=name, slug=_slugify(name), photo_url=p.photo_url,
            bio_short=p.bio_short, bio_full=p.bio_full, role=_pastoral_role(p),
            social_instagram=p.social_instagram, social_facebook=p.social_facebook,
            social_twitter=p.social_twitter, is_main_pastor=p.is_main_pastor or False,
            pastoral_sort_order=getattr(p, "pastoral_sort_order", 0) or 0,
            is_pastoral_published=getattr(p, "is_pastoral_published", True),
        ))
    return result


# ── Public Posts ─────────────────────────────────────────────────────────────


def _enrich_public_posts(
    db: Session, site_key: str, posts: list[models.CmsPost],
) -> list[schemas.CmsPublicPostRead]:
    """Batch-enrich public posts with categories, tags and author names."""
    if not posts:
        return []
    post_ids = [post.id for post in posts]
    categories_by_post = crud.get_posts_categories_batch(db, post_ids)
    tags_by_post = crud.get_posts_tags_batch(db, post_ids)
    author_ids = {post.author_persona_id for post in posts if post.author_persona_id is not None}
    authors_by_id: dict = {}
    if author_ids:
        for row in db.query(models.Persona).filter(models.Persona.id.in_(author_ids)).all():
            authors_by_id[row.id] = row.nombre_completo
    settings = get_settings()
    base_url = settings.frontend_url.rstrip("/")
    enriched: list[schemas.CmsPublicPostRead] = []
    for post in posts:
        p = schemas.CmsPublicPostRead.model_validate(post)
        p.site_key = site_key
        p.categories = [schemas.CmsCategoryRead.model_validate(c) for c in categories_by_post.get(str(post.id), [])]
        p.tags = [schemas.CmsTagRead.model_validate(t) for t in tags_by_post.get(str(post.id), [])]
        p.author_name = authors_by_id.get(post.author_persona_id) if post.author_persona_id else None
        p.canonical_url = f"{base_url}/blog/{post.slug}"
        enriched.append(p)
    return enriched


@router.get(
    "/public/sites/{site_key}/posts",
    response_model=PaginatedResponse[schemas.CmsPublicPostRead],
    dependencies=[Depends(rate_limiter(limit=30, window_seconds=60))],
)
@cached_public(ttl=300)
def public_posts_list(
    site_key: str,
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    category_slug: str | None = Query(None),
    tag_slug: str | None = Query(None),
):
    site = _get_public_site_or_404(db, site_key)
    query = db.query(models.CmsPost).options(lazyload("*")).filter(models.CmsPost.site_id == site.id, models.CmsPost.status == "published")
    if category_slug:
        query = query.join(models.CmsPostCategory).join(models.CmsCategory).filter(models.CmsCategory.slug == category_slug)
    if tag_slug:
        query = query.join(models.CmsPostTag).join(models.CmsTag).filter(models.CmsTag.slug == tag_slug)
    total = query.count()
    items = query.order_by(models.CmsPost.published_at.desc().nullslast()).offset(skip).limit(limit).all()
    enriched = _enrich_public_posts(db, site_key, items)
    return PaginatedResponse[schemas.CmsPublicPostRead](items=enriched, total=total, skip=skip, limit=limit)


@router.get(
    "/public/sites/{site_key}/posts/{slug}",
    response_model=schemas.CmsPublicPostRead,
    dependencies=[Depends(rate_limiter(limit=30, window_seconds=60))],
)
@cached_public(ttl=300)
def public_post(site_key: str, slug: str, db: Session = Depends(get_db)):
    site = _get_public_site_or_404(db, site_key)
    post = (
        db.query(models.CmsPost).options(lazyload("*"))
        .filter(models.CmsPost.site_id == site.id, models.CmsPost.slug == _slugify(slug), models.CmsPost.status == "published")
        .first()
    )
    if not post:
        raise HTTPException(status_code=404, detail="published post not found")
    return _enrich_public_posts(db, site_key, [post])[0]
