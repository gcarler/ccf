"""eradicate_compat_architecture

Revision ID: 476e020b8e2d
Revises: 018f0c02cd59
Create Date: 2026-06-11 11:31:48.083976

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '476e020b8e2d'
down_revision: Union[str, None] = '018f0c02cd59'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table: str) -> bool:
    conn = op.get_bind()
    return table in sa.inspect(conn).get_table_names()


def _has_col(table: str, column: str) -> bool:
    if not _table_exists(table):
        return False
    conn = op.get_bind()
    cols = [c["name"] for c in sa.inspect(conn).get_columns(table)]
    return column in cols


def _drop_column_if_exists(table: str, column: str) -> None:
    if not _table_exists(table):
        return
    if not _has_col(table, column):
        return
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        op.execute(f'ALTER TABLE "{table}" DROP COLUMN IF EXISTS "{column}" CASCADE')
    else:
        op.drop_column(table, column)


def _drop_table(table: str) -> None:
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
    else:
        op.execute(f"DROP TABLE IF EXISTS {table}")


def _drop_type(type_name: str) -> None:
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        op.execute(f"DROP TYPE IF EXISTS {type_name} CASCADE")


def _drop_function(func_name: str) -> None:
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        op.execute(f"DROP FUNCTION IF EXISTS {func_name} CASCADE")


def upgrade() -> None:
    # 1. Drop Spanish project tables and types
    _drop_table("dependencias_tareas")
    _drop_table("comentarios_tarea")
    _drop_table("documentos_proyecto")
    _drop_table("tareas_proyecto")
    _drop_table("equipo_proyecto")
    _drop_table("proyectos")
    _drop_type("estado_proyecto")
    _drop_type("estado_tarea")
    _drop_type("prioridad_tarea")
    _drop_type("tipo_dependencia")
    _drop_function("inyectar_historial_proyecto")

    # 2. Drop compat columns from active and potential compat tables
    tables_to_clean = [
        ("counseling_tickets", "pastor_user_id"),
        ("crm_tasks", "assignee_user_id"),
        ("communication_logs", "leader_user_id"),
        ("enrollments", "user_id"),
        ("lesson_progress", "user_id"),
        ("academy_activity_logs", "user_id"),
        ("formal_actas", "closed_by_user_id"),
        ("cms_media_items", "created_by"),
        ("cms_themes", "created_by"),
        ("cms_themes", "updated_by"),
        ("cms_pages", "created_by"),
        ("cms_pages", "updated_by"),
        ("cms_page_versions", "created_by"),
        ("cms_sections", "created_by"),
        ("cms_sections", "updated_by"),
        ("cms_publish_logs", "actor_user_id"),
        ("testimonials", "author_id"),
        ("agents", "created_by"),
        ("agents", "updated_by"),
        ("agent_roles", "created_by"),
        ("admin_audit_logs", "actor_user_id"),
        ("agent_conversations", "user_id"),
    ]

    for table, col in tables_to_clean:
        _drop_column_if_exists(table, col)
        _drop_column_if_exists(f"_compat_{table}", col)



def downgrade() -> None:
    pass
