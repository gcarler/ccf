"""repair faro reporting constraints and indexes

Revision ID: 20260516_0011
Revises: 20260505_0010
Create Date: 2026-05-16 11:30:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260516_0011"
down_revision = "20260505_0010"
branch_labels = None
depends_on = None


def _has_column(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _has_index(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    return any(index.get("name") == index_name for index in inspector.get_indexes(table_name))


def _has_fk(inspector: sa.Inspector, table_name: str, fk_name: str) -> bool:
    return any(fk.get("name") == fk_name for fk in inspector.get_foreign_keys(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("glory_house_sessions") and _has_column(inspector, "glory_house_sessions", "reported_by_member_id"):
        if not _has_fk(inspector, "glory_house_sessions", "fk_glory_house_sessions_reported_by_member_id"):
            with op.batch_alter_table("glory_house_sessions") as batch_op:
                batch_op.create_foreign_key(
                    "fk_glory_house_sessions_reported_by_member_id",
                    "members",
                    ["reported_by_member_id"],
                    ["id"],
                    ondelete="SET NULL",
                )
            inspector = sa.inspect(bind)

        if not _has_index(inspector, "glory_house_sessions", "ix_glory_house_sessions_reported_by_member_id"):
            op.create_index(
                "ix_glory_house_sessions_reported_by_member_id",
                "glory_house_sessions",
                ["reported_by_member_id"],
                unique=False,
            )
            inspector = sa.inspect(bind)

    if inspector.has_table("glory_house_attendance") and _has_column(inspector, "glory_house_attendance", "absence_reason"):
        if not _has_index(inspector, "glory_house_attendance", "ix_glory_house_attendance_absence_reason"):
            op.create_index(
                "ix_glory_house_attendance_absence_reason",
                "glory_house_attendance",
                ["absence_reason"],
                unique=False,
            )
            inspector = sa.inspect(bind)

    if inspector.has_table("glory_houses") and _has_column(inspector, "glory_houses", "code"):
        if not _has_index(inspector, "glory_houses", "ix_glory_houses_code"):
            op.create_index("ix_glory_houses_code", "glory_houses", ["code"], unique=True)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("glory_houses") and _has_index(inspector, "glory_houses", "ix_glory_houses_code"):
        op.drop_index("ix_glory_houses_code", table_name="glory_houses")

    inspector = sa.inspect(bind)
    if inspector.has_table("glory_house_attendance") and _has_index(inspector, "glory_house_attendance", "ix_glory_house_attendance_absence_reason"):
        op.drop_index("ix_glory_house_attendance_absence_reason", table_name="glory_house_attendance")

    inspector = sa.inspect(bind)
    if inspector.has_table("glory_house_sessions") and _has_index(inspector, "glory_house_sessions", "ix_glory_house_sessions_reported_by_member_id"):
        op.drop_index("ix_glory_house_sessions_reported_by_member_id", table_name="glory_house_sessions")

    inspector = sa.inspect(bind)
    if inspector.has_table("glory_house_sessions") and _has_fk(inspector, "glory_house_sessions", "fk_glory_house_sessions_reported_by_member_id"):
        with op.batch_alter_table("glory_house_sessions") as batch_op:
            batch_op.drop_constraint("fk_glory_house_sessions_reported_by_member_id", type_="foreignkey")
