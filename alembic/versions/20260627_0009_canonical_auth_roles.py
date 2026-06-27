"""Remove the parallel Kernel platform-role store.

Revision ID: 20260627_0009_auth_roles
Revises: 20260627_0008_agenda_contract
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260627_0009_auth_roles"
down_revision: str | None = "20260627_0008_agenda_contract"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    connection = op.get_bind()
    missing_roles = connection.execute(
        sa.text("SELECT COUNT(*) FROM auth_users WHERE rol_plataforma_id IS NULL")
    ).scalar_one()
    if missing_roles:
        raise RuntimeError(
            f"Cannot remove Kernel roles: {missing_roles} auth users lack a canonical auth role"
        )

    op.drop_column("auth_users", "platform_role_id")
    op.drop_table("persona_platform_roles")
    op.drop_table("platform_role_definitions")


def downgrade() -> None:
    role_enum = postgresql.ENUM(
        "ADMINISTRADOR",
        "GESTOR",
        "EDITOR",
        "LECTOR",
        name="platform_role",
        create_type=False,
    )
    op.create_table(
        "platform_role_definitions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("role", role_enum, nullable=False, unique=True),
        sa.Column("permissions", sa.JSON(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "persona_platform_roles",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "persona_id",
            sa.Uuid(),
            sa.ForeignKey("personas.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "role_id",
            sa.Integer(),
            sa.ForeignKey("platform_role_definitions.id"),
            nullable=False,
        ),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.UniqueConstraint("persona_id", "role_id", name="uq_persona_platform_role"),
    )
    op.add_column(
        "auth_users", sa.Column("platform_role_id", sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        "fk_auth_users_platform_role_id",
        "auth_users",
        "platform_role_definitions",
        ["platform_role_id"],
        ["id"],
    )
