"""Public page endpoints (Fase 4 refactor & query optimization)."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, lazyload

from backend import models, schemas
from backend.api.cms_v2._shared import (
    PUBLIC_CMS_RATE_LIMIT,
    _build_section_defaults,
    _get_public_site_or_404,
    _get_system_var,
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
)
from backend.exceptions.cms import PageNotFoundError
from backend.schemas import PaginatedResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["cms_v2_public_pages"])


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
    query = (
        db.query(models.CmsPage)
        .options(lazyload("*"))
        .filter(models.CmsPage.site_id == site.id, models.CmsPage.status == "published")
    )
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
    # Optimizado N+1: 1 query JOIN CmsPage+CmsSite (evita el site lookup
    # separado). ``lazyload('*')`` previene el cascade de JOINs de
    # ``CmsPage.site``/``published_version`` y de los joined de ``CmsSection``.
    page = (
        db.query(models.CmsPage)
        .options(lazyload("*"))
        .join(models.CmsSite, models.CmsSite.id == models.CmsPage.site_id)
        .filter(
            models.CmsSite.site_key == site_key.strip().lower(),
            models.CmsSite.is_active.is_(True),
            models.CmsPage.slug == _slugify(slug),
            models.CmsPage.status == "published",
        )
        .first()
    )
    if not page:
        raise PageNotFoundError("Published page not found")
    site = page.site

    published_version = None
    if page.published_version_id:
        published_version = (
            db.query(models.CmsPageVersion)
            .options(lazyload("*"))
            .filter(models.CmsPageVersion.page_id == page.id, models.CmsPageVersion.id == page.published_version_id)
            .first()
        )

    settings = get_settings()
    base_url = settings.frontend_url.rstrip("/")
    defaults_cache: dict[str, dict[str, Any]] = {}

    if published_version:
        snapshot = published_version.snapshot_json or {}
        page_snapshot = snapshot.get("page") if isinstance(snapshot, dict) else {}
        sections_snapshot = snapshot.get("sections") if isinstance(snapshot, dict) else []
        section_rows = [
            _snapshot_section_read(section_data, page_id=page.id, index=index, timestamp=published_version.created_at)
            for index, section_data in enumerate(
                sorted(
                    [item for item in sections_snapshot if isinstance(item, dict)],
                    key=lambda item: item.get("sort_order") if isinstance(item.get("sort_order"), int) else 0,
                )
            )
            if section_data.get("is_visible", True) is not False and section_data.get("status", "active") != "archived"
        ]
        section_rows = [
            schemas.CmsSectionRead(
                **{
                    **s.model_dump(),
                    "props_json": _build_section_defaults(
                        db, site_key, s.type, s.props_json, defaults_cache=defaults_cache
                    ),
                }
            )
            for s in section_rows
        ]
        slug_val = str(page_snapshot.get("slug") or page.slug) if isinstance(page_snapshot, dict) else page.slug
        title_val = str(page_snapshot.get("title") or page.title) if isinstance(page_snapshot, dict) else page.title
        breadcrumb_items = build_breadcrumb_items_from_slug(
            slug_val, title_val, base_url=base_url, site_name=site.name or "Home"
        )
        breadcrumb_json_ld = build_breadcrumb_list_json_ld(breadcrumb_items, base_url=base_url)
        page_url = f"{base_url}/{slug_val.lstrip('/')}"
        canonical = (
            page_snapshot.get("canonical_url")
            if isinstance(page_snapshot, dict) and page_snapshot.get("canonical_url")
            else None
        )
        json_ld_data = auto_json_ld_for_page(
            page,
            site,
            sections=section_rows,
            base_url=base_url,
            site_name=_get_system_var(db, site_key, "church_name", site.name),
        )
        snapshot_seo = (
            page_snapshot.get("seo_json")
            if isinstance(page_snapshot, dict) and isinstance(page_snapshot.get("seo_json"), dict)
            else {}
        )
        if snapshot_seo.get("json_ld"):
            json_ld_data = snapshot_seo["json_ld"]
        return schemas.CmsPublicPageRead(
            site_key=site.site_key,
            slug=slug_val,
            title=title_val,
            seo_json=snapshot_seo,
            sections=section_rows,
            json_ld=json_ld_data,
            canonical_url=canonical or page_url,
            breadcrumbs=breadcrumb_items,
            breadcrumb_json_ld=breadcrumb_json_ld,
        )

    sections_list = (
        db.query(models.CmsSection)
        .options(lazyload("*"))
        .filter(
            models.CmsSection.page_id == page.id,
            models.CmsSection.deleted_at.is_(None),
        )
        .order_by(models.CmsSection.sort_order.asc(), models.CmsSection.id.asc())
        .all()
    )
    sections = [
        section
        for section in sections_list
        if section.is_visible and getattr(section, "status", "active") != "archived"
    ]
    section_reads = []
    for section in sections:
        sr = schemas.CmsSectionRead.model_validate(section)
        sr.props_json = _build_section_defaults(
            db, site_key, sr.type, sr.props_json, defaults_cache=defaults_cache
        )
        section_reads.append(sr)
    page_url = f"{base_url}/{page.slug.lstrip('/')}"
    canonical = (page.seo_json or {}).get("canonical_url") if isinstance(page.seo_json, dict) else None
    json_ld_data = auto_json_ld_for_page(
        page,
        site,
        sections=sections,
        base_url=base_url,
        site_name=_get_system_var(db, site_key, "church_name", site.name),
    )
    if isinstance(page.seo_json, dict) and page.seo_json.get("json_ld"):
        json_ld_data = page.seo_json["json_ld"]
    breadcrumb_items = build_breadcrumb_items_from_slug(
        page.slug, page.title, base_url=base_url, site_name=site.name or "Home"
    )
    breadcrumb_json_ld = build_breadcrumb_list_json_ld(breadcrumb_items, base_url=base_url)
    return schemas.CmsPublicPageRead(
        site_key=site.site_key,
        slug=page.slug,
        title=page.title,
        seo_json=page.seo_json or {},
        sections=section_reads,
        json_ld=json_ld_data,
        canonical_url=canonical or page_url,
        breadcrumbs=breadcrumb_items,
        breadcrumb_json_ld=breadcrumb_json_ld,
    )
