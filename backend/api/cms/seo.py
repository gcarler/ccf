"""SEO endpoints: audit, snapshots, public sitemap and robots (Fase 4 refactor)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session, lazyload

from backend import crud, models, schemas
from backend.api._cms_helpers import (
    audit_pages,
    build_media_alt_lookup,
    collect_section_media_ids,
    group_sections_by_page,
)
from backend.api.cms_v2._shared import (
    CMS_EDITOR_ROLES,
    _assert_role,
    _get_public_site_or_404,
    _get_scoped_site_or_404,
)
from backend.core.cache_v2 import cached_public
from backend.core.config import get_settings
from backend.core.database import get_db
from backend.core.permissions import require_module_access
from backend.core.rate_limit import rate_limiter
from backend.core.seo import (
    build_robots_txt,
    build_sitemap_xml,
)
from backend.schemas._common import PaginatedResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["cms_v2_seo"])


@router.get("/sites/{site_key}/seo-audit", response_model=schemas.SeoAuditResponse)
def seo_audit(
    site_key: str,
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status: str | None = Query(None),
    min_score: int | None = Query(None, ge=0, le=100),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_scoped_site_or_404(db, site_key, current_user)
    pages_query = db.query(models.CmsPage).options(lazyload("*")).filter(models.CmsPage.site_id == site.id)
    if status:
        pages_query = pages_query.filter(models.CmsPage.status == status)
    pages = pages_query.order_by(models.CmsPage.updated_at.desc()).offset(skip).limit(limit).all()
    page_ids = [page.id for page in pages]
    sections_by_page = group_sections_by_page([])
    if page_ids:
        sections_rows = (
            db.query(models.CmsSection)
            .filter(models.CmsSection.page_id.in_(page_ids))
            .order_by(models.CmsSection.sort_order.asc())
            .all()
        )
        sections_by_page = group_sections_by_page(sections_rows)
    media_ids = collect_section_media_ids(section for rows in sections_by_page.values() for section in rows)
    media_alt_lookup = build_media_alt_lookup(db, media_ids)
    audits, aggregate = audit_pages(pages, sections_by_page, media_alt_lookup)
    if min_score is not None:
        audits = [audit for audit in audits if audit.score >= min_score]
    return schemas.SeoAuditResponse(site_key=site.site_key, aggregate=aggregate, pages=audits)


@router.get(
    "/sites/{site_key}/seo-snapshots",
    response_model=PaginatedResponse[schemas.CmsSeoSnapshotRead],
)
def list_seo_snapshots_endpoint(
    site_key: str,
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(90, ge=1, le=365),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_scoped_site_or_404(db, site_key, current_user)
    rows, total = crud.list_seo_snapshots(db, site_id=site.id, limit=limit, offset=skip)
    return PaginatedResponse[schemas.CmsSeoSnapshotRead](
        items=[schemas.CmsSeoSnapshotRead.model_validate(r) for r in rows],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/public/sites/{site_key}/sitemap.xml",
    dependencies=[Depends(rate_limiter(limit=10, window_seconds=60))],
)
@cached_public(ttl=300)
def public_sitemap(site_key: str, db: Session = Depends(get_db)):
    site = _get_public_site_or_404(db, site_key)
    pages = (
        db.query(models.CmsPage)
        .options(lazyload("*"))
        .filter(models.CmsPage.site_id == site.id, models.CmsPage.status == "published")
        .order_by(models.CmsPage.updated_at.desc())
        .limit(500)
        .all()
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
