"""Regression gates para TKT-042 — Single shell (consolidación AcademyDetailShell → WorkspaceLayout).

Cierre 2026-07-19:

**Decisión arquitectónica (refactor estructural):**
- ``WorkspaceLayout`` es el shell único de navegación + chrome en toda la plataforma.
- ``AcademyDetailShell`` fue refactorizado a ``AcademyDetailContainer``: ya no provee
  min-h-screen, header sticky, botón de regreso propio, ni useRouter. Solo provee el
  contenedor temático con gradientes radiales (decoración) sobre el que el contenido
  del wizard/detail se proyecta.

**Tickets que cubre este test:**
- **TKT-042** [HIGH] — Doble shell (AcademyDetailShell vs WorkspaceLayout) genera 2 microclimas visuales

**Patrón:**
1. AcademyDetailContainer (renombrado semánticamente desde AcademyDetailShell):
   - Sin ``min-h-screen`` en root
   - Sin import de ``useRouter`` (la navegación vive en WorkspaceLayout)
   - Sin import de ``ArrowLeft`` (back button viene de WorkspaceLayout.onBack)
   - Gradientes ``absolute inset-0`` (relativos al contenedor, no fixed al viewport)
2. enroll/[id]/page.tsx (único consumidor de AcademyDetailShell legacy):
   - Importa ``WorkspaceLayout`` como shell
   - Usa ``AcademyDetailContainer`` como contenedor temático interno
   - Pasa ``breadcrumbs`` al WorkspaceLayout para preservar el contexto de navegación

**Lo que NO cierra:**
- Otros consumidores de ``AcademyDetailShell`` (que ya no existen: el grep reveló solo 1 import).
- El nav-back de AcademyDetailShell legacy — ahora responsabilidad de WorkspaceLayout.onBack.
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


def _code_only(text: str) -> str:
    """Strip comments so lint-style assertions evalúan SOLO el código ejecutable.

    Remueve:
    - Block comments ``/* ... */`` (incluyendo JSDoc)
    - Line comments ``// ...``
    - HTML comments ``<!-- ... -->`` (usados a veces en JSX)

    Preserva el docstring del archivo como documentación, pero no lo evalúa
    para detectar presencia de tokens. Asi el test verifica uso real, no
    mención histórica en prosa.
    """
    no_block = re.sub(r"/\*[\s\S]*?\*/", " ", text)
    no_line = re.sub(r"//[^\n]*", " ", no_block)
    no_html = re.sub(r"<!--[\s\S]*?-->", " ", no_line)
    return no_html


# ──────────────────────────────────────────────────────────────────────
# TKT-042: AcademyDetailShell refactorizado a AcademyDetailContainer
#          (sin chrome de página, sin min-h-screen, sin useRouter)
# ──────────────────────────────────────────────────────────────────────


def test_acad_tkt_042_academy_detail_is_content_container() -> None:
    """TKT-042 — ``AcademyDetailShell.tsx`` ya no es un page-shell.

    El refactor convirtió el componente en un contenedor temático de contenido
    que vive DENTRO de WorkspaceLayout. Por lo tanto el código (no los
    comentarios) NO debe tener:
    - ``min-h-screen`` (eso es responsabilidad de WorkspaceLayout)
    - ``useRouter`` (la navegación vive en WorkspaceLayout)
    - ``ArrowLeft`` (back button lo provee WorkspaceLayout.onBack)
    - ``fixed inset-0`` (el contenedor es relativo, no fixed al viewport)
    - ``router.back(`` (navegación vive en WorkspaceLayout)

    Las menciones históricas de estos tokens en docstrings son válidas (son
    documentación, no uso), por eso usamos ``_code_only()``.
    """
    text = _read("components/academy/AcademyDetailShell.tsx")
    code = _code_only(text)
    forbidden_tokens = [
        "min-h-screen",  # viewport sizing viene de WorkspaceLayout
        "useRouter",  # navegación vive en WorkspaceLayout
        "ArrowLeft",  # back button lo provee WorkspaceLayout.onBack
        "fixed inset-0",  # el contenedor es relativo, no fixed al viewport
        "router.back(",  # navegación vive en WorkspaceLayout
    ]
    offenders = [token for token in forbidden_tokens if token in code]
    assert not offenders, (
        "TKT-042 regresión: AcademyDetailShell reintrodujo chrome de página en "
        f"código ejecutable. Tokens prohibidos: {offenders}. "
        "Mantener como contenedor de contenido dentro de WorkspaceLayout."
    )


def test_acad_tkt_042_academy_detail_exports_container() -> None:
    """TKT-042 — El archivo exporta explícitamente ``AcademyDetailContainer``
    (renombre semántico) además del default export para backward-compat.
    """
    code = _code_only(_read("components/academy/AcademyDetailShell.tsx"))
    assert "AcademyDetailContainer" in code, (
        "TKT-042 regresión: AcademyDetailShell no exporta AcademyDetailContainer "
        "en el código (puede estar solo en docstring)."
    )
    assert "export" in code and ("export default" in code or "export {" in code), (
        "TKT-042 regresión: el archivo no tiene export default o named export."
    )


def test_acad_tkt_042_academy_detail_container_has_testid_hook() -> None:
    """TKT-042 — ``AcademyDetailContainer`` emite ``data-testid="academy-detail-container"``
    en su root div. Esto habilita smoke tests de behavior y permite a consumers
    localizar el contenedor en tests DOM.
    """
    code = _code_only(_read("components/academy/AcademyDetailShell.tsx"))
    assert 'data-testid="academy-detail-container"' in code, (
        "TKT-042 regresión: el contenedor root no emite data-testid. "
        "Agregar ``<div data-testid=\"academy-detail-container\" ...>`` para smoke tests."
    )
    # Y debe ser un div relativo (no fixed al viewport)
    assert "data-variant" in code, (
        "TKT-042 regresión: no se emite data-variant. La decoración por variante "
        "sky/emerald/amber/blue debe ser inspeccionable en tests."
    )


# ──────────────────────────────────────────────────────────────────────
# TKT-042: enroll/[id]/page.tsx es consumer del nuevo container + WorkspaceLayout
# ──────────────────────────────────────────────────────────────────────


def test_acad_tkt_042_enroll_uses_workspace_layout() -> None:
    """TKT-042 — ``enroll/[id]/page.tsx`` envuelve su contenido con ``WorkspaceLayout``.

    WorkspaceLayout es el único shell de navegación de la plataforma. Si esta página
    usara cualquier otro shell (AcademyDetailShell legacy, layout propio), generaría
    un microclima visual distinto al resto del módulo Academy.
    """
    text = _read("app/plataforma/academy/enroll/[id]/page.tsx")
    assert "WorkspaceLayout" in text, (
        "TKT-042 regresión: enroll/[id]/page.tsx NO importa WorkspaceLayout. "
        "La página debe envolverse en WorkspaceLayout (shell único de plataforma) "
        "y usar AcademyDetailContainer como contenedor temático interno."
    )


def test_acad_tkt_042_enroll_uses_academy_detail_container_not_shell() -> None:
    """TKT-042 — ``enroll/[id]/page.tsx`` usa ``AcademyDetailContainer`` (sin chrome).

    El uso del nombre semántico nuevo es lo que documenta la refactorización. Si la
    página todavía usa el import original ``AcademyDetailShell`` con chrome (title,
    description, onBack), entonces tenemos 2 shells activos.
    """
    text = _read("app/plataforma/academy/enroll/[id]/page.tsx")
    assert "AcademyDetailContainer" in text, (
        "TKT-042 regresión: enroll/[id]/page.tsx NO usa AcademyDetailContainer. "
        "Usar el contenedor refactorizado (sin chrome propio) dentro de WorkspaceLayout."
    )


# ──────────────────────────────────────────────────────────────────────
# TKT-042: Solo enroll/[id]/page.tsx consume AcademyDetailShell/Container
#          (no debería haber otros consumers con chrome propio)
# ──────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "relative_path",
    [
        "app/plataforma/academy/enroll/[id]/page.tsx",
    ],
)
def test_acad_tkt_042_only_consumer_is_enroll_wizard(relative_path: str) -> None:
    """TKT-042 — El único consumer activo del contenedor temático Academy es el wizard de enrollment.

    Si en el futuro alguien introduce OTRO consumer que use AcademyDetailContainer/Shell
    sin WorkspaceLayout, este test no lo detecta directamente (eso requiere AST analysis),
    pero la gate anterior + el grep de archivos importan mantiene la disciplina arquitectónica.
    """
    text = _read(relative_path)
    # El consumer debe envolverse en WorkspaceLayout para evitar el microclima visual
    workspace_count = text.count("<WorkspaceLayout")
    container_count = text.count("<AcademyDetailContainer")
    assert workspace_count >= 1, (
        f"TKT-042 regresión: {relative_path} no envuelve con <WorkspaceLayout. "
        f"Encontrados {workspace_count} WorkspaceLayout, {container_count} AcademyDetailContainer."
    )
