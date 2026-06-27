"""Consolidate general and case CRM tasks in crm_tareas.

Revision ID: 20260627_0011_crm_tasks
Revises: 20260627_0010_strategy_uuid
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260627_0011_crm_tasks"
down_revision: str | None = "20260627_0010_strategy_uuid"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    connection = op.get_bind()
    parallel_rows = connection.execute(sa.text("SELECT COUNT(*) FROM crm_tasks")).scalar_one()
    if parallel_rows:
        raise RuntimeError(
            f"Cannot remove parallel crm_tasks table: it contains {parallel_rows} row(s)"
        )

    op.drop_table("crm_tasks")
    op.alter_column("crm_tareas", "caso_id", existing_type=postgresql.UUID(), nullable=True)
    op.alter_column(
        "crm_tareas", "asignado_a_id", existing_type=postgresql.UUID(), nullable=True
    )
    op.alter_column(
        "crm_tareas",
        "fecha_vencimiento",
        existing_type=sa.DateTime(timezone=True),
        nullable=True,
    )
    op.add_column(
        "crm_tareas", sa.Column("persona_id", postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.add_column(
        "crm_tareas", sa.Column("categoria", sa.String(length=100), nullable=True)
    )
    op.add_column(
        "crm_tareas",
        sa.Column(
            "estado",
            sa.String(length=20),
            nullable=False,
            server_default="pending",
        ),
    )
    op.add_column(
        "crm_tareas",
        sa.Column(
            "prioridad",
            sa.String(length=20),
            nullable=False,
            server_default="medium",
        ),
    )
    connection.execute(
        sa.text(
            "UPDATE crm_tareas SET estado = CASE "
            "WHEN completada IS TRUE THEN 'completed' ELSE 'pending' END"
        )
    )
    op.drop_index("ix_crm_tareas_completada", table_name="crm_tareas")
    op.drop_column("crm_tareas", "completada")
    op.create_foreign_key(
        "fk_crm_tareas_persona_id",
        "crm_tareas",
        "personas",
        ["persona_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_crm_tareas_persona_id", "crm_tareas", ["persona_id"])
    op.create_index("ix_crm_tareas_categoria", "crm_tareas", ["categoria"])
    op.create_index("ix_crm_tareas_estado", "crm_tareas", ["estado"])
    op.create_index("ix_crm_tareas_created_at", "crm_tareas", ["created_at"])
    op.alter_column("crm_tareas", "estado", server_default=None)
    op.alter_column("crm_tareas", "prioridad", server_default=None)


def downgrade() -> None:
    connection = op.get_bind()
    general_tasks = connection.execute(
        sa.text("SELECT COUNT(*) FROM crm_tareas WHERE caso_id IS NULL")
    ).scalar_one()
    if general_tasks:
        raise RuntimeError(
            f"Cannot split crm_tareas: {general_tasks} general task(s) would be lost"
        )

    op.add_column(
        "crm_tareas", sa.Column("completada", sa.Boolean(), nullable=True)
    )
    connection.execute(
        sa.text("UPDATE crm_tareas SET completada = (estado = 'completed')")
    )
    op.create_index("ix_crm_tareas_completada", "crm_tareas", ["completada"])
    op.drop_index("ix_crm_tareas_created_at", table_name="crm_tareas")
    op.drop_index("ix_crm_tareas_estado", table_name="crm_tareas")
    op.drop_index("ix_crm_tareas_categoria", table_name="crm_tareas")
    op.drop_index("ix_crm_tareas_persona_id", table_name="crm_tareas")
    op.drop_constraint("fk_crm_tareas_persona_id", "crm_tareas", type_="foreignkey")
    op.drop_column("crm_tareas", "prioridad")
    op.drop_column("crm_tareas", "estado")
    op.drop_column("crm_tareas", "categoria")
    op.drop_column("crm_tareas", "persona_id")
    op.alter_column(
        "crm_tareas",
        "fecha_vencimiento",
        existing_type=sa.DateTime(timezone=True),
        nullable=False,
    )
    op.alter_column(
        "crm_tareas", "asignado_a_id", existing_type=postgresql.UUID(), nullable=False
    )
    op.alter_column("crm_tareas", "caso_id", existing_type=postgresql.UUID(), nullable=False)

    op.create_table(
        "crm_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("persona_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("assignee_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=True),
        sa.Column("priority", sa.String(length=20), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["persona_id"], ["personas.id"]),
        sa.ForeignKeyConstraint(["assignee_id"], ["personas.id"]),
    )
    op.create_index("ix_crm_tasks_assignee_id", "crm_tasks", ["assignee_id"])
    op.create_index("ix_crm_tasks_category", "crm_tasks", ["category"])
    op.create_index("ix_crm_tasks_created_at", "crm_tasks", ["created_at"])
    op.create_index("ix_crm_tasks_persona_id", "crm_tasks", ["persona_id"])
    op.create_index("ix_crm_tasks_status", "crm_tasks", ["status"])
