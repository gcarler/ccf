"""add_user_reminders_user_idx

Revision ID: 72f30090d1d7
Revises: 20260701_0002_no_legacy
Create Date: 2026-07-01 05:41:24.298514

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '72f30090d1d7'
down_revision: Union[str, None] = '20260701_0002_no_legacy'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_user_reminders_user_id",
        "auth_user_reminders",
        ["user_id"],
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_user_reminders_user_id",
        table_name="auth_user_reminders",
        if_exists=True,
    )
