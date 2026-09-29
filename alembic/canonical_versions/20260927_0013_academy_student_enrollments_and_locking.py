"""academy student enrollments and locking

Revision ID: 20260927_0013
Revises: 20260927_0012
Create Date: 2026-09-27 13:50:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260927_0013_academy_student_enrollments_and_locking'
down_revision = '20260927_0012_academy_programs_credits_grading_schemes'
branch_labels = None
depends_on = None

def upgrade():
    # 1. Add quota_enrolled to academy_period_offerings
    op.add_column('academy_period_offerings', sa.Column('quota_enrolled', sa.Integer(), nullable=False, server_default='0'))

    # 2. Add is_locked to academy_student_subject_records
    op.add_column('academy_student_subject_records', sa.Column('is_locked', sa.Boolean(), nullable=False, server_default='false'))

    # 3. Create academy_student_enrollments table
    op.create_table(
        'academy_student_enrollments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('offering_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('persona_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('enrolled_by_persona_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('enrolled_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='active'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['enrolled_by_persona_id'], ['personas.id'], ),
        sa.ForeignKeyConstraint(['offering_id'], ['academy_period_offerings.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['persona_id'], ['personas.id'], ),
        sa.UniqueConstraint('offering_id', 'persona_id', name='uq_academy_student_enrollments_offering_persona')
    )

def downgrade():
    op.drop_table('academy_student_enrollments')
    op.drop_column('academy_student_subject_records', 'is_locked')
    op.drop_column('academy_period_offerings', 'quota_enrolled')
