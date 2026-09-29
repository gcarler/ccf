"""Projects Super-PRO: Project expenses and budget tracking."""

from __future__ import annotations

from typing import Sequence, Union
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from alembic import op

revision: str = "20260924_0002_projects_super_pro_expenses"
down_revision: Union[str, None] = "20260924_0001_projects_pro_kpis_and_gantt"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "project_expenses",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category", sa.String(length=50), server_default="general", nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("amount", sa.Float(), server_default="0", nullable=False),
        sa.Column("date", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("receipt_url", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="planned", nullable=False),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("personas.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_project_expenses_project_id", "project_expenses", ["project_id"])
    op.create_index("ix_project_expenses_created_by", "project_expenses", ["created_by"])
    op.create_index("ix_project_expenses_deleted_at", "project_expenses", ["deleted_at"])
    op.create_index("ix_project_expenses_status", "project_expenses", ["status"])


def downgrade() -> None:
    op.drop_table("project_expenses")
