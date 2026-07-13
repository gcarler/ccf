#!/usr/bin/env python3
"""Compare SQLAlchemy model tables with the configured database schema.

This script is intentionally read-only. It loads the canonical model barrel,
reflects the live database, and reports missing/extra tables and columns.
Use it with the same ENV_FILE as the backend process:

    ENV_FILE=backend/.env python scripts/audit_backend_schema.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("ENV_FILE", "backend/.env")

from sqlalchemy import inspect  # noqa: E402

from backend import models  # noqa: F401,E402
from backend.core.database import engine  # noqa: E402
from backend.models_shared import Base  # noqa: E402


def _column_names(table: Any) -> set[str]:
    return {column.name for column in table.columns}


def main() -> int:
    inspector = inspect(engine)
    db_tables = set(inspector.get_table_names())
    model_tables = set(Base.metadata.tables)

    missing_tables = sorted(model_tables - db_tables)
    extra_tables = sorted(db_tables - model_tables)

    table_diffs: dict[str, dict[str, list[str]]] = {}
    for table_name in sorted(model_tables & db_tables):
        model_columns = _column_names(Base.metadata.tables[table_name])
        db_columns = {column["name"] for column in inspector.get_columns(table_name)}
        missing_columns = sorted(model_columns - db_columns)
        extra_columns = sorted(db_columns - model_columns)
        if missing_columns or extra_columns:
            table_diffs[table_name] = {
                "missing_columns": missing_columns,
                "extra_columns": extra_columns,
            }

    blocking_table_diffs = {
        table_name: diff for table_name, diff in table_diffs.items() if diff["missing_columns"]
    }

    payload = {
        "database_url_driver": engine.url.drivername,
        "model_table_count": len(model_tables),
        "db_table_count": len(db_tables),
        "missing_tables": missing_tables,
        "extra_tables": extra_tables,
        "table_diffs": table_diffs,
        "blocking_table_diffs": blocking_table_diffs,
    }
    print(json.dumps(payload, indent=2, sort_keys=True, default=str))
    return 1 if missing_tables or blocking_table_diffs else 0


if __name__ == "__main__":
    raise SystemExit(main())
