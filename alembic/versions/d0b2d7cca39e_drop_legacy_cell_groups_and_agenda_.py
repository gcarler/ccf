"""drop_legacy_cell_groups_and_agenda_events

Revision ID: d0b2d7cca39e
Revises: 5ff8ddf9dce0
Create Date: 2026-06-11 02:11:37.406829

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd0b2d7cca39e'
down_revision: Union[str, None] = '5ff8ddf9dce0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DROP TABLE IF EXISTS _legacy_cell_groups CASCADE")
    op.execute("DROP TABLE IF EXISTS _legacy_agenda_events CASCADE")


def downgrade() -> None:
    op.create_table('_legacy_cell_groups',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(200), nullable=False)
    )
    op.create_table('_legacy_agenda_events',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('created_by_user_id', sa.Integer())
    )

