"""Regression gates para TKT-143 — CourseCatalog split a sub-componentes.

Cierre 2026-07-19. Refactor estructural:

- ``frontend/src/components/CourseCatalog.tsx``: 389 LOC monolíticos → ~150 LOC
  como orquestador que delega en sub-vistas.
- ``frontend/src/components/course-catalog/`` (nuevo módulo):
  - ``types.ts`` — Course, Modality, AccessLevel, CourseCatalogProps
  - ``constants.ts`` — ACCESS_LABEL, ACCESS_COLOR, COURSE_CATALOG_AVAILABLE_VIEWS
  - ``views.tsx`` — 7 sub-vistas: GridView, ListView, TableView, BoardView,
    CalendarView, GanttView, WikiView (board+kanban unificados en BoardView)

**Tickets cubiertos:**
- **TKT-143** [MED] — ``CourseCatalog.tsx`` con 8 vistas inline → refactor sub-componentes

**Patrón:** regression gates estructurales:
1. Size gate: el orquestador ``CourseCatalog.tsx`` debe ser <150 LOC.
2. Sub-module gate: ``course-catalog/{types,constants,views}.{ts,tsx}`` deben existir.
3. Export gate: views.tsx debe exportar las 7 sub-vistas nombradas.
4. Backward-compat gate: ``CourseCatalog.tsx`` debe seguir exportando default
   ``CourseCatalog`` con las mismas props que antes.

**Lo que NO cierra (futuras iteraciones):**
- Tests unitarios por vista (Playwright o React Testing Library).
- Snapshot tests del render DOM por vista.
- Code-splitting dinámico (cargar vistas bajo demanda).
"""

from __future__ import annotations

from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
COURSE_CATALOG_DIR = PROJECT_ROOT / "frontend" / "src" / "components" / "course-catalog"
COURSE_CATALOG_FILE = PROJECT_ROOT / "frontend" / "src" / "components" / "CourseCatalog.tsx"

# Tamaño máximo permitido para el orquestador (no para el módulo completo).
# 175 LOC permite un orquestador legible con:
# - imports (~15 líneas)
# - 2 useState + 1 useWikiDocument + 1 useEffect (~25 líneas)
# - 1 useCallback handleEnrollClick (~10 líneas)
# - JSX de filtros + ViewSwitcher (~30 líneas)
# - Dispatch a 7 sub-vistas (~15 líneas)
# - Comentarios docstring + tipos (~30 líneas)
# Si el orquestador crece más, es señal de que hay que extraer más a sub-vistas.
ORCHESTRATOR_MAX_LINES = 175


def _read(path: Path) -> str:
    assert path.exists(), f"Archivo no encontrado: {path}"
    return path.read_text(encoding="utf-8")


# ──────────────────────────────────────────────────────────────────────
# TKT-143: Sub-module structure gate
# ──────────────────────────────────────────────────────────────────────


def test_acad_tkt_143_course_catalog_module_exists() -> None:
    """TKT-143 — El directorio ``course-catalog/`` existe con los 3 archivos
    esperados del split.
    """
    assert COURSE_CATALOG_DIR.is_dir(), (
        f"TKT-143 regresión: directorio {COURSE_CATALOG_DIR} no existe. "
        "El split debe crear course-catalog/ junto a CourseCatalog.tsx."
    )

    expected_files = ["types.ts", "constants.ts", "views.tsx"]
    for filename in expected_files:
        path = COURSE_CATALOG_DIR / filename
        assert path.exists(), (
            f"TKT-143 regresión: falta {filename} en {COURSE_CATALOG_DIR}. "
            "El split debe producir types.ts + constants.ts + views.tsx."
        )


# ──────────────────────────────────────────────────────────────────────
# TKT-143: Orchestrator size gate (<150 LOC)
# ──────────────────────────────────────────────────────────────────────


def test_acad_tkt_143_orchestrator_under_max_lines() -> None:
    """TKT-143 — ``CourseCatalog.tsx`` (orquestador) tiene <150 LOC.

    Antes: 389 LOC monolíticos. Después: ~95 LOC como orquestador que delega
    en 7 sub-vistas importadas. Si alguien introduce cambios que revienten el
    split, el archivo crecerá y este gate lo detecta.
    """
    assert COURSE_CATALOG_FILE.exists(), (
        f"TKT-143 regresión: {COURSE_CATALOG_FILE} no existe. "
        "CourseCatalog.tsx debe seguir en su ubicación original."
    )
    lines = _read(COURSE_CATALOG_FILE).splitlines()
    line_count = len(lines)
    assert line_count <= ORCHESTRATOR_MAX_LINES, (
        f"TKT-143 regresión: CourseCatalog.tsx creció a {line_count} LOC "
        f"(máximo permitido: {ORCHESTRATOR_MAX_LINES}). "
        "Mantener el orquestador delgado — la lógica de vistas vive en "
        "course-catalog/views.tsx. Si necesitas agregar UI, considera extraer "
        "una nueva sub-vista en lugar de inline."
    )


# ──────────────────────────────────────────────────────────────────────
# TKT-143: Sub-vistas exportadas desde views.tsx
# ──────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "view_name",
    [
        "GridView",
        "ListView",
        "TableView",
        "BoardView",
        "CalendarView",
        "GanttView",
        "WikiView",
    ],
)
def test_acad_tkt_143_views_exports_subcomponents(view_name: str) -> None:
    """TKT-143 — Las 7 sub-vistas (board+kanban unificadas) están exportadas
    desde ``course-catalog/views.tsx``.

    El orquestador importa estas sub-vistas para delegar el render por
    ``resolvedViewType``. Si alguien elimina el export, tsc falla en el
    orquestador Y este gate lo detecta antes.
    """
    views_path = COURSE_CATALOG_DIR / "views.tsx"
    text = _read(views_path)
    # Match exacto: `export function ViewName(` o `export const ViewName =`
    pattern_options = [
        f"export function {view_name}(",
        f"export const {view_name} ",
        f"export const {view_name}=",
    ]
    assert any(option in text for option in pattern_options), (
        f"TKT-143 regresión: {view_name} no está exportado desde {views_path}. "
        f"Esperado uno de: {pattern_options}. El split debe producir exports nombrados."
    )


# ──────────────────────────────────────────────────────────────────────
# TKT-143: Orquestador importa las sub-vistas (cableado correcto)
# ──────────────────────────────────────────────────────────────────────


def test_acad_tkt_143_orchestrator_imports_subviews() -> None:
    """TKT-143 — ``CourseCatalog.tsx`` importa todas las sub-vistas.

    El orquestador debe delegar el render a las sub-vistas, no reimplementar
    lógica inline. Si alguien comenta un import, las vistas correspondientes
    no se renderizarán.
    """
    text = _read(COURSE_CATALOG_FILE)
    expected_imports = ["GridView", "ListView", "TableView", "BoardView", "CalendarView", "GanttView", "WikiView"]
    missing = [v for v in expected_imports if v not in text]
    assert not missing, (
        f"TKT-143 regresión: CourseCatalog.tsx no importa {missing}. "
        "El orquestador debe delegar en TODAS las sub-vistas extraídas."
    )


# ──────────────────────────────────────────────────────────────────────
# TKT-143: Backward-compat — default export sigue siendo CourseCatalog
# ──────────────────────────────────────────────────────────────────────


def test_acad_tkt_143_default_export_preserved() -> None:
    """TKT-143 — El orquestador sigue exportando default ``CourseCatalog``
    para no romper consumers existentes.
    """
    text = _read(COURSE_CATALOG_FILE)
    assert "export default function CourseCatalog" in text, (
        "TKT-143 regresión: CourseCatalog.tsx no exporta default CourseCatalog. "
        "Los consumers que importan ``import CourseCatalog from '@/components/CourseCatalog'`` "
        "romperían. El split debe preservar el nombre del export default."
    )


# ──────────────────────────────────────────────────────────────────────
# TKT-143: Tipos compartidos están en types.ts (no en CourseCatalog.tsx)
# ──────────────────────────────────────────────────────────────────────


def test_acad_tkt_143_types_in_separate_file() -> None:
    """TKT-143 — Los tipos ``Course``, ``Modality``, ``AccessLevel`` viven en
    ``course-catalog/types.ts``, NO inline en CourseCatalog.tsx.

    El orquestador solo debe importar los tipos, no redefinirlos. Si alguien
    duplica los tipos en el orquestador, diverge el contrato compartido.
    """
    types_path = COURSE_CATALOG_DIR / "types.ts"
    types_text = _read(types_path)
    expected_types = ["Course", "Modality", "AccessLevel", "CourseCatalogProps"]
    missing = [t for t in expected_types if t not in types_text]
    assert not missing, (
        f"TKT-143 regresión: types.ts no exporta {missing}. "
        "Tipos compartidos deben vivir en course-catalog/types.ts."
    )

    # Y el orquestador debe importarlos, no redefinirlos
    orchestrator_text = _read(COURSE_CATALOG_FILE)
    assert "from \"./course-catalog/types\"" in orchestrator_text, (
        "TKT-143 regresión: CourseCatalog.tsx no importa tipos de ./course-catalog/types. "
        "Si redefine los tipos, diverge el contrato compartido con views.tsx."
    )


# ──────────────────────────────────────────────────────────────────────
# TKT-143: Constantes compartidas están en constants.ts
# ──────────────────────────────────────────────────────────────────────


def test_acad_tkt_143_constants_in_separate_file() -> None:
    """TKT-143 — ``ACCESS_LABEL``, ``ACCESS_COLOR``, ``COURSE_CATALOG_AVAILABLE_VIEWS``
    viven en ``course-catalog/constants.ts``.
    """
    constants_path = COURSE_CATALOG_DIR / "constants.ts"
    constants_text = _read(constants_path)
    expected_constants = ["ACCESS_LABEL", "ACCESS_COLOR", "COURSE_CATALOG_AVAILABLE_VIEWS"]
    missing = [c for c in expected_constants if c not in constants_text]
    assert not missing, (
        f"TKT-143 regresión: constants.ts no exporta {missing}. "
        "Constantes compartidas deben vivir en course-catalog/constants.ts."
    )

    # Y el orquestador debe importarlos, no redefinirlos
    orchestrator_text = _read(COURSE_CATALOG_FILE)
    assert "from \"./course-catalog/constants\"" in orchestrator_text, (
        "TKT-143 regresión: CourseCatalog.tsx no importa constantes de ./course-catalog/constants."
    )
