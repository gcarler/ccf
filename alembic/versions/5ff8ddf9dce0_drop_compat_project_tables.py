"""drop_compat_project_tables

Revision ID: 5ff8ddf9dce0
Revises: 66557d00474b
Create Date: 2026-06-11 02:08:02.176444

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5ff8ddf9dce0'
down_revision: Union[str, None] = '66557d00474b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop compat project tables from the database
    op.execute("DROP TABLE IF EXISTS _compat_project_tasks CASCADE")
    op.execute("DROP TABLE IF EXISTS _compat_projects CASCADE")


def downgrade() -> None:
    # Recreate empty compat project tables for downgrade/rollback compatibility
    op.create_table('_compat_projects',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('title', sa.String(200), nullable=False)
    )
    op.create_table('_compat_project_tasks',
        sa.Column('id', sa.Integer(), sa.ForeignKey('_compat_projects.id', ondelete='CASCADE')),
        sa.Column('title', sa.String(200), nullable=False)
    )
