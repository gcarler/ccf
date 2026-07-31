"""chat: add attachments and mentions to chat_messages

Revision ID: chat_attach_0004
Revises: 20260730_0003
Create Date: 2026-07-30
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "chat_attach_0004"
down_revision = "20260730_0003"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("chat_messages", sa.Column("attachment_url", sa.Text(), nullable=True))
    op.add_column("chat_messages", sa.Column("attachment_type", sa.String(50), nullable=True))
    op.add_column("chat_messages", sa.Column("attachment_name", sa.String(255), nullable=True))
    op.add_column("chat_messages", sa.Column("attachment_size", sa.Integer(), nullable=True))
    op.add_column("chat_messages", sa.Column("reply_to_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("chat_messages", sa.Column("mentions_raw", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("chat_messages", "mentions_raw")
    op.drop_column("chat_messages", "reply_to_id")
    op.drop_column("chat_messages", "attachment_size")
    op.drop_column("chat_messages", "attachment_name")
    op.drop_column("chat_messages", "attachment_type")
    op.drop_column("chat_messages", "attachment_url")
