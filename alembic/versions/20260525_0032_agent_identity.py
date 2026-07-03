"""Create agent identity tables — canonical person model

Creates: agents, agent_auth, agent_contact, agent_roles,
agent_activities, agent_families, agent_journey, agent_permissions
"""
import sqlalchemy as sa

from alembic import op

revision = "20260525_0032"
down_revision = "20260525_0031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # agents
    op.create_table(
        "agents",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("code", sa.String(20), unique=True, nullable=False),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("email", sa.String(255), unique=True, nullable=True),
        sa.Column("phone", sa.String(50), unique=True, nullable=True),
        sa.Column("avatar_url", sa.String(500), nullable=True),
        sa.Column("spiritual_stage", sa.String(30), nullable=False, server_default="visitor"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("is_active", sa.Boolean, server_default=sa.true()),
        sa.Column("created_by", sa.Integer, sa.ForeignKey("agents.id"), nullable=True),
        sa.Column("updated_by", sa.Integer, sa.ForeignKey("agents.id"), nullable=True),
    )
    op.create_index("ix_agents_id", "agents", ["id"])
    op.create_index("ix_agents_code", "agents", ["code"])
    op.create_index("ix_agents_email", "agents", ["email"], unique=True, postgresql_where=sa.text("email IS NOT NULL"))
    op.create_index("ix_agents_phone", "agents", ["phone"], unique=True, postgresql_where=sa.text("phone IS NOT NULL"))
    op.create_index("ix_agents_spiritual_stage", "agents", ["spiritual_stage"])
    op.create_index("ix_agents_created_at", "agents", ["created_at"])
    op.create_index("ix_agents_is_active", "agents", ["is_active"])

    # agent_auth
    op.create_table(
        "agent_auth",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("agent_id", sa.Integer, sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("username", sa.String(50), unique=True, nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=True),
        sa.Column("provider", sa.String(30), server_default="local"),
        sa.Column("provider_id", sa.String(255), nullable=True),
        sa.Column("is_email_verified", sa.Boolean, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("last_login_at", sa.DateTime, nullable=True),
        sa.UniqueConstraint("agent_id", "provider", name="uq_agent_provider"),
    )
    op.create_index("ix_agent_auth_id", "agent_auth", ["id"])
    op.create_index("ix_agent_auth_agent_id", "agent_auth", ["agent_id"])
    op.create_index("ix_agent_auth_username", "agent_auth", ["username"])

    # agent_contact
    op.create_table(
        "agent_contact",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("agent_id", sa.Integer, sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("value", sa.String(500), nullable=False),
        sa.Column("is_primary", sa.Boolean, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("created_by", sa.Integer, sa.ForeignKey("agents.id"), nullable=True),
    )
    op.create_index("ix_agent_contact_id", "agent_contact", ["id"])
    op.create_index("ix_agent_contact_agent_id", "agent_contact", ["agent_id"])
    op.create_index("ix_agent_contact_type", "agent_contact", ["type"])

    # agent_roles
    op.create_table(
        "agent_roles",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("agent_id", sa.Integer, sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role_type", sa.String(30), nullable=False),
        sa.Column("role_value", sa.String(50), nullable=False),
        sa.Column("context_id", sa.Integer, nullable=True),
        sa.Column("context_type", sa.String(30), nullable=True),
        sa.Column("started_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("ended_at", sa.DateTime, nullable=True),
        sa.Column("is_primary", sa.Boolean, server_default=sa.false()),
        sa.Column("created_by", sa.Integer, sa.ForeignKey("agents.id"), nullable=True),
    )
    op.create_index("ix_agent_roles_id", "agent_roles", ["id"])
    op.create_index("ix_agent_roles_agent_id", "agent_roles", ["agent_id"])
    op.create_index("ix_agent_roles_lookup", "agent_roles", ["agent_id", "role_type", "role_value"])

    # agent_activities
    op.create_table(
        "agent_activities",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("agent_id", sa.Integer, sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("activity_type", sa.String(40), nullable=False),
        sa.Column("source_type", sa.String(30), nullable=False),
        sa.Column("source_id", sa.Integer, nullable=True),
        sa.Column("status", sa.String(30), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("occurred_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_agent_activities_id", "agent_activities", ["id"])
    op.create_index("ix_agent_activities_agent_id", "agent_activities", ["agent_id"])
    op.create_index("ix_agent_activities_lookup", "agent_activities", ["agent_id", "activity_type", "occurred_at"])
    op.create_index("ix_agent_activities_source", "agent_activities", ["source_type", "source_id"])

    # agent_families
    op.create_table(
        "agent_families",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("agent_id", sa.Integer, sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("related_agent_id", sa.Integer, sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("relationship", sa.String(30), nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint("agent_id", "related_agent_id", "relationship", name="uq_family_relationship"),
    )
    op.create_index("ix_agent_families_id", "agent_families", ["id"])
    op.create_index("ix_agent_families_agent_id", "agent_families", ["agent_id"])
    op.create_index("ix_agent_families_related_id", "agent_families", ["related_agent_id"])

    # agent_journey
    op.create_table(
        "agent_journey",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("agent_id", sa.Integer, sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("from_stage", sa.String(30), nullable=True),
        sa.Column("to_stage", sa.String(30), nullable=False),
        sa.Column("reason", sa.String(100), nullable=True),
        sa.Column("triggered_by", sa.String(30), nullable=True),
        sa.Column("triggered_by_id", sa.Integer, nullable=True),
        sa.Column("metadata", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_agent_journey_id", "agent_journey", ["id"])
    op.create_index("ix_agent_journey_agent_id", "agent_journey", ["agent_id"])
    op.create_index("ix_agent_journey_agent", "agent_journey", ["agent_id", "created_at"])

    # agent_permissions
    op.create_table(
        "agent_permissions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("agent_id", sa.Integer, sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("permission", sa.String(50), nullable=False),
        sa.Column("granted_via", sa.String(50), nullable=True),
        sa.Column("granted_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime, nullable=True),
        sa.UniqueConstraint("agent_id", "permission", name="uq_agent_permission"),
    )
    op.create_index("ix_agent_permissions_id", "agent_permissions", ["id"])
    op.create_index("ix_agent_permissions_agent_id", "agent_permissions", ["agent_id"])
    op.create_index("ix_agent_permissions_permission", "agent_permissions", ["permission"])


def downgrade() -> None:
    op.drop_table("agent_permissions")
    op.drop_table("agent_journey")
    op.drop_table("agent_families")
    op.drop_table("agent_activities")
    op.drop_table("agent_roles")
    op.drop_table("agent_contact")
    op.drop_table("agent_auth")
    op.drop_table("agents")
