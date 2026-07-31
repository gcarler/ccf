"""add_cms_newsletters_subscribers — tables for CMS newsletters and subscribers (R2-BE)

Revision ID: 20260730_0006_add_cms_newsletters_subscribers
Revises: 20260730_0005_add_cms_forms
Create Date: 2026-07-30 19:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260730_0006_add_cms_newsletters_subscribers"
down_revision = "20260730_0005_add_cms_forms"
branch_labels = None
depends_on = None


def _uuid_type() -> sa.types.TypeEngine:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        return sa.dialects.postgresql.UUID(as_uuid=True)
    return sa.String(length=36)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    uuid_t = _uuid_type()

    if not inspector.has_table("cms_newsletters"):
        op.create_table(
            "cms_newsletters",
            sa.Column("id", uuid_t, primary_key=True),
            sa.Column(
                "site_id",
                uuid_t,
                sa.ForeignKey("cms_sites.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("subject", sa.String(length=255), nullable=False),
            sa.Column("content_html", sa.Text(), nullable=False),
            sa.Column(
                "status",
                sa.String(length=20),
                nullable=False,
                server_default="draft",
            ),
            sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "recipient_count",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )

        op.create_index(
            "ix_cms_newsletters_site_id",
            "cms_newsletters",
            ["site_id"],
            unique=False,
        )
        op.create_index(
            "ix_cms_newsletters_status",
            "cms_newsletters",
            ["status"],
            unique=False,
        )

    if not inspector.has_table("cms_subscribers"):
        op.create_table(
            "cms_subscribers",
            sa.Column("id", uuid_t, primary_key=True),
            sa.Column(
                "site_id",
                uuid_t,
                sa.ForeignKey("cms_sites.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("email", sa.String(length=255), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=True),
            sa.Column(
                "is_active",
                sa.Boolean(),
                nullable=False,
                server_default="true",
            ),
            sa.Column("subscribed_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("unsubscribed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "source",
                sa.String(length=50),
                nullable=False,
                server_default="manual",
            ),
            sa.UniqueConstraint("site_id", "email", name="uq_cms_subscribers_site_email"),
        )

        op.create_index(
            "ix_cms_subscribers_site_id",
            "cms_subscribers",
            ["site_id"],
            unique=False,
        )
        op.create_index(
            "ix_cms_subscribers_is_active",
            "cms_subscribers",
            ["is_active"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("cms_subscribers"):
        op.drop_index("ix_cms_subscribers_is_active", table_name="cms_subscribers")
        op.drop_index("ix_cms_subscribers_site_id", table_name="cms_subscribers")
        op.drop_table("cms_subscribers")

    if inspector.has_table("cms_newsletters"):
        op.drop_index("ix_cms_newsletters_status", table_name="cms_newsletters")
        op.drop_index("ix_cms_newsletters_site_id", table_name="cms_newsletters")
        op.drop_table("cms_newsletters")
