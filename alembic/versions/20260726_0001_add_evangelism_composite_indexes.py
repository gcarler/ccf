"""add evangelism composite indexes for N+1 performance fix

Revision ID: 20260726_0001
Revises: 20260725_0004
Create Date: 2026-07-26

Adds composite indexes to high-frequency query paths in the evangelism
module.  All three indexes target the most-queried column combinations
identified in the 2026-07-26 audit (P-06).
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "20260726_0001"
down_revision: Union[str, None] = "20260725_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _index_exists(name: str) -> bool:
    conn = op.get_bind()
    r = conn.execute(
        sa.text("SELECT count(*) FROM pg_indexes WHERE indexname = :n"),
        {"n": name},
    )
    return r.scalar() > 0


def upgrade() -> None:
    indexes = [
        ("ix_asistencia_sesion_persona", "asistencias", ["sesion_id", "persona_id"]),
        ("ix_participante_grupo_active", "grupo_participantes", ["grupo_id", "activo"]),
        ("ix_sesion_grupo_grupo_fecha", "sesiones_grupo", ["grupo_id", "fecha_sesion"]),
    ]
    for name, table, columns in indexes:
        if not _index_exists(name):
            op.create_index(name, table, columns, unique=False)


def downgrade() -> None:
    for name in ["ix_asistencia_sesion_persona", "ix_participante_grupo_active", "ix_sesion_grupo_grupo_fecha"]:
        if _index_exists(name):
            op.drop_index(name)
