from __future__ import annotations

import argparse
import datetime as dt
import os
import shutil
import subprocess
from pathlib import Path

from sqlalchemy.engine.url import make_url

from backend.core.config import get_settings


def backup_database(target_dir: str) -> Path:
    settings = get_settings()
    url = make_url(settings.database_url)
    timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S")
    target = Path(target_dir)
    target.mkdir(parents=True, exist_ok=True)

    if url.get_backend_name().startswith("sqlite"):
        source = Path(url.database or "")
        if not source.exists():
            raise FileNotFoundError(f"SQLite database not found: {source}")
        destination = target / f"sqlite-backup-{timestamp}.db"
        shutil.copy(source, destination)
        return destination

    if url.get_backend_name().startswith("postgres"):
        destination = target / f"postgres-backup-{timestamp}.dump"
        env = os.environ.copy()
        if url.host:
            env["PGHOST"] = url.host
        if url.port:
            env["PGPORT"] = str(url.port)
        if url.username:
            env["PGUSER"] = url.username
        if url.password:
            env["PGPASSWORD"] = url.password
        command = [
            "pg_dump",
            "-Fc",
            "-d",
            url.database,
            "-f",
            str(destination),
        ]
        subprocess.run(command, check=True, env=env)
        return destination

    raise RuntimeError("Unsupported database for backup")


def main() -> None:
    parser = argparse.ArgumentParser(description="Backup primary database")
    parser.add_argument("--dest", default="backups", help="Destination folder")
    args = parser.parse_args()
    path = backup_database(args.dest)
    print(f"Backup created at {path}")


if __name__ == "__main__":  # pragma: no cover
    main()
