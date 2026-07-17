"""Add sede_id and author_id to wiki_pages for multi-tenant isolation.

Revision ID: 20260717_0003
Revises: 20260717_0002
Create Date: 2026-07-17 00:00:03
"""

from alembic import op
import sqlalchemy as sa

revision = "20260717_0003"
down_revision = "20260717_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "wiki_pages",
        sa.Column(
            "sede_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.add_column(
        "wiki_pages",
        sa.Column(
            "author_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_wiki_pages_sede_id",
        "wiki_pages",
        ["sede_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_wiki_pages_sede_id",
        "wiki_pages",
        "sedes",
        ["sede_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_wiki_pages_author_id",
        "wiki_pages",
        "personas",
        ["author_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_wiki_pages_author_id", "wiki_pages", type_="foreignkey")
    op.drop_constraint("fk_wiki_pages_sede_id", "wiki_pages", type_="foreignkey")
    op.drop_index("ix_wiki_pages_sede_id", "wiki_pages")
    op.drop_column("wiki_pages", "author_id")
    op.drop_column("wiki_pages", "sede_id")
