"""Add physical_progress_pct and estimated_hours to project_tasks, and task_id to project_expenses.

Revision ID: 20261009_0002_project_task_dimensions_rollup
Revises: 20261009_0001_project_components_edt_level2
Create Date: 2026-10-09 05:15:00

Implements WBS/EDT Level 3 & Control Dimensions for projects module:
- Adds physical_progress_pct (Float, default 0.0) to project_tasks.
- Adds estimated_hours (Float, default 0.0) to project_tasks.
- Adds task_id foreign key to project_expenses (ON DELETE SET NULL).
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20261009_0002_project_task_dimensions_rollup"
down_revision: Union[str, Sequence[str], None] = "20261009_0001_project_components_edt_level2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _uuid_type() -> sa.types.TypeEngine:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        return sa.dialects.postgresql.UUID(as_uuid=True)
    return sa.String(length=36)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    # 1. Agregar physical_progress_pct y estimated_hours a project_tasks
    if "project_tasks" in existing_tables:
        task_cols = {col["name"] for col in inspector.get_columns("project_tasks")}
        with op.batch_alter_table("project_tasks") as batch_op:
            if "physical_progress_pct" not in task_cols:
                batch_op.add_column(
                    sa.Column("physical_progress_pct", sa.Float(), nullable=False, server_default="0.0")
                )
            if "estimated_hours" not in task_cols:
                batch_op.add_column(
                    sa.Column("estimated_hours", sa.Float(), nullable=False, server_default="0.0")
                )

    # 2. Agregar task_id a project_expenses
    if "project_expenses" in existing_tables:
        expense_cols = {col["name"] for col in inspector.get_columns("project_expenses")}
        if "task_id" not in expense_cols:
            with op.batch_alter_table("project_expenses") as batch_op:
                batch_op.add_column(sa.Column("task_id", _uuid_type(), nullable=True))
                batch_op.create_foreign_key(
                    "fk_project_expenses_task_id",
                    "project_tasks",
                    ["task_id"],
                    ["id"],
                    ondelete="SET NULL",
                )
                batch_op.create_index("ix_project_expenses_task_id", ["task_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    # 1. Quitar task_id de project_expenses
    if "project_expenses" in existing_tables:
        expense_cols = {col["name"] for col in inspector.get_columns("project_expenses")}
        if "task_id" in expense_cols:
            with op.batch_alter_table("project_expenses") as batch_op:
                try:
                    batch_op.drop_index("ix_project_expenses_task_id")
                except Exception:
                    pass
                try:
                    batch_op.drop_constraint("fk_project_expenses_task_id", type_="foreignkey")
                except Exception:
                    pass
                batch_op.drop_column("task_id")

    # 2. Quitar physical_progress_pct y estimated_hours de project_tasks
    if "project_tasks" in existing_tables:
        task_cols = {col["name"] for col in inspector.get_columns("project_tasks")}
        with op.batch_alter_table("project_tasks") as batch_op:
            if "estimated_hours" in task_cols:
                batch_op.drop_column("estimated_hours")
            if "physical_progress_pct" in task_cols:
                batch_op.drop_column("physical_progress_pct")
