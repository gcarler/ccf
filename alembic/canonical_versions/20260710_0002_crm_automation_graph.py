"""crm_automation_graph

Revision ID: 20260710_0002
Revises: 20260710_0001
Create Date: 2026-07-10

Migrates CRM automation logic to a branching DAG structure via a new crm_automation_edges table.
"""

from typing import Sequence, Union
import uuid

import sqlalchemy as sa
from alembic import op

revision: str = "20260710_0002"
down_revision: Union[str, None] = "20260710_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _uuid_type() -> sa.types.TypeEngine:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        return sa.dialects.postgresql.UUID(as_uuid=True)
    return sa.String(length=36)


def upgrade() -> None:
    uuid_t = _uuid_type()

    # 1. Add sort_order to crm_casos
    op.add_column(
        "crm_casos",
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
    )

    # 2. Add ui_graph_state to crm_automations
    op.add_column(
        "crm_automations",
        sa.Column("ui_graph_state", sa.JSON(), nullable=True),
    )

    # 3. Create table crm_automation_edges
    op.create_table(
        "crm_automation_edges",
        sa.Column("id", uuid_t, primary_key=True),
        sa.Column(
            "source_id",
            uuid_t,
            sa.ForeignKey("crm_automations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "target_id",
            uuid_t,
            sa.ForeignKey("crm_automations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("condition_type", sa.String(length=50), nullable=True),
        sa.Column("condition_key", sa.String(length=100), nullable=True),
        sa.Column("condition_value", sa.String(length=200), nullable=True),
    )

    op.create_index(
        "ix_crm_automation_edges_source_id",
        "crm_automation_edges",
        ["source_id"],
        unique=False,
    )
    op.create_index(
        "ix_crm_automation_edges_target_id",
        "crm_automation_edges",
        ["target_id"],
        unique=False,
    )

    # 4. DB-Neutral Data Migration: copy next_automation_id relationships to edges
    connection = op.get_bind()
    res = connection.execute(
        sa.text(
            "SELECT id, next_automation_id FROM crm_automations WHERE next_automation_id IS NOT NULL"
        )
    )
    for row in res.all():
        source_id = row[0]
        target_id = row[1]
        new_id = str(uuid.uuid4())
        connection.execute(
            sa.text(
                "INSERT INTO crm_automation_edges (id, source_id, target_id) "
                "VALUES (:id, :source_id, :target_id)"
            ),
            {"id": new_id, "source_id": source_id, "target_id": target_id},
        )

    # 5. Drop next_automation_id from crm_automations
    with op.batch_alter_table("crm_automations") as batch_op:
        batch_op.drop_column("next_automation_id")


def downgrade() -> None:
    uuid_t = _uuid_type()
    connection = op.get_bind()

    # 1. Restore next_automation_id column and foreign key to crm_automations
    with op.batch_alter_table("crm_automations") as batch_op:
        batch_op.add_column(
            sa.Column(
                "next_automation_id",
                uuid_t,
                sa.ForeignKey("crm_automations.id"),
                nullable=True,
            )
        )

    # 2. DB-Neutral Data Migration: restore next_automation_id values from edges
    res = connection.execute(
        sa.text(
            "SELECT source_id, MIN(CAST(target_id AS VARCHAR)) FROM crm_automation_edges GROUP BY source_id"
        )
    )
    for row in res.all():
        source_id = row[0]
        target_id = row[1]
        connection.execute(
            sa.text(
                "UPDATE crm_automations SET next_automation_id = :target_id "
                "WHERE id = :source_id"
            ),
            {"target_id": target_id, "source_id": source_id},
        )

    # 3. Drop crm_automation_edges table and indices
    op.drop_index(
        "ix_crm_automation_edges_target_id", table_name="crm_automation_edges"
    )
    op.drop_index(
        "ix_crm_automation_edges_source_id", table_name="crm_automation_edges"
    )
    op.drop_table("crm_automation_edges")

    # 4. Drop ui_graph_state and sort_order columns
    with op.batch_alter_table("crm_automations") as batch_op:
        batch_op.drop_column("ui_graph_state")

    with op.batch_alter_table("crm_casos") as batch_op:
        batch_op.drop_column("sort_order")
