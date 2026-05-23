"""add faro strategy codes and weekly reporting fields

Revision ID: 20260505_0008
Revises: 20260505_0007
Create Date: 2026-05-05 10:30:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260505_0008"
down_revision = "20260505_0007"
branch_labels = None
depends_on = None


def _has_column(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    return any(
        column["name"] == column_name for column in inspector.get_columns(table_name)
    )


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("glory_houses") and not _has_column(
        inspector, "glory_houses", "code"
    ):
        with op.batch_alter_table("glory_houses") as batch_op:
            batch_op.add_column(sa.Column("code", sa.String(length=30), nullable=True))
        op.create_index("ix_glory_houses_code", "glory_houses", ["code"], unique=True)

    if inspector.has_table("glory_house_sessions"):
        with op.batch_alter_table("glory_house_sessions") as batch_op:
            if not _has_column(inspector, "glory_house_sessions", "topic"):
                batch_op.add_column(
                    sa.Column("topic", sa.String(length=255), nullable=True)
                )
            if not _has_column(inspector, "glory_house_sessions", "offering_amount"):
                batch_op.add_column(
                    sa.Column("offering_amount", sa.Numeric(12, 2), nullable=True)
                )
            if not _has_column(inspector, "glory_house_sessions", "report_notes"):
                batch_op.add_column(sa.Column("report_notes", sa.Text(), nullable=True))
            if not _has_column(inspector, "glory_house_sessions", "novelty_type"):
                batch_op.add_column(
                    sa.Column("novelty_type", sa.String(length=50), nullable=True)
                )
            if not _has_column(inspector, "glory_house_sessions", "novelty_detail"):
                batch_op.add_column(
                    sa.Column("novelty_detail", sa.Text(), nullable=True)
                )
            if not _has_column(
                inspector, "glory_house_sessions", "cancellation_reason"
            ):
                batch_op.add_column(
                    sa.Column("cancellation_reason", sa.Text(), nullable=True)
                )
            if not _has_column(
                inspector, "glory_house_sessions", "reported_by_member_id"
            ):
                batch_op.add_column(
                    sa.Column("reported_by_member_id", sa.Integer(), nullable=True)
                )
            if not _has_column(inspector, "glory_house_sessions", "reported_at"):
                batch_op.add_column(
                    sa.Column("reported_at", sa.DateTime(), nullable=True)
                )
            if not _has_column(
                inspector, "glory_house_sessions", "reported_by_member_id"
            ):
                batch_op.create_foreign_key(
                    "fk_glory_house_sessions_reported_by_member_id",
                    "members",
                    ["reported_by_member_id"],
                    ["id"],
                    ondelete="SET NULL",
                )
        if not _has_column(inspector, "glory_house_sessions", "reported_by_member_id"):
            op.create_index(
                "ix_glory_house_sessions_reported_by_member_id",
                "glory_house_sessions",
                ["reported_by_member_id"],
                unique=False,
            )

    if inspector.has_table("glory_house_attendance"):
        with op.batch_alter_table("glory_house_attendance") as batch_op:
            if not _has_column(inspector, "glory_house_attendance", "absence_reason"):
                batch_op.add_column(
                    sa.Column("absence_reason", sa.String(length=50), nullable=True)
                )
            if not _has_column(
                inspector, "glory_house_attendance", "absence_reason_detail"
            ):
                batch_op.add_column(
                    sa.Column("absence_reason_detail", sa.Text(), nullable=True)
                )
        if not _has_column(inspector, "glory_house_attendance", "absence_reason"):
            op.create_index(
                "ix_glory_house_attendance_absence_reason",
                "glory_house_attendance",
                ["absence_reason"],
                unique=False,
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("glory_house_attendance") and _has_column(
        inspector, "glory_house_attendance", "absence_reason_detail"
    ):
        op.drop_index(
            "ix_glory_house_attendance_absence_reason",
            table_name="glory_house_attendance",
        )
        with op.batch_alter_table("glory_house_attendance") as batch_op:
            if _has_column(
                inspector, "glory_house_attendance", "absence_reason_detail"
            ):
                batch_op.drop_column("absence_reason_detail")
            if _has_column(inspector, "glory_house_attendance", "absence_reason"):
                batch_op.drop_column("absence_reason")

    if inspector.has_table("glory_house_sessions") and _has_column(
        inspector, "glory_house_sessions", "topic"
    ):
        with op.batch_alter_table("glory_house_sessions") as batch_op:
            for column in [
                "reported_at",
                "reported_by_member_id",
                "cancellation_reason",
                "novelty_detail",
                "novelty_type",
                "report_notes",
                "offering_amount",
                "topic",
            ]:
                if _has_column(inspector, "glory_house_sessions", column):
                    batch_op.drop_column(column)
        if _has_column(inspector, "glory_house_sessions", "reported_by_member_id"):
            op.drop_index(
                "ix_glory_house_sessions_reported_by_member_id",
                table_name="glory_house_sessions",
            )

    if inspector.has_table("glory_houses") and _has_column(
        inspector, "glory_houses", "code"
    ):
        op.drop_index("ix_glory_houses_code", table_name="glory_houses")
        with op.batch_alter_table("glory_houses") as batch_op:
            batch_op.drop_column("code")
