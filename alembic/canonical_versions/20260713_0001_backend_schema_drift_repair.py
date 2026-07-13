"""backend_schema_drift_repair

Revision ID: 20260713_0001
Revises: 20260710_0002
Create Date: 2026-07-13

Idempotent additive repair for production drift found by
``scripts/audit_backend_schema.py``. This migration intentionally does not
drop extra live columns.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260713_0001"
down_revision: Union[str, None] = "20260710_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _uuid_type() -> sa.types.TypeEngine:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        return postgresql.UUID(as_uuid=True)
    return sa.String(length=36)


def _table_exists(table: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table)


def _col_exists(table: str, column: str) -> bool:
    if not _table_exists(table):
        return False
    return column in {col["name"] for col in sa.inspect(op.get_bind()).get_columns(table)}


def _add_column_if_missing(table: str, column: sa.Column) -> None:
    if _table_exists(table) and not _col_exists(table, column.name):
        op.add_column(table, column)


def _index_exists(table: str, index: str) -> bool:
    if not _table_exists(table):
        return False
    return index in {idx["name"] for idx in sa.inspect(op.get_bind()).get_indexes(table)}


def upgrade() -> None:
    uuid_t = _uuid_type()

    _add_column_if_missing("crm_plantillas_mensaje", sa.Column("contenido_html", sa.Text(), nullable=True))

    _add_column_if_missing("sesiones_grupo", sa.Column("novelty_type", sa.String(50), nullable=True))
    _add_column_if_missing("sesiones_grupo", sa.Column("novelty_detail", sa.Text(), nullable=True))
    _add_column_if_missing("sesiones_grupo", sa.Column("reported_by_persona_id", uuid_t, nullable=True))
    _add_column_if_missing("sesiones_grupo", sa.Column("report_deadline", sa.DateTime(timezone=True), nullable=True))

    _add_column_if_missing("crm_casos", sa.Column("drag_source_etapa_id", uuid_t, nullable=True))
    _add_column_if_missing("crm_casos", sa.Column("drag_target_etapa_id", uuid_t, nullable=True))
    _add_column_if_missing(
        "crm_casos",
        sa.Column("is_locked_for_reorder", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    _add_column_if_missing(
        "crm_casos",
        sa.Column("last_reorder_failed", sa.Boolean(), server_default=sa.false(), nullable=False),
    )

    _add_column_if_missing("crm_automation_edges", sa.Column("source_node_id", uuid_t, nullable=True))
    _add_column_if_missing("crm_automation_edges", sa.Column("target_node_id", uuid_t, nullable=True))
    _add_column_if_missing(
        "crm_automation_edges",
        sa.Column("on_delete_cascade", sa.Boolean(), server_default=sa.true(), nullable=True),
    )

    _add_column_if_missing("event_assignments", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    _add_column_if_missing("persona_church_roles", sa.Column("assigned_by_persona_id", uuid_t, nullable=True))
    _add_column_if_missing("project_whiteboards", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))

    if not _table_exists("public_contact_submissions"):
        op.create_table(
            "public_contact_submissions",
            sa.Column("id", uuid_t, primary_key=True),
            sa.Column("name", sa.String(200), nullable=False),
            sa.Column("email", sa.String(255), nullable=False),
            sa.Column("phone", sa.String(50), nullable=True),
            sa.Column("message", sa.Text(), nullable=True),
            sa.Column("status", sa.String(20), server_default="new", nullable=True),
            sa.Column("sede_id", uuid_t, nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_public_contact_submissions_status", "public_contact_submissions", ["status"])
        op.create_index("ix_public_contact_submissions_sede_id", "public_contact_submissions", ["sede_id"])


def downgrade() -> None:
    for table, column in [
        ("project_whiteboards", "deleted_at"),
        ("persona_church_roles", "assigned_by_persona_id"),
        ("event_assignments", "deleted_at"),
        ("crm_automation_edges", "on_delete_cascade"),
        ("crm_automation_edges", "target_node_id"),
        ("crm_automation_edges", "source_node_id"),
        ("crm_casos", "last_reorder_failed"),
        ("crm_casos", "is_locked_for_reorder"),
        ("crm_casos", "drag_target_etapa_id"),
        ("crm_casos", "drag_source_etapa_id"),
        ("sesiones_grupo", "report_deadline"),
        ("sesiones_grupo", "reported_by_persona_id"),
        ("sesiones_grupo", "novelty_detail"),
        ("sesiones_grupo", "novelty_type"),
        ("crm_plantillas_mensaje", "contenido_html"),
    ]:
        if _col_exists(table, column):
            op.drop_column(table, column)

    if _table_exists("public_contact_submissions"):
        if _index_exists("public_contact_submissions", "ix_public_contact_submissions_sede_id"):
            op.drop_index("ix_public_contact_submissions_sede_id", table_name="public_contact_submissions")
        if _index_exists("public_contact_submissions", "ix_public_contact_submissions_status"):
            op.drop_index("ix_public_contact_submissions_status", table_name="public_contact_submissions")
        op.drop_table("public_contact_submissions")
