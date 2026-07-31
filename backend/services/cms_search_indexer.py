"""CMS Search Auto-Indexing Service.

Provides content extraction, upserting into SearchIndex, deletion, and bulk re-indexing
for pages, posts, and other CMS content.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from backend.models_cms import CmsPage, CmsPost, CmsSite
from backend.models_enterprise import SearchIndex

logger = logging.getLogger(__name__)


def _extract_text_from_sections(sections: list[Any]) -> str:
    """Extract readable text from page section props_json."""
    extracted: list[str] = []
    for sec in sections:
        props = getattr(sec, "props_json", {}) or {}
        if isinstance(props, dict):
            for key, val in props.items():
                if isinstance(val, str) and val.strip():
                    extracted.append(val.strip())
                elif isinstance(val, list):
                    for item in val:
                        if isinstance(item, str) and item.strip():
                            extracted.append(item.strip())
                        elif isinstance(item, dict):
                            for sub_k, sub_v in item.items():
                                if isinstance(sub_v, str) and sub_v.strip():
                                    extracted.append(sub_v.strip())
    return " ".join(extracted)


def index_cms_content(
    db: Session,
    site_key: str,
    entity_type: str,
    entity_id: str,
    entity_slug: str | None,
    title: str | None,
    body_text: str | None,
    category: str | None = None,
    author: Any = None,
    tags: list[str] | None = None,
    is_published: bool = True,
    boost_score: int = 0,
    locale: str = "es",
) -> SearchIndex:
    """Upsert a content item into cms_search_index table."""
    author_persona_id: uuid.UUID | None = None
    if author:
        if isinstance(author, uuid.UUID):
            author_persona_id = author
        elif isinstance(author, str):
            try:
                author_persona_id = uuid.UUID(author)
            except ValueError:
                author_persona_id = None

    tags_list = tags if isinstance(tags, list) else []

    item = (
        db.query(SearchIndex)
        .filter(
            SearchIndex.site_key == site_key,
            SearchIndex.entity_type == entity_type,
            SearchIndex.entity_id == entity_id,
        )
        .first()
    )

    now = datetime.now(timezone.utc)
    ts_vector_text = f"{title or ''} {body_text or ''}".strip()

    if not item:
        item = SearchIndex(
            id=uuid.uuid4(),
            site_key=site_key,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_slug=entity_slug,
            title=title,
            body_text=body_text,
            category=category,
            author_persona_id=author_persona_id,
            tags=tags_list,
            locale=locale,
            is_published=is_published,
            boost_score=boost_score,
            ts_vector=ts_vector_text,
            last_indexed_at=now,
            created_at=now,
            updated_at=now,
        )
        db.add(item)
    else:
        item.entity_slug = entity_slug
        item.title = title
        item.body_text = body_text
        item.category = category
        item.author_persona_id = author_persona_id
        item.tags = tags_list
        item.locale = locale
        item.is_published = is_published
        item.boost_score = boost_score
        item.ts_vector = ts_vector_text
        item.last_indexed_at = now
        item.updated_at = now

    try:
        db.commit()
        db.refresh(item)
    except Exception as exc:
        db.rollback()
        logger.exception(f"Failed to index CMS content {entity_type}/{entity_id}: {exc}")
        raise

    return item


def delete_from_search_index(db: Session, site_key: str, entity_type: str, entity_id: str) -> bool:
    """Remove indexed item from search index upon deletion or unpublishing."""
    item = (
        db.query(SearchIndex)
        .filter(
            SearchIndex.site_key == site_key,
            SearchIndex.entity_type == entity_type,
            SearchIndex.entity_id == entity_id,
        )
        .first()
    )

    if item:
        db.delete(item)
        try:
            db.commit()
            return True
        except Exception as exc:
            db.rollback()
            logger.exception(f"Failed to delete search index entry {entity_type}/{entity_id}: {exc}")
            raise
    return False


def index_cms_page(db: Session, page: CmsPage) -> SearchIndex:
    """Extract content from CmsPage and index it."""
    site_key = page.site.site_key if page.site else "ccf"
    body_text = _extract_text_from_sections(getattr(page, "sections", []) or [])
    is_published = page.status == "published" and getattr(page, "deleted_at", None) is None

    return index_cms_content(
        db=db,
        site_key=site_key,
        entity_type="page",
        entity_id=str(page.id),
        entity_slug=page.slug,
        title=page.title,
        body_text=body_text,
        category=None,
        author=getattr(page, "created_by_persona_id", None),
        tags=None,
        is_published=is_published,
        locale=getattr(page, "locale", "es") or "es",
    )


def index_cms_post(db: Session, post: CmsPost) -> SearchIndex:
    """Extract content from CmsPost and index it."""
    site_key = post.site.site_key if post.site else "ccf"
    body_text = f"{post.excerpt or ''}\n{post.content or ''}".strip()
    categories = getattr(post, "categories", []) or []
    category_slug = categories[0].slug if categories else None
    tags = getattr(post, "tags", []) or []
    tag_slugs = [t.slug for t in tags]
    is_published = post.status == "published"

    return index_cms_content(
        db=db,
        site_key=site_key,
        entity_type="post",
        entity_id=str(post.id),
        entity_slug=post.slug,
        title=post.title,
        body_text=body_text,
        category=category_slug,
        author=getattr(post, "author_persona_id", None),
        tags=tag_slugs,
        is_published=is_published,
        locale=getattr(post, "locale", "es") or "es",
    )


def reindex_all_cms_content(db: Session, site_key: str | None = None) -> dict[str, Any]:
    """Bulk re-index all pages and posts in CMS."""
    indexed_pages = 0
    indexed_posts = 0

    pages_query = db.query(CmsPage)
    posts_query = db.query(CmsPost)

    if site_key:
        site = db.query(CmsSite).filter(CmsSite.site_key == site_key).first()
        if site:
            pages_query = pages_query.filter(CmsPage.site_id == site.id)
            posts_query = posts_query.filter(CmsPost.site_id == site.id)
        else:
            return {
                "status": "completed",
                "site_key": site_key,
                "indexed_pages": 0,
                "indexed_posts": 0,
                "total_indexed": 0,
            }

    pages = pages_query.all()
    for page in pages:
        index_cms_page(db, page)
        indexed_pages += 1

    posts = posts_query.all()
    for post in posts:
        index_cms_post(db, post)
        indexed_posts += 1

    total_indexed = indexed_pages + indexed_posts
    return {
        "status": "completed",
        "site_key": site_key,
        "indexed_pages": indexed_pages,
        "indexed_posts": indexed_posts,
        "total_indexed": total_indexed,
    }
