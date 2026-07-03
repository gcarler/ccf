"""Drop orphan tables (empty, no model) and cleanup

Removes 8 compat tables that have no SQLAlchemy models and are empty.
Also drops stale _alembic_tmp tables.

Revision ID: 20260524_0031
Revises: 20260524_0030
Create Date: 2026-05-24
"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision = "20260524_0031"
down_revision = "20260524_0030"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DROP TABLE IF EXISTS attendance CASCADE")
    op.execute("DROP TABLE IF EXISTS books CASCADE")
    op.execute("DROP TABLE IF EXISTS consolidation_automations CASCADE")
    op.execute("DROP TABLE IF EXISTS counseling_sessions CASCADE")
    op.execute("DROP TABLE IF EXISTS events CASCADE")
    op.execute("DROP TABLE IF EXISTS mesh_capabilities CASCADE")
    op.execute("DROP TABLE IF EXISTS sermons CASCADE")
    op.execute("DROP TABLE IF EXISTS volunteers CASCADE")
    op.execute("DROP TABLE IF EXISTS _alembic_tmp_event_attendances CASCADE")


def downgrade() -> None:
    # Recreate as empty shells (no data to restore — all were empty)
    op.create_table(
        "attendance",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("member_id", sa.Integer(), nullable=True),
        sa.Column("event_id", sa.Integer(), nullable=True),
        sa.Column("attended", sa.Boolean(), default=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "books",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("author", sa.String(255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price", sa.Numeric(10, 2), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "consolidation_automations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("trigger_event", sa.String(50), nullable=False),
        sa.Column("action_type", sa.String(50), nullable=False),
        sa.Column("action_payload", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "counseling_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ticket_id", sa.Integer(), nullable=True),
        sa.Column("pastor_id", sa.Integer(), nullable=True),
        sa.Column("session_date", sa.DateTime(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("event_date", sa.DateTime(), nullable=True),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "mesh_capabilities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), default=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "sermons",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("preacher", sa.String(100), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("video_url", sa.String(500), nullable=True),
        sa.Column("audio_url", sa.String(500), nullable=True),
        sa.Column("date_preached", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "volunteers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("member_id", sa.Integer(), nullable=True),
        sa.Column("ministry", sa.String(100), nullable=True),
        sa.Column("role", sa.String(100), nullable=True),
        sa.Column("status", sa.String(20), default="active"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
