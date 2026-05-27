"""0040_rename_glory_house_to_cell_group

Revision ID: 20260527_0040
Revises: 20260527_0039
Create Date: 2026-05-27

Renames GloryHouse tables to CellGroup (church-agnostic).
Only renames if tables exist (idempotent).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260527_0040"
down_revision: Union[str, None] = "20260527_0039"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    tables = sa.inspect(conn).get_table_names()
    renames = [
        ("glory_houses", "cell_groups"),
        ("glory_house_members", "cell_group_members"),
        ("glory_house_sessions", "cell_group_sessions"),
        ("glory_house_attendance", "cell_group_attendance"),
    ]
    for old, new in renames:
        if old in tables:
            op.rename_table(old, new)


def downgrade() -> None:
    conn = op.get_bind()
    tables = sa.inspect(conn).get_table_names()
    renames = [
        ("cell_groups", "glory_houses"),
        ("cell_group_members", "glory_house_members"),
        ("cell_group_sessions", "glory_house_sessions"),
        ("cell_group_attendance", "glory_house_attendance"),
    ]
    for old, new in renames:
        if old in tables:
            op.rename_table(old, new)
