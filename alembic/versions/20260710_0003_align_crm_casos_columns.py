"""Align CRM Casos columns (idempotent recovery migration)

Production-side bug driver: ``GET /api/crm/casos`` and
``GET /api/crm/leads/newsletter`` returned HTTP 500 with
``psycopg2.errors.UndefinedColumn: column crm_casos...``. The query
contains WHERE-clauses that reference model-declared columns which the live
Postgres table does not have. The runtime defenses added in
:mod:`backend.api.crm._shared` (``case_query`` + ``load_only``) only protect
the SELECT projection, NOT the WHERE clause. The root cause is a missing
column on the live table.

This migration is the surgical fix: branch from current head
``20260710_0002`` and add EVERY column from :class:`backend.models_crm_pipeline.CasoCRM`
that might be missing from `crm_casos` AND `crm_etapas_pipeline` (the
companion visual_color fix). All ``op.add_column`` calls are guarded by a
``_col_exists`` check against ``information_schema.columns`` so the migration
is fully idempotent (safe to re-run, safe to apply on databases that
already have the columns).

Per CCF ``REGLAS.md §9.1`` (migrations are immutable history once merged),
``downgrade()`` is intentionally a no-op — the column additions are a
forward-only recovery from production drift.

Revision ID: 20260710_0003
Revises: 20260710_0002
Create Date: 2026-07-10 12:00:00.000000
"""
from typing import Optional, Tuple, Union

import sqlalchemy as sa
from alembic import op

# NOTE: we use the SQLAlchemy *core* types (``sa.JSON``, ``sa.UUID(...)``)
# rather than the Postgres-dialect ones so Alembic can also reflect the
# migration on SQLite (used in the test suite). Alembic maps these types to
# native JSON / UUID on Postgres and to TEXT / CHAR(32) on SQLite.
revision: str = "20260710_0003"
down_revision: Union[str, None] = "20260710_0002"
branch_labels: Optional[Union[str, Tuple[str, ...]]] = None
depends_on: Optional[Union[str, Tuple[str, ...]]] = None


def _col_exists(table: str, col: str) -> bool:
    """Defensive introspection that works on Postgres + SQLite."""
    bind = op.get_bind()
    dialect = bind.dialect.name if bind is not None else ""
    if dialect == "sqlite":
        rows = bind.execute(
            sa.text(f"PRAGMA table_info({table})")
        ).fetchall()
        return any(row[1] == col for row in rows)
    return bool(
        bind.execute(
            sa.text(
                "SELECT count(*) FROM information_schema.columns "
                "WHERE table_name = :t AND column_name = :c"
            ),
            {"t": table, "c": col},
        ).scalar()
    )


def upgrade() -> None:
    # ── crm_casos: align to canonical CasoCRM model ────────────────────
    # Defensive additive only — NEVER drop or rename. Each block is gated
    # on information_schema so re-running this migration is a no-op.

    # FKs (declared NOT NULL in the canonical model, but live DBs pre-dating
    # the canonical contract cannot be retro-constrained without data
    # corruption; add as nullable to be safe). Every FK column carries its
    # ``ForeignKey(...)`` constraint so DRI matches the canonical contract
    # (otherwise empty pipelines/etapas rows could be referenced with no
    # referential integrity on the database side).
    if not _col_exists("crm_casos", "pipeline_id"):
        op.add_column(
            "crm_casos",
            sa.Column(
                "pipeline_id",
                sa.UUID(as_uuid=True),
                sa.ForeignKey("crm_pipelines.id"),
                nullable=True,
            ),
        )
    if not _col_exists("crm_casos", "etapa_actual_id"):
        op.add_column(
            "crm_casos",
            sa.Column(
                "etapa_actual_id",
                sa.UUID(as_uuid=True),
                sa.ForeignKey("crm_etapas_pipeline.id"),
                nullable=True,
            ),
        )
    if not _col_exists("crm_casos", "persona_id"):
        op.add_column(
            "crm_casos",
            sa.Column(
                "persona_id",
                sa.UUID(as_uuid=True),
                sa.ForeignKey("personas.id", ondelete="SET NULL"),
                nullable=True,
            ),
        )
    if not _col_exists("crm_casos", "sede_id"):
        op.add_column(
            "crm_casos",
            sa.Column(
                "sede_id",
                sa.UUID(as_uuid=True),
                sa.ForeignKey("sedes.id"),
                nullable=True,
            ),
        )
    # Evangelism FKs (added by ``b3c4d5e6f7a8_add_origen_sesion_id.py`` —
    # include in this recovery sweep so a prod DB that skipped that
    # revision also ends up at the canonical schema).
    if not _col_exists("crm_casos", "origen_sesion_id"):
        op.add_column(
            "crm_casos",
            sa.Column(
                "origen_sesion_id",
                sa.UUID(as_uuid=True),
                sa.ForeignKey("sesiones_grupo.id", ondelete="SET NULL"),
                nullable=True,
            ),
        )
    if not _col_exists("crm_casos", "origen_grupo_id"):
        op.add_column(
            "crm_casos",
            sa.Column(
                "origen_grupo_id",
                sa.UUID(as_uuid=True),
                sa.ForeignKey("grupos_evangelismo.id", ondelete="SET NULL"),
                nullable=True,
            ),
        )
    if not _col_exists("crm_casos", "origen_estrategia_id"):
        op.add_column(
            "crm_casos",
            sa.Column(
                "origen_estrategia_id",
                sa.UUID(as_uuid=True),
                sa.ForeignKey("estrategias_evangelismo.id", ondelete="SET NULL"),
                nullable=True,
            ),
        )

    # String/Text columns.  We deliberately add ENUM-like columns as
    # ``String(...)/TEXT`` to be safe: the model side declares ``SAEnum``,
    # but pre-existing rows in production databases may use raw strings.
    # A future, separate migration can normalize the type once the live
    # database has been audited at the values level.
    if not _col_exists("crm_casos", "titulo_caso"):
        op.add_column(
            "crm_casos",
            sa.Column("titulo_caso", sa.String(200), nullable=True),
        )
    if not _col_exists("crm_casos", "origen_canal"):
        op.add_column(
            "crm_casos",
            sa.Column("origen_canal", sa.String(50), nullable=True),
        )
    if not _col_exists("crm_casos", "origen_detalle_id"):
        op.add_column(
            "crm_casos",
            sa.Column("origen_detalle_id", sa.String(200), nullable=True),
        )
    if not _col_exists("crm_casos", "prioridad"):
        op.add_column(
            "crm_casos",
            sa.Column("prioridad", sa.String(20), nullable=True),
        )
    if not _col_exists("crm_casos", "estado"):
        op.add_column(
            "crm_casos",
            sa.Column("estado", sa.String(30), nullable=True),
        )

    # JSON column — Postgres natively JSON, SQLite serializes to TEXT.
    if not _col_exists("crm_casos", "payload_web"):
        op.add_column(
            "crm_casos",
            sa.Column("payload_web", JSON, nullable=True),
        )

    # FK + datetime + boolean — drag & drop fields from canonical_versions/
    # 20260710_0002_crm_automation_graph.py (draft, may not be in prod yet).
    if not _col_exists("crm_casos", "asignado_a_id"):
        op.add_column(
            "crm_casos",
            sa.Column(
                "asignado_a_id",
                sa.UUID(as_uuid=True),
                sa.ForeignKey("personas.id", ondelete="SET NULL"),
                nullable=True,
            ),
        )
    if not _col_exists("crm_casos", "fecha_creacion"):
        op.add_column(
            "crm_casos",
            sa.Column("fecha_creacion", sa.DateTime(timezone=True), nullable=True),
        )
    if not _col_exists("crm_casos", "fecha_cierre"):
        op.add_column(
            "crm_casos",
            sa.Column("fecha_cierre", sa.DateTime(timezone=True), nullable=True),
        )
    if not _col_exists("crm_casos", "sla_vencimiento_contacto"):
        op.add_column(
            "crm_casos",
            sa.Column(
                "sla_vencimiento_contacto", sa.DateTime(timezone=True), nullable=True
            ),
        )
    if not _col_exists("crm_casos", "deleted_at"):
        op.add_column(
            "crm_casos",
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        )
    if not _col_exists("crm_casos", "sort_order"):
        op.add_column(
            "crm_casos",
            sa.Column(
                "sort_order",
                sa.Integer(),
                server_default="0",
                nullable=False,
            ),
        )
    if not _col_exists("crm_casos", "drag_source_etapa_id"):
        op.add_column(
            "crm_casos",
            sa.Column("drag_source_etapa_id", sa.UUID(as_uuid=True), nullable=True),
        )
    if not _col_exists("crm_casos", "drag_target_etapa_id"):
        op.add_column(
            "crm_casos",
            sa.Column("drag_target_etapa_id", sa.UUID(as_uuid=True), nullable=True),
        )
    if not _col_exists("crm_casos", "is_locked_for_reorder"):
        op.add_column(
            "crm_casos",
            sa.Column(
                "is_locked_for_reorder",
                sa.Boolean(),
                server_default=sa.false(),
                nullable=False,
            ),
        )
    if not _col_exists("crm_casos", "last_reorder_failed"):
        op.add_column(
            "crm_casos",
            sa.Column(
                "last_reorder_failed",
                sa.Boolean(),
                server_default=sa.false(),
                nullable=False,
            ),
        )

    # ── crm_etapas_pipeline: visual_color from prior canonical_fix ────────
    if not _col_exists("crm_etapas_pipeline", "visual_color"):
        op.add_column(
            "crm_etapas_pipeline",
            sa.Column("visual_color", sa.String(50), nullable=True),
        )


def downgrade() -> None:
    # REGLAS §9.1 — migrations are immutable history once merged. We
    # intentionally do NOT drop added columns here. Operators can
    # downgrade the schema by manually dropping the columns if absolutely
    # needed; never silently lose data.
    pass
