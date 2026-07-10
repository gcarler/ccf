"""add_donation_date to donations

Revision ID: a89b968a23b0
Revises: f89b968a23a9
Create Date: 2026-07-10 06:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a89b968a23b0'
down_revision: Union[str, None] = 'f89b968a23a9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('donations') as batch_op:
        batch_op.add_column(sa.Column('donation_date', sa.Date(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('donations') as batch_op:
        batch_op.drop_column('donation_date')
