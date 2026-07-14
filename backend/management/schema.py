from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from alembic.config import Config
from sqlalchemy import inspect

from alembic import command
from backend import models  # noqa: F401
from backend.core.config import get_settings
from backend.core.database import Base, engine

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI = PROJECT_ROOT / "alembic.ini"
IGNORED_EXTRA_TABLES = {"alembic_version"}


def _is_auxiliary_sqlite_table(table_name: str) -> bool:
    suffixes = ("_config", "_data", "_docsize", "_idx")
    return table_name.endswith(suffixes)


def _alembic_config() -> Config:
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("script_location", str(PROJECT_ROOT / "alembic"))
    config.set_main_option(
        "version_locations",
        str(PROJECT_ROOT / "alembic" / "canonical_versions"),
    )
    return config


def upgrade_to_head() -> None:
    command.upgrade(_alembic_config(), "head")


def current_revision() -> str | None:
    inspector = inspect(engine)
    if "alembic_version" not in inspector.get_table_names():
        return None
    with engine.connect() as conn:
        row = conn.exec_driver_sql("SELECT version_num FROM alembic_version").first()
    return None if row is None else str(row[0])


def schema_drift_report() -> dict[str, Any]:
    inspector = inspect(engine)
    database_tables = set(inspector.get_table_names())
    metadata_tables = set(Base.metadata.tables.keys())
    extra_tables = sorted(
        table
        for table in (database_tables - metadata_tables)
        if table not in IGNORED_EXTRA_TABLES and not _is_auxiliary_sqlite_table(table)
    )
    return {
        "current_revision": current_revision(),
        "database_tables": sorted(database_tables),
        "metadata_tables": sorted(metadata_tables),
        "missing_in_db": sorted(metadata_tables - database_tables),
        "extra_in_db": extra_tables,
        "legacy_in_db": [],
    }


def print_schema_drift_report() -> None:
    report = schema_drift_report()
    print("=== Schema Drift Report ===")
    print(f"Alembic revision: {report['current_revision'] or 'unversioned'}")
    print(f"Missing tables in DB: {len(report['missing_in_db'])}")
    for table in report["missing_in_db"]:
        print(f"  - {table}")
    print(f"Extra tables in DB: {len(report['extra_in_db'])}")
    for table in report["extra_in_db"]:
        print(f"  - {table}")
    print(f"Legacy tables in DB: {len(report['legacy_in_db'])}")


def bootstrap_missing_tables() -> list[str]:
    report = schema_drift_report()
    missing_tables = report["missing_in_db"]
    if missing_tables:
        Base.metadata.create_all(bind=engine)
    return missing_tables


def upgrade_with_optional_bootstrap() -> list[str]:
    upgrade_to_head()
    if os.getenv("CCF_ALLOW_CREATE_ALL_BOOTSTRAP", "").lower() not in {
        "1",
        "true",
        "yes",
    }:
        return []
    return bootstrap_missing_tables()


def reset_database_for_local_bootstrap() -> None:
    settings = get_settings()
    env = (settings.environment or "local").strip().lower()
    if env not in {"local", "test"}:
        raise RuntimeError("Database reset is allowed only in local/test environments")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
