"""Add deleted_at column to academy_assignment_submissions.

Revision ID: 20260718_0003
Revises: 20260718_0002
Create Date: 2026-07-18

ACAD-MED-003-FOLLOWUP (cierre): ``AssignmentSubmission`` necesitaba un campo
``deleted_at`` para soportar el soft delete controlado por
``delete_submission_admin`` sin romper la integridad referencial. Anteriormente
la columna no existía y el filtro ``AssignmentSubmission.deleted_at.is_(None)``
del endpoint retornaba 0 filas silenciosamente, devolviendo 404 incluso para
entregas válidas.

Esta migración:

1. Añade ``deleted_at`` (DateTime timezone, nullable=True, con índice).
2. Las filas existentes quedan con ``deleted_at = NULL`` (= "no archivada"),
   lo que es coherente con el estado en producción.
3. El ``AcademyActivityLog.payload_json`` (migration ``20260718_0002``)
   conserva ``file_url``/``lesson_id``/``enrollment_id`` para el job batch de
   purga de Seaweed que consultará por ``event_type = 'assignment_submission_archived'``.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260718_0003"
down_revision = "20260718_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "academy_assignment_submissions",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_academy_assignment_submissions_deleted_at",
        "academy_assignment_submissions",
        ["deleted_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_academy_assignment_submissions_deleted_at",
        table_name="academy_assignment_submissions",
    )
    op.drop_column("academy_assignment_submissions", "deleted_at")
