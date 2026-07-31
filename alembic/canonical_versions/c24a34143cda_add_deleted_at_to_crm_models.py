"""add deleted_at to crm models

Revision ID: c24a34143cda
Revises: 20260725_0004
Create Date: 2026-07-28 19:02:41.958236

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c24a34143cda"
down_revision: Union[str, None] = "20260725_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add deleted_at + index only to the CRM tables that now support soft-delete.
    tables = [
        "positions",
        "ministries",
        "persona_positions",
        "persona_ministry_assignments",
        "volunteer_skills",
        "funds",
        "families",
    ]
    for table in tables:
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.add_column(sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
            batch_op.create_index(batch_op.f(f"ix_{table}_deleted_at"), ["deleted_at"], unique=False)


def downgrade() -> None:
    tables = [
        "families",
        "funds",
        "volunteer_skills",
        "persona_ministry_assignments",
        "persona_positions",
        "ministries",
        "positions",
    ]
    for table in tables:
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.drop_index(batch_op.f(f"ix_{table}_deleted_at"))
            batch_op.drop_column("deleted_at")
