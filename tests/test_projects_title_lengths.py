"""Persisted Projects title schemas must match their VARCHAR(200) columns."""

import math

import pytest
from pydantic import ValidationError

from backend.schemas.projects import (
    InstantiateProjectFromTemplate,
    normalize_wbs_component_code,
    ProjectBase,
    ProjectChangeRequestCreate,
    ProjectDocumentCreate,
    ProjectDocumentUpdate,
    ProjectMilestoneBase,
    ProjectMilestoneUpdate,
    ProjectRiskBase,
    ProjectRiskUpdate,
    ProjectTaskBase,
    ProjectTaskUpdate,
    ProjectUpdate,
    ProjectWhiteboardUpdate,
    TemplateTaskItem,
    validate_pmi_severity_matrix_bounds,
)


@pytest.mark.parametrize(
    ("schema", "payload"),
    [
        (ProjectBase, {"title": "Proyecto"}),
        (ProjectUpdate, {"title": "Proyecto"}),
        (ProjectTaskBase, {"title": "Tarea"}),
        (ProjectTaskUpdate, {"title": "Tarea"}),
        (ProjectMilestoneBase, {"title": "Hito"}),
        (ProjectMilestoneUpdate, {"title": "Hito"}),
        (ProjectRiskBase, {"title": "Riesgo"}),
        (ProjectRiskUpdate, {"title": "Riesgo"}),
        (ProjectDocumentCreate, {"title": "Wiki", "project_id": "00000000-0000-0000-0000-000000000001"}),
        (ProjectDocumentUpdate, {"title": "Wiki"}),
        (ProjectWhiteboardUpdate, {"title": "Pizarra"}),
        (TemplateTaskItem, {"title": "Tarea de plantilla"}),
        (InstantiateProjectFromTemplate, {"title": "Proyecto desde plantilla"}),
        (ProjectChangeRequestCreate, {"title": "CR", "justification": "Justificación"}),
    ],
    ids=lambda value: value.__name__ if isinstance(value, type) else None,
)
def test_persisted_title_schemas_reject_values_over_column_limit(schema, payload):
    schema.model_validate({**payload, "title": "x" * 200})

    with pytest.raises(ValidationError):
        schema.model_validate({**payload, "title": "x" * 201})


# ── Helpers PMI: normalizador de códigos WBS ───────────────────────────────


def test_normalize_wbs_component_code_replaces_whitespace_and_uppercases():
    """' edt 1.1 ' → 'EDT-1.1' (espacios internos → '-', trim + mayúsculas)."""
    assert normalize_wbs_component_code(" edt 1.1 ") == "EDT-1.1"
    assert normalize_wbs_component_code("cmp\t02\tA") == "CMP-02-A"
    # Guiones bajos se conservan del código original
    assert normalize_wbs_component_code("cmp_02") == "CMP_02"


def test_normalize_wbs_component_code_none_and_blank():
    """None, '' y espacios blanco devuelven None."""
    assert normalize_wbs_component_code(None) is None
    assert normalize_wbs_component_code("") is None
    assert normalize_wbs_component_code("   ") is None


# ── Helpers PMI: matriz de riesgos 5x5 ────────────────────────────────────


def test_validate_pmi_severity_matrix_bands():
    """Bandas de severidad: low / moderate / high / critical según score=p*i."""
    assert validate_pmi_severity_matrix_bounds(1, 4) == {
        "probability": 1,
        "impact": 4,
        "severity_score": 4,
        "severity_band": "low",
    }
    assert validate_pmi_severity_matrix_bounds(2, 3)["severity_band"] == "moderate"  # 6
    assert validate_pmi_severity_matrix_bounds(2, 5)["severity_band"] == "high"  # 10
    assert validate_pmi_severity_matrix_bounds(3, 5)["severity_band"] == "critical"  # 15
    assert validate_pmi_severity_matrix_bounds(5, 5)["severity_band"] == "critical"  # 25


def test_validate_pmi_severity_matrix_clamps_out_of_range():
    """Entradas fuera de rango se clampan a 1..5: (0, 9) → p=1, i=5, score=5, 'moderate'."""
    result = validate_pmi_severity_matrix_bounds(0, 9)
    assert result["probability"] == 1
    assert result["impact"] == 5
    assert result["severity_score"] == 5
    assert result["severity_band"] == "moderate"

    # Cero se trata como inválido (or 1) y negativos quedan en 1
    assert validate_pmi_severity_matrix_bounds(-3, -2)["probability"] == 1
    assert validate_pmi_severity_matrix_bounds(-3, -2)["impact"] == 1
    assert validate_pmi_severity_matrix_bounds(-3, -2)["severity_band"] == "low"
    # Valores extremos altos quedan en 5
    assert validate_pmi_severity_matrix_bounds(99, 99)["severity_score"] == 25
    # Inputs convertibles a int (floats enteros) se aceptan
    assert validate_pmi_severity_matrix_bounds(2.0, 5.0)["severity_score"] == 10
