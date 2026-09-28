"""academy collaborative study groups and memberships

Revision ID: 20260928_0018_academy_study_groups
Revises: 20260928_0017_academy_achievements_leaderboard
Create Date: 2026-09-28 20:48:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision = '20260928_0018_academy_study_groups'
down_revision = '20260928_0017_academy_achievements_leaderboard'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Create academy_study_groups table
    op.create_table(
        'academy_study_groups',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('offering_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('academy_period_offerings.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('max_members', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('personas.id'), nullable=False, index=True),
        sa.Column('sede_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('sedes.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True, index=True),
    )

    # 2. Create academy_study_group_members table
    op.create_table(
        'academy_study_group_members',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('group_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('academy_study_groups.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('student_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('personas.id'), nullable=False, index=True),
        sa.Column('role', sa.String(length=50), nullable=False, server_default='member'),
        sa.Column('joined_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('sede_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('sedes.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True, index=True),
        sa.UniqueConstraint('group_id', 'student_id', name='uq_study_group_student'),
    )


def downgrade():
    op.drop_table('academy_study_group_members')
    op.drop_table('academy_study_groups')
