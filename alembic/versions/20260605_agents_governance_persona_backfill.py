"""Backfill Agents/Governance persona UUID columns

Revision ID: 20260605_agents_gov_backfill
Revises: 20260605_cms_persona_backfill
Create Date: 2026-06-05
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260605_agents_gov_backfill"
down_revision: Union[str, None] = "20260605_cms_persona_backfill"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(table: str) -> bool:
    return table in set(sa.inspect(op.get_bind()).get_table_names())


def _has_col(table: str, column: str) -> bool:
    if not _has_table(table):
        return False
    return column in {col["name"] for col in sa.inspect(op.get_bind()).get_columns(table)}


def _uuid_type():
    if op.get_bind().dialect.name == "postgresql":
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


BACKFILLS = (
    ("admin_audit_logs", "actor_persona_id", "actor_user_id"),
    ("agents", "created_by_persona_id", "created_by"),
    ("agents", "updated_by_persona_id", "updated_by"),
    ("agent_roles", "created_by_persona_id", "created_by"),
    ("agent_journey", "triggered_by_persona_id", "triggered_by_id"),
    ("agent_conversations", "persona_id", "user_id"),
)


def upgrade() -> None:
    for table, target_col, source_col in BACKFILLS:
        _add_uuid_column(table, target_col)
        _backfill(table, target_col, source_col)
        _pg_add_fk_if_missing(table, target_col, f"fk_{table}_{target_col}")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        for table, target_col, _source_col in reversed(BACKFILLS):
            bind.execute(
                sa.text(
                    f"ALTER TABLE IF EXISTS {table} "
                    f"DROP CONSTRAINT IF EXISTS fk_{table}_{target_col}"
                )
            )

    for table, target_col, _source_col in reversed(BACKFILLS):
        if _has_col(table, target_col):
            bind.execute(sa.text(f"UPDATE {table} SET {target_col} = NULL"))
