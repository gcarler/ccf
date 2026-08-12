"""Add soft-delete support to Academy forum threads.

Forum threads must remain auditable after archival while disappearing from
learner-facing list, detail, and comment queries, consistently with the other
Academy entities.

Revision ID: 20260810_0001_academy_forum_threads_deleted_at
Revises: 20260809_0005_wiki_multi_tenant
Create Date: 2026-08-10
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "20260810_0001_academy_forum_threads_deleted_at"
down_revision: Union[str, None] = "20260809_0005_wiki_multi_tenant"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _inspector() -> sa.Inspector:
    return sa.inspect(op.get_bind())


def _has_table(table: str) -> bool:
    return table in set(_inspector().get_table_names())


def _has_column(table: str, column: str) -> bool:
    return _has_table(table) and any(item["name"] == column for item in _inspector().get_columns(table))


def _has_index(table: str, index: str) -> bool:
    return _has_table(table) and any(item.get("name") == index for item in _inspector().get_indexes(table))


def upgrade() -> None:
    table_name = "academy_forum_threads"
    index_name = "ix_academy_forum_threads_deleted_at"
    if not _has_table(table_name):
        return

    if not _has_column(table_name, "deleted_at"):
        op.add_column(
            table_name,
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        )
    if not _has_index(table_name, index_name):
        op.create_index(index_name, table_name, ["deleted_at"], unique=False)


def downgrade() -> None:
    if not _has_table("academy_forum_threads") or not _has_column("academy_forum_threads", "deleted_at"):
        return

    if _has_index("academy_forum_threads", "ix_academy_forum_threads_deleted_at"):
        op.drop_index("ix_academy_forum_threads_deleted_at", table_name="academy_forum_threads")
    op.drop_column("academy_forum_threads", "deleted_at")
