"""Add real columns for novelty_type, novelty_detail, reported_by_persona_id, report_deadline to sesiones_grupo

Revision ID: 20260708_sesion_grupo_real_columns
Revises: 20260706_0003_cms_sections_phase2
Create Date: 2026-07-08

Convierte cuatro atributos que eran @property Python stubs sin persistencia
a columnas reales en la tabla sesiones_grupo:

- novelty_type        -> String(50), nullable
- novelty_detail      -> Text, nullable
- reported_by_persona_id -> UUID, FK personas.id ON DELETE SET NULL, nullable
- report_deadline     -> DateTime(timezone=True), nullable

Las sesiones existentes quedan con NULL en estos campos — sin pérdida de
datos porque los valores nunca se persistían anteriormente.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "20260708_sesion_grupo_real_columns"
down_revision: Union[str, None] = "20260706_0003_cms_sections_phase2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_col(table: str, column: str) -> bool:
    bind = op.get_bind()
    cols = {col["name"] for col in sa.inspect(bind).get_columns(table)}
    return column in cols


def upgrade() -> None:
    if not _has_col("sesiones_grupo", "novelty_type"):
        op.add_column(
            "sesiones_grupo",
            sa.Column("novelty_type", sa.String(50), nullable=True),
        )

    if not _has_col("sesiones_grupo", "novelty_detail"):
        op.add_column(
            "sesiones_grupo",
            sa.Column("novelty_detail", sa.Text(), nullable=True),
        )

    if not _has_col("sesiones_grupo", "reported_by_persona_id"):
        op.add_column(
            "sesiones_grupo",
            sa.Column("reported_by_persona_id", UUID(as_uuid=True), nullable=True),
        )
        # FK solo en PostgreSQL — SQLite no soporta ADD CONSTRAINT FOREIGN KEY
        bind = op.get_bind()
        if bind.dialect.name == "postgresql":
            op.create_foreign_key(
                "fk_sesiones_grupo_reported_by_persona_id",
                "sesiones_grupo",
                "personas",
                ["reported_by_persona_id"],
                ["id"],
                ondelete="SET NULL",
            )

    if not _has_col("sesiones_grupo", "report_deadline"):
        op.add_column(
            "sesiones_grupo",
            sa.Column("report_deadline", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    if _has_col("sesiones_grupo", "report_deadline"):
        op.drop_column("sesiones_grupo", "report_deadline")

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.drop_constraint(
            "fk_sesiones_grupo_reported_by_persona_id",
            "sesiones_grupo",
            type_="foreignkey",
        )

    if _has_col("sesiones_grupo", "reported_by_persona_id"):
        op.drop_column("sesiones_grupo", "reported_by_persona_id")

    if _has_col("sesiones_grupo", "novelty_detail"):
        op.drop_column("sesiones_grupo", "novelty_detail")

    if _has_col("sesiones_grupo", "novelty_type"):
        op.drop_column("sesiones_grupo", "novelty_type")
