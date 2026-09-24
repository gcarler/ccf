"""Projects Super-PRO: Time Tracking and Task Timesheets Management."""

from __future__ import annotations

from typing import Sequence, Union
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from alembic import op

revision: str = "20260924_0005_projects_super_pro_time_tracking"
down_revision: Union[str, None] = "20260924_0004_projects_super_pro_baselines"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "project_time_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("task_id", UUID(as_uuid=True), sa.ForeignKey("project_tasks.id", ondelete="CASCADE"), nullable=True),
        sa.Column("persona_id", UUID(as_uuid=True), sa.ForeignKey("personas.id", ondelete="SET NULL"), nullable=False),
        sa.Column("hours", sa.Float(), nullable=False),
        sa.Column("date", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_billable", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_project_time_logs_project_id", "project_time_logs", ["project_id"])
    op.create_index("ix_project_time_logs_task_id", "project_time_logs", ["task_id"])
    op.create_index("ix_project_time_logs_persona_id", "project_time_logs", ["persona_id"])
    op.create_index("ix_project_time_logs_date", "project_time_logs", ["date"])
    op.create_index("ix_project_time_logs_deleted_at", "project_time_logs", ["deleted_at"])


def downgrade() -> None:
    op.drop_table("project_time_logs")
