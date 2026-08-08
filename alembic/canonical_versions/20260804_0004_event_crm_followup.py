"""Link event registrations to CRM and close event attendance.

Revision ID: 20260804_0004_event_crm_followup
Revises: 20260804_0003_event_registration_waitlist_unique
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260804_0004_event_crm_followup"
down_revision: Union[str, None] = "20260804_0003_event_registration_waitlist_unique"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _inspector():
    return sa.inspect(op.get_bind())


def _has_table(table: str) -> bool:
    return table in set(_inspector().get_table_names())


def _has_column(table: str, column: str) -> bool:
    return _has_table(table) and any(c["name"] == column for c in _inspector().get_columns(table))


def _has_index(table: str, name: str) -> bool:
    return _has_table(table) and any(i.get("name") == name for i in _inspector().get_indexes(table))


def _add_column(table: str, column: sa.Column) -> None:
    if _has_table(table) and not _has_column(table, column.name):
        with op.batch_alter_table(table) as batch:
            batch.add_column(column)


def upgrade() -> None:
    _add_column("crm_events", sa.Column("attendance_closed_at", sa.DateTime(timezone=True), nullable=True))
    _add_column("crm_events", sa.Column("attendance_closed_by", sa.UUID(), nullable=True))
    _add_column("event_registrations", sa.Column("crm_case_id", sa.UUID(), nullable=True))
    _add_column("personas", sa.Column("origen_evento_id", sa.UUID(), nullable=True))
    _add_column("crm_casos", sa.Column("origen_evento_id", sa.UUID(), nullable=True))

    for table, name, columns in (
        ("crm_events", "ix_crm_events_attendance_closed_at", ["attendance_closed_at"]),
        ("event_registrations", "ix_event_registrations_crm_case_id", ["crm_case_id"]),
        ("personas", "ix_personas_origen_evento_id", ["origen_evento_id"]),
        ("crm_casos", "ix_crm_casos_origen_evento_id", ["origen_evento_id"]),
    ):
        if _has_table(table) and not _has_index(table, name):
            op.create_index(name, table, columns, unique=False)

    if _has_table("crm_casos") and not _has_index("crm_casos", "uq_crm_case_persona_event_active"):
        op.create_index(
            "uq_crm_case_persona_event_active",
            "crm_casos",
            ["persona_id", "origen_evento_id"],
            unique=True,
            postgresql_where=sa.text("origen_evento_id IS NOT NULL AND deleted_at IS NULL"),
            sqlite_where=sa.text("origen_evento_id IS NOT NULL AND deleted_at IS NULL"),
        )


def downgrade() -> None:
    if _has_table("crm_casos"):
        for name in ("uq_crm_case_persona_event_active", "ix_crm_casos_origen_evento_id"):
            if _has_index("crm_casos", name):
                op.drop_index(name, table_name="crm_casos")
        if _has_column("crm_casos", "origen_evento_id"):
            with op.batch_alter_table("crm_casos") as batch:
                batch.drop_column("origen_evento_id")

    if _has_table("personas"):
        if _has_index("personas", "ix_personas_origen_evento_id"):
            op.drop_index("ix_personas_origen_evento_id", table_name="personas")
        if _has_column("personas", "origen_evento_id"):
            with op.batch_alter_table("personas") as batch:
                batch.drop_column("origen_evento_id")

    if _has_table("event_registrations"):
        if _has_index("event_registrations", "ix_event_registrations_crm_case_id"):
            op.drop_index("ix_event_registrations_crm_case_id", table_name="event_registrations")
        if _has_column("event_registrations", "crm_case_id"):
            with op.batch_alter_table("event_registrations") as batch:
                batch.drop_column("crm_case_id")

    if _has_table("crm_events"):
        if _has_index("crm_events", "ix_crm_events_attendance_closed_at"):
            op.drop_index("ix_crm_events_attendance_closed_at", table_name="crm_events")
        with op.batch_alter_table("crm_events") as batch:
            for column in ("attendance_closed_by", "attendance_closed_at"):
                if _has_column("crm_events", column):
                    batch.drop_column(column)
