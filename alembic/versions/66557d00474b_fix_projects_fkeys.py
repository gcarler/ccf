"""fix_projects_fkeys

Revision ID: 66557d00474b
Revises: 8662bc23994f
Create Date: 2026-06-11 01:45:18.539368

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '66557d00474b'
down_revision: Union[str, None] = '8662bc23994f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Drop old foreign key constraints pointing to legacy tables (idempotent)
    op.execute("ALTER TABLE project_documents DROP CONSTRAINT IF EXISTS project_documents_project_id_fkey")
    op.execute("ALTER TABLE project_attachments DROP CONSTRAINT IF EXISTS project_attachments_task_id_fkey")
    op.execute("ALTER TABLE task_supplies DROP CONSTRAINT IF EXISTS task_supplies_task_id_fkey")
    op.execute("ALTER TABLE project_comments DROP CONSTRAINT IF EXISTS project_comments_project_id_fkey")
    op.execute("ALTER TABLE project_comments DROP CONSTRAINT IF EXISTS project_comments_task_id_fkey")

    # 2. Drop legacy inbox state constraints and column (idempotent)
    op.execute("ALTER TABLE project_inbox_state DROP CONSTRAINT IF EXISTS uq_user_project_item")
    op.execute("ALTER TABLE project_inbox_state DROP CONSTRAINT IF EXISTS project_inbox_state_user_id_fkey")
    op.execute("ALTER TABLE project_inbox_state DROP COLUMN IF EXISTS user_id")

    # 3. Clean up any orphaned records before enforcing foreign key constraints
    op.execute("DELETE FROM project_attachments WHERE task_id NOT IN (SELECT id FROM project_tasks)")
    op.execute("DELETE FROM project_comments WHERE project_id NOT IN (SELECT id FROM projects)")
    op.execute("DELETE FROM project_comments WHERE task_id IS NOT NULL AND task_id NOT IN (SELECT id FROM project_tasks)")
    op.execute("DELETE FROM project_documents WHERE project_id NOT IN (SELECT id FROM projects)")
    op.execute("DELETE FROM task_supplies WHERE task_id NOT IN (SELECT id FROM project_tasks)")

    # 4. Add deleted_at columns for soft deletion support (idempotent)
    op.execute("ALTER TABLE project_comments ADD COLUMN IF NOT EXISTS deleted_at timestamp with time zone")
    op.execute("ALTER TABLE project_attachments ADD COLUMN IF NOT EXISTS deleted_at timestamp with time zone")
    op.execute("ALTER TABLE task_supplies ADD COLUMN IF NOT EXISTS deleted_at timestamp with time zone")
    op.execute("ALTER TABLE project_milestones ADD COLUMN IF NOT EXISTS deleted_at timestamp with time zone")
    op.execute("ALTER TABLE project_phases ADD COLUMN IF NOT EXISTS deleted_at timestamp with time zone")

    # 5. Create new foreign keys pointing to active tables
    op.execute("ALTER TABLE project_documents DROP CONSTRAINT IF EXISTS project_documents_project_id_fkey")
    op.create_foreign_key('project_documents_project_id_fkey', 'project_documents', 'projects', ['project_id'], ['id'], ondelete='CASCADE')
    
    op.execute("ALTER TABLE project_attachments DROP CONSTRAINT IF EXISTS project_attachments_task_id_fkey")
    op.create_foreign_key('project_attachments_task_id_fkey', 'project_attachments', 'project_tasks', ['task_id'], ['id'], ondelete='CASCADE')
    
    op.execute("ALTER TABLE task_supplies DROP CONSTRAINT IF EXISTS task_supplies_task_id_fkey")
    op.create_foreign_key('task_supplies_task_id_fkey', 'task_supplies', 'project_tasks', ['task_id'], ['id'], ondelete='CASCADE')
    
    op.execute("ALTER TABLE project_comments DROP CONSTRAINT IF EXISTS project_comments_project_id_fkey")
    op.create_foreign_key('project_comments_project_id_fkey', 'project_comments', 'projects', ['project_id'], ['id'], ondelete='CASCADE')
    
    op.execute("ALTER TABLE project_comments DROP CONSTRAINT IF EXISTS project_comments_task_id_fkey")
    op.create_foreign_key('project_comments_task_id_fkey', 'project_comments', 'project_tasks', ['task_id'], ['id'], ondelete='SET NULL')

    # 6. Create new unique constraint on project_inbox_state
    op.execute("ALTER TABLE project_inbox_state DROP CONSTRAINT IF EXISTS uq_persona_project_item")
    op.create_unique_constraint('uq_persona_project_item', 'project_inbox_state', ['persona_id', 'item_id'])


def downgrade() -> None:
    # 1. Drop new unique constraint and foreign key constraints pointing to active tables
    op.execute("ALTER TABLE project_inbox_state DROP CONSTRAINT IF EXISTS uq_persona_project_item")
    op.execute("ALTER TABLE project_documents DROP CONSTRAINT IF EXISTS project_documents_project_id_fkey")
    op.execute("ALTER TABLE project_attachments DROP CONSTRAINT IF EXISTS project_attachments_task_id_fkey")
    op.execute("ALTER TABLE task_supplies DROP CONSTRAINT IF EXISTS task_supplies_task_id_fkey")
    op.execute("ALTER TABLE project_comments DROP CONSTRAINT IF EXISTS project_comments_project_id_fkey")
    op.execute("ALTER TABLE project_comments DROP CONSTRAINT IF EXISTS project_comments_task_id_fkey")

    # 2. Drop deleted_at columns
    op.execute("ALTER TABLE project_comments DROP COLUMN IF EXISTS deleted_at")
    op.execute("ALTER TABLE project_attachments DROP COLUMN IF EXISTS deleted_at")
    op.execute("ALTER TABLE task_supplies DROP COLUMN IF EXISTS deleted_at")
    op.execute("ALTER TABLE project_milestones DROP COLUMN IF EXISTS deleted_at")
    op.execute("ALTER TABLE project_phases DROP COLUMN IF EXISTS deleted_at")

    # 3. Add user_id column back to project_inbox_state
    op.execute("ALTER TABLE project_inbox_state ADD COLUMN IF NOT EXISTS user_id integer")

    # 4. Recreate old foreign key constraints pointing to legacy tables
    op.execute("ALTER TABLE project_documents DROP CONSTRAINT IF EXISTS project_documents_project_id_fkey")
    op.create_foreign_key('project_documents_project_id_fkey', 'project_documents', '_legacy_projects', ['project_id'], ['id'])
    
    op.execute("ALTER TABLE project_attachments DROP CONSTRAINT IF EXISTS project_attachments_task_id_fkey")
    op.create_foreign_key('project_attachments_task_id_fkey', 'project_attachments', '_legacy_project_tasks', ['task_id'], ['id'])
    
    op.execute("ALTER TABLE task_supplies DROP CONSTRAINT IF EXISTS task_supplies_task_id_fkey")
    op.create_foreign_key('task_supplies_task_id_fkey', 'task_supplies', '_legacy_project_tasks', ['task_id'], ['id'])
    
    op.execute("ALTER TABLE project_comments DROP CONSTRAINT IF EXISTS project_comments_project_id_fkey")
    op.create_foreign_key('project_comments_project_id_fkey', 'project_comments', '_legacy_projects', ['project_id'], ['id'])
    
    op.execute("ALTER TABLE project_comments DROP CONSTRAINT IF EXISTS project_comments_task_id_fkey")
    op.create_foreign_key('project_comments_task_id_fkey', 'project_comments', '_legacy_project_tasks', ['task_id'], ['id'])
    
    op.execute("ALTER TABLE project_inbox_state DROP CONSTRAINT IF EXISTS project_inbox_state_user_id_fkey")
    op.create_foreign_key('project_inbox_state_user_id_fkey', 'project_inbox_state', '_legacy_users', ['user_id'], ['id'], ondelete='CASCADE')

    # 5. Recreate old unique constraint on project_inbox_state
    op.execute("ALTER TABLE project_inbox_state DROP CONSTRAINT IF EXISTS uq_user_project_item")
    op.create_unique_constraint('uq_user_project_item', 'project_inbox_state', ['user_id', 'item_id'])
