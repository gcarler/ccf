#!/usr/bin/env python3
"""Script de calidad canónico para plataforma compartida.

Uso:
    cd /root/ccf && ./venv/bin/python scripts/test_platform_quality.py
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


def main() -> int:
    section("PLATFORM SHARED QUALITY")
    info(f"Proyecto: {PROJECT_ROOT}")
    info(f"Python: {sys.executable}")

    auth_ok = run_command(
        "1. Auth v3 y perfil",
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-o",
            "addopts=",
            "tests/test_auth.py",
            "tests/test_auth_v3.py",
            "tests/test_auth_me.py",
        ],
    )

    contracts_ok = run_command(
        "2. Contratos estructurales de plataforma",
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-o",
            "addopts=",
            "tests/test_structural_contracts.py::test_frontend_does_not_add_auth_users_old_consumers",
            "tests/test_structural_contracts.py::test_auth_has_one_role_owner_and_no_removed_runtime_modules",
            "tests/test_structural_contracts.py::test_auth_and_scanner_have_no_parallel_fallback_contracts",
            "tests/test_arquitectura_100pct.py::test_auth_v3_uses_personas_uuid",
        ],
    )

    permissions_ok = run_command(
        "3. Permisos y core compartido",
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-o",
            "addopts=",
            "tests/test_permissions_and_more.py::TestAuthenticateUser",
            "tests/test_permissions_and_more.py::TestAuthModule",
            "tests/test_core_all.py",
        ],
    )

    section("RESUMEN")
    total = PASS + FAIL
    if auth_ok and contracts_ok and permissions_ok:
        print(f"  {GREEN}RESUMEN: {PASS} passed, {FAIL} failed, {total} total suites{NC}")
        return 0

    print(f"  {RED}RESUMEN: {PASS} passed, {FAIL} failed, {total} total suites{NC}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
