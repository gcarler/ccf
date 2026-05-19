"""add multi-role targeting to crm events

Revision ID: 20260505_0009
Revises: 20260505_0008
Create Date: 2026-05-05 11:30:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260505_0009"
down_revision = "20260505_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("crm_events")}

    if "target_role_ids" not in columns:
        op.add_column("crm_events", sa.Column("target_role_ids", sa.JSON(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("crm_events")}

    if "target_role_ids" in columns:
        op.drop_column("crm_events", "target_role_ids")
