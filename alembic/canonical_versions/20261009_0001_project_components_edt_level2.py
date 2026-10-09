"""Add project_components table and component_id FK to tasks and expenses.

Revision ID: 20261009_0001_project_components_edt_level2
Revises: 20261006_0001_project_phases_date_range, 20261007_0001_academy_assessment_retry_cooldown
Create Date: 2026-10-09 05:00:00

Implements WBS/EDT Level 2 (Project Components) for projects module:
- Creates project_components table with UUIDv4, project_id, code, name, description,
  budget_allocated, order_index, color, status, timestamps and soft-delete.
- Adds component_id foreign key to project_tasks (ON DELETE SET NULL).
- Adds component_id foreign key to project_expenses (ON DELETE SET NULL).
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20261009_0001_project_components_edt_level2"
down_revision: Union[str, Sequence[str], None] = (
    "20261006_0001_project_phases_date_range",
    "20261007_0001_academy_assessment_retry_cooldown",
)
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

    # 1. Crear tabla project_components si no existe
    if "project_components" not in existing_tables:
        op.create_table(
            "project_components",
            sa.Column("id", _uuid_type(), primary_key=True),
            sa.Column(
                "project_id",
                _uuid_type(),
                sa.ForeignKey("projects.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("code", sa.String(50), nullable=False),
            sa.Column("name", sa.String(200), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("budget_allocated", sa.Float(), nullable=False, server_default="0.0"),
            sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("color", sa.String(20), nullable=True, server_default="#3b82f6"),
            sa.Column("status", sa.String(20), nullable=False, server_default="active"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("project_id", "code", name="uq_project_components_project_code"),
        )
        op.create_index("ix_project_components_project_id", "project_components", ["project_id"])
        op.create_index("ix_project_components_code", "project_components", ["code"])
        op.create_index("ix_project_components_created_at", "project_components", ["created_at"])
        op.create_index("ix_project_components_deleted_at", "project_components", ["deleted_at"])

    # 2. Agregar component_id a project_tasks
    if "project_tasks" in existing_tables:
        task_cols = {col["name"] for col in inspector.get_columns("project_tasks")}
        if "component_id" not in task_cols:
            with op.batch_alter_table("project_tasks") as batch_op:
                batch_op.add_column(sa.Column("component_id", _uuid_type(), nullable=True))
                batch_op.create_foreign_key(
                    "fk_project_tasks_component_id",
                    "project_components",
                    ["component_id"],
                    ["id"],
                    ondelete="SET NULL",
                )
                batch_op.create_index("ix_project_tasks_component_id", ["component_id"])

    # 3. Agregar component_id a project_expenses
    if "project_expenses" in existing_tables:
        expense_cols = {col["name"] for col in inspector.get_columns("project_expenses")}
        if "component_id" not in expense_cols:
            with op.batch_alter_table("project_expenses") as batch_op:
                batch_op.add_column(sa.Column("component_id", _uuid_type(), nullable=True))
                batch_op.create_foreign_key(
                    "fk_project_expenses_component_id",
                    "project_components",
                    ["component_id"],
                    ["id"],
                    ondelete="SET NULL",
                )
                batch_op.create_index("ix_project_expenses_component_id", ["component_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    # 1. Quitar component_id de project_expenses
    if "project_expenses" in existing_tables:
        expense_cols = {col["name"] for col in inspector.get_columns("project_expenses")}
        if "component_id" in expense_cols:
            with op.batch_alter_table("project_expenses") as batch_op:
                batch_op.drop_index("ix_project_expenses_component_id")
                batch_op.drop_constraint("fk_project_expenses_component_id", type_="foreignkey")
                batch_op.drop_column("component_id")

    # 2. Quitar component_id de project_tasks
    if "project_tasks" in existing_tables:
        task_cols = {col["name"] for col in inspector.get_columns("project_tasks")}
        if "component_id" in task_cols:
            with op.batch_alter_table("project_tasks") as batch_op:
                batch_op.drop_index("ix_project_tasks_component_id")
                batch_op.drop_constraint("fk_project_tasks_component_id", type_="foreignkey")
                batch_op.drop_column("component_id")

    # 3. Eliminar tabla project_components
    if "project_components" in existing_tables:
        op.drop_index("ix_project_components_deleted_at", table_name="project_components")
        op.drop_index("ix_project_components_created_at", table_name="project_components")
        op.drop_index("ix_project_components_code", table_name="project_components")
        op.drop_index("ix_project_components_project_id", table_name="project_components")
        op.drop_table("project_components")
