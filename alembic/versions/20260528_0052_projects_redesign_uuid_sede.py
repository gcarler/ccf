"""0052_projects_redesign_uuid_sede

Revision ID: 20260528_0052
Revises: 20260528_0051
Create Date: 2026-05-28

Rediseño completo del módulo de proyectos para cumplir los 3 axiomas del
Kernel Unificado CCF. Todas las tablas estaban vacías (0 registros).

Cambios respecto al diseño anterior:
  - IDs Integer → UUID
  - projects.owner_id → UUID FK → personas (Axioma 1)
  - project_tasks.assignee_id → UUID FK → personas (Axioma 1)
  - project_comments.author_id → UUID FK → personas (Axioma 1)
  - project_attachments.uploader_id → UUID FK → personas (Axioma 1)
  - project_documents.author_id → UUID FK → personas (Axioma 1)
  - project_activity_logs.persona_id → UUID FK → personas (Axioma 1)
  - projects.sede_id → INT FK → sedes (Axioma 3)
  - projects.deleted_at + project_tasks.deleted_at (Soft Delete)
  - DateTime(timezone=True) en todas las fechas
  - field fixes: target_date (milestones), filename/file_type (attachments)
  - project_inbox_state.user_id queda como users.id (estado de lectura UI)
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision: str = "20260528_0052"
down_revision: Union[str, None] = "20260528_0051"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES = [
    "project_inbox_state",
    "project_activity_logs",
    "project_documents",
    "project_whiteboards",
    "task_supplies",
    "project_attachments",
    "project_phases",
    "project_milestones",
    "project_comments",
    "project_tasks",
    "projects",
]


def upgrade() -> None:
    # Drop all in reverse FK dependency order
    for t in TABLES:
        op.execute(sa.text(f"DROP TABLE IF EXISTS {t} CASCADE"))

    # ── projects ──────────────────────────────────────────────────────────
    op.create_table(
        "projects",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("sede_id", sa.Integer(), sa.ForeignKey("sedes.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="planning"),
        sa.Column("owner_id", UUID(as_uuid=True), sa.ForeignKey("personas.id", ondelete="SET NULL"), nullable=True),
        sa.Column("color", sa.String(20), nullable=True),
        sa.Column("icon", sa.String(50), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_projects_sede_id", "projects", ["sede_id"])
    op.create_index("ix_projects_owner_id", "projects", ["owner_id"])
    op.create_index("ix_projects_status", "projects", ["status"])
    op.create_index("ix_projects_created_at", "projects", ["created_at"])
    op.create_index("ix_projects_active", "projects", ["deleted_at"],
                    postgresql_where=sa.text("deleted_at IS NULL"))

    # ── project_tasks ─────────────────────────────────────────────────────
    op.create_table(
        "project_tasks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("parent_id", UUID(as_uuid=True), sa.ForeignKey("project_tasks.id", ondelete="CASCADE"), nullable=True),
        sa.Column("order_index", sa.Integer(), server_default="0"),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="todo"),
        sa.Column("priority", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("assignee_id", UUID(as_uuid=True), sa.ForeignKey("personas.id", ondelete="SET NULL"), nullable=True),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("labels", JSONB(), nullable=True, server_default=sa.text("'[]'::jsonb")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_project_tasks_project_id", "project_tasks", ["project_id"])
    op.create_index("ix_project_tasks_assignee_id", "project_tasks", ["assignee_id"])
    op.create_index("ix_project_tasks_status", "project_tasks", ["status"])
    op.create_index("ix_project_tasks_active", "project_tasks", ["deleted_at"],
                    postgresql_where=sa.text("deleted_at IS NULL"))

    # ── project_milestones ────────────────────────────────────────────────
    op.create_table(
        "project_milestones",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("target_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_completed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_project_milestones_project_id", "project_milestones", ["project_id"])

    # ── project_phases ────────────────────────────────────────────────────
    op.create_table(
        "project_phases",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("slug", sa.String(20), nullable=False),
        sa.Column("color", sa.String(20), nullable=False, server_default="'#94a3b8'"),
        sa.Column("order_index", sa.Integer(), server_default="0"),
    )
    op.create_index("ix_project_phases_project_id", "project_phases", ["project_id"])

    # ── project_comments ──────────────────────────────────────────────────
    op.create_table(
        "project_comments",
        sa.Column("id", sa.Integer(), sa.Identity(), primary_key=True),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("task_id", UUID(as_uuid=True), sa.ForeignKey("project_tasks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("author_id", UUID(as_uuid=True), sa.ForeignKey("personas.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("is_resolved", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_project_comments_project_id", "project_comments", ["project_id"])
    op.create_index("ix_project_comments_author_id", "project_comments", ["author_id"])

    # ── project_attachments ───────────────────────────────────────────────
    op.create_table(
        "project_attachments",
        sa.Column("id", sa.Integer(), sa.Identity(), primary_key=True),
        sa.Column("task_id", UUID(as_uuid=True), sa.ForeignKey("project_tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("file_url", sa.Text(), nullable=False),
        sa.Column("file_type", sa.String(100), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("uploader_id", UUID(as_uuid=True), sa.ForeignKey("personas.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_project_attachments_task_id", "project_attachments", ["task_id"])

    # ── task_supplies ─────────────────────────────────────────────────────
    op.create_table(
        "task_supplies",
        sa.Column("id", sa.Integer(), sa.Identity(), primary_key=True),
        sa.Column("task_id", UUID(as_uuid=True), sa.ForeignKey("project_tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("item_name", sa.String(200), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(20), nullable=False, server_default="'pending'"),
    )
    op.create_index("ix_task_supplies_task_id", "task_supplies", ["task_id"])

    # ── project_whiteboards ───────────────────────────────────────────────
    op.create_table(
        "project_whiteboards",
        sa.Column("id", sa.Integer(), sa.Identity(), primary_key=True),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("title", sa.String(200), nullable=False, server_default="'Pizarra'"),
        sa.Column("elements_json", sa.Text(), nullable=False, server_default="'[]'"),
        sa.Column("thumbnail_url", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # ── project_documents ─────────────────────────────────────────────────
    op.create_table(
        "project_documents",
        sa.Column("id", sa.Integer(), sa.Identity(), primary_key=True),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False, server_default="'Wiki'"),
        sa.Column("content", sa.Text(), nullable=False, server_default="''"),
        sa.Column("author_id", UUID(as_uuid=True), sa.ForeignKey("personas.id", ondelete="SET NULL"), nullable=True),
        sa.Column("last_edited_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_project_documents_project_id", "project_documents", ["project_id"])

    # ── project_activity_logs ─────────────────────────────────────────────
    op.create_table(
        "project_activity_logs",
        sa.Column("id", sa.Integer(), sa.Identity(), primary_key=True),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("persona_id", UUID(as_uuid=True), sa.ForeignKey("personas.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action_type", sa.String(50), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_project_activity_logs_project_id", "project_activity_logs", ["project_id"])
    op.create_index("ix_project_activity_logs_created_at", "project_activity_logs", ["created_at"])

    # ── project_inbox_state ───────────────────────────────────────────────
    op.create_table(
        "project_inbox_state",
        sa.Column("id", sa.Integer(), sa.Identity(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("item_id", sa.String(80), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("user_id", "item_id", name="uq_user_project_item"),
    )
    op.create_index("ix_project_inbox_state_user_id", "project_inbox_state", ["user_id"])


def downgrade() -> None:
    for t in TABLES:
        op.execute(sa.text(f"DROP TABLE IF EXISTS {t} CASCADE"))
