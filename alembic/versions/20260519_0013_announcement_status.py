"""add publication status to announcements

Revision ID: 20260519_0013
Revises: 20260517_0012
Create Date: 2026-05-19 00:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260519_0013"
down_revision = "20260517_0012"
branch_labels = None
depends_on = None


def _has_column(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    return any(column.get("name") == column_name for column in inspector.get_columns(table_name))


def _has_index(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    return any(index.get("name") == index_name for index in inspector.get_indexes(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("announcements"):
        return

    if not _has_column(inspector, "announcements", "status"):
        with op.batch_alter_table("announcements") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "status",
                    sa.String(length=20),
                    nullable=False,
                    server_default="published",
                )
            )
        inspector = sa.inspect(bind)

    if not _has_index(inspector, "announcements", "ix_announcements_status"):
        op.create_index("ix_announcements_status", "announcements", ["status"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("announcements"):
        return

    if _has_index(inspector, "announcements", "ix_announcements_status"):
        op.drop_index("ix_announcements_status", table_name="announcements")
        inspector = sa.inspect(bind)

    if _has_column(inspector, "announcements", "status"):
        with op.batch_alter_table("announcements") as batch_op:
            batch_op.drop_column("status")
