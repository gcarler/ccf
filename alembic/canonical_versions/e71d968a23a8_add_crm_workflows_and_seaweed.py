"""add_crm_workflows_and_seaweed

Revision ID: e71d968a23a8
Revises: 20260706_0003_cms_sections_phase2
Create Date: 2026-07-10 04:55:14.309619

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'e71d968a23a8'
down_revision: Union[str, None] = '20260706_0003_cms_sections_phase2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Add new columns to crm_automations
    automation_cols = {
        column["name"] for column in inspector.get_columns("crm_automations")
    } if inspector.has_table("crm_automations") else set()
    if "delay_minutes" not in automation_cols:
        op.add_column('crm_automations', sa.Column('delay_minutes', sa.Integer(), nullable=False, server_default='0'))
    if "next_automation_id" not in automation_cols:
        op.add_column('crm_automations', sa.Column('next_automation_id', sa.UUID(), nullable=True))
        if bind.dialect.name != "sqlite":
            op.create_foreign_key(None, 'crm_automations', 'crm_automations', ['next_automation_id'], ['id'])

    # Create crm_pending_actions table
    if not inspector.has_table("crm_pending_actions"):
        op.create_table(
            'crm_pending_actions',
            sa.Column('id', sa.UUID(), nullable=False),
            sa.Column('automation_id', sa.UUID(), nullable=False),
            sa.Column('target_persona_id', sa.UUID(), nullable=False),
            sa.Column('execute_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('status', sa.String(length=30), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(['automation_id'], ['crm_automations.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_crm_pending_actions_execute_at'), 'crm_pending_actions', ['execute_at'], unique=False)
        op.create_index(op.f('ix_crm_pending_actions_status'), 'crm_pending_actions', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_crm_pending_actions_status'), table_name='crm_pending_actions')
    op.drop_index(op.f('ix_crm_pending_actions_execute_at'), table_name='crm_pending_actions')
    op.drop_table('crm_pending_actions')

    op.drop_constraint(None, 'crm_automations', type_='foreignkey')
    op.drop_column('crm_automations', 'next_automation_id')
    op.drop_column('crm_automations', 'delay_minutes')
