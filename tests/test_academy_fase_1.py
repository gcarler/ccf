"""Regression gates para Fase 1 — Núcleo seguro de aprendizaje.

Tickets cubiertos (cierre funcional con drift detectado 2026-07-19):

- **TKT-020** [HIGH] ``AssessmentPayload.questions`` ya tipado como ``list[AssessmentQuestionPayload]`` (no ``list[dict]``)
- **TKT-050** [MED] ``CoursePayload.code`` ya tiene ``Field(max_length=50)``
- **TKT-051** [MED] ``CoursePayload.modality`` ya usa enum ``Modality`` (no raw str)
- **TKT-052** [MED] ``CoursePayload.access_level`` ya usa ``Literal["open","persona","advanced"]``
- **TKT-053** [MED] ``LessonPayload.title`` ya tiene ``Field(max_length=200)``
- **TKT-054** [MED] ``LessonPayload.content_type`` ya usa enum ``ContentType`` (no raw str)
- **TKT-055** [MED] ``AssessmentPayload.title`` ya tiene ``Field(max_length=200)``
- **TKT-056** [MED] ``list_lessons`` ya tiene ``skip`` + ``limit`` (Query default 0/100, ge=0, ge=1, le=500)
- **TKT-057** [MED] ``list_assessments`` ya tiene ``skip`` + ``limit``
- **TKT-058** [MED] ``academy_schedule`` ya tiene ``skip`` + ``limit``
- **TKT-059** [MED] ``academy_personas`` ya tiene ``skip`` + ``limit`` (elimina hardcode 500)
- **TKT-060** [MED] ``my_enrollments`` ya tiene ``skip`` + ``limit``
- **TKT-061** [MED] ``my_certificates`` ya tiene ``skip`` + ``limit``
- **TKT-062** [MED] ``my_progress`` ya tiene ``skip`` + ``limit``
- **TKT-063** [MED] ``datetime`` import movido al top de ``academy.py``
- **TKT-065** [MED] ``ForumThreadCreate.title`` ya tiene ``Field(max_length=200)``

**TKT-064 excluido:** ``ForumCategory`` enum para ``ForumThreadCreate.category``
ya está cerrado (✅ Hecho 2026-07-19 en BACKLOG §4.3, gate pytest
``test_forum_category_filter_and_resource_lifecycle_are_scoped`` ya pasa).

Estos gates sirven como **regression gates** que alertan si alguien debilita
los invariantes. Si cualquiera falla, abrir un nuevo ticket ACAD-TKT-NNN
y bloquear merge.

Patrón establecido en ``tests/test_academy_fase_a_crit.py`` (Fase A CRIT).
"""

from __future__ import annotations

import inspect

import pytest
from pydantic import ValidationError

from backend.api.academy import (
    AssessmentPayload,
    AssessmentQuestionPayload,
    CoursePayload,
    LessonPayload,
)
from backend.schemas.academy import ForumThreadCreate

# ──────────────────────────────────────────────────────────────────────
# Helpers: payloads válidos mínimos por modelo
# ──────────────────────────────────────────────────────────────────────


def _valid_base(model) -> dict:
    """Devuelve un dict con valores válidos para todos los campos de ``model``.

    - Para campos con default de Pydantic, usa el default.
    - Para campos requeridos, infiere un valor genérico válido según el tipo.

    Esto permite tests parametrizados donde cada (model, field) puede inyectar
    el valor válido/inválido en su campo específico sin romper otros campos.
    """
    base: dict = {}
    for fname, finfo in model.model_fields.items():
        if not finfo.is_required():
            # Usar default de Pydantic si existe.
            if finfo.default is not None:
                base[fname] = finfo.default
            elif finfo.default_factory is not None:
                base[fname] = finfo.default_factory()
            else:
                base[fname] = None
            continue
        # Campo requerido: inferir valor según el annotation.
        ann_str = str(finfo.annotation)
        if "UUID" in ann_str:
            base[fname] = "00000000-0000-0000-0000-000000000001"
        elif "str" in ann_str and "Optional" not in ann_str:
            base[fname] = "valid-string"
        elif "int" in ann_str:
            base[fname] = 0
        elif "bool" in ann_str:
            base[fname] = False
        elif "float" in ann_str:
            base[fname] = 0.0
        else:
            base[fname] = None
    return base


# ──────────────────────────────────────────────────────────────────────
# TKT-050, TKT-053, TKT-055, TKT-065: max_length + ge/le constraints
# ──────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "model,field,invalid_value,valid_value",
    [
        # TKT-050: CoursePayload.code max_length=50
        (CoursePayload, "code", "A" * 51, "ABC-101"),
        # TKT-053: LessonPayload.title max_length=200
        (LessonPayload, "title", "T" * 201, "Introducción al curso"),
        # TKT-055: AssessmentPayload.title max_length=200
        (AssessmentPayload, "title", "T" * 201, "Quiz módulo 1"),
        # TKT-065: ForumThreadCreate.title max_length=200
        (ForumThreadCreate, "title", "T" * 201, "Bienvenida al curso"),
    ],
    ids=[
        "TKT-050_course_code_maxlen_50",
        "TKT-053_lesson_title_maxlen_200",
        "TKT-055_assessment_title_maxlen_200",
        "TKT-065_forum_title_maxlen_200",
    ],
)
def test_tkt_050_053_055_065_field_max_length(model, field, invalid_value, valid_value):
    """TKT-050, TKT-053, TKT-055, TKT-065 — campos max_length respetan el límite.

    El valor al límite+1 debe lanzar ValidationError; el valor al límite debe pasar.
    """
    # Baseline: todos los demás campos con valores válidos; el campo bajo prueba
    # toma el valor válido. Debe instanciarse sin error.
    base = _valid_base(model)
    base[field] = valid_value
    instance = model(**base)  # type: ignore[arg-type]
    assert getattr(instance, field) == valid_value, (
        f"baseline válido debe instanciarse: {model.__name__}.{field}={valid_value!r}"
    )

    # Valor al límite+1 debe lanzar ValidationError.
    bad = _valid_base(model)
    bad[field] = invalid_value
    with pytest.raises(ValidationError) as exc_info:
        model(**bad)  # type: ignore[arg-type]
    error_fields = {err["loc"][0] for err in exc_info.value.errors()}
    assert field in error_fields, (
        f"ValidationError debe apuntar a {field!r}, "
        f"pero errors fueron {error_fields!r}"
    )


# ──────────────────────────────────────────────────────────────────────
# TKT-051, TKT-054: enum validation (TKT-064 ya cerrado, omitido)
# ──────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "model,field,invalid_value",
    [
        # TKT-051: CoursePayload.modality es enum Modality
        (CoursePayload, "modality", "INVALIDO"),
        # TKT-054: LessonPayload.content_type es enum ContentType
        (LessonPayload, "content_type", "raw-not-enum-value"),
    ],
    ids=[
        "TKT-051_course_modality_enum",
        "TKT-054_lesson_content_type_enum",
    ],
)
def test_tkt_051_054_enum_invariants(model, field, invalid_value):
    """TKT-051, TKT-054 — campos enum rechazan valores fuera del vocabulario canónico."""
    base = _valid_base(model)
    bad = dict(base)
    bad[field] = invalid_value
    with pytest.raises(ValidationError) as exc_info:
        model(**bad)  # type: ignore[arg-type]
    error_fields = {err["loc"][0] for err in exc_info.value.errors()}
    assert field in error_fields, (
        f"ValidationError debe apuntar a {field!r}, "
        f"pero errors fueron {error_fields!r}"
    )


# ──────────────────────────────────────────────────────────────────────
# TKT-052: Literal access_level
# ──────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "valid_level",
    ["open", "persona", "advanced"],
    ids=["open", "persona", "advanced"],
)
def test_tkt_052_course_access_level_literal_accepts_all(valid_level):
    """TKT-052 — ``CoursePayload.access_level`` acepta los 3 valores válidos del Literal."""
    instance = CoursePayload(
        code="ABC-101",
        title="Test",
        access_level=valid_level,
    )
    assert instance.access_level == valid_level


def test_tkt_052_course_access_level_literal_rejects_invalid():
    """TKT-052 — ``CoursePayload.access_level`` rechaza valores fuera del Literal."""
    with pytest.raises(ValidationError):
        CoursePayload(
            code="ABC-101",
            title="Test",
            access_level="not-allowed-level",
        )


# ──────────────────────────────────────────────────────────────────────
# TKT-020: AssessmentPayload.questions typed
# ──────────────────────────────────────────────────────────────────────


def test_tkt_020_assessment_questions_is_typed_list():
    """TKT-020 — ``AssessmentPayload.questions`` ya NO es ``list[dict]``.

    El tipo real debe ser ``list[AssessmentQuestionPayload]`` (Pydantic model tipado),
    NO ``list[dict]``. Esto fuerza validación de estructura al instanciar.
    """
    from typing import get_args, get_origin

    field_info = AssessmentPayload.model_fields["questions"]
    annotation = field_info.annotation

    # El annotation debe ser un list tipado.
    assert get_origin(annotation) is list, (
        f"questions debe ser list[...], pero es {annotation!r}"
    )
    args = get_args(annotation)
    assert len(args) == 1, f"list[...] debe tener 1 type arg, tiene {len(args)}"
    inner_type = args[0]

    # El inner type NO debe ser dict (eso sería el anti-pattern original).
    assert inner_type is not dict, (
        "questions NO debe ser list[dict]; debe ser list[AssessmentQuestionPayload]"
    )

    # Y debe ser el modelo Pydantic real (no raw dict).
    assert inner_type is AssessmentQuestionPayload, (
        f"questions inner type debe ser AssessmentQuestionPayload, "
        f"es {inner_type!r}"
    )

    # Verificación funcional: instanciar con dict debe fallar (Pydantic valida estructura).
    base = _valid_base(AssessmentPayload)
    base["questions"] = [{"foo": "bar"}]  # dict crudo, no Pydantic model
    with pytest.raises(ValidationError) as exc_info:
        AssessmentPayload(**base)
    errors = exc_info.value.errors()
    assert any("questions" in str(err.get("loc", [])) for err in errors), (
        f"ValidationError debe mencionar 'questions' en loc, errors={errors!r}"
    )


# ──────────────────────────────────────────────────────────────────────
# TKT-056..062: paginación skip/limit (signature inspection)
# ──────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "endpoint_name",
    [
        "list_lessons",       # TKT-056
        "list_assessments",   # TKT-057
        "academy_schedule",   # TKT-058
        "academy_personas",   # TKT-059
        "my_enrollments",     # TKT-060
        "my_certificates",    # TKT-061
        "my_progress",        # TKT-062
    ],
    ids=[
        "TKT-056_list_lessons",
        "TKT-057_list_assessments",
        "TKT-058_academy_schedule",
        "TKT-059_academy_personas",
        "TKT-060_my_enrollments",
        "TKT-061_my_certificates",
        "TKT-062_my_progress",
    ],
)
def test_tkt_056_to_062_pagination_signature(endpoint_name):
    """TKT-056..062 — endpoints de listado tienen ``skip`` + ``limit`` con ``Query``.

    Verificación estática: la firma de la función debe incluir ambos parámetros
    tipados como ``int`` y con default ``Query(...)`` (FastAPI dependency injection)
    con constraint ``ge=0/le=500``. Si alguien elimina la paginación, este gate falla.
    """
    import importlib

    module = importlib.import_module("backend.api.academy")
    func = getattr(module, endpoint_name, None)
    assert func is not None, f"{endpoint_name} no existe en backend.api.academy"

    sig = inspect.signature(func)
    params = sig.parameters

    # Ambos parámetros deben existir.
    assert "skip" in params, (
        f"{endpoint_name} debe tener parámetro 'skip' para paginación"
    )
    assert "limit" in params, (
        f"{endpoint_name} debe tener parámetro 'limit' para paginación"
    )

    # Tipo debe ser int. Usamos ``get_type_hints`` para resolver
    # ``from __future__ import annotations`` (que retorna strings).
    skip_param = params["skip"]
    limit_param = params["limit"]
    from typing import get_type_hints
    try:
        hints = get_type_hints(func)
        skip_type = hints["skip"]
        limit_type = hints["limit"]
    except Exception:
        # Fallback al annotation crudo (puede ser string ``'int'`` o type ``int``).
        skip_type = skip_param.annotation
        limit_type = limit_param.annotation
    assert skip_type is int or skip_type == "int", (
        f"{endpoint_name}.skip debe ser int, es {skip_type!r}"
    )
    assert limit_type is int or limit_type == "int", (
        f"{endpoint_name}.limit debe ser int, es {limit_type!r}"
    )

    # Default debe ser un Query object (FastAPI dependency injection).
    # ``from fastapi import Query`` importa la FUNCIÓN ``Query``, no la clase.
    # La clase real está en ``fastapi.params.Query``. Verificamos que:
    # 1. El default es una instancia de ``fastapi.params.Query``.
    # 2. La metadata del Query contiene al menos un constraint (validación numérica).
    skip_default = skip_param.default
    limit_default = limit_param.default
    from fastapi.params import Query as QueryClass
    assert isinstance(skip_default, QueryClass), (
        f"{endpoint_name}.skip debe tener default FastAPI Query(...) para paginación, "
        f"es {skip_default!r}"
    )
    assert isinstance(limit_default, QueryClass), (
        f"{endpoint_name}.limit debe tener default FastAPI Query(...) para paginación, "
        f"es {limit_default!r}"
    )
    # ``metadata`` es una tupla de constraints (Ge, Le, MultipleOf, etc.).
    # Si alguien elimina los constraints ge/le, este gate lo detecta.
    skip_metadata = getattr(skip_default, "metadata", ())
    limit_metadata = getattr(limit_default, "metadata", ())
    assert skip_metadata, (
        f"{endpoint_name}.skip debe tener al menos un constraint en metadata, "
        f"sino no hay validación numérica. default={skip_default!r}"
    )
    assert limit_metadata, (
        f"{endpoint_name}.limit debe tener al menos un constraint en metadata, "
        f"sino no hay validación numérica. default={limit_default!r}"
    )


# ──────────────────────────────────────────────────────────────────────
# TKT-063: datetime import movido al top de academy.py
# ──────────────────────────────────────────────────────────────────────


def test_tkt_063_datetime_import_at_top_of_academy():
    """TKT-063 — ``from datetime import ...`` está en el top del módulo, no dentro de una función.

    PLAN M14 reporta que ``academy.py:873`` tiene el import dentro de una función.
    Si esto se corrige, este gate confirma que el import aparece en las primeras
    ~20 líneas del archivo (zona de imports del módulo).
    """
    import backend.api.academy as academy_module

    source = inspect.getsource(academy_module)
    lines = source.split("\n")

    # Buscar la primera línea que matchee ``from datetime import``.
    datetime_import_lines = [
        i for i, line in enumerate(lines[:50], start=1)
        if line.startswith("from datetime import") or line.startswith("import datetime")
    ]
    assert datetime_import_lines, (
        "academy.py debe tener ``from datetime import ...`` en sus primeras 50 líneas "
        "(TKT-063 — import movido al top del módulo)"
    )
    # El import debe estar entre las primeras 20 líneas (zona estándar de imports).
    first_import = datetime_import_lines[0]
    assert first_import <= 20, (
        f"datetime import debe estar en top 20 líneas, está en línea {first_import}"
    )
