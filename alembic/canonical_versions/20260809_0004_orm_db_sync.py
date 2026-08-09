"""ORM↔DB sync: funds.sede_id, persona_ministries.deleted_at, drop drift

El último head (20260809_0003) dejó la cadena Alembic al día, pero el
schema DB no coincidía con los modelos ORM en varios puntos:

  1. ``funds.sede_id`` — declarado en el ORM (models_crm.py:1126) pero
     ausente en la DB. Sin esta columna los filtros financieros por sede
     no funcionan.
  2. ``persona_ministries.deleted_at`` — declarado en el ORM
     (models_kernel.py:79) pero ausente en la DB. El soft-delete del
     CRUD kernel (commit 235964f4) escribe a una columna inexistente
     (Postgres la rechaza / SQLite la descarta silenciosamente).
  3. ``_lock_probe`` — tabla probe de locking, 1 fila, sin FKs ni ORM.
  4. ``public_contact_submissions`` — tabla huérfana, 0 filas, sin ORM.
  5. ``crm_tareas.automation_key``, ``event_id``, ``registration_id`` —
     columnas fantasma en la DB (0 filas non-NULL), ausentes del ORM.
     Probablemente residuo de una migración anterior que las añadió
     pero el código nunca las consumió.

Esta migración sincroniza todo. Reversible.

Revision ID: 20260809_0004_orm_sync
Revises: 20260809_0003_dedup_sede_idx
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260809_0004_orm_sync"
down_revision: Union[str, None] = "20260809_0003_dedup_sede_idx"
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
    if op.get_bind().dialect.name == "postgresql":
        return postgresql.UUID(as_uuid=True)
    return sa.String(36)


def upgrade() -> None:
    # 1. funds.sede_id — columna ORM ausente en DB.
    if not _has_column("funds", "sede_id"):
        with op.batch_alter_table("funds") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "sede_id",
                    _uuid_type(),
                    sa.ForeignKey("sedes.id", ondelete="SET NULL"),
                    nullable=True,
                )
            )
    if not _has_index("funds", "ix_funds_sede_id"):
        op.create_index("ix_funds_sede_id", "funds", ["sede_id"], unique=False)

    # 2. persona_ministries.deleted_at — columna ORM ausente en DB.
    if not _has_column("persona_ministries", "deleted_at"):
        with op.batch_alter_table("persona_ministries") as batch_op:
            batch_op.add_column(
                sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True)
            )
    if not _has_index("persona_ministries", "ix_persona_ministries_deleted_at"):
        op.create_index("ix_persona_ministries_deleted_at", "persona_ministries", ["deleted_at"], unique=False)

    # 3. Drop _lock_probe (tabla probe de locking, sin FKs ni ORM).
    if _has_table("_lock_probe"):
        op.drop_table("_lock_probe")

    # 4. Drop public_contact_submissions (tabla huérfana, sin FKs ni ORM).
    if _has_table("public_contact_submissions"):
        op.drop_table("public_contact_submissions")

    # 5. Drop crm_tareas columnas fantasma (0 filas non-NULL, ausentes del ORM).
    for col in ("automation_key", "event_id", "registration_id"):
        if _has_column("crm_tareas", col):
            with op.batch_alter_table("crm_tareas") as batch_op:
                batch_op.drop_column(col)


def downgrade() -> None:
    # Re-create crm_tareas phantom columns (no FKs, no data — pure recovery).
    if _has_table("crm_tareas"):
        for col, col_type in (
            ("automation_key", sa.String(100)),
            ("event_id", _uuid_type()),
            ("registration_id", _uuid_type()),
        ):
            if not _has_column("crm_tareas", col):
                with op.batch_alter_table("crm_tareas") as batch_op:
                    batch_op.add_column(sa.Column(col, col_type, nullable=True))

    # Re-create public_contact_submissions
    if not _has_table("public_contact_submissions"):
        op.create_table(
            "public_contact_submissions",
            sa.Column("id", _uuid_type(), primary_key=True),
            sa.Column("name", sa.String(200), nullable=False),
            sa.Column("email", sa.String(255), nullable=False),
            sa.Column("phone", sa.String(50), nullable=True),
            sa.Column("message", sa.Text, nullable=True),
            sa.Column("status", sa.String(20), server_default="new", nullable=False),
            sa.Column("sede_id", _uuid_type(), sa.ForeignKey("sedes.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )

    # Re-create _lock_probe
    if not _has_table("_lock_probe"):
        op.create_table("_lock_probe", sa.Column("id", sa.Integer, primary_key=True))

    # Drop persona_ministries.deleted_at
    if _has_index("persona_ministries", "ix_persona_ministries_deleted_at"):
        op.drop_index("ix_persona_ministries_deleted_at", table_name="persona_ministries")
    if _has_column("persona_ministries", "deleted_at"):
        with op.batch_alter_table("persona_ministries") as batch_op:
            batch_op.drop_column("deleted_at")

    # Drop funds.sede_id
    if _has_index("funds", "ix_funds_sede_id"):
        op.drop_index("ix_funds_sede_id", table_name="funds")
    if _has_column("funds", "sede_id"):
        with op.batch_alter_table("funds") as batch_op:
            batch_op.drop_column("sede_id")