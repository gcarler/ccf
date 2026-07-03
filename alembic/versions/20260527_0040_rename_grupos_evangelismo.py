"""0040_rename_compat_groups_to_grupos_evangelismo

Revision ID: 20260527_0040
Revises: 20260527_0039
Create Date: 2026-05-27

Renames compat group tables to canonical evangelism group tables.
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
        ("cell_groups", "grupos_evangelismo"),
        ("cell_group_members", "grupo_participantes"),
        ("cell_group_sessions", "sesiones_grupo"),
        ("cell_group_attendance", "asistencias"),
    ]
    for old, new in renames:
        if old in tables:
            op.rename_table(old, new)


def downgrade() -> None:
    conn = op.get_bind()
    tables = sa.inspect(conn).get_table_names()
    renames = [
        ("grupos_evangelismo", "cell_groups"),
        ("grupo_participantes", "cell_group_members"),
        ("sesiones_grupo", "cell_group_sessions"),
        ("asistencias", "cell_group_attendance"),
    ]
    for old, new in renames:
        if old in tables:
            op.rename_table(old, new)
