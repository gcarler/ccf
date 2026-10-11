"""Create notification_preferences table.

Revision ID: 20261011_0001_notification_preferences
Revises: 20261010_0001_auth_user_ui_preferences
Create Date: 2026-10-11 04:00:00

Creates notification_preferences table for per-user notification channel
preferences:
- id: UUID primary key
- user_id: UUID foreign key auth_users.id ON DELETE CASCADE
- sede_id: UUID nullable foreign key sedes.id (tenant scope; NULL = ministerio)
- channel: varchar(20) NOT NULL (in_app | email)
- event_type: varchar(50) NOT NULL (task_assigned | mention | event_reminder | ...)
- enabled: boolean NOT NULL default TRUE
- created_at / updated_at: DateTime(timezone=True)

Unique constraint: (user_id, channel, event_type) via
``uq_notif_pref_user_channel_event``.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20261011_0001_notification_preferences"
down_revision: Union[str, Sequence[str], None] = "20261010_0001_auth_user_ui_preferences"
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

    if "notification_preferences" not in existing_tables:
        op.create_table(
            "notification_preferences",
            sa.Column("id", _uuid_type(), primary_key=True, nullable=False),
            sa.Column(
                "user_id",
                _uuid_type(),
                sa.ForeignKey("auth_users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "sede_id",
                _uuid_type(),
                sa.ForeignKey("sedes.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("channel", sa.String(20), nullable=False),
            sa.Column("event_type", sa.String(50), nullable=False),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )
        op.create_index(
            "ix_notification_preferences_user_id",
            "notification_preferences",
            ["user_id"],
        )
        op.create_index(
            "ix_notification_preferences_sede_id",
            "notification_preferences",
            ["sede_id"],
        )
        op.create_index(
            "uq_notif_pref_user_channel_event",
            "notification_preferences",
            ["user_id", "channel", "event_type"],
            unique=True,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "notification_preferences" in existing_tables:
        op.drop_index(
            "uq_notif_pref_user_channel_event",
            table_name="notification_preferences",
        )
        op.drop_index(
            "ix_notification_preferences_sede_id",
            table_name="notification_preferences",
        )
        op.drop_index(
            "ix_notification_preferences_user_id",
            table_name="notification_preferences",
        )
        op.drop_table("notification_preferences")
