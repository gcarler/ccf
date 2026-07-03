"""0042_grupos_evangelismo_columns

Revision ID: 20260527_0042
Revises: 20260527_0041
Create Date: 2026-05-27

Agrega columnas faltantes a grupos_evangelismo:
codigo, direccion, capacidad, lider_persona_id, asistente_persona_id,
anfitrion_persona_id, updated_at.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "20260527_0042"
down_revision: Union[str, None] = "20260527_0041"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    cols = [c["name"] for c in sa.inspect(conn).get_columns("grupos_evangelismo")]

    if "codigo" not in cols:
        op.add_column("grupos_evangelismo", sa.Column("codigo", sa.String(30), nullable=True))
        op.create_index("ix_grupos_evangelismo_codigo", "grupos_evangelismo", ["codigo"], unique=True)

    if "direccion" not in cols:
        op.add_column("grupos_evangelismo", sa.Column("direccion", sa.String(255), nullable=True))

    if "capacidad" not in cols:
        op.add_column("grupos_evangelismo", sa.Column("capacidad", sa.Integer(), nullable=True, server_default="15"))

    if "lider_persona_id" not in cols:
        op.add_column(
            "grupos_evangelismo",
            sa.Column("lider_persona_id", UUID(as_uuid=True), sa.ForeignKey("personas.id", ondelete="SET NULL"), nullable=True),
        )

    if "asistente_persona_id" not in cols:
        op.add_column(
            "grupos_evangelismo",
            sa.Column("asistente_persona_id", UUID(as_uuid=True), sa.ForeignKey("personas.id", ondelete="SET NULL"), nullable=True),
        )

    if "anfitrion_persona_id" not in cols:
        op.add_column(
            "grupos_evangelismo",
            sa.Column("anfitrion_persona_id", UUID(as_uuid=True), sa.ForeignKey("personas.id", ondelete="SET NULL"), nullable=True),
        )

    if "updated_at" not in cols:
        op.add_column(
            "grupos_evangelismo",
            sa.Column("updated_at", sa.DateTime(), nullable=True, server_default=sa.func.now()),
        )


def downgrade() -> None:
    conn = op.get_bind()
    cols = [c["name"] for c in sa.inspect(conn).get_columns("grupos_evangelismo")]

    for col in ["updated_at", "anfitrion_persona_id", "asistente_persona_id",
                "lider_persona_id", "capacidad", "direccion"]:
        if col in cols:
            op.drop_column("grupos_evangelismo", col)

    # Drop the unique index for codigo
    try:
        op.drop_index("ix_grupos_evangelismo_codigo", table_name="grupos_evangelismo")
    except Exception:
        pass

    if "codigo" in cols:
        op.drop_column("grupos_evangelismo", "codigo")
