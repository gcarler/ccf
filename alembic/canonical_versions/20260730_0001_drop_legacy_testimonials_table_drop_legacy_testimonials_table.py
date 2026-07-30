"""drop legacy testimonials table

Revision ID: 20260730_0001_drop_legacy_testimonials_table
Revises: 20260729_0001_migrate_testimonials_to_cms_posts
Create Date: 2026-07-30 01:57:29.710625

Pre-requisites
--------------
1. The data migration ``20260729_0001_migrate_testimonials_to_cms_posts``
   MUST have been applied to copy all legacy rows into ``cms_posts``.
2. The application code MUST have been deployed so that no endpoint reads
   from the legacy ``testimonials`` table anymore.

After this migration the legacy ``is_approved`` / ``show_on_home`` /
``sede_id`` columns live exclusively in ``cms_posts.seo_json`` (via the
adapter layer in ``backend.api.cms_v1_adapters``).

The downgrade recreates the table structure but does NOT repopulate data
from ``cms_posts`` (that would be a data-migration concern).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260730_0001_drop_legacy_testimonials_table"
down_revision: Union[str, None] = "20260729_0001_migrate_testimonials_to_cms_posts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop the legacy ``testimonials`` table.

    All data has been migrated to ``cms_posts`` in the preceding migration
    (``20260729_0001_migrate_testimonials_to_cms_posts``). The v1 API
    shim (``backend.api.cms_v1_adapters``) reads/writes ``CmsPost`` rows
    exclusively after the code deploy.
    """
    op.drop_table("testimonials")


def downgrade() -> None:
    """Recreate the ``testimonials`` table (empty).

    This is purely a structural rollback — data that was migrated to
    ``cms_posts`` is NOT copied back. If you need to restore the legacy
    data, run the data-migration in reverse (or restore from backup)
    before executing this downgrade.
    """
    op.create_table(
        "testimonials",
        sa.Column("id", UUID(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("emotion", sa.String(length=100), server_default="Gratitud"),
        sa.Column("media_type", sa.String(length=20), server_default="text"),
        sa.Column("media_url", sa.String(length=500), nullable=True),
        sa.Column("image_url", sa.String(length=500), nullable=True),
        sa.Column("video_url", sa.String(length=500), nullable=True),
        sa.Column("podcast_url", sa.String(length=500), nullable=True),
        sa.Column("is_approved", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("show_on_home", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("status", sa.String(length=20), server_default="pending"),
        sa.Column("author_persona_id", UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("sede_id", UUID(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
