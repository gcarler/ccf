"""add status to cms media items

Revision ID: 20260519_0016
Revises: 20260519_0015
Create Date: 2026-05-19 00:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260519_0016"
down_revision = "20260519_0015"
branch_labels = None
depends_on = None


def _has_column(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    return any(column.get("name") == column_name for column in inspector.get_columns(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("cms_media_items"):
        return

    with op.batch_alter_table("cms_media_items") as batch_op:
        if not _has_column(inspector, "cms_media_items", "status"):
            batch_op.add_column(sa.Column("status", sa.String(length=20), nullable=False, server_default="active"))
            batch_op.create_index("ix_cms_media_items_status", ["status"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("cms_media_items"):
        return

    with op.batch_alter_table("cms_media_items") as batch_op:
        if _has_column(inspector, "cms_media_items", "status"):
            batch_op.drop_index("ix_cms_media_items_status")
            batch_op.drop_column("status")
