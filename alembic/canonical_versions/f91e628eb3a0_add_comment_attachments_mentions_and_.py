"""add_comment_attachments_mentions_and_agenda_comments

Revision ID: f91e628eb3a0
Revises: 20260730_0004_add_cms_popups
Create Date: 2026-07-30 17:51:09.866196

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f91e628eb3a0"
down_revision: Union[str, None] = "20260730_0004_add_cms_popups"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── project_comments enhancements ──────────────────────────────
    op.add_column("project_comments", sa.Column("attachments", sa.JSON(), nullable=False, server_default="[]"))
    op.add_column("project_comments", sa.Column("mentions", sa.JSON(), nullable=False, server_default="[]"))

    # ── agenda_event_comments table ────────────────────────────────
    op.create_table(
        "agenda_event_comments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("attachments", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("mentions", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["agenda_eventos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["author_id"], ["personas.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_agenda_event_comments_event_id"), "agenda_event_comments", ["event_id"])
    op.create_index(op.f("ix_agenda_event_comments_author_id"), "agenda_event_comments", ["author_id"])
    op.create_index(op.f("ix_agenda_event_comments_created_at"), "agenda_event_comments", ["created_at"])


def downgrade() -> None:
    op.drop_index(op.f("ix_agenda_event_comments_created_at"), table_name="agenda_event_comments")
    op.drop_index(op.f("ix_agenda_event_comments_author_id"), table_name="agenda_event_comments")
    op.drop_index(op.f("ix_agenda_event_comments_event_id"), table_name="agenda_event_comments")
    op.drop_table("agenda_event_comments")

    op.drop_column("project_comments", "mentions")
    op.drop_column("project_comments", "attachments")
