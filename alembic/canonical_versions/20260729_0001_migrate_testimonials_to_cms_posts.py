"""migrate legacy testimonials to cms_posts

Revision ID: 20260729_0001_migrate_testimonials_to_cms_posts
Revises: c24a34143cda
Create Date: 2026-07-29 23:30:54.147946

Migrates every row from the legacy ``testimonials`` table into a
``CmsPost`` row categorized as ``testimonials``.

The migration preserves the original ``id`` so that v1 API consumers do
not have to update any references. For each ``sede_id`` found in the
legacy table, an active ``CmsSite`` is reused or created on the fly, and
a ``CmsCategory`` with slug ``testimonials`` is attached to the new post.

Status mapping:
  - legacy ``status='archived'``       → ``'archived'``
  - legacy ``is_approved=True``          → ``'published'``
  - otherwise                            → ``'draft'``

The migration is idempotent: posts whose ``id`` already exists in
``cms_posts`` are skipped.
"""

from __future__ import annotations

import uuid
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260729_0001_migrate_testimonials_to_cms_posts"
down_revision: Union[str, None] = "c24a34143cda"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TESTIMONIALS_SLUG = "testimonials"


def _map_status(is_approved: bool, legacy_status: str | None) -> str:
    if legacy_status == "archived":
        return "archived"
    if is_approved:
        return "published"
    return "draft"


def _build_seo_json(row) -> dict:
    seo = {
        "emotion": row.emotion or "Gratitud",
        "media_type": row.media_type or "text",
        "content_type": "testimonial",
    }
    for field in ("media_url", "video_url", "podcast_url"):
        value = getattr(row, field, None)
        if value:
            seo[field] = value
    if row.show_on_home:
        seo["show_on_home"] = True
    return seo


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # If the legacy table is gone we have nothing to migrate.
    if "testimonials" not in inspector.get_table_names():
        return

    metadata = sa.MetaData()
    metadata.reflect(
        bind=bind,
        only=["testimonials", "cms_sites", "cms_categories", "cms_posts", "cms_post_categories"],
    )

    testimonials = metadata.tables["testimonials"]
    cms_sites = metadata.tables["cms_sites"]
    cms_categories = metadata.tables["cms_categories"]
    cms_posts = metadata.tables["cms_posts"]
    cms_post_categories = metadata.tables["cms_post_categories"]

    # Cache existing post IDs to avoid duplicates.
    existing_post_ids = {str(row[0]) for row in bind.execute(sa.select(cms_posts.c.id))}

    site_cache: dict[str, uuid.UUID] = {}
    category_cache: dict[uuid.UUID, uuid.UUID] = {}

    # Order by sede_id so we can reuse site/category lookups.
    rows = bind.execute(sa.select(testimonials).order_by(testimonials.c.sede_id)).fetchall()

    for row in rows:
        testimonial_id = uuid.UUID(str(row.id))
        if str(testimonial_id) in existing_post_ids:
            continue

        sede_id = uuid.UUID(str(row.sede_id))
        site_id = site_cache.get(str(sede_id))

        if site_id is None:
            site_row = bind.execute(
                sa.select(cms_sites.c.id)
                .where(cms_sites.c.sede_id == sede_id)
                .where(cms_sites.c.is_active.is_(True))
                .order_by(cms_sites.c.created_at)
                .limit(1)
            ).fetchone()
            if site_row:
                site_id = uuid.UUID(str(site_row[0]))
            else:
                site_id = uuid.uuid4()
                short = str(sede_id).split("-")[0]
                bind.execute(
                    sa.insert(cms_sites).values(
                        id=site_id,
                        site_key=f"legacy-testimonials-{short}",
                        name="Legacy Testimonials Site",
                        base_path=f"/legacy-testimonials-{short}",
                        is_active=True,
                        sede_id=sede_id,
                    )
                )
            site_cache[str(sede_id)] = site_id

        category_id = category_cache.get(site_id)
        if category_id is None:
            cat_row = bind.execute(
                sa.select(cms_categories.c.id)
                .where(cms_categories.c.site_id == site_id)
                .where(cms_categories.c.slug == TESTIMONIALS_SLUG)
                .limit(1)
            ).fetchone()
            if cat_row:
                category_id = uuid.UUID(str(cat_row[0]))
            else:
                category_id = uuid.uuid4()
                bind.execute(
                    sa.insert(cms_categories).values(
                        id=category_id,
                        site_id=site_id,
                        slug=TESTIMONIALS_SLUG,
                        name="Testimonials",
                        description="Legacy testimonials migrated to CmsPost",
                        is_active=True,
                    )
                )
            category_cache[site_id] = category_id

        content = row.content or ""
        status = _map_status(bool(row.is_approved), row.status)
        published_at = row.created_at if status == "published" else None
        seo_json = _build_seo_json(row)
        slug = f"testimonial-{testimonial_id.hex[:8]}"
        title = content[:50] if content else "Testimonial"
        excerpt = content[:200] if content else None

        bind.execute(
            sa.insert(cms_posts).values(
                id=testimonial_id,
                site_id=site_id,
                slug=slug,
                title=title,
                excerpt=excerpt,
                content=content,
                featured_image_url=row.image_url,
                status=status,
                seo_json=seo_json,
                locale="es",
                published_at=published_at,
                author_persona_id=row.author_persona_id,
                created_by_persona_id=row.author_persona_id,
                updated_by_persona_id=row.author_persona_id,
                created_at=row.created_at,
            )
        )

        # Link the new post with the testimonials category.
        bind.execute(
            sa.insert(cms_post_categories).values(
                post_id=testimonial_id,
                category_id=category_id,
            )
        )


def downgrade() -> None:
    """Downgrade is intentionally manual: deleting migrated CmsPost rows
    would also remove any new testimonials created via the v1 API after
    the migration, which is unsafe. To revert, restore the legacy table
    from a backup.
    """
    pass
