"""Add payload_json column to academy_activity_logs.

Revision ID: 20260718_0002
Revises: 20260718_0001
Create Date: 2026-07-18

ACAD-MED-003-FOLLOWUP: el endpoint ``DELETE /admin/submissions/{id}`` archivaba
(soft delete) entregas, pero ``AcademyActivityLog.modality`` es ``String(20)`` y
no admite el ``file_url`` completo. Esta migración añade ``payload_json``
(:class:`sqlalchemy.JSON`, nullable) para preservar metadatos del archivado.

El job batch de purga de Seaweed consultará por ``event_type =
'assignment_submission_archived'`` (columna ya indexada) y leerá los campos
``file_url``/``lesson_id``/``enrollment_id``/``archived_at`` desde el JSON.

No se añade índice sobre ``payload_json`` porque SQLAlchemy ``JSON`` no es
JSONB (Regla 8) y los índices sobre JSON requerirían ``gin``/``jsonb_path_ops``
no portables. La columna ``event_type`` ya está indexada, por lo que la
búsqueda directa por ``event_type`` es eficiente.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260718_0002"
down_revision = "20260718_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "academy_activity_logs",
        sa.Column("payload_json", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("academy_activity_logs", "payload_json")
