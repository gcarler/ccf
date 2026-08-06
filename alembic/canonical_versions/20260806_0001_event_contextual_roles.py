"""Contextual participant role per event (clasificador contextual).

Revision ID: 20260806_0001_event_contextual_roles
Revises: 20260804_0003_event_registration_waitlist_unique
Create Date: 2026-08-06

Contexto
========
Plan: ``docs/PLAN_CLASIFICADOR_CONTEXTUAL_PERSONAS_EVENTO.md``.

Una persona conserva una identidad global en ``personas.id``, pero puede
participar en distintos eventos con clasificaciones distintas. El rol
contextual pertenece a la participación en el evento, no a la persona.

Esta migración añade:

    crm_events.participant_role_code            VARCHAR(40)  — rol por defecto del evento
    event_registrations.participant_role_code   VARCHAR(40)  — rol efectivo de la inscripción
    event_attendances.role_at_event             VARCHAR(30→40) — rol persistido en asistencia

Más los índices:

    ix_crm_events_participant_role_code
    ix_event_registrations_participant_role_code

Compatibilidad (REGLAS.md §9): aditivo, no destructivo.
    - Las columnas nuevas son NULL por defecto: los eventos e inscripciones
      existentes siguen siendo válidos; el rol se resuelve con el default
      ``VISITANTE_EVENTO`` cuando no está seteado.
    - ``role_at_event`` histórico se amplía de ``VARCHAR(30)`` a ``VARCHAR(40)``
      conservando los datos (``ALTER COLUMN TYPE``).

Idempotencia
------------
La migración valida antes de alterar (``_has_table`` / ``_has_column`` /
``_has_index`` / ``_ensure_string_length``) para ser segura frente a entornos
que ya la hayan aplicado manualmente. El ``downgrade()`` es intencionalmente
monotónico: no elimina columnas ni índices (rollback requiere backup y
procedimiento operativo manual, ver runbook).
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "20260806_0001_event_contextual_roles"
down_revision: Union[str, None] = "20260804_0003_event_registration_waitlist_unique"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ── Helpers de idempotencia (mismo patrón que 20260804_0001) ──────────────────


def _has_table(table: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table in inspector.get_table_names()


def _has_column(table: str, column_name: str) -> bool:
    if not _has_table(table):
        return False
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(col["name"] == column_name for col in inspector.get_columns(table))


def _has_index(table: str, index_name: str) -> bool:
    if not _has_table(table):
        return False
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(idx["name"] == index_name for idx in inspector.get_indexes(table))


def _inspector() -> sa.Inspector:
    bind = op.get_bind()
    return sa.inspect(bind)


def _add_column_if_missing(table: str, column_name: str, column: sa.Column) -> None:
    """Añade la columna solo si la tabla existe y la columna no existe ya."""
    if not _has_table(table):
        return
    if _has_column(table, column_name):
        return
    with op.batch_alter_table(table, schema=None) as batch_op:
        batch_op.add_column(column)


def _ensure_string_length(table: str, column: str, target_length: int) -> None:
    """Amplía un VARCHAR existente a ``target_length`` conservando los datos."""
    if not _has_table(table):
        return
    if not _has_column(table, column):
        return
    current = next(
        col for col in _inspector().get_columns(table) if col.get("name") == column
    )
    current_type = current.get("type")
    current_length = getattr(current_type, "length", None)
    if isinstance(current_length, int) and current_length >= target_length:
        # Ya tiene el tamaño correcto (o mayor): no recrear.
        return
    with op.batch_alter_table(table, schema=None) as batch_op:
        batch_op.alter_column(column, type_=sa.String(target_length))


def _create_index_if_missing(table: str, index_name: str) -> None:
    """Crea el índice solo si la tabla/columna existen y el índice no existe."""
    if not _has_table(table):
        return
    if not _has_column(table, "participant_role_code"):
        return
    if _has_index(table, index_name):
        return
    op.create_index(index_name, table, ["participant_role_code"])


def upgrade() -> None:
    """Aplica las columnas contextuales, el ensanche de ``role_at_event`` y los índices."""
    _add_column_if_missing(
        "crm_events",
        "participant_role_code",
        sa.Column("participant_role_code", sa.String(40), nullable=True),
    )
    _add_column_if_missing(
        "event_registrations",
        "participant_role_code",
        sa.Column("participant_role_code", sa.String(40), nullable=True),
    )
    _ensure_string_length("event_attendances", "role_at_event", 40)
    _create_index_if_missing("crm_events", "ix_crm_events_participant_role_code")
    _create_index_if_missing(
        "event_registrations", "ix_event_registrations_participant_role_code"
    )


def downgrade() -> None:
    """Monotónico: no elimina columnas ni índices (rollback requiere backup)."""
    return
