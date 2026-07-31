"""add_cms_popups — table for native CMS popups (R3-BE)

Revision ID: 20260730_0004_add_cms_popups
Revises: 20260730_0003_drop_legacy_announcements_table
Create Date: 2026-07-30 17:30:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260730_0004_add_cms_popups"
down_revision = "20260730_0003_drop_legacy_announcements_table"
branch_labels = None
depends_on = None


def _uuid_type() -> sa.types.TypeEngine:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        return sa.dialects.postgresql.UUID(as_uuid=True)
    return sa.String(length=36)


def upgrade() -> None:
    bind = op.get_bind()
    if sa.inspect(bind).has_table("cms_popups"):
        return

    uuid_t = _uuid_type()
    op.create_table(
        "cms_popups",
        sa.Column("id", uuid_t, primary_key=True),
        sa.Column(
            "site_id",
            uuid_t,
            sa.ForeignKey("cms_sites.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("content_html", sa.Text(), nullable=False, server_default=""),
        sa.Column("trigger_type", sa.String(length=50), nullable=False, server_default="on_load"),
        sa.Column("trigger_value", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("show_on_pages", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_index(
        "ix_cms_popups_site_id",
        "cms_popups",
        ["site_id"],
        unique=False,
    )
    op.create_index(
        "ix_cms_popups_is_active",
        "cms_popups",
        ["is_active"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_cms_popups_is_active", table_name="cms_popups")
    op.drop_index("ix_cms_popups_site_id", table_name="cms_popups")
    op.drop_table("cms_popups")
