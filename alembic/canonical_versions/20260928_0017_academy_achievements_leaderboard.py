"""academy achievements, verifiable credentials and leaderboard

Revision ID: 20260928_0017_academy_achievements_leaderboard
Revises: 20260928_0016_academy_wellness_copilot
Create Date: 2026-09-28 16:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision = '20260928_0017_academy_achievements_leaderboard'
down_revision = '20260928_0016_academy_wellness_copilot'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Create academy_achievements table
    op.create_table(
        'academy_achievements',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('code', sa.String(length=100), nullable=False, unique=True, index=True),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('achievement_type', sa.String(length=50), nullable=False, server_default='milestone'),
        sa.Column('points', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('badge_icon', sa.String(length=100), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True, index=True),
        sa.Column('sede_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('sedes.id', ondelete='SET NULL'), nullable=True, index=True),
    )

    # 2. Create academy_student_achievements table
    op.create_table(
        'academy_student_achievements',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('student_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('personas.id'), nullable=False, index=True),
        sa.Column('achievement_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('academy_achievements.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('offering_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('academy_period_offerings.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('earned_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('evidence', sa.JSON().with_variant(postgresql.JSONB, 'postgresql'), nullable=True),
        sa.Column('credential_hash', sa.String(length=64), nullable=True, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True, index=True),
        sa.Column('sede_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('sedes.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.UniqueConstraint('student_id', 'achievement_id', 'offering_id', name='uq_student_achievement_offering'),
    )

    # 3. Create academy_leaderboard table
    op.create_table(
        'academy_leaderboard',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('offering_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('academy_period_offerings.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('sede_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('sedes.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('period', sa.String(length=50), nullable=False, server_default='2026-Q3', index=True),
        sa.Column('student_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('personas.id'), nullable=False, index=True),
        sa.Column('total_points', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('rank', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True, index=True),
        sa.UniqueConstraint('student_id', 'period', 'offering_id', name='uq_leaderboard_student_period_offering'),
    )


def downgrade():
    op.drop_table('academy_leaderboard')
    op.drop_table('academy_student_achievements')
    op.drop_table('academy_achievements')
