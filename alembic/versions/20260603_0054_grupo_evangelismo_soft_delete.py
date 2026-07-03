"""grupo_evangelismo_soft_delete

Revision ID: 20260603_0054_grupo_soft_delete
Revises: 20260602_add_gist
Create Date: 2026-06-03

Adds soft-delete support to grupos_evangelismo without removing data.
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "20260603_0054_grupo_soft_delete"
down_revision: Union[str, None] = "20260602_add_gist"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _col_exists(table: str, col: str) -> bool:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    return any(column["name"] == col for column in inspector.get_columns(table))


def _index_exists(name: str) -> bool:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    return any(index["name"] == name for index in inspector.get_indexes("grupos_evangelismo"))


def upgrade() -> None:
    conn = op.get_bind()
    dialect = conn.dialect.name
    if not _col_exists("grupos_evangelismo", "deleted_at"):
        op.add_column(
            "grupos_evangelismo",
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        )

    if dialect == "postgresql":
        conn.execute(
            sa.text(
                "CREATE INDEX IF NOT EXISTS ix_grupos_evangelismo_active "
                "ON grupos_evangelismo (id) WHERE deleted_at IS NULL"
            )
        )
    elif not _index_exists("ix_grupos_evangelismo_active"):
        op.create_index(
            "ix_grupos_evangelismo_active",
            "grupos_evangelismo",
            ["id"],
        )


def downgrade() -> None:
    if _index_exists("ix_grupos_evangelismo_active"):
        op.drop_index("ix_grupos_evangelismo_active", table_name="grupos_evangelismo")
    if _col_exists("grupos_evangelismo", "deleted_at"):
        op.drop_column("grupos_evangelismo", "deleted_at")
