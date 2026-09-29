"""academy knowledge graph and verifiable portfolio

Revision ID: 20260927_0015_academy_knowledge_graph
Revises: 20260927_0014_academy_socratic_defense_sessions
Create Date: 2026-09-27 23:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision = '20260927_0015_academy_knowledge_graph'
down_revision = '20260927_0014_academy_socratic_defense_sessions'
branch_labels = None
depends_on = None

def upgrade():
    # 1. Create academy_knowledge_nodes
    op.create_table(
        'academy_knowledge_nodes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('offering_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('academy_period_offerings.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('node_type', sa.String(length=50), nullable=False, server_default='concept'),
        sa.Column('weight', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sede_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('sedes.id', ondelete='SET NULL'), nullable=True, index=True),
    )

    # 2. Create academy_knowledge_edges
    op.create_table(
        'academy_knowledge_edges',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('source_node_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('academy_knowledge_nodes.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('target_node_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('academy_knowledge_nodes.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('edge_type', sa.String(length=50), nullable=False, server_default='requires'),
        sa.Column('weight', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sede_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('sedes.id', ondelete='SET NULL'), nullable=True, index=True),
    )

    # 3. Create academy_student_node_progress
    op.create_table(
        'academy_student_node_progress',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('student_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('personas.id'), nullable=False, index=True),
        sa.Column('node_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('academy_knowledge_nodes.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('mastery_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_evaluated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sede_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('sedes.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.UniqueConstraint('student_id', 'node_id', name='uq_student_node_progress'),
    )

    # 4. Create academy_portfolio_entries
    op.create_table(
        'academy_portfolio_entries',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('student_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('personas.id'), nullable=False, index=True),
        sa.Column('offering_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('academy_period_offerings.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('entry_type', sa.String(length=50), nullable=False, server_default='project'),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('evidence_url', sa.String(length=500), nullable=True),
        sa.Column('score', sa.Float(), nullable=True),
        sa.Column('issued_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('credential_hash', sa.String(length=64), nullable=True, index=True),
        sa.Column('is_public', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sede_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('sedes.id', ondelete='SET NULL'), nullable=True, index=True),
    )

def downgrade():
    op.drop_table('academy_portfolio_entries')
    op.drop_table('academy_student_node_progress')
    op.drop_table('academy_knowledge_edges')
    op.drop_table('academy_knowledge_nodes')
