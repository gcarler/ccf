"""academy wellness signals and copilot alerts

Revision ID: 20260928_0016_academy_wellness_copilot
Revises: 20260927_0015_academy_knowledge_graph
Create Date: 2026-09-28 02:45:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision = '20260928_0016_academy_wellness_copilot'
down_revision = '20260927_0015_academy_knowledge_graph'
branch_labels = None
depends_on = None

def upgrade():
    # 1. Create academy_wellness_signals table
    op.create_table(
        'academy_wellness_signals',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('student_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('personas.id'), nullable=False, index=True),
        sa.Column('offering_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('academy_period_offerings.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('signal_type', sa.String(length=50), nullable=False),  # 'engagement_drop', 'grade_risk', 'absence_pattern', 'stress_indicator'
        sa.Column('severity', sa.String(length=20), nullable=False, server_default='medium'),  # 'low', 'medium', 'high', 'critical'
        sa.Column('detected_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('details', sa.JSON().with_variant(postgresql.JSONB, 'postgresql'), nullable=True),
        sa.Column('is_resolved', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_by_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('personas.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sede_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('sedes.id', ondelete='SET NULL'), nullable=True, index=True),
    )

    # 2. Create academy_wellness_alerts table
    op.create_table(
        'academy_wellness_alerts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('signal_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('academy_wellness_signals.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('recipient_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('personas.id'), nullable=False, index=True),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('sent_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sede_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('sedes.id', ondelete='SET NULL'), nullable=True, index=True),
    )

def downgrade():
    op.drop_table('academy_wellness_alerts')
    op.drop_table('academy_wellness_signals')
