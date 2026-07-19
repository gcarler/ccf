"""Regression gates para Fase 3 — Experiencia canónica (frontend hardening).

Tickets cubiertos (cierre funcional con drift detectado 2026-07-19):

- **TKT-030** [HIGH] No existen paths ``/academy/...`` rotos en router.push/href/navigate
- **TKT-031** [HIGH] ``courses/[id]/page.tsx`` usa API real (Promise.all), NO ``Promise.resolve(<stats>)``
- **TKT-032** [HIGH] ``account/page.tsx`` no tiene stats hardcodeadas
- **TKT-033** [HIGH] ``account/page.tsx`` no tiene PII mock (teléfono/ciudad literal)
- **TKT-034** [HIGH] ``enroll/[id]/page.tsx`` + ``AssessmentDrawer.tsx`` usan ``AbortController``
- **TKT-035** [HIGH] ``forum/[id]/page.tsx`` no usa ``onKeyPress`` deprecated
- **TKT-036** [HIGH] ``AcademyClient.tsx`` no tiene ``any`` types en fronteras API
- **TKT-037** [HIGH] ``assessments/[id]/page.tsx`` no tiene ``any`` types
- **TKT-038** [HIGH] ``account/page.tsx`` no tiene ``any`` types
- **TKT-144** [MED] ``academy/layout.tsx`` envuelve el shell con ``ModuleErrorBoundary``

**TKT-042 excluido:** AcademyDetailShell aún se usa en ``enroll/[id]/page.tsx``.
El refactor a WorkspaceLayout único requiere implementación real (no drift).
Queda ⬜ Pendiente para Fase 4 (decisión de producto).

**TKT-143 excluido:** ``CourseCatalog.tsx`` tiene 389 LOC. El refactor de "8 vistas
inline → sub-componentes" requiere análisis de qué vistas son extraíbles. Si bien
un size-limit ≤ 400 evita crecimiento, no certifica la separación estructural pedida.
Queda ⬜ Pendiente hasta decision: refactor completo vs freeze de tamaño.

Patrón de Fase 3: el código YA implementa los invariantes. Estos gates alertan
si alguien debilita el invariante (introduce un antipatrón).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

FRONTEND_SRC = Path(__file__).parent.parent / "frontend" / "src"


def _read(relative_path: str) -> str:
    """Lee el contenido de un archivo del frontend Academy.

    Falla explícitamente si el archivo no existe. Eso es señal de drift
    entre este test y el árbol del repo, no un fallo del invariante.
    """
    path = FRONTEND_SRC / relative_path
    assert path.exists(), f"Archivo no encontrado: {path}"
    return path.read_text(encoding="utf-8")


# ──────────────────────────────────────────────────────────────────────
# TKT-030: no paths /academy/... (sin prefijo /plataforma) en router/href
# ──────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "directory",
    [
        "app/plataforma/academy",
        "components/academy",
    ],
)
def test_acad_tkt_030_no_bare_academy_paths(directory: str) -> None:
    """TKT-030 — Ningún ``router.push('/academy/...')`` ni ``href="/academy/..."``.

    Los paths canónicos del módulo viven bajo ``/plataforma/academy/``.
    Paths ``/academy/...`` sin el segmento ``plataforma`` son drift de un
    layout antiguo o referencia muerta.
    """
    root = FRONTEND_SRC / directory
    assert root.exists(), f"Directorio no existe: {root}"

    offenders: list[str] = []
    pattern_bare = re.compile(r"""(?:router\.push|router\.replace|navigate\(|href\s*=\s*)["'](/academy/[^"']*)["']""")
    for ts_file in root.rglob("*.tsx"):
        text = ts_file.read_text(encoding="utf-8")
        for match in pattern_bare.finditer(text):
            offenders.append(f"{ts_file.name}: {match.group(0)}")

    assert not offenders, (
        "TKT-030 drift: paths '/academy/...' rotos encontrados:\n  "
        + "\n  ".join(offenders)
    )


# ──────────────────────────────────────────────────────────────────────
# TKT-031: courses/[id]/page.tsx NO usa Promise.resolve(<stats mock>)
# ──────────────────────────────────────────────────────────────────────


def test_acad_tkt_031_no_promise_resolve_stats() -> None:
    """TKT-031 — ``courses/[id]/page.tsx`` no invoca ``Promise.resolve`` con datos sintéticos.

    La carga de stats debe venir del contrato API real. ``Promise.resolve({...})``
    con valores literales es drift del modo demo.
    """
    text = _read("app/plataforma/academy/courses/[id]/page.tsx")
    # Excluir `Promise.all` y `Promise.allSettled` que son legítimos.
    assert "Promise.resolve" not in text, (
        "TKT-031 drift: Promise.resolve detectado — los datos deben venir del backend, "
        "no de un mock local de stats."
    )


# ──────────────────────────────────────────────────────────────────────
# TKT-032: account/page.tsx no tiene stats hardcodeadas (MockData / FakeData)
# ──────────────────────────────────────────────────────────────────────


def test_acad_tkt_032_no_hardcoded_account_stats() -> None:
    """TKT-032 — ``account/page.tsx`` no exporta ``MockData`` / ``FakeData`` con stats."""
    text = _read("app/plataforma/academy/account/page.tsx")
    # Detecta patrones comunes: import/export de objetos con keys de stats quemadas
    # seguido de llaves con números literales. Conservador: solo bloquea si hay un
    # token "Mock", "Fake", "Demo" como identificador.
    offenders = re.findall(r"\b(MockData|FakeData|DemoData|FAKE_STATS)\b", text)
    assert not offenders, (
        f"TKT-032 drift: bloque de stats mock detectado en account/page.tsx: {offenders}"
    )


# ──────────────────────────────────────────────────────────────────────
# TKT-033: account/page.tsx no tiene PII mockeada literal
# ──────────────────────────────────────────────────────────────────────


def test_acad_tkt_033_no_mock_pii() -> None:
    """TKT-033 — ``account/page.tsx`` no contiene strings literales de PII fake."""
    text = _read("app/plataforma/academy/account/page.tsx")
    # Busca patrones típicos de mock PII colombiano: +57, Bogotá/Medellín/Cali,
    # o "+57 300" como teléfono local.
    pii_patterns = [
        re.compile(r"""\btel[eé]fono\s*[:=]\s*["'][+\d][^"']{4,}"""),
        re.compile(r"""\bcelular\s*[:=]\s*["'][+\d][^"']{4,}"""),
        re.compile(r"""\bciudad\s*[:=]\s*["'](Bogot[aá]|Medell[ií]n|Cali|Barranquilla)""", re.IGNORECASE),
        re.compile(r"""\bdirecci[oó]n\s*[:=]\s*["'](Calle|Carrera|Avenida)\s+\d+""", re.IGNORECASE),
    ]
    offenders: list[str] = []
    for pattern in pii_patterns:
        for match in pattern.finditer(text):
            offenders.append(match.group(0))
    assert not offenders, (
        "TKT-033 drift: PII mockeada detectada en account/page.tsx:\n  "
        + "\n  ".join(offenders)
    )


# ──────────────────────────────────────────────────────────────────────
# TKT-034: AbortController presente en enroll/[id] + AssessmentDrawer
# ──────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "relative_path",
    [
        "app/plataforma/academy/enroll/[id]/page.tsx",
        "components/academy/AssessmentDrawer.tsx",
    ],
)
def test_acad_tkt_034_abort_controller_present(relative_path: str) -> None:
    """TKT-034 — Ambos archivos usan ``AbortController`` para cancelar fetches en unmount."""
    text = _read(relative_path)
    assert "AbortController" in text, (
        f"TKT-034 drift: AbortController no encontrado en {relative_path}. "
        "Toda carga async debe ser cancelable al desmontar."
    )


# ──────────────────────────────────────────────────────────────────────
# TKT-035: forum/[id] no usa onKeyPress deprecated
# ──────────────────────────────────────────────────────────────────────


def test_acad_tkt_035_no_onkeypress() -> None:
    """TKT-035 — ``forum/[id]/page.tsx`` no usa ``onKeyPress`` (deprecated en React 17+)."""
    text = _read("app/plataforma/academy/forum/[id]/page.tsx")
    assert "onKeyPress" not in text, (
        "TKT-035 drift: onKeyPress detectado. Usar onKeyDown (el estándar actual)."
    )


# ──────────────────────────────────────────────────────────────────────
# TKT-036..038: no ``any`` types en 3 archivos de borde
# ──────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "relative_path",
    [
        "app/plataforma/academy/AcademyClient.tsx",
        "app/plataforma/academy/assessments/[id]/page.tsx",
        "app/plataforma/academy/account/page.tsx",
    ],
)
def test_acad_tkt_036_to_038_no_any_types(relative_path: str) -> None:
    """TKT-036..038 — Ninguno de los 3 archivos de borde usa ``any`` types.

    Las fronteras API deben ser DTOs tipados del contrato del backend, no ``any``.
    Patrones cubiertos: ``: any``, ``<any>``, ``as any``, ``Array<any>``.
    """
    text = _read(relative_path)
    # Patrones negativos que cubren las 4 formas comunes de `any`:
    patterns = [
        re.compile(r":\s*any\b(?!\w)"),  # `: any` pero no `: anyword`
        re.compile(r"<\s*any\s*>"),  # `<any>` o `< any >`
        re.compile(r"\bas\s+any\b"),  # `as any` (con word boundary)
        re.compile(r"Array\s*<\s*any\s*>"),  # `Array<any>`
    ]
    offenders: list[tuple[str, int]] = []
    for pattern in patterns:
        for match in pattern.finditer(text):
            # Calcula línea aproximada (no crítico, basta con file + match)
            line_no = text[: match.start()].count("\n") + 1
            offenders.append((match.group(0).strip(), line_no))
    assert not offenders, (
        f"TKT-036..038 drift: tipos 'any' encontrados en {relative_path}:\n  "
        + "\n  ".join(f"L{ln}: {tok}" for tok, ln in offenders)
    )


# ──────────────────────────────────────────────────────────────────────
# TKT-144: academy/layout.tsx usa ModuleErrorBoundary
# ──────────────────────────────────────────────────────────────────────


def test_acad_tkt_144_error_boundary_in_layout() -> None:
    """TKT-144 — ``academy/layout.tsx`` importa y usa ``ModuleErrorBoundary``."""
    text = _read("app/plataforma/academy/layout.tsx")
    assert "ModuleErrorBoundary" in text, (
        "TKT-144 drift: ModuleErrorBoundary ausente en academy/layout.tsx. "
        "El módulo Academy debe envolver su shell con un error boundary explícito "
        "para evitar pantallas en blanco y permitir retry/empty states."
    )
    # Y debe haber una invocación JSX ``<ModuleErrorBoundary``
    assert re.search(r"<\s*ModuleErrorBoundary", text), (
        "TKT-144 drift: ModuleErrorBoundary importado pero no instanciado en layout."
    )
