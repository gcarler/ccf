"""add_soft_delete_to_critical

Revision ID: 20260602_add_soft_delete_to_critical
Revises: 20260602_add_missing_indexes
Create Date: 2026-06-02

Añade soft-delete (deleted_at TIMESTAMP WITH TIME ZONE) a tablas críticas
que requieren auditoría forense sin pérdida de historial (Capa E).

Cada tabla recibe un partial index ix_<tabla>_active WHERE deleted_at IS NULL
para mantener performance en queries del hot-path.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260602_add_soft_delete"
down_revision: Union[str, None] = "20260602_add_missing_idx"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABLES = [
    "chat_messages",
    "conversations",
    "event_assignments",
    "event_attendances",
    "communication_logs",
    "pastoral_call_logs",
    "member_ministries",
    "academy_courses",
    "academy_lessons",
    "academy_assessments",
    "cms_pages",
    "cms_sections",
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
        if not _col_exists(table, "deleted_at"):
            op.add_column(
                table,
                sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            )

        idx_name = f"ix_{table}_active"
        if not _index_exists(idx_name):
            op.execute(
                sa.text(
                    f"CREATE INDEX IF NOT EXISTS {idx_name} "
                    f"ON {table} (id) WHERE deleted_at IS NULL"
                )
            )


def downgrade() -> None:
    conn = op.get_bind()
    for table in TABLES:
        idx_name = f"ix_{table}_active"
        if _index_exists(idx_name):
            conn.execute(sa.text(f"DROP INDEX IF EXISTS {idx_name}"))

        if _col_exists(table, "deleted_at"):
            op.drop_column(table, "deleted_at")
