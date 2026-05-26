"""0035_agent_tables_complete

Revision ID: 20260525_0035
Revises: 20260525_0033
Create Date: 2026-05-26

Crea TODAS las tablas del sistema de agentes que faltaban:
- agents, agent_auth, agent_contact, agent_roles, agent_activities
- agent_families, agent_journey, agent_permissions
- agent_tasks, agent_insights

Además corrige agent_journey.journey_data (era "metadata", ahora JSON).
Seed: crea agente "Optimus" como agente IA del sistema.
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers
revision: str = "20260525_0035"
down_revision: Union[str, None] = "20260525_0033"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    # ── agents ──
    op.create_table(
        "agents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(20), unique=True, nullable=False),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("email", sa.String(255), unique=True, nullable=True),
        sa.Column("phone", sa.String(50), unique=True, nullable=True),
        sa.Column("avatar_url", sa.String(500), nullable=True),
        sa.Column(
            "spiritual_stage", sa.String(30),
            nullable=False, server_default="visitor",
        ),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column(
            "is_active", sa.Boolean(),
            nullable=False, server_default="true",
        ),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("agents.id"), nullable=True),
        sa.Column("updated_by", sa.Integer(), sa.ForeignKey("agents.id"), nullable=True),
        sa.Index("ix_agents_code", "code"),
        sa.Index("ix_agents_email", "email"),
        sa.Index("ix_agents_phone", "phone"),
        sa.Index("ix_agents_stage", "spiritual_stage"),
        sa.Index("ix_agents_created", "created_at"),
        sa.Index("ix_agents_active", "is_active"),
    )

    # ── agent_auth ──
    op.create_table(
        "agent_auth",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("agent_id", sa.Integer(), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("username", sa.String(50), unique=True, nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=True),
        sa.Column("provider", sa.String(30), server_default="local"),
        sa.Column("provider_id", sa.String(255), nullable=True),
        sa.Column("is_email_verified", sa.Boolean(), server_default="false"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("last_login_at", sa.DateTime(), nullable=True),
        sa.Index("ix_agent_auth_agent", "agent_id"),
        sa.Index("ix_agent_auth_username", "username"),
        sa.UniqueConstraint("agent_id", "provider", name="uq_agent_provider"),
    )

    # ── agent_contact ──
    op.create_table(
        "agent_contact",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("agent_id", sa.Integer(), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("value", sa.String(500), nullable=False),
        sa.Column("is_primary", sa.Boolean(), server_default="false"),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("agents.id"), nullable=True),
        sa.Index("ix_agent_contact_agent", "agent_id"),
        sa.Index("ix_agent_contact_type", "type"),
    )

    # ── agent_roles ──
    op.create_table(
        "agent_roles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("agent_id", sa.Integer(), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role_type", sa.String(30), nullable=False),
        sa.Column("role_value", sa.String(50), nullable=False),
        sa.Column("context_id", sa.Integer(), nullable=True),
        sa.Column("context_type", sa.String(30), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("is_primary", sa.Boolean(), server_default="false"),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("agents.id"), nullable=True),
        sa.Index("ix_agent_roles_agent", "agent_id"),
        sa.Index("ix_agent_roles_type", "role_type"),
        sa.Index("ix_agent_roles_value", "role_value"),
        sa.Index("ix_agent_roles_lookup", "agent_id", "role_type", "role_value"),
    )

    # ── agent_activities ──
    op.create_table(
        "agent_activities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("agent_id", sa.Integer(), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("activity_type", sa.String(40), nullable=False),
        sa.Column("source_type", sa.String(30), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(30), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Index("ix_agent_activities_agent", "agent_id"),
        sa.Index("ix_agent_activities_type", "activity_type"),
        sa.Index("ix_agent_activities_source_type", "source_type"),
        sa.Index("ix_agent_activities_occurred", "occurred_at"),
        sa.Index("ix_agent_activities_lookup", "agent_id", "activity_type", "occurred_at"),
        sa.Index("ix_agent_activities_source", "source_type", "source_id"),
    )

    # ── agent_families ──
    op.create_table(
        "agent_families",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("agent_id", sa.Integer(), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("related_agent_id", sa.Integer(), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("relationship", sa.String(30), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Index("ix_agent_families_agent", "agent_id"),
        sa.Index("ix_agent_families_related", "related_agent_id"),
        sa.UniqueConstraint("agent_id", "related_agent_id", "relationship", name="uq_family_relationship"),
    )

    # ── agent_journey ──
    op.create_table(
        "agent_journey",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("agent_id", sa.Integer(), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("from_stage", sa.String(30), nullable=True),
        sa.Column("to_stage", sa.String(30), nullable=False),
        sa.Column("reason", sa.String(100), nullable=True),
        sa.Column("triggered_by", sa.String(30), nullable=True),
        sa.Column("triggered_by_id", sa.Integer(), nullable=True),
        sa.Column("journey_data", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Index("ix_agent_journey_agent", "agent_id", "created_at"),
    )

    # ── agent_permissions ──
    op.create_table(
        "agent_permissions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("agent_id", sa.Integer(), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("permission", sa.String(50), nullable=False),
        sa.Column("granted_via", sa.String(50), nullable=True),
        sa.Column("granted_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Index("ix_agent_permissions_agent", "agent_id"),
        sa.Index("ix_agent_permissions_perm", "permission"),
        sa.UniqueConstraint("agent_id", "permission", name="uq_agent_permission"),
    )

    # ── agent_tasks ──
    op.create_table(
        "agent_tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("priority", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("source", sa.String(50), nullable=True),
        sa.Column("assigned_to", sa.String(100), nullable=True),
        sa.Column("agent_type", sa.String(50), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Index("ix_agent_tasks_id", "id"),
        sa.Index("ix_agent_tasks_priority", "priority"),
        sa.Index("ix_agent_tasks_status", "status", "priority"),
        sa.Index("ix_agent_tasks_assigned", "assigned_to"),
        sa.Index("ix_agent_tasks_created", "created_at"),
    )

    # ── agent_insights ──
    op.create_table(
        "agent_insights",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("insight_type", sa.String(50), nullable=False, server_default="observation"),
        sa.Column("confidence", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("source_agent", sa.String(100), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("acknowledged", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("acknowledged_at", sa.DateTime(), nullable=True),
        sa.Column("acknowledged_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Index("ix_agent_insights_id", "id"),
        sa.Index("ix_agent_insights_type", "insight_type"),
        sa.Index("ix_agent_insights_ack", "acknowledged"),
        sa.Index("ix_agent_insights_created", "created_at"),
    )

    # ── Seed: agente Optimus ──
    _seed_optimus_agent(bind)


def _seed_optimus_agent(bind):
    """Crea el agente IA Optimus con rol ai_agent."""
    sa.func.now()
    op.execute(
        "INSERT INTO agents (code, first_name, last_name, email, "
        "spiritual_stage, is_active, created_at, updated_at) "
        "VALUES ('CCF-AGENT-00001', 'Optimus', 'IA', "
        "'optimus@ccf.internal', 'servant', true, NOW(), NOW())"
    )
    op.execute(
        "INSERT INTO agent_roles (agent_id, role_type, role_value, "
        "started_at, is_primary) "
        "VALUES (1, 'system', 'ai_agent', NOW(), true)"
    )
    op.execute(
        "INSERT INTO agent_permissions (agent_id, permission, granted_via, "
        "granted_at) "
        "VALUES (1, 'system:config', 'system', NOW()), "
        "(1, 'crm:manage', 'system', NOW()), "
        "(1, 'academy:manage', 'system', NOW()), "
        "(1, 'projects:manage', 'system', NOW()), "
        "(1, 'evangelism:manage', 'system', NOW())"
    )


def downgrade() -> None:
    op.drop_table("agent_insights")
    op.drop_table("agent_tasks")
    op.drop_table("agent_permissions")
    op.drop_table("agent_journey")
    op.drop_table("agent_families")
    op.drop_table("agent_activities")
    op.drop_table("agent_roles")
    op.drop_table("agent_contact")
    op.drop_table("agent_auth")
    op.drop_table("agents")
