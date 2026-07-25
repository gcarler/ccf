"""20260725_0003 — add deleted_at to support_tickets + event_attendances

Continuación de la auditoría forense de calidad del módulo CRM (post-cierre
errorescrm.md, session ses_065da89 2026-07-25). El subagent explore re-auditó
el módulo y surfaced dos replicas del patrón QC-02 (CommunicationLog.deleted_at
faltante — cerrado commit 8c2ac1c6):

- **QC-06** `SupportTicket.deleted_at` en ``backend/models_crm.py:926``:
  El CRUD ``delete_support_ticket`` (``backend/crud/crm_/support.py:42``) ya
  hacia ``row.deleted_at = _utcnow()`` (soft-delete) pero la columna NO
  existia en el modelo ni en la tabla prod. En Postgres el commit fallaria
  (``column "deleted_at" of relation "support_tickets" does not exist``);
  en SQLite la asignación ORM se descarta silenciosamente y el ticket
  permanecia "vivo" para siempre (soft-delete silenciosamente roto,
  revivible vía update_support_ticket).

- **QC-07** `EventAttendance.deleted_at` en ``backend/models_crm.py:135``:
  Caso idéntico al patrón QC-06 — el CRUD ``delete_event_attendance`` ya
  hacia ``row.deleted_at = _utcnow()`` pero faltaba la columna. Adicionalmente,
  ``backend/crud/crm_/health.py:63`` querya ``EventAttendance`` sin filtrar
  ``deleted_at`` (una vez la columna exista, el filter debe aplicarse para
  que las asistencias soft-deletadas no distorsionen el ``pastoral_health_score``).

Esta migración añade ``deleted_at`` (DateTime(timezone=True), nullable, indexed)
a ambas tablas. Patrones hermanos: ``20260719_0001_crm_events_deleted_at``,
``20260721_0001_prayer_requests_deleted_at``, ``20260723_0001_add_deleted_at_to_admin_entities``,
``20260725_0002_communication_logs_deleted_at``.

SQLite branch: this migration is a no-op on SQLite because tests use
``Base.metadata.create_all`` (NOT alembic migrations) — the model-level change
is sufficient for the test suite. The Postgres branch performs the real
``ALTER TABLE``. Ver doctrina en MEMORY.md "Tests use Base.metadata.create_all,
NOT alembic migrations" (2026-07-23 ses_0717db479).

Revision ID: 20260725_0003
Revises: 20260725_0002
Create Date: 2026-07-25 02:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260725_0003"
down_revision: Union[str, None] = "20260725_0002"
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


def _has_index(table: str, index_name: str) -> bool:
    if not _has_table(table):
        return False
    return any(idx.get("name") == index_name for idx in _inspector().get_indexes(table))


def _add_deleted_at(table_name: str, index_name: str) -> None:
    """Idempotente: añade columna + index si faltan."""
    if not _has_table(table_name) or _has_column(table_name, "deleted_at"):
        return

    op.add_column(
        table_name,
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    if not _has_index(table_name, index_name):
        op.create_index(
            index_name,
            table_name,
            ["deleted_at"],
            unique=False,
        )


def _drop_deleted_at(table_name: str, index_name: str) -> None:
    """Idempotente: deja la tabla como estaba."""
    if not _has_table(table_name) or not _has_column(table_name, "deleted_at"):
        return

    if _has_index(table_name, index_name):
        op.drop_index(index_name, table_name=table_name)

    op.drop_column(table_name, "deleted_at")


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    # SQLite branch: no-op (tests use Base.metadata.create_all, not migrations).
    if dialect == "sqlite":
        return

    # Postgres branch (production): real ALTER TABLE idempotente.
    _add_deleted_at("support_tickets", "ix_support_tickets_deleted_at")
    _add_deleted_at("event_attendances", "ix_event_attendances_deleted_at")


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "sqlite":
        return

    _drop_deleted_at("event_attendances", "ix_event_attendances_deleted_at")
    _drop_deleted_at("support_tickets", "ix_support_tickets_deleted_at")
