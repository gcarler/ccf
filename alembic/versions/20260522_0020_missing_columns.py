"""add missing columns to existing tables

Revision ID: 20260522_0020
Revises: 20260522_0019
Create Date: 2026-05-22

Adds columns that were previously only added by
_run_startup_migrations():
- crm_tasks.category
- crm_events.fixed_date
- cms_media_items.filename, mime_type, file_size
- cms_sections.section_type
"""
from alembic import op
import sqlalchemy as sa

revision = "20260522_0020"
down_revision = "20260522_0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # crm_tasks.category
    if "crm_tasks" in inspector.get_table_names():
        cols = [c["name"] for c in inspector.get_columns("crm_tasks")]
        if "category" not in cols:
            with op.batch_alter_table("crm_tasks", schema=None) as batch_op:
                batch_op.add_column(sa.Column("category", sa.String(100), server_default="Pastoral", nullable=True))
            op.create_index("ix_crm_tasks_category", "crm_tasks", ["category"])

    # crm_events.fixed_date
    if "crm_events" in inspector.get_table_names():
        cols = [c["name"] for c in inspector.get_columns("crm_events")]
        if "fixed_date" not in cols:
            with op.batch_alter_table("crm_events", schema=None) as batch_op:
                batch_op.add_column(sa.Column("fixed_date", sa.DateTime, nullable=True))

    # cms_media_items: filename, mime_type, file_size
    if "cms_media_items" in inspector.get_table_names():
        cols = [c["name"] for c in inspector.get_columns("cms_media_items")]
        if "filename" not in cols:
            with op.batch_alter_table("cms_media_items", schema=None) as batch_op:
                batch_op.add_column(sa.Column("filename", sa.String(255), nullable=True))
        if "mime_type" not in cols:
            with op.batch_alter_table("cms_media_items", schema=None) as batch_op:
                batch_op.add_column(sa.Column("mime_type", sa.String(120), nullable=True))
        if "file_size" not in cols:
            with op.batch_alter_table("cms_media_items", schema=None) as batch_op:
                batch_op.add_column(sa.Column("file_size", sa.Integer, server_default="0"))

    # cms_sections.section_type
    if "cms_sections" in inspector.get_table_names():
        cols = [c["name"] for c in inspector.get_columns("cms_sections")]
        if "section_type" not in cols:
            with op.batch_alter_table("cms_sections", schema=None) as batch_op:
                batch_op.add_column(sa.Column("section_type", sa.String(50), nullable=True))


def downgrade() -> None:
    # Safe drop — only if column exists
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if "crm_tasks" in inspector.get_table_names():
        cols = [c["name"] for c in inspector.get_columns("crm_tasks")]
        if "category" in cols:
            with op.batch_alter_table("crm_tasks", schema=None) as batch_op:
                batch_op.drop_column("category")

    if "crm_events" in inspector.get_table_names():
        cols = [c["name"] for c in inspector.get_columns("crm_events")]
        if "fixed_date" in cols:
            with op.batch_alter_table("crm_events", schema=None) as batch_op:
                batch_op.drop_column("fixed_date")

    if "cms_media_items" in inspector.get_table_names():
        cols = [c["name"] for c in inspector.get_columns("cms_media_items")]
        with op.batch_alter_table("cms_media_items", schema=None) as batch_op:
            if "filename" in cols:
                batch_op.drop_column("filename")
            if "mime_type" in cols:
                batch_op.drop_column("mime_type")
            if "file_size" in cols:
                batch_op.drop_column("file_size")

    if "cms_sections" in inspector.get_table_names():
        cols = [c["name"] for c in inspector.get_columns("cms_sections")]
        if "section_type" in cols:
            with op.batch_alter_table("cms_sections", schema=None) as batch_op:
                batch_op.drop_column("section_type")
