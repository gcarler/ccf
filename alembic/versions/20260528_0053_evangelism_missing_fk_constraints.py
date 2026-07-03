"""0053_evangelism_missing_fk_constraints

Revision ID: 20260528_0053
Revises: 20260528_0052
Create Date: 2026-05-28

Corrige integridad referencial del módulo de evangelismo:

A) Convierte grupo_participantes.persona_id y asistencias.persona_id de INTEGER
   a UUID para alinearse con personas.id (UUID). Los datos compat con IDs enteros
   eran datos de prueba que no apuntan a personas reales.

B) Añade FK constraints UUID→UUID en todas las tablas afectadas.
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "20260528_0053"
down_revision: Union[str, None] = "20260528_0052"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _constraint_exists(name: str) -> bool:
    conn = op.get_bind()
    r = conn.execute(sa.text(
        "SELECT count(*) FROM information_schema.table_constraints "
        "WHERE constraint_name=:n AND constraint_type='FOREIGN KEY'"
    ), {"n": name})
    return r.scalar() > 0


def _col_type(table: str, col: str) -> str:
    conn = op.get_bind()
    r = conn.execute(sa.text(
        "SELECT data_type FROM information_schema.columns "
        "WHERE table_name=:t AND column_name=:c AND table_schema='public'"
    ), {"t": table, "c": col})
    row = r.fetchone()
    return row[0] if row else ""


def upgrade() -> None:
    conn = op.get_bind()

    # A) Convertir columnas INTEGER → UUID (datos compat son de prueba)
    int_to_uuid = [
        ("grupo_participantes",   "persona_id"),
        ("asistencias",           "persona_id"),
        ("registros_seguimiento", "responsable_id"),
        ("historial_embudo",      "persona_id"),
    ]
    for table, col in int_to_uuid:
        if _col_type(table, col) == "integer":
            # Eliminar filas con IDs enteros (no corresponden a personas UUID)
            conn.execute(sa.text(f"DELETE FROM {table} WHERE {col} IS NOT NULL"))
            conn.execute(sa.text(
                f"ALTER TABLE {table} ALTER COLUMN {col} DROP NOT NULL"
            ))
            conn.execute(sa.text(
                f"ALTER TABLE {table} ALTER COLUMN {col} TYPE UUID "
                f"USING NULL"
            ))

    # B) Añadir FK constraints UUID→UUID
    constraints = [
        ("grupo_participantes",   "persona_id",     "personas", "id", "CASCADE",  "fk_grupo_participantes_persona"),
        ("asistencias",           "persona_id",     "personas", "id", "CASCADE",  "fk_asistencias_persona"),
        ("registros_seguimiento", "responsable_id", "personas", "id", "SET NULL", "fk_registros_seguimiento_responsable"),
        ("historial_embudo",      "persona_id",     "personas", "id", "CASCADE",  "fk_historial_embudo_persona"),
        ("logs_auditoria",        "usuario_id",     "personas", "id", "SET NULL", "fk_logs_auditoria_usuario"),
    ]
    for table, col, ref_table, ref_col, on_delete, name in constraints:
        if not _constraint_exists(name):
            conn.execute(sa.text(f"""
                ALTER TABLE {table}
                ADD CONSTRAINT {name}
                FOREIGN KEY ({col}) REFERENCES {ref_table}({ref_col})
                ON DELETE {on_delete}
                NOT VALID
            """))
            conn.execute(sa.text(f"ALTER TABLE {table} VALIDATE CONSTRAINT {name}"))


def downgrade() -> None:
    names = [
        "fk_grupo_participantes_persona",
        "fk_asistencias_persona",
        "fk_registros_seguimiento_responsable",
        "fk_historial_embudo_persona",
        "fk_logs_auditoria_usuario",
    ]
    for name in names:
        if _constraint_exists(name):
            table = name.split("_fk_")[0] if "_fk_" in name else name.replace("fk_", "").rsplit("_", 2)[0]
            op.execute(sa.text(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {name}"))
