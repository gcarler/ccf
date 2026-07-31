"""Blog post comments endpoints for CMS v2 (Milestone 4 / R4).

Public endpoints:
  - POST /public/posts/{post_id}/comments (create pending comment)
  - GET  /public/posts/{post_id}/comments (list approved comments + 1-level replies)

Admin endpoints:
  - GET   /sites/{site_key}/post-comments (list comments with status filter + pending_count)
  - PATCH /sites/{site_key}/post-comments/{id} (update comment status)
"""
from __future__ import annotations

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend import models, schemas
from backend.api.cms_v2._shared import (
    CMS_EDITOR_ROLES,
    PUBLIC_CMS_RATE_LIMIT,
    _assert_role,
    _get_scoped_site_or_404,
)
from backend.core.database import get_db
from backend.core.permissions import require_module_access
from backend.core.rate_limit import rate_limiter
from backend.exceptions.cms import PostNotFoundError

logger = logging.getLogger(__name__)

router = APIRouter(tags=["cms_v2_post_comments"])


# ── Public Endpoints ─────────────────────────────────────────────────────────


@router.post(
    "/public/posts/{post_id}/comments",
    response_model=schemas.CmsPostCommentRead,
    status_code=201,
    dependencies=[Depends(rate_limiter(limit=PUBLIC_CMS_RATE_LIMIT, window_seconds=60))],
)
def create_public_post_comment(
    post_id: UUID,
    payload: schemas.CmsPostCommentCreate,
    db: Session = Depends(get_db),
):
    post = db.query(models.CmsPost).filter(models.CmsPost.id == post_id).first()
    if not post:
        raise PostNotFoundError("Post not found")

    if payload.parent_id:
        parent = (
            db.query(models.CmsPostComment)
            .filter(
                models.CmsPostComment.id == payload.parent_id,
                models.CmsPostComment.post_id == post_id,
            )
            .first()
        )
        if not parent:
            raise HTTPException(
                status_code=400,
                detail="Parent comment not found or belongs to another post",
            )

    comment = models.CmsPostComment(
        post_id=post_id,
        parent_id=payload.parent_id,
        author_name=payload.author_name.strip(),
        author_email=payload.author_email.strip().lower(),
        content=payload.content.strip(),
        status="pending",
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)

    res = schemas.CmsPostCommentRead.model_validate(comment)
    res.post_title = post.title
    res.post_slug = post.slug
    return res


@router.get(
    "/public/posts/{post_id}/comments",
    response_model=List[schemas.CmsPostCommentPublicRead],
    dependencies=[Depends(rate_limiter(limit=PUBLIC_CMS_RATE_LIMIT, window_seconds=60))],
)
def get_public_post_comments(
    post_id: UUID,
    db: Session = Depends(get_db),
):
    post = db.query(models.CmsPost).filter(models.CmsPost.id == post_id).first()
    if not post:
        raise PostNotFoundError("Post not found")

    approved_comments = (
        db.query(models.CmsPostComment)
        .filter(
            models.CmsPostComment.post_id == post_id,
            models.CmsPostComment.status == "approved",
        )
        .order_by(models.CmsPostComment.created_at.asc())
        .all()
    )

    root_comments = [c for c in approved_comments if c.parent_id is None]
    child_comments = [c for c in approved_comments if c.parent_id is not None]

    replies_map: dict[UUID, list[schemas.CmsPostCommentPublicRead]] = {}
    for child in child_comments:
        child_dto = schemas.CmsPostCommentPublicRead.model_validate(child)
        if child.parent_id not in replies_map:
            replies_map[child.parent_id] = []
        replies_map[child.parent_id].append(child_dto)

    result: List[schemas.CmsPostCommentPublicRead] = []
    for root in root_comments:
        root_dto = schemas.CmsPostCommentPublicRead.model_validate(root)
        root_dto.replies = replies_map.get(root.id, [])
        result.append(root_dto)

    return result


# ── Admin Endpoints ──────────────────────────────────────────────────────────


@router.get(
    "/sites/{site_key}/post-comments",
    response_model=schemas.CmsPostCommentListResponse,
)
def list_admin_post_comments(
    site_key: str,
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    site = _get_scoped_site_or_404(db, site_key, current_user)

    pending_count = (
        db.query(func.count(models.CmsPostComment.id))
        .join(models.CmsPost, models.CmsPostComment.post_id == models.CmsPost.id)
        .filter(
            models.CmsPost.site_id == site.id,
            models.CmsPostComment.status == "pending",
        )
        .scalar()
        or 0
    )

    query = (
        db.query(models.CmsPostComment, models.CmsPost.title, models.CmsPost.slug)
        .join(models.CmsPost, models.CmsPostComment.post_id == models.CmsPost.id)
        .filter(models.CmsPost.site_id == site.id)
    )

    if status and status.strip():
        query = query.filter(models.CmsPostComment.status == status.strip())

    total = query.count()

    rows = (
        query.order_by(models.CmsPostComment.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    items: List[schemas.CmsPostCommentRead] = []
    for comment, p_title, p_slug in rows:
        item = schemas.CmsPostCommentRead.model_validate(comment)
        item.post_title = p_title
        item.post_slug = p_slug
        items.append(item)

    return schemas.CmsPostCommentListResponse(
        items=items,
        total=total,
        skip=skip,
        limit=limit,
        pending_count=pending_count,
    )


@router.patch(
    "/sites/{site_key}/post-comments/{id}",
    response_model=schemas.CmsPostCommentRead,
)
def update_admin_post_comment_status(
    site_key: str,
    id: UUID,
    payload: schemas.CmsPostCommentStatusUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    _assert_role(current_user, CMS_EDITOR_ROLES)
    site = _get_scoped_site_or_404(db, site_key, current_user)

    row = (
        db.query(models.CmsPostComment, models.CmsPost.title, models.CmsPost.slug)
        .join(models.CmsPost, models.CmsPostComment.post_id == models.CmsPost.id)
        .filter(
            models.CmsPostComment.id == id,
            models.CmsPost.site_id == site.id,
        )
        .first()
    )

    if not row:
        raise HTTPException(status_code=404, detail="Comment not found")

    comment, p_title, p_slug = row
    comment.status = payload.status
    db.commit()
    db.refresh(comment)

    res = schemas.CmsPostCommentRead.model_validate(comment)
    res.post_title = p_title
    res.post_slug = p_slug
    return res
