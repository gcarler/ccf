"""add max_attempts and cooldown_minutes to academy_assessments

Revision ID: 20261007_0001_academy_assessment_retry_cooldown
Revises: 20260928_0020_academy_calendar_events
Create Date: 2026-10-07 04:20:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20261007_0001_academy_assessment_retry_cooldown"
down_revision: Union[str, None] = "20260928_0020_academy_calendar_events"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()
    if "academy_assessments" in existing_tables:
        existing_cols = {column["name"] for column in inspector.get_columns("academy_assessments")}
        missing = {
            "max_attempts": sa.Column("max_attempts", sa.Integer(), nullable=True, server_default="3"),
            "cooldown_minutes": sa.Column("cooldown_minutes", sa.Integer(), nullable=True, server_default="60"),
        }
        with op.batch_alter_table("academy_assessments") as batch_op:
            for name, column in missing.items():
                if name not in existing_cols:
                    batch_op.add_column(column)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()
    if "academy_assessments" in existing_tables:
        existing_cols = {column["name"] for column in inspector.get_columns("academy_assessments")}
        with op.batch_alter_table("academy_assessments") as batch_op:
            if "cooldown_minutes" in existing_cols:
                batch_op.drop_column("cooldown_minutes")
            if "max_attempts" in existing_cols:
                batch_op.drop_column("max_attempts")
