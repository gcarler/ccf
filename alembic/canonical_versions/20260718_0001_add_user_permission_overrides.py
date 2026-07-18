"""Persist direct per-person permission grants without replacing base roles.

Revision ID: 20260718_0001
Revises: 20260717_0006
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260718_0001"
down_revision = "20260717_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auth_user_permission_overrides",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("auth_users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("permisos", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_auth_user_permission_overrides_user_id",
        "auth_user_permission_overrides",
        ["user_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_auth_user_permission_overrides_user_id", table_name="auth_user_permission_overrides")
    op.drop_table("auth_user_permission_overrides")
