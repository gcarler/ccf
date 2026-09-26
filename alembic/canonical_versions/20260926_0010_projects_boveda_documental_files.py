"""Projects: Boveda documental y visor universal embebido (project_files).

Revision ID: 20260926_0010_projects_boveda_documental_files
Revises: 20260926_0009_projects_favorites_and_pinned_comments
Create Date: 2026-09-26 18:20:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from alembic import op

revision: str = "20260926_0010_projects_boveda_documental_files"
down_revision: Union[str, None] = "20260926_0009_projects_favorites_and_pinned_comments"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "project_files",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(100), server_default="general", nullable=False),
        sa.Column("file_source", sa.String(50), server_default="local", nullable=False),
        sa.Column("file_url", sa.Text(), nullable=False),
        sa.Column("file_type", sa.String(100), nullable=True),
        sa.Column("file_size", sa.BigInteger(), nullable=True),
        sa.Column("drive_file_id", sa.String(255), nullable=True),
        sa.Column("task_id", UUID(as_uuid=True), sa.ForeignKey("project_tasks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("phase_id", UUID(as_uuid=True), sa.ForeignKey("project_phases.id", ondelete="SET NULL"), nullable=True),
        sa.Column("uploaded_by", UUID(as_uuid=True), sa.ForeignKey("personas.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("sede_id", UUID(as_uuid=True), sa.ForeignKey("sedes.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_project_files_project_id", "project_files", ["project_id"])
    op.create_index("ix_project_files_category", "project_files", ["category"])
    op.create_index("ix_project_files_file_source", "project_files", ["file_source"])
    op.create_index("ix_project_files_drive_file_id", "project_files", ["drive_file_id"])
    op.create_index("ix_project_files_task_id", "project_files", ["task_id"])
    op.create_index("ix_project_files_phase_id", "project_files", ["phase_id"])
    op.create_index("ix_project_files_uploaded_by", "project_files", ["uploaded_by"])
    op.create_index("ix_project_files_sede_id", "project_files", ["sede_id"])
    op.create_index("ix_project_files_deleted_at", "project_files", ["deleted_at"])


def downgrade() -> None:
    op.drop_index("ix_project_files_deleted_at", table_name="project_files")
    op.drop_index("ix_project_files_sede_id", table_name="project_files")
    op.drop_index("ix_project_files_uploaded_by", table_name="project_files")
    op.drop_index("ix_project_files_phase_id", table_name="project_files")
    op.drop_index("ix_project_files_task_id", table_name="project_files")
    op.drop_index("ix_project_files_drive_file_id", table_name="project_files")
    op.drop_index("ix_project_files_file_source", table_name="project_files")
    op.drop_index("ix_project_files_category", table_name="project_files")
    op.drop_index("ix_project_files_project_id", table_name="project_files")
    op.drop_table("project_files")
