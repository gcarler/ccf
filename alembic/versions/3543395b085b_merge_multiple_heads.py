"""merge_multiple_heads

Revision ID: 3543395b085b
Revises: add_deleted_at_mod, 6c08efc4e32a
Create Date: 2026-06-04 19:21:12.462553

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3543395b085b'
down_revision: Union[str, None] = ('add_deleted_at_mod', '6c08efc4e32a')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
