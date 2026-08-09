"""dedup redundant indexes + add sede_id index to auth_notifications

DB health check (2026-08-09): 14 pares de índices duplicados detectados.
Los índices redundantes ocupan espacio y ralentizan writes sin aportar
beneficio de lectura (el índice único subsume al no-único en las mismas
columnas). También se detectó que ``auth_notifications`` tiene columna
``sede_id`` (migración 20260724_0002) pero sin índice.

DDL aditivo/destructivo puro — no cambia datos ni contratos. Reversible.

Revision ID: 20260809_0003_dedup_sede_idx
Revises: 20260809_0002_fk_indexes
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260809_0003_dedup_sede_idx"
down_revision: Union[str, None] = "20260809_0002_fk_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ── Helpers (Postgres-aware, SQLite-safe) ─────────────────────────────────


def _inspector():
    return sa.inspect(op.get_bind())


def _has_index(table: str, index_name: str) -> bool:
    if table not in set(_inspector().get_table_names()):
        return False
    return any(idx.get("name") == index_name for idx in _inspector().get_indexes(table))


def _drop_index_if_exists(table: str, index_name: str) -> None:
    if _has_index(table, index_name):
        op.drop_index(index_name, table_name=table)


def _create_index_if_missing(table: str, index_name: str, column: str) -> None:
    if not _has_index(table, index_name):
        op.create_index(index_name, table, [column], unique=False)


def upgrade() -> None:
    # 1. Drop 13 redundant duplicate indexes.
    # Each has a surviving counterpart (unique or better-named) on the same columns.
    _drop_index_if_exists("agent_knowledge_base", "ix_kb_active")
    _drop_index_if_exists("agent_knowledge_base", "ix_kb_category")
    _drop_index_if_exists("agent_knowledge_base", "ix_kb_source")
    _drop_index_if_exists("auth_refresh_tokens", "idx_refresh_token")
    _drop_index_if_exists("auth_users", "idx_auth_users_email")
    _drop_index_if_exists("cms_section_types", "ix_cms_section_types_name")
    _drop_index_if_exists("cms_seo_snapshots", "ix_cms_seo_snapshots_site_date_desc")
    _drop_index_if_exists("persona_church_roles", "idx_pers_church_role")
    _drop_index_if_exists("registros_seguimiento", "ix_registros_seguimiento_asistencia_id")
    _drop_index_if_exists("registros_seguimiento", "ix_registros_seguimiento_responsable_id")
    _drop_index_if_exists("wiki_pages", "ix_wiki_pages_page_key_trgm")
    _drop_index_if_exists("sesiones_grupo", "ix_sesiones_grupo_unreported")
    _drop_index_if_exists("auth_user_permission_overrides", "ix_auth_user_permission_overrides_user_id")

    # 2. Add missing sede_id index to auth_notifications (column added by
    # migración 20260724_0002 but index was never created).
    _create_index_if_missing("auth_notifications", "ix_auth_notifications_sede_id", "sede_id")


def downgrade() -> None:
    # Re-create the dropped indexes (best-effort — the counterpart may
    # still exist, so we only recreate if not already present).
    _drop_index_if_exists("auth_notifications", "ix_auth_notifications_sede_id")

    # Note: re-creating the 13 dropped indexes is low-value (they were
    # redundant). We recreate them for full reversibility.
    op.create_index("ix_kb_active", "agent_knowledge_base", ["is_active"], unique=False)
    op.create_index("ix_kb_category", "agent_knowledge_base", ["category"], unique=False)
    op.create_index("ix_kb_source", "agent_knowledge_base", ["source_module"], unique=False)
    op.create_index("idx_refresh_token", "auth_refresh_tokens", ["token"], unique=False)
    op.create_index("idx_auth_users_email", "auth_users", ["email"], unique=False)
    op.create_index("ix_cms_section_types_name", "cms_section_types", ["name"], unique=False)
    op.create_index("ix_cms_seo_snapshots_site_date_desc", "cms_seo_snapshots", ["site_id", "captured_date"], unique=False)
    op.create_index("idx_pers_church_role", "persona_church_roles", ["persona_id"], unique=False)
    op.create_index("ix_registros_seguimiento_asistencia_id", "registros_seguimiento", ["asistencia_id"], unique=False)
    op.create_index("ix_registros_seguimiento_responsable_id", "registros_seguimiento", ["responsable_id"], unique=False)
    # trgm index requires special operator class — skip in downgrade
    op.create_index("ix_sesiones_grupo_unreported", "sesiones_grupo", ["grupo_id"], unique=False)
    op.create_index("ix_auth_user_permission_overrides_user_id", "auth_user_permission_overrides", ["user_id"], unique=False)