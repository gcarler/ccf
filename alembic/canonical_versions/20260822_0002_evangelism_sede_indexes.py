"""Add missing sede_id indexes for core evangelism tables.

Revision ID: 20260822_0002_evangelism_sede_indexes
Revises: 20260822_0001_pgvector_rag_rls

The campaign_seasons index already exists in the canonical migration chain;
the idempotent helper keeps this migration safe for databases at either
canonical state while adding the missing strategy and group indexes.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op


revision: str = "20260822_0002_evangelism_sede_indexes"
down_revision: Union[str, None] = "20260822_0001_pgvector_rag_rls"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_INDEXES = (
    ("campaign_seasons", "ix_campaign_seasons_sede_id"),
    ("estrategias_evangelismo", "ix_estrategias_evangelismo_sede_id"),
    ("grupos_evangelismo", "ix_grupos_evangelismo_sede_id"),
)


def _index_exists(table_name: str, index_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return any(
        index["name"] == index_name
        for index in inspector.get_indexes(table_name)
    )


def upgrade() -> None:
    for table_name, index_name in _INDEXES:
        if not _index_exists(table_name, index_name):
            op.create_index(index_name, table_name, ["sede_id"], unique=False)


def downgrade() -> None:
    for table_name, index_name in reversed(_INDEXES):
        if _index_exists(table_name, index_name):
            op.drop_index(index_name, table_name=table_name)
