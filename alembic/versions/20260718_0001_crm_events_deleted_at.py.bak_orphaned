"""Add crm_events.deleted_at to align soft-delete contract.

Revision ID: 20260718_0001_crm_events_deleted_at
Revises: 20260701_0003_crm_events_uuid
Create Date: 2026-07-18

El módulo de evangelismo y el CRUD CRM ya tratan ``crm_events`` como un
recurso soft-deletable. Esta migración agrega la columna faltante
``deleted_at`` para alinear base de datos, modelo ORM y routers.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "20260718_0001_crm_events_deleted_at"
down_revision: Union[str, None] = "20260701_0003_crm_events_uuid"
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
