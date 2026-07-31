"""add_sede_id_to_auth_notifications

M-06: Agrega columna ``sede_id`` nullable a ``auth_notifications`` para
permitir filtrado multi-tenant directo sin JOIN a ``auth_users``.

Revision ID: 20260724_0002
Revises: 20260724_0001
"""

import sqlalchemy as sa

from alembic import op

revision = "20260724_0002"
down_revision = "20260724_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "auth_notifications",
        sa.Column(
            "sede_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("sedes.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_auth_notifications_sede_id",
        "auth_notifications",
        ["sede_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_auth_notifications_sede_id", table_name="auth_notifications")
    op.drop_column("auth_notifications", "sede_id")
