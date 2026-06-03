"""rename_legacy_tables

Revision ID: 20260602_rename_legacy
Revises: 20260602_add_sede_id
Create Date: 2026-06-02

Renombra tablas legacy con prefijo _legacy_ para aislarlas del hot-path
y evitar que el ORM las registre accidentalmente (Capa A — Limpieza).

⚠️ ADVERTENCIA: Solo renombra tablas LEGACY VACÍAS (entornos test/dev limpios).
En producción, ejecutar MANUALMENTE tras completar la migración de datos legacy→v2.

Downgrade revierte los nombres originales.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260602_rename_legacy"
down_revision: Union[str, None] = "20260602_add_sede_id"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


RENAME_PAIRS = [
    ("consolidation_cases", "_legacy_consolidation_cases"),
    ("cell_groups", "_legacy_cell_groups"),
    ("cell_group_sessions", "_legacy_cell_group_sessions"),
    ("courses", "_legacy_courses"),
    ("enrollments", "_legacy_enrollments"),
    ("projects", "_legacy_projects"),
    ("project_tasks", "_legacy_project_tasks"),
    ("users", "_legacy_users"),
    ("roles", "_legacy_roles"),
    ("agenda_events", "_legacy_agenda_events"),
]


def _table_exists(table: str) -> bool:
    conn = op.get_bind()
    r = conn.execute(
        sa.text(
            "SELECT count(*) FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = :t"
        ),
        {"t": table},
    )
    return r.scalar() > 0


def _table_has_rows(table: str) -> bool:
    conn = op.get_bind()
    if not _table_exists(table):
        return False
    r = conn.execute(sa.text(f"SELECT count(*) FROM {table}"))
    return (r.scalar() or 0) > 0


def upgrade() -> None:
    """Renombra tablas legacy SOLO si están vacías (test/dev limpio).

    En producción, ejecutar MANUALMENTE tras la migración de datos:
        DO $$ BEGIN
            ALTER TABLE projects RENAME TO _legacy_projects;
            -- ... etc
        END $$;
    """
    conn = op.get_bind()
    for old_name, new_name in RENAME_PAIRS:
        if not _table_exists(old_name):
            continue
        # Solo renombrar si la tabla legacy está vacía (indica entorno test/dev)
        # o si la tabla v2 ya existe con datos (migración completa)
        has_rows = _table_has_rows(old_name)
        v2_counterpart = None
        if old_name == "projects":
            v2_counterpart = "proyectos"
        elif old_name == "courses":
            v2_counterpart = "academy_courses"
        elif old_name == "enrollments":
            v2_counterpart = "academy_enrollments"
        elif old_name == "users":
            v2_counterpart = "auth_users"
        elif old_name == "roles":
            v2_counterpart = "auth_roles"

        v2_has_data = v2_counterpart and _table_has_rows(v2_counterpart)

        # Renombrar solo si: vacía (test) O v2 tiene datos (prod post-migración)
        if not has_rows and not _table_exists(new_name):
            conn.execute(
                sa.text(f'ALTER TABLE {old_name} RENAME TO "{new_name}"')
            )
        elif v2_has_data and not _table_exists(new_name):
            conn.execute(
                sa.text(f'ALTER TABLE {old_name} RENAME TO "{new_name}"')
            )


def downgrade() -> None:
    conn = op.get_bind()
    for old_name, new_name in RENAME_PAIRS:
        if _table_exists(new_name) and not _table_exists(old_name):
            conn.execute(
                sa.text(f'ALTER TABLE "{new_name}" RENAME TO "{old_name}"')
            )
