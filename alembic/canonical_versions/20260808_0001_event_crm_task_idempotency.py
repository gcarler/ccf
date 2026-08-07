"""Stable idempotency metadata for event CRM follow-up tasks."""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "20260808_0001_event_crm_task_idempotency"
down_revision: Union[str, None] = "20260807_0001_event_followup_identity"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TASK_INDEXES = (
    "uq_crm_task_event_registration_automation",
    "uq_crm_task_event_persona_automation",
)
TASK_LOOKUP_INDEXES = (
    "ix_crm_tareas_automation_key",
    "ix_crm_tareas_event_id",
    "ix_crm_tareas_registration_id",
)


def _inspector():
    return sa.inspect(op.get_bind())


def _has_table(table: str) -> bool:
    return table in set(_inspector().get_table_names())


def _has_column(column: str) -> bool:
    return any(c["name"] == column for c in _inspector().get_columns("crm_tareas"))


def _has_index(name: str) -> bool:
    return any(i.get("name") == name for i in _inspector().get_indexes("crm_tareas"))


def upgrade() -> None:
    if not _has_table("crm_tareas"):
        raise RuntimeError("La tabla crm_tareas debe existir antes de aplicar esta migración")
    if not _has_table("crm_events") or not _has_table("event_registrations"):
        raise RuntimeError("Las tablas de eventos deben existir antes de aplicar esta migración")

    with op.batch_alter_table("crm_tareas") as batch:
        if not _has_column("automation_key"):
            batch.add_column(sa.Column("automation_key", sa.String(100), nullable=True))
        if not _has_column("event_id"):
            batch.add_column(
                sa.Column(
                    "event_id",
                    sa.Uuid(as_uuid=True),
                    sa.ForeignKey("crm_events.id", ondelete="SET NULL"),
                    nullable=True,
                )
            )
        if not _has_column("registration_id"):
            batch.add_column(
                sa.Column(
                    "registration_id",
                    sa.Uuid(as_uuid=True),
                    sa.ForeignKey("event_registrations.id", ondelete="SET NULL"),
                    nullable=True,
                )
            )

    for name, columns in (
        (TASK_LOOKUP_INDEXES[0], ["automation_key"]),
        (TASK_LOOKUP_INDEXES[1], ["event_id"]),
        (TASK_LOOKUP_INDEXES[2], ["registration_id"]),
    ):
        if not _has_index(name):
            op.create_index(name, "crm_tareas", columns, unique=False)

    if not _has_index(TASK_INDEXES[0]):
        op.create_index(
            TASK_INDEXES[0],
            "crm_tareas",
            ["registration_id", "automation_key"],
            unique=True,
            postgresql_where=sa.text("automation_key IS NOT NULL AND deleted_at IS NULL"),
            sqlite_where=sa.text("automation_key IS NOT NULL AND deleted_at IS NULL"),
        )
    if not _has_index(TASK_INDEXES[1]):
        op.create_index(
            TASK_INDEXES[1],
            "crm_tareas",
            ["event_id", "persona_id", "automation_key"],
            unique=True,
            postgresql_where=sa.text(
                "automation_key IS NOT NULL AND registration_id IS NULL AND deleted_at IS NULL"
            ),
            sqlite_where=sa.text(
                "automation_key IS NOT NULL AND registration_id IS NULL AND deleted_at IS NULL"
            ),
        )


def downgrade() -> None:
    if not _has_table("crm_tareas"):
        return
    for name in reversed(TASK_INDEXES + TASK_LOOKUP_INDEXES):
        if _has_index(name):
            op.drop_index(name, table_name="crm_tareas")
    columns = {c["name"] for c in _inspector().get_columns("crm_tareas")}
    with op.batch_alter_table("crm_tareas") as batch:
        for column in ("registration_id", "event_id", "automation_key"):
            if column in columns:
                batch.drop_column(column)
