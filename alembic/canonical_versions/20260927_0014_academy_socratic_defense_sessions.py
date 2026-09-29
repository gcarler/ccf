"""academy socratic and defense sessions

Revision ID: 20260927_0014_academy_socratic_defense_sessions
Revises: 20260927_0013_academy_student_enrollments_and_locking
Create Date: 2026-09-27 21:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision = '20260927_0014_academy_socratic_defense_sessions'
down_revision = '20260927_0013_academy_student_enrollments_and_locking'
branch_labels = None
depends_on = None

def upgrade():
    # 1. Create academy_socratic_sessions table
    op.create_table(
        'academy_socratic_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('offering_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('academy_period_offerings.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('student_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('personas.id'), nullable=False, index=True),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('response', sa.Text(), nullable=False),
        sa.Column('session_type', sa.String(length=50), nullable=False, server_default='tutor'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sede_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('sedes.id', ondelete='SET NULL'), nullable=True, index=True),
    )

    # 2. Create academy_defense_sessions table
    op.create_table(
        'academy_defense_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('offering_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('academy_period_offerings.id', ondelete='CASCADE'), nullable=True, index=True),
        sa.Column('submission_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('academy_assignment_submissions.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('student_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('personas.id'), nullable=False, index=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('score', sa.Float(), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=False, server_default='300'),
        sa.Column('questions', sa.JSON().with_variant(postgresql.JSONB, 'postgresql'), nullable=True),
        sa.Column('answers', sa.JSON().with_variant(postgresql.JSONB, 'postgresql'), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sede_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('sedes.id', ondelete='SET NULL'), nullable=True, index=True),
    )

def downgrade():
    op.drop_table('academy_defense_sessions')
    op.drop_table('academy_socratic_sessions')
