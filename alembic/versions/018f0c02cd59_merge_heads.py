"""merge_heads

Revision ID: 018f0c02cd59
Revises: a1b2c3d4e5f6, d0b2d7cca39e
Create Date: 2026-06-11 11:31:45.850432

"""
from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = '018f0c02cd59'
down_revision: Union[str, None] = ('a1b2c3d4e5f6', 'd0b2d7cca39e')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
