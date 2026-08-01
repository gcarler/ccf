"""add_task_node_and_project_members

Revision ID: a9b3c4d5e6f7
Revises: 575eec15ec67
Create Date: 2026-08-01 09:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a9b3c4d5e6f7"
down_revision: Union[str, None] = "575eec15ec67"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("project_tasks", sa.Column("node", sa.String(length=50), nullable=True))
    op.create_index(op.f("ix_project_tasks_node"), "project_tasks", ["node"])

    op.create_table(
        "project_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("persona_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=True),
        sa.Column("invited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["persona_id"], ["personas.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "persona_id", name="uq_project_member_persona"),
    )
    op.create_index(op.f("ix_project_members_project_id"), "project_members", ["project_id"])
    op.create_index(op.f("ix_project_members_persona_id"), "project_members", ["persona_id"])
    op.create_index(op.f("ix_project_members_invited_at"), "project_members", ["invited_at"])


def downgrade() -> None:
    op.drop_index(op.f("ix_project_members_invited_at"), table_name="project_members")
    op.drop_index(op.f("ix_project_members_persona_id"), table_name="project_members")
    op.drop_index(op.f("ix_project_members_project_id"), table_name="project_members")
    op.drop_table("project_members")

    op.drop_index(op.f("ix_project_tasks_node"), table_name="project_tasks")
    op.drop_column("project_tasks", "node")
