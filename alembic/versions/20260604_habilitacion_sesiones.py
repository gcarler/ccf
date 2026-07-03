"""add estado_habilitacion to sesiones_grupo

Revision ID: 20260604_habilitacion_sesiones
Revises: 20260603_0054_grupo_soft_delete
Create Date: 2026-06-04

Adds session governance: estado_habilitacion (DESHABILITADO/HABILITADO/CERRADO)
and habilitado_por (quien habilitó manualmente) to sesiones_grupo.
"""
import sqlalchemy as sa

from alembic import op

revision = '20260604_habilitacion_sesiones'
down_revision = '20260603_0054_grupo_soft_delete'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('sesiones_grupo',
        sa.Column('estado_habilitacion', sa.String(20), nullable=False,
                  server_default='DESHABILITADO'))
    op.add_column('sesiones_grupo',
        sa.Column('habilitado_por', sa.UUID(), nullable=True))
    op.add_column('sesiones_grupo',
        sa.Column('habilitado_en', sa.DateTime(timezone=True), nullable=True))


def downgrade():
    op.drop_column('sesiones_grupo', 'habilitado_en')
    op.drop_column('sesiones_grupo', 'habilitado_por')
    op.drop_column('sesiones_grupo', 'estado_habilitacion')
