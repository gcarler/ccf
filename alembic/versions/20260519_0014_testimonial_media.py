"""add media fields to testimonials

Revision ID: 20260519_0014
Revises: 20260519_0013
Create Date: 2026-05-19 00:00:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260519_0014"
down_revision = "20260519_0013"
branch_labels = None
depends_on = None


def _has_column(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    return any(
        column.get("name") == column_name
        for column in inspector.get_columns(table_name)
    )


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("testimonials"):
        return

    columns = [
        sa.Column(
            "media_type", sa.String(length=30), nullable=False, server_default="text"
        ),
        sa.Column("media_url", sa.String(length=500), nullable=True),
        sa.Column("image_url", sa.String(length=500), nullable=True),
        sa.Column("video_url", sa.String(length=500), nullable=True),
        sa.Column("podcast_url", sa.String(length=500), nullable=True),
    ]

    with op.batch_alter_table("testimonials") as batch_op:
        for column in columns:
            if not _has_column(inspector, "testimonials", column.name):
                batch_op.add_column(column)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("testimonials"):
        return

    with op.batch_alter_table("testimonials") as batch_op:
        for column_name in (
            "podcast_url",
            "video_url",
            "image_url",
            "media_url",
            "media_type",
        ):
            if _has_column(inspector, "testimonials", column_name):
                batch_op.drop_column(column_name)
