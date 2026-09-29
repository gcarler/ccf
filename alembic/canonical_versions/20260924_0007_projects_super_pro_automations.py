"""Projects Super-PRO: Project Automations and Trigger-Action Rules Engine."""

from __future__ import annotations

from typing import Sequence, Union
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID
from alembic import op

revision: str = "20260924_0007_projects_super_pro_automations"
down_revision: Union[str, None] = "20260924_0006_projects_super_pro_templates"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "project_automation_rules",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("trigger_event", sa.String(50), nullable=False),
        sa.Column("condition_data", JSONB, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("action_type", sa.String(50), nullable=False),
        sa.Column("action_data", JSONB, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("execution_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_triggered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("personas.id", ondelete="SET NULL"), nullable=True),
        sa.Column("sede_id", UUID(as_uuid=True), sa.ForeignKey("sedes.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_project_automation_rules_project_id", "project_automation_rules", ["project_id"])
    op.create_index("ix_project_automation_rules_trigger_event", "project_automation_rules", ["trigger_event"])
    op.create_index("ix_project_automation_rules_is_active", "project_automation_rules", ["is_active"])
    op.create_index("ix_project_automation_rules_sede_id", "project_automation_rules", ["sede_id"])
    op.create_index("ix_project_automation_rules_created_by", "project_automation_rules", ["created_by"])
    op.create_index("ix_project_automation_rules_deleted_at", "project_automation_rules", ["deleted_at"])


def downgrade() -> None:
    op.drop_table("project_automation_rules")
