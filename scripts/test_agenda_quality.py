#!/usr/bin/env python3
"""Script de calidad canónico para Agenda / Calendar.

Uso:
    cd /root/ccf && ./venv/bin/python scripts/test_agenda_quality.py
    cd /root/ccf && ./venv/bin/python scripts/test_agenda_quality.py --backend-deep
    cd /root/ccf && ./venv/bin/python scripts/test_agenda_quality.py --frontend-smoke
"""

from __future__ import annotations

import argparse
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


def run_npx(label: str, *args: str) -> bool:
    section(label)
    frontend_dir = PROJECT_ROOT / "frontend"
    cmd = ["npx", "playwright", "test"] + list(args)
    info("Ejecutando: " + " ".join(cmd))
    result = subprocess.run(cmd, cwd=frontend_dir, text=True, capture_output=True)
    if result.stdout.strip():
        for line in result.stdout.strip().splitlines()[-20:]:
            print(f"    {line}")
    if result.returncode == 0:
        ok(f"{label} OK")
        return True
    fail(f"{label} falló")
    if result.stderr.strip():
        for line in result.stderr.strip().splitlines()[:10]:
            print(f"    {line}")
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Agenda/Calendar quality checks")
    parser.add_argument("--backend-deep", action="store_true", help="Run full backend test suite")
    parser.add_argument("--frontend-smoke", action="store_true", help="Run frontend smoke tests")
    parser.add_argument("--frontend-deep", action="store_true", help="Run full frontend e2e tests")
    args = parser.parse_args()

    section("AGENDA / CALENDAR QUALITY")
    info(f"Proyecto: {PROJECT_ROOT}")
    info(f"Python: {sys.executable}")

    api_ok = run_pytest(
        "1. CRUD Agenda (completo)",
        "tests/test_agenda_api.py",
        "tests/test_agenda_full.py",
    )

    routes_ok = run_pytest(
        "2. Rutas Agenda y Calendar",
        "tests/test_api_integration.py::TestAgendaAPI::test_list_events",
        "tests/test_api_integration.py::TestAgendaAPI::test_list_resources",
        "tests/test_api_comprehensive.py::TestAgendaEndpoints::test_agenda_events",
        "tests/test_fixed_routes.py::TestOtherFixed::test_agenda_events",
        "tests/test_fixed_routes.py::TestSystemFixed::test_calendar",
    )

    all_ok = api_ok and routes_ok

    if args.backend_deep:
        deep_ok = run_pytest(
            "3. Backend deep (schemas, dashboard, contract)",
            "tests/test_agenda_schemas.py",
            "tests/test_system_calendar_contract.py",
        )
        all_ok = all_ok and deep_ok

    if args.frontend_smoke:
        smoke_ok = run_npx(
            "4. Frontend smoke",
            "tests/e2e/agenda/smoke.spec.ts",
        )
        all_ok = all_ok and smoke_ok

    if args.frontend_deep:
        e2e_ok = run_npx(
            "5. Frontend e2e completo",
            "tests/e2e/agenda/",
        )
        all_ok = all_ok and e2e_ok

    section("RESUMEN")
    total = PASS + FAIL
    if all_ok:
        print(f"  {GREEN}RESUMEN: {PASS} passed, {FAIL} failed, {total} total suites{NC}")
        return 0

    print(f"  {RED}RESUMEN: {PASS} passed, {FAIL} failed, {total} total suites{NC}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
