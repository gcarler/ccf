"""add_gist_constraint_agenda

Revision ID: 20260602_add_gist_constraint_agenda
Revises: 20260602_rename_compat_tables
Create Date: 2026-06-02

Activa constraint EXCLUDE USING gist en agenda_reserva_recursos para
prevenir doble-booking de recursos físicos (Capa D — CRÍTICO).

Requiere la extensión btree_gist (ya activa en 0046).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260602_add_gist"
down_revision: Union[str, None] = "20260602_rename_compat"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _constraint_exists(name: str) -> bool:
    conn = op.get_bind()
    r = conn.execute(
        sa.text("SELECT count(*) FROM pg_constraint WHERE conname = :n"),
        {"n": name},
    )
    return r.scalar() > 0


def upgrade() -> None:
    conn = op.get_bind()
    dialect = conn.dialect.name
    if dialect != "postgresql":
        return  # GIST constraints solo en PostgreSQL
    conn.execute(sa.text("CREATE EXTENSION IF NOT EXISTS btree_gist"))
    if not _constraint_exists("sin_colisiones_fisicas"):
        conn.execute(
            sa.text(
                """
                ALTER TABLE agenda_reserva_recursos
                ADD CONSTRAINT sin_colisiones_fisicas
                EXCLUDE USING gist (
                    recurso_id WITH =,
                    tstzrange(bloqueo_inicio, bloqueo_fin) WITH &&
                )
                """
            )
        )


def downgrade() -> None:
    conn = op.get_bind()
    if _constraint_exists("sin_colisiones_fisicas"):
        conn.execute(
            sa.text(
                "ALTER TABLE agenda_reserva_recursos "
                "DROP CONSTRAINT IF EXISTS sin_colisiones_fisicas"
            )
        )
