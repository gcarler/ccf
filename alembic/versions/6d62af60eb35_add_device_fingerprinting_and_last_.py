"""Add device fingerprinting and last_active to refresh tokens

Revision ID: 6d62af60eb35
Revises: e47a67a4c954
Create Date: 2026-05-23 00:31:10.493214

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6d62af60eb35"
down_revision: Union[str, None] = "e47a67a4c954"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Manual surgical update for refresh_tokens fingerprinting
    with op.batch_alter_table("refresh_tokens", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("ip_address", sa.String(length=45), nullable=True)
        )
        batch_op.add_column(
            sa.Column("user_agent", sa.String(length=255), nullable=True)
        )
        batch_op.add_column(sa.Column("last_active", sa.DateTime(), nullable=True))
        # Ensure ID is correct (sqlite specific fixes if needed, but keeping it simple)
        try:
            batch_op.create_index(
                batch_op.f("ix_refresh_tokens_id"), ["id"], unique=False
            )
        except:
            pass


def downgrade() -> None:
    with op.batch_alter_table("refresh_tokens", schema=None) as batch_op:
        batch_op.drop_column("last_active")
        batch_op.drop_column("user_agent")
        batch_op.drop_column("ip_address")
        try:
            batch_op.drop_index(batch_op.f("ix_refresh_tokens_id"))
        except:
            pass
