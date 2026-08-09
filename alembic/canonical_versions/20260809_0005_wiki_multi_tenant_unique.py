"""Fix wiki_pages unique constraint for multi-tenant isolation.

The original schema had a global unique constraint on page_key alone,
which prevented two different sedes from having a page with the same key.
Replace it with a composite unique constraint on (page_key, sede_id) so
each sede can independently own pages with the same key.

Revision ID: 20260809_0005
Revises: 20260809_0004
Create Date: 2026-08-09
"""

import sqlalchemy as sa

from alembic import op

revision = "20260809_0005_wiki_multi_tenant"
down_revision = "20260809_0004_orm_sync"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the global unique index on page_key
    op.drop_index("ix_wiki_pages_page_key", table_name="wiki_pages")
    # Recreate as non-unique index for fast lookups
    op.create_index("ix_wiki_pages_page_key", "wiki_pages", ["page_key"], unique=False)
    # Add composite unique constraint for true multi-tenant isolation
    op.create_unique_constraint(
        "uq_wiki_pages_key_sede",
        "wiki_pages",
        ["page_key", "sede_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_wiki_pages_key_sede", "wiki_pages", type_="unique")
    op.drop_index("ix_wiki_pages_page_key", table_name="wiki_pages")
    op.create_index("ix_wiki_pages_page_key", "wiki_pages", ["page_key"], unique=True)