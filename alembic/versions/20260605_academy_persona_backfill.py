"""Backfill Academy persona UUID columns

Revision ID: 20260605_acad_pers_backfill
Revises: 20260604_personas_scanner_token
Create Date: 2026-06-05

Fills the legacy Academy runtime tables from personas.user_id so the app can
keep users.id as compatibility data while UUID/persona becomes canonical.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260605_acad_pers_backfill"
down_revision: Union[str, None] = "20260604_personas_scanner_token"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _cols(table: str) -> set[str]:
    return {col["name"] for col in sa.inspect(op.get_bind()).get_columns(table)}


def _has_table(table: str) -> bool:
    return table in _tables()


def _has_col(table: str, column: str) -> bool:
    return _has_table(table) and column in _cols(table)


def _uuid_type():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        return postgresql.UUID(as_uuid=True)
    return sa.String(36)


def _add_uuid_column(table: str, column: str, *, index: bool = True) -> None:
    if not _has_table(table) or _has_col(table, column):
        return
    with op.batch_alter_table(table, schema=None) as batch_op:
        batch_op.add_column(sa.Column(column, _uuid_type(), nullable=True))
    if index:
        op.create_index(f"ix_{table}_{column}", table, [column], unique=False)


def _index_exists(table: str, index_name: str) -> bool:
    if not _has_table(table):
        return False
    indexes = sa.inspect(op.get_bind()).get_indexes(table)
    return any(index["name"] == index_name for index in indexes)


def _create_index_if_missing(table: str, column: str) -> None:
    index_name = f"ix_{table}_{column}"
    if _has_table(table) and _has_col(table, column) and not _index_exists(table, index_name):
        op.create_index(index_name, table, [column], unique=False)


def _constraint_exists(name: str) -> bool:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return False
    return bool(
        bind.execute(
            sa.text(
                "SELECT 1 FROM information_schema.table_constraints "
                "WHERE constraint_schema='public' AND constraint_name=:name"
            ),
            {"name": name},
        ).first()
    )


def _pg_add_fk_if_missing(table: str, column: str, constraint_name: str) -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql" or _constraint_exists(constraint_name):
        return
    if not (_has_table(table) and _has_col(table, column)):
        return
    bind.execute(
        sa.text(
            f"ALTER TABLE {table} ADD CONSTRAINT {constraint_name} "
            f"FOREIGN KEY ({column}) REFERENCES personas(id) ON DELETE SET NULL "
            f"NOT VALID"
        )
    )


def _duplicate_count(table: str, left: str, right: str) -> int:
    bind = op.get_bind()
    if not all(_has_col(table, col) for col in (left, right)):
        return 0
    row = bind.execute(
        sa.text(
            f"SELECT COUNT(*) FROM ("
            f"SELECT {left}, {right}, COUNT(*) "
            f"FROM {table} "
            f"WHERE {left} IS NOT NULL "
            f"GROUP BY {left}, {right} HAVING COUNT(*) > 1"
            f") dupes"
        )
    ).scalar()
    return int(row or 0)


def _pg_add_unique_if_clean(table: str, columns: tuple[str, str], constraint_name: str) -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql" or _constraint_exists(constraint_name):
        return
    if not (_has_table(table) and all(_has_col(table, col) for col in columns)):
        return
    if _duplicate_count(table, columns[0], columns[1]) > 0:
        return
    bind.execute(
        sa.text(
            f"ALTER TABLE {table} ADD CONSTRAINT {constraint_name} "
            f"UNIQUE ({columns[0]}, {columns[1]})"
        )
    )


def _backfill(table: str, target_col: str, source_col: str = "user_id") -> None:
    if not (_has_table(table) and _has_table("personas")):
        return
    if not (_has_col(table, target_col) and _has_col(table, source_col)):
        return
    op.get_bind().execute(
        sa.text(
            f"UPDATE {table} "
            f"SET {target_col} = ("
            f"SELECT personas.id FROM personas "
            f"WHERE personas.user_id = {table}.{source_col}"
            f") "
            f"WHERE {target_col} IS NULL "
            f"AND {source_col} IS NOT NULL "
            f"AND EXISTS ("
            f"SELECT 1 FROM personas WHERE personas.user_id = {table}.{source_col}"
            f")"
        )
    )


def upgrade() -> None:
    _add_uuid_column("enrollments", "persona_id")
    _add_uuid_column("lesson_progress", "persona_id")
    _add_uuid_column("academy_activity_logs", "persona_id")
    _add_uuid_column("formal_actas", "closed_by_persona_id", index=False)
    _create_index_if_missing("formal_actas", "closed_by_persona_id")

    _backfill("enrollments", "persona_id")
    _backfill("lesson_progress", "persona_id")
    _backfill("academy_activity_logs", "persona_id")
    _backfill("formal_actas", "closed_by_persona_id", "closed_by_user_id")

    _pg_add_fk_if_missing("enrollments", "persona_id", "fk_enrollments_persona_id")
    _pg_add_fk_if_missing("lesson_progress", "persona_id", "fk_lesson_progress_persona_id")
    _pg_add_fk_if_missing(
        "academy_activity_logs",
        "persona_id",
        "fk_academy_activity_logs_persona_id",
    )
    _pg_add_fk_if_missing(
        "formal_actas",
        "closed_by_persona_id",
        "fk_formal_actas_closed_by_persona_id",
    )

    _pg_add_unique_if_clean(
        "enrollments",
        ("persona_id", "course_id"),
        "uq_persona_course",
    )
    _pg_add_unique_if_clean(
        "lesson_progress",
        ("persona_id", "lesson_id"),
        "uq_persona_lesson_progress",
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        for table, constraint in (
            ("lesson_progress", "uq_persona_lesson_progress"),
            ("enrollments", "uq_persona_course"),
            ("formal_actas", "fk_formal_actas_closed_by_persona_id"),
            ("academy_activity_logs", "fk_academy_activity_logs_persona_id"),
            ("lesson_progress", "fk_lesson_progress_persona_id"),
            ("enrollments", "fk_enrollments_persona_id"),
        ):
            bind.execute(
                sa.text(
                    f"ALTER TABLE IF EXISTS {table} "
                    f"DROP CONSTRAINT IF EXISTS {constraint}"
                )
            )

    for table, column in (
        ("formal_actas", "closed_by_persona_id"),
        ("academy_activity_logs", "persona_id"),
        ("lesson_progress", "persona_id"),
        ("enrollments", "persona_id"),
    ):
        if _has_col(table, column):
            bind.execute(sa.text(f"UPDATE {table} SET {column} = NULL"))
