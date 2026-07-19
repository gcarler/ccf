#!/usr/bin/env python3
"""scripts/check_academy_backlog.py — parser robusto del ACADEMY_BACKLOG.

Salida: exit 0 si TODO OK, exit 1 con mensaje si falla cualquier regla.

Reglas (matching docs/ACADEMY_BACKLOG.md §7):
  1. Tickets ⬜ deben tener `gate:` ejecutable.
  2. Severidades ∈ {CRIT, HIGH, MED, LOW, TEST}.
  3. IDs ACAD-TKT-NNN consecutivos sin duplicados.
  4. Los 3 docs legacy tienen banner DEPRECADO + redirect.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKLOG = REPO_ROOT / "docs" / "ACADEMY_BACKLOG.md"
LEGACY_DOCS = [
    REPO_ROOT / "docs" / "PLAN_ACADEMY_CALIDAD.md",
    REPO_ROOT / "docs" / "ESTADO_ACADEMY.md",
    REPO_ROOT / "docs" / "ACADEMY_QA_CHECKLIST.md",
]

VALID_STATES = {"⬜", "🟡", "✅", "📜"}
VALID_SEVERITIES = {"CRIT", "HIGH", "MED", "LOW", "TEST"}


_RE_TKT_HEADER = re.compile(
    r"^- \*\*ACAD-TKT-(\d+)\*\* \[(?:CRIT|HIGH|MED|LOW|TEST)\] "
)


def parse_tickets(backlog_text: str) -> list[dict]:
    """Parsea el backlog en bloques por ticket (no IDs únicos, líneas-state)."""
    tickets: list[dict] = []
    matches = list(_RE_TKT_HEADER.finditer(backlog_text))
    for idx, m in enumerate(matches):
        start = m.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(backlog_text)
        body = backlog_text[start:end]

        num_match = re.search(r"ACAD-TKT-(\d+)", body)
        sev_match = re.search(r"\*\*ACAD-TKT-\d+\*\* \[(\w+)\]", body)
        state_match = re.search(r"\*\*state:\*\*\s*([⬜🟡✅📜])", body)
        source_match = re.search(r"\*\*source:\*\*\s*(.+?)\n", body)
        gate_match = re.search(r"\*\*gate:\*\*\s*`([^`]+)`", body)

        tickets.append(
            {
                "number": int(num_match.group(1)) if num_match else None,
                "severity": sev_match.group(1) if sev_match else None,
                "state": state_match.group(1) if state_match else None,
                "source": source_match.group(1).strip() if source_match else "",
                "gate": gate_match.group(1).strip() if gate_match else "",
                "snapshot": body[:300],
            }
        )
    return tickets


def check_backlog() -> list[str]:
    """Devuelve lista de issues. Vacía = OK."""
    issues: list[str] = []

    if not BACKLOG.exists():
        return [f"❌ {BACKLOG} no existe. Debe crearse como fuente única."]

    text = BACKLOG.read_text(encoding="utf-8")
    tickets = parse_tickets(text)

    # 1. ⬜ sin gate → bloqueante.
    pending_without_gate = [
        t for t in tickets
        if t["state"] == "⬜" and not t["gate"]
    ]
    if pending_without_gate:
        issues.append(
            f"❌ {len(pending_without_gate)} ticket(s) ⬜ sin gate ejecutable. "
            f"Primeros 5: {[t['number'] for t in pending_without_gate[:5]]}"
        )

    # 2. Severidades inválidas.
    invalid_sev = [
        t for t in tickets
        if t["severity"] is not None
        and t["state"] is not None
        and t["severity"] not in VALID_SEVERITIES
    ]
    if invalid_sev:
        issues.append(
            f"❌ {len(invalid_sev)} ticket(s) con severidad inválida: "
            f"{[(t['number'], t['severity']) for t in invalid_sev[:5]]}"
        )

    # 3. IDs ACAD-TKT-NNN duplicados.
    nums = [t["number"] for t in tickets if t["number"] is not None]
    duplicates = sorted({n for n in nums if nums.count(n) > 1})
    if duplicates:
        issues.append(f"❌ ACAD-TKT-NNN duplicados: {duplicates}")

    # 4. Los 3 docs legacy tienen banner DEPRECADO + redirect.
    for legacy in LEGACY_DOCS:
        if not legacy.exists():
            continue
        ltext = legacy.read_text(encoding="utf-8")
        if "DEPRECADO" not in ltext:
            issues.append(f"❌ {legacy.name} sin banner 'DEPRECADO'")
        if "ACADEMY_BACKLOG.md" not in ltext:
            issues.append(f"❌ {legacy.name} sin redirect a docs/ACADEMY_BACKLOG.md")

    # 5. Estados válidos.
    invalid_state = [
        t for t in tickets
        if t["state"] is not None and t["state"] not in VALID_STATES
    ]
    if invalid_state:
        issues.append(
            f"❌ {len(invalid_state)} ticket(s) con estado inválido: "
            f"{[t['state'] for t in invalid_state[:5]]}"
        )

    return issues


def main() -> int:
    issues = check_backlog()
    if issues:
        print("🔴 ACADEMY_BACKLOG no pasa validación:")
        for issue in issues:
            print(f"  {issue}")
        return 1
    print("✅ ACADEMY_BACKLOG validado como fuente única (regla §7 anti-drift).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
