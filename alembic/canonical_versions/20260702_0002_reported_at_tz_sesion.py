"""Ensure sesiones_grupo.reported_at is DateTime(timezone=True).

Revision ID: 20260702_0002_reported_at_tz
Revises: 20260702_0001_canonical_baseline
Create Date: 2026-07-02

PROBLEMA
--------
El ORM ``backend.models_evangelism.SesionGrupo`` define ``reported_at`` como
un ``@property`` Python con setter stub (``pass``). Aunque la columna fue
añadida a la tabla por la migración ``20260505_0008_faro_strategy_reporting``
como ``DateTime()`` (naive), el stub del setter impide que cualquier valor
persistido sea leído por el ORM — el property retorna ``None`` aunque haya
datos reales en la fila.

Adicionalmente, la sesión Pydantic ``SesionGrupoResponse`` propagaba este
``null`` a las respuestas JSON de ``PUT /api/evangelism/sessions/{id}`` y
otros endpoints, ocultando la trazabilidad de cuándo se reportó asistencia.

Este Sprint 3 cierra el bug propagando la semántica de la columna hasta
``SesionGrupo`` (la columna ya existe; sólo necesitamos asegurar que su tipo
sea ``DateTime(timezone=True)`` y que el modelo la respete como columna
real).

CAMBIOS
-------
  - Idempotente: si la columna ``reported_at`` no existe, la añade como
    ``DateTime(timezone=True) nullable``. Cubre el caso fresh-install.
  - Si existe con tipo naive (``timestamp without time zone``), la convierte
    a ``timestamp with time zone`` interpretando valores preexistentes como
    UTC (alineado con la política de
    ``20260528_0048_datetime_to_timestamptz.py``).
  - Sin backfill: la columna estaba inutilizada en producción (orphan por
    el stub), por lo que los valores preexistentes son NULL.
  - En la rama legacy ``alembic/versions/`` nunca se añadió índice:
    el campo se modificaba poco y ``sede_id + fecha_sesion`` cubría los
    patrones de uso. En este Sprint 3 (post-fix) añadimos índice PARCIAL
    ``ix_sesiones_grupo_unreported`` sobre ``(grupo_id) WHERE reported_at
    IS NULL`` — optimiza ``list_my_pending_faro_sessions``
    (``grupos_sesiones.py:169``: ``or not session.reported_at``). Sin
    índice parcial, escaneo completo de la tabla en estrategias grandes.

CONTEXTO HISTÓRICO
------------------
El ``@property stub reported_at`` de ``SesionGrupo`` (cuyo setter hacía
``pass`` y devolvía siempre ``None``) fue eliminado en el commit Sprint 3
que tocó ``backend/models_evangelism.py``: ``SesionGrupo`` ahora declara
directamente ``Column(DateTime(timezone=True), nullable=True)``. Antes
esta migration apuntaba a ``20260611_season_id_sesiones`` en la legacy
chain de ``alembic/versions/`` (archivada); se re-chainó aquí porque el
proyecto sólo consume ``alembic/canonical_versions/`` (la única
``version_location`` activa según ``alembic.ini``).

DOWNGRADE
---------
Dropear la columna (data loss aceptable: durante el bug no se persistía
ningún valor legible).
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260702_0002_reported_at_tz"
# Chain desde el canonical baseline (única ``version_location`` activa
# en ``alembic.ini``: ``alembic/canonical_versions``) para que
# ``alembic upgrade head`` quede con un solo head en CI/prod.
down_revision: Union[str, None] = "20260702_0001_canonical_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ── Helpers ──────────────────────────────────────────────────────────────


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
    """Devuelve True si la tabla tiene el índice nombrado.

    Compatible con Postgres (consulta ``pg_indexes``) y SQLite (consulta
    ``sqlite_master``). Idempotente: si la tabla no existe devuelve False.
    """
    if not _has_table(table):
        return False
    bind = op.get_bind()
    inspector = _inspector()
    # Primero intentar via inspector (más portable entre dialectos).
    try:
        for idx in inspector.get_indexes(table):
            if idx.get("name") == index_name:
                return True
    except (NotImplementedError, AttributeError):
        pass
    if bind.dialect.name == "postgresql":
        row = bind.execute(
            sa.text(
                "SELECT 1 FROM pg_indexes "
                "WHERE tablename = :t AND indexname = :i"
            ),
            {"t": table, "i": index_name},
        ).fetchone()
        return row is not None
    # SQLite fallback.
    row = bind.execute(
        sa.text(
            "SELECT 1 FROM sqlite_master "
            "WHERE type = 'index' AND tbl_name = :t AND name = :i"
        ),
        {"t": table, "i": index_name},
    ).fetchone()
    return row is not None


def _column_pg_type(table: str, column: str) -> str | None:
    """Devuelve ``data_type`` desde ``information_schema`` (Postgres).

    En SQLite se devuelve ``None`` — SQLite usa tipado dinámico por valor,
    así que la verificación de tipo sólo aplica a Postgres.
    """
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return None
    if not (_has_table(table) and _has_column(table, column)):
        return None
    row = bind.execute(
        sa.text(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_name = :t AND column_name = :c"
        ),
        {"t": table, "c": column},
    ).fetchone()
    return row[0] if row else None


def _add_reported_at_column() -> None:
    """ADD COLUMN reported_at DateTime(timezone=True) nullable. Idempotente.

    Cubre el caso fresh-install donde la columna nunca fue creada por
    ``20260505_0008_faro_strategy_reporting`` (ej: tests SQLite aislados).
    """
    if _has_column("sesiones_grupo", "reported_at"):
        return

    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        # SQLite: usar batch_alter_table para mantener compatibilidad con
        # la sintaxis ALTER TABLE de tests.
        with op.batch_alter_table("sesiones_grupo") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "reported_at",
                    sa.DateTime(timezone=True),
                    nullable=True,
                )
            )
        return

    op.add_column(
        "sesiones_grupo",
        sa.Column(
            "reported_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def _ensure_partial_index() -> None:
    """Índice parcial ``WHERE reported_at IS NULL`` para queries de pendientes.

    La query caliente del módulo evangelismo es
    ``list_my_pending_faro_sessions`` (grupos_sesiones.py:169):
    ``or not session.reported_at`` para detectar sesiones sin reporte.
    Sin índice, escanea la tabla completa en estrategias grandes.
    El índice parcial sólo cubre ``reported_at IS NULL`` → muy compacto
    y efectivo porque la mayoría de sesiones se reportan.
    """
    idx_name = "ix_sesiones_grupo_unreported"
    if _has_index("sesiones_grupo", idx_name):
        return

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            sa.text(
                f"CREATE INDEX IF NOT EXISTS {idx_name} "
                f"ON sesiones_grupo (grupo_id) WHERE reported_at IS NULL"
            )
        )
        return

    # SQLite soporta índices parciales via CREATE INDEX ... WHERE.
    with op.batch_alter_table("sesiones_grupo") as batch_op:
        batch_op.create_index(
            idx_name,
            ["grupo_id"],
            unique=False,
            sqlite_where=sa.text("reported_at IS NULL"),
        )


def _ensure_reported_at_is_timestamptz() -> None:
    """Si existe como ``timestamp without time zone``, convierte a ``timestamptz``.

    PostgreSQL: usa ``ALTER COLUMN ... TYPE TIMESTAMPTZ USING ... AT TIME ZONE
    'UTC'``. Interpretamos los valores preexistentes como UTC (consistente
    con la política ya aplicada a ``crm_casos`` y ``donations`` en
    ``20260528_0048_datetime_to_timestamptz``).
    """
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return  # SQLite: tipado dinámico; no-op.
    current = _column_pg_type("sesiones_grupo", "reported_at")
    if current in ("timestamp with time zone", None, ""):
        return  # Ya es TIMESTAMPTZ o no existe (idempotente).
    bind.execute(
        sa.text(
            "ALTER TABLE sesiones_grupo ALTER COLUMN reported_at "
            "TYPE TIMESTAMPTZ USING reported_at AT TIME ZONE 'UTC'"
        )
    )


# ── Migration body ───────────────────────────────────────────────────────


def upgrade() -> None:
    if not _has_table("sesiones_grupo"):
        # Fresh install sin tablas evangelismo — la columna se creará
        # automáticamente cuando el ORM levante la tabla. No-op idempotente.
        return
    _add_reported_at_column()
    _ensure_reported_at_is_timestamptz()
    _ensure_partial_index()


def downgrade() -> None:
    if not (_has_table("sesiones_grupo") and _has_column("sesiones_grupo", "reported_at")):
        return
    # Drop partial index primero para evitar index dangling references.
    idx_name = "ix_sesiones_grupo_unreported"
    if _has_index("sesiones_grupo", idx_name):
        bind = op.get_bind()
        if bind.dialect.name == "postgresql":
            bind.execute(sa.text(f"DROP INDEX IF EXISTS {idx_name}"))
        else:
            with op.batch_alter_table("sesiones_grupo") as batch_op:
                batch_op.drop_index(idx_name)

    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("sesiones_grupo") as batch_op:
            batch_op.drop_column("reported_at")
        return

    op.drop_column("sesiones_grupo", "reported_at")
