"""Add metadata column to admin_audit_logs

Revision ID: 25ca4fa2fff6
Revises: 20260524_0024_prod_hardening3
Create Date: 2026-05-24 03:22:55.880163

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '25ca4fa2fff6'
down_revision: Union[str, None] = '20260524_0024_prod_hardening3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("admin_audit_logs") as batch_op:
        batch_op.add_column(sa.Column("metadata", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("admin_audit_logs") as batch_op:
        batch_op.drop_column("metadata")
