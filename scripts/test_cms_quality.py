#!/usr/bin/env python3
"""Script de calidad canónico para el módulo CMS.

Uso:
    cd /root/ccf && ./venv/bin/python scripts/test_cms_quality.py
"""

from __future__ import annotations

import os
import subprocess
import sys
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
    result = subprocess.run(cmd, cwd=cwd or PROJECT_ROOT, text=True, capture_output=True)
    if result.stdout.strip():
        for line in result.stdout.strip().splitlines():
            print(f"    {line}")
    if result.returncode == 0:
        ok(f"{label} OK")
        return True
    fail(f"{label} falló")
    if result.stderr.strip():
        for line in result.stderr.strip().splitlines()[:20]:
            print(f"    {line}")
    return False


def require_e2e_env() -> None:
    required = {
        "E2E_EMAIL": os.getenv("E2E_EMAIL", "").strip(),
        "E2E_PASSWORD": os.getenv("E2E_PASSWORD", "").strip(),
    }
    api_url = os.getenv("E2E_API_URL", "").strip() or os.getenv("API_BASE_URL", "").strip()
    if not api_url:
        required["E2E_API_URL_or_API_BASE_URL"] = ""
    missing = [key for key, value in required.items() if not value]
    if missing:
        raise RuntimeError(
            "Faltan variables E2E para CMS quality: "
            + ", ".join(missing)
            + ". Define E2E_EMAIL, E2E_PASSWORD y E2E_API_URL o API_BASE_URL."
        )


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

    frontend_e2e_ok = run_command(
        "3. Frontend CMS E2E",
        ["npm", "run", "test:e2e:cms"],
        cwd=PROJECT_ROOT / "frontend",
    )

    public_contract_ok = run_command(
        "4. Frontend CMS public contract",
        ["npm", "run", "test:e2e:cms:public"],
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
