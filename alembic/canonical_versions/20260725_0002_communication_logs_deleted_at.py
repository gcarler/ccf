"""20260725_0002 — add deleted_at to communication_logs

Axioma Soft-Delete hardening del modulo CRM (auditoria de calidad post-cierre
errorescrm.md, hallazgo QC-soft-delete-CommunicationLog 2026-07-25):

``communication_logs`` ya era tratado como soft-deletable en el CRUD
(``backend/crud/crm_/communication.py:delete_communication_log`` setea
``row.deleted_at = _utcnow()`` y ``get_communication_logs``/``get_communication_log``
filt ``deleted_at IS NULL``), pero la columna ``deleted_at`` NO existia en
el modelo ORM ni en la tabla prod. El ORM asignaba un atributo fantasma que:
  - En Postgres: romperia al commit (``column "deleted_at" of relation
    "communication_logs" does not exist``).
  - En SQLite: SQLAlchemy lo guarda en el ``__dict__`` instance pero
    ``UPDATE communication_logs SET deleted_at=...`` falla silenciosamente
    en commit, dejando el log "vivo" para siempre.

El dirty tree de calidad (continuar la auditoria forense CRM) añadio la
columna al modelo ORM ``backend/models_crm.py:694`` y los filtros
``deleted_at.is_(None)`` a los reads. Esta migracion añade la columna a la
base de datos prod (Postgres), alineando modelo + CRUD + tabla — siguiendo
el patrón soft-delete uniforme del backend CCF (Axioma:
``DateTime(timezone=True)`` + soft delete en vez de hard delete).

Patrones hermanos: ``20260719_0001_crm_events_deleted_at``,
``20260721_0001_prayer_requests_deleted_at``, ``20260723_0001_add_deleted_at_to_admin_entities``.

SQLite branch: this migration is a no-op on SQLite because tests use
``Base.metadata.create_all`` (NOT alembic migrations) — the model-level
change is sufficient for the test suite. The Postgres branch performs the
real ``ALTER TABLE``. Ver doctrina en MEMORY.md "Tests use Base.metadata.create_all,
NOT alembic migrations" (2026-07-23 ses_0717db479).

Revision ID: 20260725_0002
Revises: 20260725_0001
Create Date: 2026-07-25 01:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260725_0002"
down_revision: Union[str, None] = "20260725_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _inspector():
    return sa.inspect(op.get_bind())


def _has_table(table: str) -> bool:
    return table in set(_inspector().get_table_names())


def _has_column(table: str, column: str) -> bool:
    if not _has_table(table):
        return False
    return any(col.get("name") == column for col in _inspector().get_columns(table))


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    # SQLite branch: no-op (tests use Base.metadata.create_all, not migrations).
    # The model already declares the column; tests get it for free.
    if dialect == "sqlite":
        return

    # Postgres branch (production): real ALTER TABLE — idempotente guards.
    if not _has_table("communication_logs") or _has_column("communication_logs", "deleted_at"):
        return

    op.add_column(
        "communication_logs",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "sqlite":
        return

    if not _has_table("communication_logs") or not _has_column("communication_logs", "deleted_at"):
        return

    op.drop_column("communication_logs", "deleted_at")
