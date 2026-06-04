"""add_access_level_to_courses

Revision ID: 6c08efc4e32a
Revises: 20260604_habilitacion_sesiones
Create Date: 2026-06-04

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '6c08efc4e32a'
down_revision: Union[str, None] = '20260604_habilitacion_sesiones'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # La tabla real en prod se llama 'academy_courses' (models_academy.py usa 'courses' como alias legacy)
    op.add_column('academy_courses', sa.Column(
        'access_level',
        sa.String(length=20),
        nullable=False,
        server_default='member',
    ))


def downgrade() -> None:
    op.drop_column('academy_courses', 'access_level')
