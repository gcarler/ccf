"""Add PMI project charter, stakeholder register, and closure records."""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261018_0001_projects_pmi_lifecycle"
down_revision: Union[str, None] = "20261011_0002_notification_deliveries"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "project_lifecycles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sponsor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("business_case", sa.Text(), nullable=True),
        sa.Column("strategic_justification", sa.Text(), nullable=True),
        sa.Column("measurable_objectives", sa.JSON(), nullable=False),
        sa.Column("key_assumptions", sa.JSON(), nullable=False),
        sa.Column("key_constraints", sa.JSON(), nullable=False),
        sa.Column("high_level_risks", sa.JSON(), nullable=False),
        sa.Column("preliminary_budget", sa.Float(), nullable=True),
        sa.Column("charter_status", sa.String(length=20), nullable=False),
        sa.Column("authorized_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("authorized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closure_status", sa.String(length=20), nullable=False),
        sa.Column("deliverables_accepted_verified", sa.Boolean(), nullable=False),
        sa.Column("financial_reconciliation_completed", sa.Boolean(), nullable=False),
        sa.Column("final_bac", sa.Float(), nullable=True),
        sa.Column("final_ac", sa.Float(), nullable=True),
        sa.Column("final_variance", sa.Float(), nullable=True),
        sa.Column("operational_handover_to", sa.String(length=255), nullable=True),
        sa.Column("lessons_learned", sa.JSON(), nullable=False),
        sa.Column("closed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("wiki_synced", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sponsor_id"], ["personas.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["authorized_by"], ["personas.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["closed_by"], ["personas.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", name="uq_project_lifecycles_project"),
    )
    op.create_index("ix_project_lifecycles_project_id", "project_lifecycles", ["project_id"], unique=True)

    op.create_table(
        "project_stakeholders",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("persona_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("display_name", sa.String(length=200), nullable=True),
        sa.Column("role_title", sa.String(length=200), nullable=True),
        sa.Column("organization_or_ministry", sa.String(length=200), nullable=True),
        sa.Column("power_level", sa.Integer(), nullable=False),
        sa.Column("interest_level", sa.Integer(), nullable=False),
        sa.Column("quadrant", sa.String(length=30), nullable=False),
        sa.Column("engagement_level", sa.String(length=20), nullable=False),
        sa.Column("management_strategy", sa.Text(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["persona_id"], ["personas.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_project_stakeholders_project_id", "project_stakeholders", ["project_id"])
    op.create_index("ix_project_stakeholders_persona_id", "project_stakeholders", ["persona_id"])
    op.create_index("ix_project_stakeholders_deleted_at", "project_stakeholders", ["deleted_at"])


def downgrade() -> None:
    op.drop_index("ix_project_stakeholders_deleted_at", table_name="project_stakeholders")
    op.drop_index("ix_project_stakeholders_persona_id", table_name="project_stakeholders")
    op.drop_index("ix_project_stakeholders_project_id", table_name="project_stakeholders")
    op.drop_table("project_stakeholders")
    op.drop_index("ix_project_lifecycles_project_id", table_name="project_lifecycles")
    op.drop_table("project_lifecycles")
