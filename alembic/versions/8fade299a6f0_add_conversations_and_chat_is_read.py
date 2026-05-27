"""add_conversations_and_chat_is_read

Revision ID: 8fade299a6f0
Revises: 20260527_0043
Create Date: 2026-05-27 15:17:09.001909

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '8fade299a6f0'
down_revision: Union[str, None] = '20260527_0043'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # conversations table
    op.create_table('conversations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('last_message_content', sa.Text(), nullable=True),
        sa.Column('last_message_at', sa.DateTime(), nullable=True),
        sa.Column('last_sender_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['last_sender_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('conversations', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_conversations_created_at'), ['created_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_conversations_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_conversations_last_message_at'), ['last_message_at'], unique=False)

    # conversation_participants table
    op.create_table('conversation_participants',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('conversation_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('last_read_at', sa.DateTime(), nullable=True),
        sa.Column('is_archived', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('conversation_id', 'user_id', name='uq_conversation_user')
    )
    with op.batch_alter_table('conversation_participants', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_conversation_participants_conversation_id'), ['conversation_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_conversation_participants_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_conversation_participants_user_id'), ['user_id'], unique=False)

    # is_read column on chat_messages
    with op.batch_alter_table('chat_messages', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_read', sa.Boolean(), nullable=True))
        batch_op.create_index(batch_op.f('ix_chat_messages_is_read'), ['is_read'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('chat_messages', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_chat_messages_is_read'))
        batch_op.drop_column('is_read')

    with op.batch_alter_table('conversation_participants', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_conversation_participants_user_id'))
        batch_op.drop_index(batch_op.f('ix_conversation_participants_id'))
        batch_op.drop_index(batch_op.f('ix_conversation_participants_conversation_id'))

    op.drop_table('conversation_participants')

    with op.batch_alter_table('conversations', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_conversations_last_message_at'))
        batch_op.drop_index(batch_op.f('ix_conversations_id'))
        batch_op.drop_index(batch_op.f('ix_conversations_created_at'))

    op.drop_table('conversations')
