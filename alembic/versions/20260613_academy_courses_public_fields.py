"""Add public-facing fields to academy_courses for /cursos page

Revision ID: 20260613_academy_public_fields
Revises: c4d5e6f7a8b9
Create Date: 2026-06-13

Agrega slug (único, para URLs), excerpt, tag, cta_text, syllabus (JSON),
e instructor_name a academy_courses. Permite que la API pública exponga
cursos con toda la información que el frontend /cursos necesita sin depender
de datos hardcodeados.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260613_academy_public_fields"
down_revision: Union[str, None] = "c4d5e6f7a8b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _col_exists(table: str, col: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name=:t AND column_name=:c"
        ),
        {"t": table, "c": col},
    )
    return result.fetchone() is not None


def upgrade() -> None:
    cols = [
        ("slug", sa.String(200)),
        ("excerpt", sa.Text),
        ("tag", sa.String(100)),
        ("cta_text", sa.String(100)),
        ("syllabus", sa.JSON),
        ("instructor_name", sa.String(200)),
    ]
    for col_name, col_type in cols:
        if not _col_exists("academy_courses", col_name):
            op.add_column("academy_courses", sa.Column(col_name, col_type, nullable=True))

    # Índice único en slug (solo para filas no nulas)
    conn = op.get_bind()
    idx_exists = conn.execute(
        sa.text(
            "SELECT 1 FROM pg_indexes WHERE tablename='academy_courses' "
            "AND indexname='ix_academy_courses_slug'"
        )
    ).fetchone()
    if not idx_exists:
        op.create_index(
            "ix_academy_courses_slug",
            "academy_courses",
            ["slug"],
            unique=True,
            postgresql_where=sa.text("slug IS NOT NULL"),
        )


def downgrade() -> None:
    op.drop_index("ix_academy_courses_slug", table_name="academy_courses")
    for col_name in ["slug", "excerpt", "tag", "cta_text", "syllabus", "instructor_name"]:
        op.drop_column("academy_courses", col_name)
