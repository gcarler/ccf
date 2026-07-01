"""add registros_seguimiento.fecha_creacion

Revision ID: 20260701_0003
Revises: 72f30090d1d7
Create Date: 2026-07-01 07:00:00

The column was added directly via ALTER TABLE earlier. This migration
stamps the schema so alembic knows it is applied.
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260701_0003"
down_revision: str | None = "72f30090d1d7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_table(table: str) -> bool:
    bind = op.get_bind()
    return table in set(sa.inspect(bind).get_table_names())


def _has_column(table: str, column: str) -> bool:
    if not _has_table(table):
        return False
    bind = op.get_bind()
    return column in {c["name"] for c in sa.inspect(bind).get_columns(table)}


def upgrade() -> None:
    if _has_table("registros_seguimiento") and not _has_column(
        "registros_seguimiento", "fecha_creacion"
    ):
        op.add_column(
            "registros_seguimiento",
            sa.Column(
                "fecha_creacion",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )
        op.create_index(
            "ix_registros_seguimiento_fecha_creacion",
            "registros_seguimiento",
            ["fecha_creacion"],
        )


def downgrade() -> None:
    if _has_column("registros_seguimiento", "fecha_creacion"):
        op.drop_index(
            "ix_registros_seguimiento_fecha_creacion",
            table_name="registros_seguimiento",
        )
        op.drop_column("registros_seguimiento", "fecha_creacion")
