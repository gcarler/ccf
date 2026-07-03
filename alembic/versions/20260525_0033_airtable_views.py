"""Create airtable_views table for saved AirTable views.

Revision ID: 20260525_0032
Revises: 20260525_0031
Create Date: 2026-05-25
"""
import sqlalchemy as sa

from alembic import op

revision = "20260525_0033"
down_revision = "20260525_0032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "airtable_views",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("schema_json", sa.JSON, nullable=True),
        sa.Column("filters_json", sa.JSON, nullable=True),
        sa.Column("grouping_json", sa.JSON, nullable=True),
        sa.Column("conditional_format_json", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), index=True),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("airtable_views")
