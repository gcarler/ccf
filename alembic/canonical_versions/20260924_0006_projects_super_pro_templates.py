"""Projects Super-PRO: Project Templates Catalog and Project Instantiation."""

from __future__ import annotations

from typing import Sequence, Union
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID
from alembic import op

revision: str = "20260924_0006_projects_super_pro_templates"
down_revision: Union[str, None] = "20260924_0005_projects_super_pro_time_tracking"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "project_templates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(100), server_default="general", nullable=False),
        sa.Column("default_budget", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("structure", JSONB, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("personas.id", ondelete="SET NULL"), nullable=True),
        sa.Column("is_public", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("sede_id", UUID(as_uuid=True), sa.ForeignKey("sedes.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_project_templates_category", "project_templates", ["category"])
    op.create_index("ix_project_templates_is_public", "project_templates", ["is_public"])
    op.create_index("ix_project_templates_sede_id", "project_templates", ["sede_id"])
    op.create_index("ix_project_templates_created_by", "project_templates", ["created_by"])
    op.create_index("ix_project_templates_deleted_at", "project_templates", ["deleted_at"])


def downgrade() -> None:
    op.drop_table("project_templates")
