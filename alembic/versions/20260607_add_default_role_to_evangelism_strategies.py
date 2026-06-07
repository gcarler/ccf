"""Add default role to evangelism strategies

Revision ID: 20260607_evangelism_default_role
Revises: 20260605_agents_gov_backfill
Create Date: 2026-06-07 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260607_evangelism_default_role"
down_revision: Union[str, None] = "20260605_agents_gov_backfill"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "estrategias_evangelismo",
        sa.Column("default_role_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_estrategias_evangelismo_default_role_id",
        "estrategias_evangelismo",
        ["default_role_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_estrategias_evangelismo_default_role_id_estrategia_roles_personalizados",
        "estrategias_evangelismo",
        "estrategia_roles_personalizados",
        ["default_role_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_estrategias_evangelismo_default_role_id_estrategia_roles_personalizados",
        "estrategias_evangelismo",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_estrategias_evangelismo_default_role_id",
        table_name="estrategias_evangelismo",
    )
    op.drop_column("estrategias_evangelismo", "default_role_id")
