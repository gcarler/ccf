"""Add version column to wiki_pages and create wiki_page_versions table.

Revision ID: 20260717_0004
Revises: 20260717_0003
Create Date: 2026-07-17 00:00:04
"""

from alembic import op
import sqlalchemy as sa

revision = "20260717_0004"
down_revision = "20260717_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add version column to wiki_pages
    op.add_column(
        "wiki_pages",
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
    )

    # Create wiki_page_versions table
    op.create_table(
        "wiki_page_versions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("wiki_page_id", sa.UUID(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_by_persona_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["created_by_persona_id"],
            ["personas.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["wiki_page_id"],
            ["wiki_pages.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_wiki_page_versions_wiki_page_id",
        "wiki_page_versions",
        ["wiki_page_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("wiki_page_versions")
    op.drop_column("wiki_pages", "version")
