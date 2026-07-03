"""Drop the empty, unprefixed Academy table tree.

Revision ID: 20260627_0002_drop_academy
Revises: 20260627_0001_academy
"""

from typing import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260627_0002_drop_academy"
down_revision: str | None = "20260627_0001_academy"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


LEGACY_TABLES = [
    "assessment_answers",
    "course_attendance",
    "certificates",
    "assignment_submissions",
    "resources",
    "lesson_progress",
    "assessment_attempts",
    "assessment_options",
    "assessment_questions",
    "formal_actas",
    "forum_comments",
    "forum_threads",
    "enrollments",
    "assessments",
    "course_prerequisites",
    "lessons",
    "courses",
]


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names())
    populated = []
    for table in LEGACY_TABLES:
        if table in existing:
            count = bind.execute(sa.text(f'SELECT count(*) FROM "{table}"')).scalar_one()
            if count:
                populated.append(f"{table}={count}")
    if populated:
        raise RuntimeError(
            "Parallel Academy tables contain data; migration stopped: " + ", ".join(populated)
        )
    for table in LEGACY_TABLES:
        if table in existing:
            op.drop_table(table)


def downgrade() -> None:
    uuid = postgresql.UUID(as_uuid=True)
    timestamp = sa.DateTime(timezone=True)

    op.create_table(
        "courses",
        sa.Column("id", uuid, nullable=False),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("modality", sa.String(20), nullable=False),
        sa.Column("is_published", sa.Boolean(), nullable=True),
        sa.Column("is_self_paced", sa.Boolean(), nullable=True),
        sa.Column("duration_hours", sa.Integer(), nullable=True),
        sa.Column("cohort_name", sa.String(100), nullable=True),
        sa.Column("certificate_type", sa.String(50), nullable=True),
        sa.Column("xp_per_lesson", sa.Integer(), nullable=True),
        sa.Column("image_url", sa.String(500), nullable=True),
        sa.Column("instructor_name", sa.String(200), nullable=True),
        sa.Column("sede_id", uuid, nullable=True),
        sa.Column("created_at", timestamp, nullable=True),
        sa.ForeignKeyConstraint(["sede_id"], ["sedes.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_table(
        "lessons",
        sa.Column("id", uuid, nullable=False),
        sa.Column("course_id", uuid, nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_type", sa.String(50), nullable=True),
        sa.Column("media_url", sa.String(255), nullable=True),
        sa.Column("order_index", sa.Integer(), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "course_prerequisites",
        sa.Column("id", uuid, nullable=False),
        sa.Column("course_id", uuid, nullable=False),
        sa.Column("prerequisite_course_id", uuid, nullable=False),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"]),
        sa.ForeignKeyConstraint(["prerequisite_course_id"], ["courses.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("course_id", "prerequisite_course_id", name="uq_course_prerequisite_pair"),
    )
    op.create_table(
        "assessments",
        sa.Column("id", uuid, nullable=False),
        sa.Column("lesson_id", uuid, nullable=False),
        sa.Column("course_id", uuid, nullable=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("min_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("weight", sa.Numeric(5, 2), nullable=True),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"]),
        sa.ForeignKeyConstraint(["lesson_id"], ["lessons.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "assessment_questions",
        sa.Column("id", uuid, nullable=False),
        sa.Column("assessment_id", uuid, nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("question_type", sa.String(20), nullable=True),
        sa.Column("points", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["assessment_id"], ["assessments.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "assessment_options",
        sa.Column("id", uuid, nullable=False),
        sa.Column("question_id", uuid, nullable=False),
        sa.Column("option_text", sa.Text(), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(["question_id"], ["assessment_questions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "enrollments",
        sa.Column("id", uuid, nullable=False),
        sa.Column("persona_id", uuid, nullable=True),
        sa.Column("course_id", uuid, nullable=False),
        sa.Column("status", sa.String(20), nullable=True),
        sa.Column("progress_percent", sa.Float(), nullable=True),
        sa.Column("final_grade", sa.Float(), nullable=True),
        sa.Column("attendance_percent", sa.Float(), nullable=True),
        sa.Column("lessons_completed", postgresql.JSONB(), nullable=True),
        sa.Column("approved", sa.Boolean(), nullable=True),
        sa.Column("acta_closed", sa.Boolean(), nullable=True),
        sa.Column("certificate_issued", sa.Boolean(), nullable=True),
        sa.Column("certificate_code", sa.String(64), nullable=True),
        sa.Column("access_window_end", timestamp, nullable=True),
        sa.Column("completed_at", timestamp, nullable=True),
        sa.Column("created_at", timestamp, nullable=False),
        sa.Column("updated_at", timestamp, nullable=False),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"]),
        sa.ForeignKeyConstraint(["persona_id"], ["personas.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("persona_id", "course_id", name="uq_persona_course"),
    )
    op.create_table(
        "lesson_progress",
        sa.Column("id", uuid, nullable=False),
        sa.Column("persona_id", uuid, nullable=True),
        sa.Column("lesson_id", uuid, nullable=False),
        sa.Column("progress_percent", sa.Numeric(5, 2), nullable=True),
        sa.Column("last_position_seconds", sa.Integer(), nullable=True),
        sa.Column("is_completed", sa.Boolean(), nullable=True),
        sa.Column("updated_at", timestamp, nullable=True),
        sa.ForeignKeyConstraint(["lesson_id"], ["lessons.id"]),
        sa.ForeignKeyConstraint(["persona_id"], ["personas.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("persona_id", "lesson_id", name="uq_persona_lesson_progress"),
    )
    op.create_table(
        "assessment_attempts",
        sa.Column("id", uuid, nullable=False),
        sa.Column("enrollment_id", uuid, nullable=False),
        sa.Column("assessment_id", uuid, nullable=False),
        sa.Column("score", sa.Numeric(5, 2), nullable=True),
        sa.Column("passed", sa.Boolean(), nullable=True),
        sa.Column("created_at", timestamp, nullable=True),
        sa.ForeignKeyConstraint(["assessment_id"], ["assessments.id"]),
        sa.ForeignKeyConstraint(["enrollment_id"], ["enrollments.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "assessment_answers",
        sa.Column("id", uuid, nullable=False),
        sa.Column("attempt_id", uuid, nullable=False),
        sa.Column("question_id", uuid, nullable=False),
        sa.Column("selected_option_id", uuid, nullable=True),
        sa.Column("text_response", sa.Text(), nullable=True),
        sa.Column("is_correct", sa.Boolean(), nullable=True),
        sa.Column("points_awarded", sa.Numeric(5, 2), nullable=True),
        sa.ForeignKeyConstraint(["attempt_id"], ["assessment_attempts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["question_id"], ["assessment_questions.id"]),
        sa.ForeignKeyConstraint(["selected_option_id"], ["assessment_options.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "resources",
        sa.Column("id", uuid, nullable=False),
        sa.Column("lesson_id", uuid, nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("file_url", sa.String(500), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=True),
        sa.ForeignKeyConstraint(["lesson_id"], ["lessons.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "assignment_submissions",
        sa.Column("id", uuid, nullable=False),
        sa.Column("enrollment_id", uuid, nullable=False),
        sa.Column("lesson_id", uuid, nullable=False),
        sa.Column("file_url", sa.String(500), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("grade", sa.Numeric(5, 2), nullable=True),
        sa.Column("teacher_feedback", sa.Text(), nullable=True),
        sa.Column("created_at", timestamp, nullable=True),
        sa.ForeignKeyConstraint(["enrollment_id"], ["enrollments.id"]),
        sa.ForeignKeyConstraint(["lesson_id"], ["lessons.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "formal_actas",
        sa.Column("id", uuid, nullable=False),
        sa.Column("course_id", uuid, nullable=False),
        sa.Column("closed_by_persona_id", uuid, nullable=True),
        sa.Column("status", sa.String(20), nullable=True),
        sa.Column("min_grade_required", sa.Numeric(5, 2), nullable=True),
        sa.Column("min_attendance_required", sa.Numeric(5, 2), nullable=True),
        sa.Column("created_at", timestamp, nullable=True),
        sa.ForeignKeyConstraint(["closed_by_persona_id"], ["personas.id"]),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "forum_threads",
        sa.Column("id", uuid, nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("author_persona_id", uuid, nullable=False),
        sa.Column("is_resolved", sa.Boolean(), nullable=True),
        sa.Column("created_at", timestamp, nullable=True),
        sa.Column("updated_at", timestamp, nullable=True),
        sa.ForeignKeyConstraint(["author_persona_id"], ["personas.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "forum_comments",
        sa.Column("id", uuid, nullable=False),
        sa.Column("thread_id", uuid, nullable=False),
        sa.Column("author_persona_id", uuid, nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", timestamp, nullable=True),
        sa.ForeignKeyConstraint(["author_persona_id"], ["personas.id"]),
        sa.ForeignKeyConstraint(["thread_id"], ["forum_threads.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "course_attendance",
        sa.Column("id", uuid, nullable=False),
        sa.Column("enrollment_id", uuid, nullable=False),
        sa.Column("session_date", timestamp, nullable=True),
        sa.Column("status", sa.String(20), nullable=True),
        sa.Column("recorded_by_persona_id", uuid, nullable=True),
        sa.ForeignKeyConstraint(["enrollment_id"], ["enrollments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recorded_by_persona_id"], ["personas.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "certificates",
        sa.Column("id", uuid, nullable=False),
        sa.Column("enrollment_id", uuid, nullable=False),
        sa.Column("certificate_code", sa.String(64), nullable=False),
        sa.Column("issued_at", timestamp, nullable=True),
        sa.ForeignKeyConstraint(["enrollment_id"], ["enrollments.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("certificate_code"),
    )
