"""add_pastoral_health_score

Revision ID: f89b968a23a9
Revises: e71d968a23a8
Create Date: 2026-07-10 05:37:00

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f89b968a23a9"
down_revision: Union[str, None] = "e71d968a23a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    existing = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("personas")}
    missing = {
        "health_score": sa.Column("health_score", sa.Integer(), nullable=True),
        "health_status": sa.Column("health_status", sa.String(length=20), nullable=True),
    }
    if any(name not in existing for name in missing):
        with op.batch_alter_table("personas") as batch_op:
            for name, column in missing.items():
                if name not in existing:
                    batch_op.add_column(column)


def downgrade() -> None:
    existing = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("personas")}
    if "health_score" in existing or "health_status" in existing:
        with op.batch_alter_table("personas") as batch_op:
            if "health_status" in existing:
                batch_op.drop_column("health_status")
            if "health_score" in existing:
                batch_op.drop_column("health_score")
