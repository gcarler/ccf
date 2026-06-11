"""Add season_id column to sesiones_grupo

Revision ID: 20260611_season_id_sesiones
Revises: 20260607_evangelism_default_role
Create Date: 2026-06-11

Agrega la columna real season_id a sesiones_grupo con FK a campaign_seasons.
Corrige el bug donde season_id era un @property Python y no se podía usar
en filtros SQLAlchemy (violación Regla D de REGLAS.md).
Las sesiones existentes quedan con season_id NULL — sin pérdida de datos.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260611_season_id_sesiones"
down_revision: Union[str, None] = "20260607_evangelism_default_role"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_col(table: str, column: str) -> bool:
    bind = op.get_bind()
    cols = {col["name"] for col in sa.inspect(bind).get_columns(table)}
    return column in cols


def _has_index(table: str, index_name: str) -> bool:
    bind = op.get_bind()
    indexes = {idx["name"] for idx in sa.inspect(bind).get_indexes(table)}
    return index_name in indexes


def upgrade() -> None:
    if not _has_col("sesiones_grupo", "season_id"):
        op.add_column(
            "sesiones_grupo",
            sa.Column("season_id", sa.Integer(), nullable=True),
        )
        # FK solo en PostgreSQL — SQLite no soporta ADD CONSTRAINT FOREIGN KEY
        bind = op.get_bind()
        if bind.dialect.name == "postgresql":
            op.create_foreign_key(
                "fk_sesiones_grupo_season_id",
                "sesiones_grupo",
                "campaign_seasons",
                ["season_id"],
                ["id"],
                ondelete="SET NULL",
            )

    if not _has_index("sesiones_grupo", "ix_sesiones_grupo_season_id"):
        op.create_index(
            "ix_sesiones_grupo_season_id",
            "sesiones_grupo",
            ["season_id"],
            unique=False,
        )


def downgrade() -> None:
    if _has_index("sesiones_grupo", "ix_sesiones_grupo_season_id"):
        op.drop_index("ix_sesiones_grupo_season_id", table_name="sesiones_grupo")

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.drop_constraint(
            "fk_sesiones_grupo_season_id",
            "sesiones_grupo",
            type_="foreignkey",
        )

    if _has_col("sesiones_grupo", "season_id"):
        op.drop_column("sesiones_grupo", "season_id")
