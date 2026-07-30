"""Adapters for the v1→v2 CMS compatibility layer (testimonials).

This module maps the legacy ``Testimonial`` contract used by the v1 API
(``backend/api/cms.py``) onto the v2 ``CmsPost`` model. The public v1
endpoints keep returning ``schemas.TestimonialRead`` while internally
reading/writing ``CmsPost`` rows categorized as testimonials.

Axioma 3 — Multi-Tenant: ``Testimonial.sede_id`` is mapped to a
``CmsSite`` that belongs to that sede. All writes/reads go through the
existing v2 CRUD helpers, which enforce site-level scope.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from backend import models, schemas

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


# Categories used to tag v1→v2-derived posts.
TESTIMONIAL_CATEGORY_SLUG = "testimonials"
ANNOUNCEMENT_CATEGORY_SLUG = "announcements"


# ── Status mapping ─────────────────────────────────────────────────────────
# Legacy Testimonial.status ∈ {"pending", "approved", "archived"}
# v2 CmsPost.status      ∈ {"draft", "published", "archived", ...}


class _TestimonialStatus:
    PENDING = "pending"
    APPROVED = "approved"
    ARCHIVED = "archived"


class _PostStatus:
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


def _is_approved_from_status(status: str) -> bool:
    return status == _PostStatus.PUBLISHED


def _testimonial_status_from_post(status: str) -> str:
    if status == _PostStatus.PUBLISHED:
        return _TestimonialStatus.APPROVED
    if status == _PostStatus.ARCHIVED:
        return _TestimonialStatus.ARCHIVED
    return _TestimonialStatus.PENDING


def _post_status_from_testimonial(*, is_approved: bool, status: str | None) -> str:
    # Archived always wins, regardless of is_approved.
    if status == _TestimonialStatus.ARCHIVED:
        return _PostStatus.ARCHIVED
    if is_approved:
        return _PostStatus.PUBLISHED
    return _PostStatus.DRAFT


# ── Announcement helpers ─────────────────────────────────────────────────────
# Announcement.status ∈ {"draft", "published", "archived"}
# CmsPost.status      ∈ {"draft", "published", "archived", ...}
# The values are identical so no mapping is needed.


def get_or_create_announcement_site(
    db: "Session", sede_id: uuid.UUID | str
) -> models.CmsSite:
    """Return an active site for ``sede_id``; create a legacy one if needed."""
    site = get_site_for_sede(db, sede_id)
    if site is not None:
        return site

    short = str(sede_id).split("-")[0]
    site_key = f"legacy-announcements-{short}"
    site = models.CmsSite(
        site_key=site_key,
        name="Legacy Announcements Site",
        base_path=f"/legacy-announcements-{short}",
        is_active=True,
        sede_id=sede_id if isinstance(sede_id, uuid.UUID) else uuid.UUID(str(sede_id)),
    )
    db.add(site)
    db.commit()
    db.refresh(site)
    return site


def get_or_create_announcement_category(
    db: "Session", site_id: uuid.UUID
) -> models.CmsCategory:
    """Return the 'announcements' category for ``site_id``, creating it if missing."""
    cat = (
        db.query(models.CmsCategory)
        .filter(
            models.CmsCategory.site_id == site_id,
            models.CmsCategory.slug == ANNOUNCEMENT_CATEGORY_SLUG,
        )
        .first()
    )
    if cat is not None:
        return cat
    cat = models.CmsCategory(
        site_id=site_id,
        slug=ANNOUNCEMENT_CATEGORY_SLUG,
        name="Announcements",
        description="Legacy announcements migrated to CmsPost",
        is_active=True,
    )
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


# ── Query helpers (announcements) ──────────────────────────────────────────


def list_announcement_posts(
    db: "Session",
    *,
    sede_id: uuid.UUID | str | None = None,
    status: str | None = None,
    include_archived: bool = False,
) -> list[models.CmsPost]:
    """Return CmsPost rows categorized as announcements, optionally scoped by sede."""
    query = (
        db.query(models.CmsPost)
        .join(models.CmsPost.categories)
        .filter(models.CmsCategory.slug == ANNOUNCEMENT_CATEGORY_SLUG)
    )
    resolved_sede_id = _as_uuid(sede_id)
    if resolved_sede_id is not None:
        query = query.join(models.CmsSite).filter(models.CmsSite.sede_id == resolved_sede_id)
    if status is not None:
        query = query.filter(models.CmsPost.status == status)
    if not include_archived:
        query = query.filter(models.CmsPost.status != _PostStatus.ARCHIVED)
    return query.distinct().order_by(models.CmsPost.created_at.desc()).all()


def get_announcement_post_by_id(
    db: "Session",
    post_id: uuid.UUID,
    *,
    sede_id: uuid.UUID | str | None = None,
) -> models.CmsPost | None:
    """Fetch a single announcement post by id, optionally scoping by sede."""
    query = (
        db.query(models.CmsPost)
        .join(models.CmsPost.categories)
        .filter(models.CmsCategory.slug == ANNOUNCEMENT_CATEGORY_SLUG)
        .filter(models.CmsPost.id == post_id)
    )
    resolved_sede_id = _as_uuid(sede_id)
    if resolved_sede_id is not None:
        query = query.join(models.CmsSite).filter(models.CmsSite.sede_id == resolved_sede_id)
    return query.distinct().first()


# ── Mapping: CmsPost → AnnouncementRead ────────────────────────────────────


def post_to_announcement_read(post: models.CmsPost) -> schemas.AnnouncementRead:
    """Convert a v2 ``CmsPost`` into the v1 ``AnnouncementRead`` contract."""
    seo = post.seo_json or {}
    site = post.site if post.site else None
    category = seo.get("category", "General")
    is_featured = bool(seo.get("is_featured", False))
    return schemas.AnnouncementRead(
        id=post.id,
        title=post.title or "",
        content=post.content or "",
        category=category,
        image_url=post.featured_image_url,
        is_active=post.status != _PostStatus.ARCHIVED,
        is_featured=is_featured,
        status=post.status,  # same values for Announcement and CmsPost
        sede_id=site.sede_id if site else None,
        created_by_persona_id=post.created_by_persona_id,
        published_at=post.published_at or post.created_at,
        created_at=post.created_at,
    )


# ── Mapping: AnnouncementCreate → CmsPostCreate ────────────────────────────


def announcement_create_to_post_create(
    payload: schemas.AnnouncementCreate,
    site_id: uuid.UUID,
    author_persona_id: uuid.UUID | None,
) -> schemas.CmsPostCreate:
    """Convert a v1 ``AnnouncementCreate`` into a v2 ``CmsPostCreate``."""
    _ = site_id
    published_at = datetime.now(timezone.utc) if payload.status == "published" else None
    return schemas.CmsPostCreate(
        slug=f"announcement-{uuid.uuid4().hex[:8]}",
        title=payload.title,
        excerpt=payload.content[:200] if payload.content else None,
        content=payload.content,
        featured_image_url=payload.image_url,
        status=payload.status,
        published_at=published_at,
        seo_json={
            "category": payload.category or "General",
            "is_featured": payload.is_featured,
            "content_type": "announcement",
        },
    )


# ── Mapping: AnnouncementUpdate → CmsPostUpdate ────────────────────────────


def announcement_update_to_post_update(
    payload: schemas.AnnouncementUpdate,
    existing_status: str,
    existing_seo_json: dict | None,
) -> schemas.CmsPostUpdate:
    """Convert a v1 ``AnnouncementUpdate`` into a v2 ``CmsPostUpdate``.

    The existing ``seo_json`` is merged with the new announcement metadata
    so we don't lose fields not present in the v1 update payload.
    """
    seo = dict(existing_seo_json or {})

    if payload.category is not None:
        seo["category"] = payload.category
    if payload.is_featured is not None:
        seo["is_featured"] = payload.is_featured

    update = schemas.CmsPostUpdate(
        title=payload.title,
        content=payload.content,
        featured_image_url=payload.image_url,
        seo_json=seo,
    )

    # Apply status from payload first, then override with is_active
    # deactivation. This ensures is_active=False always archives even
    # when status is also provided.
    if payload.status is not None:
        update.status = payload.status

    if payload.is_active is not None and not payload.is_active:
        update.status = _PostStatus.ARCHIVED

    return update


# ── Site resolution ────────────────────────────────────────────────────────


def get_site_for_sede(db: "Session", sede_id: uuid.UUID | str | None) -> models.CmsSite | None:
    """Return the first active CmsSite belonging to ``sede_id``.

    ``None`` is returned when no site matches. Callers decide whether to
    create a legacy site or raise an error.
    """
    if sede_id is None:
        return None
    return (
        db.query(models.CmsSite)
        .filter(models.CmsSite.sede_id == sede_id, models.CmsSite.is_active.is_(True))
        .order_by(models.CmsSite.created_at.asc())
        .first()
    )


def get_or_create_testimonial_site(
    db: "Session", sede_id: uuid.UUID | str
) -> models.CmsSite:
    """Return an active site for ``sede_id``; create a legacy one if needed.

    This keeps the v1 API working even when a sede has no CMS site yet.
    The created site is clearly marked as legacy so admins can identify it.
    """
    site = get_site_for_sede(db, sede_id)
    if site is not None:
        return site

    short = str(sede_id).split("-")[0]
    site_key = f"legacy-testimonials-{short}"
    site = models.CmsSite(
        site_key=site_key,
        name="Legacy Testimonials Site",
        base_path=f"/legacy-testimonials-{short}",
        is_active=True,
        sede_id=sede_id if isinstance(sede_id, uuid.UUID) else uuid.UUID(str(sede_id)),
    )
    db.add(site)
    db.commit()
    db.refresh(site)
    return site


def get_or_create_testimonial_category(
    db: "Session", site_id: uuid.UUID
) -> models.CmsCategory:
    """Return the 'testimonials' category for ``site_id``, creating it if missing."""
    cat = (
        db.query(models.CmsCategory)
        .filter(
            models.CmsCategory.site_id == site_id,
            models.CmsCategory.slug == TESTIMONIAL_CATEGORY_SLUG,
        )
        .first()
    )
    if cat is not None:
        return cat

    cat = models.CmsCategory(
        site_id=site_id,
        slug=TESTIMONIAL_CATEGORY_SLUG,
        name="Testimonials",
        description="Legacy testimonials migrated to CmsPost",
        is_active=True,
    )
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


# ── Query helpers ──────────────────────────────────────────────────────────


def _as_uuid(value: uuid.UUID | str | None) -> uuid.UUID | None:
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(str(value))


def list_testimonial_posts(
    db: "Session",
    *,
    sede_id: uuid.UUID | str | None = None,
    status: str | None = None,
    include_archived: bool = False,
) -> list[models.CmsPost]:
    """Return CmsPost rows categorized as testimonials, optionally scoped by sede."""
    query = (
        db.query(models.CmsPost)
        .join(models.CmsPost.categories)
        .filter(models.CmsCategory.slug == TESTIMONIAL_CATEGORY_SLUG)
    )
    resolved_sede_id = _as_uuid(sede_id)
    if resolved_sede_id is not None:
        query = query.join(models.CmsSite).filter(models.CmsSite.sede_id == resolved_sede_id)
    if status is not None:
        query = query.filter(models.CmsPost.status == status)
    if not include_archived:
        query = query.filter(models.CmsPost.status != _PostStatus.ARCHIVED)
    return query.distinct().order_by(models.CmsPost.created_at.desc()).all()


def get_testimonial_post_by_id(
    db: "Session",
    post_id: uuid.UUID,
    *,
    sede_id: uuid.UUID | str | None = None,
) -> models.CmsPost | None:
    """Fetch a single testimonial post by id, optionally scoping by sede."""
    query = (
        db.query(models.CmsPost)
        .join(models.CmsPost.categories)
        .filter(models.CmsCategory.slug == TESTIMONIAL_CATEGORY_SLUG)
        .filter(models.CmsPost.id == post_id)
    )
    resolved_sede_id = _as_uuid(sede_id)
    if resolved_sede_id is not None:
        query = query.join(models.CmsSite).filter(models.CmsSite.sede_id == resolved_sede_id)
    return query.distinct().first()


# ── Mapping: CmsPost → TestimonialRead ──────────────────────────────────────


def post_to_testimonial_read(post: models.CmsPost) -> schemas.TestimonialRead:
    """Convert a v2 ``CmsPost`` into the v1 ``TestimonialRead`` contract."""
    seo = post.seo_json or {}
    site = post.site if post.site else None
    return schemas.TestimonialRead(
        id=post.id,
        content=post.content or "",
        emotion=seo.get("emotion", "Gratitud"),
        media_type=seo.get("media_type", "text"),
        media_url=seo.get("media_url"),
        image_url=post.featured_image_url,
        video_url=seo.get("video_url"),
        podcast_url=seo.get("podcast_url"),
        is_approved=_is_approved_from_status(post.status),
        show_on_home=bool(seo.get("show_on_home", False)),
        status=_testimonial_status_from_post(post.status),
        author_persona_id=post.author_persona_id,
        sede_id=site.sede_id if site else None,
        created_at=post.created_at,
    )


# ── Mapping: TestimonialCreate → CmsPostCreate ────────────────────────────


def testimonial_create_to_post_create(
    payload: schemas.TestimonialCreate,
    site_id: uuid.UUID,
    author_persona_id: uuid.UUID | None,
) -> schemas.CmsPostCreate:
    """Convert a v1 ``TestimonialCreate`` into a v2 ``CmsPostCreate``.

    ``site_id`` is the v2 site that corresponds to the v1 ``sede_id``.
    ``author_persona_id`` is resolved server-side from the actor when the
    payload omits it. Note that ``site_id`` and ``author_persona_id`` are
    passed separately to the CRUD layer; they are intentionally not part
    of ``CmsPostCreate`` so the caller keeps control of tenant scope.
    """
    _ = site_id  # consumed by the caller, not the payload
    status = _post_status_from_testimonial(
        is_approved=payload.is_approved,
        status=payload.status,
    )
    # Set published_at only when the post is meant to be public.
    published_at = datetime.now(timezone.utc) if status == _PostStatus.PUBLISHED else None
    return schemas.CmsPostCreate(
        slug=f"testimonial-{uuid.uuid4().hex[:8]}",
        title=f"Testimonial {uuid.uuid4().hex[:4]}",
        excerpt=payload.content[:200] if payload.content else None,
        content=payload.content,
        featured_image_url=payload.image_url,
        status=status,
        published_at=published_at,
        seo_json={
            "emotion": payload.emotion,
            "media_type": payload.media_type,
            "media_url": payload.media_url,
            "video_url": payload.video_url,
            "podcast_url": payload.podcast_url,
            "show_on_home": payload.show_on_home,
            "content_type": "testimonial",
        },
    )


# ── Mapping: TestimonialUpdate → CmsPostUpdate ────────────────────────────


def testimonial_update_to_post_update(
    payload: schemas.TestimonialUpdate,
    existing_status: str,
    existing_seo_json: dict | None,
) -> schemas.CmsPostUpdate:
    """Convert a v1 ``TestimonialUpdate`` into a v2 ``CmsPostUpdate``.

    The existing ``seo_json`` is merged with the new testimonial metadata
    so we don't lose fields not present in the v1 update payload.
    """
    seo = dict(existing_seo_json or {})

    if payload.emotion is not None:
        seo["emotion"] = payload.emotion
    if payload.media_type is not None:
        seo["media_type"] = payload.media_type
    if payload.media_url is not None:
        seo["media_url"] = payload.media_url
    if payload.video_url is not None:
        seo["video_url"] = payload.video_url
    if payload.podcast_url is not None:
        seo["podcast_url"] = payload.podcast_url
    if payload.show_on_home is not None:
        seo["show_on_home"] = payload.show_on_home

    update = schemas.CmsPostUpdate(
        content=payload.content,
        featured_image_url=payload.image_url,
        seo_json=seo,
    )

    # Only touch status when the v1 payload explicitly carries a status
    # or is_approved flag. This avoids unpublishing a post when the
    # caller only wanted to edit the content.
    if payload.status is not None or payload.is_approved is not None:
        current_post_status = _testimonial_status_from_post(existing_status)
        current_is_approved = current_post_status == _TestimonialStatus.APPROVED

        # If a v1 status is supplied it wins over is_approved; map it
        # explicitly so a request like {"status":"pending"} truly drafts
        # an approved post.
        if payload.status is not None:
            is_approved = payload.status == _TestimonialStatus.APPROVED
            target_status = payload.status
        else:
            is_approved = (
                payload.is_approved
                if payload.is_approved is not None
                else current_is_approved
            )
            target_status = current_post_status

        status = _post_status_from_testimonial(
            is_approved=is_approved,
            status=target_status,
        )
        update.status = status

    return update
