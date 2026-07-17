"""Add sede_id and deleted_at to role_definitions.

Revision ID: 0002_role_def_sede_del
Revises: 20260717_0001
Create Date: 2026-07-17 00:00:02
"""

from alembic import op
import sqlalchemy as sa

revision = "20260717_0002"
down_revision = "20260717_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "role_definitions",
        sa.Column("sede_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "role_definitions",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_role_definitions_sede_id",
        "role_definitions",
        ["sede_id"],
        unique=False,
    )
    op.create_index(
        "ix_role_definitions_deleted_at",
        "role_definitions",
        ["deleted_at"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_role_definitions_sede_id",
        "role_definitions",
        "sedes",
        ["sede_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_role_definitions_sede_id", "role_definitions", type_="foreignkey")
    op.drop_index("ix_role_definitions_deleted_at", "role_definitions")
    op.drop_index("ix_role_definitions_sede_id", "role_definitions")
    op.drop_column("role_definitions", "deleted_at")
    op.drop_column("role_definitions", "sede_id")
