"""Projects Super-PRO: Project Baselines for Planned vs Actual Gantt Tracking."""

from __future__ import annotations

from typing import Sequence, Union
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
from alembic import op

revision: str = "20260924_0004_projects_super_pro_baselines"
down_revision: Union[str, None] = "20260924_0003_projects_super_pro_risks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "project_baselines",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=100), server_default="Línea Base Inicial", nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("snapshot_data", sa.JSON(), nullable=False),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("personas.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_project_baselines_project_id", "project_baselines", ["project_id"])
    op.create_index("ix_project_baselines_created_by", "project_baselines", ["created_by"])
    op.create_index("ix_project_baselines_created_at", "project_baselines", ["created_at"])
    op.create_index("ix_project_baselines_deleted_at", "project_baselines", ["deleted_at"])


def downgrade() -> None:
    op.drop_table("project_baselines")
