"""Add visual_color column to crm_etapas_pipeline.

Revision ID: 20260710_0003
Revises: 20260710_0002
Create Date: 2026-07-10
"""

from alembic import op
import sqlalchemy as sa

revision = "20260710_0003"
down_revision = "20260710_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "crm_etapas_pipeline",
        sa.Column("visual_color", sa.String(50), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("crm_etapas_pipeline", "visual_color")
