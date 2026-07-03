"""Add sede_id to cms_sites (Axioma 3 — CMS dashboard multi-tenant)

Revision ID: 20260703_0001_cms_sites_sede_id
Revises: 20260702_0001_cms_section_types
Create Date: 2026-07-03 00:00:00

Añade ``sede_id`` a ``cms_sites`` para que el dashboard CMS pueda filtrar
métricas por sede. Todas las entidades CMS v2 (pages, posts, categories,
tags, menus, themes) tienen ``site_id`` FK; con ``sede_id`` en el sitio
padre, el scope por sede se resuelve vía JOIN sin necesidad de agregar
``sede_id`` a cada tabla hija.

Postgres-first con fallback SQLite (tests usan sqlite://). Idempotente
mediante checks ``information_schema``/``sa.inspect``.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260703_0001_cms_sites_sede_id"
down_revision: Union[str, None] = "20260702_0001_cms_section_types"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ── Helpers (Postgres-aware, SQLite-safe) ─────────────────────────────────


def _inspector():
    return sa.inspect(op.get_bind())


def _has_table(table: str) -> bool:
    return table in set(_inspector().get_table_names())


def _has_column(table: str, column: str) -> bool:
    if not _has_table(table):
        return False
    return any(
        col.get("name") == column for col in _inspector().get_columns(table)
    )


def _has_index(table: str, index_name: str) -> bool:
    if not _has_table(table):
        return False
    return any(
        idx.get("name") == index_name for idx in _inspector().get_indexes(table)
    )


def _uuid_type():
    """UUID portable: postgresql.UUID en Postgres, String(36) en SQLite/otros."""
    if op.get_bind().dialect.name == "postgresql":
        return postgresql.UUID(as_uuid=True)
    return sa.String(36)


# ── Migration body ───────────────────────────────────────────────────────


def upgrade() -> None:
    if not _has_table("cms_sites"):
        return

    if not _has_column("cms_sites", "sede_id"):
        with op.batch_alter_table("cms_sites") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "sede_id",
                    _uuid_type(),
                    sa.ForeignKey("sedes.id", ondelete="SET NULL"),
                    nullable=True,
                )
            )

    idx_name = "ix_cms_sites_sede_id"
    if not _has_index("cms_sites", idx_name):
        op.create_index(idx_name, "cms_sites", ["sede_id"], unique=False)


def downgrade() -> None:
    if not _has_table("cms_sites"):
        return

    idx_name = "ix_cms_sites_sede_id"
    if _has_index("cms_sites", idx_name):
        op.drop_index(idx_name, table_name="cms_sites")

    if _has_column("cms_sites", "sede_id"):
        with op.batch_alter_table("cms_sites") as batch_op:
            batch_op.drop_column("sede_id")
