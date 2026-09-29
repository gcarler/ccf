"""Projects Super-PRO: RAID Risk Matrix and Contingency Management."""

from __future__ import annotations

from typing import Sequence, Union
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from alembic import op

revision: str = "20260924_0003_projects_super_pro_risks"
down_revision: Union[str, None] = "20260924_0002_projects_super_pro_expenses"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "project_risks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("category", sa.String(length=50), server_default="tecnico", nullable=False),
        sa.Column("probability", sa.Integer(), server_default="3", nullable=False),
        sa.Column("impact", sa.Integer(), server_default="3", nullable=False),
        sa.Column("severity_score", sa.Integer(), server_default="9", nullable=False),
        sa.Column("mitigation_plan", sa.Text(), nullable=True),
        sa.Column("contingency_plan", sa.Text(), nullable=True),
        sa.Column("owner_id", UUID(as_uuid=True), sa.ForeignKey("personas.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_project_risks_project_id", "project_risks", ["project_id"])
    op.create_index("ix_project_risks_owner_id", "project_risks", ["owner_id"])
    op.create_index("ix_project_risks_status", "project_risks", ["status"])
    op.create_index("ix_project_risks_deleted_at", "project_risks", ["deleted_at"])


def downgrade() -> None:
    op.drop_table("project_risks")
