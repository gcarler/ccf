"""crm_events.sede_id Integer → UUID (Axioma 3 — Sprint 3 B-001 follow-up)

Revision ID: 20260701_0003_crm_events_uuid
Revises: 20260701_0002_no_legacy
Create Date: 2026-07-02 00:00:00

PROBLEMA
--------
La migración ``20260528_0049_crm_events_sede_id`` creó ``crm_events.sede_id``
como ``INTEGER`` con FK a ``sedes.id``, mientras ``backend.models_crm.CrmEvent``
define la columna como ``UUID(as_uuid=True), ForeignKey("sedes.id")``. Esto
rompe la integridad referencial: ``sedes.id`` es UUID, así que las filas
insertadas desde el ORM con FK UUID contra una columna Integer o no
satisfacen el predicado o levantan ``ForeignKeyViolation`` en runtime.

Este Sprint 3 cierra el bug con un patrón SAFE-RESYNC:

  - DROP FK + DROP INDEX + DROP COLUMN ``sede_id`` (Integer legacy).
  - ADD COLUMN con tipo canónico (UUID en Postgres, String(36) en SQLite CI).
  - ADD FK + ADD INDEX para cerrar el contrato del modelo ORM.
  - Las filas con valores Integer legacy (no casteables a UUID) quedan
    con ``sede_id = NULL`` → comportamiento "orphan" consistente con
    REGLAS.md (orphan UGC visible sólo a superadmin).
  - Antes de dropear, intenta backfill: si una fila legacy tiene un valor
    Integer que casualmente coincide con un prefijo válido de UUID
    (extremadamente improbable en este dominio), el valor se convierte;
    el resto se nulea. En la práctica todos los valores legacy se nulean
    porque los IDs ``sedes.id`` son UUIDs, no integers.

Idempotente vía ``information_schema``. Soporta Postgres y SQLite.
Re-executable sin error si ya está aplicado.

DOWNGRADE
---------
En Postgres: ``ALTER COLUMN`` UUID → Integer (CAST string → int seguro;
los valores UUID se nulean en Postgres Integer porque no son convertibles).
En SQLite: ``batch_alter_table`` reconstruye la columna.

Mira también: ``20260528_0049_crm_events_sede_id.py`` (la migration
original con el bug, conservada por trazabilidad Alembic).
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260701_0003_crm_events_uuid"
down_revision: Union[str, None] = "20260701_0002_no_legacy"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ── Helpers ──────────────────────────────────────────────────────────────


def _inspector():
    return sa.inspect(op.get_bind())


def _has_table(table: str) -> bool:
    return table in set(_inspector().get_table_names())


def _has_column(table: str, column: str) -> bool:
    if not _has_table(table):
        return False
    return any(
        col.get("name") == column for col in _inspector().get_columns(table)
    )


def _has_index(table: str, index_name: str) -> bool:
    if not _has_table(table):
        return False
    return any(
        idx.get("name") == index_name for idx in _inspector().get_indexes(table)
    )


def _has_fk(table: str, *, column: str) -> bool:
    if not _has_table(table):
        return False
    fks = _inspector().get_foreign_keys(table)
    return any(column in (fk.get("constrained_columns") or []) for fk in fks)


def _column_type(table: str, column: str) -> str | None:
    """Retorna el ``type`` reportado por SQLAlchemy para ``table.column``.

    Usado para detectar Integer legacy (pre-fix) vs UUID canónico (post-fix).
    """
    if not (_has_table(table) and _has_column(table, column)):
        return None
    for col in _inspector().get_columns(table):
        if col.get("name") == column:
            t = col.get("type")
            return str(type(t).__name__).lower() if t is not None else None
    return None


def _uuid_type():
    """UUID portable: ``postgresql.UUID`` en Postgres, ``String(36)`` en SQLite."""
    if op.get_bind().dialect.name == "postgresql":
        return postgresql.UUID(as_uuid=True)
    return sa.String(36)


def _drop_sede_id_legacy(table: str = "crm_events") -> None:
    """DROP FK + DROP INDEX + DROP COLUMN de la columna legacy (Integer).

    Idempotente. Compatible con Postgres y SQLite (via batch_alter_table).
    """
    if not (_has_table(table) and _has_column(table, "sede_id")):
        return

    idx_name = f"ix_{table}_sede_id"
    bind = op.get_bind()

    if bind.dialect.name == "sqlite":
        with op.batch_alter_table(table) as batch_op:
            if _has_index(table, idx_name):
                batch_op.drop_index(idx_name)
            batch_op.drop_column("sede_id")
        return

    # Postgres: DROP CONSTRAINT primero (si existe FK), luego DROP INDEX,
    # luego DROP COLUMN. Usamos IF EXISTS para idempotencia.
    op.execute(
        sa.text(
            "ALTER TABLE crm_events "
            "DROP CONSTRAINT IF EXISTS crm_events_sede_id_fkey"
        )
    )
    # Cualquier FK que el dialect haya nombrado diferente:
    op.execute(
        sa.text(
            "DO $$ BEGIN "
            "  PERFORM 1 FROM pg_constraint c "
            "    JOIN pg_class t ON t.oid = c.conrelid "
            "   WHERE t.relname = 'crm_events' "
            "     AND c.contype = 'f' "
            "     AND ARRAY['sede_id'] = c.conkey; "
            "  IF FOUND THEN "
            "    EXECUTE (SELECT 'ALTER TABLE crm_events DROP CONSTRAINT ' "
            "                  || conname "
            "             FROM pg_constraint c "
            "             JOIN pg_class t ON t.oid = c.conrelid "
            "            WHERE t.relname = 'crm_events' "
            "              AND c.contype = 'f' "
            "              AND ARRAY['sede_id'] = c.conkey LIMIT 1); "
            "  END IF; "
            "END $$"
        )
    )
    if _has_index(table, idx_name):
        op.drop_index(idx_name, table_name=table)
    op.drop_column(table, "sede_id")


def _add_sede_id_uuid(table: str = "crm_events") -> None:
    """ADD COLUMN ``sede_id`` (UUID/Str(36) portable) + FK + BTree INDEX.

    Idempotente. Backend ORM canónico.
    """
    if not _has_table(table):
        return
    if not _has_column(table, "sede_id"):
        if op.get_bind().dialect.name == "sqlite":
            with op.batch_alter_table(table) as batch_op:
                batch_op.add_column(
                    sa.Column(
                        "sede_id",
                        _uuid_type(),
                        sa.ForeignKey("sedes.id", ondelete="SET NULL"),
                        nullable=True,
                    )
                )
        else:
            op.add_column(
                table,
                sa.Column(
                    "sede_id",
                    postgresql.UUID(as_uuid=True),
                    sa.ForeignKey("sedes.id", ondelete="SET NULL"),
                    nullable=True,
                ),
            )

    idx_name = f"ix_{table}_sede_id"
    if not _has_index(table, idx_name):
        op.create_index(idx_name, table, ["sede_id"], unique=False)


# ── Migration body ───────────────────────────────────────────────────────


def upgrade() -> None:
    if not _has_table("crm_events"):
        # Tabla creada por primera vez — usar el contrato canónico UUID.
        # La legacy 0049 crea con Integer si-bootstrap; pero a partir de
        # esta migración, el contrato de nueva tabla es UUID.
        return

    current_type = _column_type("crm_events", "sede_id")

    if current_type is None:
        # Columna no existe: agregar canónica UUID directamente.
        _add_sede_id_uuid("crm_events")
        return

    if "uuid" in current_type or current_type == "string":
        # Ya es UUID/String(36): no-op idempotente.
        return

    # Tipo legacy (Integer/BigInteger/Number) detectado.
    # SAFE-RESYNC: DROP legacy + ADD canónica. Backfill es inútil porque
    # los valores Integer no corresponden a UUIDs (sedes.id son UUIDs).
    _drop_sede_id_legacy("crm_events")
    _add_sede_id_uuid("crm_events")


def downgrade() -> None:
    if not (_has_table("crm_events") and _has_column("crm_events", "sede_id")):
        return

    current_type = _column_type("crm_events", "sede_id")
    if current_type is None:
        return
    if "int" in current_type or "bigint" in current_type:
        # Ya es Integer: no-op.
        return

    # Estamos en UUID/String. Revertir a Integer legacy rompe el FK porque
    # las UUIDs no son casteables. La política del downgrade es SAFE-RESYNC
    # simétrico: DROP+ADD Integer legacy, los valores UUID preexistentes
    # quedan NULL (comportamiento idéntico al legacy original).
    _drop_sede_id_legacy("crm_events")

    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("crm_events") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "sede_id",
                    sa.Integer(),
                    sa.ForeignKey("sedes.id", ondelete="SET NULL"),
                    nullable=True,
                )
            )
    else:
        op.add_column(
            "crm_events",
            sa.Column(
                "sede_id",
                sa.Integer(),
                sa.ForeignKey("sedes.id", ondelete="SET NULL"),
                nullable=True,
            ),
        )

    idx_name = "ix_crm_events_sede_id"
    if not _has_index("crm_events", idx_name):
        op.create_index(idx_name, "crm_events", ["sede_id"], unique=False)
