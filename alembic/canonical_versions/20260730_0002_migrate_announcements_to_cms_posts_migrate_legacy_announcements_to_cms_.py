"""migrate legacy announcements to cms_posts

Revision ID: 20260730_0002_migrate_announcements_to_cms_posts
Revises: 20260730_0001_drop_legacy_testimonials_table
Create Date: 2026-07-30 02:35:10.666890

Migrates every row from the legacy ``announcements`` table into a
``CmsPost`` row categorized as ``announcements``.

The migration preserves the original ``id`` so that v1 API consumers do
not have to update any references. For each ``sede_id`` found in the
legacy table, an active ``CmsSite`` is reused or created on the fly, and
a ``CmsCategory`` with slug ``announcements`` is attached to the new post.

Status mapping:
  - Announcement.status and CmsPost.status use the same values
    (``draft``, ``published``, ``archived``) — direct copy.

The migration is idempotent: posts whose ``id`` already exists in
``cms_posts`` are skipped.
"""
import uuid
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260730_0002_migrate_announcements_to_cms_posts"
down_revision: Union[str, None] = "20260729_0001_migrate_testimonials_to_cms_posts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ANNOUNCEMENTS_SLUG = "announcements"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # If the legacy table is gone we have nothing to migrate.
    if "announcements" not in inspector.get_table_names():
        return

    metadata = sa.MetaData()
    metadata.reflect(
        bind=bind,
        only=[
            "announcements",
            "cms_sites",
            "cms_categories",
            "cms_posts",
            "cms_post_categories",
        ],
    )

    announcements = metadata.tables["announcements"]
    cms_sites = metadata.tables["cms_sites"]
    cms_categories = metadata.tables["cms_categories"]
    cms_posts = metadata.tables["cms_posts"]
    cms_post_categories = metadata.tables["cms_post_categories"]

    # Cache existing post IDs to avoid duplicates.
    existing_post_ids = {
        str(row[0]) for row in bind.execute(sa.select(cms_posts.c.id))
    }

    site_cache: dict[str, uuid.UUID] = {}
    category_cache: dict[uuid.UUID, uuid.UUID] = {}

    # Order by sede_id so we can reuse site/category lookups.
    rows = bind.execute(
        sa.select(announcements).order_by(announcements.c.sede_id)
    ).fetchall()

    for row in rows:
        announcement_id = uuid.UUID(str(row.id))
        if str(announcement_id) in existing_post_ids:
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
                        site_key=f"legacy-announcements-{short}",
                        name="Legacy Announcements Site",
                        base_path=f"/legacy-announcements-{short}",
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
                .where(cms_categories.c.slug == ANNOUNCEMENTS_SLUG)
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
                        slug=ANNOUNCEMENTS_SLUG,
                        name="Announcements",
                        description="Legacy announcements migrated to CmsPost",
                        is_active=True,
                    )
                )
            category_cache[site_id] = category_id

        content = row.content or ""
        status = row.status or "published"
        slug = f"announcement-{announcement_id.hex[:8]}"
        title = row.title or content[:50] or "Announcement"
        excerpt = content[:200] if content else None
        is_featured = bool(row.is_featured) if hasattr(row, "is_featured") else False
        category = getattr(row, "category", None) or "General"

        bind.execute(
            sa.insert(cms_posts).values(
                id=announcement_id,
                site_id=site_id,
                slug=slug,
                title=title,
                excerpt=excerpt,
                content=content,
                featured_image_url=row.image_url if hasattr(row, "image_url") else None,
                status=status,
                seo_json={
                    "category": category,
                    "is_featured": is_featured,
                    "content_type": "announcement",
                },
                locale="es",
                published_at=row.published_at if hasattr(row, "published_at") else None,
                created_by_persona_id=row.created_by_persona_id,
                updated_by_persona_id=row.created_by_persona_id,
                created_at=row.created_at,
            )
        )

        # Link the new post with the announcements category.
        bind.execute(
            sa.insert(cms_post_categories).values(
                post_id=announcement_id,
                category_id=category_id,
            )
        )


def downgrade() -> None:
    """Downgrade is intentionally manual: deleting migrated CmsPost rows
    would also remove any new announcements created via the v1 API after
    the migration, which is unsafe. To revert, restore the legacy table
    from a backup.
    """
    pass
