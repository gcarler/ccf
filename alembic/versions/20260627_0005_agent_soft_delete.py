"""Add reversible soft deletion to agent tasks and insights.

Revision ID: 20260627_0005_agent_soft_delete
Revises: 20260627_0004_drop_identity
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260627_0005_agent_soft_delete"
down_revision: str | None = "20260627_0004_drop_identity"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("agent_tasks", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_agent_tasks_deleted_at", "agent_tasks", ["deleted_at"])
    op.add_column("agent_insights", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_agent_insights_deleted_at", "agent_insights", ["deleted_at"])


def downgrade() -> None:
    op.drop_index("ix_agent_insights_deleted_at", table_name="agent_insights")
    op.drop_column("agent_insights", "deleted_at")
    op.drop_index("ix_agent_tasks_deleted_at", table_name="agent_tasks")
    op.drop_column("agent_tasks", "deleted_at")
