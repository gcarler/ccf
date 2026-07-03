"""Add is_global and global_key columns to cms_sections for reusable blocks.

Revision ID: 20260525_0029
Revises: 20260524_0028
Create Date: 2026-05-25

Task: CMS Phase 3 - Reusable/Global Blocks
"""
import sqlalchemy as sa

from alembic import op

revision = "20260525_0029"
down_revision = "20260524_0031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cms_sections",
        sa.Column("is_global", sa.Boolean(), nullable=True, server_default="0"),
    )
    op.add_column(
        "cms_sections",
        sa.Column("global_key", sa.String(120), nullable=True),
    )
    op.create_index("ix_cms_sections_is_global", "cms_sections", ["is_global"])
    op.create_index("ix_cms_sections_global_key", "cms_sections", ["global_key"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_cms_sections_global_key", table_name="cms_sections")
    op.drop_index("ix_cms_sections_is_global", table_name="cms_sections")
    op.drop_column("cms_sections", "global_key")
    op.drop_column("cms_sections", "is_global")
