"""create agenda events table

Revision ID: 20260504_0006
Revises: 20260503_0005
Create Date: 2026-05-04 09:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260504_0006"
down_revision = "20260503_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("agenda_events"):
        op.create_table(
            "agenda_events",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("title", sa.String(length=200), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("start_at", sa.DateTime(), nullable=False),
            sa.Column("end_at", sa.DateTime(), nullable=True),
            sa.Column("location", sa.String(length=200), nullable=True),
            sa.Column("is_all_day", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_by_user_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        )
        op.create_index("ix_agenda_events_title", "agenda_events", ["title"], unique=False)
        op.create_index("ix_agenda_events_start_at", "agenda_events", ["start_at"], unique=False)
        op.create_index("ix_agenda_events_end_at", "agenda_events", ["end_at"], unique=False)
        op.create_index("ix_agenda_events_is_all_day", "agenda_events", ["is_all_day"], unique=False)
        op.create_index("ix_agenda_events_created_by_user_id", "agenda_events", ["created_by_user_id"], unique=False)
        op.create_index("ix_agenda_events_created_at", "agenda_events", ["created_at"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("agenda_events"):
        op.drop_index("ix_agenda_events_created_at", table_name="agenda_events")
        op.drop_index("ix_agenda_events_created_by_user_id", table_name="agenda_events")
        op.drop_index("ix_agenda_events_is_all_day", table_name="agenda_events")
        op.drop_index("ix_agenda_events_end_at", table_name="agenda_events")
        op.drop_index("ix_agenda_events_start_at", table_name="agenda_events")
        op.drop_index("ix_agenda_events_title", table_name="agenda_events")
        op.drop_table("agenda_events")
