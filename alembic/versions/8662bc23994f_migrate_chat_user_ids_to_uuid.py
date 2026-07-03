"""migrate_chat_user_ids_to_uuid

Revision ID: 8662bc23994f
Revises: 20260611_season_id_sesiones
Create Date: 2026-06-11 00:40:13.455847

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '8662bc23994f'
down_revision: Union[str, None] = '20260611_season_id_sesiones'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop foreign keys first
    op.drop_constraint('chat_messages_sender_id_fkey', 'chat_messages', type_='foreignkey')
    op.drop_constraint('conversations_last_sender_id_fkey', 'conversations', type_='foreignkey')
    op.drop_constraint('conversation_participants_user_id_fkey', 'conversation_participants', type_='foreignkey')
    
    # Drop unique constraint
    op.drop_constraint('uq_conversation_user', 'conversation_participants', type_='unique')
    
    # Alter columns to UUID
    op.execute('ALTER TABLE chat_messages ALTER COLUMN sender_id TYPE uuid USING NULL::uuid')
    op.execute('ALTER TABLE conversations ALTER COLUMN last_sender_id TYPE uuid USING NULL::uuid')
    op.execute('ALTER TABLE conversation_participants ALTER COLUMN user_id TYPE uuid USING NULL::uuid')
    
    # Add foreign keys back pointing to auth_users.id
    op.create_foreign_key('chat_messages_sender_id_fkey', 'chat_messages', 'auth_users', ['sender_id'], ['id'])
    op.create_foreign_key('conversations_last_sender_id_fkey', 'conversations', 'auth_users', ['last_sender_id'], ['id'])
    op.create_foreign_key('conversation_participants_user_id_fkey', 'conversation_participants', 'auth_users', ['user_id'], ['id'], ondelete='CASCADE')
    
    # Recreate unique constraint
    op.create_unique_constraint('uq_conversation_user', 'conversation_participants', ['conversation_id', 'user_id'])


def downgrade() -> None:
    # Drop foreign keys
    op.drop_constraint('chat_messages_sender_id_fkey', 'chat_messages', type_='foreignkey')
    op.drop_constraint('conversations_last_sender_id_fkey', 'conversations', type_='foreignkey')
    op.drop_constraint('conversation_participants_user_id_fkey', 'conversation_participants', type_='foreignkey')
    
    # Drop unique constraint
    op.drop_constraint('uq_conversation_user', 'conversation_participants', type_='unique')
    
    # Alter columns to Integer
    op.execute('ALTER TABLE chat_messages ALTER COLUMN sender_id TYPE integer USING NULL::integer')
    op.execute('ALTER TABLE conversations ALTER COLUMN last_sender_id TYPE integer USING NULL::integer')
    op.execute('ALTER TABLE conversation_participants ALTER COLUMN user_id TYPE integer USING NULL::integer')
    
    # Add foreign keys back pointing to _compat_users.id
    op.create_foreign_key('chat_messages_sender_id_fkey', 'chat_messages', '_compat_users', ['sender_id'], ['id'])
    op.create_foreign_key('conversations_last_sender_id_fkey', 'conversations', '_compat_users', ['last_sender_id'], ['id'])
    op.create_foreign_key('conversation_participants_user_id_fkey', 'conversation_participants', '_compat_users', ['user_id'], ['id'], ondelete='CASCADE')
    
    # Recreate unique constraint
    op.create_unique_constraint('uq_conversation_user', 'conversation_participants', ['conversation_id', 'user_id'])
