#!/usr/bin/env python3
"""Script de calidad canónico para el módulo CRM.

Uso:
    cd /root/ccf && ./venv/bin/python scripts/test_crm_quality.py
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


def run_pytest(label: str, *tests: str) -> bool:
    section(label)
    cmd = [sys.executable, "-m", "pytest", "-q", "-o", "addopts="]
    cmd.extend(tests)
    info("Ejecutando: " + " ".join(tests))
    result = subprocess.run(cmd, cwd=PROJECT_ROOT, text=True, capture_output=True)
    output = result.stdout.strip()
    if output:
        for line in output.splitlines():
            print(f"    {line}")
    if result.returncode == 0:
        ok(f"{label} OK")
        return True
    fail(f"{label} falló")
    err = result.stderr.strip()
    if err:
        for line in err.splitlines()[:20]:
            print(f"    {line}")
    return False


def main() -> int:
    section("CRM QUALITY")
    info(f"Proyecto: {PROJECT_ROOT}")
    info(f"Python: {sys.executable}")

    smoke_ok = run_pytest(
        "1. Smoke mínimo CRM",
        "tests/test_crm_domain.py",
        "tests/test_crm_sede_isolation.py",
        "tests/test_crm_runtime_security.py",
    )

    extended_ok = run_pytest(
        "2. Flujos sensibles CRM",
        "tests/test_crm_persona_mentorship.py",
        "tests/test_crm_resource_bank.py",
    )

    section("RESUMEN")
    total = PASS + FAIL
    if smoke_ok and extended_ok:
        print(f"  {GREEN}RESUMEN: {PASS} passed, {FAIL} failed, {total} total suites{NC}")
        return 0

    print(f"  {RED}RESUMEN: {PASS} passed, {FAIL} failed, {total} total suites{NC}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
