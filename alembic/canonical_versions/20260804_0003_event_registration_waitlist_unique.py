"""Add UNIQUE partial index on (event_id, waiting_list_position) — waitlist position race fix.

Revision ID: 20260804_0003_event_registration_waitlist_unique
Revises: 20260804_0002_cms_form_builder_dinamico
Create Date: 2026-08-04

Contexto
========
Fix #13 detectado en auditoría de ``feature/whiteboard-superpro``.

Sin un constraint de unicidad, dos ``_promote_first_waitlist`` concurrentes
sobre el mismo evento pueden asignar el mismo ``waiting_list_position`` a
dos filas distintas (race condition), corrompiendo la cola de espera.

Esta migración añade un **partial UNIQUE index** sobre
``(event_id, waiting_list_position)`` condicionado a ``waiting_list_position
IS NOT NULL``, así:

    - Las filas CONFIRMED/CHECKED_IN/PENDING/CANCELLED con ``position=NULL``
      siguen permitiendo múltiples NULLs (las tablas dimensionales de personas
      con posición None no se rompen).
    - Solo las filas WAITLIST activas (``position IS NOT NULL``) son únicas
      por (event_id, position) — el invariant que el código espera.

Compatibilidad (REGLAS.md §9): aditivo, no destructivo. Solo añade un índice.
En caso de datos ya corruptos con duplicados, los DBA deben sanearlos ANTES
de aplicar esta migración (sino el CREATE INDEX fallará). El SNAPSHOT no
incluye datos esperados con duplicados — la validación pre-prod detecta esto.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "20260804_0003_event_registration_waitlist_unique"
down_revision: Union[str, None] = "20260804_0002_cms_form_builder_dinamico"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ── Helpers de idempotencia (mismo patrón que 20260804_0001) ──────────────────


def _has_table(table: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table in inspector.get_table_names()


def _has_index(table: str, index_name: str) -> bool:
    if not _has_table(table):
        return False
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(idx["name"] == index_name for idx in inspector.get_indexes(table))


INDEX_NAME = "uq_event_reg_waitlist_position"


def upgrade() -> None:
    """Añade el partial unique index sobre (event_id, waiting_list_position).

    Postgres soporta ``postgresql_where``. SQLite >= 3.8 soporta partial
    indexes via ``sqlite_where``. Ambas sintaxis se incluyen para que la
    migración corra en test (SQLite) y prod (Postgres).
    """
    if not _has_table("event_registrations"):
        # Sin la tabla base, no hay nada que indexar.
        return
    if _has_index("event_registrations", INDEX_NAME):
        return

    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "sqlite":
        op.create_index(
            INDEX_NAME,
            "event_registrations",
            ["event_id", "waiting_list_position"],
            unique=True,
            sqlite_where=sa.text("waiting_list_position IS NOT NULL"),
        )
    else:
        # Postgres por defecto.
        op.create_index(
            INDEX_NAME,
            "event_registrations",
            ["event_id", "waiting_list_position"],
            unique=True,
            postgresql_where=sa.text("waiting_list_position IS NOT NULL"),
        )


def downgrade() -> None:
    if not _has_table("event_registrations"):
        return
    if not _has_index("event_registrations", INDEX_NAME):
        return
    op.drop_index(INDEX_NAME, table_name="event_registrations")
