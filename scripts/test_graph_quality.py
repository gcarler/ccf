#!/usr/bin/env python3
"""Script de calidad canónico para el módulo Graph.

Uso:
    cd /root/ccf && ./venv/bin/python scripts/test_graph_quality.py
    cd /root/ccf && ./venv/bin/python scripts/test_graph_quality.py --backend-deep

Cierra ``PEND-GRAPH-001`` (artefacto #6/6 del plan 6/6 del módulo Graph).

Ancla:
    - ``DONE-GRAPH-ASSETITEM-GUARD-001`` (graceful degradation de AssetItem)
    - ``DONE-GRAPH-USER-SEDE-NULL-GUARD-001`` (PEND-GRAPH-007 hardenization)
    - ``DECISION-GRAPH-SENTINEL-001`` (vista global sólo para roles de
      plataforma)

Documentos canónicos (cross-reference):
    - ``docs/GRAPH_API_CONTRACTS.md``
    - ``docs/GRAPH_QA_CHECKLIST.md``
    - ``docs/GRAPH_RBAC_MATRIX.md`` §6.5 (anclaje tests post-hardening)
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve()
PROJECT_ROOT = next(
    (p for p in HERE.parents if (p / "backend" / "__init__.py").is_file()), None
)
if PROJECT_ROOT is None:
    raise RuntimeError(f"backend package not found above {HERE}")

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
    result = subprocess.run(
        list(check.cmd), cwd=check.cwd, text=True, capture_output=True
    )
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
    """Construye el set de checks según los flags CLI.

    ``--backend-deep`` añade la suite de servicios relacionados
    (``_has_model`` helper usada en graceful degradation de AssetItem) y
    el helper ``get_user_sede_id`` desde ``backend/core/tenant.py``.
    """
    checks = [
        Check(
            label="1. Suite dedicada Graph (10/10 tests)",
            cmd=(
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "-o",
                "addopts=",
                "tests/test_graph_api.py",
            ),
            cwd=PROJECT_ROOT,
            reason=(
                "Cubre PEND-GRAPH-007 (DECISION-GRAPH-SENTINEL-001), graceful "
                "degradation de AssetItem (DONE-GRAPH-ASSETITEM-GUARD-001) "
                "y los 3 tests de anclaje post-hardening del RBAC matrix §6.5. "
                "Backend mínimo para el módulo Graph."
            ),
        ),
    ]

    if args.backend_deep:
        checks.append(
            Check(
                label="2. Backend profundo Graph (servicios cross-module)",
                cmd=(
                    sys.executable,
                    "-m",
                    "pytest",
                    "-q",
                    "-o",
                    "addopts=",
                    "tests/test_services_round2_coverage.py",
                    "tests/test_services_final_push.py",
                    "tests/test_crm_visual_stress.py::test_user_sede_isolation",
                ),
                cwd=PROJECT_ROOT,
                reason=(
                    "Cubre el helper ``_has_model`` usado en graceful degradation "
                    "de AssetItem (DONE-GRAPH-ASSETITEM-GUARD-001), el helper "
                    "``get_user_sede_id`` desde ``backend/core/tenant.py`` "
                    "(motor del sentinel), y la suite de aislamiento de sede "
                    "(Axioma 3) para actores cross-sede."
                ),
            ),
        )

    return checks


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--backend-deep",
        action="store_true",
        help=(
            "Incluye tests de servicios relacionados con ``_has_model`` "
            "(graceful degradation), get_user_sede_id y aislamiento sede."
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    section("GRAPH QUALITY")
    info(f"Proyecto: {PROJECT_ROOT}")
    info(f"Python: {sys.executable}")
    info("Modo: " + ("backend profundo" if args.backend_deep else "base"))

    checks = build_checks(args)
    results = [run_command(check) for check in checks]

    section("RESUMEN")
    total = PASS + FAIL
    if all(results):
        print(
            f"  {GREEN}RESUMEN: {PASS} passed, {FAIL} failed, "
            f"{total} total suites{NC}"
        )
        return 0

    print(
        f"  {RED}RESUMEN: {PASS} passed, {FAIL} failed, "
        f"{total} total suites{NC}"
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
