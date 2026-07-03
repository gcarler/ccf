"""add strategy typology columns and grupos_evangelismo FK

Revision ID: 20260524_0027_strategy_typology
Revises: 20260524_0026_prod_ops
Create Date: 2026-05-24

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = '20260524_0027_strategy_typology'
down_revision: Union[str, None] = '20260524_0026_prod_ops'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Evangelism Strategy typology columns ──
    op.add_column('evangelism_strategies', sa.Column('typology', sa.String(50), nullable=True))
    op.create_index(op.f('ix_evangelism_strategies_typology'), 'evangelism_strategies', ['typology'], unique=False)
    op.add_column('evangelism_strategies', sa.Column('recurrence', sa.String(20), nullable=True))
    op.add_column('evangelism_strategies', sa.Column('day_of_week', sa.String(20), nullable=True))
    op.add_column('evangelism_strategies', sa.Column('start_time', sa.String(10), nullable=True))
    op.add_column('evangelism_strategies', sa.Column('event_format', sa.String(30), nullable=True))
    op.add_column('evangelism_strategies', sa.Column('phases', sa.JSON(), nullable=True))
    op.add_column('evangelism_strategies', sa.Column('niche_objective', sa.String(255), nullable=True))

    # ── Grupos strategy FK ──
    op.add_column('grupos_evangelismo', sa.Column('evangelism_strategy_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_grupos_evangelismo_evangelism_strategy_id'), 'grupos_evangelismo', ['evangelism_strategy_id'], unique=False)
    op.create_foreign_key(
        'fk_grupos_evangelismo_evangelism_strategy',
        'grupos_evangelismo', 'evangelism_strategies',
        ['evangelism_strategy_id'], ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    op.drop_constraint('fk_grupos_evangelismo_evangelism_strategy', 'grupos_evangelismo', type_='foreignkey')
    op.drop_index(op.f('ix_grupos_evangelismo_evangelism_strategy_id'), table_name='grupos_evangelismo')
    op.drop_column('grupos_evangelismo', 'evangelism_strategy_id')

    op.drop_column('evangelism_strategies', 'niche_objective')
    op.drop_column('evangelism_strategies', 'phases')
    op.drop_column('evangelism_strategies', 'event_format')
    op.drop_column('evangelism_strategies', 'start_time')
    op.drop_column('evangelism_strategies', 'day_of_week')
    op.drop_column('evangelism_strategies', 'recurrence')
    op.drop_index(op.f('ix_evangelism_strategies_typology'), table_name='evangelism_strategies')
    op.drop_column('evangelism_strategies', 'typology')
