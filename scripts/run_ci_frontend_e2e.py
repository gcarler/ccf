#!/usr/bin/env python3
"""Run the existing no-@auth browser suite against a disposable local backend.

The caller supplies a fresh PostgreSQL CI service. This script owns its schema,
fixtures, backend process and temporary files; it never drops a database/schema.
The migration gate remains a separate check: browser fixtures use ORM metadata.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path, PurePosixPath
from urllib.error import URLError
from urllib.parse import unquote, urlsplit
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


def validate_database(environ: dict[str, str]) -> str:
    """Reject remote, shared, unconfirmed and inconsistent targets before I/O."""
    value = environ.get("DATABASE_URL", "")
    target = urlsplit(value)
    database = unquote(target.path.lstrip("/"))
    if target.scheme not in {"postgresql", "postgresql+psycopg", "postgresql+psycopg2"}:
        raise ValueError("DATABASE_URL must use PostgreSQL")
    if target.hostname not in {"127.0.0.1", "localhost", "::1"} or target.query or target.fragment:
        raise ValueError("PostgreSQL must be loopback-only with no URL options")
    if not re.fullmatch(r"ccf_e2e_[a-z0-9_]+", database):
        raise ValueError("Disposable database name must start with ccf_e2e_")
    if environ.get("CCF_E2E_DATABASE_CONFIRM") != database:
        raise ValueError("CCF_E2E_DATABASE_CONFIRM must exactly match the disposable database")
    if environ.get("TEST_DATABASE_URL") != value:
        raise ValueError("DATABASE_URL and TEST_DATABASE_URL must be identical")
    return value


def free_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def seed_schema() -> None:
    """Only called in a fresh subprocess with the validated environment."""
    validate_database(dict(os.environ))
    sys.path.insert(0, str(ROOT))
    from sqlalchemy import inspect, text

    import backend.models  # noqa: F401
    from backend.core.database import Base, engine

    with engine.begin() as connection:
        if inspect(connection).get_table_names():
            raise RuntimeError("E2E database must be empty; recreate the disposable CI service")
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS citext"))
        Base.metadata.create_all(connection)
    engine.dispose()


def seed_theme() -> None:
    validate_database(dict(os.environ))
    sys.path.insert(0, str(ROOT))
    from backend import models
    from backend.core.database import SessionLocal

    with SessionLocal() as session:
        actor = session.query(models.Usuario).filter_by(email="e2e.admin@ccf.local").one()
        site = session.query(models.CmsSite).filter_by(site_key="ccf").one()
        if not session.query(models.CmsTheme).filter_by(site_id=site.id, is_active=True).first():
            session.add(models.CmsTheme(
                site_id=site.id,
                name="CI public contract",
                tokens_json={},
                is_active=True,
                status="active",
                created_by_persona_id=actor.id,
                updated_by_persona_id=actor.id,
            ))
        # The existing Academy multi-role test requires a published catalog entry.
        if not session.query(models.Course).filter_by(code="CI-E2E").first():
            session.add(models.Course(
                code="CI-E2E",
                title="CI Academy course",
                modality="non_formal",
                is_published=True,
                sede_id=None,
            ))
        session.commit()



def _cms_media_references(value: object) -> set[str]:
    """Read local media URLs from nested CMS properties, including JSON strings."""
    if isinstance(value, dict):
        return set().union(*(_cms_media_references(item) for item in value.values()))
    if isinstance(value, (list, tuple)):
        return set().union(*(_cms_media_references(item) for item in value))
    if not isinstance(value, str):
        return set()
    stripped = value.strip()
    if stripped.startswith(("{", "[")):
        try:
            return _cms_media_references(json.loads(stripped))
        except json.JSONDecodeError:
            return set()
    parsed = urlsplit(stripped)
    if not parsed.scheme and not parsed.netloc and parsed.path.startswith("/api/static/cms/"):
        return {stripped}
    return set()


def create_fixture_media(value: object, environ: dict[str, str]) -> dict[str, Path]:
    """Materialize synthetic images only in the disposable runner's upload tree."""
    validate_database(environ)
    scratch = Path(environ.get("CCF_E2E_WORKDIR", ""))
    uploads = Path(environ.get("UPLOADS_DIR", ""))
    if (
        not scratch.is_absolute()
        or scratch.is_symlink()
        or scratch.parent.resolve() != Path(tempfile.gettempdir()).resolve()
        or not re.fullmatch(r"ccf-e2e-[a-zA-Z0-9_-]+", scratch.name)
        or uploads != scratch / "uploads"
        or uploads.is_symlink()
        or not uploads.is_dir()
        or not (scratch / ".ccf-e2e-owner").is_file()
        or (scratch / ".ccf-e2e-owner").read_text() != "run_ci_frontend_e2e"
    ):
        raise ValueError("Media fixtures require the runner-owned temporary upload directory")
    root = uploads.resolve()
    targets = {}
    for url in sorted(_cms_media_references(value)):
        decoded = unquote(urlsplit(url).path)
        relative = decoded.removeprefix("/api/static/")
        if (
            "\\" in relative
            or "\x00" in relative
            or "%" in relative
            or any(part in {".", "..", ""} for part in relative.split("/"))
            or PurePosixPath(relative).suffix.lower() != ".webp"
        ):
            raise ValueError("CMS media fixture contains an unsafe path or unsupported image type")
        destination = (root / relative).resolve()
        if not destination.is_relative_to(root / "cms"):
            raise ValueError("CMS media fixture escapes the temporary upload directory")
        targets[url] = destination
    from PIL import Image

    for destination in targets.values():
        destination.parent.mkdir(parents=True, exist_ok=True)
        # Exclusive creation preserves files already owned by another fixture.
        if not destination.exists():
            with destination.open("xb") as stream:
                Image.new("RGB", (16, 16), color=(64, 96, 128)).save(stream, format="WEBP")
    return targets


def public_fallback_media_references(public_root: Path) -> set[str]:
    """Include local fallback images embedded in the public renderer contract."""
    references: set[str] = set()
    pattern = re.compile(r"[\"'](/api/static/cms/[A-Za-z0-9_./-]+\.webp)[\"']")
    for source in public_root.rglob("*.tsx"):
        if source.name.endswith((".test.tsx", ".stories.tsx")):
            continue
        references.update(pattern.findall(source.read_text()))
    return references


def seed_media() -> None:
    """Resolve references from the actual isolated CMS fixtures, never production."""
    validate_database(dict(os.environ))
    sys.path.insert(0, str(ROOT))
    from backend import models
    from backend.core.database import SessionLocal

    with SessionLocal() as session:
        fixture_values = [
            value
            for column in (
                models.CmsSection.props_json,
                models.CmsMediaItem.url,
                models.CmsPost.featured_image_url,
                models.Persona.photo_url,
            )
            for (value,) in session.query(column).all()
        ]
    fixture_values.extend(public_fallback_media_references(ROOT / "frontend/src/app/(public)"))
    targets = create_fixture_media(fixture_values, dict(os.environ))
    print(f"Prepared {len(targets)} local CMS image fixtures in temporary uploads", flush=True)

def wait_backend(process: subprocess.Popen, url: str) -> None:
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("Isolated E2E backend exited before readiness")
        try:
            with urlopen(f"{url}/api/system/health", timeout=2) as response:
                if response.status == 200:
                    return
        except (URLError, TimeoutError):
            pass
        time.sleep(0.25)
    raise RuntimeError("Isolated E2E backend did not become ready within 90 seconds")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-only", action="store_true", help="Validate target without connecting or building")
    parser.add_argument("--seed-schema", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--seed-theme", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--seed-media", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("specs", nargs="*", help="Optional existing Playwright spec paths for focused diagnosis")
    args = parser.parse_args()
    database_url = validate_database(dict(os.environ))
    if args.check_only:
        print("Disposable PostgreSQL target guards passed; no connection or build attempted")
        return 0
    if args.seed_schema:
        seed_schema()
        return 0
    if args.seed_theme:
        seed_theme()
        return 0
    if args.seed_media:
        seed_media()
        return 0

    with tempfile.TemporaryDirectory(prefix="ccf-e2e-") as directory:
        scratch = Path(directory)
        backend_url = f"http://127.0.0.1:{free_port()}"
        env = {
            **os.environ,
            "ENV": "test",
            "ENVIRONMENT": "test",
            "environment": "test",
            "DATABASE_URL": database_url,
            "database_url": database_url,
            "TEST_DATABASE_URL": database_url,
            "SECRET_KEY": secrets.token_urlsafe(48),
            "STUB_COMMS": "true",
            "TEST_EMAIL_OVERRIDE": "",
            "REDIS_URL": "redis://127.0.0.1:1/0",
            "UPLOADS_DIR": str(scratch / "uploads"),
            "CCF_E2E_WORKDIR": str(scratch),
            "CCF_RUNTIME_DIR": str(scratch / "runtime"),
            "ANALYTICS_DB_PATH": str(scratch / "analytics.duckdb"),
            "API_PROXY_TARGET": backend_url,
            "API_BASE_URL": f"{backend_url}/api",
            "E2E_API_URL": f"{backend_url}/api",
            "NEXT_PUBLIC_API_URL": "/api",
            "PLAYWRIGHT_BASE_URL": "",
            "PLAYWRIGHT_REUSE_EXISTING_SERVER": "0",
            "E2E_AUTH_ENABLED": "0",
            "PYTHON_BIN": sys.executable,
            "PYTHONPATH": str(ROOT),
            "PYTHONUNBUFFERED": "1",
        }
        (scratch / "uploads").mkdir()
        (scratch / ".ccf-e2e-owner").write_text("run_ci_frontend_e2e")

        def run(command: list[str], *, cwd: Path = ROOT) -> None:
            print(f"CI E2E phase: {' '.join(command[1:])}", flush=True)
            subprocess.run(command, cwd=cwd, env=env, check=True)

        run([sys.executable, str(Path(__file__).resolve()), "--seed-schema"], cwd=scratch)
        for script in (
            "seed_public_cms_v2_sections.py",
            "seed_public_url_pages.py",
            "seed_public_menus_and_footer.py",
        ):
            run([sys.executable, str(ROOT / "scripts" / script)], cwd=scratch)

        run([sys.executable, str(Path(__file__).resolve()), "--seed-media"], cwd=scratch)

        backend = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", backend_url.rsplit(":", 1)[1]],
            cwd=scratch,
            env=env,
        )
        try:
            wait_backend(backend, backend_url)
            run(["node", "tests/e2e/academy/seed-academy-roles.mjs"], cwd=ROOT / "frontend")
            run([sys.executable, str(Path(__file__).resolve()), "--seed-theme"], cwd=scratch)
            # Preserve the workflow's existing test selection; do not hide failures.
            run(["node", "scripts/run-managed-playwright.mjs", "--grep-invert", "@auth", *args.specs], cwd=ROOT / "frontend")
        finally:
            backend.terminate()
            try:
                backend.wait(timeout=10)
            except subprocess.TimeoutExpired:
                backend.kill()
                backend.wait()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, RuntimeError) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1) from None
