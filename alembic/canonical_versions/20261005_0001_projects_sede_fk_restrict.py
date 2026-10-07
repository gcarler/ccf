"""Protect tenant-scoped Projects rows from becoming global on Sede deletion.

Revision ID: 20261005_0001_projects_sede_fk_restrict
Revises: 20260930_0001_create_surveys_tables

Project rows may have a nullable ``sede_id`` to retain explicitly global
records, and project templates/automation rules intentionally use NULL as
global scope. ``ON DELETE SET NULL`` therefore turns tenant rows into global
rows when a Sede is hard-deleted. Soft deletion remains the supported Sede
lifecycle; this FK guard prevents accidental scope broadening at the database
boundary.

SQLite test databases derive the FK action from model metadata and need no
table rebuild here. PostgreSQL preserves each existing constraint name.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "20261005_0001_projects_sede_fk_restrict"
down_revision: Union[str, None] = "20260930_0001_create_surveys_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES = (
    "projects",
    "project_templates",
    "project_automation_rules",
    "project_indicators",
    "project_files",
)


def _inspector():
    return sa.inspect(op.get_bind())


def _sede_fk(table_name: str) -> dict | None:
    inspector = _inspector()
    if table_name not in set(inspector.get_table_names()):
        return None
    return next(
        (
            foreign_key
            for foreign_key in inspector.get_foreign_keys(table_name)
            if foreign_key.get("constrained_columns") == ["sede_id"]
            and foreign_key.get("referred_table") == "sedes"
            and foreign_key.get("referred_columns") == ["id"]
        ),
        None,
    )


def _set_delete_action(table_name: str, action: str) -> None:
    if op.get_bind().dialect.name != "postgresql":
        return

    foreign_key = _sede_fk(table_name)
    if foreign_key is None:
        raise RuntimeError(f"Expected {table_name}.sede_id → sedes.id foreign key")

    existing_action = str((foreign_key.get("options") or {}).get("ondelete") or "NO ACTION").upper()
    if existing_action == action:
        return

    constraint_name = foreign_key.get("name")
    if not constraint_name:
        raise RuntimeError(f"Cannot safely replace unnamed FK on {table_name}.sede_id")

    op.drop_constraint(constraint_name, table_name, type_="foreignkey")
    op.create_foreign_key(
        constraint_name,
        table_name,
        "sedes",
        ["sede_id"],
        ["id"],
        ondelete=action,
    )


def upgrade() -> None:
    for table_name in TABLES:
        _set_delete_action(table_name, "RESTRICT")


def downgrade() -> None:
    for table_name in TABLES:
        _set_delete_action(table_name, "SET NULL")
