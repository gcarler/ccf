"""Add crm_events.deleted_at to align soft-delete contract (chain fix).

Revision ID: 20260719_0001_crm_events_deleted_at
Revises: 20260718_0003
Create Date: 2026-07-19

Contexto
========

El módulo de evangelismo y el CRUD CRM ya tratan ``crm_events`` como un
recurso soft-deletable. El endpoint ``GET /api/system/calendar``
(``backend/api/system.py:141``) filtra por ``CrmEvents.deleted_at.is_(None)``
y el modelo ORM ``CrmEvent`` (``backend/models_crm.py:99``) declara la
columna ``deleted_at`` con índice.

Sin embargo, en producción la columna no existía y el endpoint lanzaba::

    sqlalchemy.exc.ProgrammingError: column crm_events.deleted_at does not exist

Origen del bug
--------------

Una migración previa que pretendía añadir esta columna
(``20260718_0001_crm_events_deleted_at`` en ``alembic/versions/``) quedó
HUÉRFANA del chain porque su ``down_revision`` apuntaba a una revisión que
no pertenece al árbol canónico cargado por ``alembic.ini::version_locations``
(``canonical_versions/``). El chain activo pasaba por
``20260718_0001 (canonical) → 0002 → 0003`` y nunca enlazaba la migración
huérfana, así que ``alembic upgrade head`` no la aplicaba. El archivo huérfano
fue respaldado como ``.bak_orphaned`` para auditoría.

Esta migración re-abre el fix dentro del chain canónico apuntando a
``20260718_0003`` (head anterior) como padre, convirtiéndose en la nueva head.

La operación es la misma del archivo huérfano (ADD COLUMN + index), solo
corrige el enlace con la cadena. No hace falta una ``downgrade`` distinta
porque la migración nunca se aplicó en producción: cualquier entorno que
esté en ``20260718_0003`` puede aplicarla o revertirla de forma idempotente.

Idempotencia
------------

La migración valida antes de alterar (``_has_column`` / ``_has_index``) para
ser segura frente a entornos que ya la hayan aplicado manualmente vía
ALTER TABLE — no falla si la columna o el índice ya existen.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "20260719_0001_crm_events_deleted_at"
down_revision: Union[str, None] = "20260718_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


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


def upgrade() -> None:
    if not _has_table("crm_events") or _has_column("crm_events", "deleted_at"):
        return

    with op.batch_alter_table("crm_events", schema=None) as batch_op:
        batch_op.add_column(sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))

    if not _has_index("crm_events", "ix_crm_events_deleted_at"):
        op.create_index("ix_crm_events_deleted_at", "crm_events", ["deleted_at"], unique=False)


def downgrade() -> None:
    if not _has_table("crm_events") or not _has_column("crm_events", "deleted_at"):
        return

    if _has_index("crm_events", "ix_crm_events_deleted_at"):
        op.drop_index("ix_crm_events_deleted_at", table_name="crm_events")

    with op.batch_alter_table("crm_events", schema=None) as batch_op:
        batch_op.drop_column("deleted_at")
