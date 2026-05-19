"""add campaign name to communication logs

Revision ID: 20260503_0005
Revises: 20260502_0004
Create Date: 2026-05-03 08:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260503_0005"
down_revision = "20260502_0004"
branch_labels = None
depends_on = None


def _has_column(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("communication_logs") and not _has_column(inspector, "communication_logs", "campaign_name"):
        with op.batch_alter_table("communication_logs") as batch_op:
            batch_op.add_column(sa.Column("campaign_name", sa.String(length=200), nullable=True))

        op.create_index(
            "ix_communication_logs_campaign_name",
            "communication_logs",
            ["campaign_name"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("communication_logs") and _has_column(inspector, "communication_logs", "campaign_name"):
        op.drop_index("ix_communication_logs_campaign_name", table_name="communication_logs")
        with op.batch_alter_table("communication_logs") as batch_op:
            batch_op.drop_column("campaign_name")
