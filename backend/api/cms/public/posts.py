"""Public post endpoints (Fase 4 refactor & N+1 query optimization)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session, lazyload, noload

from backend import crud, models, schemas
from backend.api.cms_v2._shared import (
    _slugify,
    cached_public,
)
from backend.core.config import get_settings
from backend.core.database import get_db
from backend.core.rate_limit import rate_limiter
from backend.exceptions.cms import PostNotFoundError
from backend.schemas import PaginatedResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["cms_v2_public_posts"])


def _enrich_public_posts(
    db: Session,
    site_key: str,
    posts: list[models.CmsPost],
) -> list[schemas.CmsPublicPostRead]:
    """Batch-enrich public posts with categories, tags and author names without lazy-loading post.site."""
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
        p = schemas.CmsPublicPostRead(
            site_key=site_key,
            slug=post.slug,
            title=post.title,
            excerpt=post.excerpt,
            content=post.content,
            featured_image_url=post.featured_image_url,
            seo_json=post.seo_json or {},
            published_at=post.published_at,
            author_name=authors_by_id.get(post.author_persona_id) if post.author_persona_id else None,
            categories=[schemas.CmsCategoryRead.model_validate(c) for c in categories_by_post.get(str(post.id), [])],
            tags=[schemas.CmsTagRead.model_validate(t) for t in tags_by_post.get(str(post.id), [])],
            canonical_url=f"{base_url}/blog/{post.slug}",
        )
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
    # Optimizado N+1: JOIN directo CmsPost+CmsSite evita el site lookup
    # separado. noload(comments) y lazyload(categories/tags) previenen la
    # cargas selectin automáticas que disparaban queries de cms_post_comments
    # y cms_post_categories/tags al materializar CmsPost.
    query = (
        db.query(models.CmsPost)
        .options(
            lazyload("*"),
            lazyload(models.CmsPost.categories),
            lazyload(models.CmsPost.tags),
            noload(models.CmsPost.comments),
        )
        .join(models.CmsSite, models.CmsSite.id == models.CmsPost.site_id)
        .filter(
            models.CmsSite.site_key == site_key.strip().lower(),
            models.CmsSite.is_active.is_(True),
            models.CmsPost.status == "published",
        )
    )
    # Optimizado N+1: en lugar de 2 queries separadas (count + items),
    # usamos window function ``func.count().over()`` para traer el total
    # en la misma query de items. ``lazyload('*')`` no se puede combinar
    # con add_columns directamente en una sola list comprehension, así que
    # obtenemos las filas con la columna de total agregada y filtramos por
    # página. Esto reduce el SELECT count(*) separado a 0 (va inline con
    # items). Total queries: 1 (items+total) + 2 batch (cat, tag) +
    # 1 batch authors = 4 SELECTs en happy path (sin site lookup separado
    # porque unimos site en la misma query).
    if category_slug:
        query = (
            query.join(models.CmsPostCategory).join(models.CmsCategory).filter(models.CmsCategory.slug == category_slug)
        )
    if tag_slug:
        query = query.join(models.CmsPostTag).join(models.CmsTag).filter(models.CmsTag.slug == tag_slug)

    rows = (
        query.add_columns(func.count().over().label("_total"))
        .order_by(models.CmsPost.published_at.desc().nullslast())
        .offset(skip)
        .limit(limit)
        .all()
    )
    total = int(rows[0][1]) if rows else 0
    items = [row[0] for row in rows]
    enriched = _enrich_public_posts(db, site_key, items)
    return PaginatedResponse[schemas.CmsPublicPostRead](items=enriched, total=total, skip=skip, limit=limit)


@router.get(
    "/public/sites/{site_key}/posts/{slug}",
    response_model=schemas.CmsPublicPostRead,
    dependencies=[Depends(rate_limiter(limit=30, window_seconds=60))],
)
@cached_public(ttl=300)
def public_post(site_key: str, slug: str, db: Session = Depends(get_db)):
    # Optimizado N+1: JOIN directo CmsPost+CmsSite elimina el site lookup
    # separado. lazyload(categories/tags) + noload(comments) previenen las
    # selectin automáticas que disparaban queries extra de cms_post_comments
    # y cms_post_categories/tags.
    post = (
        db.query(models.CmsPost)
        .options(
            lazyload("*"),
            lazyload(models.CmsPost.categories),
            lazyload(models.CmsPost.tags),
            noload(models.CmsPost.comments),
        )
        .join(models.CmsSite, models.CmsSite.id == models.CmsPost.site_id)
        .filter(
            models.CmsSite.site_key == site_key.strip().lower(),
            models.CmsSite.is_active.is_(True),
            models.CmsPost.slug == _slugify(slug),
            models.CmsPost.status == "published",
        )
        .first()
    )
    if not post:
        raise PostNotFoundError("Published post not found")
    return _enrich_public_posts(db, site_key, [post])[0]
