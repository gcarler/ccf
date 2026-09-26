"""Projects: User favorites and pinned comments.

Revision ID: 20260926_0009_projects_favorites_and_pinned_comments
Revises: 20260925_0008_projects_mga_crema_indicators
Create Date: 2026-09-26 18:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from alembic import op

revision: str = "20260926_0009_projects_favorites_and_pinned_comments"
down_revision: Union[str, None] = "20260925_0008_projects_mga_crema_indicators"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Crear tabla project_user_favorites
    op.create_table(
        "project_user_favorites",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("persona_id", UUID(as_uuid=True), sa.ForeignKey("personas.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entity_type", sa.String(50), server_default="task", nullable=False),
        sa.Column("entity_id", UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("persona_id", "entity_type", "entity_id", name="uq_project_user_favorites_entity"),
    )
    op.create_index("ix_project_user_favorites_project_id", "project_user_favorites", ["project_id"])
    op.create_index("ix_project_user_favorites_persona_id", "project_user_favorites", ["persona_id"])
    op.create_index("ix_project_user_favorites_project_persona", "project_user_favorites", ["project_id", "persona_id"])
    op.create_index("ix_project_user_favorites_entity", "project_user_favorites", ["entity_type", "entity_id"])

    # 2. Agregar columnas a project_comments
    op.add_column(
        "project_comments",
        sa.Column("is_pinned", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.add_column(
        "project_comments",
        sa.Column("pinned_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "project_comments",
        sa.Column("pinned_by", UUID(as_uuid=True), sa.ForeignKey("personas.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_project_comments_is_pinned", "project_comments", ["is_pinned"])
    op.create_index("ix_project_comments_pinned_by", "project_comments", ["pinned_by"])


def downgrade() -> None:
    op.drop_index("ix_project_comments_pinned_by", table_name="project_comments")
    op.drop_index("ix_project_comments_is_pinned", table_name="project_comments")
    op.drop_column("project_comments", "pinned_by")
    op.drop_column("project_comments", "pinned_at")
    op.drop_column("project_comments", "is_pinned")

    op.drop_index("ix_project_user_favorites_entity", table_name="project_user_favorites")
    op.drop_index("ix_project_user_favorites_project_persona", table_name="project_user_favorites")
    op.drop_index("ix_project_user_favorites_persona_id", table_name="project_user_favorites")
    op.drop_index("ix_project_user_favorites_project_id", table_name="project_user_favorites")
    op.drop_table("project_user_favorites")
