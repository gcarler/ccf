"""academy intelligent academic calendar events

Revision ID: 20260928_0020_academy_calendar_events
Revises: 20260928_0018_academy_study_groups
Create Date: 2026-09-28 21:28:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision = '20260928_0020_academy_calendar_events'
down_revision = '20260928_0018_academy_study_groups'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'academy_calendar_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('offering_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('academy_period_offerings.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('start_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('sede_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('sedes.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('personas.id'), nullable=False, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True, index=True),
    )


def downgrade():
    op.drop_table('academy_calendar_events')
