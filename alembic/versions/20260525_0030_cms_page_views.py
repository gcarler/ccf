"""Create cms_page_views table for analytics.

Revision ID: 20260525_0030
Revises: 20260525_0029
Create Date: 2026-05-25
"""
from alembic import op
import sqlalchemy as sa

revision = "20260525_0030"
down_revision = "20260525_0029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cms_page_views",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("page_id", sa.Integer, sa.ForeignKey("cms_pages.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("referrer", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), index=True),
    )
    op.create_index("ix_cms_page_views_page_date", "cms_page_views", ["page_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_cms_page_views_page_date", table_name="cms_page_views")
    op.drop_table("cms_page_views")
