"""repair faro reporting constraints and indexes

Revision ID: 20260516_0011
Revises: 20260505_0010
Create Date: 2026-05-16 11:30:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260516_0011"
down_revision = "20260505_0010"
branch_labels = None
depends_on = None


def _has_column(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    return any(
        column["name"] == column_name for column in inspector.get_columns(table_name)
    )


def _has_index(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    return any(
        index.get("name") == index_name for index in inspector.get_indexes(table_name)
    )


def _has_fk(inspector: sa.Inspector, table_name: str, fk_name: str) -> bool:
    return any(
        fk.get("name") == fk_name for fk in inspector.get_foreign_keys(table_name)
    )


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("sesiones_grupo") and _has_column(
        inspector, "sesiones_grupo", "reported_by_member_id"
    ):
        if not _has_fk(
            inspector,
            "sesiones_grupo",
            "fk_sesiones_grupo_reported_by_member_id",
        ):
            with op.batch_alter_table("sesiones_grupo") as batch_op:
                batch_op.create_foreign_key(
                    "fk_sesiones_grupo_reported_by_member_id",
                    "members",
                    ["reported_by_member_id"],
                    ["id"],
                    ondelete="SET NULL",
                )
            inspector = sa.inspect(bind)

        if not _has_index(
            inspector,
            "sesiones_grupo",
            "ix_sesiones_grupo_reported_by_member_id",
        ):
            op.create_index(
                "ix_sesiones_grupo_reported_by_member_id",
                "sesiones_grupo",
                ["reported_by_member_id"],
                unique=False,
            )
            inspector = sa.inspect(bind)

    if inspector.has_table("asistencias") and _has_column(
        inspector, "asistencias", "absence_reason"
    ):
        if not _has_index(
            inspector,
            "asistencias",
            "ix_asistencias_absence_reason",
        ):
            op.create_index(
                "ix_asistencias_absence_reason",
                "asistencias",
                ["absence_reason"],
                unique=False,
            )
            inspector = sa.inspect(bind)

    if inspector.has_table("grupos_evangelismo") and _has_column(
        inspector, "grupos_evangelismo", "code"
    ):
        if not _has_index(inspector, "grupos_evangelismo", "ix_grupos_evangelismo_code"):
            op.create_index(
                "ix_grupos_evangelismo_code", "grupos_evangelismo", ["code"], unique=True
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("grupos_evangelismo") and _has_index(
        inspector, "grupos_evangelismo", "ix_grupos_evangelismo_code"
    ):
        op.drop_index("ix_grupos_evangelismo_code", table_name="grupos_evangelismo")

    inspector = sa.inspect(bind)
    if inspector.has_table("asistencias") and _has_index(
        inspector, "asistencias", "ix_asistencias_absence_reason"
    ):
        op.drop_index(
            "ix_asistencias_absence_reason",
            table_name="asistencias",
        )

    inspector = sa.inspect(bind)
    if inspector.has_table("sesiones_grupo") and _has_index(
        inspector,
        "sesiones_grupo",
        "ix_sesiones_grupo_reported_by_member_id",
    ):
        op.drop_index(
            "ix_sesiones_grupo_reported_by_member_id",
            table_name="sesiones_grupo",
        )

    inspector = sa.inspect(bind)
    if inspector.has_table("sesiones_grupo") and _has_fk(
        inspector,
        "sesiones_grupo",
        "fk_sesiones_grupo_reported_by_member_id",
    ):
        with op.batch_alter_table("sesiones_grupo") as batch_op:
            batch_op.drop_constraint(
                "fk_sesiones_grupo_reported_by_member_id", type_="foreignkey"
            )
