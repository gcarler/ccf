"""Add prayer_requests.deleted_at to align soft-delete contract.

Revision ID: 20260721_0001_prayer_requests_deleted_at
Revises: 20260718_0001_crm_events_deleted_at
Create Date: 2026-07-21

El CRUD de oración (``backend/crud/crm_/prayer.py``) ya trata
``prayer_requests`` como un recurso soft-deletable: ``delete_prayer_request``
setea ``deleted_at`` y ``get_prayer_requests`` filtra ``deleted_at IS NULL``.
Esta migración agrega la columna faltante en la base de datos para alinear
schema, modelo ORM y routers — siguiendo el patrón de soft-delete uniforme
del backend CCF (Axioma: DateTime(timezone=True) + soft delete en vez de
hard delete).
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "20260721_0001_prayer_requests_deleted_at"
down_revision: Union[str, None] = "20260719_0001_crm_events_deleted_at"
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
    if not _has_table("prayer_requests") or _has_column("prayer_requests", "deleted_at"):
        return

    with op.batch_alter_table("prayer_requests", schema=None) as batch_op:
        batch_op.add_column(sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))

    if not _has_index("prayer_requests", "ix_prayer_requests_deleted_at"):
        op.create_index(
            "ix_prayer_requests_deleted_at",
            "prayer_requests",
            ["deleted_at"],
            unique=False,
        )


def downgrade() -> None:
    if not _has_table("prayer_requests") or not _has_column("prayer_requests", "deleted_at"):
        return

    if _has_index("prayer_requests", "ix_prayer_requests_deleted_at"):
        op.drop_index("ix_prayer_requests_deleted_at", table_name="prayer_requests")

    with op.batch_alter_table("prayer_requests", schema=None) as batch_op:
        batch_op.drop_column("deleted_at")
