"""Create notification_deliveries table.

Revision ID: 20261011_0002_notification_deliveries
Revises: 20261011_0001_notification_preferences
Create Date: 2026-10-11 05:00:00

Trazabilidad de entregas del Notification Hub (canal email, extensible).
Estados: pending | sent | failed | suppressed.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20261011_0002_notification_deliveries"
down_revision: Union[str, Sequence[str], None] = "20261011_0001_notification_preferences"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _uuid_type() -> sa.types.TypeEngine:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        return sa.dialects.postgresql.UUID(as_uuid=True)
    return sa.String(length=36)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "notification_deliveries" not in existing_tables:
        op.create_table(
            "notification_deliveries",
            sa.Column("id", _uuid_type(), primary_key=True, nullable=False),
            sa.Column(
                "notification_id",
                _uuid_type(),
                sa.ForeignKey("auth_notifications.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "user_id",
                _uuid_type(),
                sa.ForeignKey("auth_users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("channel", sa.String(20), nullable=False),
            sa.Column("recipient", sa.String(320), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'pending'")),
            sa.Column("attempts", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("provider_message_id", sa.String(255), nullable=True),
            sa.Column("error", sa.Text(), nullable=True),
            sa.Column("event_type", sa.String(50), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("read_before_send", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
        )
        op.create_index("ix_notif_deliv_notification_id", "notification_deliveries", ["notification_id"])
        op.create_index("ix_notif_deliv_status", "notification_deliveries", ["status"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "notification_deliveries" in existing_tables:
        op.drop_index("ix_notif_deliv_status", table_name="notification_deliveries")
        op.drop_index("ix_notif_deliv_notification_id", table_name="notification_deliveries")
        op.drop_table("notification_deliveries")
