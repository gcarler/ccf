"""add_deleted_at_to_project_tables

Revision ID: 20260710_0001
Revises: a89b968a23b0
Create Date: 2026-07-10

Adds missing deleted_at (soft-delete) columns to project-related tables
that already define them in backend/models_projects.py but did not
receive them in the 20260528_0052 redesign migration.
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "20260710_0001"
down_revision: Union[str, None] = "a89b968a23b0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _add_deleted_at(table: str) -> None:
    """Idempotently add a nullable deleted_at column to a table."""
    op.execute(
        sa.text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE")
    )


def upgrade() -> None:
    tables = [
        "project_milestones",
        "project_phases",
        "project_comments",
        "project_attachments",
        "task_supplies",
        "project_documents",
    ]
    for table in tables:
        _add_deleted_at(table)


def downgrade() -> None:
    tables = [
        "project_documents",
        "task_supplies",
        "project_attachments",
        "project_comments",
        "project_phases",
        "project_milestones",
    ]
    for table in tables:
        op.execute(sa.text(f"ALTER TABLE {table} DROP COLUMN IF EXISTS deleted_at"))
