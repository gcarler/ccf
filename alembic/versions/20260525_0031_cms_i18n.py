"""Add locale support to cms_pages and cms_sections for multi-language.

Revision ID: 20260525_0031
Revises: 20260525_0030
Create Date: 2026-05-25
"""
from alembic import op
import sqlalchemy as sa

revision = "20260525_0031"
down_revision = "20260525_0030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cms_pages",
        sa.Column("locale", sa.String(5), nullable=True, server_default="es"),
    )
    op.add_column(
        "cms_sections",
        sa.Column("locale", sa.String(5), nullable=True, server_default="es"),
    )
    op.create_index("ix_cms_pages_locale", "cms_pages", ["locale"])
    op.create_index("ix_cms_sections_locale", "cms_sections", ["locale"])


def downgrade() -> None:
    op.drop_index("ix_cms_sections_locale", table_name="cms_sections")
    op.drop_index("ix_cms_pages_locale", table_name="cms_pages")
    op.drop_column("cms_sections", "locale")
    op.drop_column("cms_pages", "locale")
