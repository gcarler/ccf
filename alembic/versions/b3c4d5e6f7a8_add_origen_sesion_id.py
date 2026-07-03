"""add origen_sesion_id to personas and crm_casos; add origen_grupo/estrategia to crm_casos

Revision ID: b3c4d5e6f7a8
Revises: 476e020b8e2d
Create Date: 2026-06-11

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = 'b3c4d5e6f7a8'
down_revision: Union[str, None] = '476e020b8e2d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # personas: agregar origen_sesion_id
    op.add_column('personas',
        sa.Column('origen_sesion_id', sa.Integer(),
                  sa.ForeignKey('sesiones_grupo.id', ondelete='SET NULL'),
                  nullable=True)
    )
    # crm_casos: agregar los 3 campos de origen evangelismo
    op.add_column('crm_casos',
        sa.Column('origen_sesion_id', sa.Integer(),
                  sa.ForeignKey('sesiones_grupo.id', ondelete='SET NULL'),
                  nullable=True)
    )
    op.add_column('crm_casos',
        sa.Column('origen_grupo_id', sa.UUID(),
                  sa.ForeignKey('grupos_evangelismo.id', ondelete='SET NULL'),
                  nullable=True)
    )
    op.add_column('crm_casos',
        sa.Column('origen_estrategia_id', sa.String(36),
                  sa.ForeignKey('estrategias_evangelismo.id', ondelete='SET NULL'),
                  nullable=True)
    )


def downgrade() -> None:
    op.drop_column('crm_casos', 'origen_estrategia_id')
    op.drop_column('crm_casos', 'origen_grupo_id')
    op.drop_column('crm_casos', 'origen_sesion_id')
    op.drop_column('personas', 'origen_sesion_id')
