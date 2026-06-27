"""Remove the parallel CRM consolidation model tree.

Revision ID: 20260627_0006_crm_contract
Revises: 20260627_0005_agent_soft_delete
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260627_0006_crm_contract"
down_revision: str | None = "20260627_0005_agent_soft_delete"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


PARALLEL_TABLES = (
    "pastoral_call_logs",
    "consolidation_tasks",
    "consolidation_interactions",
    "consolidation_assignments",
    "consolidation_cases",
)


def _assert_empty(connection, table_name: str) -> None:
    count = connection.execute(sa.text(f'SELECT COUNT(*) FROM "{table_name}"')).scalar_one()
    if count:
        raise RuntimeError(
            f"Cannot remove parallel CRM table {table_name}: it contains {count} rows"
        )


def upgrade() -> None:
    connection = op.get_bind()
    for table_name in PARALLEL_TABLES:
        _assert_empty(connection, table_name)

    op.add_column(
        "crm_pipelines",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "crm_etapas_pipeline",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    for table_name in PARALLEL_TABLES:
        op.drop_table(table_name)


def downgrade() -> None:
    uuid_type = sa.Uuid()
    timestamp = sa.DateTime(timezone=True)

    op.create_table(
        "consolidation_cases",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("persona_id", uuid_type, sa.ForeignKey("personas.id", ondelete="CASCADE"), nullable=False),
        sa.Column("stage", sa.String(20), nullable=True),
        sa.Column("status", sa.String(20), nullable=True),
        sa.Column("source", sa.String(100), nullable=True),
        sa.Column("source_campaign", sa.String(200), nullable=True),
        sa.Column("last_contact_at", timestamp, nullable=True),
        sa.Column("next_contact_at", timestamp, nullable=True),
        sa.Column("assigned_pastor_id", uuid_type, sa.ForeignKey("personas.id", ondelete="SET NULL"), nullable=True),
        sa.Column("assigned_leader_id", uuid_type, sa.ForeignKey("personas.id", ondelete="SET NULL"), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("sede_id", uuid_type, sa.ForeignKey("sedes.id", ondelete="SET NULL"), nullable=True),
        sa.Column("deleted_at", timestamp, nullable=True),
        sa.Column("created_at", timestamp, nullable=True),
        sa.Column("updated_at", timestamp, nullable=True),
    )
    op.create_table(
        "consolidation_assignments",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("case_id", uuid_type, sa.ForeignKey("consolidation_cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("assigned_by_id", uuid_type, sa.ForeignKey("personas.id", ondelete="CASCADE"), nullable=False),
        sa.Column("assigned_to_id", uuid_type, sa.ForeignKey("personas.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("priority", sa.String(20), nullable=True),
        sa.Column("start_date", timestamp, nullable=True),
        sa.Column("end_date", timestamp, nullable=True),
        sa.Column("status", sa.String(20), nullable=True),
        sa.Column("created_at", timestamp, nullable=True),
    )
    op.create_table(
        "consolidation_interactions",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("case_id", uuid_type, sa.ForeignKey("consolidation_cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("performed_by_id", uuid_type, sa.ForeignKey("personas.id", ondelete="CASCADE"), nullable=False),
        sa.Column("interaction_type", sa.String(50), nullable=False),
        sa.Column("interaction_date", timestamp, nullable=True),
        sa.Column("result", sa.String(100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("next_action_date", timestamp, nullable=True),
        sa.Column("created_at", timestamp, nullable=True),
    )
    op.create_table(
        "consolidation_tasks",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("case_id", uuid_type, sa.ForeignKey("consolidation_cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("assignment_id", uuid_type, sa.ForeignKey("consolidation_assignments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("due_date", timestamp, nullable=True),
        sa.Column("status", sa.String(20), nullable=True),
        sa.Column("completed_at", timestamp, nullable=True),
        sa.Column("created_at", timestamp, nullable=True),
    )
    op.create_table(
        "pastoral_call_logs",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("case_id", uuid_type, sa.ForeignKey("consolidation_cases.id", ondelete="SET NULL"), nullable=True),
        sa.Column("persona_id", uuid_type, sa.ForeignKey("personas.id", ondelete="SET NULL"), nullable=True),
        sa.Column("pastor_id", uuid_type, sa.ForeignKey("personas.id"), nullable=False),
        sa.Column("outcome", sa.String(120), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("prayer_requests", sa.Text(), nullable=True),
        sa.Column("created_at", timestamp, nullable=True),
        sa.Column("updated_at", timestamp, nullable=True),
    )

    op.drop_column("crm_etapas_pipeline", "deleted_at")
    op.drop_column("crm_pipelines", "deleted_at")
