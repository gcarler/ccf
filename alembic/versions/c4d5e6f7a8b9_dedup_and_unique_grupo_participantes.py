"""deduplicate grupo_participantes and add unique constraint (grupo_id, persona_id)

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
Create Date: 2026-06-11

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'c4d5e6f7a8b9'
down_revision: Union[str, None] = 'b3c4d5e6f7a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Eliminar duplicados manteniendo el registro más antiguo (id más bajo)
    op.execute("""
        DELETE FROM grupo_participantes
        WHERE id NOT IN (
            SELECT MIN(id)
            FROM grupo_participantes
            GROUP BY grupo_id, persona_id
        )
    """)

    # Agregar constraint único
    op.create_unique_constraint(
        "uq_participante_grupo_persona",
        "grupo_participantes",
        ["grupo_id", "persona_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_participante_grupo_persona", "grupo_participantes", type_="unique")
