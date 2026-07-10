"""add publish_at / expires_at to cms_pages and cms_posts

Revision ID: 20260706_0001_cms_schedule
Revises: 20260703_0002_rename_faro_site_key
Create Date: 2026-07-06 00:00:00

Scheduled publish + auto-archive (semantic fidel):

- ``cms_pages.publish_at``  → datetime (nullable) — momento futuro en que
  la página debe transicionar ``draft|in_review|approved|scheduled`` →
  ``published`` (scheduler automático vía cron).
- ``cms_pages.expires_at``  → datetime (nullable) — momento en que una
  página ``published`` debe transicionar a ``archived``.
- ``cms_posts.expires_at``  → datetime (nullable) — equivalente semántico
  para posts. ``cms_posts.published_at`` ya existe (cubre publish);
  añadimos sólo ``expires_at``.

Ambas columnas son nullable (control lógico puro; ningún row necesita
defaults no triviales). Los índices son simples B-Tree — el scheduler
consulta por ``publish_at <= now AND status == 'scheduled'`` y por
``expires_at <= now AND status == 'published'``. Sin índices estos
escaneos serían full-table en cada tick del cron (cada minuto).

Downgrade: drop columnas (cascade indexes first). Reversible salvo que
existan filas con contenido — al ser additive-soft (control lógico),
los rows legacy sobreviven al downgrade (queda el ``seo_json``
``_scheduled_at`` legacy intacto y el scheduler canario puede
re-abrirse).

Postgres-first con fallback SQLite. Idempotente: re-ejecución salta
columnas/índices ya presentes.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "20260706_0001_cms_schedule"
down_revision: Union[str, None] = "20260703_0002_rename_faro_site_key"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ── Helpers (Postgres-aware, SQLite-safe) ──────────────────────────────────


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


def _timestamptz():
    """Postgres-aware timestamptz fallback to DateTime para SQLite (tests)."""
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        return sa.DateTime(timezone=True)
    return sa.DateTime()


def _add_scheduling_columns(table: str, columns: tuple[str, ...]) -> None:
    """Añade columnas de scheduling (todas nullable DateTime + index B-Tree).

    Idempotente. Compatible con Postgres y SQLite.
    """
    if not _has_table(table):
        return
    for column in columns:
        if not _has_column(table, column):
            with op.batch_alter_table(table) as batch_op:
                batch_op.add_column(
                    sa.Column(column, _timestamptz(), nullable=True)
                )

        idx_name = f"ix_{table}_{column}"
        if not _has_index(table, idx_name):
            op.create_index(idx_name, table, [column], unique=False)


def _purge_legacy_scheduled_at_cruft(table: str) -> None:
    """Borra ``seo_json['_scheduled_at']`` legacy.

    El scheduler pre-migration leía este campo del ``seo_json`` de cada
    página para decidir cuando auto-publicar. Ahora esa lógica usa la
    columna ``publish_at`` propia, así que la key cruft se elimina para
    que el audit log quede consistente.

    Portable Postgres + SQLite. Idempotente — un row ya sin la key es un
    no-op. Compatible con columnas ``JSON`` (no JSONB): usamos casts
    explícitos a JSONB sólo para acceder al path, y reconstruimos el
    payload con ``jsonb_object_agg`` para re-proyectarlo como ``JSON``.
    Evitamos el operador ``-`` (JSONB-only) y el operador ``?``
    (JSONB-only); el ``->`` trabaja en ambos.

    Soft-fallback: si Postgres es JSON-only (versión / migration inicial
    donde SQLAlchemy ``JSON`` mapea a ``JSON``, no ``JSONB``) y la
    columna está poblada, el cast funciona vía ``::jsonb`` y la
    reconstrucción devuelve un JSON limpio.
    """
    if not _has_table(table):
        return
    if not _has_column(table, "seo_json"):
        return
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        # Strategy: cast column → jsonb (gives us full JSONB operator set
        # regardless of underlying JSON vs JSONB), drop the key, and cast
        # back to json. Uses only the keys operator—no reliance on the
        # column storage type.
        bind.execute(
            sa.text(
                f"UPDATE {table} AS t "
                f"SET seo_json = ( "
                f"  SELECT jsonb_object_agg(key, value)::json "
                f"  FROM jsonb_each(t.seo_json::jsonb) "
                f"  WHERE key <> '_scheduled_at' "
                f") "
                f"WHERE (t.seo_json -> '_scheduled_at') IS NOT NULL"
            )
        )
    else:
        # SQLite portable: rewrite seo_json without _scheduled_at using json_extract.
        # No-op if the key is absent (json_extract returns NULL, COALESCE preserves).
        bind.execute(
            sa.text(
                f"UPDATE {table} "
                f"SET seo_json = json_remove("
                f"  seo_json, '$._scheduled_at'"
                f") "
                f"WHERE json_type("
                f"  json_extract(seo_json, '$._scheduled_at')"
                f") IS NOT NULL"
            )
        )


# ── Migration body ──────────────────────────────────────────────────────────


def upgrade() -> None:
    # 1. cms_pages: publish_at + expires_at
    _add_scheduling_columns("cms_pages", ("publish_at", "expires_at"))

    # 2. cms_posts: expires_at (published_at ya existe)
    _add_scheduling_columns("cms_posts", ("expires_at",))

    # 3. Limpieza cruft: borra _scheduled_at legacy de seo_json.
    _purge_legacy_scheduled_at_cruft("cms_pages")
    _purge_legacy_scheduled_at_cruft("cms_posts")


def downgrade() -> None:
    for table, columns in (
        ("cms_pages", ("publish_at", "expires_at")),
        ("cms_posts", ("expires_at",)),
    ):
        if not _has_table(table):
            continue
        for column in columns:
            idx_name = f"ix_{table}_{column}"
            if _has_index(table, idx_name):
                op.drop_index(idx_name, table_name=table)
            if _has_column(table, column):
                with op.batch_alter_table(table) as batch_op:
                    batch_op.drop_column(column)
