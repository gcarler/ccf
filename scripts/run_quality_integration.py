#!/usr/bin/env python3
"""Ejecutor determinista de suites de calidad de integración.

Este comando no crea una base implícita ni consulta una API fija. El entorno
debe ser provisionado por CI o por el operador y se valida antes de ejecutar
datos de prueba.

Ejemplos:
    QUALITY_DATABASE_URL=postgresql://... \
    QUALITY_API_URL=http://127.0.0.1:8000 \
    QUALITY_RUN_ID=local-20260823 \
    ./venv/bin/python scripts/run_quality_integration.py --suite projects
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

from sqlalchemy import create_engine, inspect, text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.quality_environment import QualityEnvironment, QualityEnvironmentError  # noqa: E402, I001


SUITES = {
    "academy": [sys.executable, "scripts/test_academy_quality.py"],
    "projects": [sys.executable, "scripts/test_projects_quality.py"],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", choices=sorted(SUITES), required=True)
    parser.add_argument(
        "--test-database-url",
        help="Base SQLite/DB para tests unitarios; no sustituye QUALITY_DATABASE_URL.",
    )
    return parser.parse_args()


def validate_database(environment: QualityEnvironment) -> None:
    engine = create_engine(environment.database_url, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            if connection.dialect.name != "postgresql":
                raise QualityEnvironmentError("La base de integración debe ser PostgreSQL.")
            extensions = {
                row[0]
                for row in connection.execute(
                    text("SELECT extname FROM pg_extension WHERE extname = 'citext'")
                )
            }
            if "citext" not in extensions:
                raise QualityEnvironmentError(
                    "La base de integración no tiene habilitada la extensión PostgreSQL citext."
                )
            if "alembic_version" not in inspect(connection).get_table_names():
                raise QualityEnvironmentError("La base de integración no tiene alembic_version.")
    finally:
        engine.dispose()


def validate_api(environment: QualityEnvironment) -> None:
    url = f"{environment.api_url}/openapi.json"
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            if response.status != 200:
                raise QualityEnvironmentError(f"La API respondió HTTP {response.status}: {url}")
    except urllib.error.URLError as exc:
        raise QualityEnvironmentError(f"No se pudo validar QUALITY_API_URL ({url}): {exc}") from exc


def main() -> int:
    args = parse_args()
    try:
        environment = QualityEnvironment.from_process(require_api=True)
        validate_database(environment)
        validate_api(environment)
    except (QualityEnvironmentError, OSError) as exc:
        print(f"QUALITY_ENVIRONMENT_ERROR: {exc}", file=sys.stderr)
        return 2

    child_env = environment.child_environment()
    if args.test_database_url:
        child_env["TEST_DATABASE_URL"] = args.test_database_url

    print(f"Quality integration environment: {environment.describe()}")
    command = SUITES[args.suite]
    result = subprocess.run(command, cwd=PROJECT_ROOT, env=child_env)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
