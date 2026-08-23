#!/usr/bin/env python3
"""Provisiona una base PostgreSQL aislada para calidad de integración.

La base se crea fuera de la base de aplicación, recibe sus extensiones y se
actualiza con la cadena Alembic canónica. El comando nunca reutiliza una base
existente silenciosamente.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from sqlalchemy import create_engine, inspect, text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATABASE_NAME_RE = re.compile(r"^[a-z_][a-z0-9_]{2,62}$")


def database_url_with_name(url: str, name: str) -> str:
    parsed = urlsplit(url)
    return urlunsplit((parsed.scheme, parsed.netloc, f"/{name}", "", ""))


def identifier(name: str) -> str:
    if not DATABASE_NAME_RE.fullmatch(name):
        raise ValueError(f"Nombre de base inválido: {name!r}")
    return f'"{name}"'


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", required=True)
    parser.add_argument(
        "--admin-url",
        default=os.environ.get("QUALITY_ADMIN_DATABASE_URL"),
        help="URL de una base administrativa del mismo PostgreSQL.",
    )
    parser.add_argument("--destroy", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    target = urlsplit(args.database_url)
    database_name = target.path.lstrip("/")
    if not args.admin_url:
        print("Falta --admin-url o QUALITY_ADMIN_DATABASE_URL", file=sys.stderr)
        return 2
    if not DATABASE_NAME_RE.fullmatch(database_name):
        print(f"Nombre de base inválido: {database_name!r}", file=sys.stderr)
        return 2

    admin = create_engine(database_url_with_name(args.admin_url, "postgres"))
    quoted_name = identifier(database_name)
    try:
        with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
            exists = connection.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": database_name},
            ).scalar()
            if args.destroy:
                if exists:
                    connection.execute(text(f"DROP DATABASE {quoted_name} WITH (FORCE)"))
                    print(f"Destroyed quality database: {database_name}")
                return 0
            if exists:
                print(
                    f"Quality database already exists: {database_name}. "
                    "Use --destroy explicitly before recreating it.",
                    file=sys.stderr,
                )
                return 2
            connection.execute(text(f"CREATE DATABASE {quoted_name}"))
    finally:
        admin.dispose()

    target_engine = create_engine(args.database_url)
    try:
        with target_engine.begin() as connection:
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS citext"))
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))
    finally:
        target_engine.dispose()

    env = os.environ.copy()
    env.update(
        {
            "DATABASE_URL": args.database_url,
            "database_url": args.database_url,
            "ENV": "local",
        }
    )
    baseline = "20260702_0001_canonical_baseline"
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", baseline],
        cwd=PROJECT_ROOT,
        env=env,
    )
    if result.returncode:
        print("Canonical baseline failed; destroy the isolated database before retrying.", file=sys.stderr)
        return result.returncode

    # The canonical baseline materializes the current ORM schema in one shot.
    # Later historical revisions describe changes already represented by that
    # snapshot, so replaying them would duplicate columns. Stamp head only
    # after the baseline has completed successfully.
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "stamp", "head"],
        cwd=PROJECT_ROOT,
        env=env,
    )
    if result.returncode:
        print("Alembic stamp failed; destroy the isolated database before retrying.", file=sys.stderr)
        return result.returncode

    fixture_env = {**env, "QUALITY_RUN_ID": os.environ.get("QUALITY_RUN_ID", database_name)}
    result = subprocess.run(
        [sys.executable, "scripts/seed_quality_fixtures.py"],
        cwd=PROJECT_ROOT,
        env=fixture_env,
    )
    if result.returncode:
        print("Quality fixtures failed; destroy the isolated database before retrying.", file=sys.stderr)
        return result.returncode

    with create_engine(args.database_url).connect() as connection:
        tables = set(inspect(connection).get_table_names())
        if "alembic_version" not in tables:
            print("Provisioned database has no alembic_version", file=sys.stderr)
            return 1
    print(f"QUALITY_DATABASE_URL={args.database_url}")
    print(f"Provisioned quality database: {database_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
