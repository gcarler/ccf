"""Add landing_page and campaign columns to consolidation_pipeline for UTM attribution.

Revision ID: 20260524_0028
Revises: 20260524_0027
Create Date: 2026-05-24

Task 3.3: Campaign Attribution System
"""
from alembic import op
import sqlalchemy as sa

revision = "20260524_0028"
down_revision = "20260524_0027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "consolidation_pipeline",
        sa.Column("landing_page", sa.String(500), nullable=True),
    )
    op.add_column(
        "consolidation_pipeline",
        sa.Column("campaign", sa.String(200), nullable=True),
    )
    # Index for filtering pipeline leads by campaign
    op.create_index(
        "ix_pipeline_campaign",
        "consolidation_pipeline",
        ["campaign"],
    )


def downgrade() -> None:
    op.drop_index("ix_pipeline_campaign", table_name="consolidation_pipeline")
    op.drop_column("consolidation_pipeline", "campaign")
    op.drop_column("consolidation_pipeline", "landing_page")
