"""add sede_id to volunteer_shifts, support_tickets, crm_tareas (Axioma 3)

Auditoría de calidad backend (ses_01d60c45): 3 modelos UGC expuestos por
API admin carecían de columna ``sede_id`` propia, delegando el aislamiento
multi-tenant a JOINs indirectos (vía persona/caso). Esto rompía el axioma
de filtro directo por sede y abría brechas donde un admin podía listar
filas cross-sede.

  - ``volunteer_shifts``  → ``sede_id`` (backfill: ``persona.sede_id``)
  - ``support_tickets``   → ``sede_id`` (backfill: ``user_id`` → ``personas.sede_id``)
  - ``crm_tareas``        → ``sede_id`` (backfill: ``persona_id`` → ``personas.sede_id``
                            con fallback ``caso_id`` → ``crm_casos.sede_id``)

Columnas ``nullable=True`` (no-fatal con datos históricos). Defense-in-depth
en CRUD/API: actor con sede ⇒ ``sede_id`` del row debe coincidir.

Postgres-first con fallback SQLite (tests usan sqlite://). Idempotente
mediante checks ``sa.inspect``.

Revision ID: 20260809_0001_sede_vol_sup_task
Revises: 20260808_0003_merge_contextual_followup_heads
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260809_0001_sede_vol_sup_task"
down_revision: Union[str, None] = "20260808_0003_merge_contextual_followup_heads"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ── Helpers (Postgres-aware, SQLite-safe) ─────────────────────────────────


def _inspector():
    return sa.inspect(op.get_bind())


def _has_table(table: str) -> bool:
    return table in set(_inspector().get_table_names())


def _has_column(table: str, column: str) -> bool:
    if not _has_table(table):
        return False
    return any(col.get("name") == column for col in _inspector().get_columns(table))


def _has_index(table: str, index_name: str) -> bool:
    if not _has_table(table):
        return False
    return any(idx.get("name") == index_name for idx in _inspector().get_indexes(table))


def _uuid_type():
    """UUID portable: postgresql.UUID en Postgres, String(36) en SQLite/otros."""
    if op.get_bind().dialect.name == "postgresql":
        return postgresql.UUID(as_uuid=True)
    return sa.String(36)


def _add_sede_column(table: str) -> None:
    """Añade ``sede_id`` (UUID, nullable, FK a sedes.id) + índice B-Tree.

    Idempotente. Compatible con Postgres y SQLite.
    """
    if not _has_table(table):
        return
    if not _has_column(table, "sede_id"):
        with op.batch_alter_table(table) as batch_op:
            batch_op.add_column(
                sa.Column(
                    "sede_id",
                    _uuid_type(),
                    sa.ForeignKey("sedes.id", ondelete="SET NULL"),
                    nullable=True,
                )
            )

    idx_name = f"ix_{table}_sede_id"
    if not _has_index(table, idx_name):
        op.create_index(idx_name, table, ["sede_id"], unique=False)


def _backfill_sede_from_persona_fk(table: str, fk_col: str) -> None:
    """``UPDATE table SET sede_id = p.sede_id`` desde ``personas`` cuando sea NULL.

    Portable Postgres + SQLite.
    """
    if not (_has_table(table) and _has_table("personas")):
        return
    if not (_has_column(table, "sede_id") and _has_column(table, fk_col)):
        return
    if not _has_column("personas", "sede_id"):
        return

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        bind.execute(
            sa.text(
                f"UPDATE {table} AS t "
                f"SET sede_id = p.sede_id "
                f"FROM personas AS p "
                f"WHERE t.{fk_col}::text = p.id::text "
                f"AND p.sede_id IS NOT NULL "
                f"AND t.sede_id IS NULL"
            )
        )
    else:
        bind.execute(
            sa.text(
                f"UPDATE {table} "
                f"SET sede_id = ("
                f"  SELECT p.sede_id FROM personas p "
                f"  WHERE CAST(p.id AS TEXT) = "
                f"CAST({table}.{fk_col} AS TEXT)"
                f") "
                f"WHERE sede_id IS NULL "
                f"AND {fk_col} IS NOT NULL "
                f"AND EXISTS ("
                f"  SELECT 1 FROM personas p "
                f"  WHERE CAST(p.id AS TEXT) = "
                f"CAST({table}.{fk_col} AS TEXT) "
                f"  AND p.sede_id IS NOT NULL"
                f")"
            )
        )


def _backfill_sede_from_caso_fk(table: str, fk_col: str) -> None:
    """Fallback ``UPDATE table SET sede_id = c.sede_id`` desde ``crm_casos``.

    Sólo aplica a filas que aún tienen ``sede_id IS NULL`` después del
    backfill principal (personas). Portable Postgres + SQLite.
    """
    if not (_has_table(table) and _has_table("crm_casos")):
        return
    if not (_has_column(table, "sede_id") and _has_column(table, fk_col)):
        return
    if not _has_column("crm_casos", "sede_id"):
        return

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        bind.execute(
            sa.text(
                f"UPDATE {table} AS t "
                f"SET sede_id = c.sede_id "
                f"FROM crm_casos AS c "
                f"WHERE t.{fk_col}::text = c.id::text "
                f"AND c.sede_id IS NOT NULL "
                f"AND t.sede_id IS NULL"
            )
        )
    else:
        bind.execute(
            sa.text(
                f"UPDATE {table} "
                f"SET sede_id = ("
                f"  SELECT c.sede_id FROM crm_casos c "
                f"  WHERE CAST(c.id AS TEXT) = "
                f"CAST({table}.{fk_col} AS TEXT)"
                f") "
                f"WHERE sede_id IS NULL "
                f"AND {fk_col} IS NOT NULL "
                f"AND EXISTS ("
                f"  SELECT 1 FROM crm_casos c "
                f"  WHERE CAST(c.id AS TEXT) = "
                f"CAST({table}.{fk_col} AS TEXT) "
                f"  AND c.sede_id IS NOT NULL"
                f")"
            )
        )


# ── Migration body ───────────────────────────────────────────────────────


def upgrade() -> None:
    # 1. volunteer_shifts.sede_id (backfill desde persona_id → personas.sede_id)
    _add_sede_column("volunteer_shifts")
    _backfill_sede_from_persona_fk("volunteer_shifts", "persona_id")

    # 2. support_tickets.sede_id (backfill desde user_id → personas.sede_id)
    _add_sede_column("support_tickets")
    _backfill_sede_from_persona_fk("support_tickets", "user_id")

    # 3. crm_tareas.sede_id (backfill principal desde persona_id; fallback
    #    desde caso_id → crm_casos.sede_id para tareas huérfanas de persona
    #    pero ancladas a un caso con sede).
    _add_sede_column("crm_tareas")
    _backfill_sede_from_persona_fk("crm_tareas", "persona_id")
    _backfill_sede_from_caso_fk("crm_tareas", "caso_id")


def downgrade() -> None:
    for table in ("crm_tareas", "support_tickets", "volunteer_shifts"):
        if not _has_table(table):
            continue
        idx_name = f"ix_{table}_sede_id"
        if _has_index(table, idx_name):
            op.drop_index(idx_name, table_name=table)
        if _has_column(table, "sede_id"):
            with op.batch_alter_table(table) as batch_op:
                batch_op.drop_column("sede_id")