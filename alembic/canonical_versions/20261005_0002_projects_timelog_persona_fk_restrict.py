"""Preserve required persona attribution for project time logs.

Revision ID: 20261005_0002_projects_timelog_persona_fk_restrict
Revises: 20261005_0001_projects_sede_fk_restrict

``project_time_logs.persona_id`` is NOT NULL and the API/schema require a
canonical person. The prior ``ON DELETE SET NULL`` action contradicted that
contract and made physical Persona deletion fail indirectly at NOT NULL.
The supported Persona lifecycle is soft delete; RESTRICT makes the database
protect historical timesheet attribution explicitly.

SQLite test databases derive the action from model metadata and need no
table rebuild here. PostgreSQL preserves the live FK constraint name.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "20261005_0002_projects_timelog_persona_fk_restrict"
down_revision: Union[str, None] = "20261005_0001_projects_sede_fk_restrict"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE_NAME = "project_time_logs"


def _persona_fk() -> dict | None:
    inspector = sa.inspect(op.get_bind())
    if TABLE_NAME not in set(inspector.get_table_names()):
        return None
    return next(
        (
            foreign_key
            for foreign_key in inspector.get_foreign_keys(TABLE_NAME)
            if foreign_key.get("constrained_columns") == ["persona_id"]
            and foreign_key.get("referred_table") == "personas"
            and foreign_key.get("referred_columns") == ["id"]
        ),
        None,
    )


def _set_delete_action(action: str) -> None:
    if op.get_bind().dialect.name != "postgresql":
        return

    foreign_key = _persona_fk()
    if foreign_key is None:
        raise RuntimeError("Expected project_time_logs.persona_id → personas.id foreign key")

    existing_action = str((foreign_key.get("options") or {}).get("ondelete") or "NO ACTION").upper()
    if existing_action == action:
        return

    constraint_name = foreign_key.get("name")
    if not constraint_name:
        raise RuntimeError("Cannot safely replace unnamed FK on project_time_logs.persona_id")

    op.drop_constraint(constraint_name, TABLE_NAME, type_="foreignkey")
    op.create_foreign_key(
        constraint_name,
        TABLE_NAME,
        "personas",
        ["persona_id"],
        ["id"],
        ondelete=action,
    )


def upgrade() -> None:
    _set_delete_action("RESTRICT")


def downgrade() -> None:
    _set_delete_action("SET NULL")
