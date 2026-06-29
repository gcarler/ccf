"""add sede_id to cms media / testimonials / announcements (Axioma 3 Fase 5)

Revision ID: 20260701_0001_cms_content_sede_id
Revises: 20260627_0011_canonical_crm_tasks
Create Date: 2026-07-01 00:00:00

Cierra las brechas multi-tenant restantes en Content User-Generated del CMS:
  - ``cms_media_items``         → ``sede_id`` (backfill: ``created_by_persona.sede_id``)
  - ``testimonials``            → ``sede_id`` (backfill: ``author_persona.sede_id``)
  - ``announcements``           → ``sede_id`` + ``created_by_persona_id``
                                  (no creator persona previo, NULL aceptable)

Las nuevas columnas son ``nullable=True`` (no-fatal con datos legacy + admin
override). La defense-in-depth del CRUD/API layer trabaja con el axioma
"actor con sede ⇒ sede_id del row debe matchear".

Postgres-first con fallback SQLite (tests usan sqlite://). Idempotente
mediante checks ``information_schema``/``sa.inspect``.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260701_0001_cms_content_sede_id"
down_revision: Union[str, None] = "20260627_0011_crm_tasks"
# NOTE: el archivo del predecessor lleva sufijo ``_canonical_crm_tasks`` pero
# la variable revision EXPORTADA es ``20260627_0011_crm_tasks`` (sin
# ``canonical_``). El chain se mantiene linear via este revision id.
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


def _has_fk(table: str, fk_name: str) -> bool:
    if not _has_table(table):
        return False
    return any(
        fk.get("name") == fk_name for fk in _inspector().get_foreign_keys(table)
    )


def _uuid_type():
    """UUID portable: postgresql.UUID en Postgres, String(36) en SQLite/otros."""
    if op.get_bind().dialect.name == "postgresql":
        return postgresql.UUID(as_uuid=True)
    return sa.String(36)


def _add_sede_column(table: str) -> None:
    """Añade ``sede_id`` (UUID, nullable, FK a sedes.id) + índice B-Tree.

    Idempotente. Compatible con Postgres y SQLite.
    """
    if not _has_table(table):
        return
    if not _has_column(table, "sede_id"):
        with op.batch_alter_table(table) as batch_op:
            batch_op.add_column(
                sa.Column(
                    "sede_id",
                    _uuid_type(),
                    sa.ForeignKey("sedes.id", ondelete="SET NULL"),
                    nullable=True,
                )
            )

    idx_name = f"ix_{table}_sede_id"
    if not _has_index(table, idx_name):
        op.create_index(idx_name, table, ["sede_id"], unique=False)


def _add_created_by_column(table: str) -> None:
    """Añade ``created_by_persona_id`` (UUID, nullable, FK a personas.id) +
    índice B-Tree. Idempotente.
    """
    if not _has_table(table):
        return
    if not _has_column(table, "created_by_persona_id"):
        with op.batch_alter_table(table) as batch_op:
            batch_op.add_column(
                sa.Column(
                    "created_by_persona_id",
                    _uuid_type(),
                    sa.ForeignKey("personas.id", ondelete="SET NULL"),
                    nullable=True,
                )
            )

    idx_name = f"ix_{table}_created_by_persona_id"
    if not _has_index(table, idx_name):
        op.create_index(idx_name, table, ["created_by_persona_id"], unique=False)


def _backfill_sede_from_creator_fk(table: str, creator_col: str) -> None:
    """``UPDATE table SET sede_id = creator.sede_id`` cuando sede_id IS NULL.

    Solo Postgres (no SQLite en tests pre-existentes, pero dejamos
    fallback SQL-portable). Si ``personas`` no existe o la columna ya
    tiene datos, se sale silenciosamente.
    """
    if not (_has_table(table) and _has_table("personas")):
        return
    if not (_has_column(table, "sede_id") and _has_column(table, creator_col)):
        return
    if not _has_column("personas", "sede_id"):
        return

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        bind.execute(
            sa.text(
                f"UPDATE {table} AS t "
                f"SET sede_id = p.sede_id "
                f"FROM personas AS p "
                f"WHERE t.{creator_col}::text = p.id::text "
                f"AND p.sede_id IS NOT NULL "
                f"AND t.sede_id IS NULL"
            )
        )
    else:
        # SQLite-portable: subquery join (sintaxis distinta a Postgres).
        bind.execute(
            sa.text(
                f"UPDATE {table} "
                f"SET sede_id = ("
                f"  SELECT p.sede_id FROM personas p "
                f"  WHERE p.id::text = {table}.{creator_col}::text"
                f") "
                f"WHERE sede_id IS NULL "
                f"AND {creator_col} IS NOT NULL "
                f"AND EXISTS ("
                f"  SELECT 1 FROM personas p "
                f"  WHERE p.id::text = {table}.{creator_col}::text "
                f"  AND p.sede_id IS NOT NULL"
                f")"
            )
        )


# ── Migration body ───────────────────────────────────────────────────────


def upgrade() -> None:
    # 1. cms_media_items.sede_id (backfill desde created_by_persona_id)
    _add_sede_column("cms_media_items")
    _backfill_sede_from_creator_fk("cms_media_items", "created_by_persona_id")

    # 2. testimonials.sede_id (backfill desde author_persona_id)
    _add_sede_column("testimonials")
    _backfill_sede_from_creator_fk("testimonials", "author_persona_id")

    # 3. announcements.sede_id + announcements.created_by_persona_id
    #    (no backfill posible: announcements pre-migration no tienen FK a
    #    persona. Rows legacy con sede_id NULL son visibles sólo a
    #    superadmins sin sede — comportamiento consistente con Axioma 3
    #    sobre orphans en otras entidades.)
    _add_sede_column("announcements")
    _add_created_by_column("announcements")


def downgrade() -> None:
    bind = op.get_bind()

    # announcements: drop columnas en orden inverso (FKs primero).
    if _has_table("announcements"):
        for col in ("created_by_persona_id", "sede_id"):
            idx_name = f"ix_announcements_{col}"
            if _has_index("announcements", idx_name):
                op.drop_index(idx_name, table_name="announcements")
            if _has_column("announcements", col):
                with op.batch_alter_table("announcements") as batch_op:
                    batch_op.drop_column(col)

    # testimonials / cms_media_items: solo sede_id.
    for table in ("testimonials", "cms_media_items"):
        if not _has_table(table):
            continue
        idx_name = f"ix_{table}_sede_id"
        if _has_index(table, idx_name):
            op.drop_index(idx_name, table_name=table)
        if _has_column(table, "sede_id"):
            with op.batch_alter_table(table) as batch_op:
                batch_op.drop_column("sede_id")

    if bind.dialect.name == "postgresql":
        bind.execute(sa.text("SELECT 1"))  # noop; kept for explicitness
