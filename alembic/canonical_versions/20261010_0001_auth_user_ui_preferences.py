"""Create auth_user_ui_preferences table.

Revision ID: 20261010_0001_auth_user_ui_preferences
Revises: 20261009_0002_project_task_dimensions_rollup
Create Date: 2026-10-10 16:35:00

Creates auth_user_ui_preferences table for persistent UI preferences:
- id: UUID primary key
- user_id: UUID foreign key auth_users.id ON DELETE CASCADE
- settings: JSONB / JSON default '{}'
- updated_at: DateTime(timezone=True)
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20261010_0001_auth_user_ui_preferences"
down_revision: Union[str, Sequence[str], None] = "20261009_0002_project_task_dimensions_rollup"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _uuid_type() -> sa.types.TypeEngine:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        return sa.dialects.postgresql.UUID(as_uuid=True)
    return sa.String(length=36)


def _json_type() -> sa.types.TypeEngine:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        return sa.dialects.postgresql.JSONB(astext_type=sa.Text())
    return sa.JSON()


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "auth_user_ui_preferences" not in existing_tables:
        op.create_table(
            "auth_user_ui_preferences",
            sa.Column("id", _uuid_type(), primary_key=True, nullable=False),
            sa.Column(
                "user_id",
                _uuid_type(),
                sa.ForeignKey("auth_users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("settings", _json_type(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )
        op.create_index(
            "ix_auth_user_ui_preferences_user_id",
            "auth_user_ui_preferences",
            ["user_id"],
            unique=True,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "auth_user_ui_preferences" in existing_tables:
        op.drop_index(
            "ix_auth_user_ui_preferences_user_id",
            table_name="auth_user_ui_preferences",
        )
        op.drop_table("auth_user_ui_preferences")
