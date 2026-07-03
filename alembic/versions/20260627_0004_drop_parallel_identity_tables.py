"""Drop empty identity tables superseded by Auth v3.

Revision ID: 20260627_0004_drop_identity
Revises: 20260627_0003_academy_access
"""

from typing import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260627_0004_drop_identity"
down_revision: str | None = "20260627_0003_academy_access"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


PARALLEL_TABLES = [
    "user_badges",
    "user_ui_preferences",
    "user_permissions",
    "notifications",
    "user_reminders",
    "badges",
    "levels",
]


def upgrade() -> None:
    bind = op.get_bind()
    existing = set(sa.inspect(bind).get_table_names())
    populated = []
    for table in PARALLEL_TABLES:
        if table in existing:
            count = bind.execute(sa.text(f'SELECT count(*) FROM "{table}"')).scalar_one()
            if count:
                populated.append(f"{table}={count}")
    if populated:
        raise RuntimeError(
            "Parallel identity tables contain data; migration stopped: " + ", ".join(populated)
        )
    for table in PARALLEL_TABLES:
        if table in existing:
            op.drop_table(table)


def downgrade() -> None:
    uuid = postgresql.UUID(as_uuid=True)
    timestamp = sa.DateTime(timezone=True)
    op.create_table(
        "levels",
        sa.Column("id", uuid, nullable=False),
        sa.Column("title", sa.String(50), nullable=False),
        sa.Column("min_xp", sa.Integer(), nullable=True),
        sa.Column("icon_key", sa.String(50), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("title"),
    )
    op.create_table(
        "badges",
        sa.Column("id", uuid, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("icon_key", sa.String(50), nullable=False),
        sa.Column("xp_reward", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "user_badges",
        sa.Column("id", uuid, nullable=False),
        sa.Column("user_id", uuid, nullable=False),
        sa.Column("badge_id", uuid, nullable=False),
        sa.Column("earned_at", timestamp, nullable=True),
        sa.ForeignKeyConstraint(["badge_id"], ["badges.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["auth_users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "user_ui_preferences",
        sa.Column("id", uuid, nullable=False),
        sa.Column("user_id", uuid, nullable=False),
        sa.Column("settings", postgresql.JSONB(), nullable=True),
        sa.Column("updated_at", timestamp, nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["auth_users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_table(
        "user_permissions",
        sa.Column("id", uuid, nullable=False),
        sa.Column("user_id", uuid, nullable=False),
        sa.Column("permissions", postgresql.JSONB(), nullable=True),
        sa.Column("updated_at", timestamp, nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["auth_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_table(
        "notifications",
        sa.Column("id", uuid, nullable=False),
        sa.Column("user_id", uuid, nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=True),
        sa.Column("created_at", timestamp, nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["auth_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "user_reminders",
        sa.Column("id", uuid, nullable=False),
        sa.Column("user_id", uuid, nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("remind_at", timestamp, nullable=False),
        sa.Column("priority", sa.String(20), nullable=True),
        sa.Column("related_type", sa.String(50), nullable=True),
        sa.Column("related_id", uuid, nullable=True),
        sa.Column("is_dismissed", sa.Boolean(), nullable=True),
        sa.Column("created_at", timestamp, nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["auth_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
