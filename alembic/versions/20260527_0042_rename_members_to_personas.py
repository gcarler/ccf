"""0042_rename_members_to_personas

Revision ID: 20260527_0042
Revises: 20260527_0041
Create Date: 2026-05-27

Renames members table to personas (church-agnostic).
"""

from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "20260527_0042"
down_revision: Union[str, None] = "20260527_0041"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    tables = sa.inspect(conn).get_table_names()

    if 'members' in tables:
        # Drop constraints that reference members first
        # Then rename the table
        op.rename_table('members', 'personas')

        # Rename indexes
        for old, new in [
            ('ix_members_sede', 'ix_personas_sede'),
            ('ix_members_rol_iglesia', 'ix_personas_rol_iglesia'),
            ('ix_members_fecha_registro', 'ix_personas_fecha_registro'),
            ('ix_members_estado_vital', 'ix_personas_estado_vital'),
            ('ix_members_ministerio', 'ix_personas_ministerio'),
        ]:
            try:
                op.execute(f'ALTER INDEX {old} RENAME TO {new}')
            except:
                pass  # Index may not exist


def downgrade() -> None:
    conn = op.get_bind()
    tables = sa.inspect(conn).get_table_names()

    if 'personas' in tables:
        op.rename_table('personas', 'members')
