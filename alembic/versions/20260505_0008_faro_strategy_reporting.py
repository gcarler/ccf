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

    if inspector.has_table("grupos_evangelismo") and not _has_column(
        inspector, "grupos_evangelismo", "code"
    ):
        with op.batch_alter_table("grupos_evangelismo") as batch_op:
            batch_op.add_column(sa.Column("code", sa.String(length=30), nullable=True))
        op.create_index("ix_grupos_evangelismo_code", "grupos_evangelismo", ["code"], unique=True)

    if inspector.has_table("sesiones_grupo"):
        with op.batch_alter_table("sesiones_grupo") as batch_op:
            if not _has_column(inspector, "sesiones_grupo", "topic"):
                batch_op.add_column(
                    sa.Column("topic", sa.String(length=255), nullable=True)
                )
            if not _has_column(inspector, "sesiones_grupo", "offering_amount"):
                batch_op.add_column(
                    sa.Column("offering_amount", sa.Numeric(12, 2), nullable=True)
                )
            if not _has_column(inspector, "sesiones_grupo", "report_notes"):
                batch_op.add_column(sa.Column("report_notes", sa.Text(), nullable=True))
            if not _has_column(inspector, "sesiones_grupo", "novelty_type"):
                batch_op.add_column(
                    sa.Column("novelty_type", sa.String(length=50), nullable=True)
                )
            if not _has_column(inspector, "sesiones_grupo", "novelty_detail"):
                batch_op.add_column(
                    sa.Column("novelty_detail", sa.Text(), nullable=True)
                )
            if not _has_column(
                inspector, "sesiones_grupo", "cancellation_reason"
            ):
                batch_op.add_column(
                    sa.Column("cancellation_reason", sa.Text(), nullable=True)
                )
            if not _has_column(
                inspector, "sesiones_grupo", "reported_by_member_id"
            ):
                batch_op.add_column(
                    sa.Column("reported_by_member_id", sa.Integer(), nullable=True)
                )
            if not _has_column(inspector, "sesiones_grupo", "reported_at"):
                batch_op.add_column(
                    sa.Column("reported_at", sa.DateTime(), nullable=True)
                )
            if not _has_column(
                inspector, "sesiones_grupo", "reported_by_member_id"
            ):
                batch_op.create_foreign_key(
                    "fk_sesiones_grupo_reported_by_member_id",
                    "members",
                    ["reported_by_member_id"],
                    ["id"],
                    ondelete="SET NULL",
                )
        if not _has_column(inspector, "sesiones_grupo", "reported_by_member_id"):
            op.create_index(
                "ix_sesiones_grupo_reported_by_member_id",
                "sesiones_grupo",
                ["reported_by_member_id"],
                unique=False,
            )

    if inspector.has_table("asistencias"):
        with op.batch_alter_table("asistencias") as batch_op:
            if not _has_column(inspector, "asistencias", "absence_reason"):
                batch_op.add_column(
                    sa.Column("absence_reason", sa.String(length=50), nullable=True)
                )
            if not _has_column(
                inspector, "asistencias", "absence_reason_detail"
            ):
                batch_op.add_column(
                    sa.Column("absence_reason_detail", sa.Text(), nullable=True)
                )
        if not _has_column(inspector, "asistencias", "absence_reason"):
            op.create_index(
                "ix_asistencias_absence_reason",
                "asistencias",
                ["absence_reason"],
                unique=False,
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("asistencias") and _has_column(
        inspector, "asistencias", "absence_reason_detail"
    ):
        op.drop_index(
            "ix_asistencias_absence_reason",
            table_name="asistencias",
        )
        with op.batch_alter_table("asistencias") as batch_op:
            if _has_column(
                inspector, "asistencias", "absence_reason_detail"
            ):
                batch_op.drop_column("absence_reason_detail")
            if _has_column(inspector, "asistencias", "absence_reason"):
                batch_op.drop_column("absence_reason")

    if inspector.has_table("sesiones_grupo") and _has_column(
        inspector, "sesiones_grupo", "topic"
    ):
        with op.batch_alter_table("sesiones_grupo") as batch_op:
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
                if _has_column(inspector, "sesiones_grupo", column):
                    batch_op.drop_column(column)
        if _has_column(inspector, "sesiones_grupo", "reported_by_member_id"):
            op.drop_index(
                "ix_sesiones_grupo_reported_by_member_id",
                table_name="sesiones_grupo",
            )

    if inspector.has_table("grupos_evangelismo") and _has_column(
        inspector, "grupos_evangelismo", "code"
    ):
        op.drop_index("ix_grupos_evangelismo_code", table_name="grupos_evangelismo")
        with op.batch_alter_table("grupos_evangelismo") as batch_op:
            batch_op.drop_column("code")
