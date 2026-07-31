#!/usr/bin/env python3
"""Script de calidad canónico para el módulo CMS.

Uso:
    cd /root/ccf && ./venv/bin/python scripts/test_cms_quality.py
"""

from __future__ import annotations

import contextlib
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve()
PROJECT_ROOT = next((p for p in HERE.parents if (p / "backend" / "__init__.py").is_file()), None)
if PROJECT_ROOT is None:
    raise RuntimeError(f"backend package not found above {HERE}")

os.chdir(PROJECT_ROOT)

GREEN = "\033[0;32m"
RED = "\033[0;31m"
BLUE = "\033[0;34m"
NC = "\033[0m"

PASS = 0
FAIL = 0


def section(title: str) -> None:
    print(f"\n{'=' * 64}")
    print(f"  {title}")
    print(f"{'=' * 64}")


def ok(message: str) -> None:
    global PASS
    PASS += 1
    print(f"  {GREEN}✓{NC} {message}")


def fail(message: str) -> None:
    global FAIL
    FAIL += 1
    print(f"  {RED}✗{NC} {message}")


def info(message: str) -> None:
    print(f"  {BLUE}ℹ{NC} {message}")


def run_command(label: str, cmd: list[str], cwd: Path | None = None) -> bool:
    section(label)
    info("Ejecutando: " + " ".join(cmd))
    # Stream output directly to avoid buffering deadlocks on long-running E2E steps.
    result = subprocess.run(cmd, cwd=cwd or PROJECT_ROOT, text=True)
    if result.returncode == 0:
        ok(f"{label} OK")
        return True
    fail(f"{label} falló")
    return False


def _clean_stale_next_lock() -> None:
    """Remove stale next-command.lock left by killed builds."""
    lock_dir = PROJECT_ROOT / "frontend" / ".next-command.lock"
    if not lock_dir.is_dir():
        return

    import datetime as _dt
    import time as _time

    try:
        info_json = (lock_dir / "owner.json").read_text(encoding="utf-8")
        lock_info = json.loads(info_json)
        pid = int(lock_info.get("pid", 0))
        created_at = lock_info.get("createdAt", "")
        created = _dt.datetime.fromisoformat(created_at) if created_at else None
    except Exception:
        pid = 0
        created = None

    try:
        alive = pid > 0 and os.kill(pid, 0) is None
    except (OSError, ProcessLookupError):
        alive = False

    now = _dt.datetime.now(_dt.timezone.utc)
    if not alive or (created and (now - created).total_seconds() > 600):
        import shutil as _shutil

        _shutil.rmtree(lock_dir, ignore_errors=True)
        info("Removed stale .next-command.lock")


def require_e2e_env() -> None:
    email = os.getenv("E2E_EMAIL", "").strip()
    password = os.getenv("E2E_PASSWORD", "").strip()
    required: dict[str, str] = {}
    if not email:
        required["E2E_EMAIL"] = ""
    if not password:
        required["E2E_PASSWORD"] = ""

    api_base = os.getenv("API_BASE_URL", "").strip() or "http://127.0.0.1:8000/api"
    e2e_api = os.getenv("E2E_API_URL", "").strip()

    if required:
        raise RuntimeError(
            "Faltan variables E2E para CMS quality: "
            + ", ".join(required.keys())
            + ". Define E2E_EMAIL, E2E_PASSWORD y E2E_API_URL o API_BASE_URL."
        )

    # E2E_API_URL must point to the host root; API_BASE_URL is the /api prefix.
    # If the caller only supplied API_BASE_URL, derive the root from it.
    if not e2e_api:
        e2e_api = api_base.rstrip("/")
        if e2e_api.endswith("/api"):
            e2e_api = e2e_api[: -len("/api")]
        os.environ["E2E_API_URL"] = e2e_api or "http://127.0.0.1:8000"
    else:
        os.environ["E2E_API_URL"] = e2e_api

    os.environ.setdefault("API_BASE_URL", api_base)


@contextlib.contextmanager
def managed_backend_server():
    """Ensure a backend server is running for E2E stages.

    If a server is already listening on 127.0.0.1:8000, reuse it. Otherwise
    start uvicorn for the lifetime of the E2E suite and terminate it when
    the context manager exits.
    """
    health_url = "http://127.0.0.1:8000/healthz"
    log_path = Path("/tmp/cms_backend_server.log")
    try:
        with urllib.request.urlopen(health_url, timeout=2) as response:
            if response.status == 200:
                info("Backend server already running at 127.0.0.1:8000 (will not stop it)")
                yield
                return
    except (urllib.error.URLError, ConnectionRefusedError, TimeoutError, OSError):
        pass

    info("Starting backend server for E2E tests")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT)
    env.setdefault("ENV_FILE", str(PROJECT_ROOT / "backend" / ".env"))
    log_file = log_path.open("w")
    try:
        proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8000"],
            cwd=PROJECT_ROOT,
            env=env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
        )
    except Exception as exc:
        log_file.close()
        raise RuntimeError(f"Failed to launch backend server: {exc}")
    started = False
    try:
        for _ in range(120):
            try:
                with urllib.request.urlopen(health_url, timeout=2) as response:
                    if response.status == 200:
                        started = True
                        break
            except (urllib.error.URLError, ConnectionRefusedError, TimeoutError):
                pass
            time.sleep(0.5)
        if not started:
            raise RuntimeError(f"Backend server did not start in time for E2E tests. See {log_path}")
        yield
    finally:
        info("Stopping backend server")
        if started:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
        else:
            proc.kill()
            try:
                proc.wait()
            except Exception:
                pass
        log_file.close()


def main() -> int:
    section("CMS QUALITY")
    info(f"Proyecto: {PROJECT_ROOT}")
    info(f"Python: {sys.executable}")

    backend_ok = run_command(
        "1. Backend CMS",
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-o",
            "addopts=",
            "tests/test_cms_domain.py",
            "tests/test_cms_sede_isolation.py",
            "tests/test_cms_upload_and_image_hardening.py",
            "tests/test_cms_metrics_sede_isolation.py",
        ],
    )

    frontend_ok = run_command(
        "2. Frontend CMS unit",
        ["npx", "vitest", "run", "tests/cms-components.test.ts", "tests/cms-public-fetch.test.ts"],
        cwd=PROJECT_ROOT / "frontend",
    )

    require_e2e_env()
    _clean_stale_next_lock()

    # Reuse the existing production build when available to avoid rebuilding
    # twice in the managed runner. If .next is missing, the managed runner will
    # build once before starting the server.
    has_frontend_build = (PROJECT_ROOT / "frontend" / ".next" / "BUILD_ID").is_file() or (
        PROJECT_ROOT / "frontend" / ".next" / "build-manifest.json"
    ).is_file()
    reuse_args = ["--reuse-build"] if has_frontend_build else []

    with managed_backend_server():
        frontend_e2e_smoke_ok = run_command(
            "3. Frontend CMS E2E smoke",
            [
                "node",
                "scripts/run-managed-playwright.mjs",
                "--auth",
                *reuse_args,
                "tests/e2e/cms/smoke.spec.ts",
            ],
            cwd=PROJECT_ROOT / "frontend",
        )
        frontend_e2e_preview_ok = run_command(
            "4. Frontend CMS E2E preview",
            [
                "node",
                "scripts/run-managed-playwright.mjs",
                *reuse_args,
                "tests/e2e/cms/pages-preview.spec.ts",
            ],
            cwd=PROJECT_ROOT / "frontend",
        )
        frontend_e2e_ok = frontend_e2e_smoke_ok and frontend_e2e_preview_ok

        public_contract_ok = run_command(
            "5. Frontend CMS public contract",
            [
                "node",
                "scripts/run-managed-playwright.mjs",
                *reuse_args,
                "tests/e2e/cms-public-contract.spec.ts",
            ],
            cwd=PROJECT_ROOT / "frontend",
        )

    section("RESUMEN")
    total = PASS + FAIL
    if backend_ok and frontend_ok and frontend_e2e_ok and public_contract_ok:
        print(f"  {GREEN}RESUMEN: {PASS} passed, {FAIL} failed, {total} total suites{NC}")
        return 0

    print(f"  {RED}RESUMEN: {PASS} passed, {FAIL} failed, {total} total suites{NC}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
