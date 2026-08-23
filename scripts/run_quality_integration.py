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
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

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
    parser.add_argument(
        "--auto-provision",
        action="store_true",
        help="Crea una base PostgreSQL y una API aisladas para esta suite, y las destruye al terminar.",
    )
    parser.add_argument(
        "--admin-database-url",
        default=os.environ.get("QUALITY_ADMIN_DATABASE_URL"),
        help="URL administrativa PostgreSQL; si falta, se deriva de DATABASE_URL solo para localhost.",
    )
    parser.add_argument(
        "--database-name",
        help="Nombre explícito de la base temporal; por defecto se genera uno por ejecución.",
    )
    parser.add_argument(
        "--api-port",
        type=int,
        help="Puerto de la API temporal; por defecto se reserva uno libre.",
    )
    return parser.parse_args()


def _local_admin_url() -> str:
    """Derive a safe local admin URL without ever guessing a remote database."""
    source = os.environ.get("DATABASE_URL") or os.environ.get("database_url")
    if not source:
        # The backend's local .env is the only implicit source allowed here;
        # Settings still rejects non-local deployment defaults, and the host
        # check below prevents deriving an admin URL for a remote database.
        try:
            from backend.core.config import Settings

            source = Settings().database_url
        except Exception:
            source = ""
    if not source:
        raise QualityEnvironmentError(
            "Falta QUALITY_ADMIN_DATABASE_URL; no se puede provisionar sin una URL administrativa explícita."
        )
    parsed = urlsplit(source)
    if parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise QualityEnvironmentError(
            "QUALITY_ADMIN_DATABASE_URL es obligatorio cuando DATABASE_URL no apunta a localhost."
        )
    return urlunsplit((parsed.scheme, parsed.netloc, "/postgres", "", ""))


def _reserve_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _safe_database_name(suite: str, run_id: str) -> str:
    suffix = re.sub(r"[^a-z0-9_]", "_", run_id.lower()).strip("_") or "run"
    name = f"ccf_quality_{suite}_{suffix}"
    return name[:63].rstrip("_")


def _database_url(admin_url: str, name: str) -> str:
    parsed = urlsplit(admin_url)
    return urlunsplit((parsed.scheme, parsed.netloc, f"/{name}", "", ""))


def _run_provisioner(database_url: str, admin_url: str, *, destroy: bool, env: dict[str, str]) -> None:
    command = [
        sys.executable,
        "scripts/provision_quality_database.py",
        "--database-url",
        database_url,
        "--admin-url",
        admin_url,
    ]
    if destroy:
        command.append("--destroy")
    result = subprocess.run(command, cwd=PROJECT_ROOT, env=env)
    if result.returncode:
        action = "destrucción" if destroy else "provisionamiento"
        raise QualityEnvironmentError(f"Falló la {action} de la base temporal (exit {result.returncode}).")


def _wait_for_api(api_url: str, process: subprocess.Popen[bytes]) -> None:
    deadline = time.monotonic() + 30
    last_error = "sin respuesta"
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise QualityEnvironmentError(f"La API temporal terminó prematuramente (exit {process.returncode}).")
        try:
            validate_api(QualityEnvironment(api_url=api_url, database_url="postgresql://local/quality", run_id="wait"))
            return
        except QualityEnvironmentError as exc:
            last_error = str(exc)
            time.sleep(0.5)
    raise QualityEnvironmentError(f"La API temporal no estuvo disponible: {last_error}")


def _terminate(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def provision_runtime(args: argparse.Namespace) -> tuple[QualityEnvironment, subprocess.Popen[bytes], str, str]:
    run_id = os.environ.get("QUALITY_RUN_ID") or f"prepush_{args.suite}_{os.getpid()}_{int(time.time())}"
    admin_url = args.admin_database_url or _local_admin_url()
    database_name = args.database_name or _safe_database_name(args.suite, run_id)
    database_url = _database_url(admin_url, database_name)
    api_port = args.api_port or _reserve_port()
    api_url = f"http://127.0.0.1:{api_port}"
    env = os.environ.copy()
    env.update({"QUALITY_RUN_ID": run_id, "DATABASE_URL": database_url, "database_url": database_url, "ENV": "local"})

    _run_provisioner(database_url, admin_url, destroy=False, env=env)
    api_env = {**env, "QUALITY_DATABASE_URL": database_url, "QUALITY_API_URL": api_url}
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", str(api_port)],
        cwd=PROJECT_ROOT,
        env=api_env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        _wait_for_api(api_url, process)
    except Exception:
        _terminate(process)
        try:
            _run_provisioner(database_url, admin_url, destroy=True, env=env)
        except Exception:
            pass
        raise
    return QualityEnvironment(database_url=database_url, api_url=api_url, run_id=run_id), process, admin_url, database_url


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
    process: subprocess.Popen[bytes] | None = None
    admin_url = ""
    owned_database_url = ""
    try:
        if args.auto_provision:
            environment, process, admin_url, owned_database_url = provision_runtime(args)
        else:
            environment = QualityEnvironment.from_process(require_api=True)
        validate_database(environment)
        validate_api(environment)
    except (QualityEnvironmentError, OSError) as exc:
        if process is not None:
            _terminate(process)
        if owned_database_url:
            cleanup_env = os.environ.copy()
            try:
                _run_provisioner(owned_database_url, admin_url, destroy=True, env=cleanup_env)
            except Exception as cleanup_exc:
                print(f"QUALITY_CLEANUP_ERROR: {cleanup_exc}", file=sys.stderr)
        print(f"QUALITY_ENVIRONMENT_ERROR: {exc}", file=sys.stderr)
        return 2

    try:
        child_env = environment.child_environment()
        if args.test_database_url:
            child_env["TEST_DATABASE_URL"] = args.test_database_url

        print(f"Quality integration environment: {environment.describe()}")
        command = SUITES[args.suite]
        result = subprocess.run(command, cwd=PROJECT_ROOT, env=child_env)
        return result.returncode
    finally:
        if process is not None:
            _terminate(process)
        if owned_database_url:
            cleanup_env = os.environ.copy()
            cleanup_env["QUALITY_RUN_ID"] = environment.run_id
            try:
                _run_provisioner(owned_database_url, admin_url, destroy=True, env=cleanup_env)
            except Exception as exc:
                print(f"QUALITY_CLEANUP_ERROR: {exc}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
