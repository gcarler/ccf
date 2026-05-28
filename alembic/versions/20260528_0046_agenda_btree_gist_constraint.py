"""0046_agenda_btree_gist_constraint

Revision ID: 20260528_0046
Revises: 20260528_0045
Create Date: 2026-05-28

Activa el constraint EXCLUDE USING gist en agenda_reserva_recursos para
prevenir doble-booking de recursos físicos (Capa D — CRÍTICO del audit forense).

INSTRUCCIONES DBA:
  1. Verificar primero que no haya colisiones existentes:
     SELECT r1.id, r2.id FROM agenda_reserva_recursos r1
     JOIN agenda_reserva_recursos r2
       ON r1.recurso_id = r2.recurso_id AND r1.id < r2.id
       AND tstzrange(r1.bloqueo_inicio, r1.bloqueo_fin)
           && tstzrange(r2.bloqueo_inicio, r2.bloqueo_fin);
  2. Si retorna 0 filas → ejecutar esta migración.
  3. Si retorna filas → resolver conflictos primero, luego migrar.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260528_0046"
down_revision: Union[str, None] = "20260528_0045"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _extension_exists(name: str) -> bool:
    conn = op.get_bind()
    r = conn.execute(sa.text(
        "SELECT count(*) FROM pg_extension WHERE extname = :n"
    ), {"n": name})
    return r.scalar() > 0


def _constraint_exists(name: str) -> bool:
    conn = op.get_bind()
    r = conn.execute(sa.text(
        "SELECT count(*) FROM pg_constraint WHERE conname = :n"
    ), {"n": name})
    return r.scalar() > 0


def _has_collisions() -> bool:
    conn = op.get_bind()
    r = conn.execute(sa.text("""
        SELECT count(*) FROM agenda_reserva_recursos r1
        JOIN agenda_reserva_recursos r2
          ON r1.recurso_id = r2.recurso_id
         AND r1.id < r2.id
         AND tstzrange(r1.bloqueo_inicio, r1.bloqueo_fin)
             && tstzrange(r2.bloqueo_inicio, r2.bloqueo_fin)
    """))
    return r.scalar() > 0


def upgrade() -> None:
    conn = op.get_bind()

    # Requiere superuser — falla con error claro si no disponible
    if not _extension_exists("btree_gist"):
        conn.execute(sa.text("CREATE EXTENSION IF NOT EXISTS btree_gist"))

    if _has_collisions():
        raise RuntimeError(
            "ABORT: Se detectaron reservas con colisión de horarios en "
            "agenda_reserva_recursos. Resolver conflictos antes de aplicar "
            "el constraint. Ver query de verificación en el docstring."
        )

    if not _constraint_exists("sin_colisiones_fisicas"):
        conn.execute(sa.text("""
            ALTER TABLE agenda_reserva_recursos
              ADD CONSTRAINT sin_colisiones_fisicas
              EXCLUDE USING gist (
                recurso_id WITH =,
                tstzrange(bloqueo_inicio, bloqueo_fin) WITH &&
              )
        """))


def downgrade() -> None:
    conn = op.get_bind()
    if _constraint_exists("sin_colisiones_fisicas"):
        conn.execute(sa.text(
            "ALTER TABLE agenda_reserva_recursos "
            "DROP CONSTRAINT IF EXISTS sin_colisiones_fisicas"
        ))
    # No drop btree_gist — other constraints may use it
