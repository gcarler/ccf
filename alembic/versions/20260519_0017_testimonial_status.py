"""add status to testimonials

Revision ID: 20260519_0017
Revises: 20260519_0016
Create Date: 2026-05-19 00:00:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260519_0017"
down_revision = "20260519_0016"
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

    with op.batch_alter_table("testimonials") as batch_op:
        if not _has_column(inspector, "testimonials", "status"):
            batch_op.add_column(
                sa.Column(
                    "status",
                    sa.String(length=20),
                    nullable=False,
                    server_default="pending",
                )
            )
            batch_op.create_index("ix_testimonials_status", ["status"])

    op.execute(
        "UPDATE testimonials SET status = CASE WHEN is_approved = TRUE THEN 'approved' ELSE 'pending' END WHERE status IS NULL OR status = 'pending'"
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("testimonials"):
        return

    with op.batch_alter_table("testimonials") as batch_op:
        if _has_column(inspector, "testimonials", "status"):
            batch_op.drop_index("ix_testimonials_status")
            batch_op.drop_column("status")
