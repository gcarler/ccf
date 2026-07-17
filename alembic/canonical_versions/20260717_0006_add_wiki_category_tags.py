"""Add category and tags columns to wiki_pages.

Revision ID: 20260717_0006
Revises: 20260717_0005
Create Date: 2026-07-17 00:00:06
"""

from alembic import op
import sqlalchemy as sa

revision = "20260717_0006"
down_revision = "20260717_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "wiki_pages",
        sa.Column("category", sa.String(100), nullable=True),
    )
    op.add_column(
        "wiki_pages",
        sa.Column("tags", sa.JSON(), nullable=True),
    )
    op.create_index("ix_wiki_pages_category", "wiki_pages", ["category"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_wiki_pages_category", "wiki_pages")
    op.drop_column("wiki_pages", "tags")
    op.drop_column("wiki_pages", "category")
