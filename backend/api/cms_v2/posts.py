"""Categories, tags and posts admin endpoints (Fase 4 refactor).

Extracted from the monolithic ``cms_v2/__init__.py``.
"""
from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend import crud, models, schemas
from backend.api.cms_v2._shared import (
    CMS_EDITOR_ROLES,
    _assert_role,
    _ensure_canonical_category,
    _get_category_or_404,
    _get_post_or_404,
    _get_scoped_site_or_404,
    _get_tag_or_404,
    _slugify,
    _validate_canonical_category,
)
from backend.core.database import get_db
from backend.core.permissions import require_module_access
from backend.schemas._common import PaginatedResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["cms_v2_posts"])


# ── Categories CRUD ──────────────────────────────────────────────────────────


@router.get("/sites/{site_key}/categories", response_model=list[schemas.CmsCategoryRead])
def list_categories(
    site_key: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    site = _get_scoped_site_or_404(db, site_key, current_user)
    return crud.list_cms_categories(db, site.id)


@router.post("/sites/{site_key}/categories", response_model=schemas.CmsCategoryRead, status_code=201)
def create_category(
    site_key: str,
    payload: schemas.CmsCategoryCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_scoped_site_or_404(db, site_key, current_user)
    payload.slug = _slugify(payload.slug)
    if not payload.slug:
        raise HTTPException(status_code=422, detail="slug is required")
    if crud.get_cms_category(db, site.id, payload.slug):
        raise HTTPException(status_code=409, detail="category slug already exists")
    try:
        return crud.create_cms_category(db, site.id, payload, actor_user_id=str(current_user.id))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/sites/{site_key}/categories/{slug}", response_model=schemas.CmsCategoryRead)
def get_category(
    site_key: str,
    slug: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    site = _get_scoped_site_or_404(db, site_key, current_user)
    return _get_category_or_404(db, site.id, slug)


@router.patch("/sites/{site_key}/categories/{slug}", response_model=schemas.CmsCategoryRead)
def patch_category(
    site_key: str,
    slug: str,
    payload: schemas.CmsCategoryUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_scoped_site_or_404(db, site_key, current_user)
    row = _get_category_or_404(db, site.id, slug)
    try:
        return crud.update_cms_category(db, row, payload, actor_user_id=str(current_user.id))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.delete("/sites/{site_key}/categories/{slug}", status_code=204)
def delete_category(
    site_key: str,
    slug: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_scoped_site_or_404(db, site_key, current_user)
    row = _get_category_or_404(db, site.id, slug)
    crud.delete_cms_category(db, row, actor_user_id=str(current_user.id))


# ── Tags CRUD ────────────────────────────────────────────────────────────────


@router.get("/sites/{site_key}/tags", response_model=list[schemas.CmsTagRead])
def list_tags(
    site_key: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    site = _get_scoped_site_or_404(db, site_key, current_user)
    return crud.list_cms_tags(db, site.id)


@router.post("/sites/{site_key}/tags", response_model=schemas.CmsTagRead, status_code=201)
def create_tag(
    site_key: str,
    payload: schemas.CmsTagCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_scoped_site_or_404(db, site_key, current_user)
    payload.slug = _slugify(payload.slug)
    if not payload.slug:
        raise HTTPException(status_code=422, detail="slug is required")
    if crud.get_cms_tag(db, site.id, payload.slug):
        raise HTTPException(status_code=409, detail="tag slug already exists")
    return crud.create_cms_tag(db, site.id, payload, actor_user_id=str(current_user.id))


@router.get("/sites/{site_key}/tags/{slug}", response_model=schemas.CmsTagRead)
def get_tag(
    site_key: str,
    slug: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    site = _get_scoped_site_or_404(db, site_key, current_user)
    return _get_tag_or_404(db, site.id, slug)


@router.patch("/sites/{site_key}/tags/{slug}", response_model=schemas.CmsTagRead)
def patch_tag(
    site_key: str,
    slug: str,
    payload: schemas.CmsTagUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_scoped_site_or_404(db, site_key, current_user)
    row = _get_tag_or_404(db, site.id, slug)
    return crud.update_cms_tag(db, row, payload, actor_user_id=str(current_user.id))


@router.delete("/sites/{site_key}/tags/{slug}", status_code=204)
def delete_tag(
    site_key: str,
    slug: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_scoped_site_or_404(db, site_key, current_user)
    row = _get_tag_or_404(db, site.id, slug)
    crud.delete_cms_tag(db, row, actor_user_id=str(current_user.id))


# ── Posts (Admin) ────────────────────────────────────────────────────────────


@router.get(
    "/sites/{site_key}/posts",
    response_model=PaginatedResponse[schemas.CmsPostReadWithTaxonomies],
)
def list_posts(
    site_key: str,
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status: str | None = Query(None),
    category_id: uuid.UUID | None = Query(None),
    tag_id: uuid.UUID | None = Query(None),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    site = _get_scoped_site_or_404(db, site_key, current_user)
    items, total = crud.list_cms_posts(db, site.id, skip=skip, limit=limit, status=status, category_id=category_id, tag_id=tag_id)
    post_ids = [post.id for post in items]
    cats_by_post = crud.get_posts_categories_batch(db, post_ids)
    tags_by_post = crud.get_posts_tags_batch(db, post_ids)
    enriched = []
    for post in items:
        p = schemas.CmsPostReadWithTaxonomies.model_validate(post)
        p.categories = [schemas.CmsCategoryRead.model_validate(c) for c in cats_by_post.get(str(post.id), [])]
        p.tags = [schemas.CmsTagRead.model_validate(t) for t in tags_by_post.get(str(post.id), [])]
        enriched.append(p)
    return PaginatedResponse[schemas.CmsPostReadWithTaxonomies](items=enriched, total=total, skip=skip, limit=limit)


@router.post("/sites/{site_key}/posts", response_model=schemas.CmsPostReadWithTaxonomies, status_code=201)
def create_post(
    site_key: str,
    payload: schemas.CmsPostCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    if payload.status.strip().lower() not in {"draft", "in_review", "approved", "published", "archived"}:
        raise HTTPException(status_code=422, detail="invalid status")
    site = _get_scoped_site_or_404(db, site_key, current_user)
    payload.slug = _slugify(payload.slug)
    if not payload.slug:
        raise HTTPException(status_code=422, detail="slug is required")
    if crud.get_cms_post(db, site.id, payload.slug):
        raise HTTPException(status_code=409, detail="slug already exists")
    try:
        row = crud.create_cms_post(db, site.id, payload, current_user.id, actor_user_id=str(current_user.id))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    p = schemas.CmsPostReadWithTaxonomies.model_validate(row)
    p.categories = [schemas.CmsCategoryRead.model_validate(c) for c in crud.get_post_categories(db, row.id)]
    p.tags = [schemas.CmsTagRead.model_validate(t) for t in crud.get_post_tags(db, row.id)]
    return p


@router.get("/sites/{site_key}/posts/{slug}", response_model=schemas.CmsPostReadWithTaxonomies)
def get_post(
    site_key: str,
    slug: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    site = _get_scoped_site_or_404(db, site_key, current_user)
    row = _get_post_or_404(db, site.id, slug)
    p = schemas.CmsPostReadWithTaxonomies.model_validate(row)
    p.categories = [schemas.CmsCategoryRead.model_validate(c) for c in crud.get_post_categories(db, row.id)]
    p.tags = [schemas.CmsTagRead.model_validate(t) for t in crud.get_post_tags(db, row.id)]
    return p


@router.patch("/sites/{site_key}/posts/{slug}", response_model=schemas.CmsPostReadWithTaxonomies)
def patch_post(
    site_key: str,
    slug: str,
    payload: schemas.CmsPostUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_scoped_site_or_404(db, site_key, current_user)
    row = _get_post_or_404(db, site.id, slug)
    if payload.status is not None and payload.status.strip().lower() not in {"draft", "in_review", "approved", "published", "archived"}:
        raise HTTPException(status_code=422, detail="invalid status")
    try:
        updated = crud.update_cms_post(db, row, payload, current_user.id, actor_user_id=str(current_user.id))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    p = schemas.CmsPostReadWithTaxonomies.model_validate(updated)
    p.categories = [schemas.CmsCategoryRead.model_validate(c) for c in crud.get_post_categories(db, updated.id)]
    p.tags = [schemas.CmsTagRead.model_validate(t) for t in crud.get_post_tags(db, updated.id)]
    return p


@router.delete("/sites/{site_key}/posts/{slug}", status_code=204)
def delete_post(
    site_key: str,
    slug: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_scoped_site_or_404(db, site_key, current_user)
    row = _get_post_or_404(db, site.id, slug)
    crud.delete_cms_post(db, row, actor_user_id=str(current_user.id))


# ── Posts by Canonical Category (Testimonials / Announcements) ────────────────


@router.get(
    "/sites/{site_key}/posts-by-category",
    response_model=PaginatedResponse[schemas.CmsPostReadWithTaxonomies],
)
def list_posts_by_category(
    site_key: str,
    category: str = Query(..., description="Canonical category: testimonials or announcements"),
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status: str | None = Query(None),
    include_archived: bool = Query(False),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    _validate_canonical_category(category)
    site = _get_scoped_site_or_404(db, site_key, current_user)
    _ensure_canonical_category(db, site.id, category)
    items, total = crud.list_cms_posts_by_category(db, site_id=site.id, category_slug=category, skip=skip, limit=limit, status=status, include_archived=include_archived)
    post_ids = [post.id for post in items]
    cats_by_post = crud.get_posts_categories_batch(db, post_ids)
    tags_by_post = crud.get_posts_tags_batch(db, post_ids)
    enriched = []
    for post in items:
        p = schemas.CmsPostReadWithTaxonomies.model_validate(post)
        p.categories = [schemas.CmsCategoryRead.model_validate(c) for c in cats_by_post.get(str(post.id), [])]
        p.tags = [schemas.CmsTagRead.model_validate(t) for t in tags_by_post.get(str(post.id), [])]
        enriched.append(p)
    return PaginatedResponse[schemas.CmsPostReadWithTaxonomies](items=enriched, total=total, skip=skip, limit=limit)


@router.post(
    "/sites/{site_key}/posts-by-category",
    response_model=schemas.CmsPostReadWithTaxonomies,
    status_code=201,
)
def create_post_by_category(
    site_key: str,
    category: str = Query(..., description="Canonical category: testimonials or announcements"),
    payload: schemas.CmsPostCreate = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    _validate_canonical_category(category)
    if payload.status.strip().lower() not in {"draft", "in_review", "approved", "published", "archived"}:
        raise HTTPException(status_code=422, detail="invalid status")
    site = _get_scoped_site_or_404(db, site_key, current_user)
    cat = _ensure_canonical_category(db, site.id, category)
    payload.slug = _slugify(payload.slug) or f"{category}-{uuid.uuid4().hex[:8]}"
    if crud.get_cms_post(db, site.id, payload.slug):
        raise HTTPException(status_code=409, detail="slug already exists")
    payload.category_ids = [cat.id]
    try:
        row = crud.create_cms_post(db, site.id, payload, current_user.id, actor_user_id=str(current_user.id))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    p = schemas.CmsPostReadWithTaxonomies.model_validate(row)
    p.categories = [schemas.CmsCategoryRead.model_validate(c) for c in crud.get_post_categories(db, row.id)]
    p.tags = [schemas.CmsTagRead.model_validate(t) for t in crud.get_post_tags(db, row.id)]
    return p


@router.get(
    "/sites/{site_key}/posts-by-category/{slug}",
    response_model=schemas.CmsPostReadWithTaxonomies,
)
def get_post_by_category(
    site_key: str,
    slug: str,
    category: str = Query(..., description="Canonical category: testimonials or announcements"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    _validate_canonical_category(category)
    site = _get_scoped_site_or_404(db, site_key, current_user)
    _ensure_canonical_category(db, site.id, category)
    row = crud.get_cms_post_by_slug_and_category(db, site.id, slug, category)
    if not row:
        raise HTTPException(status_code=404, detail="post not found")
    p = schemas.CmsPostReadWithTaxonomies.model_validate(row)
    p.categories = [schemas.CmsCategoryRead.model_validate(c) for c in crud.get_post_categories(db, row.id)]
    p.tags = [schemas.CmsTagRead.model_validate(t) for t in crud.get_post_tags(db, row.id)]
    return p


@router.patch(
    "/sites/{site_key}/posts-by-category/{slug}",
    response_model=schemas.CmsPostReadWithTaxonomies,
)
def patch_post_by_category(
    site_key: str,
    slug: str,
    category: str = Query(..., description="Canonical category: testimonials or announcements"),
    payload: schemas.CmsPostUpdate = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    _validate_canonical_category(category)
    site = _get_scoped_site_or_404(db, site_key, current_user)
    row = crud.get_cms_post_by_slug_and_category(db, site.id, slug, category)
    if not row:
        raise HTTPException(status_code=404, detail="post not found")
    if payload.status is not None and payload.status.strip().lower() not in {"draft", "in_review", "approved", "published", "archived"}:
        raise HTTPException(status_code=422, detail="invalid status")
    if payload.category_ids is not None:
        raise HTTPException(status_code=422, detail="cannot change canonical category")
    try:
        updated = crud.update_cms_post(db, row, payload, current_user.id, actor_user_id=str(current_user.id))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    p = schemas.CmsPostReadWithTaxonomies.model_validate(updated)
    p.categories = [schemas.CmsCategoryRead.model_validate(c) for c in crud.get_post_categories(db, updated.id)]
    p.tags = [schemas.CmsTagRead.model_validate(t) for t in crud.get_post_tags(db, updated.id)]
    return p


@router.delete("/sites/{site_key}/posts-by-category/{slug}", status_code=204)
def delete_post_by_category(
    site_key: str,
    slug: str,
    category: str = Query(..., description="Canonical category: testimonials or announcements"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    _validate_canonical_category(category)
    site = _get_scoped_site_or_404(db, site_key, current_user)
    row = crud.get_cms_post_by_slug_and_category(db, site.id, slug, category)
    if not row:
        raise HTTPException(status_code=404, detail="post not found")
    crud.delete_cms_post(db, row, actor_user_id=str(current_user.id))
