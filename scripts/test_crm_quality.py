#!/usr/bin/env python3
"""Script de calidad canónico para el módulo CRM.

Uso:
    cd /root/ccf && ./venv/bin/python scripts/test_crm_quality.py
    cd /root/ccf && ./venv/bin/python scripts/test_crm_quality.py --backend-deep
    cd /root/ccf && ./venv/bin/python scripts/test_crm_quality.py --frontend-smoke
    cd /root/ccf && ./venv/bin/python scripts/test_crm_quality.py --frontend-deep
    cd /root/ccf && ./venv/bin/python scripts/test_crm_quality.py --expanded
    cd /root/ccf && ./venv/bin/python scripts/test_crm_quality.py --pipeline
    cd /root/ccf && ./venv/bin/python scripts/test_crm_quality.py --concurrency
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
    stream_output: bool = False


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
    if check.stream_output:
        result = subprocess.run(list(check.cmd), cwd=check.cwd, text=True)
    else:
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
            label="1. Smoke mínimo CRM",
            cmd=(
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "-o",
                "addopts=",
                "tests/test_crm_domain.py",
                "tests/test_crm_sede_isolation.py",
                "tests/test_crm_runtime_security.py",
            ),
            cwd=PROJECT_ROOT,
            reason="Base canónica: dominio, aislamiento por sede y seguridad runtime.",
        ),
        Check(
            label="2. RBAC HTTP-level",
            cmd=(
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "-o",
                "addopts=",
                "tests/test_crm_rbac_http.py",
            ),
            cwd=PROJECT_ROOT,
            reason="Valida 401/403/200 por rol en 15+ endpoints CRM.",
        ),
    ]

    if args.backend_deep or args.expanded:
        checks.append(
            Check(
                label="3. Cobertura amplia backend CRM",
                cmd=(
                    sys.executable,
                    "-m",
                    "pytest",
                    "-q",
                    "-o",
                    "addopts=",
                    "tests/test_crm_persona_mentorship.py",
                    "tests/test_crm_resource_bank.py",
                    "tests/test_crm_automations_dag.py",
                    "tests/test_crm_concurrency_adversarial.py",
                ),
                cwd=PROJECT_ROOT,
                reason="Mentoría, resource bank, automatizaciones DAG y concurrencia adversarial.",
            )
        )

    if args.pipeline or args.expanded:
        checks.append(
            Check(
                label="4. Pipeline visual y adversarial",
                cmd=(
                    sys.executable,
                    "-m",
                    "pytest",
                    "-q",
                    "-o",
                    "addopts=",
                    "tests/test_crm_visual.py",
                    "tests/test_crm_challenger_adversarial.py",
                ),
                cwd=PROJECT_ROOT,
                reason="Kanban visual, reorder y edge cases adversariales del pipeline.",
            )
        )

    if args.concurrency or args.expanded:
        checks.append(
            Check(
                label="5. Concurrencia y stress CRM",
                cmd=(
                    sys.executable,
                    "-m",
                    "pytest",
                    "-q",
                    "-o",
                    "addopts=",
                    "tests/test_crm_concurrency_adversarial.py",
                    "tests/test_crm_challenger_stress.py",
                    "tests/test_crm_stress.py",
                ),
                cwd=PROJECT_ROOT,
                reason="Race conditions, locks de reorder y stress con volumen alto.",
            )
        )

    if args.frontend_smoke or args.expanded:
        checks.append(
            Check(
                label="6. Smoke frontend CRM",
                cmd=("npm", "run", "test:e2e:crm"),
                cwd=FRONTEND_ROOT,
                reason="Smoke autenticado de dashboard, personas con búsqueda/detalle vivo y bridge de grupos, más coberturas mockeadas estables.",
                stream_output=True,
            )
        )

    if args.frontend_deep:
        checks.append(
            Check(
                label="7. Cobertura profunda frontend CRM",
                cmd=("npm", "run", "test:e2e:crm:deep"),
                cwd=FRONTEND_ROOT,
                reason="Dashboard, bridge de grupos, mensajería, recursos, pipeline y detalle de persona con contratos UI profundos del módulo.",
                stream_output=True,
            )
        )

    return checks


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--backend-deep",
        action="store_true",
        help="Incluye mentoría, resource bank, automations DAG y concurrencia.",
    )
    parser.add_argument(
        "--frontend-smoke",
        action="store_true",
        help="Incluye el smoke frontend CRM (`npm run test:e2e:crm`).",
    )
    parser.add_argument(
        "--frontend-deep",
        action="store_true",
        help="Incluye la cobertura profunda frontend (`npm run test:e2e:crm:deep`).",
    )
    parser.add_argument(
        "--expanded",
        action="store_true",
        help="Incluye backend ampliado + frontend smoke.",
    )
    parser.add_argument(
        "--pipeline",
        action="store_true",
        help="Incluye tests de pipeline visual y adversarial.",
    )
    parser.add_argument(
        "--concurrency",
        action="store_true",
        help="Incluye tests de concurrencia y stress.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    section("CRM QUALITY")
    info(f"Proyecto: {PROJECT_ROOT}")
    info(f"Python: {sys.executable}")
    info(
        "Modo: "
        + (
            "expandido"
            if args.expanded
            else "pipeline"
            if args.pipeline
            else "concurrency"
            if args.concurrency
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
