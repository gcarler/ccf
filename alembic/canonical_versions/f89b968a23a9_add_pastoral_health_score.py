"""add_pastoral_health_score

Revision ID: f89b968a23a9
Revises: e71d968a23a8
Create Date: 2026-07-10 05:37:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f89b968a23a9'
down_revision: Union[str, None] = 'e71d968a23a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('personas') as batch_op:
        batch_op.add_column(sa.Column('health_score', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('health_status', sa.String(length=20), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('personas') as batch_op:
        batch_op.drop_column('health_status')
        batch_op.drop_column('health_score')
