"""Merge heads

Revision ID: e47a67a4c954
Revises: 20260522_0021, ffb57364a038
Create Date: 2026-05-23 00:31:03.857704

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e47a67a4c954'
down_revision: Union[str, None] = ('20260522_0021', 'ffb57364a038')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
