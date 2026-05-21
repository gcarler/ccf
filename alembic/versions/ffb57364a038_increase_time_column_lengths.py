"""increase_time_column_lengths

Revision ID: ffb57364a038
Revises: 20260519_0018
Create Date: 2026-05-21 00:22:16.731841

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ffb57364a038'
down_revision: Union[str, None] = '20260519_0018'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('crm_events') as batch_op:
        batch_op.alter_column('start_time',
                              existing_type=sa.VARCHAR(length=10),
                              type_=sa.VARCHAR(length=50),
                              existing_nullable=True)
        batch_op.alter_column('end_time',
                              existing_type=sa.VARCHAR(length=10),
                              type_=sa.VARCHAR(length=50),
                              existing_nullable=True)

    with op.batch_alter_table('glory_houses') as batch_op:
        batch_op.alter_column('start_time',
                              existing_type=sa.VARCHAR(length=10),
                              type_=sa.VARCHAR(length=50),
                              existing_nullable=True)
        batch_op.alter_column('end_time',
                              existing_type=sa.VARCHAR(length=10),
                              type_=sa.VARCHAR(length=50),
                              existing_nullable=True)


def downgrade() -> None:
    with op.batch_alter_table('glory_houses') as batch_op:
        batch_op.alter_column('end_time',
                              existing_type=sa.VARCHAR(length=50),
                              type_=sa.VARCHAR(length=10),
                              existing_nullable=True)
        batch_op.alter_column('start_time',
                              existing_type=sa.VARCHAR(length=50),
                              type_=sa.VARCHAR(length=10),
                              existing_nullable=True)

    with op.batch_alter_table('crm_events') as batch_op:
        batch_op.alter_column('end_time',
                              existing_type=sa.VARCHAR(length=50),
                              type_=sa.VARCHAR(length=10),
                              existing_nullable=True)
        batch_op.alter_column('start_time',
                              existing_type=sa.VARCHAR(length=50),
                              type_=sa.VARCHAR(length=10),
                              existing_nullable=True)
