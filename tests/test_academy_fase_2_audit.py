"""Regression gates para Fase 2 — Operación y trazabilidad.

Tickets cubiertos (cierre funcional con drift detectado 2026-07-19):

- **TKT-023** [HIGH] ``archive_course_admin`` ya escribe ``AcademyActivityLog(event_type="course_archived")``
- **TKT-024** [HIGH] ``archive_lesson_admin`` ya escribe ``AcademyActivityLog(event_type="lesson_archived")``
- **TKT-025** [HIGH] ``grade_submission`` ya escribe ``AcademyActivityLog(event_type="submission_graded")``
- **TKT-026** [HIGH] ``update_course_admin`` ya escribe ``AcademyActivityLog(event_type="course_updated")``
- **TKT-027** [HIGH] ``update_lesson_admin`` ya escribe ``AcademyActivityLog(event_type="lesson_updated")``
- **TKT-028** [HIGH] ``resolve_forum_thread`` ya escribe ``AcademyActivityLog(event_type="forum_resolved")``
- **TKT-090** [MED] ``create_forum_thread`` ya retorna 403 si ``course_id=None`` y user sin ``academy:edit``/``academy:manage``
- **TKT-091** [MED] Ya existe endpoint ``PATCH /forum/threads/{thread_id}/resolve`` que toggle ``is_resolved``
- **TKT-134** [TEST] Esta suite cubre el sub-set de audit logs del nightly regression

Estos gates sirven como **regression gates** que alertan si alguien debilita
la trazabilidad. Si cualquiera falla, abrir un nuevo ticket ACAD-TKT-NNN
y bloquear merge.

Patrón establecido en ``tests/test_academy_fase_a_crit.py`` (Fase A CRIT) +
``tests/test_academy_fase_1.py`` (Fase 1 schemas/pagination).
"""

from __future__ import annotations

import importlib
import inspect
import re

import pytest

from backend.api.academy import (
    create_forum_thread,
    resolve_forum_thread,
)

# ──────────────────────────────────────────────────────────────────────
# TKT-023..028: 6 endpoints admin escriben AcademyActivityLog
# ──────────────────────────────────────────────────────────────────────


def _get_endpoint_source(endpoint_name: str) -> str:
    """Devuelve el código fuente del endpoint en ``backend.api.academy``."""
    module = importlib.import_module("backend.api.academy")
    func = getattr(module, endpoint_name, None)
    assert func is not None, f"{endpoint_name} no existe en backend.api.academy"
    return inspect.getsource(func)


@pytest.mark.parametrize(
    "endpoint_name,expected_event_type,expected_payload_keys",
    [
        ("archive_course_admin", "course_archived", ["course_code", "course_title"]),
        ("archive_lesson_admin", "lesson_archived", ["lesson_id", "lesson_title"]),
        ("grade_submission", "submission_graded", ["submission_id", "lesson_id", "grade"]),
        ("update_course_admin", "course_updated", ["changes"]),
        ("update_lesson_admin", "lesson_updated", ["lesson_id", "changes"]),
        ("resolve_forum_thread", "forum_resolved", ["thread_id", "is_resolved"]),
    ],
    ids=[
        "TKT-023_archive_course",
        "TKT-024_archive_lesson",
        "TKT-025_grade_submission",
        "TKT-026_update_course",
        "TKT-027_update_lesson",
        "TKT-028_resolve_forum",
    ],
)
def test_tkt_023_to_028_audit_log(endpoint_name, expected_event_type, expected_payload_keys):
    """TKT-023..028 — endpoints admin escriben ``AcademyActivityLog`` con event_type y payload correctos.

    Verificación estática via ``inspect.getsource``:
    - ``event_type="<expected>"`` aparece en el body de la función.
    - ``payload_json={"<key>": ...`` aparece para cada key esperada.

    Si alguien elimina la línea de audit log o cambia el event_type, este gate falla.
    """
    source = _get_endpoint_source(endpoint_name)

    # 1. La función llama AcademyActivityLog con event_type correcto.
    expected_call = f'event_type="{expected_event_type}"'
    assert expected_call in source, (
        f"{endpoint_name} debe llamar AcademyActivityLog con {expected_call}, "
        f"pero el source no lo contiene"
    )

    # 2. ``payload_json={{...}}`` está presente.
    assert "payload_json=" in source, (
        f"{endpoint_name} debe incluir ``payload_json={{...}}`` en AcademyActivityLog"
    )

    # 3. Cada key esperada aparece en el source (búsqueda simple, robusta a
    #    cualquier anidación de dict/lista).
    for key in expected_payload_keys:
        assert f'"{key}"' in source, (
            f"{endpoint_name} payload_json debe incluir '{key}', "
            f"source no lo contiene"
        )


# ──────────────────────────────────────────────────────────────────────
# TKT-090: foro global course_id=None requiere academy:edit/manage
# ──────────────────────────────────────────────────────────────────────


def test_tkt_090_create_forum_thread_global_requires_edit_permission():
    """TKT-090 — ``create_forum_thread`` retorna 403 si ``course_id=None`` y user sin ``academy:edit``/``academy:manage``.

    Drift detectado: el código YA valida con `get_user_effective_permissions` +
    raise HTTPException 403 si el user no tiene los permisos correctos.
    """
    source = inspect.getsource(create_forum_thread)

    # 1. La función checa ``payload.course_id is None``.
    assert "course_id is None" in source, (
        "create_forum_thread debe chequear payload.course_id is None para hilos globales"
    )

    # 2. Verifica permisos del usuario via ``get_user_effective_permissions``.
    assert "get_user_effective_permissions" in source, (
        "create_forum_thread debe llamar get_user_effective_permissions para validar permisos"
    )

    # 3. Verifica explícitamente los permisos ``academy:edit`` y ``academy:manage``.
    assert "academy:edit" in source, (
        "create_forum_thread debe verificar permiso academy:edit"
    )
    assert "academy:manage" in source, (
        "create_forum_thread debe verificar permiso academy:manage"
    )

    # 4. Raise HTTPException con status_code 403.
    assert "status_code=403" in source or "status.HTTP_403" in source, (
        "create_forum_thread debe raise HTTPException 403 para estudiantes sin permisos"
    )


# ──────────────────────────────────────────────────────────────────────
# TKT-091: PATCH /forum/threads/{thread_id}/resolve existe
# ──────────────────────────────────────────────────────────────────────


def test_tkt_091_resolve_forum_thread_endpoint_exists():
    """TKT-091 — existe endpoint ``PATCH /forum/threads/{thread_id}/resolve`` que toggle ``is_resolved``."""
    import backend.api.academy as academy_module

    # ``inspect.getsource(APIRouter)`` no funciona porque ``router`` es una
    # instancia, no un code object. Leemos el archivo fuente directamente para
    # encontrar el decorator ``@router.patch``.
    source_path = academy_module.__file__
    assert source_path is not None, "academy.py debe tener __file__"
    with open(source_path, encoding="utf-8") as fh:
        module_source = fh.read()

    # 1. Existe el decorator ``@router.patch`` con el path correcto en el módulo.
    pattern = r'@router\.patch\(\s*[\'"][^\'"]*/forum/threads/\{thread_id\}/resolve[\'"]'
    assert re.search(pattern, module_source), (
        "Debe existir @router.patch('/forum/threads/{thread_id}/resolve') "
        "decorando la función resolve_forum_thread"
    )

    # 2. La función ``resolve_forum_thread`` toggle ``is_resolved`` explícitamente.
    func_source = inspect.getsource(resolve_forum_thread)
    assert "is_resolved" in func_source, (
        "resolve_forum_thread debe referenciar is_resolved"
    )
    assert re.search(r"is_resolved\s*=\s*not\s+bool\(", func_source), (
        "resolve_forum_thread debe alternar is_resolved con ``not bool(...)`` "
        "(patrón toggle explícito)"
    )

    # 3. Solo Editor/Manager pueden invocarlo (verificación de permisos via require_module_access).
    sig = inspect.signature(resolve_forum_thread)
    params = sig.parameters
    assert "current_user" in params, (
        "resolve_forum_thread debe recibir current_user como parámetro"
    )
    # Verificamos que el source usa el alias ``current_user: AcademyEditor``
    # o ``current_user: AcademyManager``. ``AcademyEditor = Annotated[User, Depends(require_module_access("academy","edit"))]``
    # se declara a nivel módulo, así que ``get_type_hints`` no preserva la info del alias.
    # Inspeccionamos el source directamente para el type annotation.
    assert "current_user: AcademyEditor" in func_source or "current_user: AcademyManager" in func_source, (
        "resolve_forum_thread debe declarar current_user: AcademyEditor o AcademyManager "
        "para restringir acceso a Editor/Manager"
    )


# ──────────────────────────────────────────────────────────────────────
# TKT-134: nightly regression subset (subset del ACAD-T134 master gate)
# ──────────────────────────────────────────────────────────────────────# TKT-134 eliminado — el subset nightly de audit logs YA está cubierto por los 6
# tests parametrizados ``test_tkt_023_to_028_audit_log`` anteriores. El master gate
# ``test_acad_tkt_134_audit_logs`` en ``test_academy_backlog.py`` corre en nightly CI.
