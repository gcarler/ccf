"""add_missing_indexes

Revision ID: 20260602_add_missing_indexes
Revises: 20260528_0053
Create Date: 2026-06-02

Crea índices B-Tree en FKs frecuentes sin índice (Capa D — Performance).
Usa CREATE INDEX CONCURRENTLY IF NOT EXISTS para evitar bloqueos de escritura.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260602_add_missing_idx"
down_revision: Union[str, None] = "20260528_0053"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _index_exists(name: str) -> bool:
    conn = op.get_bind()
    r = conn.execute(
        sa.text("SELECT count(*) FROM pg_indexes WHERE indexname = :n"),
        {"n": name},
    )
    return r.scalar() > 0


INDEXES = [
    ("ix_academy_lessons_course_id", "academy_lessons", "course_id"),
    ("ix_academy_assessments_course_id", "academy_assessments", "course_id"),
    ("ix_academy_assessments_lesson_id", "academy_assessments", "lesson_id"),
    ("ix_academy_assessment_questions_assessment_id", "academy_assessment_questions", "assessment_id"),
    ("ix_academy_assignment_submissions_enrollment_id", "academy_assignment_submissions", "enrollment_id"),
    ("ix_academy_assignment_submissions_lesson_id", "academy_assignment_submissions", "lesson_id"),
    ("ix_dependencias_tareas_tarea_bloqueante_id", "dependencias_tareas", "tarea_bloqueante_id"),
    ("ix_dependencias_tareas_tarea_bloqueada_id", "dependencias_tareas", "tarea_bloqueada_id"),
    ("ix_comentarios_tarea_tarea_id", "comentarios_tarea", "tarea_id"),
    ("ix_comentarios_tarea_persona_id", "comentarios_tarea", "persona_id"),
    ("ix_documentos_proyecto_proyecto_id", "documentos_proyecto", "proyecto_id"),
    ("ix_documentos_proyecto_tarea_id", "documentos_proyecto", "tarea_id"),
]


def upgrade() -> None:
    conn = op.get_bind()
    for idx_name, table, column in INDEXES:
        if not _index_exists(idx_name):
            conn.execute(
                sa.text(
                    f"CREATE INDEX IF NOT EXISTS {idx_name} "
                    f"ON {table} ({column})"
                )
            )


def downgrade() -> None:
    conn = op.get_bind()
    for idx_name, table, _ in INDEXES:
        if _index_exists(idx_name):
            conn.execute(sa.text(f"DROP INDEX IF EXISTS {idx_name}"))
