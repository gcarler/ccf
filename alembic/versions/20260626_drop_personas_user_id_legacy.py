"""drop_personas_user_id_legacy

Revision ID: 20260626_drop_personas_user_id
Revises: 20260622_0001_mass_uuid_migr
Create Date: 2026-06-26 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260626_drop_personas_user_id"
down_revision: Union[str, None] = "20260622_0001_mass_uuid_migr"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table: str) -> bool:
    conn = op.get_bind()
    return table in sa.inspect(conn).get_table_names()


def _has_col(table: str, column: str) -> bool:
    if not _table_exists(table):
        return False
    conn = op.get_bind()
    return column in {c["name"] for c in sa.inspect(conn).get_columns(table)}


def _index_exists(table: str, index: str) -> bool:
    if not _table_exists(table):
        return False
    conn = op.get_bind()
    return any(i.get("name") == index for i in sa.inspect(conn).get_indexes(table))


def upgrade() -> None:
    if not _has_col("personas", "user_id"):
        return

    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        op.execute("ALTER TABLE personas DROP CONSTRAINT IF EXISTS personas_user_id_fkey")
        op.execute("DROP INDEX IF EXISTS ix_personas_user_id")
        op.execute("ALTER TABLE personas DROP COLUMN IF EXISTS user_id")
        return

    with op.batch_alter_table("personas") as batch_op:
        batch_op.drop_column("user_id")


def downgrade() -> None:
    if not _table_exists("personas") or _has_col("personas", "user_id"):
        return

    with op.batch_alter_table("personas") as batch_op:
        batch_op.add_column(
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True)
        )
        if _table_exists("auth_users"):
            batch_op.create_foreign_key(
                "personas_user_id_fkey",
                "auth_users",
                ["user_id"],
                ["id"],
                ondelete="SET NULL",
            )
        if not _index_exists("personas", "ix_personas_user_id"):
            batch_op.create_index("ix_personas_user_id", ["user_id"], unique=True)
