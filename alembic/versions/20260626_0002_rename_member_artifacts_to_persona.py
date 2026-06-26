"""rename_member_artifacts_to_persona

Revision ID: 20260626_0002_persona_names
Revises: 20260626_drop_personas_user_id
Create Date: 2026-06-26 15:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260626_0002_persona_names"
down_revision: Union[str, None] = "20260626_drop_personas_user_id"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _inspector():
    return sa.inspect(op.get_bind())


def _table_exists(table: str) -> bool:
    return table in _inspector().get_table_names()


def _has_col(table: str, column: str) -> bool:
    if not _table_exists(table):
        return False
    return column in {c["name"] for c in _inspector().get_columns(table)}


def _rename_table(old: str, new: str) -> None:
    if _table_exists(old) and not _table_exists(new):
        op.rename_table(old, new)


def _rename_column(table: str, old: str, new: str) -> None:
    if not _has_col(table, old) or _has_col(table, new):
        return
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table(table) as batch_op:
            batch_op.alter_column(old, new_column_name=new)
    else:
        op.alter_column(table, old, new_column_name=new)


def _rename_index_pg(old: str, new: str) -> None:
    op.execute(
        f"""
        DO $$
        BEGIN
            IF to_regclass('{old}') IS NOT NULL
               AND to_regclass('{new}') IS NULL THEN
                ALTER INDEX {old} RENAME TO {new};
            END IF;
        END $$;
        """
    )


def _rename_constraint_pg(table: str, old: str, new: str) -> None:
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM pg_constraint c
                JOIN pg_class t ON t.oid = c.conrelid
                WHERE t.relname = '{table}' AND c.conname = '{old}'
            )
            AND NOT EXISTS (
                SELECT 1
                FROM pg_constraint c
                JOIN pg_class t ON t.oid = c.conrelid
                WHERE t.relname = '{table}' AND c.conname = '{new}'
            ) THEN
                ALTER TABLE {table} RENAME CONSTRAINT {old} TO {new};
            END IF;
        END $$;
        """
    )


def _rename_runtime_indexes(forward: bool = True) -> None:
    pairs = [
        ("ix_member_positions_persona_id", "ix_persona_positions_persona_id"),
        ("ix_member_positions_position_id", "ix_persona_positions_position_id"),
        ("ix_member_positions_start_date", "ix_persona_positions_start_date"),
        ("ix_member_positions_end_date", "ix_persona_positions_end_date"),
        ("ix_member_positions_is_active", "ix_persona_positions_is_active"),
        ("ix_member_positions_created_at", "ix_persona_positions_created_at"),
        ("ix_member_ministries_persona_id", "ix_persona_ministry_assignments_persona_id"),
        ("ix_member_ministries_ministry_id", "ix_persona_ministry_assignments_ministry_id"),
        ("ix_member_ministries_is_active", "ix_persona_ministry_assignments_is_active"),
        ("ix_member_roles_persona_id", "ix_persona_role_links_persona_id"),
        ("ix_member_roles_role_id", "ix_persona_role_links_role_id"),
    ]
    for old, new in pairs:
        _rename_index_pg(old if forward else new, new if forward else old)


def _rename_runtime_constraints(forward: bool = True) -> None:
    pairs = [
        ("persona_positions", "uq_member_position_history", "uq_persona_position_history"),
        ("persona_ministry_assignments", "uq_member_ministry", "uq_persona_ministry_assignment"),
        ("persona_role_links", "uq_member_role", "uq_persona_role_link"),
    ]
    for table, old, new in pairs:
        _rename_constraint_pg(table, old if forward else new, new if forward else old)


def upgrade() -> None:
    _rename_column("crm_events", "target_member_ids", "target_persona_ids")
    _rename_column("personas", "membership_type", "participation_type")
    _rename_table("member_positions", "persona_positions")
    _rename_table("member_ministries", "persona_ministry_assignments")
    _rename_table("member_roles", "persona_role_links")
    _rename_table("member_volunteer_skills", "persona_volunteer_skills")

    if _has_col("academy_courses", "access_level"):
        op.execute("UPDATE academy_courses SET access_level = 'persona' WHERE access_level = 'member'")

    if op.get_bind().dialect.name == "postgresql":
        _rename_runtime_indexes(forward=True)
        _rename_runtime_constraints(forward=True)
        if _has_col("academy_courses", "access_level"):
            op.execute("ALTER TABLE academy_courses ALTER COLUMN access_level SET DEFAULT 'persona'")


def downgrade() -> None:
    if _has_col("academy_courses", "access_level"):
        op.execute("UPDATE academy_courses SET access_level = 'member' WHERE access_level = 'persona'")

    _rename_column("crm_events", "target_persona_ids", "target_member_ids")
    _rename_column("personas", "participation_type", "membership_type")

    if op.get_bind().dialect.name == "postgresql":
        if _has_col("academy_courses", "access_level"):
            op.execute("ALTER TABLE academy_courses ALTER COLUMN access_level SET DEFAULT 'member'")
        _rename_runtime_constraints(forward=False)
        _rename_runtime_indexes(forward=False)

    _rename_table("persona_positions", "member_positions")
    _rename_table("persona_ministry_assignments", "member_ministries")
    _rename_table("persona_role_links", "member_roles")
    _rename_table("persona_volunteer_skills", "member_volunteer_skills")
