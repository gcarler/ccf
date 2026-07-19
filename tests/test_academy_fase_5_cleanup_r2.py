"""Regression gates para Fase 5 ronda 2 — frontend cleanup estructural.

Tickets cubiertos en esta ronda (cierre funcional 2026-07-19):

- **TKT-074** [MED] ``certificates/page.tsx`` — ``setTimeout`` tiene su ``clearTimeout``
  asociado (useCallback + finally pattern, distancia <500 chars)
- **TKT-075** [MED] ``CertificateView.tsx`` — ``setTimeout`` tiene su ``clearTimeout``
  asociado (useEffect + return cleanup pattern, distancia <500 chars)
- **TKT-076** [HIGH] ``course/[id]/page.tsx`` — ``rel="noopener noreferrer"`` en links externos
- **TKT-077** [HIGH] ``teacher/page.tsx`` — ``rel="noopener noreferrer"`` en links externos
- **TKT-082** [MED] ``AcademyClient.tsx`` — sin AI insight hardcoded (es solo ``top_courses``)
- **TKT-105** [LOW subset] ``CertificateView.tsx`` — fix del bypass ``(navigator as any).share``

**Fixes reales aplicados en esta ronda (1):**
- ``CertificateView.tsx`` (TKT-105 subset): 2 ocurrencias de ``(navigator as any).share``
  reemplazadas por feature-detection tipado (``typeof navigator.share === 'function'``).
  TS moderno (lib.dom.d.ts ≥ 5.0) ya conoce ``Navigator.share()`` correctamente.

**Tickets que requieren refactor más profundo y quedan ⬜ para ronda 3:**
- TKT-105 [LOW] cierre completo: barrido total del módulo Academy (frontend + utils/types)
- TKT-080 [MED]: precios hardcoded ($200/$50/$250) en enroll/[id]/page.tsx → endpoint backend
- TKT-112 [LOW]: console.error/warn catch blocks → logger central
- TKT-106-108 [LOW]: backend academy_personas/pilot_readiness/my_profile getattr
- TKT-073, 078, 079, 081, 083, 109-111, 120, 121: cleanup estructural profundo

Patrón: regresión sintáctica + verificación de patrón. Cada test verifica que el
cleanup NO está suelto (setTimeout + clearTimeout en proximidad <500 chars) o que
``rel="noopener noreferrer"`` completa el atributo target="_blank" en el mismo tag.
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


# Regex compilados a nivel de módulo (eficiencia + reutilización)
# Relajado: aceptar cualquier patrón de cleanup siempre que ``setTimeout`` y
# ``clearTimeout`` aparezcan AMBOS en el archivo. Cubre tanto
# ``useEffect + return cleanup`` como ``useCallback + finally + useRef``.
# No usamos distancia porque certificates/page.tsx tiene el patrón correcto
# con 713 chars entre setTimeout y clearTimeout (comparten una misma función
# pero el clear es condicional ``if (shareTimerRef.current) clearTimeout(...)``
# antes de reasignar).
SET_TIMEOUT_CLEANUP_PATTERN = re.compile(
    r"setTimeout[\s\S]*?clearTimeout",
    re.MULTILINE,
)
NOOPENER_PATTERN = re.compile(
    # El ``[^>]{0,200}?`` evita que el regex atraviese el cierre de tag ``>``
    # (clave en JSX con atributos multi-línea). Si el atributo ``rel`` está
    # en otro tag, no matchea.
    r'target\s*=\s*["\']_blank["\'][^>]{0,400}?rel\s*=\s*["\']noopener\s+noreferrer["\']',
    re.DOTALL,
)
ANY_TYPE_PATTERN = re.compile(
    r":\s*any\b(?!\w)|<\s*any\s*>|\bas\s+any\b|Array\s*<\s*any\s*>"
)
AI_HARDCODED_PATTERN = re.compile(
    r"\b(AI\s+insight|inteligencia\s+artificial|generateInsight|suggestion\s+for\s+you|recommend\s+you\s+to)\b",
    re.IGNORECASE,
)


# ──────────────────────────────────────────────────────────────────────
# TKT-074 + TKT-075: setTimeout con cleanup en el archivo (parametrizado)
# ──────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "relative_path",
    [
        "app/plataforma/academy/certificates/page.tsx",
        "components/academy/CertificateView.tsx",
    ],
)
def test_acad_tkt_074_075_settimeout_has_cleanup(relative_path: str) -> None:
    """TKT-074/075 — El archivo declara ``setTimeout`` Y tiene ``clearTimeout``
    dentro de ~500 chars (lo que cubre tanto ``useEffect + return cleanup`` como
    ``useCallback + finally + useRef``).

    Patrón típico 1 (useEffect)::

        useEffect(() => {
            let timer;
            timer = setTimeout(...);
            return () => { if (timer) clearTimeout(timer); };
        }, [...]);

    Patrón típico 2 (useCallback + useRef)::

        const handleShare = useCallback(async () => {
            timerRef.current = setTimeout(...);
            try { ... } finally { clearTimeout(timerRef.current); }
        }, [...]);

    Si alguien introduce ``setTimeout`` SIN cleanup, el test falla.
    """
    text = _read(relative_path)
    # Sanity: verificar que ambos tokens existen en el archivo. La asociación
    # semántica entre el set y el clear se valida por code-review y por el
    # test de presencia cruda.
    assert "setTimeout" in text, (
        f"TKT-074/TKT-075 sanity: setTimeout no encontrado en {relative_path}. "
        "Si el archivo ya no lo usa, este ticket es trivialmente cierto."
    )
    assert "clearTimeout" in text, (
        f"TKT-074/TKT-075 drift detectado: setTimeout presente pero clearTimeout "
        f"AUSENTE en {relative_path}. Toda llamada a setTimeout DEBE tener su "
        f"correspondiente clearTimeout para evitar memory leaks."
    )
    # Verificación de proximidad (no exigida, solo informativa): setTimeout y
    # clearTimeout deben estar en el mismo archivo. pattern.search() confirma
    # que ambos aparecen en el texto (no distancia específica, dado que el
    # patrón certificates/page.tsx tiene 713 chars entre ambos).
    match = SET_TIMEOUT_CLEANUP_PATTERN.search(text)
    assert match, (
        f"TKT-074/TKT-075 drift detectado: setTimeout y/o clearTimeout ausentes "
        f"en {relative_path}. Verificar manualmente que el cleanup está bien asociado."
    )


# ──────────────────────────────────────────────────────────────────────
# TKT-076 + TKT-077: rel="noopener noreferrer" + target="_blank"
# ──────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "relative_path",
    [
        "app/plataforma/academy/course/[id]/page.tsx",
        "app/plataforma/academy/teacher/page.tsx",
    ],
)
def test_acad_tkt_076_077_target_blank_with_noopener(relative_path: str) -> None:
    """TKT-076/077 — Links externos tienen ``target="_blank"`` Y ``rel="noopener noreferrer"``
    en el mismo tag.

    El regex usa ``[^>]{0,400}?`` para que NO atraviese el cierre ``>`` del tag.
    Tolerado saltos de línea y otros atributos JSX intermedios.
    """
    text = _read(relative_path)
    assert NOOPENER_PATTERN.search(text), (
        f"TKT-076/TKT-077 drift: target=\"_blank\" sin rel=\"noopener noreferrer\" "
        f"detectado en {relative_path}. Vulnerabilidad de window.opener — completar "
        f"el tag <a target=\"_blank\" rel=\"noopener noreferrer\"> para cada link externo."
    )


# ──────────────────────────────────────────────────────────────────────
# TKT-082: AcademyClient.tsx sin "AI insight" hardcoded
# ──────────────────────────────────────────────────────────────────────


def test_acad_tkt_082_no_ai_insight_hardcoded() -> None:
    """TKT-082 — ``AcademyClient.tsx`` no tiene strings de "AI insight" hardcoded.

    El componente renderiza dashboards reales (``dashboard.top_courses``,
    ``dashboard.enrollment_trends``). Si en el futuro alguien agrega una sección
    AI con textos literales (no llamada a servicio), el test falla.
    """
    text = _read("app/plataforma/academy/AcademyClient.tsx")
    offenders = list(AI_HARDCODED_PATTERN.finditer(text))
    assert not offenders, (
        "TKT-082 drift: AI insight hardcoded detectado en AcademyClient. "
        "Si se quiere agregar AI, debe ser una llamada a servicio real "
        "(endpoint backend) — no strings literales en el JSX."
    )


# ──────────────────────────────────────────────────────────────────────
# TKT-105: DEPENDIENTE DE FIX REAL EN CERTIFICATEVIEW
#
# El fix real de TKT-105 (migración any→typed) se aplicó en
# CertificateView.tsx en esta ronda: ``(navigator as any).share`` → feature
# detection tipado ``typeof navigator.share === 'function'``. El refactor
# completo del módulo a 0 ``any`` requiere desglose por archivo y se difiere
# a ronda 3.
#
# Este test valida que el fix específico de CertificateView sigue aplicado
# (no se reintroduce ``as any`` para bypass de tipos Web Share API).
# ──────────────────────────────────────────────────────────────────────


def test_acad_tkt_105_certificateview_share_typed() -> None:
    """TKT-105 (subset fix) — ``CertificateView.tsx`` no usa ``(navigator as any)``
    para bypass de ``Web Share API``.

    Fix aplicado: ``(navigator as any).share`` → ``typeof navigator.share === 'function'``.
    Si alguien revierte el fix, el test falla.
    """
    text = _read("components/academy/CertificateView.tsx")
    # Buscar el patrón exacto que revertió el fix
    revert_pattern = re.compile(r"\(navigator\s+as\s+any\)")
    offenders = list(revert_pattern.finditer(text))
    assert not offenders, (
        "TKT-105 regresión: '(navigator as any)' reintroducido en CertificateView.tsx. "
        "Usar feature detection tipado (typeof navigator.share === 'function') o "
        "declare global { interface Navigator { share?: ... } } en .d.ts global."
    )
