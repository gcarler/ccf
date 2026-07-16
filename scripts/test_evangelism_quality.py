#!/usr/bin/env python3
"""Script de calidad canónico para el módulo Evangelismo.

Uso:
    cd /root/ccf && ./venv/bin/python scripts/test_evangelism_quality.py
    cd /root/ccf && ./venv/bin/python scripts/test_evangelism_quality.py --expanded
    cd /root/ccf && ./venv/bin/python scripts/test_evangelism_quality.py --frontend-smoke
    cd /root/ccf && ./venv/bin/python scripts/test_evangelism_quality.py --frontend-deep
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve()
PROJECT_ROOT = next((p for p in HERE.parents if (p / "backend" / "__init__.py").is_file()), None)
if PROJECT_ROOT is None:
    raise RuntimeError(f"backend package not found above {HERE}")

FRONTEND_ROOT = PROJECT_ROOT / "frontend"

os.chdir(PROJECT_ROOT)

GREEN = "\033[0;32m"
RED = "\033[0;31m"
BLUE = "\033[0;34m"
YELLOW = "\033[0;33m"
NC = "\033[0m"

PASS = 0
FAIL = 0


@dataclass(frozen=True)
class Check:
    label: str
    cmd: tuple[str, ...]
    cwd: Path
    optional: bool = False
    reason: str | None = None


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


def warn(message: str) -> None:
    print(f"  {YELLOW}!{NC} {message}")


def run_command(check: Check) -> bool:
    section(check.label)
    if check.reason:
        info(check.reason)
    info("Ejecutando: " + " ".join(check.cmd))
    result = subprocess.run(list(check.cmd), cwd=check.cwd, text=True, capture_output=True)
    if result.stdout.strip():
        for line in result.stdout.strip().splitlines():
            print(f"    {line}")
    if result.returncode == 0:
        ok(f"{check.label} OK")
        return True
    if check.optional:
        warn(f"{check.label} no pasó y queda como validación opcional")
    else:
        fail(f"{check.label} falló")
    if result.stderr.strip():
        for line in result.stderr.strip().splitlines()[:20]:
            print(f"    {line}")
    return False


def build_checks(args: argparse.Namespace) -> list[Check]:
    checks = [
        Check(
            label="1. Smoke mínimo Evangelismo",
            cmd=(
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "-o",
                "addopts=",
                "tests/test_evangelism_triple7_flow.py",
                "tests/test_evangelism_crm_bridge.py",
                "tests/test_evangelism_reports_api.py",
                "tests/test_calculo_sesiones.py",
            ),
            cwd=PROJECT_ROOT,
            reason="Base canónica para detectar regresiones del flujo principal.",
        ),
        Check(
            label="2. Regresiones críticas Evangelismo",
            cmd=(
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "-o",
                "addopts=",
                "tests/test_evangelism_habilitacion_regression.py",
                "tests/test_evangelism_custom_role_regression.py",
            ),
            cwd=PROJECT_ROOT,
            reason="Protege habilitación de sesiones y roles personalizados.",
        ),
    ]

    if args.backend_deep or args.expanded:
        checks.append(
            Check(
                label="3. Cobertura amplia backend Evangelismo",
                cmd=(
                    sys.executable,
                    "-m",
                    "pytest",
                    "-q",
                    "-o",
                    "addopts=",
                    "tests/test_evangelism_module_coverage.py",
                ),
                cwd=PROJECT_ROOT,
                reason="Validación amplia de contratos, aliases, eventos, follow-up y multiplicación.",
            )
        )

    if args.frontend_smoke or args.expanded:
        checks.append(
            Check(
                label="4. Smoke frontend Evangelismo",
                cmd=("npm", "run", "test:e2e:evangelism"),
                cwd=FRONTEND_ROOT,
                reason=(
                    "Ejecuta el comando oficial del módulo (smoke autenticado + cobertura profunda mockeada)."
                ),
            )
        )

    if args.frontend_deep:
        checks.append(
            Check(
                label="5. Cobertura profunda frontend Evangelismo",
                cmd=("npm", "run", "test:e2e:evangelism:deep"),
                cwd=FRONTEND_ROOT,
                reason="Aísla sesiones, rankings, multiplication, events y scanner sobre webServer administrado.",
            )
        )

    return checks


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--backend-deep",
        action="store_true",
        help="Incluye la suite amplia backend tests/test_evangelism_module_coverage.py.",
    )
    parser.add_argument(
        "--frontend-smoke",
        action="store_true",
        help="Incluye el comando oficial frontend del módulo (`npm run test:e2e:evangelism`).",
    )
    parser.add_argument(
        "--frontend-deep",
        action="store_true",
        help="Incluye la cobertura profunda frontend (`npm run test:e2e:evangelism:deep`).",
    )
    parser.add_argument(
        "--expanded",
        action="store_true",
        help="Incluye validación amplia backend y el comando oficial frontend del módulo.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    section("EVANGELISM QUALITY")
    info(f"Proyecto: {PROJECT_ROOT}")
    info(f"Python: {sys.executable}")
    info(
        "Modo: "
        + (
            "expandido"
            if args.expanded
            else "base + frontend profundo"
            if args.frontend_deep
            else "base + backend profundo"
            if args.backend_deep
            else "base + frontend smoke"
            if args.frontend_smoke
            else "base"
        )
    )

    checks = build_checks(args)
    results = [run_command(check) for check in checks]

    section("RESUMEN")
    total = PASS + FAIL
    if all(results):
        print(f"  {GREEN}RESUMEN: {PASS} passed, {FAIL} failed, {total} total suites{NC}")
        return 0

    print(f"  {RED}RESUMEN: {PASS} passed, {FAIL} failed, {total} total suites{NC}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
