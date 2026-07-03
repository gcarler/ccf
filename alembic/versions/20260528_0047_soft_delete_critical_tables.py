"""0047_soft_delete_critical_tables

Revision ID: 20260528_0047
Revises: 20260528_0046
Create Date: 2026-05-28

Añade deleted_at a tablas con historial irreemplazable (Capa E — Audit Forense).
Ningún dato existente es eliminado. Partial index WHERE deleted_at IS NULL
mantiene performance en queries normales.

Tablas:
  - counseling_tickets
  - donations
  - spiritual_milestones
  - crm_casos
  - academy_enrollments
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "20260528_0047"
down_revision: Union[str, None] = "20260528_0046"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _col_exists(table: str, col: str) -> bool:
    conn = op.get_bind()
    r = conn.execute(sa.text(
        "SELECT count(*) FROM information_schema.columns "
        "WHERE table_name=:t AND column_name=:c"
    ), {"t": table, "c": col})
    return r.scalar() > 0


def _index_exists(name: str) -> bool:
    conn = op.get_bind()
    r = conn.execute(sa.text(
        "SELECT count(*) FROM pg_indexes WHERE indexname=:n"
    ), {"n": name})
    return r.scalar() > 0


TABLES = [
    "counseling_tickets",
    "donations",
    "spiritual_milestones",
    "crm_casos",
    "academy_enrollments",
]


def upgrade() -> None:
    conn = op.get_bind()

    for table in TABLES:
        if not _col_exists(table, "deleted_at"):
            op.add_column(table, sa.Column("deleted_at", sa.DateTime(), nullable=True))

        idx_name = f"ix_{table}_active"
        if not _index_exists(idx_name):
            conn.execute(sa.text(
                f"CREATE INDEX {idx_name} ON {table} (id) WHERE deleted_at IS NULL"
            ))


def downgrade() -> None:
    conn = op.get_bind()
    for table in TABLES:
        idx_name = f"ix_{table}_active"
        conn.execute(sa.text(f"DROP INDEX IF EXISTS {idx_name}"))
        if _col_exists(table, "deleted_at"):
            op.drop_column(table, "deleted_at")
