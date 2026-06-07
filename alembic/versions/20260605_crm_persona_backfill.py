"""Backfill CRM persona UUID owner columns

Revision ID: 20260605_crm_persona_backfill
Revises: 20260605_acad_pers_backfill
Create Date: 2026-06-05

Moves CRM assignment/leadership fields toward personas.id while keeping
legacy users.id columns as compatibility data.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260605_crm_persona_backfill"
down_revision: Union[str, None] = "20260605_acad_pers_backfill"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _cols(table: str) -> set[str]:
    return {col["name"] for col in sa.inspect(op.get_bind()).get_columns(table)}


def _has_table(table: str) -> bool:
    return table in _tables()


def _has_col(table: str, column: str) -> bool:
    return _has_table(table) and column in _cols(table)


def _uuid_type():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        return postgresql.UUID(as_uuid=True)
    return sa.String(36)


def _add_uuid_column(table: str, column: str) -> None:
    if not _has_table(table) or _has_col(table, column):
        return
    with op.batch_alter_table(table, schema=None) as batch_op:
        batch_op.add_column(sa.Column(column, _uuid_type(), nullable=True))
    op.create_index(f"ix_{table}_{column}", table, [column], unique=False)


def _constraint_exists(name: str) -> bool:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return False
    return bool(
        bind.execute(
            sa.text(
                "SELECT 1 FROM information_schema.table_constraints "
                "WHERE constraint_schema='public' AND constraint_name=:name"
            ),
            {"name": name},
        ).first()
    )


def _pg_add_fk_if_missing(table: str, column: str, constraint_name: str) -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql" or _constraint_exists(constraint_name):
        return
    bind.execute(
        sa.text(
            f"ALTER TABLE {table} ADD CONSTRAINT {constraint_name} "
            f"FOREIGN KEY ({column}) REFERENCES personas(id) ON DELETE SET NULL "
            f"NOT VALID"
        )
    )


def _backfill(table: str, target_col: str, source_col: str) -> None:
    if not (_has_table(table) and _has_table("personas")):
        return
    if not (_has_col(table, target_col) and _has_col(table, source_col)):
        return
    op.get_bind().execute(
        sa.text(
            f"UPDATE {table} "
            f"SET {target_col} = ("
            f"SELECT personas.id FROM personas "
            f"WHERE personas.user_id = {table}.{source_col}"
            f") "
            f"WHERE {target_col} IS NULL "
            f"AND {source_col} IS NOT NULL "
            f"AND EXISTS ("
            f"SELECT 1 FROM personas WHERE personas.user_id = {table}.{source_col}"
            f")"
        )
    )


def upgrade() -> None:
    _add_uuid_column("counseling_tickets", "pastor_id")
    _add_uuid_column("consolidation_tasks", "assignee_id")
    _add_uuid_column("communication_logs", "leader_id")

    _backfill("counseling_tickets", "pastor_id", "pastor_user_id")
    _backfill("consolidation_tasks", "assignee_id", "assignee_user_id")
    _backfill("communication_logs", "leader_id", "leader_user_id")

    _pg_add_fk_if_missing("counseling_tickets", "pastor_id", "fk_counseling_tickets_pastor_id")
    _pg_add_fk_if_missing("consolidation_tasks", "assignee_id", "fk_consolidation_tasks_assignee_id")
    _pg_add_fk_if_missing("communication_logs", "leader_id", "fk_communication_logs_leader_id")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        for table, constraint in (
            ("communication_logs", "fk_communication_logs_leader_id"),
            ("consolidation_tasks", "fk_consolidation_tasks_assignee_id"),
            ("counseling_tickets", "fk_counseling_tickets_pastor_id"),
        ):
            bind.execute(
                sa.text(
                    f"ALTER TABLE IF EXISTS {table} "
                    f"DROP CONSTRAINT IF EXISTS {constraint}"
                )
            )

    for table, column in (
        ("communication_logs", "leader_id"),
        ("consolidation_tasks", "assignee_id"),
        ("counseling_tickets", "pastor_id"),
    ):
        if _has_col(table, column):
            bind.execute(sa.text(f"UPDATE {table} SET {column} = NULL"))
