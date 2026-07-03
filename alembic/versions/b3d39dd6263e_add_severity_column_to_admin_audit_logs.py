"""Add severity column to admin_audit_logs

Revision ID: b3d39dd6263e
Revises: 20260524_0022_prod_hardening
Create Date: 2026-05-24 02:58:14.876638

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b3d39dd6263e'
down_revision: Union[str, None] = '20260524_0022_prod_hardening'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("admin_audit_logs") as batch_op:
        batch_op.add_column(sa.Column("severity", sa.String(20), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("admin_audit_logs") as batch_op:
        batch_op.drop_column("severity")
