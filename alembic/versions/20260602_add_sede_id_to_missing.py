"""add_sede_id_to_missing

Revision ID: 20260602_add_sede_id_to_missing
Revises: 20260602_add_soft_delete_to_critical
Create Date: 2026-06-02

Cierra brechas multi-tenant en tablas operativas sin sede_id.
Añade sede_id UUID REFERENCES sedes(id) + índice B-Tree.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "20260602_add_sede_id"
down_revision: Union[str, None] = "20260602_add_soft_delete"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABLES = [
    "chat_messages",
    "conversations",
    "donations",
    "communication_logs",
    "academy_enrollments",
]


def _col_exists(table: str, col: str) -> bool:
    conn = op.get_bind()
    r = conn.execute(
        sa.text(
            "SELECT count(*) FROM information_schema.columns "
            "WHERE table_name = :t AND column_name = :c"
        ),
        {"t": table, "c": col},
    )
    return r.scalar() > 0


def _index_exists(name: str) -> bool:
    conn = op.get_bind()
    r = conn.execute(
        sa.text("SELECT count(*) FROM pg_indexes WHERE indexname = :n"),
        {"n": name},
    )
    return r.scalar() > 0


def upgrade() -> None:
    for table in TABLES:
        if not _col_exists(table, "sede_id"):
            op.add_column(
                table,
                sa.Column(
                    "sede_id",
                    UUID(as_uuid=True),
                    sa.ForeignKey("sedes.id", ondelete="SET NULL"),
                    nullable=True,
                ),
            )

        idx_name = f"ix_{table}_sede_id"
        if not _index_exists(idx_name):
            op.execute(
                sa.text(
                    f"CREATE INDEX IF NOT EXISTS {idx_name} "
                    f"ON {table} (sede_id)"
                )
            )


def downgrade() -> None:
    conn = op.get_bind()
    for table in TABLES:
        idx_name = f"ix_{table}_sede_id"
        if _index_exists(idx_name):
            conn.execute(sa.text(f"DROP INDEX IF EXISTS {idx_name}"))

        if _col_exists(table, "sede_id"):
            op.drop_column(table, "sede_id")
