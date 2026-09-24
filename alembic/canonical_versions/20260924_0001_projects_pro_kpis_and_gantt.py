"""Projects PRO: KPIs, progress modes, and task dependencies for Gantt."""

from __future__ import annotations

from typing import Sequence, Union
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from alembic import op

revision: str = "20260924_0001_projects_pro_kpis_and_gantt"
down_revision: Union[str, None] = "20260901_0015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add PRO fields to `projects`
    op.add_column("projects", sa.Column("start_date", sa.DateTime(timezone=True), nullable=True))
    op.add_column("projects", sa.Column("target_date", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "projects",
        sa.Column("progress_mode", sa.String(length=20), server_default="auto_tasks", nullable=False),
    )
    op.add_column(
        "projects",
        sa.Column("manual_progress", sa.Float(), server_default="0", nullable=False),
    )
    op.add_column("projects", sa.Column("budget_allocated", sa.Float(), nullable=True))
    op.add_column("projects", sa.Column("budget_spent", sa.Float(), nullable=True))
    op.add_column("projects", sa.Column("health_override", sa.String(length=20), nullable=True))

    # 2. Create `project_kpis` table
    op.create_table(
        "project_kpis",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("target_value", sa.Float(), nullable=False),
        sa.Column("current_value", sa.Float(), server_default="0", nullable=False),
        sa.Column("unit", sa.String(length=30), server_default="unidades", nullable=False),
        sa.Column("category", sa.String(length=50), server_default="impact", nullable=False),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_project_kpis_project_id", "project_kpis", ["project_id"])
    op.create_index("ix_project_kpis_deleted_at", "project_kpis", ["deleted_at"])

    # 3. Create `project_task_dependencies` table
    op.create_table(
        "project_task_dependencies",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("predecessor_id", UUID(as_uuid=True), sa.ForeignKey("project_tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("successor_id", UUID(as_uuid=True), sa.ForeignKey("project_tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("dependency_type", sa.String(length=10), server_default="FS", nullable=False),
        sa.Column("lag_days", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("predecessor_id", "successor_id", name="uq_project_task_dependency_pair"),
    )
    op.create_index("ix_project_task_dependencies_project_id", "project_task_dependencies", ["project_id"])
    op.create_index("ix_project_task_dependencies_predecessor_id", "project_task_dependencies", ["predecessor_id"])
    op.create_index("ix_project_task_dependencies_successor_id", "project_task_dependencies", ["successor_id"])


def downgrade() -> None:
    op.drop_table("project_task_dependencies")
    op.drop_table("project_kpis")
    op.drop_column("projects", "health_override")
    op.drop_column("projects", "budget_spent")
    op.drop_column("projects", "budget_allocated")
    op.drop_column("projects", "manual_progress")
    op.drop_column("projects", "progress_mode")
    op.drop_column("projects", "target_date")
    op.drop_column("projects", "start_date")
