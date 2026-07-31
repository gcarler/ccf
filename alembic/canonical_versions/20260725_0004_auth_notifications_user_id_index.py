"""20260725_0004 — add index on auth_notifications.user_id

Revision ID: 20260725_0004
Revises: 20260725_0003
"""

from alembic import op

revision = "20260725_0004"
down_revision = "20260725_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_auth_notifications_user_id",
        "auth_notifications",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_auth_notifications_user_id", table_name="auth_notifications")
