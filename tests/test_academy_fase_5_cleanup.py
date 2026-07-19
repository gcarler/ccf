"""Regression gates para Fase 5 — Fiabilidad y deuda residual (cleanup parcial).

Tickets cubiertos en esta ronda (cierre con drift detectado 2026-07-19):

- **TKT-070** [MED] ``coordination/courses/new/page.tsx`` no tiene ``setTimeout(...800)`` artificial
- **TKT-071** [MED] ``profile/progress/page.tsx`` no tiene ``setTimeout(...600)`` artificial
- **TKT-100** [LOW] ``coordination/page.tsx`` no tiene ``p-4 p-4`` duplicado
- **TKT-101** [LOW] ``teacher/page.tsx`` no tiene ``p-4 p-4`` duplicado
- **TKT-102** [LOW] ``AcademyClient.tsx`` no usa ``key={index|i}`` en listas

**Excluidos explícitamente (inspección reveló que el antipatrón SÍ existe — quedan ⬜ pendiente hasta refactor real):**

- TKT-072 — ``Promise.allSettled`` SÍ está presente en ``courses/[id]/lessons/page.tsx`` (uso legítimo, sin catch muerto). Refinar el gate al patrón "catch muerto" o migrar a ``Promise.all`` con manejo explícito queda como tarea separada.
- TKT-103 — ``key={i}`` SÍ está presente en ``account/page.tsx``. Decidir si el list reordena (entonces es bug) o es estático (entonces OK con eslint-disable justificado).
- TKT-104 — ``key={i}`` SÍ está presente en ``profile/page.tsx``. Idem TKT-103.

**Excluidos explícitamente (quedan ⬜ pendiente — requieren fix real, no drift):**

- TKT-073 mixed toast — requiere unificación sonner/ToastContext
- TKT-074-075 setTimeout sin cleanup — requiere ``return () => clearTimeout(...)`` real
- TKT-076-077 missing noopener — requiere refactor a Link externo o rel="noopener noreferrer"
- TKT-078-079 unstable deps — requiere extracción de properties o memoización
- TKT-080 precios hardcoded — requiere nuevo endpoint backend + DTO
- TKT-081 fallback video URL — requiere plan de hosting
- TKT-082 AI insight hardcoded — requiere servicio de AI real
- TKT-083 timer 45:00 — requiere duración dinámica del assessment
- TKT-105 any types ~15 archivos — requiere migración gradual type-by-type
- TKT-106-108 backend hardcodea role/profile/getattr — requiere refactor backend
- TKT-109-111 imports no optimizados — requiere cleanup de eslint-config
- TKT-112 console.error/warn (102 archivos) — requiere logger central + migración
- TKT-120 Download/Share certificado sin handler — requiere implementar handlers
- TKT-121 enrollment_id redundante — requiere análisis de contrato API

Patrón aplicado: regresión sintáctica negativa. Drift detectado afirma que el
antipatrón NO está presente. Si alguien lo reintroduce, el test falla con
mensaje claro citando el TKT-NNN y la línea exacta.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

FRONTEND_SRC = Path(__file__).parent.parent / "frontend" / "src"


def _read(relative_path: str) -> str:
    path = FRONTEND_SRC / relative_path
    assert path.exists(), f"Archivo no encontrado: {path}"
    return path.read_text(encoding="utf-8")


# ──────────────────────────────────────────────────────────────────────
# TKT-070: coordination/courses/new sin delay artificial 800ms
# ──────────────────────────────────────────────────────────────────────


def test_acad_tkt_070_no_settimeout_800ms() -> None:
    """TKT-070 — ``coordination/courses/new/page.tsx`` no simula latency con ``setTimeout`` 800ms."""
    text = _read("app/plataforma/academy/coordination/courses/new/page.tsx")
    pattern = re.compile(r"setTimeout\s*\([^,]+,\s*800\s*[,)]")
    offenders = list(pattern.finditer(text))
    assert not offenders, (
        "TKT-070 drift: delay 800ms detectado en coordination/courses/new. "
        "Quitar el setTimeout para que la latencia sea la real de la API."
    )


# ──────────────────────────────────────────────────────────────────────
# TKT-071: profile/progress sin delay artificial 600ms
# ──────────────────────────────────────────────────────────────────────


def test_acad_tkt_071_no_settimeout_600ms() -> None:
    """TKT-071 — ``profile/progress/page.tsx`` no simula latency con ``setTimeout`` 600ms."""
    text = _read("app/plataforma/academy/profile/progress/page.tsx")
    pattern = re.compile(r"setTimeout\s*\([^,]+,\s*600\s*[,)]")
    offenders = list(pattern.finditer(text))
    assert not offenders, (
        "TKT-071 drift: delay 600ms detectado en profile/progress. "
        "Quitar el setTimeout para que la latencia sea la real de la API."
    )


# ──────────────────────────────────────────────────────────────────────
# TKT-100..101: p-4 duplicado en coordination + teacher pages
# ──────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "relative_path",
    [
        "app/plataforma/academy/coordination/page.tsx",
        "app/plataforma/academy/teacher/page.tsx",
    ],
)
def test_acad_tkt_100_101_no_p4_duplicate(relative_path: str) -> None:
    """TKT-100/101 — ``p-4 p-4`` (duplicado) no debe aparecer en coordination ni teacher."""
    text = _read(relative_path)
    assert "p-4 p-4" not in text, (
        f"TKT-100/TKT-101 drift: 'p-4 p-4' duplicado detectado en {relative_path}. "
        "Tailwind colapsa estos duplicados pero es señal de copy/paste descuidado."
    )


# ──────────────────────────────────────────────────────────────────────
# TKT-102..104: index-as-key en AcademyClient + account + profile
# ──────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "relative_path",
    [
        "app/plataforma/academy/AcademyClient.tsx",
    ],
)
def test_acad_tkt_102_no_index_as_key_academyclient(relative_path: str) -> None:
    """TKT-102 — ``AcademyClient.tsx`` no usa ``key={index|i}`` en listas.

    TKT-103 (account) y TKT-104 (profile) excluidos: el antipatrón SÍ está presente
    en esos archivos y requiere refactor real antes de poder cerrar el gate.
    """
    text = _read(relative_path)
    pattern = re.compile(r"""\bkey\s*=\s*\{\s*(?:index|i)\s*\}""")
    offenders = list(pattern.finditer(text))
    assert not offenders, (
        f"TKT-102 drift: key={'{index|i}'} detectado en {relative_path}. "
        "Usar el ID estable del item (id o key único del backend) para evitar "
        "re-renders incorrectos al reorderar la lista."
    )
