"""academy content recommendations and mentorship system

Revision ID: 20260928_0019_academy_recommendation_mentorship
Revises: 20260928_0020_academy_calendar_events
Create Date: 2026-09-28 23:22:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision = '20260928_0019_academy_recommendation_mentorship'
down_revision = '20260928_0020_academy_calendar_events'
branch_labels = None
depends_on = None


def upgrade():
    # 1. academy_content_recommendations
    op.create_table(
        'academy_content_recommendations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('student_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('personas.id'), nullable=False, index=True),
        sa.Column('recommendation_type', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('score', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('target_url', sa.String(length=500), nullable=True),
        sa.Column('viewed', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('viewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sede_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('sedes.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True, index=True),
    )

    # 2. academy_mentor_profiles
    op.create_table(
        'academy_mentor_profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('mentor_persona_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('personas.id'), nullable=False, unique=True, index=True),
        sa.Column('bio', sa.Text(), nullable=True),
        sa.Column('expertise', sa.JSON().with_variant(postgresql.JSONB, 'postgresql'), nullable=True),
        sa.Column('availability_summary', sa.String(length=255), nullable=True),
        sa.Column('max_mentees', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('sede_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('sedes.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True, index=True),
    )

    # 3. academy_mentorship_requests
    op.create_table(
        'academy_mentorship_requests',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('mentor_persona_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('personas.id'), nullable=False, index=True),
        sa.Column('mentee_persona_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('personas.id'), nullable=False, index=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('response_note', sa.Text(), nullable=True),
        sa.Column('requested_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('responded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sede_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('sedes.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True, index=True),
    )


def downgrade():
    op.drop_table('academy_mentorship_requests')
    op.drop_table('academy_mentor_profiles')
    op.drop_table('academy_content_recommendations')
