"""operational tables backfill

Revision ID: 20260502_0002
Revises: 20260408_0001
Create Date: 2026-05-02 12:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260502_0002"
down_revision = "20260408_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("automation_rules"):
        op.create_table(
            "automation_rules",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=100), nullable=False),
            sa.Column("trigger_type", sa.String(length=50), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=True, server_default=sa.true()),
            sa.Column("last_run", sa.DateTime(), nullable=True),
            sa.Column("config_json", sa.Text(), nullable=True, server_default="{}"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_automation_rules_id"), "automation_rules", ["id"], unique=False)
        op.create_index(op.f("ix_automation_rules_trigger_type"), "automation_rules", ["trigger_type"], unique=False)
        op.create_index(op.f("ix_automation_rules_is_active"), "automation_rules", ["is_active"], unique=False)

    if not inspector.has_table("project_documents"):
        op.create_table(
            "project_documents",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("project_id", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(length=200), nullable=False),
            sa.Column("content", sa.Text(), nullable=True),
            sa.Column("author_id", sa.Integer(), nullable=True),
            sa.Column("last_edited_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("version", sa.Integer(), nullable=True, server_default="1"),
            sa.ForeignKeyConstraint(["author_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_project_documents_id"), "project_documents", ["id"], unique=False)
        op.create_index(op.f("ix_project_documents_project_id"), "project_documents", ["project_id"], unique=False)
        op.create_index(op.f("ix_project_documents_created_at"), "project_documents", ["created_at"], unique=False)

    if not inspector.has_table("project_whiteboards"):
        op.create_table(
            "project_whiteboards",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("project_id", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(length=200), nullable=False),
            sa.Column("elements_json", sa.Text(), nullable=True, server_default="[]"),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.Column("thumbnail_url", sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_project_whiteboards_id"), "project_whiteboards", ["id"], unique=False)
        op.create_index(op.f("ix_project_whiteboards_project_id"), "project_whiteboards", ["project_id"], unique=False)
        op.create_index(op.f("ix_project_whiteboards_created_at"), "project_whiteboards", ["created_at"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("project_whiteboards"):
        op.drop_index(op.f("ix_project_whiteboards_created_at"), table_name="project_whiteboards")
        op.drop_index(op.f("ix_project_whiteboards_project_id"), table_name="project_whiteboards")
        op.drop_index(op.f("ix_project_whiteboards_id"), table_name="project_whiteboards")
        op.drop_table("project_whiteboards")

    if inspector.has_table("project_documents"):
        op.drop_index(op.f("ix_project_documents_created_at"), table_name="project_documents")
        op.drop_index(op.f("ix_project_documents_project_id"), table_name="project_documents")
        op.drop_index(op.f("ix_project_documents_id"), table_name="project_documents")
        op.drop_table("project_documents")

    if inspector.has_table("automation_rules"):
        op.drop_index(op.f("ix_automation_rules_is_active"), table_name="automation_rules")
        op.drop_index(op.f("ix_automation_rules_trigger_type"), table_name="automation_rules")
        op.drop_index(op.f("ix_automation_rules_id"), table_name="automation_rules")
        op.drop_table("automation_rules")
