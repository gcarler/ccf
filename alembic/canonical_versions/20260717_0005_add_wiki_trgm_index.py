"""Add pg_trgm extension and trigram index for wiki_pages search.

Improves ILIKE search performance on wiki_pages.title and wiki_pages.page_key
by using a GiST trigram index.

Revision ID: 20260717_0005
Revises: 20260717_0004
Create Date: 2026-07-17 00:00:05
"""

from alembic import op
import sqlalchemy as sa

revision = "20260717_0005"
down_revision = "20260717_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.create_index(
        "ix_wiki_pages_title_trgm",
        "wiki_pages",
        [sa.text("title gin_trgm_ops")],
        postgresql_using="gin",
    )
    op.create_index(
        "ix_wiki_pages_page_key_trgm",
        "wiki_pages",
        [sa.text("page_key gin_trgm_ops")],
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("ix_wiki_pages_page_key_trgm")
    op.drop_index("ix_wiki_pages_title_trgm")
