"""add_cms_forms — tables for CMS contact forms and submissions (R1-BE)

Revision ID: 20260730_0005_add_cms_forms
Revises: 20260730_0004_add_cms_popups
Create Date: 2026-07-30 18:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260730_0005_add_cms_forms"
down_revision = "20260730_0004_add_cms_popups"
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

    if not inspector.has_table("cms_forms"):
        op.create_table(
            "cms_forms",
            sa.Column("id", uuid_t, primary_key=True),
            sa.Column(
                "site_id",
                uuid_t,
                sa.ForeignKey("cms_sites.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("description", sa.String(length=500), nullable=True),
            sa.Column("fields", sa.JSON(), nullable=False, server_default="[]"),
            sa.Column(
                "submit_button_text",
                sa.String(length=100),
                nullable=False,
                server_default="Enviar",
            ),
            sa.Column(
                "success_message",
                sa.String(length=255),
                nullable=False,
                server_default="¡Gracias por tu mensaje!",
            ),
            sa.Column("notify_emails", sa.JSON(), nullable=False, server_default="[]"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )

        op.create_index(
            "ix_cms_forms_site_id",
            "cms_forms",
            ["site_id"],
            unique=False,
        )
        op.create_index(
            "ix_cms_forms_is_active",
            "cms_forms",
            ["is_active"],
            unique=False,
        )

    if not inspector.has_table("cms_form_submissions"):
        op.create_table(
            "cms_form_submissions",
            sa.Column("id", uuid_t, primary_key=True),
            sa.Column(
                "form_id",
                uuid_t,
                sa.ForeignKey("cms_forms.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("data", sa.JSON(), nullable=False),
            sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("ip_address", sa.String(length=45), nullable=True),
        )

        op.create_index(
            "ix_cms_form_submissions_form_id",
            "cms_form_submissions",
            ["form_id"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("cms_form_submissions"):
        op.drop_index("ix_cms_form_submissions_form_id", table_name="cms_form_submissions")
        op.drop_table("cms_form_submissions")

    if inspector.has_table("cms_forms"):
        op.drop_index("ix_cms_forms_is_active", table_name="cms_forms")
        op.drop_index("ix_cms_forms_site_id", table_name="cms_forms")
        op.drop_table("cms_forms")
