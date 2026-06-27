"""Align academy_* tables with the single Academy contract.

Revision ID: 20260627_0001_academy
Revises: 20260626_0002_persona_names
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260627_0001_academy"
down_revision: str | None = "20260626_0002_persona_names"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_table(table: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table)


def _has_column(table: str, column: str) -> bool:
    if not _has_table(table):
        return False
    return column in {item["name"] for item in sa.inspect(op.get_bind()).get_columns(table)}


def _add_column(table: str, column: sa.Column) -> None:
    if not _has_column(table, column.name):
        op.add_column(table, column)


def _drop_column(table: str, column: str) -> None:
    if _has_column(table, column):
        op.drop_column(table, column)


def upgrade() -> None:
    _add_column("academy_courses", sa.Column("cohort_name", sa.String(100), nullable=True))
    _add_column("academy_courses", sa.Column("certificate_type", sa.String(50), nullable=True))

    _add_column(
        "academy_lessons",
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    _add_column(
        "academy_lessons",
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    _add_column(
        "academy_assessments",
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    _add_column(
        "academy_assessments",
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    _add_column("academy_assessments", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    _add_column(
        "academy_assessment_questions",
        sa.Column("order_index", sa.Integer(), server_default="0", nullable=False),
    )

    enrollment_columns = [
        sa.Column("lessons_completed", postgresql.JSONB(), nullable=True),
        sa.Column("certificate_issued", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("certificate_code", sa.String(64), nullable=True),
        sa.Column("access_window_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]
    for column in enrollment_columns:
        _add_column("academy_enrollments", column)

    _add_column(
        "academy_lesson_progress",
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    _add_column("academy_assignment_submissions", sa.Column("comment", sa.Text(), nullable=True))
    if _has_column("academy_assignment_submissions", "seaweed_fid"):
        op.alter_column(
            "academy_assignment_submissions",
            "seaweed_fid",
            existing_type=sa.String(100),
            type_=sa.String(500),
            existing_nullable=False,
        )

    _add_column(
        "academy_formal_actas",
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    if _has_column("academy_forum_threads", "course_id"):
        op.alter_column(
            "academy_forum_threads",
            "course_id",
            existing_type=postgresql.UUID(as_uuid=True),
            nullable=True,
        )
    _add_column(
        "academy_forum_threads",
        sa.Column("category", sa.String(50), server_default="general", nullable=False),
    )
    _add_column(
        "academy_forum_threads",
        sa.Column("is_resolved", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    _add_column(
        "academy_forum_threads",
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    if _has_column("academy_course_attendance", "recorded_by_persona_id"):
        op.alter_column(
            "academy_course_attendance",
            "recorded_by_persona_id",
            existing_type=postgresql.UUID(as_uuid=True),
            nullable=True,
        )

    if not _has_table("academy_assessment_answers"):
        op.create_table(
            "academy_assessment_answers",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("attempt_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("question_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("selected_option_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("text_response", sa.Text(), nullable=True),
            sa.Column("is_correct", sa.Boolean(), nullable=True),
            sa.Column("points_awarded", sa.Numeric(5, 2), server_default="0", nullable=True),
            sa.ForeignKeyConstraint(
                ["attempt_id"], ["academy_assessment_attempts.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(["question_id"], ["academy_assessment_questions.id"]),
            sa.ForeignKeyConstraint(["selected_option_id"], ["academy_assessment_options.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_academy_assessment_answers_attempt_id",
            "academy_assessment_answers",
            ["attempt_id"],
        )

    if not _has_table("academy_resources"):
        op.create_table(
            "academy_resources",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("lesson_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("title", sa.String(200), nullable=False),
            sa.Column("file_url", sa.String(500), nullable=False),
            sa.Column("resource_type", sa.String(50), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["lesson_id"], ["academy_lessons.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_academy_resources_lesson_id", "academy_resources", ["lesson_id"])

    inspector = sa.inspect(op.get_bind())
    activity_fks = {
        fk["name"]: fk for fk in inspector.get_foreign_keys("academy_activity_logs")
    }
    old_fk = activity_fks.get("academy_activity_logs_course_id_fkey")
    if old_fk and old_fk.get("referred_table") == "courses":
        op.drop_constraint(
            "academy_activity_logs_course_id_fkey",
            "academy_activity_logs",
            type_="foreignkey",
        )
        op.create_foreign_key(
            "fk_academy_activity_logs_course_id",
            "academy_activity_logs",
            "academy_courses",
            ["course_id"],
            ["id"],
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    fk_names = {fk["name"] for fk in inspector.get_foreign_keys("academy_activity_logs")}
    if "fk_academy_activity_logs_course_id" in fk_names:
        op.drop_constraint(
            "fk_academy_activity_logs_course_id", "academy_activity_logs", type_="foreignkey"
        )
        if _has_table("courses"):
            op.create_foreign_key(
                "academy_activity_logs_course_id_fkey",
                "academy_activity_logs",
                "courses",
                ["course_id"],
                ["id"],
            )

    if _has_table("academy_resources"):
        op.drop_table("academy_resources")
    if _has_table("academy_assessment_answers"):
        op.drop_table("academy_assessment_answers")

    _drop_column("academy_forum_threads", "updated_at")
    _drop_column("academy_forum_threads", "is_resolved")
    _drop_column("academy_forum_threads", "category")
    if _has_column("academy_forum_threads", "course_id"):
        op.alter_column(
            "academy_forum_threads",
            "course_id",
            existing_type=postgresql.UUID(as_uuid=True),
            nullable=False,
        )
    if _has_column("academy_course_attendance", "recorded_by_persona_id"):
        op.alter_column(
            "academy_course_attendance",
            "recorded_by_persona_id",
            existing_type=postgresql.UUID(as_uuid=True),
            nullable=False,
        )
    _drop_column("academy_formal_actas", "created_at")
    if _has_column("academy_assignment_submissions", "seaweed_fid"):
        op.alter_column(
            "academy_assignment_submissions",
            "seaweed_fid",
            existing_type=sa.String(500),
            type_=sa.String(100),
            existing_nullable=False,
        )
    _drop_column("academy_assignment_submissions", "comment")
    _drop_column("academy_lesson_progress", "updated_at")
    for column in [
        "updated_at",
        "created_at",
        "access_window_end",
        "certificate_code",
        "certificate_issued",
        "lessons_completed",
    ]:
        _drop_column("academy_enrollments", column)
    _drop_column("academy_assessment_questions", "order_index")
    for column in ["deleted_at", "updated_at", "created_at"]:
        _drop_column("academy_assessments", column)
    for column in ["updated_at", "created_at"]:
        _drop_column("academy_lessons", column)
    for column in ["certificate_type", "cohort_name"]:
        _drop_column("academy_courses", column)
