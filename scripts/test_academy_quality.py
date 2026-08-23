#!/usr/bin/env python3
"""Script de calidad canónico para el módulo Academy.

Ejecuta la suite completa de tests del módulo Academy (16 archivos).
Uso:
    cd /root/ccf && ./venv/bin/python scripts/test_academy_quality.py
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
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.quality_environment import QualityEnvironment

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


# All 16 academy test files
ACADEMY_TEST_FILES = [
    "tests/test_academy_api.py",
    "tests/test_academy_domain.py",
    "tests/test_academy_comprehensive.py",
    "tests/test_academy_backlog.py",
    "tests/test_academy_fase_1.py",
    "tests/test_academy_fase_2_audit.py",
    "tests/test_academy_fase_3_frontend.py",
    "tests/test_academy_fase_5_cleanup.py",
    "tests/test_academy_fase_5_cleanup_r2.py",
    "tests/test_academy_fase_6_to_100.py",
    "tests/test_academy_fase_7_transversal.py",
    "tests/test_academy_fase_7_tkt_204_a11y_gate.py",
    "tests/test_academy_fase_a_crit.py",
    "tests/test_academy_tkt_042_single_shell.py",
    "tests/test_academy_tkt_143_course_catalog_split.py",
    "tests/test_e2e_academy_tkt_202_gate.py",
]


def main() -> int:
    section("ACADEMY QUALITY — FULL SUITE (16 files)")
    info(f"Proyecto: {PROJECT_ROOT}")
    info(f"Python: {sys.executable}")
    try:
        quality_env = QualityEnvironment.from_process(require_api=False)
    except Exception as exc:
        fail(str(exc))
        return 1
    info(f"Entorno: {quality_env.describe()}")

    # Verify all test files exist
    missing = [f for f in ACADEMY_TEST_FILES if not (PROJECT_ROOT / f).is_file()]
    if missing:
        for f in missing:
            fail(f"Archivo no encontrado: {f}")
        return 1

    results: list[bool] = []

    # Group 1: Runtime / API tests
    results.append(
        run_pytest(
            "1. API y domain runtime",
            "tests/test_academy_api.py",
            "tests/test_academy_domain.py",
        )
    )

    # Group 2: Comprehensive suite
    results.append(
        run_pytest(
            "2. Comprehensive suite",
            "tests/test_academy_comprehensive.py",
        )
    )

    # Group 3: Backlog structural validation
    results.append(
        run_pytest(
            "3. Backlog estructural",
            "tests/test_academy_backlog.py",
        )
    )

    # Group 4: Fase A CRIT regression gates
    results.append(
        run_pytest(
            "4. Fase A CRIT (TKT-010..015)",
            "tests/test_academy_fase_a_crit.py",
        )
    )

    # Group 5: Fase 1-3 (schema, audit, frontend)
    results.append(
        run_pytest(
            "5. Fase 1-3 (schema, audit, frontend)",
            "tests/test_academy_fase_1.py",
            "tests/test_academy_fase_2_audit.py",
            "tests/test_academy_fase_3_frontend.py",
        )
    )

    # Group 6: Fase 5-6 (cleanup, closure)
    results.append(
        run_pytest(
            "6. Fase 5-6 (cleanup, closure)",
            "tests/test_academy_fase_5_cleanup.py",
            "tests/test_academy_fase_5_cleanup_r2.py",
            "tests/test_academy_fase_6_to_100.py",
        )
    )

    # Group 7: Fase 7 transversal (rate limit, cache, N+1)
    results.append(
        run_pytest(
            "7. Fase 7 transversal (rate limit, cache, N+1)",
            "tests/test_academy_fase_7_transversal.py",
        )
    )

    # Group 8: Ticket-specific tests
    results.append(
        run_pytest(
            "8. Ticket-specific (TKT-042, TKT-143)",
            "tests/test_academy_tkt_042_single_shell.py",
            "tests/test_academy_tkt_143_course_catalog_split.py",
        )
    )

    # Group 9: Gated tests (a11y, E2E) — may skip if not configured
    results.append(
        run_pytest(
            "9. Gated tests (a11y, E2E)",
            "tests/test_academy_fase_7_tkt_204_a11y_gate.py",
            "tests/test_e2e_academy_tkt_202_gate.py",
        )
    )

    section("RESUMEN")
    passed = sum(1 for r in results if r)
    failed = sum(1 for r in results if not r)
    total = len(results)

    if failed == 0:
        print(f"  {GREEN}RESUMEN: {passed}/{total} suites OK — ALL GREEN{NC}")
        return 0

    print(f"  {RED}RESUMEN: {passed} passed, {failed} failed, {total} total suites{NC}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
