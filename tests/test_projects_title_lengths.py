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
    validate_milestone_weights_distribution,
    validate_pmi_severity_matrix_bounds,
    validate_raci_assignment_matrix,
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


# ── Helpers PMI: distribución de pesos de hitos (Weighted Milestones EVMT) ──


def test_validate_milestone_weights_distribution_balanced():
    """Distribución equilibrada de múltiples hitos ([20, 30, 50]) e hito único ([100])."""
    res = validate_milestone_weights_distribution([20, 30, 50])
    assert res == {
        "total_milestones": 3,
        "positive_weight_count": 3,
        "zero_or_negative_count": 0,
        "total_weight": 100.0,
        "normalized_shares_pct": [20.0, 30.0, 50.0],
        "max_share_pct": 50.0,
        "is_balanced": True,
    }

    single_res = validate_milestone_weights_distribution([100])
    assert single_res["total_milestones"] == 1
    assert single_res["max_share_pct"] == 100.0
    assert single_res["is_balanced"] is True


def test_validate_milestone_weights_distribution_excessive_concentration():
    """Concentración > 80% en un hito cuando hay múltiples hitos se marca como desbalanceada."""
    res = validate_milestone_weights_distribution([90, 5, 5])
    assert res["total_milestones"] == 3
    assert res["normalized_shares_pct"] == [90.0, 5.0, 5.0]
    assert res["max_share_pct"] == 90.0
    assert res["is_balanced"] is False


def test_validate_milestone_weights_distribution_zero_or_negative_weights():
    """Presencia de pesos cero o negativos incrementa zero_or_negative_count e invalida el balance."""
    res = validate_milestone_weights_distribution([50, 0, -10])
    assert res["total_milestones"] == 3
    assert res["positive_weight_count"] == 1
    assert res["zero_or_negative_count"] == 2
    assert res["total_weight"] == 50.0
    assert res["normalized_shares_pct"] == [100.0, 0.0, 0.0]
    assert res["is_balanced"] is False


def test_validate_milestone_weights_distribution_empty_or_none():
    """Lista vacía o None retorna total_milestones=0, normalized_shares_pct=[] e is_balanced=False."""
    for empty_input in ([], None, [None, True, False]):
        res = validate_milestone_weights_distribution(empty_input)  # type: ignore[arg-type]
        assert res == {
            "total_milestones": 0,
            "positive_weight_count": 0,
            "zero_or_negative_count": 0,
            "total_weight": 0.0,
            "normalized_shares_pct": [],
            "max_share_pct": 0.0,
            "is_balanced": False,
        }


# ── Helpers PMI: matriz de asignación de responsabilidades RACI (§9.1.2.2) ──


def test_validate_raci_assignment_matrix_valid_compliant():
    """Matriz RACI con exactamente 1 Accountable y al menos 1 Responsible cumple la regla PMI."""
    res = validate_raci_assignment_matrix(
        [
            {"role": "Accountable"},
            {"role": "R"},
            {"raci_role": "C"},
            {"raci_role": "informed"},
        ]
    )
    assert res == {
        "responsible_count": 1,
        "accountable_count": 1,
        "consulted_count": 1,
        "informed_count": 1,
        "invalid_role_count": 0,
        "has_single_accountable": True,
        "has_at_least_one_responsible": True,
        "is_raci_compliant": True,
        "raci_violation_reason": "none",
    }


def test_validate_raci_assignment_matrix_missing_accountable():
    """Falta de Accountable (accountable_count == 0) reporta missing_accountable."""
    res = validate_raci_assignment_matrix([{"role": "Responsible"}, {"raci_role": "Consulted"}])
    assert res["accountable_count"] == 0
    assert res["responsible_count"] == 1
    assert res["has_single_accountable"] is False
    assert res["is_raci_compliant"] is False
    assert res["raci_violation_reason"] == "missing_accountable"


def test_validate_raci_assignment_matrix_multiple_accountable():
    """Múltiples Accountable (accountable_count > 1) reporta multiple_accountable."""
    res = validate_raci_assignment_matrix(
        [{"role": "A"}, {"raci_role": "ACCOUNTABLE"}, {"role": "R"}]
    )
    assert res["accountable_count"] == 2
    assert res["responsible_count"] == 1
    assert res["has_single_accountable"] is False
    assert res["is_raci_compliant"] is False
    assert res["raci_violation_reason"] == "multiple_accountable"


def test_validate_raci_assignment_matrix_missing_responsible_and_invalid_role():
    """Valida falta de Responsible (missing_responsible) y presencia de rol inválido (invalid_role)."""
    no_resp = validate_raci_assignment_matrix([{"role": "A"}, {"raci_role": "C"}])
    assert no_resp["accountable_count"] == 1
    assert no_resp["responsible_count"] == 0
    assert no_resp["has_at_least_one_responsible"] is False
    assert no_resp["is_raci_compliant"] is False
    assert no_resp["raci_violation_reason"] == "missing_responsible"

    invalid_role = validate_raci_assignment_matrix(
        [{"role": "A"}, {"role": "R"}, {"raci_role": "OWNER"}]
    )
    assert invalid_role["accountable_count"] == 1
    assert invalid_role["responsible_count"] == 1
    assert invalid_role["invalid_role_count"] == 1
    assert invalid_role["is_raci_compliant"] is False
    assert invalid_role["raci_violation_reason"] == "invalid_role"
