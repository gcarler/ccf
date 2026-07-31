"""drop legacy announcements table

Revision ID: 20260730_0003_drop_legacy_announcements_table
Revises: 0461885be9c9
Create Date: 2026-07-30 03:20:08.828072

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260730_0003_drop_legacy_announcements_table"
down_revision: Union[str, None] = "0461885be9c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table("announcements")


def downgrade() -> None:
    """Structural downgrade: re-create the announcements table.

    NOTE: data that was migrated to ``cms_posts`` is NOT restored.
    """
    op.create_table(
        "announcements",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("category", sa.String(100), server_default="General"),
        sa.Column("image_url", sa.String(500), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("is_featured", sa.Boolean(), server_default="false"),
        sa.Column("status", sa.String(20), server_default="published"),
        sa.Column("sede_id", sa.UUID(), nullable=False),
        sa.Column("created_by_persona_id", sa.UUID(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_announcements_status", "announcements", ["status"])
    op.create_index("ix_announcements_sede_id", "announcements", ["sede_id"])
