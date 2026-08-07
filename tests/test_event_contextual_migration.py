"""Migración 20260806_0001 — ensanche de role_at_event en SQLite legacy.

Reconstruido desde su bytecode (restauración de trabajo perdido): crea un
esquema legacy (alembic_version + crm_events + event_registrations +
event_attendances con ``role_at_event VARCHAR(30)`` + datos), ejecuta el
``upgrade()`` de la migración contextual y verifica que:

    - ``role_at_event`` se amplía a VARCHAR(40) conservando los datos.
    - ``participant_role_code`` se añade a crm_events y event_registrations.
    - Se crean los índices ``ix_*_participant_role_code``.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations

ROOT = Path(__file__).resolve().parent.parent
MIGRATION_PATH = ROOT / "alembic" / "canonical_versions" / "20260806_0001_event_contextual_roles.py"


def _load_migration():
    spec = importlib.util.spec_from_file_location("ctx_migration_20260806", MIGRATION_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # typing/dataclass requieren el módulo registrado
    spec.loader.exec_module(module)
    return module


def test_upgrade_expands_legacy_role_column_on_sqlite_without_losing_data():
    engine = sa.create_engine("sqlite://")
    metadata = sa.MetaData()
    sa.Table(
        "alembic_version",
        metadata,
        sa.Column("version_num", sa.String(255), nullable=False),
    )
    sa.Table("crm_events", metadata, sa.Column("id", sa.String(36), primary_key=True))
    sa.Table(
        "event_registrations", metadata, sa.Column("id", sa.String(36), primary_key=True)
    )
    sa.Table(
        "event_attendances",
        metadata,
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("role_at_event", sa.String(30), nullable=True),
    )

    with engine.begin() as connection:
        metadata.create_all(connection)
        connection.execute(
            sa.text("INSERT INTO alembic_version(version_num) VALUES ('0003')")
        )
        connection.execute(
            sa.text(
                "INSERT INTO event_attendances(id, role_at_event) VALUES ('a1', 'VISITANTE_EVENTO')"
            )
        )

        migration = _load_migration()
        # Patrón test_no_legacy_migration.py:99 — el proxy global `op` del
        # módulo se reemplaza por un Operations ligado a este contexto.
        migration.op = Operations(MigrationContext.configure(connection))
        migration.upgrade()

        inspector = sa.inspect(connection)

        attendance_columns = {
            column["name"]: column for column in inspector.get_columns("event_attendances")
        }
        assert attendance_columns["role_at_event"]["type"].length == 40

        # Los datos históricos se conservan (ALTER COLUMN TYPE, no destructivo).
        assert (
            connection.execute(
                sa.text("SELECT role_at_event FROM event_attendances WHERE id = 'a1'")
            ).scalar_one()
            == "VISITANTE_EVENTO"
        )

        event_columns = {column["name"] for column in inspector.get_columns("crm_events")}
        registration_columns = {
            column["name"] for column in inspector.get_columns("event_registrations")
        }
        assert "participant_role_code" in event_columns
        assert "participant_role_code" in registration_columns

        event_indexes = {index["name"] for index in inspector.get_indexes("crm_events")}
        registration_indexes = {
            index["name"] for index in inspector.get_indexes("event_registrations")
        }
        assert "ix_crm_events_participant_role_code" in event_indexes
        assert "ix_event_registrations_participant_role_code" in registration_indexes
