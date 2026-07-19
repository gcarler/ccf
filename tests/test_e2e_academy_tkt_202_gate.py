"""
TKT-202 — pytest regression gate for the multi-role Playwright suite.

Logic:
    * Skips by default — pytest collection stays green even when the
      Playwright harness has no backend / browser binary available.
    * When ``E2E_GATE_RUN=1`` is exported, the test invokes the managed
      Playwright runner (frontend/scripts/run-managed-playwright.mjs)
      with the multi-role spec file and the ``--academy-roles`` flag
      that triggers 4-user seeding.
    * Pytest fails (non-zero exit) iff ``npx playwright test`` exits
      non-zero. The captured stdout/stderr is surfaced inline for the
      failing engineer to triage.

Why a managed wrapper, not a raw `npx playwright test`:
    * Build + server boot + seed order. ``run-managed-playwright.mjs``
      already wires all three; creating a parallel invocation would
      duplicate env-management code we already trust.
    * Idempotency. The seeder already runs idempotently (re-running only
      updates password/role/sede). Repeating the gate on a subset of
      files therefore leaves seeded data healthier instead of brighter.

Operation:
    E2E_GATE_RUN=1 E2E_API_URL=http://127.0.0.1:8000/api \
        PYTHON_BIN=./venv/bin/python pytest -q tests/test_e2e_academy_tkt_202_gate.py

No-ops when the env vars are missing: this keeps the suite compatible
with platform machines that don't have a Postgres + FastAPI backend.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC_RELATIVE = "frontend/tests/e2e/academy/multi-role-flow.spec.ts"
WRAPPER_RELATIVE = "frontend/scripts/run-managed-playwright.mjs"


@pytest.mark.tkt202
def test_tkt_202_playwright_academy_multi_role_gate() -> None:
    """Gate para ACAD-TKT-202.: Playwright multi-role multi-flujo Academy.

    Skipped por defecto. Activado con ``E2E_GATE_RUN=1``. Falla pytest
    exactamente cuando Playwright retorna exit code != 0.
    """
    if os.environ.get("E2E_GATE_RUN") != "1":
        pytest.skip(
            "Gate opt-in: ejecuta con E2E_GATE_RUN=1 "
            "(ver docstring del módulo para el comando completo)."
        )

    frontend_dir = REPO_ROOT / "frontend"
    spec_path = frontend_dir / "tests" / "e2e" / "academy" / "multi-role-flow.spec.ts"
    wrapper_path = frontend_dir / "scripts" / "run-managed-playwright.mjs"

    if not spec_path.exists():
        pytest.fail(
            f"Playwright multi-role spec no encontrado en {spec_path}. "
            "Fixture del TKT-202 incompleta."
        )
    if not wrapper_path.exists():
        pytest.fail(
            f"Wrapper {wrapper_path} no encontrado — el gate depende de "
            "run-managed-playwright.mjs para construir, servir y seedear."
        )

    node_binary = shutil.which("node") or shutil.which("nodejs")
    if not node_binary:
        pytest.fail(
            "`node` no disponible en PATH — el gate necesita Node >=18 "
            "para invocar el wrapper Playwright."
        )

    cmd = [node_binary, str(wrapper_path), "--academy-roles", SPEC_RELATIVE]
    print(f"[tkt-202-gate] Ejecutando: {' '.join(cmd)} (cwd={frontend_dir})")

    env = os.environ.copy()
    env.setdefault("PLAYWRIGHT_MANAGED_WEBSERVER", "1")

    result = subprocess.run(
        cmd,
        cwd=str(frontend_dir),
        env=env,
        capture_output=True,
        text=True,
    )

    # Always surface the wrapper's output for triage when the gate fails.
    if result.stdout:
        print("[tkt-202-gate] STDOUT:\n" + result.stdout[-4000:])
    if result.stderr:
        print("[tkt-202-gate] STDERR:\n" + result.stderr[-4000:])

    assert result.returncode == 0, (
        f"Playwright multi-role Academy suite FAILED con exit={result.returncode}. "
        "El wrapper ya construyó, seeded (4 usuarios) y sirvió la app — "
        "mirar STDOUT/STDERR arriba para el detalle del fallo."
    )
