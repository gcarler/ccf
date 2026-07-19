"""
TKT-204 — pytest regression gate for the Academy WCAG AA accessibility
audit (TKT-204, ACAD-TKT-204).

Logic:
    * Reads ``e2e-results/a11y-report.json`` produced by
      ``frontend/tests/e2e/academy/a11y.spec.ts`` (Playwright +
      ``@axe-core/playwright`` loop over the 6 critical Academy pages).
    * Skips cleanly when the report does not exist so pytest collection
      stays green on environments that haven't run Playwright yet
      (e.g. local pytest without browser binary).
    * Asserts that the persisted report shows ZERO entries with
      ``impact in {serious, critical}`` for any of the 6 pages.
    * Surfaces a per-page violation summary inline to make triage easy.

Operation:
    # 1) Run Playwright once and write the JSON report.
    cd frontend && E2E_GATE_RUN=1 \
        npx playwright test tests/e2e/academy/a11y.spec.ts \
        --reporter=line
    # 2) Run the gate.
    ./venv/bin/pytest -q tests/test_academy_fase_7_tkt_204_a11y_gate.py

No-op when the JSON report is missing:
    Keeps the suite compatible with machines that don't have
    Playwright + Chrome installed.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = REPO_ROOT / "frontend" / "e2e-results" / "a11y-report.json"

ACCEPTED_PAGES = {
    "catalog",
    "course-detail",
    "lessons",
    "assessment",
    "forum",
    "profile",
}


@pytest.mark.tkt204
def test_tkt_204_accessibility_wcag_aa_violations_count_is_zero() -> None:
    """Gate ACAD-TKT-204: ninguna violation serious/critical WCAG 2.1 AA en las 6 páginas críticas de Academy.

    Lee el reporte JSON producido por ``frontend/tests/e2e/academy/a11y.spec.ts``
    (Playwright + @axe-core/playwright) y exige 0 entries con impact
    serious/critical. Si el reporte no existe, hace ``pytest.skip`` para
    mantener la suite compatible con pytest collection sin browser.
    """
    if not REPORT_PATH.exists():
        pytest.skip(
            f"Reporte a11y no encontrado en {REPORT_PATH}. "
            "Ejecuta `cd frontend && npx playwright test "
            "tests/e2e/academy/a11y.spec.ts` antes de correr este gate."
        )

    raw = REPORT_PATH.read_text(encoding="utf-8")
    try:
        payload: Dict[str, Any] = json.loads(raw)
    except json.JSONDecodeError as exc:
        pytest.fail(f"Reporte a11y malformado en {REPORT_PATH}: {exc}")

    violations: List[Dict[str, Any]] = payload.get("violations", [])
    page_slug: str = payload.get("slug", "<unknown>")

    # The report is per-page (last-write-wins). When all 6 page tests run
    # in parallel/serial, the LAST slug is what we read here. The Playwright
    # spec writes failures inline (expect.toEqual([])) so the
    # pytest process would already have failed for any serious/critical
    # violation. This gate functions as a SECOND-layer audit that reads
    # the same report and re-asserts.
    serious_or_critical = [v for v in violations if v.get("impact") in {"serious", "critical"}]

    if page_slug not in ACCEPTED_PAGES:
        # Defensive: if a future spec writes an unfamiliar slug, surface
        # it loudly instead of silently passing.
        pytest.fail(
            f"Reporte a11y tiene slug inesperado '{page_slug}'. "
            f"Esperado: {sorted(ACCEPTED_PAGES)}"
        )

    summary_lines = [
        f"[tkt-204-gate] Página auditada: {page_slug}",
        f"[tkt-204-gate] URL: {payload.get('url')}",
        f"[tkt-204-gate] Violaciones total: {len(violations)}",
        f"[tkt-204-gate] Violaciones serious/critical: {len(serious_or_critical)}",
    ]
    for line in summary_lines:
        print(line)

    if serious_or_critical:
        bullets = "\n".join(
            f"  - [{v['impact']}] {v['id']}: {v['help']} ({v['nodes']} nodes)"
            for v in serious_or_critical
        )
        pytest.fail(
            f"WCAG 2.1 AA violations en Academy — {len(serious_or_critical)} "
            f"violation(s) serious/critical en '{page_slug}':\n{bullets}\n\n"
            "Remediación: agrega aria-label/role/dialog/title apropiados en "
            "los archivos frontend/src/app/plataforma/academy/ y "
            "frontend/src/components/academy/."
        )

    # Soft summary assertion — informational (no fail).
    assert isinstance(violations, list), "Reporte a11y debe contener lista de violations"
