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


# ── validate_pmi_risk_response_strategy (PMBOK §11.5, pure helper) ────────


def test_risk_response_strategy_valid_threat_and_acceptance_modes():
    """Threat alineado (mitigate/avoid) y accept con contingencia activa vs pasiva."""
    from backend.schemas.projects import validate_pmi_risk_response_strategy

    mitigate = validate_pmi_risk_response_strategy("THREAT", " Mitigate ", -3)
    assert mitigate == {
        "risk_type": "threat",
        "strategy": "mitigate",
        "contingency_reserve": 0.0,  # negativa se clampea a 0
        "is_valid_risk_type": True,
        "is_aligned_strategy": True,
        "acceptance_mode": "not_applicable",
        "allowed_strategies": ["accept", "avoid", "escalate", "mitigate", "transfer"],
        "response_validity_status": "valid_response",
    }

    active = validate_pmi_risk_response_strategy("threat", "accept", 2500.0)
    assert active["acceptance_mode"] == "active_acceptance"
    assert active["contingency_reserve"] == 2500.0
    assert active["response_validity_status"] == "valid_response"

    passive = validate_pmi_risk_response_strategy("threat", "ACCEPT", 0.0)
    assert passive["acceptance_mode"] == "passive_acceptance"
    assert passive["response_validity_status"] == "valid_response"
    assert passive["is_aligned_strategy"] is True


def test_risk_response_strategy_valid_opportunity():
    """Opportunity con exploit/enhance alineados → valid_response."""
    from backend.schemas.projects import OPPORTUNITY_STRATEGIES, validate_pmi_risk_response_strategy

    exploit = validate_pmi_risk_response_strategy("opportunity", "exploit", 150.75)
    assert exploit == {
        "risk_type": "opportunity",
        "strategy": "exploit",
        "contingency_reserve": 150.75,
        "is_valid_risk_type": True,
        "is_aligned_strategy": True,
        "acceptance_mode": "not_applicable",
        "allowed_strategies": ["accept", "enhance", "escalate", "exploit", "share"],
        "response_validity_status": "valid_response",
    }
    enhance = validate_pmi_risk_response_strategy("Opportunity", "ENHANCE")
    assert enhance["is_aligned_strategy"] is True
    assert enhance["response_validity_status"] == "valid_response"
    # 'escalate' y 'accept' comparten ambos conjuntos
    assert "escalate" in OPPORTUNITY_STRATEGIES and "accept" in OPPORTUNITY_STRATEGIES


def test_risk_response_strategy_misaligned():
    """Estrategia del tipo opuesto → 'misaligned_strategy'."""
    from backend.schemas.projects import validate_pmi_risk_response_strategy

    exploit_en_threat = validate_pmi_risk_response_strategy("threat", "exploit")
    assert exploit_en_threat["is_aligned_strategy"] is False
    assert exploit_en_threat["response_validity_status"] == "misaligned_strategy"

    mitigate_en_oportunity = validate_pmi_risk_response_strategy("opportunity", "mitigate")
    assert mitigate_en_oportunity["is_aligned_strategy"] is False
    # acceptance_mode aún aplica por regla de estrategia 'accept' sólo si es accept;
    # mitigate no es accept → not_applicable
    assert mitigate_en_oportunity["acceptance_mode"] == "not_applicable"


def test_risk_response_strategy_invalid_type_and_missing_strategy():
    """Tipo inválido → 'invalid_risk_type' (sin allowed); estrategia vacía → 'missing_strategy'."""
    from backend.schemas.projects import validate_pmi_risk_response_strategy

    weird = validate_pmi_risk_response_strategy("hybrid", "mitigate")
    assert weird == {
        "risk_type": "hybrid",
        "strategy": "mitigate",
        "contingency_reserve": 0.0,
        "is_valid_risk_type": False,
        "is_aligned_strategy": False,
        "acceptance_mode": "not_applicable",
        "allowed_strategies": [],
        "response_validity_status": "invalid_risk_type",
    }

    missing = validate_pmi_risk_response_strategy(None, None)
    assert missing["risk_type"] == "threat"  # default por tipo vacío/None
    assert missing["strategy"] == ""
    assert missing["is_valid_risk_type"] is True
    assert missing["is_aligned_strategy"] is False
    assert missing["response_validity_status"] == "missing_strategy"

    blank = validate_pmi_risk_response_strategy("threat", "   ")
    assert blank["strategy"] == ""
    assert blank["response_validity_status"] == "missing_strategy"


def test_classify_stakeholder_quadrant_manage_closely_and_keep_satisfied():
    """Verifica cuadrantes de alto poder: manage_closely y keep_satisfied."""
    from backend.schemas.projects import classify_stakeholder_power_interest_quadrant

    closely = classify_stakeholder_power_interest_quadrant(5, 4)
    assert closely["power"] == 5
    assert closely["interest"] == 4
    assert closely["salience_index"] == 20
    assert closely["is_high_power"] is True
    assert closely["is_high_interest"] is True
    assert closely["is_clamped"] is False
    assert closely["quadrant_code"] == "manage_closely"
    assert (
        closely["recommended_strategy"]
        == "Involucrar activamente y gestionar de cerca en decisiones clave"
    )

    satisfied = classify_stakeholder_power_interest_quadrant(4, 2)
    assert satisfied["power"] == 4
    assert satisfied["interest"] == 2
    assert satisfied["salience_index"] == 8
    assert satisfied["is_high_power"] is True
    assert satisfied["is_high_interest"] is False
    assert satisfied["is_clamped"] is False
    assert satisfied["quadrant_code"] == "keep_satisfied"
    assert (
        satisfied["recommended_strategy"]
        == "Mantener satisfecho sin saturar con detalles operativos"
    )


def test_classify_stakeholder_quadrant_keep_informed_and_monitor():
    """Verifica cuadrantes de bajo poder: keep_informed y monitor."""
    from backend.schemas.projects import classify_stakeholder_power_interest_quadrant

    informed = classify_stakeholder_power_interest_quadrant(2, 5)
    assert informed["power"] == 2
    assert informed["interest"] == 5
    assert informed["salience_index"] == 10
    assert informed["is_high_power"] is False
    assert informed["is_high_interest"] is True
    assert informed["is_clamped"] is False
    assert informed["quadrant_code"] == "keep_informed"
    assert (
        informed["recommended_strategy"]
        == "Mantener informado periódicamente y consultar en su área"
    )

    monitor = classify_stakeholder_power_interest_quadrant(1, 2)
    assert monitor["power"] == 1
    assert monitor["interest"] == 2
    assert monitor["salience_index"] == 2
    assert monitor["is_high_power"] is False
    assert monitor["is_high_interest"] is False
    assert monitor["is_clamped"] is False
    assert monitor["quadrant_code"] == "monitor"
    assert (
        monitor["recommended_strategy"]
        == "Monitorear con esfuerzo mínimo de comunicación"
    )


def test_classify_stakeholder_quadrant_clamps_out_of_bounds_and_none():
    """Verifica acotación en [1, 5] y manejo seguro de valores None."""
    from backend.schemas.projects import classify_stakeholder_power_interest_quadrant

    out_of_bounds = classify_stakeholder_power_interest_quadrant(9, -2)
    assert out_of_bounds["power"] == 5
    assert out_of_bounds["interest"] == 1
    assert out_of_bounds["salience_index"] == 5
    assert out_of_bounds["is_clamped"] is True
    assert out_of_bounds["quadrant_code"] == "keep_satisfied"

    nones = classify_stakeholder_power_interest_quadrant(None, None)
    assert nones["power"] == 1
    assert nones["interest"] == 1
    assert nones["salience_index"] == 1
    assert nones["is_clamped"] is True
    assert nones["quadrant_code"] == "monitor"


def test_classify_stakeholder_quadrant_custom_threshold():
    """Verifica que un umbral personalizado high_threshold=4 reclasifique (3, 3) en monitor."""
    from backend.schemas.projects import classify_stakeholder_power_interest_quadrant

    custom = classify_stakeholder_power_interest_quadrant(3, 3, high_threshold=4)
    assert custom["power"] == 3
    assert custom["interest"] == 3
    assert custom["salience_index"] == 9
    assert custom["is_high_power"] is False
    assert custom["is_high_interest"] is False
    assert custom["is_clamped"] is False
    assert custom["quadrant_code"] == "monitor"


def test_validate_risk_emv_exposure_threat_high_and_moderate():
    """Valida amenaza con exposición alta (-20000.0) y moderada (-2500.0)."""
    from backend.schemas.projects import validate_risk_emv_exposure

    high = validate_risk_emv_exposure(40.0, 50000.0, "threat")
    assert high == {
        "risk_type": "threat",
        "is_valid_risk_type": True,
        "probability_pct": 40.0,
        "probability_decimal": 0.4,
        "is_prob_clamped": False,
        "impact_magnitude": 50000.0,
        "emv_magnitude": 20000.0,
        "signed_emv": -20000.0,
        "emv_exposure_tier": "high_financial_exposure",
    }

    mod = validate_risk_emv_exposure(25.0, 10000.0, "threat")
    assert mod["emv_magnitude"] == 2500.0
    assert mod["signed_emv"] == -2500.0
    assert mod["emv_exposure_tier"] == "moderate_financial_exposure"


def test_validate_risk_emv_exposure_opportunity_positive_sign():
    """Valida oportunidad con signo positivo y exposición menor (< 1000.0)."""
    from backend.schemas.projects import validate_risk_emv_exposure

    opp = validate_risk_emv_exposure(50.0, 1000.0, "opportunity")
    assert opp == {
        "risk_type": "opportunity",
        "is_valid_risk_type": True,
        "probability_pct": 50.0,
        "probability_decimal": 0.5,
        "is_prob_clamped": False,
        "impact_magnitude": 1000.0,
        "emv_magnitude": 500.0,
        "signed_emv": 500.0,
        "emv_exposure_tier": "minor_financial_exposure",
    }


def test_validate_risk_emv_exposure_clamps_probability_bounds():
    """Valida acotación de probabilidad en [0.0, 100.0] y estado zero_exposure."""
    from backend.schemas.projects import validate_risk_emv_exposure

    over = validate_risk_emv_exposure(150.0, 2000.0, "threat")
    assert over["probability_pct"] == 100.0
    assert over["probability_decimal"] == 1.0
    assert over["is_prob_clamped"] is True
    assert over["emv_magnitude"] == 2000.0
    assert over["signed_emv"] == -2000.0
    assert over["emv_exposure_tier"] == "moderate_financial_exposure"

    under = validate_risk_emv_exposure(-10.0, 2000.0, "threat")
    assert under["probability_pct"] == 0.0
    assert under["is_prob_clamped"] is True
    assert under["emv_magnitude"] == 0.0
    assert under["signed_emv"] == 0.0
    assert under["emv_exposure_tier"] == "zero_exposure"


def test_validate_risk_emv_exposure_invalid_type_and_none():
    """Valida tipo de riesgo desconocido ('invalid_risk_type') y entradas None ('zero_exposure')."""
    from backend.schemas.projects import validate_risk_emv_exposure

    invalid = validate_risk_emv_exposure(30.0, 5000.0, "unknown")
    assert invalid["risk_type"] == "unknown"
    assert invalid["is_valid_risk_type"] is False
    assert invalid["emv_exposure_tier"] == "invalid_risk_type"

    nones = validate_risk_emv_exposure(None, None)
    assert nones["is_valid_risk_type"] is True
    assert nones["is_prob_clamped"] is True
    assert nones["emv_magnitude"] == 0.0
    assert nones["emv_exposure_tier"] == "zero_exposure"


# ─── validate_ccb_change_request_justification (pure helper) ──────────────


def test_validate_ccb_change_request_high_baseline_impact_goes_to_board():
    """Impacto en baseline alto (costo >= 5000) con justificacion >= 20 -> CCB_FORMAL_BOARD_REVIEW."""
    from backend.schemas.projects import validate_ccb_change_request_justification

    by_cost = validate_ccb_change_request_justification(
        title="Ampliar presupuesto del Proyecto F",
        justification="Se requiere activo adicional aprobado por el comité de obras",
        cost_impact=5000.0,
        schedule_days_impact=0,
    )
    assert by_cost["has_baseline_impact"] is True
    assert by_cost["is_valid"] is True
    assert by_cost["impact_tier"] == "HIGH_BASELINE_IMPACT"
    assert by_cost["posture"] == "CCB_FORMAL_BOARD_REVIEW"

    by_schedule = validate_ccb_change_request_justification(
        title="Reprogramar fase 2",
        justification="El proveedor complico la ventana de instalacion21",
        cost_impact=0.0,
        schedule_days_impact=10,
    )
    assert by_schedule["schedule_delta_days"] == 10.0
    assert by_schedule["impact_tier"] == "HIGH_BASELINE_IMPACT"
    assert by_schedule["posture"] == "CCB_FORMAL_BOARD_REVIEW"


def test_validate_ccb_change_request_moderate_and_pm_delegated():
    """Impacto en baseline moderado (costo o dias != 0, < umbrales) -> PM_DELEGATED_APPROVAL_ELIGIBLE."""
    from backend.schemas.projects import validate_ccb_change_request_justification

    res = validate_ccb_change_request_justification(
        title="Ajustar cronograma",
        justification="El coro requiere desplazar el estreno una semana",
        cost_impact=0.0,
        schedule_days_impact=3,
    )
    assert res["schedule_delta_days"] == 3.0
    assert res["has_baseline_impact"] is True
    assert res["is_valid"] is True
    assert res["impact_tier"] == "MODERATE_BASELINE_IMPACT"
    assert res["posture"] == "PM_DELEGATED_APPROVAL_ELIGIBLE"


def test_validate_ccb_change_request_rejects_insufficient_justification():
    """Justificación corta según impacto (>= 20 con baseline, >= 10 admin) -> REJECTED_INSUFFICIENT_JUSTIFICATION."""
    from backend.schemas.projects import validate_ccb_change_request_justification

    with_baseline = validate_ccb_change_request_justification(
        title="Cambiar costos",
        justification="Solo 15 chars",
        cost_impact=250.0,
    )
    assert with_baseline["is_valid"] is False
    assert with_baseline["posture"] == "REJECTED_INSUFFICIENT_JUSTIFICATION"

    short_title = validate_ccb_change_request_justification(
        title="ab",
        justification="Justificacion administrativa larga suficiente",
        cost_impact=0.0,
    )
    assert short_title["is_valid"] is False
    assert short_title["posture"] == "REJECTED_INSUFFICIENT_JUSTIFICATION"

    # Justificación >= 10 sin impacto en baseline -> FAST_TRACK_ADMINISTRATIVE
    admin_ok = validate_ccb_change_request_justification(
        title="Renombrar plantilla",
        justification="Renombrado interno sin efecto en baseline",
        cost_impact=0.0,
        schedule_days_impact=0,
    )
    assert admin_ok["has_baseline_impact"] is False
    assert admin_ok["is_valid"] is True
    assert admin_ok["impact_tier"] == "ADMINISTRATIVE_NO_BASELINE_SHIFT"
    assert admin_ok["posture"] == "FAST_TRACK_ADMINISTRATIVE"


def test_validate_ccb_change_request_defaults_and_normalization():
    """Defaults 0/None -> esquina administrativa; espacios y floats se normalizan."""
    from backend.schemas.projects import validate_ccb_change_request_justification

    res = validate_ccb_change_request_justification(None, None, None, None)
    assert res["clean_title"] == ""
    assert res["clean_justification"] == ""
    assert res["cost_delta"] == 0.0
    assert res["schedule_delta_days"] == 0.0
    assert res["has_baseline_impact"] is False
    assert res["is_valid"] is False
    assert res["impact_tier"] == "ADMINISTRATIVE_NO_BASELINE_SHIFT"
    assert res["posture"] == "REJECTED_INSUFFICIENT_JUSTIFICATION"

    stripped = validate_ccb_change_request_justification(
        "  Ok titulo  ",
        "  ok  ",
        cost_impact=0.0,
        schedule_days_impact=0,
    )
    assert stripped["clean_title"] == "Ok titulo"
    assert stripped["clean_justification"] == "ok"  # 2 chars -> invalid
    assert stripped["is_valid"] is False


# ─── validate_milestone_deliverable_gate (PMBOK §6.2 / §5.5, pure helper) ───


def test_validate_milestone_deliverable_gate_verified():
    """Hito con título >= 5, criterio >= 15, fecha >= 8 y avance >= 100.0 -> 'MILESTONE_GATE_VERIFIED'."""
    from backend.schemas.projects import validate_milestone_deliverable_gate

    res = validate_milestone_deliverable_gate(
        title="  Cierre Fase 1  ",
        acceptance_criteria="  Acta firmada por sponsor y pruebas QA al 100%  ",
        due_date="2026-10-30",
        progress_pct=105.0,
    )
    assert res == {
        "clean_title": "Cierre Fase 1",
        "clean_criteria": "Acta firmada por sponsor y pruebas QA al 100%",
        "clean_due_date": "2026-10-30",
        "safe_progress": 100.0,
        "has_valid_title": True,
        "has_acceptance_criteria": True,
        "has_due_date": True,
        "is_gate_ready": True,
        "posture": "MILESTONE_GATE_VERIFIED",
    }


def test_validate_milestone_deliverable_gate_in_execution():
    """Hito gate-ready pero con safe_progress < 100.0 -> 'MILESTONE_IN_EXECUTION'."""
    from backend.schemas.projects import validate_milestone_deliverable_gate

    res = validate_milestone_deliverable_gate(
        title="Despliegue Producción",
        acceptance_criteria="Verificación de humo HTTP 200 en todos los módulos",
        due_date="2026-11-15",
        progress_pct=65.5,
    )
    assert res["is_gate_ready"] is True
    assert res["safe_progress"] == 65.5
    assert res["posture"] == "MILESTONE_IN_EXECUTION"


def test_validate_milestone_deliverable_gate_missing_acceptance_criteria():
    """Título y fecha válidos pero criterio < 15 caracteres -> 'MISSING_ACCEPTANCE_CRITERIA'."""
    from backend.schemas.projects import validate_milestone_deliverable_gate

    res = validate_milestone_deliverable_gate(
        title="Hito Intermedio",
        acceptance_criteria="Muy corto",
        due_date="2026-11-01",
        progress_pct=100.0,
    )
    assert res["has_valid_title"] is True
    assert res["has_due_date"] is True
    assert res["has_acceptance_criteria"] is False
    assert res["is_gate_ready"] is False
    assert res["posture"] == "MISSING_ACCEPTANCE_CRITERIA"


def test_validate_milestone_deliverable_gate_invalid_spec():
    """Sin título válido (< 5) o sin fecha válida (< 8) -> 'INVALID_MILESTONE_SPEC'."""
    from backend.schemas.projects import validate_milestone_deliverable_gate

    no_title = validate_milestone_deliverable_gate(
        title="abc",
        acceptance_criteria="Criterio suficientemente detallado para validación",
        due_date="2026-12-01",
        progress_pct=-10.0,
    )
    assert no_title["has_valid_title"] is False
    assert no_title["safe_progress"] == 0.0
    assert no_title["is_gate_ready"] is False
    assert no_title["posture"] == "INVALID_MILESTONE_SPEC"

    no_date = validate_milestone_deliverable_gate(
        title="Hito Sin Fecha",
        acceptance_criteria="Criterio suficientemente detallado para validación",
        due_date=None,
    )
    assert no_date["has_due_date"] is False
    assert no_date["is_gate_ready"] is False
    assert no_date["posture"] == "INVALID_MILESTONE_SPEC"


def test_validate_wbs_code_hierarchy_root_and_work_package():
    """WBS nivel 1 -> 'ROOT_CONTROL_ACCOUNT' y subnivel alineado -> 'VALID_WORK_PACKAGE_WBS'."""
    from backend.schemas.projects import validate_wbs_code_hierarchy

    root_res = validate_wbs_code_hierarchy(" 1 ", parent_wbs_code=None, max_depth=5)
    assert root_res == {
        "clean_code": "1",
        "clean_parent": "",
        "safe_max_depth": 5,
        "is_valid_format": True,
        "segments": ["1"],
        "depth": 1,
        "parent_aligned": True,
        "exceeds_max_depth": False,
        "is_valid": True,
        "posture": "ROOT_CONTROL_ACCOUNT",
    }

    wp_res = validate_wbs_code_hierarchy("1.2.3", parent_wbs_code="1.2", max_depth=5)
    assert wp_res["is_valid"] is True
    assert wp_res["depth"] == 3
    assert wp_res["parent_aligned"] is True
    assert wp_res["posture"] == "VALID_WORK_PACKAGE_WBS"


def test_validate_wbs_code_hierarchy_orphan_parent_mismatch():
    """WBS bien formado pero cuyo prefijo no coincide con parent_wbs_code -> 'ORPHAN_PARENT_MISMATCH'."""
    from backend.schemas.projects import validate_wbs_code_hierarchy

    res = validate_wbs_code_hierarchy("1.3.2", parent_wbs_code="1.2", max_depth=5)
    assert res["is_valid_format"] is True
    assert res["parent_aligned"] is False
    assert res["is_valid"] is False
    assert res["posture"] == "ORPHAN_PARENT_MISMATCH"


def test_validate_wbs_code_hierarchy_excessive_decomposition():
    """WBS bien formado y alineado pero con depth > safe_max_depth -> 'EXCESSIVE_WBS_DECOMPOSITION'."""
    from backend.schemas.projects import validate_wbs_code_hierarchy

    res = validate_wbs_code_hierarchy(
        "1.2.1.4.2", parent_wbs_code="1.2.1.4", max_depth=4
    )
    assert res["is_valid_format"] is True
    assert res["parent_aligned"] is True
    assert res["depth"] == 5
    assert res["safe_max_depth"] == 4
    assert res["exceeds_max_depth"] is True
    assert res["is_valid"] is False
    assert res["posture"] == "EXCESSIVE_WBS_DECOMPOSITION"


def test_validate_wbs_code_hierarchy_malformed_code():
    """Código vacío, con ceros iniciales o formato inválido -> 'MALFORMED_WBS_CODE'."""
    from backend.schemas.projects import validate_wbs_code_hierarchy

    for bad_code in ["", "0.1", "1.02.3", "1..2", "WBS-1.1", None]:
        res = validate_wbs_code_hierarchy(bad_code, parent_wbs_code="1")
        assert res["is_valid_format"] is False
        assert res["segments"] == []
        assert res["depth"] == 0
        assert res["is_valid"] is False
        assert res["posture"] == "MALFORMED_WBS_CODE"


def test_validate_resource_allocation_utilization_optimal_load():
    """Utilización entre 70% y safe_max_pct -> 'OPTIMAL_RESOURCE_LOAD'."""
    from backend.schemas.projects import validate_resource_allocation_utilization

    res = validate_resource_allocation_utilization(
        assigned_hours=34.0, capacity_hours=40.0, max_utilization_pct=100.0
    )
    assert res == {
        "safe_assigned": 34.0,
        "safe_capacity": 40.0,
        "safe_max_pct": 100.0,
        "utilization_pct": 85.0,
        "overallocated_hours": 0.0,
        "is_overallocated": False,
        "posture": "OPTIMAL_RESOURCE_LOAD",
    }


def test_validate_resource_allocation_utilization_overallocated():
    """Utilización supera safe_max_pct -> 'RESOURCE_OVERALLOCATED'."""
    from backend.schemas.projects import validate_resource_allocation_utilization

    res = validate_resource_allocation_utilization(
        assigned_hours=48.0, capacity_hours=40.0, max_utilization_pct=100.0
    )
    assert res["utilization_pct"] == 120.0
    assert res["overallocated_hours"] == 8.0
    assert res["is_overallocated"] is True
    assert res["posture"] == "RESOURCE_OVERALLOCATED"


def test_validate_resource_allocation_utilization_underutilized():
    """Capacidad > 0 pero utilización < 70% y no sobreasignado -> 'UNDERUTILIZED_CAPACITY'."""
    from backend.schemas.projects import validate_resource_allocation_utilization

    res = validate_resource_allocation_utilization(
        assigned_hours=16.0, capacity_hours=40.0, max_utilization_pct=100.0
    )
    assert res["utilization_pct"] == 40.0
    assert res["overallocated_hours"] == 0.0
    assert res["is_overallocated"] is False
    assert res["posture"] == "UNDERUTILIZED_CAPACITY"


def test_validate_resource_allocation_utilization_zero_capacity():
    """Capacidad 0 o negativa -> 'ZERO_CAPACITY_UNAVAILABLE'."""
    from backend.schemas.projects import validate_resource_allocation_utilization

    with_hours = validate_resource_allocation_utilization(
        assigned_hours=12.0, capacity_hours=0.0, max_utilization_pct=100.0
    )
    assert with_hours["safe_capacity"] == 0.0
    assert with_hours["utilization_pct"] == 100.0
    assert with_hours["overallocated_hours"] == 12.0
    assert with_hours["is_overallocated"] is True
    assert with_hours["posture"] == "ZERO_CAPACITY_UNAVAILABLE"

    no_hours = validate_resource_allocation_utilization(
        assigned_hours=0.0, capacity_hours=-5.0, max_utilization_pct=5.0
    )
    assert no_hours["safe_capacity"] == 0.0
    assert no_hours["safe_max_pct"] == 10.0
    assert no_hours["utilization_pct"] == 0.0
    assert no_hours["is_overallocated"] is False
    assert no_hours["posture"] == "ZERO_CAPACITY_UNAVAILABLE"


# ─── validate_schedule_dependency_lead_lag (pure helper) ──────────


def test_validate_schedule_dependency_lead_lag_sound_network():
    """FS/SS con lead negativo dentro de max_lag -> SOUND_SCHEDULE_NETWORK e is_valid True."""
    from backend.schemas.projects import validate_schedule_dependency_lead_lag

    res = validate_schedule_dependency_lead_lag(
        [
            {"predecessor_id": "T1", "successor_id": "T2", "type": "fs", "lag_days": 3},
            {"predecessor_id": "T2", "successor_id": "T3", "relationship": "SS", "lag_days": -2},
            {"predecessor_id": "T3", "successor_id": "T4"},  # default FS
            {"predecessor_id": "T4", "successor_id": "T5", "type": "SF"},
        ],
        max_lag_days=30,
    )

    assert res["is_valid"] is True
    assert res["total_dependencies"] == 4
    assert res["self_dependency_ids"] == []
    assert res["invalid_relationship_types"] == []
    assert res["excessive_lag_links"] == []
    assert res["sf_relationship_count"] == 1
    assert res["network_posture"] == "SOUND_SCHEDULE_NETWORK"


def test_validate_schedule_dependency_lead_lag_self_links_take_precedence():
    """Self-link + gramática inválida + lag excesivo -> CIRCULAR_SELF_LINK_DETECTED (precedencia 1)."""
    from backend.schemas.projects import validate_schedule_dependency_lead_lag

    res = validate_schedule_dependency_lead_lag(
        [
            {"predecessor_id": "T1", "successor_id": "T1"},
            {"predecessor_id": "T2", "successor_id": "T3", "type": "ZZ"},
            {"predecessor_id": "T3", "successor_id": "T4", "lag_days": 90},
        ]
    )

    assert res["self_dependency_ids"] == ["T1"]
    assert res["invalid_relationship_types"] == ["zz"]
    assert res["excessive_lag_links"] == ["T3->T4"]
    assert res["is_valid"] is False
    assert res["network_posture"] == "CIRCULAR_SELF_LINK_DETECTED"


def test_validate_schedule_dependency_lead_lag_invalid_and_excessive_lag():
    """Gramática inválida sin self-links -> INVALID_DEPENDENCY_GRAMMAR; solo lag -> EXCESSIVE_LAG_DISTORTION."""
    from backend.schemas.projects import validate_schedule_dependency_lead_lag

    bad_grammar = validate_schedule_dependency_lead_lag(
        [
            {"predecessor_id": "T1", "successor_id": "T2", "type": "xy"},
            {"predecessor_id": "T2", "successor_id": "T3", "lag_days": 99},
            {"predecessor_id": "T3", "successor_id": "T4", "relationship": "ff"},
        ]
    )
    assert bad_grammar["invalid_relationship_types"] == ["xy"]
    assert bad_grammar["excessive_lag_links"] == ["T2->T3"]
    assert bad_grammar["network_posture"] == "INVALID_DEPENDENCY_GRAMMAR"

    only_lag = validate_schedule_dependency_lead_lag(
        [
            {"predecessor_id": "A", "successor_id": "B", "lag_days": 31},
            {"predecessor_id": "C", "successor_id": "D", "lag_days": -45},
        ],
        max_lag_days=30,
    )
    assert only_lag["excessive_lag_links"] == ["A->B", "C->D"]
    assert only_lag["is_valid"] is False
    assert only_lag["network_posture"] == "EXCESSIVE_LAG_DISTORTION"


def test_validate_procurement_contract_sound_structure():
    """Contratos FFP/CPIF sanos con share balanceado -> SOUND_PROCUREMENT_STRUCTURE."""
    from backend.schemas.projects import validate_procurement_contract_fee_structure

    res = validate_procurement_contract_fee_structure(
        [
            {"contract_id": "C-1", "contract_type": "FFP", "base_amount": 50000.0, "fixed_fee": 5000.0},
            {
                "contract_id": "C-2",
                "contract_type": "CPIF",
                "target_cost": 80000.0,
                "fee_amount": 12000.0,
                "buyer_share_ratio": 0.60,
                "seller_share_ratio": 0.40,
            },
        ],
        max_award_fee_pct=20.0,
    )

    assert res["total_contracts"] == 2
    assert res["invalid_type_ids"] == []
    assert res["unbounded_tm_ids"] == []
    assert res["excessive_fee_ids"] == []
    assert res["imbalanced_share_ratio_ids"] == []
    assert res["is_valid"] is True
    assert res["contract_governance_posture"] == "SOUND_PROCUREMENT_STRUCTURE"


def test_validate_procurement_contract_invalid_types_take_precedence():
    """Tipos fuera de gramática -> INVALID_CONTRACT_TYPE precede a TM sin techo y fees."""
    from backend.schemas.projects import validate_procurement_contract_fee_structure

    res = validate_procurement_contract_fee_structure(
        [
            {"contract_id": "C-1", "contract_type": "XYZ"},
            {"contract_id": "C-2", "contract_type": "TM"},  # sin techo
            {
                "contract_id": "C-3",
                "contract_type": "CPFF",
                "target_cost": 1000.0,
                "fee_amount": 500.0,  # 50% > 20%
            },
        ]
    )

    assert res["invalid_type_ids"] == ["C-1"]
    assert res["unbounded_tm_ids"] == ["C-2"]
    assert res["excessive_fee_ids"] == ["C-3"]
    assert res["is_valid"] is False
    assert res["contract_governance_posture"] == "INVALID_CONTRACT_TYPE"


def test_validate_procurement_contract_unbounded_tm_and_excessive_fee():
    """Sin tipos inválidos: TM sin techo -> UNBOUNDED_TM_EXPOSURE; solo fee excesivo -> IMBALANCED_OR_EXCESSIVE."""
    from backend.schemas.projects import validate_procurement_contract_fee_structure

    unbounded = validate_procurement_contract_fee_structure(
        [
            {"contract_id": "C-1", "contract_type": "TM"},
            {
                "contract_id": "C-2",
                "contract_type": "TM",
                "ceiling_price": 120000.0,
            },
        ]
    )
    assert unbounded["unbounded_tm_ids"] == ["C-1"]
    assert unbounded["contract_governance_posture"] == "UNBOUNDED_TM_EXPOSURE"

    excessive = validate_procurement_contract_fee_structure(
        [
            {
                "contract_id": "C-1",
                "contract_type": "CPFF",
                "target_cost": 10000.0,
                "fee_amount": 2501.0,  # 25.01% > 20%
            },
        ],
        max_award_fee_pct=20.0,
    )
    assert excessive["excessive_fee_ids"] == ["C-1"]
    assert excessive["contract_governance_posture"] == "IMBALANCED_INCENTIVE_OR_EXCESSIVE_FEE"


def test_validate_procurement_contract_imbalanced_share_and_empty():
    """FPIF/CPIF con share no-somatorio -> IMBALANCED; sin contratos/no dicts -> NO_CONTRACTS_DEFINED."""
    from backend.schemas.projects import validate_procurement_contract_fee_structure

    imbalanced = validate_procurement_contract_fee_structure(
        [
            {
                "contract_id": "C-1",
                "contract_type": "FPIF",
                "target_cost": 90000.0,
                "fee_amount": 9000.0,
                "buyer_share_ratio": 0.65,
                "seller_share_ratio": 0.20,  # 0.85 != 1.0
            },
            {
                "contract_id": "C-2",
                "contract_type": "CPIF",
                "target_cost": 40000.0,
                "fee_amount": 8000.0,  # 20% == límite, no excesivo
                "buyer_share_ratio": 0.80,
                "seller_share_ratio": 0.20,  # balanceado
            },
        ]
    )
    assert imbalanced["imbalanced_share_ratio_ids"] == ["C-1"]
    assert imbalanced["excessive_fee_ids"] == []
    assert imbalanced["contract_governance_posture"] == "IMBALANCED_INCENTIVE_OR_EXCESSIVE_FEE"

    for payload in (None, [], ["no dict", 3]):
        res = validate_procurement_contract_fee_structure(payload)  # type: ignore[arg-type]
        assert res == {
            "total_contracts": 0,
            "invalid_type_ids": [],
            "unbounded_tm_ids": [],
            "excessive_fee_ids": [],
            "imbalanced_share_ratio_ids": [],
            "is_valid": True,
            "contract_governance_posture": "NO_CONTRACTS_DEFINED",
        }


def test_validate_schedule_dependency_lead_lag_empty_and_non_dicts():
    """None, lista vacía o items no-dict -> NO_DEPENDENCIES_DEFINED con is_valid True."""
    from backend.schemas.projects import validate_schedule_dependency_lead_lag

    for deps in (None, [], ["no dict", 7]):
        res = validate_schedule_dependency_lead_lag(deps)  # type: ignore[arg-type]
        assert res == {
            "is_valid": True,
            "total_dependencies": 0,
            "self_dependency_ids": [],
            "invalid_relationship_types": [],
            "excessive_lag_links": [],
            "sf_relationship_count": 0,
            "network_posture": "NO_DEPENDENCIES_DEFINED",
        }


# ─── validate_risk_trigger_and_fallback_plan (pure helper) ───────


def test_validate_risk_trigger_and_fallback_plan_governed_matrix():
    """Riesgos de alta exposición con trigger >= 6 chars, fallback >= 8 chars y residual < severity -> GOVERNED_RISK_RESPONSE_MATRIX."""
    from backend.schemas.projects import validate_risk_trigger_and_fallback_plan

    risks = [
        {
            "id": "RSK-01",
            "probability": 4,
            "impact": 4,
            "trigger_condition": "Latencia sostenida > 250ms por 15 min",
            "fallback_plan": "Conmutar tráfico al nodo secundario multi-región",
            "residual_severity": 6,
        },
        {
            "code": "RSK-02",
            "severity": 15,
            "early_warning_trigger": "Retraso aduanero > 5 días hábiles",
            "contingency_plan": "Activar proveedor local precalificado",
            "residual_severity": 5,
        },
        {
            "id": "RSK-03",
            "probability": 2,
            "impact": 2,  # severidad 4 < 12 (no requiere trigger/fallback de alta exposición)
        },
    ]

    res = validate_risk_trigger_and_fallback_plan(risks, high_severity_threshold=12)
    assert res == {
        "is_valid": True,
        "total_risks": 3,
        "high_exposure_count": 2,
        "missing_trigger_ids": [],
        "missing_fallback_ids": [],
        "unreduced_residual_ids": [],
        "risk_governance_posture": "GOVERNED_RISK_RESPONSE_MATRIX",
    }


def test_validate_risk_trigger_and_fallback_plan_missing_triggers():
    """Riesgo de alta exposición con trigger < 6 chars -> MISSING_EARLY_WARNING_TRIGGERS."""
    from backend.schemas.projects import validate_risk_trigger_and_fallback_plan

    risks = [
        {
            "id": "RSK-10",
            "probability": 5,
            "impact": 3,
            "trigger_condition": "TBD",
            "fallback_plan": "Desplegar cuadrilla de contingencia nocturna",
            "residual_severity": 6,
        },
        {
            "id": "RSK-11",
            "score": 16,
            "early_warning_trigger": "Alerta de capacidad > 85%",
            "contingency_plan": "Escalar instancias automáticamente",
            "residual_severity": 4,
        },
    ]

    res = validate_risk_trigger_and_fallback_plan(risks, high_severity_threshold=12)
    assert res["is_valid"] is False
    assert res["total_risks"] == 2
    assert res["high_exposure_count"] == 2
    assert res["missing_trigger_ids"] == ["RSK-10"]
    assert res["missing_fallback_ids"] == []
    assert res["unreduced_residual_ids"] == []
    assert res["risk_governance_posture"] == "MISSING_EARLY_WARNING_TRIGGERS"


def test_validate_risk_trigger_and_fallback_plan_missing_fallback_and_unreduced_residual():
    """Sin triggers faltantes pero fallback < 8 chars -> MISSING_FALLBACK_CONTINGENCY; residual >= severity -> INEFFECTIVE_RESIDUAL_MITIGATION."""
    from backend.schemas.projects import validate_risk_trigger_and_fallback_plan

    no_fallback = validate_risk_trigger_and_fallback_plan(
        [
            {
                "id": "RSK-20",
                "probability": 4,
                "impact": 3,
                "trigger_condition": "Variación CPI < 0.88 en dos cortes",
                "fallback_plan": "Corto",
                "residual_severity": 6,
            }
        ],
        high_severity_threshold=12,
    )
    assert no_fallback["is_valid"] is False
    assert no_fallback["missing_trigger_ids"] == []
    assert no_fallback["missing_fallback_ids"] == ["RSK-20"]
    assert no_fallback["risk_governance_posture"] == "MISSING_FALLBACK_CONTINGENCY"

    unreduced = validate_risk_trigger_and_fallback_plan(
        [
            {
                "code": "RSK-21",
                "probability": 4,
                "impact": 4,
                "trigger_condition": "Falla en enlace principal fibra",
                "fallback_plan": "Activar enlace microondas de respaldo",
                "residual_severity": 16,
            }
        ],
        high_severity_threshold=12,
    )
    assert unreduced["is_valid"] is False
    assert unreduced["missing_trigger_ids"] == []
    assert unreduced["missing_fallback_ids"] == []
    assert unreduced["unreduced_residual_ids"] == ["RSK-21"]
    assert unreduced["risk_governance_posture"] == "INEFFECTIVE_RESIDUAL_MITIGATION"


def test_validate_risk_trigger_and_fallback_plan_no_risks():
    """None, lista vacía o entradas no-dict -> NO_RISKS_EVALUATED con is_valid True."""
    from backend.schemas.projects import validate_risk_trigger_and_fallback_plan

    for payload in (None, [], ["invalid", 42]):
        res = validate_risk_trigger_and_fallback_plan(payload)  # type: ignore[arg-type]
        assert res == {
            "is_valid": True,
            "total_risks": 0,
            "high_exposure_count": 0,
            "missing_trigger_ids": [],
            "missing_fallback_ids": [],
            "unreduced_residual_ids": [],
            "risk_governance_posture": "NO_RISKS_EVALUATED",
        }


def test_validate_resource_histogram_overallocation_balanced():
    """Asignaciones válidas dentro de la capacidad -> histograma balanceado."""
    from backend.schemas.projects import validate_resource_histogram_overallocation

    res = validate_resource_histogram_overallocation(
        [
            {
                "id": "ALLOC-1",
                "resource_id": "RES-1",
                "period": "2026-10-18",
                "allocated_hours": 6.0,
                "capacity_hours": 8.0,
            },
            {
                "id": "ALLOC-2",
                "resource_id": "RES-2",
                "date": "2026-10-18",
                "hours": 4.0,
                "max_hours": 8.0,
            },
        ]
    )
    assert res["is_valid"] is True
    assert res["total_records"] == 2
    assert res["unique_resources_count"] == 2
    assert res["invalid_allocation_ids"] == []
    assert res["overallocated_resource_periods"] == []
    assert res["peak_utilization_pct"] == 75.0
    assert res["allocation_posture"] == "BALANCED_RESOURCE_HISTOGRAM"


def test_validate_resource_histogram_overallocation_invalid_hours():
    """Horas <= 0.0 se marcan como inválidas con precedencia de posture."""
    from backend.schemas.projects import validate_resource_histogram_overallocation

    res = validate_resource_histogram_overallocation(
        [
            {
                "id": "ALLOC-OK",
                "resource_id": "RES-1",
                "period": "W43",
                "allocated_hours": 2.0,
                "capacity_hours": 4.0,
            },
            {
                "id": "ALLOC-ZERO",
                "resource_id": "RES-2",
                "period": "W43",
                "allocated_hours": 0.0,
            },
            {
                "id": "ALLOC-NEG",
                "resource_id": "RES-3",
                "week": "W43",
                "allocated_hours": -3.5,
            },
        ]
    )
    assert res["is_valid"] is False
    assert res["total_records"] == 3
    assert res["unique_resources_count"] == 3
    assert res["invalid_allocation_ids"] == ["ALLOC-ZERO", "ALLOC-NEG"]
    assert res["overallocated_resource_periods"] == []
    assert res["peak_utilization_pct"] == 50.0
    assert res["allocation_posture"] == "INVALID_ALLOCATION_HOURS"


def test_validate_resource_histogram_overallocation_resource_period_accumulation():
    """Varias tareas del mismo recurso en la misma fecha suman horas para la sobreasignación."""
    from backend.schemas.projects import validate_resource_histogram_overallocation

    res = validate_resource_histogram_overallocation(
        [
            {
                "resource_id": "RES-1",
                "period": "2026-10-18",
                "allocated_hours": 5.0,
                "capacity_hours": 8.0,
            },
            {
                "resource_id": "RES-1",
                "period": "2026-10-18",
                "allocated_hours": 4.0,
                "capacity_hours": 4.0,
            },
            {
                "resource_id": "RES-2",
                "period": "2026-10-18",
                "allocated_hours": 9.0,
            },
        ],
        max_daily_hours=8.0,
    )
    # La capacidad del bucket es el máximo de los caps (8.0); 9.0 > 8.0 + 1e-9 -> sobreasignado.
    assert res["is_valid"] is False
    assert res["total_records"] == 3
    assert res["unique_resources_count"] == 2
    assert res["invalid_allocation_ids"] == []
    assert res["overallocated_resource_periods"] == ["RES-1@2026-10-18", "RES-2@2026-10-18"]
    # RES-2 usa el fallback max(0.01, max_daily_hours) = 8.0 -> 112.5%.
    assert res["peak_utilization_pct"] == 112.5
    assert res["allocation_posture"] == "RESOURCE_HISTOGRAM_OVERALLOCATION"


def test_validate_resource_histogram_overallocation_empty_or_none():
    """None, lista vacía o sin entradas dict -> NO_ALLOCATIONS_DEFINED."""
    from backend.schemas.projects import validate_resource_histogram_overallocation

    for payload in (None, [], ["invalid", 42, None]):
        res = validate_resource_histogram_overallocation(payload)  # type: ignore[arg-type]
        assert res == {
            "total_records": 0,
            "unique_resources_count": 0,
            "peak_utilization_pct": 0.0,
            "invalid_allocation_ids": [],
            "overallocated_resource_periods": [],
            "is_valid": True,
            "allocation_posture": "NO_ALLOCATIONS_DEFINED",
        }


def test_validate_pert_three_point_estimates_sound_model():
    """Estimaciones PERT válidas con E=(O+4M+P)/6 y sigma combinada sqrt(sum(sigma^2)) -> SOUND_PERT_THREE_POINT_MODEL."""
    from backend.schemas.projects import validate_pert_three_point_estimates

    # Act 1: O=4, M=10, P=22 -> E=(4+40+22)/6=11.0, sigma=(22-4)/6=3.0, V=9.0
    # Act 2: O=6, M=12, P=30 -> E=(6+48+30)/6=14.0, sigma=(30-6)/6=4.0, V=16.0
    # Total E = 25.0, Combined sigma = sqrt(9+16) = 5.0
    res = validate_pert_three_point_estimates(
        [
            {"id": "ACT-1", "optimistic": 4.0, "most_likely": 10.0, "pessimistic": 22.0},
            {"activity_id": "ACT-2", "o": 6.0, "m": 12.0, "p": 30.0},
        ],
        max_coefficient_of_variation_pct=35.0,
    )
    assert res == {
        "total_items": 2,
        "total_expected_estimate": 25.0,
        "combined_standard_deviation": 5.0,
        "inverted_or_nonpositive_ids": [],
        "excessive_uncertainty_ids": [],
        "is_valid": True,
        "pert_posture": "SOUND_PERT_THREE_POINT_MODEL",
    }


def test_validate_pert_three_point_estimates_inverted_or_nonpositive():
    """Cotas invertidas (O > M o M > P) o valores <= 0 -> INVERTED_OR_NONPOSITIVE_PERT_BOUNDS."""
    from backend.schemas.projects import validate_pert_three_point_estimates

    res = validate_pert_three_point_estimates(
        [
            {"id": "ACT-INV-1", "optimistic": 15.0, "most_likely": 10.0, "pessimistic": 20.0},
            {"task_id": "ACT-INV-2", "optimistic": 5.0, "most_likely": 12.0, "pessimistic": 8.0},
            {"id": "ACT-ZERO", "optimistic": 0.0, "most_likely": 5.0, "pessimistic": 10.0},
            {"id": "ACT-OK", "optimistic": 6.0, "most_likely": 12.0, "pessimistic": 18.0},
        ]
    )
    assert res["total_items"] == 4
    assert res["total_expected_estimate"] == 12.0
    assert res["combined_standard_deviation"] == 2.0
    assert res["inverted_or_nonpositive_ids"] == ["ACT-INV-1", "ACT-INV-2", "ACT-ZERO"]
    assert res["excessive_uncertainty_ids"] == []
    assert res["is_valid"] is False
    assert res["pert_posture"] == "INVERTED_OR_NONPOSITIVE_PERT_BOUNDS"


def test_validate_pert_three_point_estimates_excessive_uncertainty():
    """Dispersión extrema (sigma/E * 100 > max_coefficient_of_variation_pct) -> EXCESSIVE_ESTIMATE_UNCERTAINTY_SPREAD."""
    from backend.schemas.projects import validate_pert_three_point_estimates

    # O=2, M=4, P=38 -> E=(2+16+38)/6=9.3333, sigma=(38-2)/6=6.0 -> CV = 64.29% > 35%
    res = validate_pert_three_point_estimates(
        [
            {"id": "ACT-SPREAD", "optimistic": 2.0, "most_likely": 4.0, "pessimistic": 38.0},
        ],
        max_coefficient_of_variation_pct=35.0,
    )
    assert res["total_items"] == 1
    assert res["total_expected_estimate"] == 9.33
    assert res["combined_standard_deviation"] == 6.0
    assert res["inverted_or_nonpositive_ids"] == []
    assert res["excessive_uncertainty_ids"] == ["ACT-SPREAD"]
    assert res["is_valid"] is False
    assert res["pert_posture"] == "EXCESSIVE_ESTIMATE_UNCERTAINTY_SPREAD"


def test_validate_pert_three_point_estimates_empty_or_none():
    """Lista vacía, None o entradas no-dict -> NO_PERT_ESTIMATES_PROVIDED."""
    from backend.schemas.projects import validate_pert_three_point_estimates

    for payload in (None, [], ["invalid", 99]):
        res = validate_pert_three_point_estimates(payload)  # type: ignore[arg-type]
        assert res == {
            "total_items": 0,
            "total_expected_estimate": 0.0,
            "combined_standard_deviation": 0.0,
            "inverted_or_nonpositive_ids": [],
            "excessive_uncertainty_ids": [],
            "is_valid": True,
            "pert_posture": "NO_PERT_ESTIMATES_PROVIDED",
        }


def test_validate_requirements_traceability_matrix_bidirectional_compliant():
    """Matriz RTM 100% trazada en ambas direcciones e ignorando requisitos cancelados/diferidos."""
    from backend.schemas.projects import validate_requirements_traceability_matrix

    res = validate_requirements_traceability_matrix(
        [
            {
                "id": "REQ-01",
                "status": "approved",
                "business_objective": "OBJ-01 Reducir tiempo de acreditación",
                "wbs_deliverable": "1.2.1 Módulo QR",
                "verification_test_id": "TC-101",
            },
            {
                "req_id": "REQ-02",
                "status": "active",
                "objective_id": "OBJ-02",
                "wbs_code": "1.3.4",
                "test_case_id": "TC-102",
            },
            {
                "code": "REQ-03",
                "status": "cancelled",
                "business_objective": "",
                "wbs_deliverable": "",
                "verification_test_id": "",
            },
        ]
    )
    assert res == {
        "total_requirements": 3,
        "active_requirements_count": 2,
        "fully_traced_count": 2,
        "traceability_coverage_pct": 100.0,
        "orphan_business_objective_ids": [],
        "unmapped_wbs_deliverable_ids": [],
        "unverified_test_case_ids": [],
        "is_valid": True,
        "rtm_posture": "BIDIRECTIONAL_RTM_COMPLIANT",
    }


def test_validate_requirements_traceability_matrix_orphan_business_objective():
    """Requisito activo sin business_objective -> ORPHAN_REQUIREMENTS_WITHOUT_BUSINESS_NEED."""
    from backend.schemas.projects import validate_requirements_traceability_matrix

    res = validate_requirements_traceability_matrix(
        [
            {
                "id": "REQ-GOLD-1",
                "status": "active",
                "business_objective": "   ",
                "wbs_deliverable": "2.1.1",
                "verification_test_id": "TC-201",
            },
            {
                "id": "REQ-OK",
                "status": "active",
                "strategic_goal": "GOAL-5",
                "deliverable_id": "DEL-9",
                "acceptance_test": "UAT-04",
            },
        ]
    )
    assert res["total_requirements"] == 2
    assert res["active_requirements_count"] == 2
    assert res["fully_traced_count"] == 1
    assert res["traceability_coverage_pct"] == 50.0
    assert res["orphan_business_objective_ids"] == ["REQ-GOLD-1"]
    assert res["unmapped_wbs_deliverable_ids"] == []
    assert res["unverified_test_case_ids"] == []
    assert res["is_valid"] is False
    assert res["rtm_posture"] == "ORPHAN_REQUIREMENTS_WITHOUT_BUSINESS_NEED"


def test_validate_requirements_traceability_matrix_unmapped_wbs_and_unverified_test():
    """Requisito activo sin WBS -> UNMAPPED_WBS_DELIVERABLE_GAPS y sin test -> MISSING_VERIFICATION_TEST_COVERAGE."""
    from backend.schemas.projects import validate_requirements_traceability_matrix

    unmapped_res = validate_requirements_traceability_matrix(
        [
            {
                "id": "REQ-NOWBS",
                "status": "active",
                "business_objective": "OBJ-10",
                "wbs_deliverable": "",
                "verification_test_id": "TC-300",
            }
        ]
    )
    assert unmapped_res["unmapped_wbs_deliverable_ids"] == ["REQ-NOWBS"]
    assert unmapped_res["is_valid"] is False
    assert unmapped_res["rtm_posture"] == "UNMAPPED_WBS_DELIVERABLE_GAPS"

    unverified_res = validate_requirements_traceability_matrix(
        [
            {
                "id": "REQ-NOTEST",
                "status": "active",
                "business_objective": "OBJ-11",
                "wbs_deliverable": "3.1.2",
                "verification_test_id": None,
            }
        ]
    )
    assert unverified_res["unverified_test_case_ids"] == ["REQ-NOTEST"]
    assert unverified_res["is_valid"] is False
    assert unverified_res["rtm_posture"] == "MISSING_VERIFICATION_TEST_COVERAGE"


def test_validate_requirements_traceability_matrix_empty_or_none():
    """Lista vacía o None -> NO_REQUIREMENTS_DEFINED."""
    from backend.schemas.projects import validate_requirements_traceability_matrix

    for payload in (None, [], ["invalid", 42]):
        res = validate_requirements_traceability_matrix(payload)  # type: ignore[arg-type]
        assert res == {
            "total_requirements": 0,
            "active_requirements_count": 0,
            "fully_traced_count": 0,
            "traceability_coverage_pct": 0.0,
            "orphan_business_objective_ids": [],
            "unmapped_wbs_deliverable_ids": [],
            "unverified_test_case_ids": [],
            "is_valid": True,
            "rtm_posture": "NO_REQUIREMENTS_DEFINED",
        }







def test_validate_cpm_float_and_critical_path_sound_network():
    """Actividades crïticas (TF=0) y cuasi-críticas (TF dentro del umbral) -> SOUND."""
    from backend.schemas.projects import validate_cpm_float_and_critical_path

    res = validate_cpm_float_and_critical_path(
        [
            {
                "id": "ACT-1",
                "total_float_days": 0.0,
                "free_float_days": 0.0,
                "is_critical": True,
            },
            {
                "wbs_code": "1.4",
                "total_float": 1.5,
                "free_float": 1.0,
            },
            {
                "activity_id": "ACT-3",
                "total_float_days": 5.0,
                "free_float_days": 2.0,
            },
        ]
    )
    assert res["is_cpm_schedule_valid"] is True
    assert res["total_activities"] == 3
    assert res["critical_activities_count"] == 1
    assert res["near_critical_count"] == 1
    assert res["negative_float_activity_ids"] == []
    assert res["float_inversion_activity_ids"] == []
    assert res["misclassified_critical_activity_ids"] == []
    assert res["cpm_schedule_posture"] == "SOUND_CPM_NETWORK_SCHEDULE"


def test_validate_cpm_float_and_critical_path_float_inversion():
    """Free Float mayor que Total Float -> CPM_FLOAT_INVERSION_ERROR."""
    from backend.schemas.projects import validate_cpm_float_and_critical_path

    res = validate_cpm_float_and_critical_path(
        [
            {
                "id": "ACT-OK",
                "total_float_days": 3.0,
                "free_float_days": 1.0,
            },
            {
                "id": "ACT-BAD",
                "total_float_days": 2.0,
                "free_float_days": 3.5,
            },
        ]
    )
    assert res["is_cpm_schedule_valid"] is False
    assert res["total_activities"] == 2
    assert res["critical_activities_count"] == 0
    assert res["near_critical_count"] == 1
    assert res["negative_float_activity_ids"] == []
    assert res["float_inversion_activity_ids"] == ["ACT-BAD"]
    assert res["misclassified_critical_activity_ids"] == []
    assert res["cpm_schedule_posture"] == "CPM_FLOAT_INVERSION_ERROR"


def test_validate_cpm_float_and_critical_path_negative_float_and_drift():
    """TF negativo (precedencia posture) y drift del flag is_critical identificados."""
    from backend.schemas.projects import validate_cpm_float_and_critical_path

    res = validate_cpm_float_and_critical_path(
        [
            {
                "id": "ACT-NEG",
                "total_float_days": -3.0,
                "free_float_days": -5.0,
                "is_critical": True,
            },
            {
                "id": "ACT-DRIFT",
                "total_float_days": 0.0,
                "free_float_days": 0.0,
            },
            {
                "id": "ACT-DRIFT2",
                "total_float_days": 7.0,
                "critical_path": True,
            },
        ]
    )
    assert res["is_cpm_schedule_valid"] is False
    assert res["total_activities"] == 3
    assert res["critical_activities_count"] == 2
    assert res["near_critical_count"] == 0
    assert res["negative_float_activity_ids"] == ["ACT-NEG"]
    assert res["float_inversion_activity_ids"] == []
    assert res["misclassified_critical_activity_ids"] == [
        "ACT-DRIFT",
        "ACT-DRIFT2",
    ]
    # Precedencia: float inversion > negative > drift (FF=-5 <= TF=-3 no invierte).
    assert res["cpm_schedule_posture"] == "NEGATIVE_TOTAL_FLOAT_ALERT"


def test_validate_cpm_float_and_critical_path_empty_or_none():
    """None, lista vacía o entradas no-dict -> NO_ACTIVITIES_EVALUATED."""
    from backend.schemas.projects import validate_cpm_float_and_critical_path

    for payload in (None, [], ["invalid", 42, None]):
        res = validate_cpm_float_and_critical_path(payload)  # type: ignore[arg-type]
        assert res == {
            "total_activities": 0,
            "critical_activities_count": 0,
            "near_critical_count": 0,
            "negative_float_activity_ids": [],
            "float_inversion_activity_ids": [],
            "misclassified_critical_activity_ids": [],
            "is_cpm_schedule_valid": True,
            "cpm_schedule_posture": "NO_ACTIVITIES_EVALUATED",
        }


def test_validate_emv_decision_tree_exposure_buffered():
    """Amenazas y oportunidades con reserva suficiente -> BUFFERED_EMV_EXPOSURE."""
    from backend.schemas.projects import validate_emv_decision_tree_exposure

    # RSK-1 amenaza: 0.4 * 20000 = +8000; RSK-2 oportunidad: 0.5 * 4000 = -2000 -> net_threat_emv = 6000.0
    res = validate_emv_decision_tree_exposure(
        [
            {
                "id": "RSK-1",
                "probability": 0.4,
                "impact_cost": 20000.0,
                "type": "threat",
                "reported_emv": 8000.0,
            },
            {
                "risk_id": "RSK-2",
                "prob": 0.5,
                "impact_amount": 4000.0,
                "risk_type": "opportunity",
                "emv": -2000.0,
            },
        ],
        contingency_reserve_available=7500.0,
    )
    assert res == {
        "total_scenarios": 2,
        "net_threat_emv": 6000.0,
        "reserve_shortfall": 0.0,
        "invalid_probability_risk_ids": [],
        "emv_mismatch_risk_ids": [],
        "is_emv_valid_and_buffered": True,
        "emv_posture": "BUFFERED_EMV_EXPOSURE",
    }


def test_validate_emv_decision_tree_exposure_invalid_probability():
    """Probabilidad fuera de [0.0, 1.0] -> INVALID_PROBABILITY_RANGE."""
    from backend.schemas.projects import validate_emv_decision_tree_exposure

    res = validate_emv_decision_tree_exposure(
        [
            {"id": "RSK-OVER", "probability": 1.5, "impact": 10000.0},
            {"id": "RSK-NEG", "probability": -0.2, "impact": 5000.0},
            {"id": "RSK-OK", "probability": 0.25, "impact": 4000.0},
        ],
        contingency_reserve_available=2000.0,
    )
    assert res["total_scenarios"] == 3
    assert res["net_threat_emv"] == 1000.0
    assert res["invalid_probability_risk_ids"] == ["RSK-OVER", "RSK-NEG"]
    assert res["is_emv_valid_and_buffered"] is False
    assert res["emv_posture"] == "INVALID_PROBABILITY_RANGE"


def test_validate_emv_decision_tree_exposure_mismatch_and_shortfall():
    """Discrepancia reported_emv -> EMV_CALCULATION_MISMATCH; déficit de reserva -> CONTINGENCY_RESERVE_EMV_SHORTFALL."""
    from backend.schemas.projects import validate_emv_decision_tree_exposure

    mismatch_res = validate_emv_decision_tree_exposure(
        [
            {
                "id": "RSK-MIS",
                "probability": 0.3,
                "impact_cost": 10000.0,
                "reported_emv": 4500.0,
            }
        ],
        contingency_reserve_available=5000.0,
    )
    assert mismatch_res["emv_mismatch_risk_ids"] == ["RSK-MIS"]
    assert mismatch_res["is_emv_valid_and_buffered"] is False
    assert mismatch_res["emv_posture"] == "EMV_CALCULATION_MISMATCH"

    shortfall_res = validate_emv_decision_tree_exposure(
        [
            {
                "id": "RSK-BIG",
                "probability": 0.5,
                "impact_cost": 30000.0,
            }
        ],
        contingency_reserve_available=10000.0,
    )
    assert shortfall_res["net_threat_emv"] == 15000.0
    assert shortfall_res["reserve_shortfall"] == 5000.0
    assert shortfall_res["is_emv_valid_and_buffered"] is False
    assert shortfall_res["emv_posture"] == "CONTINGENCY_RESERVE_EMV_SHORTFALL"


def test_validate_emv_decision_tree_exposure_empty_or_none():
    """Lista vacía o None -> NO_RISK_SCENARIOS."""
    from backend.schemas.projects import validate_emv_decision_tree_exposure

    for payload in (None, [], ["invalid", 42]):
        res = validate_emv_decision_tree_exposure(payload)  # type: ignore[arg-type]
        assert res == {
            "total_scenarios": 0,
            "net_threat_emv": 0.0,
            "reserve_shortfall": 0.0,
            "invalid_probability_risk_ids": [],
            "emv_mismatch_risk_ids": [],
            "is_emv_valid_and_buffered": True,
            "emv_posture": "NO_RISK_SCENARIOS",
        }


def test_validate_pdm_dependency_leads_and_lags_sound_network():
    """Red lógica PDM válida con FS/SS/FF y SF justificado -> SOUND_PDM_LOGICAL_NETWORK."""
    from backend.schemas.projects import validate_pdm_dependency_leads_and_lags

    res = validate_pdm_dependency_leads_and_lags(
        [
            {
                "id": "DEP-1",
                "predecessor_id": "ACT-A",
                "successor_id": "ACT-B",
                "type": "FS",
                "lag_days": 2.0,
                "predecessor_duration_days": 10.0,
            },
            {
                "id": "DEP-2",
                "from_id": "ACT-B",
                "to_id": "ACT-C",
                "dependency_type": "SS",
                "lag": -3.0,
                "predecessor_duration": 8.0,
            },
            {
                "id": "DEP-3",
                "predecessor_id": "ACT-C",
                "successor_id": "ACT-D",
                "link_type": "SF",
                "justification": "Transición de guardia operativa continua 24x7",
            },
        ]
    )
    assert res == {
        "total_dependencies": 3,
        "invalid_relationship_ids": [],
        "excessive_lead_dependency_ids": [],
        "unjustified_sf_dependency_ids": [],
        "is_pdm_network_valid": True,
        "pdm_posture": "SOUND_PDM_LOGICAL_NETWORK",
    }


def test_validate_pdm_dependency_leads_and_lags_invalid_relationship():
    """Auto-dependencia o tipo desconocido -> INVALID_PDM_RELATIONSHIP."""
    from backend.schemas.projects import validate_pdm_dependency_leads_and_lags

    res = validate_pdm_dependency_leads_and_lags(
        [
            {
                "id": "DEP-SELF",
                "predecessor_id": "ACT-1",
                "successor_id": "ACT-1",
                "type": "FS",
            },
            {
                "id": "DEP-BADTYPE",
                "predecessor_id": "ACT-1",
                "successor_id": "ACT-2",
                "type": "XX",
            },
        ]
    )
    assert res["total_dependencies"] == 2
    assert res["invalid_relationship_ids"] == ["DEP-SELF", "DEP-BADTYPE"]
    assert res["is_pdm_network_valid"] is False
    assert res["pdm_posture"] == "INVALID_PDM_RELATIONSHIP"


def test_validate_pdm_dependency_leads_and_lags_excessive_lead_and_unjustified_sf():
    """Lead negativo >= duración predecesora -> EXCESSIVE_NEGATIVE_LAG_LEAD; SF sin justificación -> UNJUSTIFIED_SF_DEPENDENCY."""
    from backend.schemas.projects import validate_pdm_dependency_leads_and_lags

    res_lead = validate_pdm_dependency_leads_and_lags(
        [
            {
                "id": "DEP-LEAD",
                "predecessor_id": "ACT-1",
                "successor_id": "ACT-2",
                "type": "FS",
                "lag_days": -10.0,
                "predecessor_duration_days": 8.0,
            }
        ]
    )
    assert res_lead["excessive_lead_dependency_ids"] == ["DEP-LEAD"]
    assert res_lead["is_pdm_network_valid"] is False
    assert res_lead["pdm_posture"] == "EXCESSIVE_NEGATIVE_LAG_LEAD"

    res_sf = validate_pdm_dependency_leads_and_lags(
        [
            {
                "id": "DEP-SF",
                "predecessor_id": "ACT-2",
                "successor_id": "ACT-3",
                "type": "SF",
                "justification": "",
            }
        ]
    )
    assert res_sf["unjustified_sf_dependency_ids"] == ["DEP-SF"]
    assert res_sf["is_pdm_network_valid"] is False
    assert res_sf["pdm_posture"] == "UNJUSTIFIED_SF_DEPENDENCY"


def test_validate_pdm_dependency_leads_and_lags_empty_or_none():
    """Lista vacía o None -> NO_DEPENDENCIES_EVALUATED e is_pdm_network_valid=True."""
    from backend.schemas.projects import validate_pdm_dependency_leads_and_lags

    for payload in (None, [], ["invalid", 99]):
        res = validate_pdm_dependency_leads_and_lags(payload)  # type: ignore[arg-type]
        assert res == {
            "total_dependencies": 0,
            "invalid_relationship_ids": [],
            "excessive_lead_dependency_ids": [],
            "unjustified_sf_dependency_ids": [],
            "is_pdm_network_valid": True,
            "pdm_posture": "NO_DEPENDENCIES_EVALUATED",
        }



def test_validate_schedule_compression_options_optimal_critical_path():
    """> Crashing y fast-tracking moderados en ruta crítico -> OPTIMAL compression."""
    from backend.schemas.projects import validate_schedule_compression_options

    res = validate_schedule_compression_options(
        [
            {
                "id": "ACT-1",
                "is_critical": True,
                "normal_duration_days": 10.0,
                "crash_duration_days": 8.0,
                "normal_cost": 5000.0,
                "crash_cost": 7000.0,
                "technique": "crashing",
            },
            {
                "id": "ACT-2",
                "on_critical_path": True,
                "normal_duration": 8.0,
                "crash_duration_days": 6.0,
                "technique": "fast_tracking",
                "rework_risk_pct": 15.0,
            },
        ]
    )
    assert res["is_compression_plan_sound"] is True
    assert res["total_options"] == 2
    assert res["non_critical_compression_ids"] == []
    assert res["invalid_crash_slope_ids"] == []
    assert res["high_risk_fast_track_ids"] == []
    assert res["total_days_saved"] == 4.0
    assert res["compression_posture"] == "OPTIMAL_CRITICAL_PATH_COMPRESSION"


def test_validate_schedule_compression_options_invalid_slope():
    """> Crash > normal o costo crashing menor que normal -> INVALID slope."""
    from backend.schemas.projects import validate_schedule_compression_options

    res = validate_schedule_compression_options(
        [
            {
                "id": "ACT-EXPANDED",
                "is_critical": True,
                "normal_duration_days": 5.0,
                "crash_duration_days": 7.0,
            },
            {
                "id": "ACT-CHEAP",
                "is_critical": True,
                "normal_duration_days": 6.0,
                "crash_duration_days": 4.0,
                "normal_cost": 4000.0,
                "crash_cost": 2500.0,
                "technique": "crashing",
            },
        ]
    )
    assert res["is_compression_plan_sound"] is False
    assert res["total_options"] == 2
    assert res["invalid_crash_slope_ids"] == ["ACT-EXPANDED", "ACT-CHEAP"]
    assert res["non_critical_compression_ids"] == []
    assert res["high_risk_fast_track_ids"] == []
    assert res["total_days_saved"] == 0.0
    assert res["compression_posture"] == "INVALID_CRASH_COST_DURATION_SLOPE"


def test_validate_schedule_compression_options_noncritical_and_risky_fasttrack():
    """> Compresión fuera de ruta crítico y fast-tracking agresivo por pilar."""
    from backend.schemas.projects import validate_schedule_compression_options

    res = validate_schedule_compression_options(
        [
            {
                "id": "ACT-WASTE",
                "is_critical": False,
                "normal_duration_days": 9.0,
                "crash_duration_days": 6.0,
            },
            {
                "id": "ACT-RISKY",
                "is_critical": True,
                "normal_duration_days": 8.0,
                "crash_duration_days": 7.0,
                "technique": "fast_tracking",
                "rework_risk_pct": 40.0,
            },
            {
                "id": "ACT-SQUEEZE",
                "is_critical": True,
                "normal_duration_days": 10.0,
                "crash_duration_days": 4.0,
                "technique": "ejecucion_rapida",
                "overlap_risk_pct": 10.0,
            },
        ]
    )
    assert res["is_compression_plan_sound"] is False
    assert res["total_options"] == 3
    # ACT-WASTE comprimido sin ser critico; ACT-RISKY rework 40% > 25%; ACT-SQUEEZE comprime 60% > 50%.
    assert res["non_critical_compression_ids"] == ["ACT-WASTE"]
    assert res["high_risk_fast_track_ids"] == ["ACT-RISKY", "ACT-SQUEEZE"]
    assert res["invalid_crash_slope_ids"] == []
    assert res["total_days_saved"] == 0.0
    assert res["compression_posture"] == "NON_CRITICAL_PATH_COMPRESSION_WASTE"


def test_validate_schedule_compression_options_empty_or_none():
    """None, lista vacía o entradas no-dict -> NO_COMPRESSION_OPTIONS."""
    from backend.schemas.projects import validate_schedule_compression_options

    for payload in (None, [], ["invalid", 42, None]):
        res = validate_schedule_compression_options(payload)  # type: ignore[arg-type]
        assert res == {
            "total_options": 0,
            "total_days_saved": 0.0,
            "non_critical_compression_ids": [],
            "invalid_crash_slope_ids": [],
            "high_risk_fast_track_ids": [],
            "is_compression_plan_sound": True,
            "compression_posture": "NO_COMPRESSION_OPTIONS",
        }


def test_validate_wbs_work_package_sizing_heuristic_balanced():
    """Paquetes hoja entre 8 y 80h con 1 owner -> BALANCED_8_80_WBS_DECOMPOSITION; ignora nodos resumen."""
    from backend.schemas.projects import validate_wbs_work_package_sizing_heuristic

    res = validate_wbs_work_package_sizing_heuristic(
        [
            {"id": "WBS-1.0", "is_leaf": False, "estimated_hours": 240.0},
            {"id": "WP-1.1", "is_leaf": True, "estimated_hours": 16.0, "owner_id": "USR-1"},
            {"wp_id": "WP-1.2", "estimated_hours": 80.0, "owners": ["USR-2"]},
            {"id": "WP-1.3", "estimated_hours": 8.0, "owner_id": "USR-3"},
        ]
    )
    assert res == {
        "total_leaf_packages": 3,
        "undersized_package_ids": [],
        "oversized_package_ids": [],
        "invalid_ownership_package_ids": [],
        "is_wbs_sizing_compliant": True,
        "sizing_posture": "BALANCED_8_80_WBS_DECOMPOSITION",
    }


def test_validate_wbs_work_package_sizing_heuristic_oversized():
    """Paquetes hoja > 80h -> OVERSIZED_WORK_PACKAGES_NEED_DECOMPOSITION."""
    from backend.schemas.projects import validate_wbs_work_package_sizing_heuristic

    res = validate_wbs_work_package_sizing_heuristic(
        [
            {"id": "WP-BIG", "estimated_hours": 120.0, "owner_id": "USR-1"},
            {"id": "WP-OK", "estimated_hours": 40.0, "owner_id": "USR-2"},
        ]
    )
    assert res["total_leaf_packages"] == 2
    assert res["oversized_package_ids"] == ["WP-BIG"]
    assert res["undersized_package_ids"] == []
    assert res["invalid_ownership_package_ids"] == []
    assert res["is_wbs_sizing_compliant"] is False
    assert res["sizing_posture"] == "OVERSIZED_WORK_PACKAGES_NEED_DECOMPOSITION"


def test_validate_wbs_work_package_sizing_heuristic_invalid_ownership_and_undersized():
    """Sin owner o múltiples owners -> INVALID_WORK_PACKAGE_OWNERSHIP; < 8h -> UNDERSIZED_MICRO_WORK_PACKAGES."""
    from backend.schemas.projects import validate_wbs_work_package_sizing_heuristic

    res_own = validate_wbs_work_package_sizing_heuristic(
        [
            {"id": "WP-NO-OWN", "estimated_hours": 24.0},
            {"id": "WP-DUAL-OWN", "estimated_hours": 32.0, "owners": ["USR-1", "USR-2"]},
        ]
    )
    assert res_own["invalid_ownership_package_ids"] == ["WP-NO-OWN", "WP-DUAL-OWN"]
    assert res_own["is_wbs_sizing_compliant"] is False
    assert res_own["sizing_posture"] == "INVALID_WORK_PACKAGE_OWNERSHIP"

    res_micro = validate_wbs_work_package_sizing_heuristic(
        [
            {"id": "WP-MICRO", "estimated_hours": 4.0, "owner_id": "USR-1"},
        ]
    )
    assert res_micro["undersized_package_ids"] == ["WP-MICRO"]
    assert res_micro["is_wbs_sizing_compliant"] is False
    assert res_micro["sizing_posture"] == "UNDERSIZED_MICRO_WORK_PACKAGES"


def test_validate_wbs_work_package_sizing_heuristic_empty_or_only_summary():
    """Lista vacía, None o solo nodos resumen -> NO_LEAF_WORK_PACKAGES."""
    from backend.schemas.projects import validate_wbs_work_package_sizing_heuristic

    for payload in (None, [], [{"id": "WBS-ROOT", "is_leaf": False, "estimated_hours": 500.0}]):
        res = validate_wbs_work_package_sizing_heuristic(payload)
        assert res == {
            "total_leaf_packages": 0,
            "undersized_package_ids": [],
            "oversized_package_ids": [],
            "invalid_ownership_package_ids": [],
            "is_wbs_sizing_compliant": False,
            "sizing_posture": "NO_LEAF_WORK_PACKAGES",
        }


def test_validate_monte_carlo_schedule_confidence_buffer_adequate_p80_and_p95():
    """Buffer cubre P80 (< P95) -> ADEQUATE_P80_SCHEDULE_CONFIDENCE; cubre >= P95 -> HIGH_P95_CONFIDENCE_COVERAGE."""
    from backend.schemas.projects import validate_monte_carlo_schedule_confidence_buffer

    res_p80 = validate_monte_carlo_schedule_confidence_buffer(
        deterministic_duration_days=100.0,
        p50_days=108.0,
        p80_days=120.0,
        p95_days=135.0,
        allocated_buffer_days=22.0,
    )
    assert res_p80 == {
        "committed_duration_days": 122.0,
        "required_p80_buffer_days": 20.0,
        "buffer_shortfall_days": 0.0,
        "tail_spread_p95_p50_days": 27.0,
        "is_monotonic_distribution": True,
        "meets_p80_confidence": True,
        "monte_carlo_posture": "ADEQUATE_P80_SCHEDULE_CONFIDENCE",
    }

    res_p95 = validate_monte_carlo_schedule_confidence_buffer(
        deterministic_duration_days=100.0,
        p50_days=108.0,
        p80_days=120.0,
        p95_days=135.0,
        allocated_buffer_days=36.0,
    )
    assert res_p95["committed_duration_days"] == 136.0
    assert res_p95["meets_p80_confidence"] is True
    assert res_p95["monte_carlo_posture"] == "HIGH_P95_CONFIDENCE_COVERAGE"


def test_validate_monte_carlo_schedule_confidence_buffer_below_p50_and_insufficient_p80():
    """Comprometido < P50 -> BELOW_P50_HIGH_OVERRUN_PROBABILITY; P50 <= comprometido < P80 -> INSUFFICIENT_P80_CONFIDENCE_BUFFER."""
    from backend.schemas.projects import validate_monte_carlo_schedule_confidence_buffer

    res_below_p50 = validate_monte_carlo_schedule_confidence_buffer(
        deterministic_duration_days=100.0,
        p50_days=110.0,
        p80_days=125.0,
        p95_days=140.0,
        allocated_buffer_days=5.0,
    )
    assert res_below_p50["committed_duration_days"] == 105.0
    assert res_below_p50["buffer_shortfall_days"] == 20.0
    assert res_below_p50["meets_p80_confidence"] is False
    assert res_below_p50["monte_carlo_posture"] == "BELOW_P50_HIGH_OVERRUN_PROBABILITY"

    res_insuf_p80 = validate_monte_carlo_schedule_confidence_buffer(
        deterministic_duration_days=100.0,
        p50_days=110.0,
        p80_days=125.0,
        p95_days=140.0,
        allocated_buffer_days=15.0,
    )
    assert res_insuf_p80["committed_duration_days"] == 115.0
    assert res_insuf_p80["buffer_shortfall_days"] == 10.0
    assert res_insuf_p80["meets_p80_confidence"] is False
    assert res_insuf_p80["monte_carlo_posture"] == "INSUFFICIENT_P80_CONFIDENCE_BUFFER"


def test_validate_monte_carlo_schedule_confidence_buffer_non_monotonic():
    """Percentiles invertidos (P50 > P80 o P80 > P95) -> NON_MONOTONIC_PERCENTILE_CURVE."""
    from backend.schemas.projects import validate_monte_carlo_schedule_confidence_buffer

    res = validate_monte_carlo_schedule_confidence_buffer(
        deterministic_duration_days=100.0,
        p50_days=130.0,
        p80_days=120.0,
        p95_days=140.0,
        allocated_buffer_days=25.0,
    )
    assert res["is_monotonic_distribution"] is False
    assert res["meets_p80_confidence"] is False
    assert res["monte_carlo_posture"] == "NON_MONOTONIC_PERCENTILE_CURVE"


def test_validate_monte_carlo_schedule_confidence_buffer_invalid_inputs():
    """Duración determinística o percentiles <= 0 -> INVALID_MONTE_CARLO_INPUTS."""
    from backend.schemas.projects import validate_monte_carlo_schedule_confidence_buffer

    for kwargs in (
        {"deterministic_duration_days": 0.0, "p50_days": 10.0, "p80_days": 12.0, "p95_days": 15.0},
        {"deterministic_duration_days": 10.0, "p50_days": 0.0, "p80_days": 12.0, "p95_days": 15.0},
        {"deterministic_duration_days": 10.0, "p50_days": 10.0, "p80_days": -5.0, "p95_days": 15.0},
    ):
        res = validate_monte_carlo_schedule_confidence_buffer(**kwargs)
        assert res == {
            "committed_duration_days": 0.0,
            "required_p80_buffer_days": 0.0,
            "buffer_shortfall_days": 0.0,
            "tail_spread_p95_p50_days": 0.0,
            "is_monotonic_distribution": False,
            "meets_p80_confidence": False,
            "monte_carlo_posture": "INVALID_MONTE_CARLO_INPUTS",
        }


def test_validate_resource_leveling_overallocation_leveled_and_smoothed():
    """Recursos con carga <= capacidad y ratio pico/promedio <= 1.5 -> LEVELED_AND_SMOOTHED_RESOURCES."""
    import backend.schemas.projects as projects_module
    from backend.schemas.projects import validate_resource_leveling_overallocation

    allocations = [
        {
            "resource_id": "RES-01",
            "capacity_hours_per_period": 40.0,
            "period_loads": [32.0, 36.0, 40.0, 36.0],
        },
        {
            "id": "RES-02",
            "capacity_hours": 30.0,
            "period_loads": [20.0, 24.0, 28.0, 24.0],
        },
    ]
    res = validate_resource_leveling_overallocation(
        allocations, max_peak_to_average_ratio=1.5
    )
    assert res == {
        "total_resources": 2,
        "overallocated_resource_ids": [],
        "unsmoothed_peak_resource_ids": [],
        "is_resource_schedule_leveled": True,
        "leveling_posture": "LEVELED_AND_SMOOTHED_RESOURCES",
    }
    assert "validate_resource_leveling_overallocation" in projects_module.__all__


def test_validate_resource_leveling_overallocation_capacity_overallocated():
    """Recurso con carga pico > capacidad -> RESOURCE_CAPACITY_OVERALLOCATED."""
    from backend.schemas.projects import validate_resource_leveling_overallocation

    res = validate_resource_leveling_overallocation(
        [
            {
                "resource_id": "RES-OVER",
                "capacity_hours_per_period": 40.0,
                "period_loads": [38.0, 48.0, 36.0],
            },
            {
                "resource_id": "RES-OK",
                "capacity_hours_per_period": 40.0,
                "period_loads": [35.0, 35.0, 35.0],
            },
        ]
    )
    assert res["total_resources"] == 2
    assert res["overallocated_resource_ids"] == ["RES-OVER"]
    assert res["is_resource_schedule_leveled"] is False
    assert res["leveling_posture"] == "RESOURCE_CAPACITY_OVERALLOCATED"


def test_validate_resource_leveling_overallocation_unsmoothed_peaks():
    """Sin sobre-asignación pero ratio pico/promedio > límite -> UNSMOOTHED_RESOURCE_LOAD_PEAKS."""
    from backend.schemas.projects import validate_resource_leveling_overallocation

    res = validate_resource_leveling_overallocation(
        [
            {
                "resource_id": "RES-SPIKE",
                "capacity_hours_per_period": 40.0,
                "period_loads": [5.0, 5.0, 40.0, 10.0],
            }
        ],
        max_peak_to_average_ratio=1.5,
    )
    assert res == {
        "total_resources": 1,
        "overallocated_resource_ids": [],
        "unsmoothed_peak_resource_ids": ["RES-SPIKE"],
        "is_resource_schedule_leveled": False,
        "leveling_posture": "UNSMOOTHED_RESOURCE_LOAD_PEAKS",
    }


def test_validate_resource_leveling_overallocation_no_allocations():
    """Lista vacía, None o entradas sin cargas válidas -> NO_RESOURCE_ALLOCATIONS."""
    from backend.schemas.projects import validate_resource_leveling_overallocation

    for payload in (
        None,
        [],
        [{"resource_id": ""}],
        [{"resource_id": "RES-EMPTY", "period_loads": []}],
    ):
        res = validate_resource_leveling_overallocation(payload)
        assert res == {
            "total_resources": 0,
            "overallocated_resource_ids": [],
            "unsmoothed_peak_resource_ids": [],
            "is_resource_schedule_leveled": False,
            "leveling_posture": "NO_RESOURCE_ALLOCATIONS",
        }


def test_validate_schedule_buffer_fever_chart_status_green_and_yellow_zones():
    """Cadenas en zona verde y amarilla sin violaciones -> is_valid True."""
    from backend.schemas.projects import validate_schedule_buffer_fever_chart_status

    res = validate_schedule_buffer_fever_chart_status(
        [
            {
                "chain_id": "CHAIN-GREEN",
                "chain_progress_pct": 50.0,
                "buffer_total_days": 20.0,
                "buffer_consumed_days": 4.0,
                "recovery_plan_defined": False,
            },
            {
                "chain_id": "CHAIN-YELLOW",
                "chain_progress_pct": 50.0,
                "buffer_total_days": 20.0,
                "buffer_consumed_days": 10.0,
                "recovery_plan_defined": False,
            },
        ]
    )
    assert res == {
        "evaluated_chain_count": 2,
        "green_zone_chain_ids": ["CHAIN-GREEN"],
        "yellow_zone_chain_ids": ["CHAIN-YELLOW"],
        "red_zone_chain_ids": [],
        "unmitigated_red_zone_ids": [],
        "invalid_buffer_ids": [],
        "max_burn_rate_index": 1.0,
        "is_valid": True,
    }


def test_validate_schedule_buffer_fever_chart_status_red_zone_mitigated_and_unmitigated():
    """Zona roja con plan de recuperación -> is_valid True; sin plan -> unmitigated_red_zone_ids y is_valid False."""
    from backend.schemas.projects import validate_schedule_buffer_fever_chart_status

    res_mitigated = validate_schedule_buffer_fever_chart_status(
        [
            {
                "chain_id": "CHAIN-RED-OK",
                "chain_progress_pct": 20.0,
                "buffer_total_days": 10.0,
                "buffer_consumed_days": 6.0,
                "recovery_plan_defined": True,
            }
        ]
    )
    assert res_mitigated["red_zone_chain_ids"] == ["CHAIN-RED-OK"]
    assert res_mitigated["unmitigated_red_zone_ids"] == []
    assert res_mitigated["max_burn_rate_index"] == 3.0
    assert res_mitigated["is_valid"] is True

    res_unmitigated = validate_schedule_buffer_fever_chart_status(
        [
            {
                "chain_id": "CHAIN-RED-BAD",
                "chain_progress_pct": 20.0,
                "buffer_total_days": 10.0,
                "buffer_consumed_days": 6.0,
                "recovery_plan_defined": False,
            }
        ]
    )
    assert res_unmitigated["red_zone_chain_ids"] == ["CHAIN-RED-BAD"]
    assert res_unmitigated["unmitigated_red_zone_ids"] == ["CHAIN-RED-BAD"]
    assert res_unmitigated["is_valid"] is False


def test_validate_schedule_buffer_fever_chart_status_invalid_buffer_total():
    """Buffer total <= 0 -> invalid_buffer_ids poblado, consumo 100%, is_valid False."""
    from backend.schemas.projects import validate_schedule_buffer_fever_chart_status

    res = validate_schedule_buffer_fever_chart_status(
        [
            {
                "chain_id": "CHAIN-ZERO-BUF",
                "chain_progress_pct": 40.0,
                "buffer_total_days": 0.0,
                "buffer_consumed_days": 2.0,
                "recovery_plan_defined": True,
            }
        ]
    )
    assert res["invalid_buffer_ids"] == ["CHAIN-ZERO-BUF"]
    assert res["red_zone_chain_ids"] == ["CHAIN-ZERO-BUF"]
    assert res["max_burn_rate_index"] == 2.5
    assert res["is_valid"] is False


def test_validate_schedule_buffer_fever_chart_status_empty_or_invalid_entries():
    """Lista vacía, None o entradas sin chain_id -> evaluated_chain_count 0, is_valid False."""
    from backend.schemas.projects import validate_schedule_buffer_fever_chart_status

    for payload in (None, [], [{"chain_id": "   "}], ["invalid"]):
        res = validate_schedule_buffer_fever_chart_status(payload)  # type: ignore[arg-type]
        assert res == {
            "evaluated_chain_count": 0,
            "green_zone_chain_ids": [],
            "yellow_zone_chain_ids": [],
            "red_zone_chain_ids": [],
            "unmitigated_red_zone_ids": [],
            "invalid_buffer_ids": [],
            "max_burn_rate_index": 0.0,
            "is_valid": False,
        }


def test_validate_rolling_wave_planning_horizon_valid():
    """> Planning lejos del horizonte y work packages near-term listos -> is_valid."""
    from backend.schemas.projects import validate_rolling_wave_planning_horizon

    res = validate_rolling_wave_planning_horizon(
        [
            {
                "package_id": "PP-FAR",
                "package_type": "planning_package",
                "days_until_start": 90,
            },
            {
                "package_id": "WP-NEAR",
                "package_type": "work_package",
                "days_until_start": 10,
                "has_detailed_activities": True,
                "has_assigned_owner": True,
                "estimated_effort_hours": 40.0,
            },
        ]
    )
    assert res["evaluated_package_count"] == 2
    assert res["undecomposed_near_term_planning_ids"] == []
    assert res["unready_near_term_work_package_ids"] == []
    assert res["valid_far_term_planning_ids"] == ["PP-FAR"]
    assert res["invalid_package_type_ids"] == []
    assert res["is_valid"] is True


def test_validate_rolling_wave_planning_horizon_undecomposed_near_term_planning():
    """> Planning package cerca del horizonte sin descomponer (y lejos con tope custom)."""
    from backend.schemas.projects import validate_rolling_wave_planning_horizon

    res = validate_rolling_wave_planning_horizon(
        [
            {
                "package_id": "PP-NEAR",
                "package_type": "planning_package",
                "days_until_start": 15,
            },
            {
                "package_id": "PP-EDGE",
                "package_type": "planning_package",
                "days_until_start": 30,
            },
        ]
    )
    assert res["evaluated_package_count"] == 2
    assert res["undecomposed_near_term_planning_ids"] == ["PP-NEAR", "PP-EDGE"]
    assert res["valid_far_term_planning_ids"] == []
    assert res["invalid_package_type_ids"] == []
    assert res["is_valid"] is False

    # Con horizonte de 14 días: PP-15 pasa a ser válido lejos y PP-10 queda cerca.
    res_relaxed = validate_rolling_wave_planning_horizon(
        [
            {"package_id": "PP-15", "package_type": "planning_package", "days_until_start": 15},
            {"package_id": "PP-10", "package_type": "planning_package", "days_until_start": 10},
        ],
        near_term_horizon_days=14,
    )
    assert res_relaxed["undecomposed_near_term_planning_ids"] == ["PP-10"]
    assert res_relaxed["valid_far_term_planning_ids"] == ["PP-15"]
    assert res_relaxed["is_valid"] is False


def test_validate_rolling_wave_planning_horizon_unready_near_term_work_package():
    """> Work package near-term detallado a medias -> unready (3 variantes + lejos)."""
    from backend.schemas.projects import validate_rolling_wave_planning_horizon

    res = validate_rolling_wave_planning_horizon(
        [
            {
                "package_id": "WP-NO-DETAIL",
                "package_type": "work_package",
                "days_until_start": 5,
                "has_detailed_activities": False,
                "has_assigned_owner": True,
                "estimated_effort_hours": 20.0,
            },
            {
                "package_id": "WP-NO-OWNER",
                "package_type": "work_package",
                "days_until_start": 5,
                "has_detailed_activities": True,
                "has_assigned_owner": False,
                "estimated_effort_hours": 20.0,
            },
            {
                "package_id": "WP-NO-EFFORT",
                "package_type": "work_package",
                "days_until_start": 5,
                "has_detailed_activities": True,
                "has_assigned_owner": True,
                "estimated_effort_hours": 0.0,
            },
            {
                "package_id": "WP-FAR-EXEMPT",
                "package_type": "work_package",
                "days_until_start": 60,
                "has_detailed_activities": False,
                "has_assigned_owner": False,
                "estimated_effort_hours": 0.0,
            },
        ]
    )
    assert res["evaluated_package_count"] == 4
    assert res["unready_near_term_work_package_ids"] == [
        "WP-NO-DETAIL",
        "WP-NO-OWNER",
        "WP-NO-EFFORT",
    ]
    assert res["undecomposed_near_term_planning_ids"] == []
    assert res["invalid_package_type_ids"] == []
    assert res["is_valid"] is False


def test_validate_rolling_wave_planning_horizon_invalid_type_and_empty():
    """> Tipos inválidos y entradas vacías/None/basura -> invalid_package_type_ids recogidos."""
    from backend.schemas.projects import validate_rolling_wave_planning_horizon

    res = validate_rolling_wave_planning_horizon(
        [
            {"package_id": "WP-WEIRD", "package_type": "Milestone"},
            {"package_id": "PP-EMPTY-TYPE", "package_type": ""},
            {"package_id": "WP-OK", "package_type": "WORK_PACKAGE", "days_until_start": 100},
        ]
    )
    assert res["evaluated_package_count"] == 3
    assert res["invalid_package_type_ids"] == ["WP-WEIRD", "PP-EMPTY-TYPE"]
    # WP-OK es work_package lejos del horizonte: no infringe ninguna lista.
    assert res["undecomposed_near_term_planning_ids"] == []
    assert res["unready_near_term_work_package_ids"] == []
    assert res["valid_far_term_planning_ids"] == []
    assert res["is_valid"] is False

    for payload in (None, [], ["no-dict", 42]):
        assert validate_rolling_wave_planning_horizon(payload) == {  # type: ignore[arg-type]
            "evaluated_package_count": 0,
            "undecomposed_near_term_planning_ids": [],
            "unready_near_term_work_package_ids": [],
            "valid_far_term_planning_ids": [],
            "invalid_package_type_ids": [],
            "is_valid": False,
        }


def test_validate_schedule_path_convergence_risk_safe_and_buffered():
    """Nodos con convergencia segura o hotspots mitigados con buffer pasan is_valid=True."""
    from backend.schemas.projects import validate_schedule_path_convergence_risk

    res = validate_schedule_path_convergence_risk(
        [
            {
                "node_id": "M-100",
                "predecessor_float_days": [5.0, 8.0],
                "is_milestone": True,
                "risk_mitigation_buffered": False,
            },
            {
                "node_id": "M-200",
                "predecessor_float_days": [0.0, 1.5, 4.0, 6.0],
                "is_milestone": True,
                "risk_mitigation_buffered": True,
            },
        ]
    )
    assert res == {
        "evaluated_node_count": 2,
        "high_convergence_node_ids": ["M-200"],
        "multi_near_critical_merge_ids": ["M-200"],
        "unbuffered_merge_hotspot_ids": [],
        "invalid_node_ids": [],
        "is_valid": True,
    }


def test_validate_schedule_path_convergence_risk_unbuffered_hotspots():
    """Detecta alta convergencia (>3 predecesoras) y múltiples rutas cuasi-críticas sin buffer."""
    from backend.schemas.projects import validate_schedule_path_convergence_risk

    res = validate_schedule_path_convergence_risk(
        [
            {
                "node_id": "ACT-MERGE-HIGH",
                "predecessor_float_days": [5.0, 6.0, 7.0, 8.0],
                "risk_mitigation_buffered": False,
            },
            {
                "node_id": "ACT-MERGE-CRIT",
                "predecessor_float_days": [0.0, 2.0],
                "risk_mitigation_buffered": False,
            },
        ]
    )
    assert res == {
        "evaluated_node_count": 2,
        "high_convergence_node_ids": ["ACT-MERGE-HIGH"],
        "multi_near_critical_merge_ids": ["ACT-MERGE-CRIT"],
        "unbuffered_merge_hotspot_ids": ["ACT-MERGE-HIGH", "ACT-MERGE-CRIT"],
        "invalid_node_ids": [],
        "is_valid": False,
    }


def test_validate_schedule_path_convergence_risk_invalid_floats():
    """Registra nodos con lista de holguras vacía, negativa o no numérica en invalid_node_ids."""
    from backend.schemas.projects import validate_schedule_path_convergence_risk

    res = validate_schedule_path_convergence_risk(
        [
            {"node_id": "N-EMPTY", "predecessor_float_days": []},
            {"node_id": "N-NEG", "predecessor_float_days": [3.0, -1.0]},
            {"node_id": "N-STR", "predecessor_float_days": ["bad"]},
            {"node_id": "N-OK", "predecessor_float_days": [4.0, 5.0]},
        ]
    )
    assert res == {
        "evaluated_node_count": 4,
        "high_convergence_node_ids": [],
        "multi_near_critical_merge_ids": [],
        "unbuffered_merge_hotspot_ids": [],
        "invalid_node_ids": ["N-EMPTY", "N-NEG", "N-STR"],
        "is_valid": False,
    }


def test_validate_schedule_path_convergence_risk_empty_or_non_mapping():
    """Entradas vacías o sin nodos válidos devuelven is_valid=False."""
    from backend.schemas.projects import validate_schedule_path_convergence_risk

    for payload in (None, [], ["invalid", {"node_id": "   "}]):
        assert validate_schedule_path_convergence_risk(payload) == {  # type: ignore[arg-type]
            "evaluated_node_count": 0,
            "high_convergence_node_ids": [],
            "multi_near_critical_merge_ids": [],
            "unbuffered_merge_hotspot_ids": [],
            "invalid_node_ids": [],
            "is_valid": False,
        }


def test_validate_schedule_risk_mitigation_residual_delay_controlled():
    """Respuestas válidas con reducción real de demora y residual dentro del umbral pasan is_schedule_risk_controlled=True."""
    from backend.schemas.projects import (
        validate_schedule_risk_mitigation_residual_delay,
    )

    res = validate_schedule_risk_mitigation_residual_delay(
        [
            {
                "risk_id": "RSK-01",
                "strategy": "Mitigate",
                "pre_mitigation_delay_days": 12.0,
                "post_mitigation_delay_days": 3.0,
                "fallback_plan": "Activar proveedor secundario",
            },
            {
                "risk_id": "RSK-02",
                "strategy": "avoid",
                "pre_mitigation_delay_days": 8.0,
                "post_mitigation_delay_days": 0.0,
            },
        ],
        max_acceptable_residual_days=5.0,
    )
    assert res == {
        "total_evaluated": 2,
        "total_pre_mitigation_days": 20.0,
        "total_post_mitigation_days": 3.0,
        "delay_reduction_pct": 85.0,
        "ineffective_response_risk_ids": [],
        "excessive_residual_risk_ids": [],
        "missing_fallback_risk_ids": [],
        "is_schedule_risk_controlled": True,
    }


def test_validate_schedule_risk_mitigation_residual_delay_ineffective_strategy():
    """Detecta estrategias inválidas o avoid/mitigate que no reducen la demora pre-mitigación."""
    from backend.schemas.projects import (
        validate_schedule_risk_mitigation_residual_delay,
    )

    res = validate_schedule_risk_mitigation_residual_delay(
        [
            {
                "risk_id": "RSK-NO-REDUCTION",
                "strategy": "mitigate",
                "pre_mitigation_delay_days": 4.0,
                "post_mitigation_delay_days": 4.0,
            },
            {
                "risk_id": "RSK-BAD-STRAT",
                "strategy": "ignore",
                "pre_mitigation_delay_days": 3.0,
                "post_mitigation_delay_days": 1.0,
            },
        ]
    )
    assert res["total_evaluated"] == 2
    assert res["ineffective_response_risk_ids"] == [
        "RSK-NO-REDUCTION",
        "RSK-BAD-STRAT",
    ]
    assert res["is_schedule_risk_controlled"] is False


def test_validate_schedule_risk_mitigation_residual_delay_excessive_and_missing_fallback():
    """Detecta demora residual superior al umbral y ausencia de fallback_plan."""
    from backend.schemas.projects import (
        validate_schedule_risk_mitigation_residual_delay,
    )

    res = validate_schedule_risk_mitigation_residual_delay(
        [
            {
                "risk_id": "RSK-RES-WITH-FB",
                "strategy": "transfer",
                "pre_mitigation_delay_days": 15.0,
                "post_mitigation_delay_days": 7.0,
                "fallback_plan": "Usar reserva de contingencia de cronograma",
            },
            {
                "risk_id": "RSK-RES-NO-FB",
                "strategy": "accept",
                "pre_mitigation_delay_days": 10.0,
                "post_mitigation_delay_days": 8.0,
                "fallback_plan": "   ",
            },
        ],
        max_acceptable_residual_days=5.0,
    )
    assert res == {
        "total_evaluated": 2,
        "total_pre_mitigation_days": 25.0,
        "total_post_mitigation_days": 15.0,
        "delay_reduction_pct": 40.0,
        "ineffective_response_risk_ids": [],
        "excessive_residual_risk_ids": ["RSK-RES-WITH-FB", "RSK-RES-NO-FB"],
        "missing_fallback_risk_ids": ["RSK-RES-NO-FB"],
        "is_schedule_risk_controlled": False,
    }


def test_validate_schedule_risk_mitigation_residual_delay_empty_or_invalid():
    """Entradas vacías, None o no-secuencia devuelven total_evaluated=0 e is_schedule_risk_controlled=False."""
    from backend.schemas.projects import (
        validate_schedule_risk_mitigation_residual_delay,
    )

    for payload in (None, [], "invalid", {"risk_id": "RSK-1"}, [{"risk_id": "  "}]):
        assert validate_schedule_risk_mitigation_residual_delay(payload) == {  # type: ignore[arg-type]
            "total_evaluated": 0,
            "total_pre_mitigation_days": 0.0,
            "total_post_mitigation_days": 0.0,
            "delay_reduction_pct": 0.0,
            "ineffective_response_risk_ids": [],
            "excessive_residual_risk_ids": [],
            "missing_fallback_risk_ids": [],
            "is_schedule_risk_controlled": False,
        }




def test_validate_resource_smoothing_float_boundaries_valid():
    """> Suavizado dentro de holgura libre sin tocar ruta crítica -> is_smoothing_valid."""
    from backend.schemas.projects import validate_resource_smoothing_float_boundaries

    res = validate_resource_smoothing_float_boundaries(
        [
            {
                "activity_id": "ACT-A",
                "free_float_days": 5.0,
                "total_float_days": 8.0,
                "smoothing_shift_days": 3.0,
                "peak_utilization_pct": 90.0,
            },
            {
                "activity_id": "ACT-B",
                "free_float_days": 2.0,
                "total_float_days": 6.0,
                "smoothing_shift_days": 2.0,
                "peak_utilization_pct": 100.0,
            },
            {
                "activity_id": "ACT-C",
                "is_critical": True,
                "free_float_days": 0.0,
                "total_float_days": 0.0,
                "smoothing_shift_days": 0.0,
                "peak_utilization_pct": 75.0,
            },
        ]
    )
    assert res["total_activities"] == 3
    assert res["critical_path_shifted_activity_ids"] == []
    assert res["float_exceeded_activity_ids"] == []
    assert res["unresolved_overallocation_activity_ids"] == []
    assert res["is_smoothing_valid"] is True


def test_validate_resource_smoothing_float_boundaries_critical_shifted():
    """> is_critical=True o total_float_days=0 desplazadas -> critical_path_shifted."""
    from backend.schemas.projects import validate_resource_smoothing_float_boundaries

    res = validate_resource_smoothing_float_boundaries(
        [
            {
                "activity_id": "ACT-FLAG-CP",
                "is_critical": True,
                "free_float_days": 4.0,
                "total_float_days": 9.0,
                "smoothing_shift_days": 1.0,
            },
            {
                "activity_id": "ACT-ZERO-TF",
                "free_float_days": 2.0,
                "smoothing_shift_days": 0.5,
            },
        ]
    )
    assert res["total_activities"] == 2
    assert res["critical_path_shifted_activity_ids"] == ["ACT-FLAG-CP", "ACT-ZERO-TF"]
    assert res["is_smoothing_valid"] is False


def test_validate_resource_smoothing_float_boundaries_float_exceeded_and_overallocation():
    """> Shift > free_float_days y pico > 100% -> listas separadas."""
    from backend.schemas.projects import validate_resource_smoothing_float_boundaries

    res = validate_resource_smoothing_float_boundaries(
        [
            {
                "activity_id": "ACT-EXCEED",
                "free_float_days": 3.0,
                "total_float_days": 7.0,
                "smoothing_shift_days": 3.5,
                "peak_utilization_pct": 80.0,
            },
            {
                "activity_id": "ACT-OVERALLOC",
                "free_float_days": 10.0,
                "total_float_days": 12.0,
                "smoothing_shift_days": 4.0,
                "peak_utilization_pct": 120.5,
            },
            {
                "activity_id": "ACT-EDGE-OK",
                "free_float_days": 2.0,
                "total_float_days": 5.0,
                "smoothing_shift_days": 2.0,
                "peak_utilization_pct": 100.0,
            },
        ]
    )
    assert res["total_activities"] == 3
    assert res["float_exceeded_activity_ids"] == ["ACT-EXCEED"]
    assert res["unresolved_overallocation_activity_ids"] == ["ACT-OVERALLOC"]
    assert res["critical_path_shifted_activity_ids"] == []
    assert res["is_smoothing_valid"] is False


def test_validate_resource_smoothing_float_boundaries_empty_or_none():
    """None, str, Mapping, 42 o entradas malformadas -> 0 actividades y valid False."""
    from backend.schemas.projects import validate_resource_smoothing_float_boundaries

    empty_result = {
        "total_activities": 0,
        "critical_path_shifted_activity_ids": [],
        "float_exceeded_activity_ids": [],
        "unresolved_overallocation_activity_ids": [],
        "is_smoothing_valid": False,
    }

    for payload in (None, "activities-string", {"activity_id": "X"}, 42, [], ["no-dict", {"is_critical": True}]):
        assert validate_resource_smoothing_float_boundaries(payload) == empty_result  # type: ignore[arg-type]


def test_validate_sprint_velocity_commitment_stability_predictable_sustainable():
    """Velocidades estables (CV <= 25%) y compromiso dentro de [0.70, 1.15] -> predictable_sustainable."""
    from backend.schemas.projects import validate_sprint_velocity_commitment_stability

    res = validate_sprint_velocity_commitment_stability(
        [40.0, 42.0, 38.0, 40.0],
        42.0,
    )
    assert res == {
        "sprints_analyzed": 4,
        "mean_velocity": 40.0,
        "velocity_cv_pct": 3.54,
        "committed_points": 42.0,
        "commitment_to_mean_ratio": 1.05,
        "stability_posture": "predictable_sustainable",
        "is_commitment_sustainable": True,
    }


def test_validate_sprint_velocity_commitment_stability_overcommitted_and_volatile():
    """Compromiso > max_overcommitment_ratio -> overcommitted; CV > 25% -> volatile_velocity."""
    from backend.schemas.projects import validate_sprint_velocity_commitment_stability

    over = validate_sprint_velocity_commitment_stability(
        [30, 32, 28],
        36.0,
        max_overcommitment_ratio=1.15,
    )
    assert over["sprints_analyzed"] == 3
    assert over["mean_velocity"] == 30.0
    assert over["commitment_to_mean_ratio"] == 1.2
    assert over["stability_posture"] == "overcommitted"
    assert over["is_commitment_sustainable"] is False

    volatile = validate_sprint_velocity_commitment_stability(
        [10.0, 50.0, 20.0, 40.0],
        30.0,
    )
    assert volatile["sprints_analyzed"] == 4
    assert volatile["mean_velocity"] == 30.0
    assert volatile["velocity_cv_pct"] > 25.0
    assert volatile["stability_posture"] == "volatile_velocity"
    assert volatile["is_commitment_sustainable"] is False


def test_validate_sprint_velocity_commitment_stability_underutilized_capacity():
    """Ratio < 0.70 con velocidad estable -> underutilized_capacity."""
    from backend.schemas.projects import validate_sprint_velocity_commitment_stability

    res = validate_sprint_velocity_commitment_stability(
        [50.0, 50.0, 50.0],
        30.0,
    )
    assert res == {
        "sprints_analyzed": 3,
        "mean_velocity": 50.0,
        "velocity_cv_pct": 0.0,
        "committed_points": 30.0,
        "commitment_to_mean_ratio": 0.6,
        "stability_posture": "underutilized_capacity",
        "is_commitment_sustainable": False,
    }


def test_validate_sprint_velocity_commitment_stability_insufficient_history_or_invalid():
    """Sin historial válido, entradas booleanas/negativas o promedio 0 -> insufficient_history."""
    from backend.schemas.projects import validate_sprint_velocity_commitment_stability

    for payload in (None, "invalid", {"a": 1}, [], [True, False, -5.0, "bad"], [0.0, 0.0]):
        res = validate_sprint_velocity_commitment_stability(payload, 25.0)  # type: ignore[arg-type]
        assert res["mean_velocity"] == 0.0
        assert res["velocity_cv_pct"] == 0.0
        assert res["committed_points"] == 25.0
        assert res["commitment_to_mean_ratio"] == 0.0
        assert res["stability_posture"] == "insufficient_history"
        assert res["is_commitment_sustainable"] is False


def test_validate_fpif_point_of_total_assumption_within_pta():
    """> on_or_under_target y cost_overrun_shared con buffer PTA -> is_within_pta True."""
    from backend.schemas.projects import validate_fpif_point_of_total_assumption

    contract = {
        "target_cost": 1000.0,
        "target_fee": 100.0,
        "ceiling_price": 1400.0,
        "buyer_share_ratio": 0.5,
    }

    res_on = validate_fpif_point_of_total_assumption(
        {**contract, "estimated_actual_cost": 1000.0}
    )
    assert res_on["target_price"] == 1100.0
    assert res_on["pta"] == 1600.0
    assert res_on["estimated_actual_cost"] == 1000.0
    assert res_on["pta_buffer_remaining"] == 600.0
    assert res_on["contract_posture"] == "on_or_under_target"
    assert res_on["is_within_pta"] is True

    res_shared = validate_fpif_point_of_total_assumption(
        {**contract, "estimated_actual_cost": 1300.0}
    )
    assert res_shared["estimated_actual_cost"] == 1300.0
    assert res_shared["pta_buffer_remaining"] == 300.0
    assert res_shared["contract_posture"] == "cost_overrun_shared"
    assert res_shared["is_within_pta"] is True


def test_validate_fpif_point_of_total_assumption_above_pta_seller_absorbs():
    """> PTA < EAC <= techo -> above_pta_seller_absorbs (is_within_pta False)."""
    from backend.schemas.projects import validate_fpif_point_of_total_assumption

    # share=0.8 -> PTA = 1000 + 300/0.8 = 1375; techo = 1400.
    res = validate_fpif_point_of_total_assumption(
        {
            "target_cost": 1000.0,
            "target_fee": 100.0,
            "ceiling_price": 1400.0,
            "buyer_share_ratio": 0.8,
            "estimated_actual_cost": 1400.0,
        }
    )
    assert res["target_price"] == 1100.0
    assert res["pta"] == 1375.0
    assert res["estimated_actual_cost"] == 1400.0
    assert res["pta_buffer_remaining"] == -25.0
    assert res["contract_posture"] == "above_pta_seller_absorbs"
    assert res["is_within_pta"] is False


def test_validate_fpif_point_of_total_assumption_ceiling_breached():
    """> EAC > techo -> ceiling_breached tiene precedencia sobre above_pta."""
    from backend.schemas.projects import validate_fpif_point_of_total_assumption

    res = validate_fpif_point_of_total_assumption(
        {
            "target_cost": 1000.0,
            "target_fee": 100.0,
            "ceiling_price": 1400.0,
            "buyer_share_ratio": 0.8,
            "estimated_actual_cost": 1450.0,
        }
    )
    assert res["estimated_actual_cost"] == 1450.0
    assert res["pta_buffer_remaining"] == -75.0
    assert res["contract_posture"] == "ceiling_breached"
    assert res["is_within_pta"] is False


def test_validate_fpif_point_of_total_assumption_invalid_inputs():
    """None, vacío, techo < target_price, share fuera de (0,1), EAC<=0 -> invalid."""
    from backend.schemas.projects import validate_fpif_point_of_total_assumption

    invalid_result = {
        "target_price": 0.0,
        "pta": 0.0,
        "estimated_actual_cost": 0.0,
        "pta_buffer_remaining": 0.0,
        "contract_posture": "invalid_inputs",
        "is_within_pta": False,
    }

    base = {
        "target_cost": 1000.0,
        "target_fee": 100.0,
        "ceiling_price": 1400.0,
        "buyer_share_ratio": 0.5,
        "estimated_actual_cost": 1200.0,
    }

    bad_contracts = (
        None,
        {},
        "contract-string",
        42,
        {**base, "target_cost": 0.0},
        {**base, "target_fee": -1.0},
        {**base, "ceiling_price": 1050.0},  # techo < target_price (1100)
        {**base, "buyer_share_ratio": 0.0},
        {**base, "buyer_share_ratio": 1.0},
        {**base, "estimated_actual_cost": 0.0},
    )
    for payload in bad_contracts:
        assert validate_fpif_point_of_total_assumption(payload) == invalid_result  # type: ignore[arg-type]


def test_validate_schedule_network_lead_lag_and_float_feasibility_healthy():
    """Relaciones FS y SS con lag positivo o lead moderado y holgura no negativa pasan con status='healthy'."""
    from backend.schemas.projects import (
        validate_schedule_network_lead_lag_and_float_feasibility,
    )

    res_fs = validate_schedule_network_lead_lag_and_float_feasibility(
        predecessor_duration_days=10.0,
        successor_duration_days=8.0,
        relationship_type="fs",
        lag_days=2.0,
        total_float_days=4.0,
    )
    assert res_fs == {
        "relationship_type": "FS",
        "lag_days": 2.0,
        "lead_days": 0.0,
        "lead_ratio_pct": 0.0,
        "total_float_days": 4.0,
        "excessive_lead_detected": False,
        "sf_relationship_warning": False,
        "negative_float_detected": False,
        "is_schedule_logic_healthy": True,
        "status": "healthy",
        "recommendations": [],
    }

    res_ss = validate_schedule_network_lead_lag_and_float_feasibility(
        predecessor_duration_days=10.0,
        successor_duration_days=8.0,
        relationship_type="SS",
        lag_days=-3.0,
        total_float_days=0.0,
        max_lead_ratio_pct=50.0,
    )
    assert res_ss["lead_days"] == 3.0
    assert res_ss["lead_ratio_pct"] == 30.0
    assert res_ss["is_schedule_logic_healthy"] is True
    assert res_ss["status"] == "healthy"


def test_validate_schedule_network_lead_lag_and_float_feasibility_excessive_lead_critical():
    """Lead > max_lead_ratio_pct (ej. lag_days=-8.0 sobre predecesora de 10.0 días) dispara excessive_lead_detected=True y status='critical'."""
    from backend.schemas.projects import (
        validate_schedule_network_lead_lag_and_float_feasibility,
    )

    res = validate_schedule_network_lead_lag_and_float_feasibility(
        predecessor_duration_days=10.0,
        successor_duration_days=12.0,
        relationship_type="FS",
        lag_days=-8.0,
        total_float_days=2.0,
        max_lead_ratio_pct=50.0,
    )
    assert res["lead_days"] == 8.0
    assert res["lead_ratio_pct"] == 80.0
    assert res["excessive_lead_detected"] is True
    assert res["is_schedule_logic_healthy"] is False
    assert res["status"] == "critical"
    assert len(res["recommendations"]) == 1


def test_validate_schedule_network_lead_lag_and_float_feasibility_negative_float_and_sf_warning():
    """Holgura total negativa retorna status='critical'; relación SF con holgura positiva retorna status='warning'."""
    from backend.schemas.projects import (
        validate_schedule_network_lead_lag_and_float_feasibility,
    )

    res_neg = validate_schedule_network_lead_lag_and_float_feasibility(
        predecessor_duration_days=10.0,
        successor_duration_days=5.0,
        relationship_type="FS",
        lag_days=0.0,
        total_float_days=-3.5,
    )
    assert res_neg["negative_float_detected"] is True
    assert res_neg["is_schedule_logic_healthy"] is False
    assert res_neg["status"] == "critical"

    res_sf = validate_schedule_network_lead_lag_and_float_feasibility(
        predecessor_duration_days=10.0,
        successor_duration_days=5.0,
        relationship_type="sf",
        lag_days=0.0,
        total_float_days=1.0,
    )
    assert res_sf["relationship_type"] == "SF"
    assert res_sf["sf_relationship_warning"] is True
    assert res_sf["is_schedule_logic_healthy"] is False
    assert res_sf["status"] == "warning"


def test_validate_schedule_network_lead_lag_and_float_feasibility_invalid_inputs_raise():
    """Rechaza con ValueError duraciones <= 0, max_lead_ratio_pct fuera de rango o relationship_type inválido."""
    import pytest
    from backend.schemas.projects import (
        validate_schedule_network_lead_lag_and_float_feasibility,
    )

    with pytest.raises(ValueError):
        validate_schedule_network_lead_lag_and_float_feasibility(0.0, 5.0)
    with pytest.raises(ValueError):
        validate_schedule_network_lead_lag_and_float_feasibility(5.0, -2.0)
    with pytest.raises(ValueError):
        validate_schedule_network_lead_lag_and_float_feasibility(
            5.0, 5.0, relationship_type="INVALID"
        )
    with pytest.raises(ValueError):
        validate_schedule_network_lead_lag_and_float_feasibility(
            5.0, 5.0, max_lead_ratio_pct=0.0
        )


def test_validate_cpif_cost_sharing_and_fee_bounds_within_range():
    """> Underrun y overrun moderado dentro de la banda -> is_within_incentive_range."""
    from backend.schemas.projects import validate_cpif_cost_sharing_and_fee_bounds

    # seller=20%: fee crudo = 100 + (1000 - actual) * 0.2.
    res_underrun = validate_cpif_cost_sharing_and_fee_bounds(
        1000.0, 100.0, 60.0, 150.0, 80.0, 20.0, 950.0
    )
    assert res_underrun["cost_variance"] == 50.0
    assert res_underrun["raw_calculated_fee"] == 110.0
    assert res_underrun["final_fee"] == 110.0
    assert res_underrun["total_reimbursed_price"] == 1060.0
    assert res_underrun["is_capped_at_max_fee"] is False
    assert res_underrun["is_floored_at_min_fee"] is False
    assert res_underrun["optimistic_range_cost"] == 750.0
    assert res_underrun["pessimistic_range_cost"] == 1200.0
    assert res_underrun["is_within_incentive_range"] is True

    res_overrun = validate_cpif_cost_sharing_and_fee_bounds(
        1000.0, 100.0, 60.0, 150.0, 80.0, 20.0, 1050.0
    )
    assert res_overrun["cost_variance"] == -50.0
    assert res_overrun["raw_calculated_fee"] == 90.0
    assert res_overrun["total_reimbursed_price"] == 1140.0
    assert res_overrun["is_within_incentive_range"] is True


def test_validate_cpif_cost_sharing_and_fee_bounds_capped_at_max_fee():
    """> Ahorro fuerte: fee crudo supera maximum_fee -> capped y final == max."""
    from backend.schemas.projects import validate_cpif_cost_sharing_and_fee_bounds

    res = validate_cpif_cost_sharing_and_fee_bounds(
        1000.0, 100.0, 60.0, 150.0, 50.0, 50.0, 700.0
    )
    assert res["cost_variance"] == 300.0
    assert res["raw_calculated_fee"] == 250.0
    assert res["final_fee"] == 150.0
    assert res["is_capped_at_max_fee"] is True
    assert res["is_floored_at_min_fee"] is False
    assert res["total_reimbursed_price"] == 850.0
    assert res["is_within_incentive_range"] is False

    # Un ahorro algo menor pero aún sobre el borde (raw > max) también queda capped.
    edge = validate_cpif_cost_sharing_and_fee_bounds(
        1000.0, 100.0, 60.0, 150.0, 50.0, 50.0, 700.5
    )
    assert edge["raw_calculated_fee"] == 249.75
    assert edge["is_capped_at_max_fee"] is True


def test_validate_cpif_cost_sharing_and_fee_bounds_floored_at_min_fee():
    """> Sobrecosto severo: fee crudo cae bajo minimum_fee -> floored y final == min."""
    from backend.schemas.projects import validate_cpif_cost_sharing_and_fee_bounds

    res = validate_cpif_cost_sharing_and_fee_bounds(
        1000.0, 100.0, 60.0, 150.0, 50.0, 50.0, 2200.0
    )
    assert res["cost_variance"] == -1200.0
    assert res["raw_calculated_fee"] == -500.0
    assert res["final_fee"] == 60.0
    assert res["is_floored_at_min_fee"] is True
    assert res["is_capped_at_max_fee"] is False
    assert res["total_reimbursed_price"] == 2260.0
    assert res["pessimistic_range_cost"] == 1080.0
    assert res["is_within_incentive_range"] is False


def test_validate_cpif_cost_sharing_and_fee_bounds_value_errors():
    """ValueError: reparto != 100%, banda desordenada, costos <= 0, bool/NaN."""
    from backend.schemas.projects import validate_cpif_cost_sharing_and_fee_bounds

    bad_calls = (
        (1000.0, 100.0, 60.0, 150.0, 60.0, 20.0, 950.0),   # suma 80 != 100
        (1000.0, 100.0, 60.0, 150.0, 90.0, 20.0, 950.0),   # suma 110 != 100
        (1000.0, 100.0, 120.0, 150.0, 50.0, 50.0, 950.0),  # minimum > target fee
        (1000.0, 100.0, 60.0, 90.0, 50.0, 50.0, 950.0),    # target > maximum fee
        (1000.0, 100.0, -1.0, 150.0, 50.0, 50.0, 950.0),   # minimum < 0
        (0.0, 100.0, 60.0, 150.0, 50.0, 50.0, 950.0),      # target_cost <= 0
        (1000.0, 100.0, 60.0, 150.0, 50.0, 50.0, 0.0),     # actual_cost <= 0
        (1000.0, 100.0, 60.0, 150.0, 0.0, 100.0, 950.0),   # buyer share <= 0
        (1000.0, 100.0, 60.0, 150.0, 100.0, 0.0, 950.0),   # seller share <= 0
        (True, 100.0, 60.0, 150.0, 50.0, 50.0, 950.0),     # bool
        (1000.0, True, 60.0, 150.0, 50.0, 50.0, 950.0),
        (float("nan"), 100.0, 60.0, 150.0, 50.0, 50.0, 950.0),
        (float("inf"), 100.0, 60.0, 150.0, 50.0, 50.0, 950.0),
    )
    for args in bad_calls:
        with pytest.raises(ValueError):
            validate_cpif_cost_sharing_and_fee_bounds(*args)


def test_validate_three_point_pert_skew_and_confidence_band_reliable():
    """Estimación de tres valores balanceada con bajo coeficiente de variación -> is_estimate_reliable=True."""
    from backend.schemas.projects import (
        validate_three_point_pert_skew_and_confidence_band,
    )

    res = validate_three_point_pert_skew_and_confidence_band(
        optimistic=8.0,
        most_likely=10.0,
        pessimistic=14.0,
        max_cv_pct=25.0,
    )
    assert res == {
        "pert_expected": 10.33,
        "triangular_expected": 10.67,
        "standard_deviation": 1.0,
        "variance": 1.0,
        "coefficient_of_variation_pct": 9.68,
        "confidence_68_band": (9.33, 11.33),
        "confidence_95_band": (8.33, 12.33),
        "excessive_uncertainty_detected": False,
        "severe_right_skew_detected": False,
        "is_estimate_reliable": True,
    }


def test_validate_three_point_pert_skew_and_confidence_band_excessive_uncertainty():
    """Coeficiente de variación superior a max_cv_pct dispara excessive_uncertainty_detected=True."""
    from backend.schemas.projects import (
        validate_three_point_pert_skew_and_confidence_band,
    )

    res = validate_three_point_pert_skew_and_confidence_band(
        optimistic=10.0,
        most_likely=40.0,
        pessimistic=70.0,
        max_cv_pct=20.0,
    )
    assert res["pert_expected"] == 40.0
    assert res["triangular_expected"] == 40.0
    assert res["standard_deviation"] == 10.0
    assert res["variance"] == 100.0
    assert res["coefficient_of_variation_pct"] == 25.0
    assert res["excessive_uncertainty_detected"] is True
    assert res["severe_right_skew_detected"] is False
    assert res["is_estimate_reliable"] is False


def test_validate_three_point_pert_skew_and_confidence_band_severe_right_skew():
    """Cola derecha desproporcionada (> 2.5x del margen izquierdo) dispara severe_right_skew_detected=True."""
    from backend.schemas.projects import (
        validate_three_point_pert_skew_and_confidence_band,
    )

    res = validate_three_point_pert_skew_and_confidence_band(
        optimistic=18.0,
        most_likely=20.0,
        pessimistic=30.0,
        max_cv_pct=25.0,
    )
    assert res["pert_expected"] == 21.33
    assert res["standard_deviation"] == 2.0
    assert res["coefficient_of_variation_pct"] == 9.38
    assert res["excessive_uncertainty_detected"] is False
    assert res["severe_right_skew_detected"] is True
    assert res["is_estimate_reliable"] is False


def test_validate_three_point_pert_skew_and_confidence_band_value_errors():
    """Rechaza orden inválido (O > M o M > P), valores <= 0, bool o NaN con ValueError."""
    from backend.schemas.projects import (
        validate_three_point_pert_skew_and_confidence_band,
    )

    bad_calls = [
        (0.0, 5.0, 10.0),
        (-2.0, 5.0, 10.0),
        (12.0, 10.0, 15.0),
        (8.0, 16.0, 14.0),
        (8.0, 10.0, 12.0, 0.0),
        (8.0, 10.0, 12.0, -5.0),
        (True, 10.0, 12.0),
        (8.0, float("nan"), 12.0),
        (8.0, 10.0, float("inf")),
    ]
    for args in bad_calls:
        with pytest.raises(ValueError):
            validate_three_point_pert_skew_and_confidence_band(*args)  # type: ignore[arg-type]


def test_validate_deliverable_acceptance_criteria_measurability_compliant():
    """Entregables con criterios >= 15 chars, rol aprobador, método válido y umbral cuantitativo -> measurable True."""
    from backend.schemas.projects import (
        validate_deliverable_acceptance_criteria_measurability,
    )

    deliverables = [
        {
            "deliverable_id": "DEL-01",
            "acceptance_criteria": "Latencia p95 menor a 200ms bajo carga de 500 usuarios concurrentes",
            "verification_method": "test",
            "designated_approver_role": "Arquitecto Líder",
            "has_quantitative_threshold": True,
        },
        {
            "id": "DEL-02",
            "acceptance_criteria": "Manual operativo revisado con 100% de procedimientos firmados por QA",
            "verification_method": "inspection",
            "designated_approver_role": "Líder de Operaciones",
            "has_quantitative_threshold": False,
        },
    ]
    res = validate_deliverable_acceptance_criteria_measurability(deliverables)
    assert res == {
        "total_evaluated": 2,
        "missing_criteria_deliverable_ids": [],
        "invalid_verification_method_deliverable_ids": [],
        "ambiguous_subjective_deliverable_ids": [],
        "is_acceptance_criteria_measurable": True,
    }


def test_validate_deliverable_acceptance_criteria_measurability_missing_and_invalid_method():
    """Criterio corto (< 15 chars), sin rol aprobador o método de verificación fuera de catálogo."""
    from backend.schemas.projects import (
        validate_deliverable_acceptance_criteria_measurability,
    )

    deliverables = [
        {
            "deliverable_id": "DEL-SHORT",
            "acceptance_criteria": "Todo listo",
            "verification_method": "audit",
            "designated_approver_role": "Sponsor",
            "has_quantitative_threshold": True,
        },
        {
            "deliverable_id": "DEL-NO-APPROVER",
            "acceptance_criteria": "Cobertura de pruebas unitarias superior al 90 por ciento",
            "verification_method": "guesswork",
            "designated_approver_role": "   ",
            "has_quantitative_threshold": True,
        },
    ]
    res = validate_deliverable_acceptance_criteria_measurability(deliverables)
    assert res["total_evaluated"] == 2
    assert res["missing_criteria_deliverable_ids"] == [
        "DEL-SHORT",
        "DEL-NO-APPROVER",
    ]
    assert res["invalid_verification_method_deliverable_ids"] == [
        "DEL-NO-APPROVER"
    ]
    assert res["ambiguous_subjective_deliverable_ids"] == []
    assert res["is_acceptance_criteria_measurable"] is False


def test_validate_deliverable_acceptance_criteria_measurability_ambiguous_subjective():
    """Términos subjetivos sin has_quantitative_threshold -> ambiguous_subjective_deliverable_ids."""
    from backend.schemas.projects import (
        validate_deliverable_acceptance_criteria_measurability,
    )

    deliverables = [
        {
            "deliverable_id": "DEL-VAGUE-1",
            "acceptance_criteria": "El sistema debe ser intuitivo, amigable y de buena calidad para el usuario",
            "verification_method": "demonstration",
            "designated_approver_role": "Product Owner",
            "has_quantitative_threshold": False,
        },
        {
            "deliverable_id": "DEL-VAGUE-QUANTIFIED",
            "acceptance_criteria": "Rendimiento óptimo con tiempo de respuesta p99 <= 150ms",
            "verification_method": "analysis",
            "designated_approver_role": "QA Lead",
            "has_quantitative_threshold": True,
        },
    ]
    res = validate_deliverable_acceptance_criteria_measurability(deliverables)
    assert res["total_evaluated"] == 2
    assert res["missing_criteria_deliverable_ids"] == []
    assert res["invalid_verification_method_deliverable_ids"] == []
    assert res["ambiguous_subjective_deliverable_ids"] == ["DEL-VAGUE-1"]
    assert res["is_acceptance_criteria_measurable"] is False


def test_validate_deliverable_acceptance_criteria_measurability_invalid_inputs():
    """Ignora entradas no secuencia o sin id válido."""
    from backend.schemas.projects import (
        validate_deliverable_acceptance_criteria_measurability,
    )

    for bad in (None, "not-a-seq", b"bytes", bytearray(b"123"), [{"id": "  "}, 99]):
        res = validate_deliverable_acceptance_criteria_measurability(bad)
        assert res == {
            "total_evaluated": 0,
            "missing_criteria_deliverable_ids": [],
            "invalid_verification_method_deliverable_ids": [],
            "ambiguous_subjective_deliverable_ids": [],
            "is_acceptance_criteria_measurable": True,
        }


def test_validate_tm_contract_nte_and_rate_card_valid():
    """Contratos T&M con techo NTE, rate card aprobada y signoff -> gobernanza valida."""
    from backend.schemas.projects import validate_tm_contract_not_to_exceed_and_rate_card

    contracts = [
        {
            "contract_id": "TM-1",
            "not_to_exceed_ceiling": 10000.0,
            "cumulative_billed_amount": 5000.0,
            "has_approved_rate_card": True,
            "timesheet_supervisor_signoff_required": True,
        },
        {
            "id": "TM-2",
            "not_to_exceed_ceiling": 2000.0,
            "cumulative_billed_amount": 1699.0,  # burn 84.95% < 85% -> sin breach.
            "has_approved_rate_card": True,
            "timesheet_supervisor_signoff_required": True,
        },
    ]
    res = validate_tm_contract_not_to_exceed_and_rate_card(contracts)
    assert res == {
        "total_evaluated": 2,
        "missing_nte_ceiling_contract_ids": [],
        "uncontrolled_rate_or_timesheet_contract_ids": [],
        "nte_threshold_breach_contract_ids": [],
        "is_tm_contract_governance_valid": True,
    }


def test_validate_tm_contract_nte_missing_and_uncontrolled():
    """Detecta contratos sin techo NTE (<= 0) y sin rate card aprobada o sin signoff."""
    from backend.schemas.projects import validate_tm_contract_not_to_exceed_and_rate_card

    contracts = [
        {"contract_id": "B-1", "not_to_exceed_ceiling": 0.0,
         "has_approved_rate_card": True, "timesheet_supervisor_signoff_required": True},
        {"contract_id": "B-2", "not_to_exceed_ceiling": -500.0,
         "has_approved_rate_card": True, "timesheet_supervisor_signoff_required": True},
        {"contract_id": "B-3", "not_to_exceed_ceiling": 1000.0,
         "cumulative_billed_amount": 100.0,
         "has_approved_rate_card": False, "timesheet_supervisor_signoff_required": True},
        {"contract_id": "B-4", "not_to_exceed_ceiling": 1000.0,
         "cumulative_billed_amount": 100.0,
         "has_approved_rate_card": True, "timesheet_supervisor_signoff_required": False},
        {"contract_id": "B-5", "not_to_exceed_ceiling": 1000.0,
         "cumulative_billed_amount": 100.0,  # ambos controles ausentes (defaults).
        },
    ]
    res = validate_tm_contract_not_to_exceed_and_rate_card(contracts)
    assert res["total_evaluated"] == 5
    assert res["missing_nte_ceiling_contract_ids"] == ["B-1", "B-2"]
    assert res["uncontrolled_rate_or_timesheet_contract_ids"] == ["B-3", "B-4", "B-5"]
    assert res["nte_threshold_breach_contract_ids"] == []
    assert res["is_tm_contract_governance_valid"] is False


def test_validate_tm_contract_nte_threshold_breach_edges():
    """Burn >= umbral (por defecto 85%) marca breach; bajo el umbral no; coercion segura."""
    from backend.schemas.projects import validate_tm_contract_not_to_exceed_and_rate_card

    contracts = [
        # burn exacto 85.0% -> breach (>=).
        {"contract_id": "E-1", "not_to_exceed_ceiling": 1000.0,
         "cumulative_billed_amount": 850.0,
         "has_approved_rate_card": True, "timesheet_supervisor_signoff_required": True},
        # burn 84.9% -> sin breach.
        {"contract_id": "E-2", "not_to_exceed_ceiling": 1000.0,
         "cumulative_billed_amount": 849.0,
         "has_approved_rate_card": True, "timesheet_supervisor_signoff_required": True},
        # burn 89.9% -> breach; ademas coercion de montos invalidos.
        {"contract_id": "E-3", "not_to_exceed_ceiling": "oops",
         "cumulative_billed_amount": "oops",
         "has_approved_rate_card": True, "timesheet_supervisor_signoff_required": True},
    ]
    res = validate_tm_contract_not_to_exceed_and_rate_card(contracts)
    assert res["nte_threshold_breach_contract_ids"] == ["E-1"]
    assert res["missing_nte_ceiling_contract_ids"] == ["E-3"]  # coercion a 0.
    assert res["is_tm_contract_governance_valid"] is False

    # Umbral personalizado mas estricto.
    strict = validate_tm_contract_not_to_exceed_and_rate_card(
        contracts[:2], burn_warning_threshold_pct=50.0
    )
    assert strict["nte_threshold_breach_contract_ids"] == ["E-1", "E-2"]


def test_validate_tm_contract_nte_empty_and_exports():
    """Entradas vacias/None/invalidas + exportacion en __all__."""
    from backend.schemas.projects import (
        validate_tm_contract_not_to_exceed_and_rate_card,
    )
    import backend.schemas.projects as _m

    res_none = validate_tm_contract_not_to_exceed_and_rate_card(None)
    assert res_none == {
        "total_evaluated": 0,
        "missing_nte_ceiling_contract_ids": [],
        "uncontrolled_rate_or_timesheet_contract_ids": [],
        "nte_threshold_breach_contract_ids": [],
        "is_tm_contract_governance_valid": True,
    }
    assert validate_tm_contract_not_to_exceed_and_rate_card("no-seq")["total_evaluated"] == 0
    assert (
        validate_tm_contract_not_to_exceed_and_rate_card(
            ["no-map", {"contract_id": "   "}, {"other_id": "x"}]
        )["total_evaluated"]
        == 0
    )
    assert "validate_tm_contract_not_to_exceed_and_rate_card" in _m.__all__


def test_validate_resource_calendar_overtime_and_blackout_bounds_compliant():
    """Valida asignaciones sin sobretiempo o con sobretiempo autorizado dentro del tope y excepción de blackout aprobada."""
    from backend.schemas.projects import (
        validate_resource_calendar_overtime_and_blackout_bounds,
    )

    allocations = [
        {
            "allocation_id": "CAL-DEV-01",
            "standard_weekly_hours": 40.0,
            "scheduled_weekly_hours": 40.0,
            "overtime_authorized": False,
            "scheduled_during_blackout_or_holiday": False,
        },
        {
            "id": "CAL-SRE-02",
            "standard_weekly_hours": 40.0,
            "scheduled_weekly_hours": 48.0,
            "overtime_authorized": True,
            "scheduled_during_blackout_or_holiday": True,
            "change_freeze_exception_approved": True,
        },
    ]
    res = validate_resource_calendar_overtime_and_blackout_bounds(
        allocations, max_weekly_overtime_hours=10.0
    )
    assert res == {
        "total_evaluated": 2,
        "unauthorized_overtime_allocation_ids": [],
        "excessive_overtime_cap_allocation_ids": [],
        "blackout_violation_allocation_ids": [],
        "is_resource_calendar_compliant": True,
    }


def test_validate_resource_calendar_unauthorized_and_excessive_overtime():
    """Detecta sobretiempo sin autorización y horas que superan el tope semanal o son <= 0."""
    from backend.schemas.projects import (
        validate_resource_calendar_overtime_and_blackout_bounds,
    )

    allocations = [
        {
            "allocation_id": "CAL-UNAUTH-OT",
            "standard_weekly_hours": 40.0,
            "scheduled_weekly_hours": 45.0,
            "overtime_authorized": False,
        },
        {
            "allocation_id": "CAL-EXCESS-OT",
            "standard_weekly_hours": 40.0,
            "scheduled_weekly_hours": 56.0,
            "overtime_authorized": True,
        },
        {
            "allocation_id": "CAL-ZERO-HRS",
            "standard_weekly_hours": 40.0,
            "scheduled_weekly_hours": 0.0,
        },
    ]
    res = validate_resource_calendar_overtime_and_blackout_bounds(
        allocations, max_weekly_overtime_hours=10.0
    )
    assert res["total_evaluated"] == 3
    assert res["unauthorized_overtime_allocation_ids"] == ["CAL-UNAUTH-OT"]
    assert res["excessive_overtime_cap_allocation_ids"] == [
        "CAL-EXCESS-OT",
        "CAL-ZERO-HRS",
    ]
    assert res["blackout_violation_allocation_ids"] == []
    assert res["is_resource_calendar_compliant"] is False


def test_validate_resource_calendar_blackout_violation():
    """Detecta trabajo programado en ventana de blackout o festivo sin excepción aprobada."""
    from backend.schemas.projects import (
        validate_resource_calendar_overtime_and_blackout_bounds,
    )

    allocations = [
        {
            "allocation_id": "CAL-BLACKOUT-BREACH",
            "standard_weekly_hours": 40.0,
            "scheduled_weekly_hours": 32.0,
            "scheduled_during_blackout_or_holiday": True,
            "change_freeze_exception_approved": False,
        }
    ]
    res = validate_resource_calendar_overtime_and_blackout_bounds(allocations)
    assert res["total_evaluated"] == 1
    assert res["unauthorized_overtime_allocation_ids"] == []
    assert res["excessive_overtime_cap_allocation_ids"] == []
    assert res["blackout_violation_allocation_ids"] == ["CAL-BLACKOUT-BREACH"]
    assert res["is_resource_calendar_compliant"] is False


def test_validate_resource_calendar_invalid_inputs_and_export():
    """Ignora entradas no secuencia o sin allocation_id válido y verifica exportación en __all__."""
    import backend.schemas.projects as _m
    from backend.schemas.projects import (
        validate_resource_calendar_overtime_and_blackout_bounds,
    )

    assert "validate_resource_calendar_overtime_and_blackout_bounds" in _m.__all__
    for bad in (None, "not-a-seq", b"bytes", bytearray(b"123"), [{"allocation_id": "  "}, 42]):
        assert validate_resource_calendar_overtime_and_blackout_bounds(bad) == {
            "total_evaluated": 0,
            "unauthorized_overtime_allocation_ids": [],
            "excessive_overtime_cap_allocation_ids": [],
            "blackout_violation_allocation_ids": [],
            "is_resource_calendar_compliant": True,
        }



def test_validate_fpif_share_ratio_and_pta_compliant():
    """FPIF con share ratio 80/20, ceiling >= target_price y PTA calculado."""
    from backend.schemas.projects import validate_fpif_share_ratio_and_point_of_total_assumption

    contracts = [
        {
            "contract_id": "F-1",
            "target_cost": 1000.0,
            "target_fee": 100.0,
            "ceiling_price": 1200.0,
            "buyer_share_pct": 80.0,
            "seller_share_pct": 20.0,
            "actual_or_forecast_cost": 1100.0,
        }
    ]
    res = validate_fpif_share_ratio_and_point_of_total_assumption(contracts)
    assert res == {
        "total_contracts": 1,
        "invalid_share_ratio_contract_ids": [],
        "invalid_ceiling_or_target_contract_ids": [],
        "degenerate_pta_contract_ids": [],
        "pta_breached_contract_ids": [],
        # PTA = target_cost + (ceiling - target_price)/buyer_share_ratio = 1000 + 100/0.8.
        "computed_pta_by_contract": {"F-1": 1125.0},
        "is_fpif_governance_valid": True,
    }


def test_validate_fpif_share_ratio_and_pta_invalid_share_ratios():
    """Share ratios que no suman 100% o con una parte <= 0 quedan marcados."""
    from backend.schemas.projects import validate_fpif_share_ratio_and_point_of_total_assumption

    contracts = [
        {"contract_id": "S-1", "target_cost": 1000.0, "target_fee": 100.0,
         "ceiling_price": 1200.0, "buyer_share_pct": 70.0, "seller_share_pct": 20.0},
        {"contract_id": "S-2", "target_cost": 1000.0, "target_fee": 100.0,
         "ceiling_price": 1200.0, "buyer_share_pct": 100.0, "seller_share_pct": 0.0},
        # Suma 99.995 -> dentro de la tolerancia 0.01 -> ratio valido.
        {"contract_id": "S-3", "target_cost": 1000.0, "target_fee": 100.0,
         "ceiling_price": 1200.0, "buyer_share_pct": 79.995, "seller_share_pct": 20.0},
    ]
    res = validate_fpif_share_ratio_and_point_of_total_assumption(contracts)
    assert res["total_contracts"] == 3
    assert res["invalid_share_ratio_contract_ids"] == ["S-1", "S-2"]
    assert res["invalid_ceiling_or_target_contract_ids"] == []
    assert res["is_fpif_governance_valid"] is False


def test_validate_fpif_share_ratio_and_pta_invalid_ceiling_and_degenerate():
    """target_cost <= 0, target_fee < 0, ceiling < target_price y PTA degenerado."""
    from backend.schemas.projects import validate_fpif_share_ratio_and_point_of_total_assumption

    contracts = [
        {"contract_id": "C-1", "target_cost": 0.0, "target_fee": 100.0,
         "ceiling_price": 1100.0, "buyer_share_pct": 80.0, "seller_share_pct": 20.0},
        {"contract_id": "C-2", "target_cost": 1000.0, "target_fee": -50.0,
         "ceiling_price": 1200.0, "buyer_share_pct": 80.0, "seller_share_pct": 20.0},
        {"contract_id": "C-3", "target_cost": 1000.0, "target_fee": 100.0,
         "ceiling_price": 1090.0, "buyer_share_pct": 80.0, "seller_share_pct": 20.0},
        # PTA degenerado: buyer 200%: pta = 1000 + 100/2.0 = 1050 < ceiling 1200 y > target_cost.
        # Para degenerate usar buyer que empuje pta fuera de [target_cost, ceiling]:
        {"contract_id": "C-4", "target_cost": 1000.0, "target_fee": 0.0,
         "ceiling_price": 1000.0, "buyer_share_pct": 400.0, "seller_share_pct": -300.0},
    ]
    res = validate_fpif_share_ratio_and_point_of_total_assumption(contracts)
    assert res["invalid_ceiling_or_target_contract_ids"] == ["C-1", "C-2", "C-3"]
    # C-4: ratio invalido tambien (seller negativo); pta = 1000 + (1000-1000)/4 = 1000.
    assert res["invalid_share_ratio_contract_ids"] == ["C-4"]
    # C-4: pta == 1000 == target_cost -> no degenerado por pta < target_cost (no estricto)
    # pero actual 0 no breach.
    assert res["computed_pta_by_contract"]["C-4"] == 1000.0
    assert res["is_fpif_governance_valid"] is False


def test_validate_fpif_share_ratio_and_pta_breach_and_scope():
    """Breach del PTA: costo real sobre el PTA; montos invalidos y entradas vacias."""
    from backend.schemas.projects import validate_fpif_share_ratio_and_point_of_total_assumption
    import backend.schemas.projects as _m

    contracts = [
        {"contract_id": "F-1", "target_cost": 1000.0, "target_fee": 100.0,
         "ceiling_price": 1200.0, "buyer_share_pct": 80.0, "seller_share_pct": 20.0,
         "actual_or_forecast_cost": 1125.0},  # == PTA -> sin breach (comparacion estricta).
        {"contract_id": "F-2", "target_cost": 1000.0, "target_fee": 100.0,
         "ceiling_price": 1200.0, "buyer_share_pct": 80.0, "seller_share_pct": 20.0,
         "actual_or_forecast_cost": 1125.01},  # > PTA -> breach.
        {"contract_id": "B-1", "target_cost": "oops", "target_fee": None,
         "ceiling_price": "x", "buyer_share_pct": "y", "seller_share_pct": "z"},
    ]
    res = validate_fpif_share_ratio_and_point_of_total_assumption(contracts)
    assert res["total_contracts"] == 3
    assert res["pta_breached_contract_ids"] == ["F-2"]
    assert res["computed_pta_by_contract"] == {"F-1": 1125.0, "F-2": 1125.0}
    assert res["invalid_ceiling_or_target_contract_ids"] == ["B-1"]
    assert res["is_fpif_governance_valid"] is False

    empty = validate_fpif_share_ratio_and_point_of_total_assumption(None)
    assert empty == {
        "total_contracts": 0,
        "invalid_share_ratio_contract_ids": [],
        "invalid_ceiling_or_target_contract_ids": [],
        "degenerate_pta_contract_ids": [],
        "pta_breached_contract_ids": [],
        "computed_pta_by_contract": {},
        "is_fpif_governance_valid": True,
    }
    assert validate_fpif_share_ratio_and_point_of_total_assumption("no-seq")["total_contracts"] == 0
    assert (
        validate_fpif_share_ratio_and_point_of_total_assumption(
            ["no-map", {"contract_id": "   "}, 42]
        )["total_contracts"]
        == 0
    )
    assert "validate_fpif_share_ratio_and_point_of_total_assumption" in _m.__all__


def test_validate_ccpm_feeding_and_project_buffer_sizing_compliant():
    """Buffers CCPM dentro de ratio 0.20..0.60 y fuera de zona roja sin mitigación cumplen §6.5."""
    from backend.schemas.projects import (
        validate_ccpm_feeding_and_project_buffer_sizing,
    )

    buffers = [
        {
            "buffer_id": "BUF-PROJ-01",
            "buffer_type": "project",
            "feeding_chain_duration_days": 100.0,
            "buffer_size_days": 35.0,
            "buffer_consumed_days": 14.0,  # 40% consumed, progress 50% -> limit 65%
            "chain_progress_pct": 50.0,
            "recovery_plan_triggered": False,
        },
        {
            "buffer_id": "BUF-FEED-01",
            "buffer_type": "Feeding",
            "feeding_chain_duration_days": 40.0,
            "buffer_size_days": 12.0,
            "buffer_consumed_days": 10.0,  # 83.3% > limit 72%, pero plan activado
            "chain_progress_pct": 60.0,
            "recovery_plan_triggered": True,
        },
        {
            "buffer_id": "BUF-RES-01",
            "buffer_type": "resource",
            "feeding_chain_duration_days": 50.0,
            "buffer_size_days": 5.0,  # resource buffer no aplica ratio 0.20..0.60
            "buffer_consumed_days": 1.0,
            "chain_progress_pct": 20.0,
        },
    ]
    res = validate_ccpm_feeding_and_project_buffer_sizing(buffers)
    assert res == {
        "total_buffers": 3,
        "invalid_buffer_definition_ids": [],
        "misaligned_buffer_sizing_ids": [],
        "unmitigated_fever_chart_red_zone_ids": [],
        "is_ccpm_buffer_governance_valid": True,
    }


def test_validate_ccpm_buffer_misaligned_sizing_ratios():
    """Detecta buffers project o feeding subdimensionados (< 0.20) o sobredimensionados (> 0.60)."""
    from backend.schemas.projects import (
        validate_ccpm_feeding_and_project_buffer_sizing,
    )

    buffers = [
        {
            "buffer_id": "BUF-TOO-SMALL",
            "buffer_type": "project",
            "feeding_chain_duration_days": 100.0,
            "buffer_size_days": 15.0,  # 0.15 < 0.20
            "buffer_consumed_days": 2.0,
            "chain_progress_pct": 30.0,
        },
        {
            "buffer_id": "BUF-TOO-LARGE",
            "buffer_type": "feeding",
            "feeding_chain_duration_days": 50.0,
            "buffer_size_days": 35.0,  # 0.70 > 0.60
            "buffer_consumed_days": 5.0,
            "chain_progress_pct": 30.0,
        },
    ]
    res = validate_ccpm_feeding_and_project_buffer_sizing(buffers)
    assert res["total_buffers"] == 2
    assert res["misaligned_buffer_sizing_ids"] == [
        "BUF-TOO-SMALL",
        "BUF-TOO-LARGE",
    ]
    assert res["unmitigated_fever_chart_red_zone_ids"] == []
    assert res["is_ccpm_buffer_governance_valid"] is False


def test_validate_ccpm_buffer_unmitigated_fever_chart_red_zone():
    """Detecta incursión en Zona Roja del Fever Chart (consumption_pct > 30 + 0.70 * progress) sin plan de recuperación."""
    from backend.schemas.projects import (
        validate_ccpm_feeding_and_project_buffer_sizing,
    )

    buffers = [
        {
            "buffer_id": "BUF-RED-UNMITIGATED",
            "buffer_type": "project",
            "feeding_chain_duration_days": 80.0,
            "buffer_size_days": 24.0,  # ratio 0.30
            "buffer_consumed_days": 15.0,  # 62.5% > 30 + 0.70*20 = 44%
            "chain_progress_pct": 20.0,
            "recovery_plan_triggered": False,
        }
    ]
    res = validate_ccpm_feeding_and_project_buffer_sizing(buffers)
    assert res["misaligned_buffer_sizing_ids"] == []
    assert res["unmitigated_fever_chart_red_zone_ids"] == [
        "BUF-RED-UNMITIGATED"
    ]
    assert res["is_ccpm_buffer_governance_valid"] is False


def test_validate_ccpm_buffer_invalid_definitions_and_export():
    """Detecta tipos o duraciones inválidas, ignora entradas no secuencia y verifica __all__."""
    import backend.schemas.projects as _m
    from backend.schemas.projects import (
        validate_ccpm_feeding_and_project_buffer_sizing,
    )

    assert "validate_ccpm_feeding_and_project_buffer_sizing" in _m.__all__
    res = validate_ccpm_feeding_and_project_buffer_sizing(
        [
            {
                "buffer_id": "BUF-BAD-TYPE",
                "buffer_type": "contingency",
                "feeding_chain_duration_days": 50.0,
                "buffer_size_days": 15.0,
            },
            {
                "buffer_id": "BUF-ZERO-SIZE",
                "buffer_type": "project",
                "feeding_chain_duration_days": 50.0,
                "buffer_size_days": 0.0,
            },
        ]
    )
    assert res["invalid_buffer_definition_ids"] == [
        "BUF-BAD-TYPE",
        "BUF-ZERO-SIZE",
    ]
    assert res["is_ccpm_buffer_governance_valid"] is False

    for bad in (None, "not-a-seq", b"bytes", [{"buffer_id": "  "}]):
        assert validate_ccpm_feeding_and_project_buffer_sizing(bad) == {
            "total_buffers": 0,
            "invalid_buffer_definition_ids": [],
            "misaligned_buffer_sizing_ids": [],
            "unmitigated_fever_chart_red_zone_ids": [],
            "is_ccpm_buffer_governance_valid": True,
        }


def test_validate_wbs_hundred_percent_rule_decomposition_compliant():
    """Descomposición WBS 100% exacta, con >= 2 hijos y entregables mutuamente excluyentes cumple §5.4."""
    from backend.schemas.projects import (
        validate_wbs_hundred_percent_rule_decomposition,
    )

    nodes = [
        {
            "parent_code": "1.0",
            "parent_planned_effort_hours": 200.0,
            "parent_planned_budget": 50000.0,
            "children": [
                {
                    "child_code": "1.1",
                    "effort_hours": 120.0,
                    "budget": 30000.0,
                    "scope_deliverable_key": "DLV-API-BACKEND",
                },
                {
                    "child_code": "1.2",
                    "effort_hours": 80.0,
                    "budget": 20000.0,
                    "scope_deliverable_key": "DLV-UI-PORTAL",
                },
            ],
        }
    ]
    res = validate_wbs_hundred_percent_rule_decomposition(nodes)
    assert res == {
        "total_parent_nodes": 1,
        "invalid_or_undecomposed_parent_codes": [],
        "single_child_redundant_decomposition_codes": [],
        "hundred_percent_rule_violation_codes": [],
        "overlapping_child_scope_codes": [],
        "is_wbs_hundred_percent_rule_valid": True,
    }


def test_validate_wbs_hundred_percent_rule_sum_mismatch_and_single_child():
    """Detecta suma de hijos distinta al 100% del padre y descomposición redundante de hijo único."""
    from backend.schemas.projects import (
        validate_wbs_hundred_percent_rule_decomposition,
    )

    nodes = [
        {
            "parent_code": "2.0",
            "parent_planned_effort_hours": 100.0,
            "parent_planned_budget": 25000.0,
            "children": [
                {
                    "child_code": "2.1",
                    "effort_hours": 50.0,
                    "budget": 12000.0,
                    "scope_deliverable_key": "DLV-A",
                },
                {
                    "child_code": "2.2",
                    "effort_hours": 40.0,  # Suma 90 != 100
                    "budget": 13000.0,
                    "scope_deliverable_key": "DLV-B",
                },
            ],
        },
        {
            "parent_code": "3.0",
            "parent_planned_effort_hours": 60.0,
            "parent_planned_budget": 15000.0,
            "children": [
                {
                    "child_code": "3.1",
                    "effort_hours": 60.0,
                    "budget": 15000.0,
                    "scope_deliverable_key": "DLV-SINGLE",
                }
            ],
        },
    ]
    res = validate_wbs_hundred_percent_rule_decomposition(nodes)
    assert res["total_parent_nodes"] == 2
    assert res["hundred_percent_rule_violation_codes"] == ["2.0"]
    assert res["single_child_redundant_decomposition_codes"] == ["3.0"]
    assert res["is_wbs_hundred_percent_rule_valid"] is False


def test_validate_wbs_hundred_percent_rule_overlapping_child_scope():
    """Detecta solapamiento de entregables (scope_deliverable_key duplicado entre hermanos)."""
    from backend.schemas.projects import (
        validate_wbs_hundred_percent_rule_decomposition,
    )

    nodes = [
        {
            "parent_code": "4.0",
            "parent_planned_effort_hours": 100.0,
            "parent_planned_budget": 10000.0,
            "children": [
                {
                    "child_code": "4.1",
                    "effort_hours": 50.0,
                    "budget": 5000.0,
                    "scope_deliverable_key": "DLV-SHARED-MODULE",
                },
                {
                    "child_code": "4.2",
                    "effort_hours": 50.0,
                    "budget": 5000.0,
                    "scope_deliverable_key": "dlv-shared-module",
                },
            ],
        }
    ]
    res = validate_wbs_hundred_percent_rule_decomposition(nodes)
    assert res["overlapping_child_scope_codes"] == ["4.0"]
    assert res["hundred_percent_rule_violation_codes"] == []
    assert res["is_wbs_hundred_percent_rule_valid"] is False


def test_validate_wbs_hundred_percent_rule_invalid_parents_and_export():
    """Detecta nodos padre sin hijos o con presupuesto/esfuerzo <= 0 y verifica exportación en __all__."""
    import backend.schemas.projects as _m
    from backend.schemas.projects import (
        validate_wbs_hundred_percent_rule_decomposition,
    )

    assert "validate_wbs_hundred_percent_rule_decomposition" in _m.__all__
    res = validate_wbs_hundred_percent_rule_decomposition(
        [
            {
                "parent_code": "5.0-EMPTY",
                "parent_planned_effort_hours": 80.0,
                "parent_planned_budget": 8000.0,
                "children": [],
            }
        ]
    )
    assert res["invalid_or_undecomposed_parent_codes"] == ["5.0-EMPTY"]
    assert res["is_wbs_hundred_percent_rule_valid"] is False

    for bad in (None, "not-a-seq", b"bytes", [{"parent_code": "  "}]):
        assert validate_wbs_hundred_percent_rule_decomposition(bad) == {
            "total_parent_nodes": 0,
            "invalid_or_undecomposed_parent_codes": [],
            "single_child_redundant_decomposition_codes": [],
            "hundred_percent_rule_violation_codes": [],
            "overlapping_child_scope_codes": [],
            "is_wbs_hundred_percent_rule_valid": True,
        }


def test_validate_emv_decision_tree_and_contingency_reserve_compliant():
    """Nodo valido con EMV mixto negativo y reserva suficiente."""
    from backend.schemas.projects import (
        validate_emv_decision_tree_and_contingency_reserve,
    )

    res = validate_emv_decision_tree_and_contingency_reserve(
        [
            {
                "node_id": "ND-TREE",
                "branches": [
                    {"branch_id": "B1", "probability": 0.4, "monetary_impact": -25000.0},
                    {"branch_id": "B2", "probability": 0.6, "monetary_impact": 15000.0},
                ],
            },
        ],
        allocated_contingency_reserve=15000.0,
    )
    assert res == {
        "total_nodes": 1,
        "emv_by_node": {"ND-TREE": -1000.0},
        "total_positive_threat_emv": 0.0,
        "reserve_shortfall": 0.0,
        "has_contingency_reserve_shortfall": False,
        "empty_branch_node_ids": [],
        "invalid_probability_range_node_ids": [],
        "unnormalized_probability_sum_node_ids": [],
        "is_emv_tree_valid": True,
    }


def test_validate_emv_decision_tree_and_contingency_reserve_findings():
    """Nodos con ramas vacias, probabilidad fuera de rango y suma no normalizada."""
    from backend.schemas.projects import (
        validate_emv_decision_tree_and_contingency_reserve,
    )

    res = validate_emv_decision_tree_and_contingency_reserve(
        [
            {"node_id": "ND-EMPTY", "branches": []},
            {
                "node_id": "ND-RANGE",
                "branches": [
                    {"branch_id": "B1", "probability": 1.5, "monetary_impact": 100.0},
                ],
            },
            {
                "node_id": "ND-SUM",
                "branches": [
                    {"branch_id": "B1", "probability": 0.5, "monetary_impact": 100.0},
                    {"branch_id": "B2", "probability": 0.2, "monetary_impact": 50.0},
                ],
            },
            {
                "node_id": "ND-POS",
                "branches": [
                    {"branch_id": "B1", "probability": 0.5, "monetary_impact": 40000.0},
                    {"branch_id": "B2", "probability": 0.5, "monetary_impact": -5000.0},
                ],
            },
        ],
        allocated_contingency_reserve=10000.0,
    )
    assert res["total_nodes"] == 4
    assert res["empty_branch_node_ids"] == ["ND-EMPTY"]
    assert res["invalid_probability_range_node_ids"] == ["ND-RANGE"]
    # La regla de suma normalizada aplica a todo nodo con ramas (tambien ND-RANGE).
    assert res["unnormalized_probability_sum_node_ids"] == ["ND-RANGE", "ND-SUM"]
    assert res["emv_by_node"] == {"ND-POS": 17500.0}
    assert res["total_positive_threat_emv"] == 17500.0
    assert res["reserve_shortfall"] == 7500.0
    assert res["has_contingency_reserve_shortfall"] is True
    assert res["is_emv_tree_valid"] is False


def test_validate_emv_decision_tree_and_contingency_reserve_shortfall_boundary():
    """Borde del shortfall: reserva justo en el limite (0.01) y impactos positivos puros."""
    from backend.schemas.projects import (
        validate_emv_decision_tree_and_contingency_reserve as fn,
    )

    node = {
        "node_id": "ND-TRE",
        "branches": [
            {"branch_id": "B1", "probability": 0.5, "monetary_impact": 40000.02},
            {"branch_id": "B2", "probability": 0.5, "monetary_impact": 0.0},
        ],
    }
    # EMV = 20000.01, shortfall = 0.01 -> NO es shortfall (> 0.01, no >=).
    at_limit = fn([dict(node)], allocated_contingency_reserve=20000.0)
    assert at_limit["reserve_shortfall"] == 0.01
    assert at_limit["has_contingency_reserve_shortfall"] is False
    assert at_limit["is_emv_tree_valid"] is True

    beyond = fn([dict(node)], allocated_contingency_reserve=20000.0)
    assert beyond["total_positive_threat_emv"] == 20000.01

    shortfall = fn([dict(node)], allocated_contingency_reserve=20000.0)
    # Con reserva 0.00 el shortfall rebasa el umbral.
    no_reserve = fn(
        [{**node, "branches": [{"branch_id": "B1", "probability": 0.5, "monetary_impact": 40000.02},
                               {"branch_id": "B2", "probability": 0.5, "monetary_impact": 0.0}]}],
        allocated_contingency_reserve=0.0,
    )
    assert no_reserve["reserve_shortfall"] == 20000.01
    assert no_reserve["has_contingency_reserve_shortfall"] is True
    assert no_reserve["is_emv_tree_valid"] is False


def test_validate_emv_decision_tree_and_contingency_reserve_empty_and_export():
    """Entrada vacia/None + entrada en __all__ y firma con kwarg obligatorio."""
    from backend.schemas.projects import (
        validate_emv_decision_tree_and_contingency_reserve as fn,
    )
    import backend.schemas.projects as mod

    empty = fn([])
    assert empty["total_nodes"] == 0
    assert empty["emv_by_node"] == {}
    assert empty["is_emv_tree_valid"] is True

    assert fn(None)["is_emv_tree_valid"] is True

    # allocated_contingency_reserve es kwarg-only.
    try:
        fn([], 100.0)  # type: ignore[misc]
        raised = False
    except TypeError:
        raised = True
    assert raised is True

    assert "validate_emv_decision_tree_and_contingency_reserve" in mod.__all__


def test_validate_parametric_estimation_model_fit_valid():
    """Acepta modelo paramétrico con R², grados de libertad y MAPE dentro de umbrales PMBOK §6.4 / §7.2."""
    import backend.schemas.projects as mod
    from backend.schemas.projects import validate_parametric_estimation_model_fit

    assert "validate_parametric_estimation_model_fit" in mod.__all__
    res = validate_parametric_estimation_model_fit(
        r_squared=0.85,
        sample_size=22,
        independent_variables_count=2,
        mean_absolute_percentage_error_pct=12.5,
        extrapolation_beyond_historical_range=True,
        scale_adjustment_documented=True,
    )
    assert res == {
        "r_squared": 0.85,
        "adjusted_r_squared": round(1.0 - ((1.0 - 0.85) * 21 / 19), 4),
        "degrees_of_freedom": 19,
        "mean_absolute_percentage_error_pct": 12.5,
        "extrapolation_beyond_historical_range": True,
        "is_valid": True,
    }


def test_validate_parametric_estimation_model_fit_insufficient_degrees_of_freedom():
    """Rechaza regresión paramétrica sin grados de libertad suficientes (sample_size < k + 2)."""
    import pytest
    from backend.schemas.projects import validate_parametric_estimation_model_fit

    with pytest.raises(ValueError, match="muestra histórica insuficiente|grados de libertad"):
        validate_parametric_estimation_model_fit(
            r_squared=0.90,
            sample_size=3,
            independent_variables_count=2,
            mean_absolute_percentage_error_pct=10.0,
        )


def test_validate_parametric_estimation_model_fit_poor_r_squared_or_high_mape():
    """Rechaza modelos con R² inferior al mínimo o MAPE superior al máximo permitido."""
    import pytest
    from backend.schemas.projects import validate_parametric_estimation_model_fit

    with pytest.raises(ValueError, match="ajuste estadístico insuficiente"):
        validate_parametric_estimation_model_fit(
            r_squared=0.55,
            sample_size=15,
            independent_variables_count=1,
            mean_absolute_percentage_error_pct=15.0,
            min_r_squared=0.70,
        )

    with pytest.raises(ValueError, match="ajuste estadístico insuficiente"):
        validate_parametric_estimation_model_fit(
            r_squared=0.82,
            sample_size=15,
            independent_variables_count=1,
            mean_absolute_percentage_error_pct=32.0,
            max_mape_pct=25.0,
        )


def test_validate_parametric_estimation_model_fit_undocumented_extrapolation_and_bounds():
    """Rechaza extrapolación fuera del rango histórico sin ajuste de escala documentado o parámetros fuera de rango."""
    import pytest
    from backend.schemas.projects import validate_parametric_estimation_model_fit

    with pytest.raises(ValueError, match="ajuste de escala"):
        validate_parametric_estimation_model_fit(
            r_squared=0.88,
            sample_size=20,
            independent_variables_count=2,
            mean_absolute_percentage_error_pct=11.0,
            extrapolation_beyond_historical_range=True,
            scale_adjustment_documented=False,
        )

    with pytest.raises(ValueError):
        validate_parametric_estimation_model_fit(
            r_squared=1.2,
            sample_size=20,
            independent_variables_count=1,
            mean_absolute_percentage_error_pct=10.0,
        )



def test_validate_schedule_compression_fast_tracking_and_crashing_valid():
    """Compresion valida con fast-tracking documentado y crashing razonable."""
    import pytest

    from backend.schemas.projects import (
        validate_schedule_compression_fast_tracking_and_crashing as fn,
    )

    res = fn(30.0, 27.0, 20.0, 3000.0, 50000.0, rework_risk_contingency_documented=True)
    assert res == {
        "duration_reduction_days": 3.0,
        "compression_ratio_pct": 10.0,
        "fast_tracked_overlap_pct": 20.0,
        "crashing_cost_ratio_pct": 6.0,
        "crash_cost_per_day_saved": 1000.0,
        "is_valid": True,
    }

    # Sin overlap ni crashing: costo por dia guardado 0.0 y ratio crashing 0.0.
    no_cost = fn(30.0, 25.0, 0.0, 0.0, 50000.0)
    assert no_cost["duration_reduction_days"] == 5.0
    assert no_cost["compression_ratio_pct"] == 16.67
    assert no_cost["crash_cost_per_day_saved"] == 0.0
    assert no_cost["crashing_cost_ratio_pct"] == 0.0
    assert no_cost["is_valid"] is True


def test_validate_schedule_compression_fast_tracking_and_crashing_overlap_rules():
    """Contingencia exigida con overlap > 0; rango [0,100] y max_overlap_pct."""
    import pytest

    from backend.schemas.projects import (
        validate_schedule_compression_fast_tracking_and_crashing as fn,
    )

    # Overlap > 0 sin contingencia documentada -> ValueError.
    with pytest.raises(ValueError):
        fn(30.0, 27.0, 20.0, 0.0, 50000.0)

    # Overlap fuera de [0, 100].
    with pytest.raises(ValueError):
        fn(30.0, 27.0, -1.0, 0.0, 50000.0)
    with pytest.raises(ValueError):
        fn(30.0, 27.0, 101.0, 0.0, 50000.0)

    # Overlap > max_overlap_pct default 33.3 -> ValueError.
    with pytest.raises(ValueError):
        fn(30.0, 27.0, 33.4, 0.0, 50000.0)

    # Borde inclusive: 33.3 es valido con contingencia.
    edge = fn(30.0, 27.0, 33.3, 0.0, 50000.0, rework_risk_contingency_documented=True)
    assert edge["is_valid"] is True

    # max_overlap_pct custom (50.0) admite 40.0 con contingencia.
    custom = fn(30.0, 27.0, 40.0, 0.0, 50000.0, rework_risk_contingency_documented=True, max_overlap_pct=50.0)
    assert custom["fast_tracked_overlap_pct"] == 40.0
    assert custom["is_valid"] is True


def test_validate_schedule_compression_fast_tracking_and_crashing_crashing_rules():
    """Sobrecosto desproporcionado y crashing sin reduccion efectiva -> ValueError."""
    import pytest

    from backend.schemas.projects import (
        validate_schedule_compression_fast_tracking_and_crashing as fn,
    )

    # (3000/50000)*100 = 6.0, pero con max 5.0 -> ValueError.
    with pytest.raises(ValueError):
        fn(30.0, 27.0, 0.0, 3000.0, 50000.0, max_crashing_cost_ratio_pct=5.0)

    # Ratio 16.0 > default 15.0 -> ValueError (sobrecosto desproporcionado).
    with pytest.raises(ValueError):
        fn(30.0, 27.0, 0.0, 8000.0, 50000.0)

    # Borde inclusive: 15.0 exacto es valido.
    border = fn(30.0, 27.0, 0.0, 7500.0, 50000.0)
    assert border["crashing_cost_ratio_pct"] == 15.0
    assert border["is_valid"] is True

    # Compressed == original con crashing > 0 -> ValueError (sin reduccion efectiva).
    with pytest.raises(ValueError):
        fn(30.0, 30.0, 0.0, 3000.0, 50000.0)


def test_validate_schedule_compression_fast_tracking_and_crashing_domain_valueerrors():
    """ValueErrors de dominio (duracion/compressed/cost/BAC/maxes) y export __all__."""
    import pytest

    from backend.schemas.projects import (
        validate_schedule_compression_fast_tracking_and_crashing as fn,
    )
    import backend.schemas.projects as mod

    invalid_cases = [
        ((0.0, 27.0, 0.0, 0.0, 50000.0), {}),   # original <= 0
        ((30.0, 0.0, 0.0, 0.0, 50000.0), {}),   # compressed <= 0
        ((30.0, 31.0, 0.0, 0.0, 50000.0), {}),  # compressed > original
        ((30.0, 27.0, 0.0, -1.0, 50000.0), {}), # crashing negativo
        ((30.0, 27.0, 0.0, 0.0, 0.0), {}),      # BAC <= 0
        ((30.0, 27.0, 0.0, 0.0, 50000.0), {"max_overlap_pct": 0.0}),
        ((30.0, 27.0, 0.0, 0.0, 50000.0), {"max_overlap_pct": 101.0}),
        ((30.0, 27.0, 0.0, 0.0, 50000.0), {"max_crashing_cost_ratio_pct": 0.0}),
        ((30.0, 27.0, 0.0, 0.0, 50000.0), {"max_crashing_cost_ratio_pct": -2.0}),
    ]
    for args, kwargs in invalid_cases:
        with pytest.raises(ValueError):
            fn(*args, **kwargs)

    # Bloque kwarg-only en rework_risk_contingency_documented.
    with pytest.raises(TypeError):
        fn(30.0, 27.0, 20.0, 0.0, 50000.0, True)  # type: ignore[misc]

    assert "validate_schedule_compression_fast_tracking_and_crashing" in mod.__all__


def test_validate_funding_limit_reconciliation_and_cash_flow_cliff_healthy():
    """Flujo de caja conciliado con colchon de liquidez >= 5% por periodo (PMBOK §7.3, §7.4)."""
    from backend.schemas.projects import (
        validate_funding_limit_reconciliation_and_cash_flow_cliff as fn,
    )

    res = fn(
        [9000.0, 9000.0, 9000.0],
        [10000.0, 10000.0, 10000.0],
        min_liquidity_buffer_pct=5.0,
    )
    assert res == {
        "periods_count": 3,
        "total_planned_expenditure": 27000.0,
        "total_funding_limit": 30000.0,
        "min_period_buffer_pct": 10.0,
        "funding_breach_periods": [],
        "is_valid": True,
    }


def test_validate_funding_limit_reconciliation_and_cash_flow_cliff_breach_and_cr_override():
    """Detecta brecha intermedia de financiamiento o colchon bajo y exige CR fiscal aprobado."""
    import pytest

    from backend.schemas.projects import (
        validate_funding_limit_reconciliation_and_cash_flow_cliff as fn,
    )

    # Brecha en periodo 2 (acumulado exp 22000 > fund 20000) aunque el total cierre (28000 <= 30000)
    with pytest.raises(ValueError, match="Deficit de flujo de caja"):
        fn([10000.0, 12000.0, 6000.0], [10000.0, 10000.0, 10000.0])

    # Con flag activado pero sin CR ID valido sigue fallando
    with pytest.raises(ValueError, match="Deficit de flujo de caja"):
        fn(
            [10000.0, 12000.0, 6000.0],
            [10000.0, 10000.0, 10000.0],
            allow_fiscal_rescheduling_with_cr=True,
            approved_rescheduling_cr_id="   ",
        )

    # Con CR aprobado se permite reprogramacion fiscal y se reportan los periodos en brecha
    res = fn(
        [10000.0, 12000.0, 6000.0],
        [10000.0, 10000.0, 10000.0],
        allow_fiscal_rescheduling_with_cr=True,
        approved_rescheduling_cr_id="CR-FIN-2026-09",
    )
    assert res["funding_breach_periods"] == [2]
    assert res["min_period_buffer_pct"] == -10.0
    assert res["is_valid"] is True


def test_validate_funding_limit_reconciliation_and_cash_flow_cliff_low_buffer_rejection():
    """Rechaza colchon de liquidez inferior al minimo configurado aunque no exista sobregiro."""
    import pytest

    from backend.schemas.projects import (
        validate_funding_limit_reconciliation_and_cash_flow_cliff as fn,
    )

    # Periodo 1 tiene colchon de 2% (< 5% requerido)
    with pytest.raises(ValueError, match="colchon de liquidez insuficiente"):
        fn([9800.0, 8000.0], [10000.0, 10000.0], min_liquidity_buffer_pct=5.0)

    # Con CR de reprogramacion aprobado pasa
    res = fn(
        [9800.0, 8000.0],
        [10000.0, 10000.0],
        min_liquidity_buffer_pct=5.0,
        allow_fiscal_rescheduling_with_cr=True,
        approved_rescheduling_cr_id="CR-LIQ-01",
    )
    assert res["funding_breach_periods"] == []
    assert res["min_period_buffer_pct"] == 2.0
    assert res["is_valid"] is True


def test_validate_funding_limit_reconciliation_and_cash_flow_cliff_domain_errors_and_export():
    """Valida errores de dominio (listas vacias, longitudes, negativos, total_exp > total_fund) y __all__."""
    import pytest

    import backend.schemas.projects as mod
    from backend.schemas.projects import (
        validate_funding_limit_reconciliation_and_cash_flow_cliff as fn,
    )

    invalid_cases = [
        (([], []), {}),
        (([100.0, 200.0], [100.0]), {}),
        (([-10.0, 100.0], [100.0, 100.0]), {}),
        (([10.0, 100.0], [100.0, -5.0]), {}),
        (([0.0, 0.0], [0.0, 0.0]), {}),
        (([500.0, 600.0], [500.0, 500.0]), {}),  # total_exp > total_fund
        (([100.0], [200.0]), {"min_liquidity_buffer_pct": -1.0}),
        (([100.0], [200.0]), {"min_liquidity_buffer_pct": 100.0}),
    ]
    for args, kwargs in invalid_cases:
        with pytest.raises(ValueError):
            fn(*args, **kwargs)

    assert "validate_funding_limit_reconciliation_and_cash_flow_cliff" in mod.__all__


def test_validate_business_case_npv_irr_and_payback_hurdle_healthy():
    """Caso de negocio con NPV >= 0, IRR >= WACC, BCR >= 1.0 y payback en rango (PMBOK §1.2, §7.2)."""
    from backend.schemas.projects import (
        validate_business_case_npv_irr_and_payback_hurdle as fn,
    )

    res = fn(
        net_present_value_npv=125000.456,
        internal_rate_of_return_irr_pct=16.5,
        discount_rate_wacc_pct=10.0,
        payback_period_months=18.0,
        max_allowed_payback_months=24.0,
        benefit_cost_ratio_bcr=1.3525,
    )
    assert res == {
        "net_present_value_npv": 125000.46,
        "irr_spread_over_wacc_pct": 6.5,
        "benefit_cost_ratio_bcr": 1.3525,
        "payback_period_months": 18.0,
        "is_mandatory_regulatory_compliance": False,
        "is_valid": True,
    }


def test_validate_business_case_npv_irr_and_payback_hurdle_rejection_and_regulatory_waiver():
    """Rechaza caso discrecional bajo hurdle rate pero permite exencion por cumplimiento regulatorio obligatorio."""
    import pytest

    from backend.schemas.projects import (
        validate_business_case_npv_irr_and_payback_hurdle as fn,
    )

    # NPV negativo
    with pytest.raises(ValueError, match="hurdle rate"):
        fn(-5000.0, 12.0, 10.0, 18.0, 24.0, 1.1)

    # IRR < WACC
    with pytest.raises(ValueError, match="hurdle rate"):
        fn(5000.0, 8.5, 10.0, 18.0, 24.0, 1.1)

    # BCR < 1.0
    with pytest.raises(ValueError, match="hurdle rate"):
        fn(5000.0, 12.0, 10.0, 18.0, 24.0, 0.92)

    # Payback > max_allowed_payback_months
    with pytest.raises(ValueError, match="hurdle rate"):
        fn(5000.0, 12.0, 10.0, 30.0, 24.0, 1.15)

    # Exencion regulatoria obligatoria (is_mandatory_regulatory_compliance=True)
    reg = fn(
        -25000.0,
        4.0,
        10.0,
        36.0,
        24.0,
        0.65,
        is_mandatory_regulatory_compliance=True,
    )
    assert reg == {
        "net_present_value_npv": -25000.0,
        "irr_spread_over_wacc_pct": -6.0,
        "benefit_cost_ratio_bcr": 0.65,
        "payback_period_months": 36.0,
        "is_mandatory_regulatory_compliance": True,
        "is_valid": True,
    }


def test_validate_business_case_npv_irr_and_payback_hurdle_exact_boundaries():
    """Acepta valores exactos en la frontera: NPV == 0, IRR == WACC, BCR == 1.0 y payback == max."""
    from backend.schemas.projects import (
        validate_business_case_npv_irr_and_payback_hurdle as fn,
    )

    res = fn(0.0, 10.0, 10.0, 24.0, 24.0, 1.0)
    assert res["irr_spread_over_wacc_pct"] == 0.0
    assert res["is_valid"] is True


def test_validate_business_case_npv_irr_and_payback_hurdle_domain_errors_and_export():
    """Valida errores de dominio (WACC <= 0, payback <= 0, max_payback <= 0, BCR < 0) y exportacion en __all__."""
    import pytest

    import backend.schemas.projects as mod
    from backend.schemas.projects import (
        validate_business_case_npv_irr_and_payback_hurdle as fn,
    )

    invalid_cases = [
        (10000.0, 12.0, 0.0, 12.0, 24.0, 1.2),   # discount_rate_wacc_pct <= 0
        (10000.0, 12.0, -5.0, 12.0, 24.0, 1.2),  # discount_rate_wacc_pct < 0
        (10000.0, 12.0, 10.0, 0.0, 24.0, 1.2),   # payback_period_months <= 0
        (10000.0, 12.0, 10.0, 12.0, 0.0, 1.2),   # max_allowed_payback_months <= 0
        (10000.0, 12.0, 10.0, 12.0, 24.0, -0.1), # benefit_cost_ratio_bcr < 0
    ]
    for args in invalid_cases:
        with pytest.raises(ValueError):
            fn(*args)

    assert "validate_business_case_npv_irr_and_payback_hurdle" in mod.__all__




def test_validate_monte_carlo_confidence_band_and_reserve_adequacy_healthy():
    """Banda monotónica bien muestreada con reserva que cubre P80."""
    import pytest

    from backend.schemas.projects import (
        validate_monte_carlo_confidence_band_and_reserve_adequacy,
    )

    res = validate_monte_carlo_confidence_band_and_reserve_adequacy(
        [
            {"simulation_id": "MC-1", "iterations": 1000, "deterministic_base": 100.0,
             "p50_estimate": 105.0, "p80_estimate": 120.0, "p90_estimate": 130.0,
             "allocated_contingency_reserve": 25.0},
        ]
    )
    assert res == {
        "total_simulations": 1,
        "compliant_simulations_count": 1,
        "non_monotonic_or_under_sampled_count": 0,
        "reserve_shortfall_at_p80_count": 0,
        "excessive_tail_uncertainty_spread_count": 0,
        "simulation_governance_status": "HEALTHY",
        "violations": [],
    }


def test_validate_monte_carlo_confidence_band_and_reserve_adequacy_critical():
    """Shortfall en P80 (CRITICAL) + under-sampled/non-monotónica (CRITICAL)."""
    import pytest

    from backend.schemas.projects import (
        validate_monte_carlo_confidence_band_and_reserve_adequacy,
    )

    res = validate_monte_carlo_confidence_band_and_reserve_adequacy(
        [
            # MC-2: base+reserva 130 < P80 140 -> shortfall; spread 140/105 OK.
            {"simulation_id": "MC-2", "iterations": 1000, "deterministic_base": 100.0,
             "p50_estimate": 105.0, "p80_estimate": 140.0, "p90_estimate": 140.0,
             "allocated_contingency_reserve": 30.0},
            # MC-3: iterations 999 < 1000 y banda P50=90 < base=100, P80<P50.
            {"simulation_id": "MC-3", "iterations": 999, "deterministic_base": 100.0,
             "p50_estimate": 90.0, "p80_estimate": 85.0, "p90_estimate": 88.0,
             "allocated_contingency_reserve": 10.0},
        ]
    )
    assert res["total_simulations"] == 2
    assert res["reserve_shortfall_at_p80_count"] == 1
    assert res["non_monotonic_or_under_sampled_count"] == 1
    assert res["compliant_simulations_count"] == 0
    assert res["simulation_governance_status"] == "CRITICAL"
    assert res["violations"][0]["reasons"] == ["RESERVE_SHORTFALL_AT_P80 (130.0<140.0)"]
    assert res["violations"][1]["reasons"] == [
        "UNDER_SAMPLED (999<1000)",
        "NON_MONOTONIC_BAND (debe cumplir 0 < base <= P50 <= P80 <= P90)",
    ]

    # base <= 0 no cumple la monotonicidad 0 < base.
    zero = validate_monte_carlo_confidence_band_and_reserve_adequacy(
        [
            {"simulation_id": "MC-6", "iterations": 1000, "deterministic_base": 0.0,
             "p50_estimate": 1.0, "p80_estimate": 2.0, "p90_estimate": 3.0,
             "allocated_contingency_reserve": 5.0},
        ]
    )
    assert zero["non_monotonic_or_under_sampled_count"] == 1
    assert zero["simulation_governance_status"] == "CRITICAL"


def test_validate_monte_carlo_confidence_band_and_reserve_adequacy_at_risk_and_borders():
    """Spread excesivo P90/P50 > ratio -> AT_RISK; bordes inclusivos de todas las reglas."""
    import pytest

    from backend.schemas.projects import (
        validate_monte_carlo_confidence_band_and_reserve_adequacy,
    )

    risk = validate_monte_carlo_confidence_band_and_reserve_adequacy(
        [
            {"simulation_id": "MC-4", "iterations": 1000, "deterministic_base": 100.0,
             "p50_estimate": 100.0, "p80_estimate": 120.0, "p90_estimate": 141.0,
             "allocated_contingency_reserve": 30.0},
        ]
    )
    assert risk["excessive_tail_uncertainty_spread_count"] == 1
    assert risk["compliant_simulations_count"] == 0
    assert risk["simulation_governance_status"] == "AT_RISK"
    assert risk["violations"][0]["reasons"] == ["EXCESSIVE_TAIL_SPREAD (P90/P50=1.41>1.35)"]

    # Bordes: base+reserva == P80 (125 == 125) OK; spread == ratio (141/105 <= custom) OK.
    border = validate_monte_carlo_confidence_band_and_reserve_adequacy(
        [
            {"simulation_id": "MC-5", "iterations": 1000, "deterministic_base": 100.0,
             "p50_estimate": 105.0, "p80_estimate": 125.0, "p90_estimate": 141.0,
             "allocated_contingency_reserve": 25.0},
        ],
        max_p90_to_p50_spread_ratio=1.3428572,
    )
    assert border["simulation_governance_status"] == "HEALTHY"
    assert border["compliant_simulations_count"] == 1

    # Spread no se evalua cuando P50 == 0.
    z50 = validate_monte_carlo_confidence_band_and_reserve_adequacy(
        [
            {"simulation_id": "MC-7", "iterations": 1000, "deterministic_base": 0.0,
             "p50_estimate": 0.0, "p80_estimate": 0.0, "p90_estimate": 0.0,
             "allocated_contingency_reserve": 0.0},
        ]
    )
    assert z50["excessive_tail_uncertainty_spread_count"] == 0


def test_validate_monte_carlo_confidence_band_and_reserve_adequacy_custom_and_empty():
    """Umbrales custom, entrada vacia/None y export en __all__."""
    import pytest

    from backend.schemas.projects import (
        validate_monte_carlo_confidence_band_and_reserve_adequacy as fn,
    )
    import backend.schemas.projects as mod

    custom = fn(
        [
            {"simulation_id": "MC-8", "iterations": 500, "deterministic_base": 50.0,
             "p50_estimate": 55.0, "p80_estimate": 65.0, "p90_estimate": 70.0,
             "allocated_contingency_reserve": 16.0},
        ],
        min_iterations=500,
        max_p90_to_p50_spread_ratio=1.30,
    )
    assert custom["simulation_governance_status"] == "HEALTHY"
    assert custom["compliant_simulations_count"] == 1

    for payload in ([], None, 42, ["x"]):
        empty = fn(payload)
        assert empty["total_simulations"] == 0
        assert empty["simulation_governance_status"] == "HEALTHY"
        assert empty["violations"] == []

    assert "validate_monte_carlo_confidence_band_and_reserve_adequacy" in mod.__all__


def test_validate_resource_leveling_and_smoothing_constraints_healthy():
    """Corridas válidas de smoothing (dentro de holgura, sin extender CP) y leveling (con CCB y slip moderado)."""
    from backend.schemas.projects import (
        validate_resource_leveling_and_smoothing_constraints,
    )

    runs = [
        {
            "id": "OPT-01",
            "mode": "smoothing",
            "total_float_available_days": 5.0,
            "activity_delay_days": 3.0,
            "baseline_duration_days": 60.0,
            "critical_path_extended_days": 0.0,
            "ccb_approved_slip": False,
            "peak_allocation_fte": 4.0,
            "average_allocation_fte": 3.0,
            "capacity_ceiling_fte": 5.0,
        },
        {
            "id": "OPT-02",
            "mode": "leveling",
            "total_float_available_days": 0.0,
            "activity_delay_days": 6.0,
            "baseline_duration_days": 60.0,
            "critical_path_extended_days": 6.0,
            "ccb_approved_slip": True,
            "peak_allocation_fte": 4.5,
            "average_allocation_fte": 3.5,
            "capacity_ceiling_fte": 5.0,
        },
    ]
    res = validate_resource_leveling_and_smoothing_constraints(runs)
    assert res["total_runs"] == 2
    assert res["compliant_runs"] == 2
    assert res["smoothing_violates_float_or_critical_path_ids"] == []
    assert res["unapproved_or_excessive_leveling_slip_ids"] == []
    assert res["unresolved_over_allocation_or_spike_ids"] == []
    assert res["optimization_governance_status"] == "HEALTHY"
    assert res["is_valid"] is True
    assert res["recommendations"] == []


def test_validate_resource_leveling_and_smoothing_constraints_critical_smoothing_and_leveling():
    """Detecta smoothing que viola holgura/ruta crítica y leveling sin CCB o con deslizamiento excesivo (CRITICAL)."""
    from backend.schemas.projects import (
        validate_resource_leveling_and_smoothing_constraints,
    )

    runs = [
        {
            "run_id": "OPT-10",
            "mode": "smoothing",
            "total_float_available_days": 2.0,
            "activity_delay_days": 4.0,
            "baseline_duration_days": 50.0,
            "critical_path_extended_days": 2.0,
            "peak_allocation_fte": 3.0,
            "average_allocation_fte": 2.5,
            "capacity_ceiling_fte": 4.0,
        },
        {
            "run_id": "OPT-11",
            "mode": "leveling",
            "baseline_duration_days": 50.0,
            "critical_path_extended_days": 10.0,
            "ccb_approved_slip": True,
            "peak_allocation_fte": 3.0,
            "average_allocation_fte": 2.5,
            "capacity_ceiling_fte": 4.0,
        },
    ]
    res = validate_resource_leveling_and_smoothing_constraints(
        runs, max_leveling_schedule_slip_pct=15.0
    )
    assert res["total_runs"] == 2
    assert res["compliant_runs"] == 0
    assert res["smoothing_violates_float_or_critical_path_ids"] == ["OPT-10"]
    assert res["unapproved_or_excessive_leveling_slip_ids"] == ["OPT-11"]
    assert res["optimization_governance_status"] == "CRITICAL"
    assert res["is_valid"] is False
    assert len(res["recommendations"]) >= 2


def test_validate_resource_leveling_and_smoothing_constraints_at_risk_overallocation_spike():
    """Detecta sobreasignación sobre capacity_ceiling_fte o ratio pico/promedio excesivo (AT_RISK)."""
    from backend.schemas.projects import (
        validate_resource_leveling_and_smoothing_constraints,
    )

    runs = [
        {
            "run_id": "OPT-20",
            "mode": "smoothing",
            "total_float_available_days": 5.0,
            "activity_delay_days": 2.0,
            "critical_path_extended_days": 0.0,
            "peak_allocation_fte": 6.0,
            "average_allocation_fte": 3.0,
            "capacity_ceiling_fte": 5.0,
        }
    ]
    res = validate_resource_leveling_and_smoothing_constraints(
        runs, max_peak_to_average_ratio=1.6
    )
    assert res["total_runs"] == 1
    assert res["compliant_runs"] == 0
    assert res["unresolved_over_allocation_or_spike_ids"] == ["OPT-20"]
    assert res["smoothing_violates_float_or_critical_path_ids"] == []
    assert res["unapproved_or_excessive_leveling_slip_ids"] == []
    assert res["optimization_governance_status"] == "AT_RISK"
    assert res["is_valid"] is False
    assert len(res["recommendations"]) >= 1


def test_validate_resource_leveling_and_smoothing_constraints_empty_and_export():
    """Manejo defensivo de entradas vacías/no-secuencia y exportación en __all__."""
    import backend.schemas.projects as mod
    from backend.schemas.projects import (
        validate_resource_leveling_and_smoothing_constraints,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = validate_resource_leveling_and_smoothing_constraints(payload)  # type: ignore[arg-type]
        assert empty["total_runs"] == 0
        assert empty["compliant_runs"] == 0
        assert empty["optimization_governance_status"] == "HEALTHY"
        assert empty["is_valid"] is True
        assert empty["recommendations"] == []

    assert "validate_resource_leveling_and_smoothing_constraints" in mod.__all__


def test_validate_wbs_100_percent_rollup_and_8_80_granularity_healthy():
    """Valida nodos padres con rollup al 100% y paquetes hoja dentro de [8.0, 80.0]h con responsable único."""
    from backend.schemas.projects import (
        validate_wbs_100_percent_rollup_and_8_80_granularity,
    )

    nodes = [
        {
            "wbs_code": "1.0",
            "is_leaf": False,
            "planned_effort_hours": 100.0,
            "children_effort_sum_hours": 100.0,
            "children_scope_weight_sum_pct": 100.0,
        },
        {
            "wbs_code": "1.1",
            "is_leaf": True,
            "planned_effort_hours": 40.0,
            "single_owner_assigned": True,
        },
        {
            "wbs_code": "1.2",
            "is_leaf": True,
            "planned_effort_hours": 60.0,
            "single_owner_assigned": True,
        },
    ]
    res = validate_wbs_100_percent_rollup_and_8_80_granularity(nodes)
    assert res["total_nodes"] == 3
    assert res["compliant_nodes"] == 3
    assert res["parent_100_pct_rollup_violation_ids"] == []
    assert res["leaf_granularity_out_of_8_80_bounds_ids"] == []
    assert res["unowned_work_package_ids"] == []
    assert res["wbs_governance_status"] == "HEALTHY"
    assert res["is_valid"] is True
    assert res["recommendations"] == []


def test_validate_wbs_100_percent_rollup_and_8_80_granularity_critical():
    """Detecta violación de Regla del 100% en padre y paquete de trabajo hoja sin dueño único ('CRITICAL')."""
    from backend.schemas.projects import (
        validate_wbs_100_percent_rollup_and_8_80_granularity,
    )

    nodes = [
        {
            "node_id": "WBS-1.0",
            "is_leaf": False,
            "planned_effort_hours": 120.0,
            "children_effort_sum_hours": 90.0,
            "children_scope_weight_sum_pct": 85.0,
        },
        {
            "node_id": "WBS-1.1",
            "is_leaf": True,
            "planned_effort_hours": 24.0,
            "single_owner_assigned": False,
        },
    ]
    res = validate_wbs_100_percent_rollup_and_8_80_granularity(nodes)
    assert res["total_nodes"] == 2
    assert res["compliant_nodes"] == 0
    assert res["parent_100_pct_rollup_violation_ids"] == ["WBS-1.0"]
    assert res["unowned_work_package_ids"] == ["WBS-1.1"]
    assert res["wbs_governance_status"] == "CRITICAL"
    assert res["is_valid"] is False
    assert len(res["recommendations"]) >= 2


def test_validate_wbs_100_percent_rollup_and_8_80_granularity_at_risk_bounds():
    """Detecta paquetes hoja fuera de límites de 8/80 horas (< 8h o > 80h -> 'AT_RISK')."""
    from backend.schemas.projects import (
        validate_wbs_100_percent_rollup_and_8_80_granularity,
    )

    nodes = [
        {
            "id": "WBS-2.1",
            "is_leaf": True,
            "planned_effort_hours": 4.0,
            "single_owner_assigned": True,
        },
        {
            "id": "WBS-2.2",
            "is_leaf": True,
            "planned_effort_hours": 120.0,
            "single_owner_assigned": True,
        },
    ]
    res = validate_wbs_100_percent_rollup_and_8_80_granularity(nodes)
    assert res["total_nodes"] == 2
    assert res["compliant_nodes"] == 0
    assert res["leaf_granularity_out_of_8_80_bounds_ids"] == ["WBS-2.1", "WBS-2.2"]
    assert res["parent_100_pct_rollup_violation_ids"] == []
    assert res["unowned_work_package_ids"] == []
    assert res["wbs_governance_status"] == "AT_RISK"
    assert res["is_valid"] is False
    assert len(res["recommendations"]) >= 1


def test_validate_wbs_100_percent_rollup_and_8_80_granularity_empty_and_export():
    """Manejo defensivo de entradas vacías/no-secuencia y exportación en __all__."""
    import backend.schemas.projects as mod
    from backend.schemas.projects import (
        validate_wbs_100_percent_rollup_and_8_80_granularity,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = validate_wbs_100_percent_rollup_and_8_80_granularity(payload)  # type: ignore[arg-type]
        assert empty["total_nodes"] == 0
        assert empty["compliant_nodes"] == 0
        assert empty["parent_100_pct_rollup_violation_ids"] == []
        assert empty["leaf_granularity_out_of_8_80_bounds_ids"] == []
        assert empty["unowned_work_package_ids"] == []
        assert empty["wbs_governance_status"] == "HEALTHY"
        assert empty["is_valid"] is True
        assert empty["recommendations"] == []

    assert "validate_wbs_100_percent_rollup_and_8_80_granularity" in mod.__all__


def test_validate_make_or_buy_breakeven_and_tco_healthy():
    """Valida decisiones make y buy óptimas en TCO, con capacidad interna o protección IP/escrow."""
    from backend.schemas.projects import (
        validate_make_or_buy_breakeven_and_tco,
    )

    decisions = [
        {
            "id": "MOB-01",
            "selected_option": "make",
            "make_initial_cost": 20000.0,
            "make_recurring_cost": 1000.0,
            "buy_initial_cost": 10000.0,
            "buy_recurring_cost": 2500.0,
            "horizon_periods": 12,
            "is_core_proprietary_ip": True,
            "internal_capacity_available": True,
        },
        {
            "id": "MOB-02",
            "selected_option": "buy",
            "make_initial_cost": 50000.0,
            "make_recurring_cost": 3000.0,
            "buy_initial_cost": 15000.0,
            "buy_recurring_cost": 2000.0,
            "horizon_periods": 12,
            "is_core_proprietary_ip": True,
            "ip_protection_and_escrow_signed": True,
        },
    ]
    res = validate_make_or_buy_breakeven_and_tco(decisions)
    assert res["total_decisions"] == 2
    assert res["compliant_decisions"] == 2
    assert res["core_ip_outsourced_without_escrow_ids"] == []
    assert res["make_selected_without_capacity_ids"] == []
    assert res["unjustified_tco_premium_ids"] == []
    assert res["mob_governance_status"] == "HEALTHY"
    assert res["is_valid"] is True
    assert res["recommendations"] == []


def test_validate_make_or_buy_breakeven_and_tco_critical():
    """Detecta externalización de IP crítica sin escrow y selección make sin capacidad interna ('CRITICAL')."""
    from backend.schemas.projects import (
        validate_make_or_buy_breakeven_and_tco,
    )

    decisions = [
        {
            "decision_id": "MOB-10",
            "selected_option": "buy",
            "make_initial_cost": 40000.0,
            "make_recurring_cost": 2000.0,
            "buy_initial_cost": 10000.0,
            "buy_recurring_cost": 1500.0,
            "horizon_periods": 12,
            "is_core_proprietary_ip": True,
            "ip_protection_and_escrow_signed": False,
        },
        {
            "decision_id": "MOB-11",
            "selected_option": "make",
            "make_initial_cost": 15000.0,
            "make_recurring_cost": 1000.0,
            "buy_initial_cost": 30000.0,
            "buy_recurring_cost": 2000.0,
            "horizon_periods": 12,
            "internal_capacity_available": False,
        },
    ]
    res = validate_make_or_buy_breakeven_and_tco(decisions)
    assert res["total_decisions"] == 2
    assert res["compliant_decisions"] == 0
    assert res["core_ip_outsourced_without_escrow_ids"] == ["MOB-10"]
    assert res["make_selected_without_capacity_ids"] == ["MOB-11"]
    assert res["mob_governance_status"] == "CRITICAL"
    assert res["is_valid"] is False
    assert len(res["recommendations"]) >= 2


def test_validate_make_or_buy_breakeven_and_tco_at_risk_and_override():
    """Detecta sobrecosto TCO injustificado ('AT_RISK') y valida exención con strategic_override_approved=True."""
    from backend.schemas.projects import (
        validate_make_or_buy_breakeven_and_tco,
    )

    decisions = [
        {
            "id": "MOB-20",
            "selected_option": "make",
            "make_initial_cost": 60000.0,
            "make_recurring_cost": 2000.0,
            "buy_initial_cost": 20000.0,
            "buy_recurring_cost": 1000.0,
            "horizon_periods": 10,
            "internal_capacity_available": True,
            "strategic_override_approved": False,
        },
        {
            "id": "MOB-21",
            "selected_option": "make",
            "make_initial_cost": 60000.0,
            "make_recurring_cost": 2000.0,
            "buy_initial_cost": 20000.0,
            "buy_recurring_cost": 1000.0,
            "horizon_periods": 10,
            "internal_capacity_available": True,
            "strategic_override_approved": True,
        },
    ]
    res = validate_make_or_buy_breakeven_and_tco(decisions)
    assert res["total_decisions"] == 2
    assert res["compliant_decisions"] == 1
    assert res["unjustified_tco_premium_ids"] == ["MOB-20"]
    assert res["mob_governance_status"] == "AT_RISK"
    assert res["is_valid"] is False
    assert len(res["recommendations"]) >= 1


def test_validate_make_or_buy_breakeven_and_tco_empty_and_export():
    """Manejo defensivo de entradas vacías/no-secuencia y exportación en __all__."""
    import backend.schemas.projects as mod
    from backend.schemas.projects import (
        validate_make_or_buy_breakeven_and_tco,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = validate_make_or_buy_breakeven_and_tco(payload)  # type: ignore[arg-type]
        assert empty["total_decisions"] == 0
        assert empty["compliant_decisions"] == 0
        assert empty["core_ip_outsourced_without_escrow_ids"] == []
        assert empty["make_selected_without_capacity_ids"] == []
        assert empty["unjustified_tco_premium_ids"] == []
        assert empty["mob_governance_status"] == "HEALTHY"
        assert empty["is_valid"] is True
        assert empty["recommendations"] == []

    assert "validate_make_or_buy_breakeven_and_tco" in mod.__all__


def test_validate_risk_response_strategy_and_contingency_triggers_compliant():
    """Valida respuestas a amenazas y oportunidades bien alineadas, con reducción efectiva, triggers y fallback ('compliant')."""
    from backend.schemas.projects import (
        validate_risk_response_strategy_and_contingency_triggers,
    )

    responses = [
        {
            "risk_id": "RSK-01",
            "risk_type": "threat",
            "strategy": "mitigate",
            "pre_response_score": 20.0,
            "residual_score": 8.0,
            "early_warning_trigger": "Latencia p99 > 250ms durante 15m",
            "fallback_plan": None,
            "action_owner_id": "USR-101",
        },
        {
            "risk_id": "RSK-02",
            "risk_type": "threat",
            "strategy": "avoid",
            "pre_response_score": 16.0,
            "residual_score": 0.0,
            "early_warning_trigger": "Retraso de homologación > 5 días",
            "fallback_plan": "Conmutar a pasarela secundaria certificada",
            "action_owner_id": "USR-102",
        },
        {
            "risk_id": "RSK-03",
            "risk_type": "opportunity",
            "strategy": "exploit",
            "pre_response_score": 8.0,
            "residual_score": 10.0,
            "early_warning_trigger": "Descuento por pronto pago disponible",
            "fallback_plan": None,
            "action_owner_id": "USR-103",
        },
    ]
    res = validate_risk_response_strategy_and_contingency_triggers(responses)
    assert res["is_valid"] is True
    assert res["total_responses_evaluated"] == 3
    assert res["invalid_strategy_alignment_ids"] == []
    assert res["ineffective_mitigation_ids"] == []
    assert res["missing_trigger_ids"] == []
    assert res["missing_fallback_ids"] == []
    assert res["average_risk_reduction_pct"] == 80.0
    assert res["governance_status"] == "compliant"
    assert res["issues"] == []


def test_validate_risk_response_strategy_and_contingency_triggers_non_compliant():
    """Detecta estrategia de oportunidad en amenaza, falta de responsable y mitigación/avoid inefectiva ('non_compliant')."""
    from backend.schemas.projects import (
        validate_risk_response_strategy_and_contingency_triggers,
    )

    responses = [
        {
            "risk_id": "RSK-10",
            "risk_type": "threat",
            "strategy": "exploit",
            "pre_response_score": 15.0,
            "residual_score": 10.0,
            "early_warning_trigger": "Trigger X",
            "fallback_plan": "Plan B",
            "action_owner_id": "USR-201",
        },
        {
            "risk_id": "RSK-11",
            "risk_type": "threat",
            "strategy": "mitigate",
            "pre_response_score": 12.0,
            "residual_score": 12.0,
            "early_warning_trigger": "Trigger Y",
            "fallback_plan": "Plan C",
            "action_owner_id": "",
        },
        {
            "risk_id": "RSK-12",
            "risk_type": "threat",
            "strategy": "avoid",
            "pre_response_score": 18.0,
            "residual_score": 4.0,
            "early_warning_trigger": "Trigger Z",
            "fallback_plan": "Plan D",
            "action_owner_id": "USR-203",
        },
    ]
    res = validate_risk_response_strategy_and_contingency_triggers(responses)
    assert res["is_valid"] is False
    assert res["invalid_strategy_alignment_ids"] == ["RSK-10", "RSK-11"]
    assert res["ineffective_mitigation_ids"] == ["RSK-11", "RSK-12"]
    assert res["governance_status"] == "non_compliant"
    assert len(res["issues"]) >= 3


def test_validate_risk_response_strategy_and_contingency_triggers_needs_refinement():
    """Detecta falta de early_warning_trigger en estrategia activa y falta de fallback_plan en riesgo residual alto ('needs_refinement')."""
    from backend.schemas.projects import (
        validate_risk_response_strategy_and_contingency_triggers,
    )

    responses = [
        {
            "risk_id": "RSK-20",
            "risk_type": "threat",
            "strategy": "transfer",
            "pre_response_score": 25.0,
            "residual_score": 14.0,
            "early_warning_trigger": "",
            "fallback_plan": None,
            "action_owner_id": "USR-301",
        },
        {
            "risk_id": "RSK-21",
            "risk_type": "threat",
            "strategy": "accept",
            "pre_response_score": 6.0,
            "residual_score": 6.0,
            "early_warning_trigger": None,
            "fallback_plan": None,
            "action_owner_id": "USR-302",
        },
    ]
    res = validate_risk_response_strategy_and_contingency_triggers(responses)
    assert res["is_valid"] is False
    assert res["invalid_strategy_alignment_ids"] == []
    assert res["ineffective_mitigation_ids"] == []
    assert res["missing_trigger_ids"] == ["RSK-20"]
    assert res["missing_fallback_ids"] == ["RSK-20"]
    assert res["governance_status"] == "needs_refinement"
    assert len(res["issues"]) == 2


def test_validate_risk_response_strategy_and_contingency_triggers_empty_and_export():
    """Verifica manejo defensivo de entradas vacías/no-secuencia y exportación en __all__."""
    import backend.schemas.projects as mod
    from backend.schemas.projects import (
        validate_risk_response_strategy_and_contingency_triggers,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = validate_risk_response_strategy_and_contingency_triggers(payload)  # type: ignore[arg-type]
        assert empty["is_valid"] is True
        assert empty["total_responses_evaluated"] == 0
        assert empty["invalid_strategy_alignment_ids"] == []
        assert empty["ineffective_mitigation_ids"] == []
        assert empty["missing_trigger_ids"] == []
        assert empty["missing_fallback_ids"] == []
        assert empty["average_risk_reduction_pct"] == 0.0
        assert empty["governance_status"] == "compliant"
        assert empty["issues"] == []

    assert (
        "validate_risk_response_strategy_and_contingency_triggers"
        in mod.__all__
    )


def test_validate_schedule_network_pdm_lead_lag_hygiene_compliant():
    """Valida red PDM con >= 80% FS, adelantos justificados dentro de límite y lags razonables ('COMPLIANT')."""
    from backend.schemas.projects import (
        validate_schedule_network_pdm_lead_lag_hygiene,
    )

    deps = [
        {
            "dependency_id": "DEP-01",
            "relationship_type": "FS",
            "lag_days": 0.0,
            "successor_duration_days": 10.0,
            "has_documented_justification": False,
        },
        {
            "dependency_id": "DEP-02",
            "relationship_type": "FS",
            "lag_days": -2.0,
            "successor_duration_days": 8.0,
            "has_documented_justification": True,
        },
        {
            "dependency_id": "DEP-03",
            "relationship_type": "FS",
            "lag_days": 2.0,
            "successor_duration_days": 10.0,
            "has_documented_justification": True,
        },
        {
            "dependency_id": "DEP-04",
            "relationship_type": "FS",
            "lag_days": 0.0,
            "successor_duration_days": 5.0,
            "has_documented_justification": False,
        },
        {
            "dependency_id": "DEP-05",
            "relationship_type": "SS",
            "lag_days": 1.0,
            "successor_duration_days": 6.0,
            "has_documented_justification": True,
        },
    ]
    res = validate_schedule_network_pdm_lead_lag_hygiene(deps)
    assert res["is_valid"] is True
    assert res["total_dependencies"] == 5
    assert res["invalid_relationship_ids"] == []
    assert res["excessive_negative_lead_ids"] == []
    assert res["excessive_positive_lag_ids"] == []
    assert res["fs_dominant_ratio_pct"] == 80.0
    assert res["pdm_hygiene_status"] == "COMPLIANT"
    assert res["issues"] == []


def test_validate_schedule_network_pdm_lead_lag_hygiene_non_compliant():
    """Detecta relación SF sin justificar/tipo desconocido y adelantos negativos sin justificar o excesivos ('NON_COMPLIANT')."""
    from backend.schemas.projects import (
        validate_schedule_network_pdm_lead_lag_hygiene,
    )

    deps = [
        {
            "dependency_id": "DEP-10",
            "relationship_type": "SF",
            "lag_days": 0.0,
            "successor_duration_days": 10.0,
            "has_documented_justification": False,
        },
        {
            "dependency_id": "DEP-11",
            "relationship_type": "FS",
            "lag_days": -8.0,
            "successor_duration_days": 12.0,
            "has_documented_justification": True,
        },
        {
            "dependency_id": "DEP-12",
            "relationship_type": "FS",
            "lag_days": -2.0,
            "successor_duration_days": 10.0,
            "has_documented_justification": False,
        },
    ]
    res = validate_schedule_network_pdm_lead_lag_hygiene(deps)
    assert res["is_valid"] is False
    assert res["invalid_relationship_ids"] == ["DEP-10"]
    assert res["excessive_negative_lead_ids"] == ["DEP-11", "DEP-12"]
    assert res["pdm_hygiene_status"] == "NON_COMPLIANT"
    assert len(res["issues"]) >= 3


def test_validate_schedule_network_pdm_lead_lag_hygiene_needs_refinement():
    """Detecta lag positivo excesivo (>50% duración sucesor) o baja dominancia FS (<80%) ('NEEDS_REFINEMENT')."""
    from backend.schemas.projects import (
        validate_schedule_network_pdm_lead_lag_hygiene,
    )

    deps = [
        {
            "dependency_id": "DEP-20",
            "relationship_type": "FS",
            "lag_days": 8.0,
            "successor_duration_days": 10.0,
            "has_documented_justification": True,
        },
        {
            "dependency_id": "DEP-21",
            "relationship_type": "SS",
            "lag_days": 1.0,
            "successor_duration_days": 10.0,
            "has_documented_justification": True,
        },
    ]
    res = validate_schedule_network_pdm_lead_lag_hygiene(deps)
    assert res["is_valid"] is False
    assert res["invalid_relationship_ids"] == []
    assert res["excessive_negative_lead_ids"] == []
    assert res["excessive_positive_lag_ids"] == ["DEP-20"]
    assert res["fs_dominant_ratio_pct"] == 50.0
    assert res["pdm_hygiene_status"] == "NEEDS_REFINEMENT"
    assert len(res["issues"]) == 2


def test_validate_schedule_network_pdm_lead_lag_hygiene_empty_and_export():
    """Verifica manejo defensivo de entradas vacías/no-secuencia y exportación en __all__."""
    import backend.schemas.projects as mod
    from backend.schemas.projects import (
        validate_schedule_network_pdm_lead_lag_hygiene,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = validate_schedule_network_pdm_lead_lag_hygiene(payload)  # type: ignore[arg-type]
        assert empty["is_valid"] is True
        assert empty["total_dependencies"] == 0
        assert empty["invalid_relationship_ids"] == []
        assert empty["excessive_negative_lead_ids"] == []
        assert empty["excessive_positive_lag_ids"] == []
        assert empty["fs_dominant_ratio_pct"] == 100.0
        assert empty["pdm_hygiene_status"] == "COMPLIANT"
        assert empty["issues"] == []

    assert "validate_schedule_network_pdm_lead_lag_hygiene" in mod.__all__





def test_rtm_bidirectional_fully_traced_and_gap():
    """Todo trazado -> FULLY_TRACED; mandatory sin test o falta de WBS -> TRACEABILITY_GAP."""
    from backend.schemas.projects import (
        validate_requirements_traceability_bidirectional_coverage,
    )

    def req(rid, obj=None, wbs=None, test=None, prio="mandatory", deferred=False):
        return {
            "requirement_id": rid,
            "priority_class": prio,
            "business_objective_id": obj,
            "wbs_deliverable_id": wbs,
            "verification_test_case_id": test,
            "is_deferred_or_descoped": deferred,
        }

    fully = validate_requirements_traceability_bidirectional_coverage(
        [req("REQ-1", "OBJ-1", "WBS-1", "TC-1"), req("REQ-2", "OBJ-2", "WBS-2", "TC-2", "should")]
    )
    assert fully["active_requirements_count"] == 2
    assert fully["fully_traced_count"] == 2
    assert fully["traceability_coverage_pct"] == 100.0
    assert fully["backward_untraced_requirement_ids"] == []
    assert fully["forward_untraced_wbs_requirement_ids"] == []
    assert fully["unverified_test_requirement_ids"] == []
    assert fully["rtm_governance_status"] == "FULLY_TRACED"
    assert fully["is_valid"] is True

    gap = validate_requirements_traceability_bidirectional_coverage(
        [
            req("REQ-3", "OBJ-3", None, None),
            req("REQ-4", "OBJ-4", "WBS-4", "TC-4"),
        ]
    )
    assert gap["forward_untraced_wbs_requirement_ids"] == ["REQ-3"]
    assert gap["unverified_test_requirement_ids"] == ["REQ-3"]
    assert gap["rtm_governance_status"] == "TRACEABILITY_GAP"
    assert gap["is_valid"] is False

    # Unverified solo para mandatory: should sin test no genera hallazgo de tests.
    should_scope = validate_requirements_traceability_bidirectional_coverage(
        [req("REQ-5", "OBJ-5", "WBS-5", None, "should")]
    )
    assert should_scope["unverified_test_requirement_ids"] == []
    assert should_scope["traceability_coverage_pct"] == 0.0
    assert should_scope["rtm_governance_status"] == "PARTIAL_COVERAGE"

    # Flag apagado: mandatory sin test tampoco genera unverified.
    flag_off = validate_requirements_traceability_bidirectional_coverage(
        [req("REQ-6", "OBJ-6", "WBS-6", None)],
        require_test_case_for_mandatory=False,
    )
    assert flag_off["unverified_test_requirement_ids"] == []
    assert flag_off["traceability_coverage_pct"] == 0.0
    assert flag_off["rtm_governance_status"] == "PARTIAL_COVERAGE"


def test_rtm_bidirectional_partial_coverage_and_deferred():
    """Backward sin objetivo o cobertura < min -> PARTIAL_COVERAGE; deferred/descoped excluidos."""
    from backend.schemas.projects import (
        validate_requirements_traceability_bidirectional_coverage,
    )

    def req(rid, obj=None, wbs=None, test=None, prio="mandatory", deferred=False):
        return {
            "requirement_id": rid,
            "priority_class": prio,
            "business_objective_id": obj,
            "wbs_deliverable_id": wbs,
            "verification_test_case_id": test,
            "is_deferred_or_descoped": deferred,
        }

    backward = validate_requirements_traceability_bidirectional_coverage(
        [req("REQ-7", None, "WBS-7", "TC-7")]
    )
    assert backward["backward_untraced_requirement_ids"] == ["REQ-7"]
    assert backward["forward_untraced_wbs_requirement_ids"] == []
    assert backward["traceability_coverage_pct"] == 0.0
    assert backward["rtm_governance_status"] == "PARTIAL_COVERAGE"

    deferred = validate_requirements_traceability_bidirectional_coverage(
        [
            req("REQ-8", "OBJ-8", "WBS-8", "TC-8"),
            req("REQ-9", None, None, None, deferred=True),
        ]
    )
    assert deferred["active_requirements_count"] == 1
    assert deferred["fully_traced_count"] == 1
    assert deferred["traceability_coverage_pct"] == 100.0
    assert deferred["rtm_governance_status"] == "FULLY_TRACED"

    # Umbral custom: 75% con min 80 -> PARTIAL_COVERAGE; con min 70 -> FULLY_TRACED.
    four = [
        req("REQ-10", "OBJ-10", "WBS-10", "TC-10"),
        req("REQ-11", "OBJ-11", "WBS-11", "TC-11"),
        req("REQ-12", "OBJ-12", "WBS-12", "TC-12"),
        req("REQ-13", "OBJ-13", "WBS-13", None, "should"),
    ]
    under = validate_requirements_traceability_bidirectional_coverage(
        four, min_traceability_coverage_pct=80.0
    )
    assert under["traceability_coverage_pct"] == 75.0
    assert under["rtm_governance_status"] == "PARTIAL_COVERAGE"

    over = validate_requirements_traceability_bidirectional_coverage(
        four, min_traceability_coverage_pct=70.0
    )
    assert over["traceability_coverage_pct"] == 75.0
    assert over["rtm_governance_status"] == "FULLY_TRACED"
    assert over["is_valid"] is True


def test_rtm_bidirectional_neutral_and_edge_cases():
    """Lista vacía -> 100.0 FULLY_TRACED; no-dict ignorados; prioridad case-insensitive."""
    from backend.schemas.projects import (
        validate_requirements_traceability_bidirectional_coverage,
    )

    for payload in (None, "no-list", 42):
        empty = validate_requirements_traceability_bidirectional_coverage(payload)
        assert empty["active_requirements_count"] == 0
        assert empty["fully_traced_count"] == 0
        assert empty["traceability_coverage_pct"] == 100.0
        assert empty["rtm_governance_status"] == "FULLY_TRACED"
        assert empty["is_valid"] is True

    mixed = validate_requirements_traceability_bidirectional_coverage(
        [
            "no-dict",
            42,
            {
                "requirement_id": "REQ-14",
                "priority_class": "could",
                "business_objective_id": "OBJ-14",
                "wbs_deliverable_id": "WBS-14",
                "verification_test_case_id": "TC-14",
                "is_deferred_or_descoped": False,
            },
        ]
    )
    assert mixed["active_requirements_count"] == 1
    assert mixed["fully_traced_count"] == 1
    assert mixed["traceability_coverage_pct"] == 100.0
    assert mixed["rtm_governance_status"] == "FULLY_TRACED"

    # Prioridad con espacios y mayúsculas: ' MANDATORY ' sin test -> unverified.
    case_insensitive = validate_requirements_traceability_bidirectional_coverage(
        [
            {
                "requirement_id": "REQ-15",
                "priority_class": "  MANDATORY ",
                "business_objective_id": "OBJ-15",
                "wbs_deliverable_id": "WBS-15",
                "verification_test_case_id": None,
                "is_deferred_or_descoped": False,
            }
        ]
    )
    assert case_insensitive["unverified_test_requirement_ids"] == ["REQ-15"]
    assert case_insensitive["rtm_governance_status"] == "TRACEABILITY_GAP"

    # IDs con whitespace cuentan como presentes (strip antes de evaluar).
    whitespace_ok = validate_requirements_traceability_bidirectional_coverage(
        [
            {
                "requirement_id": "REQ-16",
                "priority_class": "mandatory",
                "business_objective_id": "  OBJ-16  ",
                "wbs_deliverable_id": "  WBS-16  ",
                "verification_test_case_id": "  TC-16  ",
                "is_deferred_or_descoped": False,
            }
        ]
    )
    assert whitespace_ok["fully_traced_count"] == 1
    assert whitespace_ok["rtm_governance_status"] == "FULLY_TRACED"


def test_rtm_bidirectional_all_pass_and_precedence():
    """TRACEABILITY_GAP domina; status consolidation; validación directa vs __all__ del caso completo."""
    from backend.schemas.projects import (
        validate_requirements_traceability_bidirectional_coverage,
    )
    import backend.schemas.projects as mod

    mixed_breaches = validate_requirements_traceability_bidirectional_coverage(
        [
            {
                "requirement_id": "REQ-17",
                "priority_class": "mandatory",
                "business_objective_id": None,
                "wbs_deliverable_id": None,
                "verification_test_case_id": None,
                "is_deferred_or_descoped": False,
            }
        ]
    )
    # Sin test (mandatory) y sin WBS -> TRACEABILITY_GAP aunque también sin objetivo.
    assert mixed_breaches["rtm_governance_status"] == "TRACEABILITY_GAP"
    assert mixed_breaches["backward_untraced_requirement_ids"] == ["REQ-17"]

    empty_ok = validate_requirements_traceability_bidirectional_coverage([])
    assert empty_ok["is_valid"] is True

    plain_req = {
        "requirement_id": "REQ-18",
        "priority_class": "mandatory",
        "business_objective_id": "OBJ",
        "wbs_deliverable_id": "WBS",
        "verification_test_case_id": None,
        "is_deferred_or_descoped": False,
    }
    plain = validate_requirements_traceability_bidirectional_coverage([plain_req])
    assert plain["unverified_test_requirement_ids"] == ["REQ-18"]
    assert "validate_requirements_traceability_bidirectional_coverage" in mod.__all__


def test_validate_three_point_pert_and_triangular_calibrated():
    """Caso 1: Paquetes Beta y Triangular con 0 < O <= M <= P y dispersión controlada -> CALIBRATED."""
    from backend.schemas.projects import (
        validate_three_point_pert_and_triangular_estimates,
    )

    estimates = [
        {
            "work_package_id": "WP-101",
            "optimistic_o": 6.0,
            "most_likely_m": 9.0,
            "pessimistic_p": 12.0,
            "distribution": "beta",  # expected = 9.0, std = 1.0
        },
        {
            "work_package_id": "WP-102",
            "optimistic_o": 6.0,
            "most_likely_m": 9.0,
            "pessimistic_p": 15.0,
            "distribution": "triangular",  # expected = 10.0, std = sqrt((36+81+225-54-90-135)/18)=sqrt(63/18)=sqrt(3.5)=1.8708
        },
    ]
    res = validate_three_point_pert_and_triangular_estimates(
        estimates,
        max_uncertainty_ratio=3.0,
        max_cv_coefficient_of_variation_pct=35.0,
    )
    assert res["is_valid"] is True
    assert res["total_estimates"] == 2
    assert res["inverted_ordering_wp_ids"] == []
    assert res["excessive_spread_wp_ids"] == []
    assert res["total_pert_expected"] == 19.0
    assert res["portfolio_combined_std_dev"] == 2.12
    assert res["estimation_governance_status"] == "CALIBRATED"
    assert res["issues"] == []


def test_validate_three_point_pert_and_triangular_high_uncertainty_cone():
    """Caso 2: P/O > max_uncertainty_ratio o CV% > max_cv -> HIGH_UNCERTAINTY_CONE."""
    from backend.schemas.projects import (
        validate_three_point_pert_and_triangular_estimates,
    )

    estimates = [
        {
            "work_package_id": "WP-CONE",
            "optimistic_o": 4.0,
            "most_likely_m": 8.0,
            "pessimistic_p": 20.0,  # P/O = 5.0 > 3.0
            "distribution": "beta",
        }
    ]
    res = validate_three_point_pert_and_triangular_estimates(
        estimates,
        max_uncertainty_ratio=3.0,
        max_cv_coefficient_of_variation_pct=35.0,
    )
    assert res["is_valid"] is False
    assert res["total_estimates"] == 1
    assert res["inverted_ordering_wp_ids"] == []
    assert res["excessive_spread_wp_ids"] == ["WP-CONE"]
    assert res["estimation_governance_status"] == "HIGH_UNCERTAINTY_CONE"
    assert len(res["issues"]) >= 1


def test_validate_three_point_pert_and_triangular_invalid_bounds():
    """Caso 3: O <= 0 o O > M o M > P -> INVALID_BOUNDS."""
    from backend.schemas.projects import (
        validate_three_point_pert_and_triangular_estimates,
    )

    estimates = [
        {
            "work_package_id": "WP-INV-1",
            "optimistic_o": 12.0,
            "most_likely_m": 8.0,
            "pessimistic_p": 15.0,
            "distribution": "beta",
        },
        {
            "work_package_id": "WP-INV-2",
            "optimistic_o": 0.0,
            "most_likely_m": 5.0,
            "pessimistic_p": 10.0,
            "distribution": "triangular",
        },
    ]
    res = validate_three_point_pert_and_triangular_estimates(estimates)
    assert res["is_valid"] is False
    assert res["total_estimates"] == 2
    assert res["inverted_ordering_wp_ids"] == ["WP-INV-1", "WP-INV-2"]
    assert res["excessive_spread_wp_ids"] == []
    assert res["total_pert_expected"] == 0.0
    assert res["portfolio_combined_std_dev"] == 0.0
    assert res["estimation_governance_status"] == "INVALID_BOUNDS"
    assert len(res["issues"]) >= 2


def test_validate_three_point_pert_and_triangular_empty_and_export():
    """Caso 4: Entradas vacías/inválidas y presencia en __all__."""
    import backend.schemas.projects as mod
    from backend.schemas.projects import (
        validate_three_point_pert_and_triangular_estimates,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = validate_three_point_pert_and_triangular_estimates(payload)  # type: ignore[arg-type]
        assert empty["is_valid"] is True
        assert empty["total_estimates"] == 0
        assert empty["inverted_ordering_wp_ids"] == []
        assert empty["excessive_spread_wp_ids"] == []
        assert empty["total_pert_expected"] == 0.0
        assert empty["portfolio_combined_std_dev"] == 0.0
        assert empty["estimation_governance_status"] == "CALIBRATED"
        assert empty["issues"] == []

    assert "validate_three_point_pert_and_triangular_estimates" in mod.__all__


def test_validate_ccpm_critical_chain_buffer_fever_chart_green_protected():
    """Caso 1: Todas las cadenas con consumo de buffer <= umbral amarillo -> GREEN_PROTECTED."""
    from backend.schemas.projects import (
        validate_ccpm_critical_chain_buffer_fever_chart,
    )

    chains = [
        {
            "chain_id": "PB-MAIN",
            "chain_type": "project_buffer",
            "chain_completion_pct": 50.0,  # yellow=20+0.6*50=50, red=40+0.6*50=70
            "buffer_consumed_pct": 40.0,
        },
        {
            "chain_id": "FB-01",
            "chain_type": "feeding_buffer",
            "chain_completion_pct": 30.0,  # yellow=38, red=58
            "buffer_consumed_pct": 38.0,
        },
    ]
    res = validate_ccpm_critical_chain_buffer_fever_chart(chains)
    assert res["is_valid"] is True
    assert res["total_chains"] == 2
    assert res["red_zone_action_chain_ids"] == []
    assert res["yellow_zone_watch_chain_ids"] == []
    assert res["green_zone_healthy_chain_ids"] == ["PB-MAIN", "FB-01"]
    assert res["fever_chart_status"] == "GREEN_PROTECTED"
    assert res["issues"] == []


def test_validate_ccpm_critical_chain_buffer_fever_chart_yellow_plan_recovery():
    """Caso 2: Cadena en zona amarilla (yellow_threshold < consumed <= red_threshold) -> YELLOW_PLAN_RECOVERY."""
    from backend.schemas.projects import (
        validate_ccpm_critical_chain_buffer_fever_chart,
    )

    chains = [
        {
            "chain_id": "PB-MAIN",
            "chain_type": "project_buffer",
            "chain_completion_pct": 50.0,  # yellow=50, red=70
            "buffer_consumed_pct": 60.0,
        },
        {
            "chain_id": "FB-02",
            "chain_type": "feeding_buffer",
            "chain_completion_pct": 40.0,  # yellow=44, red=64
            "buffer_consumed_pct": 30.0,
        },
    ]
    res = validate_ccpm_critical_chain_buffer_fever_chart(chains)
    assert res["is_valid"] is False
    assert res["total_chains"] == 2
    assert res["red_zone_action_chain_ids"] == []
    assert res["yellow_zone_watch_chain_ids"] == ["PB-MAIN"]
    assert res["green_zone_healthy_chain_ids"] == ["FB-02"]
    assert res["fever_chart_status"] == "YELLOW_PLAN_RECOVERY"
    assert len(res["issues"]) >= 1


def test_validate_ccpm_critical_chain_buffer_fever_chart_red_recovery_required():
    """Caso 3: Consumo supera umbral rojo o > 100% -> RED_RECOVERY_REQUIRED."""
    from backend.schemas.projects import (
        validate_ccpm_critical_chain_buffer_fever_chart,
    )

    chains = [
        {
            "chain_id": "PB-RED",
            "chain_type": "project_buffer",
            "chain_completion_pct": 20.0,  # yellow=32, red=52
            "buffer_consumed_pct": 65.0,
        },
        {
            "chain_id": "FB-EXHAUSTED",
            "chain_type": "feeding_buffer",
            "chain_completion_pct": 100.0,  # red=100, pero > 100%
            "buffer_consumed_pct": 105.0,
        },
    ]
    res = validate_ccpm_critical_chain_buffer_fever_chart(chains)
    assert res["is_valid"] is False
    assert res["total_chains"] == 2
    assert res["red_zone_action_chain_ids"] == ["PB-RED", "FB-EXHAUSTED"]
    assert res["yellow_zone_watch_chain_ids"] == []
    assert res["green_zone_healthy_chain_ids"] == []
    assert res["fever_chart_status"] == "RED_RECOVERY_REQUIRED"
    assert len(res["issues"]) >= 2


def test_validate_ccpm_critical_chain_buffer_fever_chart_empty_and_export():
    """Caso 4: Entradas vacías/inválidas y presencia en __all__."""
    import backend.schemas.projects as mod
    from backend.schemas.projects import (
        validate_ccpm_critical_chain_buffer_fever_chart,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = validate_ccpm_critical_chain_buffer_fever_chart(payload)  # type: ignore[arg-type]
        assert empty["is_valid"] is True
        assert empty["total_chains"] == 0
        assert empty["red_zone_action_chain_ids"] == []
        assert empty["yellow_zone_watch_chain_ids"] == []
        assert empty["green_zone_healthy_chain_ids"] == []
        assert empty["fever_chart_status"] == "GREEN_PROTECTED"
        assert empty["issues"] == []

    assert "validate_ccpm_critical_chain_buffer_fever_chart" in mod.__all__




def test_validate_raci_responsibility_assignment_matrix_hygiene_non_compliant_paths():
    """Caso 1: sin accountable, multiple accountable y sin responsible -> NON_COMPLIANT."""
    from backend.schemas.projects import (
        validate_raci_responsibility_assignment_matrix_hygiene,
    )

    res = validate_raci_responsibility_assignment_matrix_hygiene(
        [
            {
                "deliverable_id": "D-01",
                "accountable_ids": [],
                "responsible_ids": ["R-1"],
                "consulted_ids": ["C-1"],
                "informed_ids": ["I-1"],
            },
            {
                "deliverable_id": "D-02",
                "accountable_ids": ["A-1", "A-2"],
                "responsible_ids": ["R-1", "R-2"],
                "consulted_ids": [],
                "informed_ids": [],
            },
            {
                "deliverable_id": "D-03",
                "accountable_ids": ["A-1"],
                "responsible_ids": [],
                "consulted_ids": [],
                "informed_ids": [],
            },
        ]
    )
    assert res["total_deliverables"] == 3
    assert res["zero_accountable_deliverable_ids"] == ["D-01"]
    assert res["multiple_accountable_deliverable_ids"] == ["D-02"]
    assert res["zero_responsible_deliverable_ids"] == ["D-03"]
    assert res["overloaded_responsible_deliverable_ids"] == []
    assert res["consultation_bottleneck_deliverable_ids"] == []
    assert res["raci_governance_status"] == "NON_COMPLIANT"
    assert res["is_raci_valid"] is False
    assert len(res["recommendations"]) == 3


def test_validate_raci_responsibility_assignment_matrix_hygiene_warning_paths():
    """Caso 2: sobrecarga R y cuello de botella C sin brechas A/R -> WARNING."""
    from backend.schemas.projects import (
        validate_raci_responsibility_assignment_matrix_hygiene,
    )

    res = validate_raci_responsibility_assignment_matrix_hygiene(
        [
            {
                "deliverable_id": "D-10",
                "accountable_ids": ["A-1"],
                "responsible_ids": ["R-1", "R-2", "R-3", "R-4"],
                "consulted_ids": [],
                "informed_ids": [],
            },
            {
                "deliverable_id": "D-11",
                "accountable_ids": ["A-9"],
                "responsible_ids": ["R-9"],
                "consulted_ids": ["C-1", "C-2", "C-3", "C-4", "C-5"],
                "informed_ids": [],
            },
        ]
    )
    assert res["total_deliverables"] == 2
    assert res["zero_accountable_deliverable_ids"] == []
    assert res["multiple_accountable_deliverable_ids"] == []
    assert res["zero_responsible_deliverable_ids"] == []
    assert res["overloaded_responsible_deliverable_ids"] == ["D-10"]
    assert res["consultation_bottleneck_deliverable_ids"] == ["D-11"]
    assert res["raci_governance_status"] == "WARNING"
    assert res["is_raci_valid"] is False
    assert len(res["recommendations"]) == 2


def test_validate_raci_responsibility_assignment_matrix_hygiene_compliant_and_thresholds():
    """Caso 3: fronteras exactas de umbrales y caso COMPLIANT."""
    from backend.schemas.projects import (
        validate_raci_responsibility_assignment_matrix_hygiene,
    )

    res = validate_raci_responsibility_assignment_matrix_hygiene(
        [
            {
                "deliverable_id": "D-20",
                "accountable_ids": ["A-1"],
                "responsible_ids": ["R-1", "R-2", "R-3"],
                "consulted_ids": ["C-1", "C-2", "C-3", "C-4"],
                "informed_ids": ["I-1"],
            }
        ]
    )
    assert res["total_deliverables"] == 1
    assert res["overloaded_responsible_deliverable_ids"] == []
    assert res["consultation_bottleneck_deliverable_ids"] == []
    assert res["raci_governance_status"] == "COMPLIANT"
    assert res["is_raci_valid"] is True
    assert res["recommendations"] == []

    tight = validate_raci_responsibility_assignment_matrix_hygiene(
        [
            {
                "deliverable_id": "D-21",
                "accountable_ids": ["A-1"],
                "responsible_ids": ["R-1"],
                "consulted_ids": [],
            }
        ],
        max_responsible_per_deliverable=0,
        max_consulted_per_deliverable=0,
    )
    assert tight["overloaded_responsible_deliverable_ids"] == ["D-21"]
    assert tight["raci_governance_status"] == "WARNING"


def test_validate_raci_responsibility_assignment_matrix_hygiene_invalid_entries_and_export():
    """Caso 4: entradas no-lista/no-dict y export en __all__."""
    import backend.schemas.projects as mod
    from backend.schemas.projects import (
        validate_raci_responsibility_assignment_matrix_hygiene,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = validate_raci_responsibility_assignment_matrix_hygiene(payload)  # type: ignore[arg-type]
        assert empty["total_deliverables"] == 0
        assert empty["zero_accountable_deliverable_ids"] == []
        assert empty["multiple_accountable_deliverable_ids"] == []
        assert empty["zero_responsible_deliverable_ids"] == []
        assert empty["overloaded_responsible_deliverable_ids"] == []
        assert empty["consultation_bottleneck_deliverable_ids"] == []
        assert empty["raci_governance_status"] == "COMPLIANT"
        assert empty["is_raci_valid"] is True
        assert empty["recommendations"] == []

    assert "validate_raci_responsibility_assignment_matrix_hygiene" in mod.__all__


def test_validate_monte_carlo_confidence_percentiles_and_contingency_valid():
    """Caso 1: Simulaciones con >=1000 iteraciones, percentiles monótonos y reserva suficiente ('VALID')."""
    from backend.schemas.projects import (
        validate_monte_carlo_confidence_percentiles_and_contingency,
    )

    sims = [
        {
            "simulation_id": "MC-01",
            "iterations_count": 5000,
            "deterministic_baseline": 100000.0,
            "p50_estimate": 100000.0,
            "p80_estimate": 115000.0,
            "p90_estimate": 125000.0,
            "allocated_contingency_reserve": 15000.0,
        },
        {
            "simulation_id": "MC-02",
            "iterations_count": 2000,
            "deterministic_baseline": 50000.0,
            "p50_estimate": 49000.0,
            "p80_estimate": 54000.0,
            "p90_estimate": 58000.0,
            "allocated_contingency_reserve": 3900.0,  # 2.5% shortfall <= 5%
        },
    ]
    res = validate_monte_carlo_confidence_percentiles_and_contingency(sims)
    assert res["total_simulations"] == 2
    assert res["insufficient_iterations_ids"] == []
    assert res["non_monotonic_percentile_ids"] == []
    assert res["optimistic_bias_ids"] == []
    assert res["underfunded_contingency_ids"] == []
    assert res["monte_carlo_governance_status"] == "VALID"
    assert res["is_monte_carlo_valid"] is True
    assert res["recommendations"] == []


def test_validate_monte_carlo_confidence_percentiles_and_contingency_warning():
    """Caso 2: Pocas iteraciones o sesgo optimista con reserva suficiente ('WARNING')."""
    from backend.schemas.projects import (
        validate_monte_carlo_confidence_percentiles_and_contingency,
    )

    sims = [
        {
            "simulation_id": "MC-10",
            "iterations_count": 500,  # < 1000
            "deterministic_baseline": 100000.0,
            "p50_estimate": 105000.0,  # baseline < p50 -> optimistic bias
            "p80_estimate": 115000.0,
            "p90_estimate": 122000.0,
            "allocated_contingency_reserve": 15000.0,
        }
    ]
    res = validate_monte_carlo_confidence_percentiles_and_contingency(sims)
    assert res["total_simulations"] == 1
    assert res["insufficient_iterations_ids"] == ["MC-10"]
    assert res["optimistic_bias_ids"] == ["MC-10"]
    assert res["non_monotonic_percentile_ids"] == []
    assert res["underfunded_contingency_ids"] == []
    assert res["monte_carlo_governance_status"] == "WARNING"
    assert res["is_monte_carlo_valid"] is False
    assert len(res["recommendations"]) >= 2


def test_validate_monte_carlo_confidence_percentiles_and_contingency_invalid():
    """Caso 3: Percentiles no monótonos o reserva de contingencia subfinanciada ('INVALID')."""
    from backend.schemas.projects import (
        validate_monte_carlo_confidence_percentiles_and_contingency,
    )

    sims = [
        {
            "simulation_id": "MC-20",
            "iterations_count": 2000,
            "deterministic_baseline": 100000.0,
            "p50_estimate": 110000.0,
            "p80_estimate": 108000.0,  # non-monotonic
            "p90_estimate": 120000.0,
            "allocated_contingency_reserve": 20000.0,
        },
        {
            "simulation_id": "MC-21",
            "iterations_count": 3000,
            "deterministic_baseline": 100000.0,
            "p50_estimate": 100000.0,
            "p80_estimate": 115000.0,
            "p90_estimate": 130000.0,
            "allocated_contingency_reserve": 15000.0,  # P90 requires 30000 -> 50% shortfall
        },
    ]
    res = validate_monte_carlo_confidence_percentiles_and_contingency(
        sims,
        target_confidence_level="P90",
    )
    assert res["total_simulations"] == 2
    assert res["non_monotonic_percentile_ids"] == ["MC-20"]
    assert res["underfunded_contingency_ids"] == ["MC-21"]
    assert res["monte_carlo_governance_status"] == "INVALID"
    assert res["is_monte_carlo_valid"] is False
    assert len(res["recommendations"]) >= 2


def test_validate_monte_carlo_confidence_percentiles_and_contingency_empty_and_export():
    """Caso 4: Entradas vacías/inválidas y exportación en __all__."""
    import backend.schemas.projects as mod
    from backend.schemas.projects import (
        validate_monte_carlo_confidence_percentiles_and_contingency,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = validate_monte_carlo_confidence_percentiles_and_contingency(payload)  # type: ignore[arg-type]
        assert empty["total_simulations"] == 0
        assert empty["insufficient_iterations_ids"] == []
        assert empty["non_monotonic_percentile_ids"] == []
        assert empty["optimistic_bias_ids"] == []
        assert empty["underfunded_contingency_ids"] == []
        assert empty["monte_carlo_governance_status"] == "VALID"
        assert empty["is_monte_carlo_valid"] is True
        assert empty["recommendations"] == []

    assert (
        "validate_monte_carlo_confidence_percentiles_and_contingency" in mod.__all__
    )


def test_validate_make_or_buy_tco_and_strategic_lock_in_sound():
    """Caso 1: Decisiones Make/Buy económicamente óptimas, core IP interna y bajo lock-in -> SOUND."""
    from backend.schemas.projects import validate_make_or_buy_tco_and_strategic_lock_in

    options = [
        {
            "component_id": "CMP-CORE-ENGINE",
            "selected_decision": "MAKE",
            "make_upfront_cost": 40000.0,
            "make_monthly_opex": 1000.0,
            "buy_upfront_cost": 20000.0,
            "buy_monthly_license_cost": 2500.0,
            "buy_switching_exit_cost": 15000.0,
            "is_core_intellectual_property": True,
        },
        {
            "component_id": "CMP-AUTH-SAAS",
            "selected_decision": "BUY",
            "make_upfront_cost": 50000.0,
            "make_monthly_opex": 1500.0,
            "buy_upfront_cost": 5000.0,
            "buy_monthly_license_cost": 1000.0,
            "buy_switching_exit_cost": 8000.0,
            "is_core_intellectual_property": False,
        },
    ]
    res = validate_make_or_buy_tco_and_strategic_lock_in(
        options, evaluation_horizon_months=36, max_switching_cost_ratio_pct=35.0
    )
    assert res["total_components"] == 2
    assert res["total_selected_tco"] == 117000.0
    assert res["core_ip_outsourced_component_ids"] == []
    assert res["uneconomic_decision_component_ids"] == []
    assert res["vendor_lock_in_risk_component_ids"] == []
    assert res["make_or_buy_governance_status"] == "SOUND"
    assert res["is_make_or_buy_valid"] is True
    assert res["recommendations"] == []


def test_validate_make_or_buy_tco_and_strategic_lock_in_warning():
    """Caso 2: Una decisión antieconómica o alto costo de salida (>35%) sin externalizar core IP -> WARNING."""
    from backend.schemas.projects import validate_make_or_buy_tco_and_strategic_lock_in

    options = [
        {
            "component_id": "CMP-LOGGING",
            "selected_decision": "MAKE",
            "make_upfront_cost": 60000.0,
            "make_monthly_opex": 2000.0,
            "buy_upfront_cost": 4000.0,
            "buy_monthly_license_cost": 1000.0,
            "buy_switching_exit_cost": 2000.0,
            "is_core_intellectual_property": False,
        },
        {
            "component_id": "CMP-CRM",
            "selected_decision": "BUY",
            "make_upfront_cost": 80000.0,
            "make_monthly_opex": 2000.0,
            "buy_upfront_cost": 14000.0,
            "buy_monthly_license_cost": 1000.0,
            "buy_switching_exit_cost": 25000.0,
            "is_core_intellectual_property": False,
        },
    ]
    res = validate_make_or_buy_tco_and_strategic_lock_in(
        options, evaluation_horizon_months=36, max_switching_cost_ratio_pct=35.0
    )
    assert res["total_components"] == 2
    assert res["core_ip_outsourced_component_ids"] == []
    assert res["uneconomic_decision_component_ids"] == ["CMP-LOGGING"]
    assert res["vendor_lock_in_risk_component_ids"] == ["CMP-CRM"]
    assert res["make_or_buy_governance_status"] == "WARNING"
    assert res["is_make_or_buy_valid"] is False
    assert len(res["recommendations"]) >= 2


def test_validate_make_or_buy_tco_and_strategic_lock_in_critical():
    """Caso 3: Propiedad intelectual core externalizada (BUY) -> CRITICAL."""
    from backend.schemas.projects import validate_make_or_buy_tco_and_strategic_lock_in

    options = [
        {
            "component_id": "CMP-ALGO-PROPRIETARY",
            "selected_decision": "BUY",
            "make_upfront_cost": 50000.0,
            "make_monthly_opex": 1000.0,
            "buy_upfront_cost": 30000.0,
            "buy_monthly_license_cost": 3000.0,
            "buy_switching_exit_cost": 70000.0,
            "is_core_intellectual_property": True,
        }
    ]
    res = validate_make_or_buy_tco_and_strategic_lock_in(options)
    assert res["total_components"] == 1
    assert res["core_ip_outsourced_component_ids"] == ["CMP-ALGO-PROPRIETARY"]
    assert res["uneconomic_decision_component_ids"] == ["CMP-ALGO-PROPRIETARY"]
    assert res["vendor_lock_in_risk_component_ids"] == ["CMP-ALGO-PROPRIETARY"]
    assert res["make_or_buy_governance_status"] == "CRITICAL"
    assert res["is_make_or_buy_valid"] is False
    assert len(res["recommendations"]) >= 2


def test_validate_make_or_buy_tco_and_strategic_lock_in_empty_and_export():
    """Caso 4: Entradas vacías/inválidas y exportación en __all__."""
    import backend.schemas.projects as mod
    from backend.schemas.projects import validate_make_or_buy_tco_and_strategic_lock_in

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = validate_make_or_buy_tco_and_strategic_lock_in(payload)  # type: ignore[arg-type]
        assert empty["total_components"] == 0
        assert empty["total_selected_tco"] == 0.0
        assert empty["core_ip_outsourced_component_ids"] == []
        assert empty["uneconomic_decision_component_ids"] == []
        assert empty["vendor_lock_in_risk_component_ids"] == []
        assert empty["make_or_buy_governance_status"] == "SOUND"
        assert empty["is_make_or_buy_valid"] is True
        assert empty["recommendations"] == []

    assert "validate_make_or_buy_tco_and_strategic_lock_in" in mod.__all__


def test_validate_resource_calendar_timezone_overlap_and_allocation_aligned():
    """Caso 1: Equipo con >=3h de traslape síncrono UTC, asignación <=100% y <=2 proyectos -> ALIGNED."""
    from backend.schemas.projects import (
        validate_resource_calendar_timezone_overlap_and_allocation,
    )

    members = [
        {
            "member_id": "DEV-BOGOTA",
            "utc_work_start_hour": 13.0,
            "utc_work_end_hour": 21.0,
            "total_allocation_pct": 100.0,
            "concurrent_projects_count": 1,
            "unmitigated_holiday_conflict_days": 0,
        },
        {
            "member_id": "DEV-MADRID",
            "utc_work_start_hour": 8.0,
            "utc_work_end_hour": 17.0,
            "total_allocation_pct": 80.0,
            "concurrent_projects_count": 2,
            "unmitigated_holiday_conflict_days": 0,
        },
    ]
    res = validate_resource_calendar_timezone_overlap_and_allocation(
        members, min_core_overlap_hours=3.0, max_concurrent_projects_per_member=2
    )
    assert res["total_members"] == 2
    assert res["team_synchronous_overlap_hours"] == 4.0
    assert res["insufficient_timezone_overlap"] is False
    assert res["overallocated_member_ids"] == []
    assert res["context_switching_fragmented_member_ids"] == []
    assert res["holiday_conflict_member_ids"] == []
    assert res["calendar_governance_status"] == "ALIGNED"
    assert res["is_calendar_valid"] is True
    assert res["recommendations"] == []


def test_validate_resource_calendar_timezone_overlap_and_allocation_warning():
    """Caso 2: Traslape bajo (<3h pero >0h), fragmentación (>2 proyectos) y festivos sin mitigar -> WARNING."""
    from backend.schemas.projects import (
        validate_resource_calendar_timezone_overlap_and_allocation,
    )

    members = [
        {
            "member_id": "DEV-SF",
            "utc_work_start_hour": 15.0,
            "utc_work_end_hour": 23.0,
            "total_allocation_pct": 100.0,
            "concurrent_projects_count": 4,
            "unmitigated_holiday_conflict_days": 2,
        },
        {
            "member_id": "DEV-BERLIN",
            "utc_work_start_hour": 8.0,
            "utc_work_end_hour": 16.5,
            "total_allocation_pct": 90.0,
            "concurrent_projects_count": 1,
            "unmitigated_holiday_conflict_days": 0,
        },
    ]
    res = validate_resource_calendar_timezone_overlap_and_allocation(
        members, min_core_overlap_hours=3.0, max_concurrent_projects_per_member=2
    )
    assert res["total_members"] == 2
    assert res["team_synchronous_overlap_hours"] == 1.5
    assert res["insufficient_timezone_overlap"] is True
    assert res["overallocated_member_ids"] == []
    assert res["context_switching_fragmented_member_ids"] == ["DEV-SF"]
    assert res["holiday_conflict_member_ids"] == ["DEV-SF"]
    assert res["calendar_governance_status"] == "WARNING"
    assert res["is_calendar_valid"] is False
    assert len(res["recommendations"]) >= 3


def test_validate_resource_calendar_timezone_overlap_and_allocation_critical():
    """Caso 3: Miembro sobreasignado (>100%) y cero traslape horario síncrono (0.0h) -> CRITICAL."""
    from backend.schemas.projects import (
        validate_resource_calendar_timezone_overlap_and_allocation,
    )

    members = [
        {
            "member_id": "DEV-TOKYO",
            "utc_work_start_hour": 0.0,
            "utc_work_end_hour": 8.0,
            "total_allocation_pct": 135.0,
            "concurrent_projects_count": 3,
            "unmitigated_holiday_conflict_days": 1,
        },
        {
            "member_id": "DEV-NY",
            "utc_work_start_hour": 14.0,
            "utc_work_end_hour": 22.0,
            "total_allocation_pct": 100.0,
            "concurrent_projects_count": 1,
            "unmitigated_holiday_conflict_days": 0,
        },
    ]
    res = validate_resource_calendar_timezone_overlap_and_allocation(members)
    assert res["total_members"] == 2
    assert res["team_synchronous_overlap_hours"] == 0.0
    assert res["insufficient_timezone_overlap"] is True
    assert res["overallocated_member_ids"] == ["DEV-TOKYO"]
    assert res["calendar_governance_status"] == "CRITICAL"
    assert res["is_calendar_valid"] is False
    assert len(res["recommendations"]) >= 2


def test_validate_resource_calendar_timezone_overlap_and_allocation_empty_and_export():
    """Caso 4: Entradas vacías/inválidas y exportación en __all__."""
    import backend.schemas.projects as mod
    from backend.schemas.projects import (
        validate_resource_calendar_timezone_overlap_and_allocation,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = validate_resource_calendar_timezone_overlap_and_allocation(payload)  # type: ignore[arg-type]
        assert empty["total_members"] == 0
        assert empty["team_synchronous_overlap_hours"] == 8.0
        assert empty["insufficient_timezone_overlap"] is False
        assert empty["overallocated_member_ids"] == []
        assert empty["context_switching_fragmented_member_ids"] == []
        assert empty["holiday_conflict_member_ids"] == []
        assert empty["calendar_governance_status"] == "ALIGNED"
        assert empty["is_calendar_valid"] is True
        assert empty["recommendations"] == []

    assert (
        "validate_resource_calendar_timezone_overlap_and_allocation" in mod.__all__
    )


def test_validate_wbs_work_package_8_80_granularity_and_dictionary_well_decomposed():
    """Caso 1: Paquetes hoja entre 8h y 80h, nivel <=6 y diccionario WBS completo -> WELL_DECOMPOSED."""
    from backend.schemas.projects import (
        validate_wbs_work_package_8_80_granularity_and_dictionary,
    )

    wps = [
        {
            "wp_id": "WBS-1.0",
            "is_leaf_package": False,
            "estimated_effort_hours": 120.0,
            "wbs_level": 1,
            "has_acceptance_criteria": True,
            "has_assigned_control_account": True,
            "deliverable_noun_phrase_valid": True,
        },
        {
            "wp_id": "WBS-1.1",
            "is_leaf_package": True,
            "estimated_effort_hours": 40.0,
            "wbs_level": 2,
            "has_acceptance_criteria": True,
            "has_assigned_control_account": True,
            "deliverable_noun_phrase_valid": True,
        },
        {
            "wp_id": "WBS-1.2",
            "is_leaf_package": True,
            "estimated_effort_hours": 80.0,
            "wbs_level": 2,
            "has_acceptance_criteria": True,
            "has_assigned_control_account": True,
            "deliverable_noun_phrase_valid": True,
        },
    ]
    res = validate_wbs_work_package_8_80_granularity_and_dictionary(
        wps, min_effort_hours=8.0, max_effort_hours=80.0, max_wbs_depth_level=6
    )
    assert res["total_work_packages"] == 3
    assert res["micromanaged_wp_ids"] == []
    assert res["oversized_wp_ids"] == []
    assert res["excessive_depth_wp_ids"] == []
    assert res["incomplete_dictionary_wp_ids"] == []
    assert res["wbs_governance_status"] == "WELL_DECOMPOSED"
    assert res["is_wbs_valid"] is True
    assert res["recommendations"] == []


def test_validate_wbs_work_package_8_80_granularity_and_dictionary_warning():
    """Caso 2: Paquete hoja <8h (micromanagement) y nivel >6 sin paquetes >80h ni diccionario incompleto -> WARNING."""
    from backend.schemas.projects import (
        validate_wbs_work_package_8_80_granularity_and_dictionary,
    )

    wps = [
        {
            "wp_id": "WBS-1.1.1.1.1.1.1",
            "is_leaf_package": True,
            "estimated_effort_hours": 3.5,
            "wbs_level": 7,
            "has_acceptance_criteria": True,
            "has_assigned_control_account": True,
            "deliverable_noun_phrase_valid": True,
        }
    ]
    res = validate_wbs_work_package_8_80_granularity_and_dictionary(
        wps, min_effort_hours=8.0, max_effort_hours=80.0, max_wbs_depth_level=6
    )
    assert res["total_work_packages"] == 1
    assert res["micromanaged_wp_ids"] == ["WBS-1.1.1.1.1.1.1"]
    assert res["oversized_wp_ids"] == []
    assert res["excessive_depth_wp_ids"] == ["WBS-1.1.1.1.1.1.1"]
    assert res["incomplete_dictionary_wp_ids"] == []
    assert res["wbs_governance_status"] == "WARNING"
    assert res["is_wbs_valid"] is False
    assert len(res["recommendations"]) >= 2


def test_validate_wbs_work_package_8_80_granularity_and_dictionary_invalid():
    """Caso 3: Paquete hoja >80h y diccionario WBS sin criterios de aceptación o cuenta de control -> INVALID_WBS."""
    from backend.schemas.projects import (
        validate_wbs_work_package_8_80_granularity_and_dictionary,
    )

    wps = [
        {
            "wp_id": "WBS-2.1",
            "is_leaf_package": True,
            "estimated_effort_hours": 160.0,
            "wbs_level": 2,
            "has_acceptance_criteria": False,
            "has_assigned_control_account": True,
            "deliverable_noun_phrase_valid": True,
        }
    ]
    res = validate_wbs_work_package_8_80_granularity_and_dictionary(wps)
    assert res["total_work_packages"] == 1
    assert res["oversized_wp_ids"] == ["WBS-2.1"]
    assert res["incomplete_dictionary_wp_ids"] == ["WBS-2.1"]
    assert res["wbs_governance_status"] == "INVALID_WBS"
    assert res["is_wbs_valid"] is False
    assert len(res["recommendations"]) >= 2


def test_validate_wbs_work_package_8_80_granularity_and_dictionary_empty_and_export():
    """Caso 4: Entradas vacías/inválidas y exportación en __all__."""
    import backend.schemas.projects as mod
    from backend.schemas.projects import (
        validate_wbs_work_package_8_80_granularity_and_dictionary,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = validate_wbs_work_package_8_80_granularity_and_dictionary(payload)  # type: ignore[arg-type]
        assert empty["total_work_packages"] == 0
        assert empty["micromanaged_wp_ids"] == []
        assert empty["oversized_wp_ids"] == []
        assert empty["excessive_depth_wp_ids"] == []
        assert empty["incomplete_dictionary_wp_ids"] == []
        assert empty["wbs_governance_status"] == "WELL_DECOMPOSED"
        assert empty["is_wbs_valid"] is True
        assert empty["recommendations"] == []

    assert (
        "validate_wbs_work_package_8_80_granularity_and_dictionary" in mod.__all__
    )


def test_validate_risk_probability_impact_matrix_and_appetite_thresholds_miscalibrated():
    from backend.schemas.projects import (
        validate_risk_probability_impact_matrix_and_appetite_thresholds,
    )

    res = validate_risk_probability_impact_matrix_and_appetite_thresholds(
        [
            {
                "risk_id": "RSK-SCALE",
                "probability": 1.2,
                "impact_weight": 0.5,
                "days_to_impact_proximity": 30,
                "assigned_tier": "HIGH",
                "has_active_mitigation_plan": True,
                "on_watchlist": True,
            },
            {
                "risk_id": "RSK-UNDERTIER",
                "probability": 0.5,
                "impact_weight": 0.5,
                "days_to_impact_proximity": 25,
                "assigned_tier": "MODERATE",
                "has_active_mitigation_plan": True,
                "on_watchlist": True,
            },
            {
                "risk_id": "RSK-URGENT-UNMIT",
                "probability": 0.2,
                "impact_weight": 0.4,
                "days_to_impact_proximity": 10,
                "assigned_tier": "MODERATE",
                "has_active_mitigation_plan": False,
                "on_watchlist": True,
            },
        ],
        high_risk_score_threshold=0.18,
        urgency_days_threshold=14,
    )
    assert res["total_risks"] == 3
    assert res["invalid_scale_risk_ids"] == ["RSK-SCALE"]
    assert res["undertiered_high_risk_ids"] == ["RSK-UNDERTIER"]
    assert res["unmitigated_high_or_urgent_risk_ids"] == ["RSK-URGENT-UNMIT"]
    assert res["pi_matrix_governance_status"] == "MISCALIBRATED"
    assert res["is_pi_matrix_valid"] is False
    assert len(res["recommendations"]) >= 3


def test_validate_risk_probability_impact_matrix_and_appetite_thresholds_warning():
    from backend.schemas.projects import (
        validate_risk_probability_impact_matrix_and_appetite_thresholds,
    )

    res = validate_risk_probability_impact_matrix_and_appetite_thresholds(
        [
            {
                "risk_id": "RSK-LOW-ORPHAN",
                "probability": 0.1,
                "impact_weight": 0.2,
                "days_to_impact_proximity": 45,
                "assigned_tier": "LOW",
                "has_active_mitigation_plan": False,
                "on_watchlist": False,
            }
        ],
        high_risk_score_threshold=0.18,
        urgency_days_threshold=14,
    )
    assert res["invalid_scale_risk_ids"] == []
    assert res["undertiered_high_risk_ids"] == []
    assert res["unmitigated_high_or_urgent_risk_ids"] == []
    assert res["unmonitored_low_risk_ids"] == ["RSK-LOW-ORPHAN"]
    assert res["pi_matrix_governance_status"] == "WARNING"
    assert res["is_pi_matrix_valid"] is False


def test_validate_risk_probability_impact_matrix_and_appetite_thresholds_calibrated():
    from backend.schemas.projects import (
        validate_risk_probability_impact_matrix_and_appetite_thresholds,
    )

    res = validate_risk_probability_impact_matrix_and_appetite_thresholds(
        [
            {
                "risk_id": "RSK-HIGH-OK",
                "probability": 0.6,
                "impact_weight": 0.4,
                "days_to_impact_proximity": 7,
                "assigned_tier": "HIGH",
                "has_active_mitigation_plan": True,
                "on_watchlist": True,
            },
            {
                "risk_id": "RSK-LOW-WATCHED",
                "probability": 0.1,
                "impact_weight": 0.2,
                "days_to_impact_proximity": 60,
                "assigned_tier": "LOW",
                "has_active_mitigation_plan": False,
                "on_watchlist": True,
            },
        ]
    )
    assert res["total_risks"] == 2
    assert res["invalid_scale_risk_ids"] == []
    assert res["undertiered_high_risk_ids"] == []
    assert res["unmitigated_high_or_urgent_risk_ids"] == []
    assert res["unmonitored_low_risk_ids"] == []
    assert res["pi_matrix_governance_status"] == "CALIBRATED"
    assert res["is_pi_matrix_valid"] is True
    assert res["recommendations"] == []


def test_validate_risk_probability_impact_matrix_and_appetite_thresholds_empty_and_export():
    import backend.schemas.projects as mod
    from backend.schemas.projects import (
        validate_risk_probability_impact_matrix_and_appetite_thresholds,
    )

    for payload in (None, [], "invalid", [{"risk_id": "   "}]):
        empty = validate_risk_probability_impact_matrix_and_appetite_thresholds(payload)  # type: ignore[arg-type]
        assert empty["total_risks"] == 0
        assert empty["invalid_scale_risk_ids"] == []
        assert empty["undertiered_high_risk_ids"] == []
        assert empty["unmitigated_high_or_urgent_risk_ids"] == []
        assert empty["unmonitored_low_risk_ids"] == []
        assert empty["pi_matrix_governance_status"] == "CALIBRATED"
        assert empty["is_pi_matrix_valid"] is True
        assert empty["recommendations"] == []

    assert (
        "validate_risk_probability_impact_matrix_and_appetite_thresholds"
        in mod.__all__
    )


def test_validate_ccpm_fever_chart_and_buffer_consumption_fever_breach_unmitigated():
    from backend.schemas.projects import (
        validate_ccpm_fever_chart_and_buffer_consumption,
    )

    res = validate_ccpm_fever_chart_and_buffer_consumption(
        [
            {
                "chain_id": "CC-MAIN",
                "buffer_type": "PROJECT_BUFFER",
                "chain_completion_pct": 40.0,
                "buffer_total_days": 20.0,
                "buffer_consumed_days": 15.0,
                "has_recovery_plan": False,
            },
            {
                "chain_id": "CC-FEED-01",
                "buffer_type": "FEEDING_BUFFER",
                "chain_completion_pct": 50.0,
                "buffer_total_days": 10.0,
                "buffer_consumed_days": 4.0,
                "has_recovery_plan": True,
            },
        ],
        red_zone_slope_factor=0.7,
        red_zone_intercept_pct=30.0,
        yellow_zone_intercept_pct=15.0,
    )
    assert res["total_chains_evaluated"] == 2
    assert res["red_zone_count"] == 1
    assert res["green_zone_count"] == 1
    assert res["yellow_zone_count"] == 0
    assert res["unmitigated_red_zone_chain_ids"] == ["CC-MAIN"]
    assert res["max_buffer_burn_index"] == 1.88
    assert res["fever_chart_status"] == "FEVER_BREACH_UNMITIGATED"
    assert res["is_ccpm_buffer_compliant"] is False


def test_validate_ccpm_fever_chart_and_buffer_consumption_critical_red_mitigated_and_watch_yellow():
    from backend.schemas.projects import (
        validate_ccpm_fever_chart_and_buffer_consumption,
    )

    red_mit = validate_ccpm_fever_chart_and_buffer_consumption(
        [
            {
                "chain_id": "CC-MIT",
                "buffer_type": "PROJECT_BUFFER",
                "chain_completion_pct": 20.0,
                "buffer_total_days": 10.0,
                "buffer_consumed_days": 6.0,
                "has_recovery_plan": True,
            }
        ]
    )
    assert red_mit["red_zone_count"] == 1
    assert red_mit["unmitigated_red_zone_chain_ids"] == []
    assert red_mit["fever_chart_status"] == "CRITICAL_RED_MITIGATED"
    assert red_mit["is_ccpm_buffer_compliant"] is True

    yellow = validate_ccpm_fever_chart_and_buffer_consumption(
        [
            {
                "chain_id": "CC-YEL",
                "buffer_type": "FEEDING_BUFFER",
                "chain_completion_pct": 40.0,
                "buffer_total_days": 20.0,
                "buffer_consumed_days": 10.0,
                "has_recovery_plan": False,
            }
        ]
    )
    assert yellow["yellow_zone_count"] == 1
    assert yellow["red_zone_count"] == 0
    assert yellow["fever_chart_status"] == "WATCH_YELLOW"
    assert yellow["is_ccpm_buffer_compliant"] is True


def test_validate_ccpm_fever_chart_and_buffer_consumption_healthy_green():
    from backend.schemas.projects import (
        validate_ccpm_fever_chart_and_buffer_consumption,
    )

    res = validate_ccpm_fever_chart_and_buffer_consumption(
        [
            {
                "chain_id": "CC-GRN",
                "buffer_type": "PROJECT_BUFFER",
                "chain_completion_pct": 50.0,
                "buffer_total_days": 20.0,
                "buffer_consumed_days": 5.0,
                "has_recovery_plan": False,
            }
        ]
    )
    assert res["total_chains_evaluated"] == 1
    assert res["green_zone_count"] == 1
    assert res["yellow_zone_count"] == 0
    assert res["red_zone_count"] == 0
    assert res["unmitigated_red_zone_chain_ids"] == []
    assert res["max_buffer_burn_index"] == 0.5
    assert res["fever_chart_status"] == "HEALTHY_GREEN"
    assert res["is_ccpm_buffer_compliant"] is True


def test_validate_ccpm_fever_chart_and_buffer_consumption_empty_and_export():
    import backend.schemas.projects as mod
    from backend.schemas.projects import (
        validate_ccpm_fever_chart_and_buffer_consumption,
    )

    for payload in (None, [], "invalid", [{"chain_id": "   "}]):
        empty = validate_ccpm_fever_chart_and_buffer_consumption(payload)  # type: ignore[arg-type]
        assert empty["total_chains_evaluated"] == 0
        assert empty["green_zone_count"] == 0
        assert empty["yellow_zone_count"] == 0
        assert empty["red_zone_count"] == 0
        assert empty["unmitigated_red_zone_chain_ids"] == []
        assert empty["max_buffer_burn_index"] == 0.0
        assert empty["fever_chart_status"] == "HEALTHY_GREEN"
        assert empty["is_ccpm_buffer_compliant"] is True

    assert "validate_ccpm_fever_chart_and_buffer_consumption" in mod.__all__


def test_validate_sprint_velocity_volatility_and_commitment_reliability_unpredictable_churn():
    from backend.schemas.projects import (
        validate_sprint_velocity_volatility_and_commitment_reliability,
    )

    res = validate_sprint_velocity_volatility_and_commitment_reliability(
        [
            {
                "sprint_id": "SPR-01",
                "committed_story_points": 40.0,
                "completed_story_points": 20.0,
                "carryover_story_points": 15.0,
                "unplanned_scope_added_points": 5.0,
            },
            {
                "sprint_id": "SPR-02",
                "committed_story_points": 40.0,
                "completed_story_points": 36.0,
                "carryover_story_points": 4.0,
                "unplanned_scope_added_points": 0.0,
            },
        ],
        min_say_do_ratio_pct=80.0,
        max_carryover_rate_pct=20.0,
        max_velocity_cv_pct=30.0,
    )
    assert res["total_sprints_evaluated"] == 2
    assert res["mean_velocity"] == 28.0
    assert res["unreliable_commitment_sprint_ids"] == ["SPR-01"]
    assert res["excessive_carryover_sprint_ids"] == ["SPR-01"]
    assert res["predictability_status"] == "UNPREDICTABLE_CHURN"
    assert res["is_sprint_cadence_compliant"] is False


def test_validate_sprint_velocity_volatility_and_commitment_reliability_volatile_velocity():
    from backend.schemas.projects import (
        validate_sprint_velocity_volatility_and_commitment_reliability,
    )

    res = validate_sprint_velocity_volatility_and_commitment_reliability(
        [
            {
                "sprint_id": "SPR-10",
                "committed_story_points": 20.0,
                "completed_story_points": 20.0,
                "carryover_story_points": 0.0,
            },
            {
                "sprint_id": "SPR-11",
                "committed_story_points": 60.0,
                "completed_story_points": 60.0,
                "carryover_story_points": 0.0,
            },
        ],
        min_say_do_ratio_pct=80.0,
        max_carryover_rate_pct=20.0,
        max_velocity_cv_pct=30.0,
    )
    assert res["unreliable_commitment_sprint_ids"] == []
    assert res["excessive_carryover_sprint_ids"] == []
    assert res["mean_velocity"] == 40.0
    assert res["velocity_cv_pct"] == 50.0
    assert res["predictability_status"] == "VOLATILE_VELOCITY"
    assert res["is_sprint_cadence_compliant"] is False


def test_validate_sprint_velocity_volatility_and_commitment_reliability_predictable_cadence():
    from backend.schemas.projects import (
        validate_sprint_velocity_volatility_and_commitment_reliability,
    )

    res = validate_sprint_velocity_volatility_and_commitment_reliability(
        [
            {
                "sprint_id": "SPR-20",
                "committed_story_points": 40.0,
                "completed_story_points": 38.0,
                "carryover_story_points": 2.0,
            },
            {
                "sprint_id": "SPR-21",
                "committed_story_points": 40.0,
                "completed_story_points": 42.0,
                "carryover_story_points": 0.0,
            },
        ]
    )
    assert res["total_sprints_evaluated"] == 2
    assert res["mean_velocity"] == 40.0
    assert res["velocity_cv_pct"] == 5.0
    assert res["unreliable_commitment_sprint_ids"] == []
    assert res["excessive_carryover_sprint_ids"] == []
    assert res["predictability_status"] == "PREDICTABLE_CADENCE"
    assert res["is_sprint_cadence_compliant"] is True


def test_validate_sprint_velocity_volatility_and_commitment_reliability_empty_and_export():
    import backend.schemas.projects as mod
    from backend.schemas.projects import (
        validate_sprint_velocity_volatility_and_commitment_reliability,
    )

    for payload in (None, [], "invalid", [{"sprint_id": "   "}]):
        empty = validate_sprint_velocity_volatility_and_commitment_reliability(payload)  # type: ignore[arg-type]
        assert empty["total_sprints_evaluated"] == 0
        assert empty["mean_velocity"] == 0.0
        assert empty["velocity_cv_pct"] == 0.0
        assert empty["unreliable_commitment_sprint_ids"] == []
        assert empty["excessive_carryover_sprint_ids"] == []
        assert empty["predictability_status"] == "PREDICTABLE_CADENCE"
        assert empty["is_sprint_cadence_compliant"] is True

    assert (
        "validate_sprint_velocity_volatility_and_commitment_reliability"
        in mod.__all__
    )


def test_validate_portfolio_frontier_constraint_breach_paths():
    """Caso 1: techo de presupuesto excedido o desalineación estratégica -> PORTFOLIO_CONSTRAINT_BREACH."""
    from backend.schemas.projects import (
        validate_portfolio_efficient_frontier_and_budget_knapsack,
    )

    res_budget = validate_portfolio_efficient_frontier_and_budget_knapsack(
        [
            {
                "project_id": "PRJ-01",
                "expected_npv_return": 200000.0,
                "risk_volatility_cost": 100000.0,
                "required_capex_budget": 90000.0,
                "strategic_fit_score": 80.0,
                "is_selected_in_portfolio": True,
            },
            {
                "project_id": "PRJ-02",
                "expected_npv_return": 150000.0,
                "risk_volatility_cost": 50000.0,
                "required_capex_budget": 60000.0,
                "strategic_fit_score": 70.0,
                "is_selected_in_portfolio": True,
            },
        ],
        total_portfolio_budget_cap=100000.0,
    )
    assert res_budget["total_candidates_evaluated"] == 2
    assert res_budget["selected_projects_count"] == 2
    assert res_budget["selected_total_capex"] == 150000.0
    assert res_budget["is_budget_cap_exceeded"] is True
    assert res_budget["portfolio_optimization_status"] == "PORTFOLIO_CONSTRAINT_BREACH"
    assert res_budget["is_portfolio_frontier_compliant"] is False

    # Alineación: seleccionado con fit bajo (cap no roto).
    res_misaligned = validate_portfolio_efficient_frontier_and_budget_knapsack(
        [
            {
                "project_id": "PRJ-03",
                "expected_npv_return": 150000.0,
                "risk_volatility_cost": 100000.0,
                "required_capex_budget": 40000.0,
                "strategic_fit_score": 50.0,
                "is_selected_in_portfolio": True,
            },
        ]
    )
    assert res_misaligned["is_budget_cap_exceeded"] is False
    assert res_misaligned["strategically_misaligned_selected_ids"] == ["PRJ-03"]
    assert res_misaligned["portfolio_optimization_status"] == "PORTFOLIO_CONSTRAINT_BREACH"


def test_validate_portfolio_frontier_suboptimal_warning_only():
    """Caso 2: solo retornos dominados (ratio bajo) seleccionados -> SUBOPTIMAL_FRONTIER_WARNING."""
    from backend.schemas.projects import (
        validate_portfolio_efficient_frontier_and_budget_knapsack,
    )

    res = validate_portfolio_efficient_frontier_and_budget_knapsack(
        [
            {
                "project_id": "PRJ-10",
                "expected_npv_return": 100000.0,
                "risk_volatility_cost": 100000.0,
                "required_capex_budget": 30000.0,
                "strategic_fit_score": 80.0,
                "is_selected_in_portfolio": True,
            },
        ]
    )
    # ratio = 1.0 < 1.2 -> dominado; cap 30000 <= 100000; fit 80 >= 65.
    assert res["total_candidates_evaluated"] == 1
    assert res["selected_projects_count"] == 1
    assert res["selected_total_capex"] == 30000.0
    assert res["is_budget_cap_exceeded"] is False
    assert res["dominated_suboptimal_selected_ids"] == ["PRJ-10"]
    assert res["strategically_misaligned_selected_ids"] == []
    assert res["portfolio_optimization_status"] == "SUBOPTIMAL_FRONTIER_WARNING"
    assert res["is_portfolio_frontier_compliant"] is False

    # Precisión: no seleccionado con mal ratio no empaña el resultado.
    res_unselected = validate_portfolio_efficient_frontier_and_budget_knapsack(
        [
            {
                "project_id": "PRJ-11",
                "expected_npv_return": 10.0,
                "risk_volatility_cost": 1.0,
                "strategic_fit_score": 0.0,
                "is_selected_in_portfolio": False,
            },
        ]
    )
    assert res_unselected["selected_projects_count"] == 0
    assert res_unselected["selected_total_capex"] == 0.0
    assert res_unselected["portfolio_optimization_status"] == "EFFICIENT_FRONTIER_OPTIMAL"


def test_validate_portfolio_frontier_optimal_and_boundaries():
    """Caso 3: fronteras exactas (ratio = min, fit = min, cap = límite) -> OPTIMAL."""
    from backend.schemas.projects import (
        validate_portfolio_efficient_frontier_and_budget_knapsack,
    )

    res = validate_portfolio_efficient_frontier_and_budget_knapsack(
        [
            {
                "project_id": "PRJ-20",
                "expected_npv_return": 120000.0,
                "risk_volatility_cost": 100000.0,
                "required_capex_budget": 100000.0,
                "strategic_fit_score": 65.0,
                "is_selected_in_portfolio": True,
            },
        ],
        total_portfolio_budget_cap=100000.0,
    )
    # ratio 1.2 no < 1.2; fit 65 no < 65; cap 100000 no > 100000.
    assert res["selected_projects_count"] == 1
    assert res["selected_total_capex"] == 100000.0
    assert res["is_budget_cap_exceeded"] is False
    assert res["dominated_suboptimal_selected_ids"] == []
    assert res["strategically_misaligned_selected_ids"] == []
    assert res["portfolio_optimization_status"] == "EFFICIENT_FRONTIER_OPTIMAL"
    assert res["is_portfolio_frontier_compliant"] is True


def test_validate_portfolio_frontier_invalid_and_binding():
    """Caso 4: entradas no-lista/no-dict y export en __all__."""
    import backend.schemas.projects as mod
    from backend.schemas.projects import (
        validate_portfolio_efficient_frontier_and_budget_knapsack,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = validate_portfolio_efficient_frontier_and_budget_knapsack(payload)  # type: ignore[arg-type]
        assert empty["total_candidates_evaluated"] == 0
        assert empty["selected_projects_count"] == 0
        assert empty["selected_total_capex"] == 0.0
        assert empty["is_budget_cap_exceeded"] is False
        assert empty["dominated_suboptimal_selected_ids"] == []
        assert empty["strategically_misaligned_selected_ids"] == []
        assert empty["portfolio_optimization_status"] == "EFFICIENT_FRONTIER_OPTIMAL"
        assert empty["is_portfolio_frontier_compliant"] is True

    assert "validate_portfolio_efficient_frontier_and_budget_knapsack" in mod.__all__


def test_validate_pdm_network_dangling_activities_and_negative_float_dcma_breach():
    from backend.schemas.projects import (
        validate_pdm_network_dangling_activities_and_negative_float,
    )

    res = validate_pdm_network_dangling_activities_and_negative_float(
        [
            {
                "activity_id": "ACT-OPEN-END",
                "is_start_milestone": False,
                "is_finish_milestone": False,
                "predecessor_count": 1,
                "successor_count": 0,
                "total_float_days": 2.0,
                "max_incoming_lead_days": 0.0,
                "max_incoming_lag_days": 0.0,
                "duration_days": 5.0,
            },
            {
                "activity_id": "ACT-NEG-FLOAT",
                "is_start_milestone": False,
                "is_finish_milestone": False,
                "predecessor_count": 1,
                "successor_count": 1,
                "total_float_days": -3.5,
                "max_incoming_lead_days": 0.0,
                "max_incoming_lag_days": 0.0,
                "duration_days": 4.0,
            },
        ],
        max_lag_to_duration_ratio=0.5,
    )
    assert res["total_activities_evaluated"] == 2
    assert res["dangling_logic_activity_ids"] == ["ACT-OPEN-END"]
    assert res["negative_float_activity_ids"] == ["ACT-NEG-FLOAT"]
    assert res["excessive_lead_or_lag_activity_ids"] == []
    assert res["schedule_network_status"] == "DCMA_LOGIC_OR_FLOAT_BREACH"
    assert res["is_pdm_network_compliant"] is False


def test_validate_pdm_network_dangling_activities_and_negative_float_lead_lag_warning():
    from backend.schemas.projects import (
        validate_pdm_network_dangling_activities_and_negative_float,
    )

    res = validate_pdm_network_dangling_activities_and_negative_float(
        [
            {
                "activity_id": "ACT-LEAD",
                "is_start_milestone": False,
                "is_finish_milestone": False,
                "predecessor_count": 1,
                "successor_count": 1,
                "total_float_days": 1.0,
                "max_incoming_lead_days": 2.0,
                "max_incoming_lag_days": 0.0,
                "duration_days": 10.0,
            },
            {
                "activity_id": "ACT-HEAVY-LAG",
                "is_start_milestone": False,
                "is_finish_milestone": False,
                "predecessor_count": 1,
                "successor_count": 1,
                "total_float_days": 0.0,
                "max_incoming_lead_days": 0.0,
                "max_incoming_lag_days": 6.0,
                "duration_days": 10.0,
            },
        ],
        max_lag_to_duration_ratio=0.5,
    )
    assert res["dangling_logic_activity_ids"] == []
    assert res["negative_float_activity_ids"] == []
    assert res["excessive_lead_or_lag_activity_ids"] == [
        "ACT-LEAD",
        "ACT-HEAVY-LAG",
    ]
    assert res["schedule_network_status"] == "LEAD_LAG_DISTORTION_WARNING"
    assert res["is_pdm_network_compliant"] is False


def test_validate_pdm_network_dangling_activities_and_negative_float_sound_and_empty():
    from backend.schemas.projects import (
        validate_pdm_network_dangling_activities_and_negative_float,
    )

    empty = validate_pdm_network_dangling_activities_and_negative_float(
        [{"activity_id": "   "}, "invalid"]  # type: ignore[list-item]
    )
    assert empty["total_activities_evaluated"] == 0
    assert empty["schedule_network_status"] == "NETWORK_INTEGRITY_SOUND"
    assert empty["is_pdm_network_compliant"] is True

    sound = validate_pdm_network_dangling_activities_and_negative_float(
        [
            {
                "activity_id": "MS-START",
                "is_start_milestone": True,
                "is_finish_milestone": False,
                "predecessor_count": 0,
                "successor_count": 2,
                "total_float_days": 0.0,
                "duration_days": 0.0,
            },
            {
                "activity_id": "ACT-WORK",
                "is_start_milestone": False,
                "is_finish_milestone": False,
                "predecessor_count": 1,
                "successor_count": 1,
                "total_float_days": 2.0,
                "max_incoming_lead_days": 0.0,
                "max_incoming_lag_days": 2.0,
                "duration_days": 10.0,
            },
            {
                "activity_id": "MS-FINISH",
                "is_start_milestone": False,
                "is_finish_milestone": True,
                "predecessor_count": 1,
                "successor_count": 0,
                "total_float_days": 0.0,
                "duration_days": 0.0,
            },
        ],
        max_lag_to_duration_ratio=0.5,
    )
    assert sound["total_activities_evaluated"] == 3
    assert sound["schedule_network_status"] == "NETWORK_INTEGRITY_SOUND"
    assert sound["is_pdm_network_compliant"] is True


def test_validate_pdm_network_dangling_activities_and_negative_float_dunder_all():
    import backend.schemas.projects as mod

    assert (
        "validate_pdm_network_dangling_activities_and_negative_float"
        in mod.__all__
    )


def test_validate_risk_emv_decision_tree_and_contingency_adequacy_underfunded_or_invalid():
    from backend.schemas.projects import (
        validate_risk_emv_decision_tree_and_contingency_adequacy,
    )

    res = validate_risk_emv_decision_tree_and_contingency_adequacy(
        [
            {
                "risk_id": "RSK-BAD-PROB",
                "probability": 1.4,
                "financial_impact": 5000.0,
                "has_quantified_fallback_branch": True,
            },
            {
                "risk_id": "RSK-CLOUD-OUTAGE",
                "probability": 0.5,
                "financial_impact": 30000.0,
                "has_quantified_fallback_branch": True,
            },
        ],
        allocated_contingency_reserve=10000.0,
        max_underfunded_shortfall_pct=5.0,
    )
    assert res["total_risks_evaluated"] == 2
    assert res["net_threat_emv"] == 15000.0
    assert res["reserve_shortfall"] == 5000.0
    assert res["shortfall_pct"] == 33.33
    assert res["invalid_probability_risk_ids"] == ["RSK-BAD-PROB"]
    assert res["emv_adequacy_status"] == "UNDERFUNDED_OR_INVALID_MODEL"
    assert res["is_emv_adequate"] is False


def test_validate_risk_emv_decision_tree_and_contingency_adequacy_branch_warning():
    from backend.schemas.projects import (
        validate_risk_emv_decision_tree_and_contingency_adequacy,
    )

    res = validate_risk_emv_decision_tree_and_contingency_adequacy(
        [
            {
                "risk_id": "RSK-VENDOR-LOCK",
                "probability": 0.4,
                "financial_impact": 6000.0,
                "has_quantified_fallback_branch": False,
            }
        ],
        allocated_contingency_reserve=5000.0,
        max_underfunded_shortfall_pct=5.0,
    )
    assert res["net_threat_emv"] == 2400.0
    assert res["reserve_shortfall"] == 0.0
    assert res["invalid_probability_risk_ids"] == []
    assert res["unmodeled_high_threat_risk_ids"] == ["RSK-VENDOR-LOCK"]
    assert res["emv_adequacy_status"] == "DECISION_TREE_BRANCH_WARNING"
    assert res["is_emv_adequate"] is False


def test_validate_risk_emv_decision_tree_and_contingency_adequacy_adequate_and_empty():
    from backend.schemas.projects import (
        validate_risk_emv_decision_tree_and_contingency_adequacy,
    )

    empty = validate_risk_emv_decision_tree_and_contingency_adequacy(
        [{"risk_id": "   "}, "invalid"]  # type: ignore[list-item]
    )
    assert empty["total_risks_evaluated"] == 0
    assert empty["emv_adequacy_status"] == "EMV_RESERVE_ADEQUATE"
    assert empty["is_emv_adequate"] is True

    adequate = validate_risk_emv_decision_tree_and_contingency_adequacy(
        [
            {
                "risk_id": "RSK-THREAT-01",
                "probability": 0.3,
                "financial_impact": 20000.0,
                "has_quantified_fallback_branch": True,
            },
            {
                "risk_id": "RSK-OPP-02",
                "probability": 0.5,
                "financial_impact": -4000.0,
                "has_quantified_fallback_branch": True,
            },
        ],
        allocated_contingency_reserve=5000.0,
        max_underfunded_shortfall_pct=5.0,
    )
    assert adequate["total_risks_evaluated"] == 2
    assert adequate["net_threat_emv"] == 4000.0
    assert adequate["reserve_shortfall"] == 0.0
    assert adequate["emv_adequacy_status"] == "EMV_RESERVE_ADEQUATE"
    assert adequate["is_emv_adequate"] is True


def test_validate_risk_emv_decision_tree_and_contingency_adequacy_dunder_all():
    import backend.schemas.projects as mod

    assert (
        "validate_risk_emv_decision_tree_and_contingency_adequacy"
        in mod.__all__
    )


def test_validate_pert_three_point_estimation_and_delphi_convergence_invalid_or_unconverged():
    from backend.schemas.projects import (
        validate_pert_three_point_estimation_and_delphi_convergence,
    )

    res = validate_pert_three_point_estimation_and_delphi_convergence(
        [
            {
                "work_package_id": "WP-INVERTED",
                "optimistic_o": 12.0,
                "most_likely_m": 8.0,
                "pessimistic_p": 20.0,
                "delphi_round_divergence_pct": 10.0,
            },
            {
                "work_package_id": "WP-DELPHI-SPLIT",
                "optimistic_o": 6.0,
                "most_likely_m": 12.0,
                "pessimistic_p": 18.0,
                "delphi_round_divergence_pct": 40.0,
            },
        ],
        max_uncertainty_spread_ratio=3.0,
        max_expert_divergence_pct=25.0,
    )
    assert res["total_estimates_evaluated"] == 2
    assert res["total_pert_expected_effort"] == 12.0
    assert res["inverted_bounds_package_ids"] == ["WP-INVERTED"]
    assert res["excessive_spread_package_ids"] == []
    assert res["unconverged_delphi_package_ids"] == ["WP-DELPHI-SPLIT"]
    assert res["pert_estimation_status"] == "INVALID_BOUNDS_OR_UNCONVERGED"
    assert res["is_pert_estimation_compliant"] is False


def test_validate_pert_three_point_estimation_and_delphi_convergence_wide_cone_warning():
    from backend.schemas.projects import (
        validate_pert_three_point_estimation_and_delphi_convergence,
    )

    res = validate_pert_three_point_estimation_and_delphi_convergence(
        [
            {
                "work_package_id": "WP-RESEARCH-SPIKE",
                "optimistic_o": 4.0,
                "most_likely_m": 10.0,
                "pessimistic_p": 20.0,
                "delphi_round_divergence_pct": 15.0,
            }
        ],
        max_uncertainty_spread_ratio=3.0,
        max_expert_divergence_pct=25.0,
    )
    assert res["total_pert_expected_effort"] == 10.67
    assert res["inverted_bounds_package_ids"] == []
    assert res["excessive_spread_package_ids"] == ["WP-RESEARCH-SPIKE"]
    assert res["unconverged_delphi_package_ids"] == []
    assert res["pert_estimation_status"] == "WIDE_UNCERTAINTY_CONE_WARNING"
    assert res["is_pert_estimation_compliant"] is False


def test_validate_pert_three_point_estimation_and_delphi_convergence_sound_and_empty():
    from backend.schemas.projects import (
        validate_pert_three_point_estimation_and_delphi_convergence,
    )

    empty = validate_pert_three_point_estimation_and_delphi_convergence(
        [{"work_package_id": "   "}, "invalid"]  # type: ignore[list-item]
    )
    assert empty["total_estimates_evaluated"] == 0
    assert empty["total_pert_expected_effort"] == 0.0
    assert empty["pert_estimation_status"] == "PERT_CONVERGED_SOUND"
    assert empty["is_pert_estimation_compliant"] is True

    sound = validate_pert_three_point_estimation_and_delphi_convergence(
        [
            {
                "work_package_id": "WP-API-AUTH",
                "optimistic_o": 10.0,
                "most_likely_m": 15.0,
                "pessimistic_p": 26.0,
                "delphi_round_divergence_pct": 12.0,
            }
        ],
        max_uncertainty_spread_ratio=3.0,
        max_expert_divergence_pct=25.0,
    )
    assert sound["total_estimates_evaluated"] == 1
    assert sound["total_pert_expected_effort"] == 16.0
    assert sound["pert_estimation_status"] == "PERT_CONVERGED_SOUND"
    assert sound["is_pert_estimation_compliant"] is True


def test_validate_pert_three_point_estimation_and_delphi_convergence_dunder_all():
    import backend.schemas.projects as mod

    assert (
        "validate_pert_three_point_estimation_and_delphi_convergence"
        in mod.__all__
    )


def test_validate_monte_carlo_p80_p90_breach_convergence_or_monotonicity():
    from backend.schemas.projects import (
        validate_monte_carlo_p80_p90_convergence_and_tornado_sensitivity,
    )

    res = validate_monte_carlo_p80_p90_convergence_and_tornado_sensitivity(
        [
            {
                "model_id": "MC-LOW-ITER",
                "iterations_count": 4999,
            },
            {
                "model_id": "MC-INVERTED",
                "p50_estimate": 120.0,
                "p80_estimate": 110.0,
            },
            {
                "model_id": "MC-TAIL-ONLY",
                "p90_estimate": 150.0,
            },
        ],
        min_iterations_required=5000,
        max_p90_to_p50_tail_ratio=1.35,
    )
    assert res["evaluated_models_count"] == 3
    assert res["under_converged_or_inverted_model_ids"] == [
        "MC-LOW-ITER",
        "MC-INVERTED",
    ]
    assert res["underfunded_or_fat_tail_model_ids"] == ["MC-TAIL-ONLY"]
    assert (
        res["monte_carlo_validation_status"]
        == "MONTE_CARLO_CONVERGENCE_OR_MONOTONICITY_BREACH"
    )
    assert res["is_monte_carlo_valid"] is False


def test_validate_monte_carlo_p80_p90_underfunded_or_fat_tail_warning():
    from backend.schemas.projects import (
        validate_monte_carlo_p80_p90_convergence_and_tornado_sensitivity,
    )

    res = validate_monte_carlo_p80_p90_convergence_and_tornado_sensitivity(
        [
            {
                "model_id": "MC-UNDERFUNDED",
                "baseline_commitment": 105.0,
                "p80_estimate": 110.0,
            },
            {
                "model_id": "MC-FAT-TAIL",
                "p90_estimate": 150.0,
            },
            {
                "model_id": "MC-HOT-CORRELATION",
                "top_driver_correlation_r": 0.9,
            },
        ],
        min_iterations_required=5000,
        max_p90_to_p50_tail_ratio=1.35,
    )
    assert res["evaluated_models_count"] == 3
    assert res["under_converged_or_inverted_model_ids"] == []
    assert res["underfunded_or_fat_tail_model_ids"] == [
        "MC-UNDERFUNDED",
        "MC-FAT-TAIL",
        "MC-HOT-CORRELATION",
    ]
    assert (
        res["monte_carlo_validation_status"]
        == "MONTE_CARLO_P80_UNDERFUNDED_OR_TAIL_WARNING"
    )
    assert res["is_monte_carlo_valid"] is False


def test_validate_monte_carlo_p80_p90_boundaries_inclusive_and_defaults():
    from backend.schemas.projects import (
        validate_monte_carlo_p80_p90_convergence_and_tornado_sensitivity,
    )

    res = validate_monte_carlo_p80_p90_convergence_and_tornado_sensitivity(
        [
            {
                "model_id": "MC-BOUNDARY",
                "iterations_count": 5000,
                "p50_estimate": 100.0,
                "p80_estimate": 115.0,
                "p90_estimate": 135.0,
                "baseline_commitment": 115.0,
                "top_driver_correlation_r": 0.85,
            },
            {"model_id": "MC-ALL-DEFAULTS"},
        ],
        min_iterations_required=5000,
        max_p90_to_p50_tail_ratio=1.35,
    )
    assert res["evaluated_models_count"] == 2
    assert res["under_converged_or_inverted_model_ids"] == []
    assert res["underfunded_or_fat_tail_model_ids"] == []
    assert (
        res["monte_carlo_validation_status"]
        == "MONTE_CARLO_CONFIDENCE_OPTIMAL"
    )
    assert res["is_monte_carlo_valid"] is True


def test_validate_monte_carlo_p80_p90_invalid_and_dunder_all():
    from backend.schemas.projects import (
        validate_monte_carlo_p80_p90_convergence_and_tornado_sensitivity,
    )

    empty = validate_monte_carlo_p80_p90_convergence_and_tornado_sensitivity(
        None
    )
    assert empty["evaluated_models_count"] == 0
    assert empty["under_converged_or_inverted_model_ids"] == []
    assert empty["underfunded_or_fat_tail_model_ids"] == []
    assert (
        empty["monte_carlo_validation_status"]
        == "MONTE_CARLO_CONFIDENCE_OPTIMAL"
    )
    assert empty["is_monte_carlo_valid"] is True

    invalid = validate_monte_carlo_p80_p90_convergence_and_tornado_sensitivity(
        [42, "not-a-dict", None, {"iterations_count": 9000}]  # type: ignore[list-item]
    )
    assert invalid["evaluated_models_count"] == 0

    defaults = validate_monte_carlo_p80_p90_convergence_and_tornado_sensitivity(
        [
            {
                "model_id": "MC-DEFAULTS",
                "iterations_count": None,
                "p50_estimate": None,
                "p80_estimate": None,
                "p90_estimate": None,
                "baseline_commitment": None,
                "top_driver_correlation_r": None,
            }
        ]
    )
    assert defaults["evaluated_models_count"] == 1
    assert (
        defaults["monte_carlo_validation_status"]
        == "MONTE_CARLO_CONFIDENCE_OPTIMAL"
    )
    assert defaults["is_monte_carlo_valid"] is True

    import backend.schemas.projects as mod

    assert (
        "validate_monte_carlo_p80_p90_convergence_and_tornado_sensitivity"
        in mod.__all__
    )


def test_validate_resource_leveling_overallocation_and_context_switching_breach():
    from backend.schemas.projects import (
        validate_resource_leveling_overallocation_and_context_switching,
    )

    result = validate_resource_leveling_overallocation_and_context_switching(
        [
            {
                "resource_id": "RES-OVERALLOC",
                "allocated_hours_per_week": 48.0,
                "available_capacity_hours_per_week": 40.0,
                "concurrent_active_tasks_count": 2,
                "sustained_overtime_weeks_count": 1,
            },
            {
                "resource_id": "RES-BURNOUT",
                "allocated_hours_per_week": 38.0,
                "available_capacity_hours_per_week": 40.0,
                "concurrent_active_tasks_count": 2,
                "sustained_overtime_weeks_count": 3,
            },
            {
                "resource_id": "RES-ZERO-CAP",
                "allocated_hours_per_week": 10.0,
                "available_capacity_hours_per_week": 0.0,
                "concurrent_active_tasks_count": 1,
                "sustained_overtime_weeks_count": 0,
            },
        ],
        max_allocation_utilization_pct=100.0,
        max_concurrent_work_packages=3,
    )
    assert result["evaluated_resources_count"] == 3
    assert result["overallocated_or_burnout_resource_ids"] == [
        "RES-OVERALLOC",
        "RES-BURNOUT",
        "RES-ZERO-CAP",
    ]
    assert result["fragmented_context_switching_resource_ids"] == []
    assert (
        result["resource_leveling_status"]
        == "RESOURCE_OVERALLOCATION_OR_BURNOUT_BREACH"
    )
    assert result["is_resource_leveling_valid"] is False


def test_validate_resource_leveling_overallocation_and_context_switching_warning():
    from backend.schemas.projects import (
        validate_resource_leveling_overallocation_and_context_switching,
    )

    result = validate_resource_leveling_overallocation_and_context_switching(
        [
            {
                "resource_id": "RES-FRAGMENTED",
                "allocated_hours_per_week": 36.0,
                "available_capacity_hours_per_week": 40.0,
                "concurrent_active_tasks_count": 5,
                "sustained_overtime_weeks_count": 1,
            }
        ],
        max_allocation_utilization_pct=100.0,
        max_concurrent_work_packages=3,
    )
    assert result["evaluated_resources_count"] == 1
    assert result["overallocated_or_burnout_resource_ids"] == []
    assert result["fragmented_context_switching_resource_ids"] == [
        "RES-FRAGMENTED"
    ]
    assert (
        result["resource_leveling_status"]
        == "RESOURCE_CONTEXT_SWITCHING_WARNING"
    )
    assert result["is_resource_leveling_valid"] is False


def test_validate_resource_leveling_overallocation_and_context_switching_balanced_and_empty():
    from backend.schemas.projects import (
        validate_resource_leveling_overallocation_and_context_switching,
    )

    empty = validate_resource_leveling_overallocation_and_context_switching(
        [{"resource_id": "   "}, "invalid"]  # type: ignore[list-item]
    )
    assert empty["evaluated_resources_count"] == 0
    assert empty["resource_leveling_status"] == "RESOURCE_LEVELING_BALANCED"
    assert empty["is_resource_leveling_valid"] is True

    balanced = validate_resource_leveling_overallocation_and_context_switching(
        [
            {
                "resource_id": "RES-BALANCED-1",
                "allocated_hours_per_week": 36.0,
                "available_capacity_hours_per_week": 40.0,
                "concurrent_active_tasks_count": 2,
                "sustained_overtime_weeks_count": 0,
            }
        ],
        max_allocation_utilization_pct=100.0,
        max_concurrent_work_packages=3,
    )
    assert balanced["evaluated_resources_count"] == 1
    assert balanced["resource_leveling_status"] == "RESOURCE_LEVELING_BALANCED"
    assert balanced["is_resource_leveling_valid"] is True


def test_validate_resource_leveling_overallocation_and_context_switching_defaults_and_dunder_all():
    import backend.schemas.projects as mod
    from backend.schemas.projects import (
        validate_resource_leveling_overallocation_and_context_switching,
    )

    defaults = validate_resource_leveling_overallocation_and_context_switching(
        [
            {
                "resource_id": "RES-DEF",
                "allocated_hours_per_week": None,
                "available_capacity_hours_per_week": None,
                "concurrent_active_tasks_count": None,
                "sustained_overtime_weeks_count": None,
            }
        ]
    )
    assert defaults["evaluated_resources_count"] == 1
    assert defaults["resource_leveling_status"] == "RESOURCE_LEVELING_BALANCED"
    assert defaults["is_resource_leveling_valid"] is True
    assert (
        "validate_resource_leveling_overallocation_and_context_switching"
        in mod.__all__
    )


def test_validate_wbs_rolling_wave_horizon_and_8_80_rule_breach():
    from backend.schemas.projects import (
        validate_wbs_rolling_wave_horizon_and_8_80_rule,
    )

    result = validate_wbs_rolling_wave_horizon_and_8_80_rule(
        [
            {
                "element_id": "WBS-PP-LATE",
                "is_unexpanded_planning_package": True,
                "days_until_scheduled_start": 15,
                "estimated_effort_hours": 160.0,
                "has_single_accountable_owner": True,
            },
            {
                "element_id": "WBS-WP-UNOWNED",
                "is_unexpanded_planning_package": False,
                "days_until_scheduled_start": 10,
                "estimated_effort_hours": 32.0,
                "has_single_accountable_owner": False,
            },
        ],
        freeze_horizon_days=30,
        min_work_package_hours=8.0,
        max_work_package_hours=80.0,
    )
    assert result["evaluated_elements_count"] == 2
    assert result["undecomposed_horizon_or_unowned_ids"] == [
        "WBS-PP-LATE",
        "WBS-WP-UNOWNED",
    ]
    assert result["sizing_rule_8_80_violation_ids"] == []
    assert (
        result["rolling_wave_status"]
        == "WBS_ROLLING_WAVE_DECOMPOSITION_OR_OWNERSHIP_BREACH"
    )
    assert result["is_rolling_wave_valid"] is False


def test_validate_wbs_rolling_wave_horizon_and_8_80_rule_sizing_warning():
    from backend.schemas.projects import (
        validate_wbs_rolling_wave_horizon_and_8_80_rule,
    )

    result = validate_wbs_rolling_wave_horizon_and_8_80_rule(
        [
            {
                "element_id": "WBS-WP-MICRO",
                "is_unexpanded_planning_package": False,
                "days_until_scheduled_start": 10,
                "estimated_effort_hours": 4.0,
                "has_single_accountable_owner": True,
            },
            {
                "element_id": "WBS-WP-MEGA",
                "is_unexpanded_planning_package": False,
                "days_until_scheduled_start": 10,
                "estimated_effort_hours": 120.0,
                "has_single_accountable_owner": True,
            },
        ],
        freeze_horizon_days=30,
        min_work_package_hours=8.0,
        max_work_package_hours=80.0,
    )
    assert result["evaluated_elements_count"] == 2
    assert result["undecomposed_horizon_or_unowned_ids"] == []
    assert result["sizing_rule_8_80_violation_ids"] == [
        "WBS-WP-MICRO",
        "WBS-WP-MEGA",
    ]
    assert result["rolling_wave_status"] == "WBS_8_80_SIZING_RULE_WARNING"
    assert result["is_rolling_wave_valid"] is False


def test_validate_wbs_rolling_wave_horizon_and_8_80_rule_optimal_and_empty():
    from backend.schemas.projects import (
        validate_wbs_rolling_wave_horizon_and_8_80_rule,
    )

    empty = validate_wbs_rolling_wave_horizon_and_8_80_rule(
        [{"element_id": "   "}, "invalid"]  # type: ignore[list-item]
    )
    assert empty["evaluated_elements_count"] == 0
    assert empty["rolling_wave_status"] == "WBS_ROLLING_WAVE_OPTIMAL"
    assert empty["is_rolling_wave_valid"] is True

    optimal = validate_wbs_rolling_wave_horizon_and_8_80_rule(
        [
            {
                "element_id": "WBS-PP-FUTURE",
                "is_unexpanded_planning_package": True,
                "days_until_scheduled_start": 60,
                "estimated_effort_hours": 240.0,
                "has_single_accountable_owner": True,
            },
            {
                "element_id": "WBS-WP-NEAR",
                "is_unexpanded_planning_package": False,
                "days_until_scheduled_start": 10,
                "estimated_effort_hours": 40.0,
                "has_single_accountable_owner": True,
            },
        ],
        freeze_horizon_days=30,
        min_work_package_hours=8.0,
        max_work_package_hours=80.0,
    )
    assert optimal["evaluated_elements_count"] == 2
    assert optimal["rolling_wave_status"] == "WBS_ROLLING_WAVE_OPTIMAL"
    assert optimal["is_rolling_wave_valid"] is True


def test_validate_wbs_rolling_wave_horizon_and_8_80_rule_defaults_and_dunder_all():
    import backend.schemas.projects as mod
    from backend.schemas.projects import (
        validate_wbs_rolling_wave_horizon_and_8_80_rule,
    )

    defaults = validate_wbs_rolling_wave_horizon_and_8_80_rule(
        [
            {
                "element_id": "WBS-DEF",
                "is_unexpanded_planning_package": None,
                "days_until_scheduled_start": None,
                "estimated_effort_hours": None,
                "has_single_accountable_owner": None,
            }
        ]
    )
    assert defaults["evaluated_elements_count"] == 1
    assert defaults["rolling_wave_status"] == "WBS_ROLLING_WAVE_OPTIMAL"
    assert defaults["is_rolling_wave_valid"] is True
    assert "validate_wbs_rolling_wave_horizon_and_8_80_rule" in mod.__all__


def test_validate_rtm_bidirectional_traceability_and_gold_plating_breach():
    from backend.schemas.projects import (
        validate_rtm_bidirectional_traceability_and_gold_plating,
    )

    result = validate_rtm_bidirectional_traceability_and_gold_plating(
        [
            {
                "req_id": "REQ-GOLD-PLATE",
                "linked_business_objective_id": "OBJ-1",
                "linked_wbs_deliverable_id": "WBS-1.1",
                "linked_verification_test_cases_count": 3,
                "is_unapproved_gold_plating_feature": True,
            },
            {
                "req_id": "REQ-UNTESTED",
                "linked_business_objective_id": "OBJ-1",
                "linked_wbs_deliverable_id": "WBS-1.1",
                "linked_verification_test_cases_count": 0,
                "is_unapproved_gold_plating_feature": False,
            },
        ],
        min_test_case_coverage_per_req=1,
    )
    assert result["evaluated_requirements_count"] == 2
    assert result["untested_or_gold_plating_req_ids"] == [
        "REQ-GOLD-PLATE",
        "REQ-UNTESTED",
    ]
    assert result["untraced_objective_or_wbs_req_ids"] == []
    assert (
        result["rtm_traceability_status"]
        == "RTM_GOLD_PLATING_OR_UNTESTED_BREACH"
    )
    assert result["is_rtm_traceability_valid"] is False


def test_validate_rtm_bidirectional_traceability_and_gold_plating_warning():
    from backend.schemas.projects import (
        validate_rtm_bidirectional_traceability_and_gold_plating,
    )

    result = validate_rtm_bidirectional_traceability_and_gold_plating(
        [
            {
                "req_id": "REQ-NO-OBJ",
                "linked_business_objective_id": None,
                "linked_wbs_deliverable_id": "WBS-1.1",
                "linked_verification_test_cases_count": 2,
                "is_unapproved_gold_plating_feature": False,
            },
            {
                "req_id": "REQ-BLANK-WBS",
                "linked_business_objective_id": "OBJ-1",
                "linked_wbs_deliverable_id": "   ",
                "linked_verification_test_cases_count": 2,
                "is_unapproved_gold_plating_feature": False,
            },
        ],
        min_test_case_coverage_per_req=1,
    )
    assert result["evaluated_requirements_count"] == 2
    assert result["untested_or_gold_plating_req_ids"] == []
    assert result["untraced_objective_or_wbs_req_ids"] == [
        "REQ-NO-OBJ",
        "REQ-BLANK-WBS",
    ]
    assert (
        result["rtm_traceability_status"]
        == "RTM_ORPHAN_TRACEABILITY_LINK_WARNING"
    )
    assert result["is_rtm_traceability_valid"] is False


def test_validate_rtm_bidirectional_traceability_and_gold_plating_optimal_and_empty():
    from backend.schemas.projects import (
        validate_rtm_bidirectional_traceability_and_gold_plating,
    )

    empty = validate_rtm_bidirectional_traceability_and_gold_plating(
        [{"req_id": "   "}, "invalid"]  # type: ignore[list-item]
    )
    assert empty["evaluated_requirements_count"] == 0
    assert (
        empty["rtm_traceability_status"]
        == "RTM_BIDIRECTIONAL_TRACEABILITY_OPTIMAL"
    )
    assert empty["is_rtm_traceability_valid"] is True

    optimal = validate_rtm_bidirectional_traceability_and_gold_plating(
        [
            {
                "req_id": "REQ-OPTIMAL-1",
                "linked_business_objective_id": "OBJ-10",
                "linked_wbs_deliverable_id": "WBS-2.1",
                "linked_verification_test_cases_count": 2,
                "is_unapproved_gold_plating_feature": False,
            }
        ],
        min_test_case_coverage_per_req=1,
    )
    assert optimal["evaluated_requirements_count"] == 1
    assert (
        optimal["rtm_traceability_status"]
        == "RTM_BIDIRECTIONAL_TRACEABILITY_OPTIMAL"
    )
    assert optimal["is_rtm_traceability_valid"] is True


def test_validate_rtm_bidirectional_traceability_and_gold_plating_defaults_and_dunder_all():
    import backend.schemas.projects as mod
    from backend.schemas.projects import (
        validate_rtm_bidirectional_traceability_and_gold_plating,
    )

    defaults = validate_rtm_bidirectional_traceability_and_gold_plating(
        [{"req_id": "REQ-DEF-99"}]
    )
    assert defaults["evaluated_requirements_count"] == 1
    assert (
        defaults["rtm_traceability_status"]
        == "RTM_BIDIRECTIONAL_TRACEABILITY_OPTIMAL"
    )
    assert defaults["is_rtm_traceability_valid"] is True
    assert (
        "validate_rtm_bidirectional_traceability_and_gold_plating"
        in mod.__all__
    )



def test_validate_bcr_sunk_cost_or_negative_npv_breach():
    from backend.schemas.projects import (
        validate_benefit_cost_ratio_and_sunk_cost_governance,
    )

    res = validate_benefit_cost_ratio_and_sunk_cost_governance(
        [
            {
                "case_id": "CASE-SUNK-BAD-BCR",
                "historical_sunk_costs_included_in_justification": True,
                "pv_expected_benefits": 100000.0,
                "pv_future_incremental_costs": 100000.0,
            },
            {
                "case_id": "CASE-NEG-NPV",
                "net_present_value": -5000.0,
            },
            {
                "case_id": "CASE-ZERO-COSTS",
                "pv_future_incremental_costs": 0,
            },
            {
                "case_id": "CASE-EXEMPT-NEG-NPV",
                "regulatory_mandatory_exemption": True,
                "net_present_value": -1.0,
            },
        ],
        min_bcr_threshold=1.15,
    )
    assert res["evaluated_cases_count"] == 4
    assert res["sunk_cost_or_negative_npv_case_ids"] == [
        "CASE-SUNK-BAD-BCR",
        "CASE-NEG-NPV",
        "CASE-ZERO-COSTS",
    ]
    assert res["marginal_bcr_case_ids"] == ["CASE-SUNK-BAD-BCR"]
    assert (
        res["bcr_governance_status"]
        == "BCR_SUNK_COST_OR_NEGATIVE_NPV_BREACH"
    )
    assert res["is_investment_case_valid"] is False


def test_validate_bcr_below_hurdle_ratio_warning():
    from backend.schemas.projects import (
        validate_benefit_cost_ratio_and_sunk_cost_governance,
    )

    res = validate_benefit_cost_ratio_and_sunk_cost_governance(
        [
            {
                "case_id": "CASE-LOW-BCR",
                "pv_expected_benefits": 110000.0,
                "pv_future_incremental_costs": 100000.0,
            },
            {
                "case_id": "CASE-EXEMPT-LOW-BCR",
                "regulatory_mandatory_exemption": True,
                "pv_expected_benefits": 50000.0,
                "pv_future_incremental_costs": 100000.0,
            },
        ],
        min_bcr_threshold=1.15,
    )
    assert res["evaluated_cases_count"] == 2
    assert res["sunk_cost_or_negative_npv_case_ids"] == []
    assert res["marginal_bcr_case_ids"] == ["CASE-LOW-BCR"]
    assert (
        res["bcr_governance_status"]
        == "BCR_BELOW_HURDLE_RATIO_WARNING"
    )
    assert res["is_investment_case_valid"] is False


def test_validate_bcr_boundaries_optimal_and_defaults():
    from backend.schemas.projects import (
        validate_benefit_cost_ratio_and_sunk_cost_governance,
    )

    res = validate_benefit_cost_ratio_and_sunk_cost_governance(
        [
            {
                "case_id": "CASE-BOUNDARY",
                "pv_expected_benefits": 115000.0,
                "pv_future_incremental_costs": 100000.0,
            },
            {"case_id": "CASE-ALL-DEFAULTS"},
        ],
        min_bcr_threshold=1.15,
    )
    assert res["evaluated_cases_count"] == 2
    assert res["sunk_cost_or_negative_npv_case_ids"] == []
    assert res["marginal_bcr_case_ids"] == []
    assert (
        res["bcr_governance_status"]
        == "BCR_INVESTMENT_CASE_OPTIMAL"
    )
    assert res["is_investment_case_valid"] is True


def test_validate_bcr_invalid_and_dunder_all():
    from backend.schemas.projects import (
        validate_benefit_cost_ratio_and_sunk_cost_governance,
    )

    empty = validate_benefit_cost_ratio_and_sunk_cost_governance(None)
    assert empty["evaluated_cases_count"] == 0
    assert empty["sunk_cost_or_negative_npv_case_ids"] == []
    assert empty["marginal_bcr_case_ids"] == []
    assert (
        empty["bcr_governance_status"]
        == "BCR_INVESTMENT_CASE_OPTIMAL"
    )
    assert empty["is_investment_case_valid"] is True

    invalid = validate_benefit_cost_ratio_and_sunk_cost_governance(
        [42, "not-a-dict", None, {"case_id": "   "}]  # type: ignore[list-item]
    )
    assert invalid["evaluated_cases_count"] == 0

    defaults = validate_benefit_cost_ratio_and_sunk_cost_governance(
        [
            {
                "case_id": "CASE-DEFAULTS",
                "pv_expected_benefits": None,
                "pv_future_incremental_costs": None,
                "historical_sunk_costs_included_in_justification": None,
                "net_present_value": None,
                "regulatory_mandatory_exemption": None,
            }
        ]
    )
    assert defaults["evaluated_cases_count"] == 1
    assert (
        defaults["bcr_governance_status"]
        == "BCR_INVESTMENT_CASE_OPTIMAL"
    )
    assert defaults["is_investment_case_valid"] is True

    import backend.schemas.projects as mod

    assert (
        "validate_benefit_cost_ratio_and_sunk_cost_governance"
        in mod.__all__
    )


def test_validate_schedule_crashing_and_fast_tracking_compression_breach():
    from backend.schemas.projects import (
        validate_schedule_crashing_and_fast_tracking_compression,
    )

    result = validate_schedule_crashing_and_fast_tracking_compression(
        [
            {
                "activity_id": "ACT-EXCESSIVE-OVERLAP",
                "is_on_critical_path": True,
                "crash_cost_per_day_saved": 1200.0,
                "fast_track_overlap_pct": 55.0,
                "rework_probability_increase_pct": 10.0,
            },
            {
                "activity_id": "ACT-HIGH-REWORK",
                "is_on_critical_path": True,
                "crash_cost_per_day_saved": 1200.0,
                "fast_track_overlap_pct": 20.0,
                "rework_probability_increase_pct": 40.0,
            },
        ],
        max_fast_track_overlap_pct=35.0,
        max_crash_cost_per_day_saved=5000.0,
    )
    assert result["evaluated_activities_count"] == 2
    assert result["excessive_overlap_or_rework_activity_ids"] == [
        "ACT-EXCESSIVE-OVERLAP",
        "ACT-HIGH-REWORK",
    ]
    assert result["non_critical_or_expensive_crash_activity_ids"] == []
    assert (
        result["schedule_compression_status"]
        == "SCHEDULE_COMPRESSION_REWORK_OR_OVERLAP_BREACH"
    )
    assert result["is_schedule_compression_valid"] is False


def test_validate_schedule_crashing_and_fast_tracking_compression_warning():
    from backend.schemas.projects import (
        validate_schedule_crashing_and_fast_tracking_compression,
    )

    result = validate_schedule_crashing_and_fast_tracking_compression(
        [
            {
                "activity_id": "ACT-NON-CRITICAL-CRASH",
                "is_on_critical_path": False,
                "crash_cost_per_day_saved": 1200.0,
                "fast_track_overlap_pct": 10.0,
                "rework_probability_increase_pct": 5.0,
            },
            {
                "activity_id": "ACT-EXPENSIVE-CRASH",
                "is_on_critical_path": True,
                "crash_cost_per_day_saved": 8500.0,
                "fast_track_overlap_pct": 10.0,
                "rework_probability_increase_pct": 5.0,
            },
        ],
        max_fast_track_overlap_pct=35.0,
        max_crash_cost_per_day_saved=5000.0,
    )
    assert result["evaluated_activities_count"] == 2
    assert result["excessive_overlap_or_rework_activity_ids"] == []
    assert result["non_critical_or_expensive_crash_activity_ids"] == [
        "ACT-NON-CRITICAL-CRASH",
        "ACT-EXPENSIVE-CRASH",
    ]
    assert (
        result["schedule_compression_status"]
        == "SCHEDULE_COMPRESSION_INEFFICIENT_CRASH_WARNING"
    )
    assert result["is_schedule_compression_valid"] is False


def test_validate_schedule_crashing_and_fast_tracking_compression_optimal_and_empty():
    from backend.schemas.projects import (
        validate_schedule_crashing_and_fast_tracking_compression,
    )

    empty = validate_schedule_crashing_and_fast_tracking_compression(
        [{"activity_id": "   "}, "invalid"]  # type: ignore[list-item]
    )
    assert empty["evaluated_activities_count"] == 0
    assert empty["schedule_compression_status"] == "SCHEDULE_COMPRESSION_OPTIMAL"
    assert empty["is_schedule_compression_valid"] is True

    optimal = validate_schedule_crashing_and_fast_tracking_compression(
        [
            {
                "activity_id": "ACT-OPT-CRASH-1",
                "is_on_critical_path": True,
                "crash_cost_per_day_saved": 1800.0,
                "fast_track_overlap_pct": 20.0,
                "rework_probability_increase_pct": 8.0,
            }
        ],
        max_fast_track_overlap_pct=35.0,
        max_crash_cost_per_day_saved=5000.0,
    )
    assert optimal["evaluated_activities_count"] == 1
    assert optimal["excessive_overlap_or_rework_activity_ids"] == []
    assert optimal["non_critical_or_expensive_crash_activity_ids"] == []
    assert (
        optimal["schedule_compression_status"]
        == "SCHEDULE_COMPRESSION_OPTIMAL"
    )
    assert optimal["is_schedule_compression_valid"] is True


def test_validate_schedule_crashing_and_fast_tracking_compression_dunder_all_and_defaults():
    import backend.schemas.projects as mod
    from backend.schemas.projects import (
        validate_schedule_crashing_and_fast_tracking_compression,
    )

    res = validate_schedule_crashing_and_fast_tracking_compression(
        [{"activity_id": "ACT-DEFAULT-01"}]
    )
    assert res["evaluated_activities_count"] == 1
    assert res["is_schedule_compression_valid"] is True
    assert (
        "validate_schedule_crashing_and_fast_tracking_compression"
        in mod.__all__
    )


def test_validate_make_or_buy_core_ip_or_lockin_breach():
    from backend.schemas.projects import (
        validate_make_or_buy_tco_and_vendor_concentration,
    )

    res = validate_make_or_buy_tco_and_vendor_concentration(
        [
            {
                "component_id": "COMP-CORE-IP-OUTSOURCED",
                "is_core_proprietary_ip": True,
                "decision": "BUY",
            },
            {
                "component_id": "COMP-LOCKIN-NO-EXIT",
                "decision": "BUY",
                "exit_portability_plan_documented": False,
            },
            {
                "component_id": "COMP-CORE-IP-AND-CONCENTRATED",
                "is_core_proprietary_ip": True,
                "decision": "BUY",
                "vendor_spend_share_pct": 55.0,
            },
        ],
        max_single_vendor_spend_share_pct=40.0,
        min_core_ip_internal_build=True,
    )
    assert res["evaluated_components_count"] == 3
    assert res["core_ip_outsourced_or_missing_exit_component_ids"] == [
        "COMP-CORE-IP-OUTSOURCED",
        "COMP-LOCKIN-NO-EXIT",
        "COMP-CORE-IP-AND-CONCENTRATED",
    ]
    assert res["tco_inefficient_or_concentrated_vendor_component_ids"] == [
        "COMP-CORE-IP-AND-CONCENTRATED"
    ]
    assert (
        res["make_or_buy_status"]
        == "MAKE_OR_BUY_CORE_IP_OR_LOCKIN_BREACH"
    )
    assert res["is_make_or_buy_valid"] is False

    exempt = validate_make_or_buy_tco_and_vendor_concentration(
        [
            {
                "component_id": "COMP-CORE-IP-OFF-FLAG",
                "is_core_proprietary_ip": True,
                "decision": "BUY",
            }
        ],
        max_single_vendor_spend_share_pct=40.0,
        min_core_ip_internal_build=False,
    )
    assert exempt["core_ip_outsourced_or_missing_exit_component_ids"] == []


def test_validate_make_or_buy_tco_or_concentration_warning():
    from backend.schemas.projects import (
        validate_make_or_buy_tco_and_vendor_concentration,
    )

    res = validate_make_or_buy_tco_and_vendor_concentration(
        [
            {
                "component_id": "COMP-CONCENTRATED",
                "decision": "BUY",
                "vendor_spend_share_pct": 55.0,
            },
            {
                "component_id": "COMP-TCO-DRIFT",
                "decision": "BUY",
                "buy_5yr_tco_usd": 200000.0,
                "make_5yr_tco_usd": 120000.0,
            },
            {
                "component_id": "COMP-WASTEFUL-MAKE",
                "decision": "MAKE",
                "is_core_proprietary_ip": False,
                "make_5yr_tco_usd": 250000.0,
                "buy_5yr_tco_usd": 100000.0,
            },
        ],
        max_single_vendor_spend_share_pct=40.0,
        min_core_ip_internal_build=True,
    )
    assert res["evaluated_components_count"] == 3
    assert res["core_ip_outsourced_or_missing_exit_component_ids"] == []
    assert res["tco_inefficient_or_concentrated_vendor_component_ids"] == [
        "COMP-CONCENTRATED",
        "COMP-TCO-DRIFT",
        "COMP-WASTEFUL-MAKE",
    ]
    assert (
        res["make_or_buy_status"]
        == "MAKE_OR_BUY_TCO_OR_CONCENTRATION_WARNING"
    )
    assert res["is_make_or_buy_valid"] is False


def test_validate_make_or_buy_boundaries_optimal_and_defaults():
    from backend.schemas.projects import (
        validate_make_or_buy_tco_and_vendor_concentration,
    )

    res = validate_make_or_buy_tco_and_vendor_concentration(
        [
            {
                "component_id": "COMP-BOUNDARY",
                "decision": "BUY",
                "vendor_spend_share_pct": 40.0,
                "buy_5yr_tco_usd": 150000.0,
                "make_5yr_tco_usd": 120000.0,
            },
            {
                "component_id": "COMP-MAKE-CORE",
                "decision": "MAKE",
                "is_core_proprietary_ip": True,
                "make_5yr_tco_usd": 300000.0,
                "buy_5yr_tco_usd": 100000.0,
            },
            {"component_id": "COMP-ALL-DEFAULTS"},
        ],
        max_single_vendor_spend_share_pct=40.0,
        min_core_ip_internal_build=True,
    )
    assert res["evaluated_components_count"] == 3
    assert res["core_ip_outsourced_or_missing_exit_component_ids"] == []
    assert res["tco_inefficient_or_concentrated_vendor_component_ids"] == []
    assert (
        res["make_or_buy_status"] == "MAKE_OR_BUY_STRATEGY_OPTIMAL"
    )
    assert res["is_make_or_buy_valid"] is True


def test_validate_make_or_buy_invalid_and_dunder_all():
    from backend.schemas.projects import (
        validate_make_or_buy_tco_and_vendor_concentration,
    )

    empty = validate_make_or_buy_tco_and_vendor_concentration(None)
    assert empty["evaluated_components_count"] == 0
    assert empty["core_ip_outsourced_or_missing_exit_component_ids"] == []
    assert (
        empty["tco_inefficient_or_concentrated_vendor_component_ids"]
        == []
    )
    assert empty["make_or_buy_status"] == "MAKE_OR_BUY_STRATEGY_OPTIMAL"
    assert empty["is_make_or_buy_valid"] is True

    invalid = validate_make_or_buy_tco_and_vendor_concentration(
        [42, "not-a-dict", None, {"component_id": "   "}]  # type: ignore[list-item]
    )
    assert invalid["evaluated_components_count"] == 0

    defaults = validate_make_or_buy_tco_and_vendor_concentration(
        [
            {
                "component_id": "COMP-DEFAULTS",
                "decision": None,
                "is_core_proprietary_ip": None,
                "buy_5yr_tco_usd": None,
                "make_5yr_tco_usd": None,
                "vendor_spend_share_pct": None,
                "exit_portability_plan_documented": None,
            }
        ]
    )
    assert defaults["evaluated_components_count"] == 1
    assert defaults["make_or_buy_status"] == "MAKE_OR_BUY_STRATEGY_OPTIMAL"
    assert defaults["is_make_or_buy_valid"] is True

    import backend.schemas.projects as mod

    assert (
        "validate_make_or_buy_tco_and_vendor_concentration"
        in mod.__all__
    )


def test_validate_stakeholder_salience_power_urgency_legitimacy_alignment_breach():
    from backend.schemas.projects import (
        validate_stakeholder_salience_power_urgency_legitimacy_alignment,
    )

    res = validate_stakeholder_salience_power_urgency_legitimacy_alignment(
        [
            {
                "stakeholder_id": "  SH-DEFINITIVE-NO-OWNER  ",
                "high_power": True,
                "high_urgency": True,
                "high_legitimacy": True,
                "engagement_gap_steps": 0,
                "is_resistant_with_high_power": False,
                "executive_owner_assigned": False,
            },
            {
                "stakeholder_id": "SH-RESISTANT-BLOCKER",
                "high_power": True,
                "high_urgency": False,
                "high_legitimacy": True,
                "engagement_gap_steps": 2,
                "is_resistant_with_high_power": True,
                "executive_owner_assigned": True,
            },
            {
                "stakeholder_id": "SH-CLEAN",
                "high_power": True,
                "high_urgency": True,
                "high_legitimacy": True,
                "engagement_gap_steps": 1,
                "is_resistant_with_high_power": False,
                "executive_owner_assigned": True,
            },
        ]
    )
    assert res["evaluated_stakeholders_count"] == 3
    assert (
        res["unowned_definitive_or_resistant_blocker_stakeholder_ids"]
        == ["SH-DEFINITIVE-NO-OWNER", "SH-RESISTANT-BLOCKER"]
    )
    assert res["wide_engagement_gap_stakeholder_ids"] == [
        "SH-RESISTANT-BLOCKER"
    ]
    assert (
        res["stakeholder_salience_status"]
        == "STAKEHOLDER_SALIENCE_BLOCKER_OR_UNOWNED_BREACH"
    )
    assert res["is_stakeholder_salience_valid"] is False


def test_validate_stakeholder_salience_power_urgency_legitimacy_alignment_warning():
    from backend.schemas.projects import (
        validate_stakeholder_salience_power_urgency_legitimacy_alignment,
    )

    res = validate_stakeholder_salience_power_urgency_legitimacy_alignment(
        [
            {
                "stakeholder_id": "SH-GAP-2",
                "high_power": True,
                "high_urgency": True,
                "high_legitimacy": True,
                "engagement_gap_steps": 2,
                "is_resistant_with_high_power": False,
                "executive_owner_assigned": True,
            },
            {
                "stakeholder_id": "SH-UNOWNED-ALLOWED",
                "high_power": True,
                "high_urgency": True,
                "high_legitimacy": True,
                "engagement_gap_steps": 1,
                "is_resistant_with_high_power": False,
                "executive_owner_assigned": False,
            },
        ],
        max_engagement_gap_steps=1,
        require_definitive_stakeholder_owner=False,
    )
    assert res["evaluated_stakeholders_count"] == 2
    assert res["unowned_definitive_or_resistant_blocker_stakeholder_ids"] == []
    assert res["wide_engagement_gap_stakeholder_ids"] == ["SH-GAP-2"]
    assert (
        res["stakeholder_salience_status"]
        == "STAKEHOLDER_ENGAGEMENT_GAP_WARNING"
    )
    assert res["is_stakeholder_salience_valid"] is False


def test_validate_stakeholder_salience_power_urgency_legitimacy_alignment_optimal_and_boundaries():
    from backend.schemas.projects import (
        validate_stakeholder_salience_power_urgency_legitimacy_alignment,
    )

    res = validate_stakeholder_salience_power_urgency_legitimacy_alignment(
        [
            {
                "stakeholder_id": "SH-BOUNDARY",
                "high_power": True,
                "high_urgency": True,
                "high_legitimacy": True,
                "engagement_gap_steps": 1,
                "is_resistant_with_high_power": False,
                "executive_owner_assigned": True,
            },
            {
                "stakeholder_id": "SH-NON-DEFINITIVE-NO-OWNER",
                "high_power": True,
                "high_urgency": False,
                "high_legitimacy": True,
                "engagement_gap_steps": 0,
                "is_resistant_with_high_power": False,
                "executive_owner_assigned": False,
            },
        ]
    )
    assert res["evaluated_stakeholders_count"] == 2
    assert res["unowned_definitive_or_resistant_blocker_stakeholder_ids"] == []
    assert res["wide_engagement_gap_stakeholder_ids"] == []
    assert (
        res["stakeholder_salience_status"]
        == "STAKEHOLDER_SALIENCE_ALIGNMENT_OPTIMAL"
    )
    assert res["is_stakeholder_salience_valid"] is True


def test_validate_stakeholder_salience_power_urgency_legitimacy_alignment_defensive_and_dunder_all():
    import backend.schemas.projects as mod
    from backend.schemas.projects import (
        validate_stakeholder_salience_power_urgency_legitimacy_alignment,
    )

    empty = validate_stakeholder_salience_power_urgency_legitimacy_alignment(
        None
    )
    assert empty["evaluated_stakeholders_count"] == 0
    assert (
        empty["stakeholder_salience_status"]
        == "STAKEHOLDER_SALIENCE_ALIGNMENT_OPTIMAL"
    )
    assert empty["is_stakeholder_salience_valid"] is True

    defaults = validate_stakeholder_salience_power_urgency_legitimacy_alignment(
        [
            "not-a-dict",  # type: ignore[list-item]
            {"stakeholder_id": "   "},
            {
                "stakeholder_id": "SH-DEFAULTS",
                "high_power": None,
                "high_urgency": None,
                "high_legitimacy": None,
                "engagement_gap_steps": None,
                "is_resistant_with_high_power": None,
                "executive_owner_assigned": None,
            },
        ]
    )
    assert defaults["evaluated_stakeholders_count"] == 1
    assert (
        defaults["stakeholder_salience_status"]
        == "STAKEHOLDER_SALIENCE_ALIGNMENT_OPTIMAL"
    )
    assert defaults["is_stakeholder_salience_valid"] is True
    assert (
        "validate_stakeholder_salience_power_urgency_legitimacy_alignment"
        in mod.__all__
    )



def test_validate_boe_undocumented_or_padding_breach():
    from backend.schemas.projects import (
        validate_basis_of_estimate_boe_and_padding_hygiene,
    )

    res = validate_basis_of_estimate_boe_and_padding_hygiene(
        [
            {
                "estimate_id": "EST-NO-BOE",
                "assumptions_and_constraints_documented": False,
            },
            {
                "estimate_id": "EST-PADDING-BADBOE",
                "unexplained_buffer_padding_pct": 22.0,
            },
        ],
        max_parametric_r_squared_deficit=0.20,
        max_unexplained_padding_pct=10.0,
    )
    assert res["evaluated_estimates_count"] == 2
    assert res["undocumented_boe_or_hidden_padding_estimate_ids"] == [
        "EST-NO-BOE",
        "EST-PADDING-BADBOE",
    ]
    assert res["weak_calibration_or_unreviewed_estimate_ids"] == []
    assert (
        res["boe_hygiene_status"]
        == "BOE_UNDOCUMENTED_OR_HIDDEN_PADDING_BREACH"
    )
    assert res["is_boe_hygiene_valid"] is False


def test_validate_boe_weak_calibration_or_unreviewed_warning():
    from backend.schemas.projects import (
        validate_basis_of_estimate_boe_and_padding_hygiene,
    )

    res = validate_basis_of_estimate_boe_and_padding_hygiene(
        [
            {
                "estimate_id": "EST-WEAK-CALIB",
                "historical_calibration_r_squared": 0.55,
            },
            {
                "estimate_id": "EST-UNREVIEWED",
                "independent_peer_review_completed": False,
            },
        ],
        max_parametric_r_squared_deficit=0.20,
        max_unexplained_padding_pct=10.0,
    )
    assert res["evaluated_estimates_count"] == 2
    assert res["undocumented_boe_or_hidden_padding_estimate_ids"] == []
    assert res["weak_calibration_or_unreviewed_estimate_ids"] == [
        "EST-WEAK-CALIB",
        "EST-UNREVIEWED",
    ]
    assert (
        res["boe_hygiene_status"]
        == "BOE_WEAK_CALIBRATION_OR_UNREVIEWED_WARNING"
    )
    assert res["is_boe_hygiene_valid"] is False


def test_validate_boe_boundaries_optimal_and_defaults():
    from backend.schemas.projects import (
        validate_basis_of_estimate_boe_and_padding_hygiene,
    )

    res = validate_basis_of_estimate_boe_and_padding_hygiene(
        [
            {
                "estimate_id": "EST-BOUNDARY",
                "historical_calibration_r_squared": 0.80,
                "unexplained_buffer_padding_pct": 10.0,
            },
            {"estimate_id": "EST-ALL-DEFAULTS"},
        ],
        max_parametric_r_squared_deficit=0.20,
        max_unexplained_padding_pct=10.0,
    )
    assert res["evaluated_estimates_count"] == 2
    assert res["undocumented_boe_or_hidden_padding_estimate_ids"] == []
    assert res["weak_calibration_or_unreviewed_estimate_ids"] == []
    assert res["boe_hygiene_status"] == "BOE_ESTIMATION_HYGIENE_OPTIMAL"
    assert res["is_boe_hygiene_valid"] is True


def test_validate_boe_invalid_and_dunder_all():
    from backend.schemas.projects import (
        validate_basis_of_estimate_boe_and_padding_hygiene,
    )

    empty = validate_basis_of_estimate_boe_and_padding_hygiene(None)
    assert empty["evaluated_estimates_count"] == 0
    assert empty["undocumented_boe_or_hidden_padding_estimate_ids"] == []
    assert empty["weak_calibration_or_unreviewed_estimate_ids"] == []
    assert (
        empty["boe_hygiene_status"] == "BOE_ESTIMATION_HYGIENE_OPTIMAL"
    )
    assert empty["is_boe_hygiene_valid"] is True

    invalid = validate_basis_of_estimate_boe_and_padding_hygiene(
        [42, "not-a-dict", None, {"estimate_id": "   "}]  # type: ignore[list-item]
    )
    assert invalid["evaluated_estimates_count"] == 0

    defaults = validate_basis_of_estimate_boe_and_padding_hygiene(
        [
            {
                "estimate_id": "EST-DEFAULTS",
                "assumptions_and_constraints_documented": None,
                "historical_calibration_r_squared": None,
                "unexplained_buffer_padding_pct": None,
                "independent_peer_review_completed": None,
            }
        ]
    )
    assert defaults["evaluated_estimates_count"] == 1
    assert defaults["boe_hygiene_status"] == "BOE_ESTIMATION_HYGIENE_OPTIMAL"
    assert defaults["is_boe_hygiene_valid"] is True

    import backend.schemas.projects as mod

    assert (
        "validate_basis_of_estimate_boe_and_padding_hygiene"
        in mod.__all__
    )


def test_validate_cost_of_quality_coq_conformance_vs_failure_ratio_breach():
    from backend.schemas.projects import (
        validate_cost_of_quality_coq_conformance_vs_failure_ratio,
    )

    res = validate_cost_of_quality_coq_conformance_vs_failure_ratio(
        [
            {
                "workstream_id": "  WS-RECALL  ",
                "conformance_spend_share_pct": 80.0,
                "external_failure_share_pct": 5.0,
                "escaped_production_recall_occurred": True,
                "preventive_root_cause_capa_active": True,
            },
            {
                "workstream_id": "WS-EXT-FAILURE",
                "conformance_spend_share_pct": 55.0,
                "external_failure_share_pct": 12.0,
                "escaped_production_recall_occurred": False,
                "preventive_root_cause_capa_active": False,
            },
            {
                "workstream_id": "WS-CLEAN",
                "conformance_spend_share_pct": 65.0,
                "external_failure_share_pct": 10.0,
                "escaped_production_recall_occurred": False,
                "preventive_root_cause_capa_active": True,
            },
        ]
    )
    assert res["evaluated_workstreams_count"] == 3
    assert res["external_failure_or_recall_workstream_ids"] == [
        "WS-RECALL",
        "WS-EXT-FAILURE",
    ]
    assert res["underinvested_conformance_or_missing_capa_workstream_ids"] == [
        "WS-EXT-FAILURE"
    ]
    assert res["coq_balance_status"] == "COQ_EXTERNAL_FAILURE_OR_RECALL_BREACH"
    assert res["is_coq_balance_valid"] is False


def test_validate_cost_of_quality_coq_conformance_vs_failure_ratio_warning():
    from backend.schemas.projects import (
        validate_cost_of_quality_coq_conformance_vs_failure_ratio,
    )

    res = validate_cost_of_quality_coq_conformance_vs_failure_ratio(
        [
            {
                "workstream_id": "WS-UNDERINVESTED",
                "conformance_spend_share_pct": 64.9,
                "external_failure_share_pct": 10.0,
                "escaped_production_recall_occurred": False,
                "preventive_root_cause_capa_active": True,
            },
            {
                "workstream_id": "WS-NO-CAPA",
                "conformance_spend_share_pct": 65.0,
                "external_failure_share_pct": 4.0,
                "escaped_production_recall_occurred": False,
                "preventive_root_cause_capa_active": False,
            },
        ],
        min_conformance_spend_share_pct=65.0,
        max_external_failure_share_pct=10.0,
    )
    assert res["evaluated_workstreams_count"] == 2
    assert res["external_failure_or_recall_workstream_ids"] == []
    assert res["underinvested_conformance_or_missing_capa_workstream_ids"] == [
        "WS-UNDERINVESTED",
        "WS-NO-CAPA",
    ]
    assert (
        res["coq_balance_status"] == "COQ_CONFORMANCE_UNDERINVESTMENT_WARNING"
    )
    assert res["is_coq_balance_valid"] is False


def test_validate_cost_of_quality_coq_conformance_vs_failure_ratio_optimal_and_boundaries():
    from backend.schemas.projects import (
        validate_cost_of_quality_coq_conformance_vs_failure_ratio,
    )

    res = validate_cost_of_quality_coq_conformance_vs_failure_ratio(
        [
            {
                "workstream_id": "WS-BOUNDARY",
                "conformance_spend_share_pct": 65.0,
                "external_failure_share_pct": 10.0,
                "escaped_production_recall_occurred": False,
                "preventive_root_cause_capa_active": True,
            }
        ],
        min_conformance_spend_share_pct=65.0,
        max_external_failure_share_pct=10.0,
    )
    assert res["evaluated_workstreams_count"] == 1
    assert res["external_failure_or_recall_workstream_ids"] == []
    assert res["underinvested_conformance_or_missing_capa_workstream_ids"] == []
    assert res["coq_balance_status"] == "COQ_INVESTMENT_BALANCE_OPTIMAL"
    assert res["is_coq_balance_valid"] is True


def test_validate_cost_of_quality_coq_conformance_vs_failure_ratio_defensive_and_dunder_all():
    import backend.schemas.projects as mod
    from backend.schemas.projects import (
        validate_cost_of_quality_coq_conformance_vs_failure_ratio,
    )

    empty = validate_cost_of_quality_coq_conformance_vs_failure_ratio(None)
    assert empty["evaluated_workstreams_count"] == 0
    assert empty["coq_balance_status"] == "COQ_INVESTMENT_BALANCE_OPTIMAL"
    assert empty["is_coq_balance_valid"] is True

    defaults = validate_cost_of_quality_coq_conformance_vs_failure_ratio(
        [
            "not-a-dict",  # type: ignore[list-item]
            {"workstream_id": "   "},
            {
                "workstream_id": "WS-DEFAULTS",
                "conformance_spend_share_pct": None,
                "external_failure_share_pct": None,
                "escaped_production_recall_occurred": None,
                "preventive_root_cause_capa_active": None,
            },
        ]
    )
    assert defaults["evaluated_workstreams_count"] == 1
    assert defaults["coq_balance_status"] == "COQ_INVESTMENT_BALANCE_OPTIMAL"
    assert defaults["is_coq_balance_valid"] is True
    assert (
        "validate_cost_of_quality_coq_conformance_vs_failure_ratio"
        in mod.__all__
    )


def test_validate_raci_matrix_single_accountable_and_role_overload_breach():
    from backend.schemas.projects import (
        validate_raci_matrix_single_accountable_and_role_overload,
    )

    res = validate_raci_matrix_single_accountable_and_role_overload(
        [
            {
                "deliverable_id": "  DELIV-MULTI-A  ",
                "accountable_count": 2,
                "responsible_count": 2,
                "consulted_count": 3,
                "accountable_and_responsible_same_person_overloaded": False,
            },
            {
                "deliverable_id": "DELIV-ZERO-A",
                "accountable_count": 0,
                "responsible_count": 2,
                "consulted_count": 2,
                "accountable_and_responsible_same_person_overloaded": False,
            },
            {
                "deliverable_id": "DELIV-ZERO-R",
                "accountable_count": 1,
                "responsible_count": 0,
                "consulted_count": 8,
                "accountable_and_responsible_same_person_overloaded": True,
            },
            {
                "deliverable_id": "DELIV-CLEAN",
                "accountable_count": 1,
                "responsible_count": 1,
                "consulted_count": 5,
                "accountable_and_responsible_same_person_overloaded": False,
            },
        ]
    )
    assert res["evaluated_deliverables_count"] == 4
    assert res["ambiguous_accountability_or_unassigned_deliverable_ids"] == [
        "DELIV-MULTI-A",
        "DELIV-ZERO-A",
        "DELIV-ZERO-R",
    ]
    assert res["excessive_consulted_or_role_overload_deliverable_ids"] == [
        "DELIV-ZERO-R"
    ]
    assert (
        res["raci_governance_status"]
        == "RACI_ACCOUNTABILITY_OR_RESPONSIBLE_BREACH"
    )
    assert res["is_raci_matrix_valid"] is False


def test_validate_raci_matrix_single_accountable_and_role_overload_warning():
    from backend.schemas.projects import (
        validate_raci_matrix_single_accountable_and_role_overload,
    )

    res = validate_raci_matrix_single_accountable_and_role_overload(
        [
            {
                "deliverable_id": "DELIV-TOO-MANY-C",
                "accountable_count": 1,
                "responsible_count": 0,
                "consulted_count": 6,
                "accountable_and_responsible_same_person_overloaded": False,
            },
            {
                "deliverable_id": "DELIV-OVERLOADED-AR",
                "accountable_count": 1,
                "responsible_count": 1,
                "consulted_count": 5,
                "accountable_and_responsible_same_person_overloaded": True,
            },
        ],
        max_consulted_reviewers=5,
        require_at_least_one_responsible=False,
    )
    assert res["evaluated_deliverables_count"] == 2
    assert res["ambiguous_accountability_or_unassigned_deliverable_ids"] == []
    assert res["excessive_consulted_or_role_overload_deliverable_ids"] == [
        "DELIV-TOO-MANY-C",
        "DELIV-OVERLOADED-AR",
    ]
    assert (
        res["raci_governance_status"]
        == "RACI_CONSULTED_BLOAT_OR_OVERLOAD_WARNING"
    )
    assert res["is_raci_matrix_valid"] is False


def test_validate_raci_matrix_single_accountable_and_role_overload_optimal_and_boundaries():
    from backend.schemas.projects import (
        validate_raci_matrix_single_accountable_and_role_overload,
    )

    res = validate_raci_matrix_single_accountable_and_role_overload(
        [
            {
                "deliverable_id": "DELIV-BOUNDARY",
                "accountable_count": 1,
                "responsible_count": 1,
                "consulted_count": 5,
                "accountable_and_responsible_same_person_overloaded": False,
            }
        ],
        max_consulted_reviewers=5,
        require_at_least_one_responsible=True,
    )
    assert res["evaluated_deliverables_count"] == 1
    assert res["ambiguous_accountability_or_unassigned_deliverable_ids"] == []
    assert res["excessive_consulted_or_role_overload_deliverable_ids"] == []
    assert res["raci_governance_status"] == "RACI_MATRIX_ALIGNMENT_OPTIMAL"
    assert res["is_raci_matrix_valid"] is True


def test_validate_raci_matrix_single_accountable_and_role_overload_defensive_and_dunder_all():
    import backend.schemas.projects as mod
    from backend.schemas.projects import (
        validate_raci_matrix_single_accountable_and_role_overload,
    )

    empty = validate_raci_matrix_single_accountable_and_role_overload(None)
    assert empty["evaluated_deliverables_count"] == 0
    assert empty["raci_governance_status"] == "RACI_MATRIX_ALIGNMENT_OPTIMAL"
    assert empty["is_raci_matrix_valid"] is True

    defaults = validate_raci_matrix_single_accountable_and_role_overload(
        [
            "not-a-dict",  # type: ignore[list-item]
            {"deliverable_id": "   "},
            {
                "deliverable_id": "DELIV-DEFAULTS",
                "accountable_count": None,
                "responsible_count": None,
                "consulted_count": None,
                "accountable_and_responsible_same_person_overloaded": None,
            },
        ]
    )
    assert defaults["evaluated_deliverables_count"] == 1
    assert (
        defaults["raci_governance_status"] == "RACI_MATRIX_ALIGNMENT_OPTIMAL"
    )
    assert defaults["is_raci_matrix_valid"] is True
    assert (
        "validate_raci_matrix_single_accountable_and_role_overload"
        in mod.__all__
    )


def test_validate_risk_bowtie_barrier_redundancy_and_independence_breach():
    from backend.schemas.projects import (
        validate_risk_bowtie_barrier_redundancy_and_independence,
    )

    res = validate_risk_bowtie_barrier_redundancy_and_independence(
        [
            {
                "hazard_id": "  HAZ-CMF  ",
                "preventive_barriers_count": 3,
                "mitigative_barriers_count": 2,
                "common_mode_failure_present": True,
                "escalation_factors_controlled": True,
            },
            {
                "hazard_id": "HAZ-ZERO-PREV",
                "preventive_barriers_count": 0,
                "mitigative_barriers_count": 2,
                "common_mode_failure_present": False,
                "escalation_factors_controlled": True,
            },
            {
                "hazard_id": "HAZ-ZERO-MIT",
                "preventive_barriers_count": 2,
                "mitigative_barriers_count": 0,
                "common_mode_failure_present": False,
                "escalation_factors_controlled": False,
            },
            {
                "hazard_id": "HAZ-CLEAN",
                "preventive_barriers_count": 2,
                "mitigative_barriers_count": 2,
                "common_mode_failure_present": False,
                "escalation_factors_controlled": True,
            },
        ]
    )
    assert res["evaluated_hazards_count"] == 4
    assert res["single_point_or_common_mode_hazard_ids"] == [
        "HAZ-CMF",
        "HAZ-ZERO-PREV",
        "HAZ-ZERO-MIT",
    ]
    assert res["low_redundancy_or_escalation_hazard_ids"] == [
        "HAZ-ZERO-PREV",
        "HAZ-ZERO-MIT",
    ]
    assert (
        res["bowtie_barrier_status"]
        == "BOWTIE_COMMON_MODE_OR_ZERO_BARRIER_BREACH"
    )
    assert res["is_bowtie_barrier_valid"] is False


def test_validate_risk_bowtie_barrier_redundancy_and_independence_warning():
    from backend.schemas.projects import (
        validate_risk_bowtie_barrier_redundancy_and_independence,
    )

    res = validate_risk_bowtie_barrier_redundancy_and_independence(
        [
            {
                "hazard_id": "HAZ-LOW-PREV",
                "preventive_barriers_count": 1,
                "mitigative_barriers_count": 2,
                "common_mode_failure_present": False,
                "escalation_factors_controlled": True,
            },
            {
                "hazard_id": "HAZ-LOW-MIT",
                "preventive_barriers_count": 2,
                "mitigative_barriers_count": 1,
                "common_mode_failure_present": False,
                "escalation_factors_controlled": True,
            },
            {
                "hazard_id": "HAZ-UNCTRL-ESC",
                "preventive_barriers_count": 3,
                "mitigative_barriers_count": 3,
                "common_mode_failure_present": False,
                "escalation_factors_controlled": False,
            },
        ],
        min_preventive_barriers=2,
        min_mitigative_barriers=2,
    )
    assert res["evaluated_hazards_count"] == 3
    assert res["single_point_or_common_mode_hazard_ids"] == []
    assert res["low_redundancy_or_escalation_hazard_ids"] == [
        "HAZ-LOW-PREV",
        "HAZ-LOW-MIT",
        "HAZ-UNCTRL-ESC",
    ]
    assert (
        res["bowtie_barrier_status"]
        == "BOWTIE_REDUNDANCY_OR_ESCALATION_WARNING"
    )
    assert res["is_bowtie_barrier_valid"] is False


def test_validate_risk_bowtie_barrier_redundancy_and_independence_optimal_and_boundaries():
    from backend.schemas.projects import (
        validate_risk_bowtie_barrier_redundancy_and_independence,
    )

    res = validate_risk_bowtie_barrier_redundancy_and_independence(
        [
            {
                "hazard_id": "HAZ-BOUNDARY",
                "preventive_barriers_count": 2,
                "mitigative_barriers_count": 2,
                "common_mode_failure_present": False,
                "escalation_factors_controlled": True,
            }
        ],
        min_preventive_barriers=2,
        min_mitigative_barriers=2,
    )
    assert res["evaluated_hazards_count"] == 1
    assert res["single_point_or_common_mode_hazard_ids"] == []
    assert res["low_redundancy_or_escalation_hazard_ids"] == []
    assert res["bowtie_barrier_status"] == "BOWTIE_DEFENSE_IN_DEPTH_OPTIMAL"
    assert res["is_bowtie_barrier_valid"] is True


def test_validate_risk_bowtie_barrier_redundancy_and_independence_defensive_and_dunder_all():
    import backend.schemas.projects as mod
    from backend.schemas.projects import (
        validate_risk_bowtie_barrier_redundancy_and_independence,
    )

    empty = validate_risk_bowtie_barrier_redundancy_and_independence(None)
    assert empty["evaluated_hazards_count"] == 0
    assert empty["bowtie_barrier_status"] == "BOWTIE_DEFENSE_IN_DEPTH_OPTIMAL"
    assert empty["is_bowtie_barrier_valid"] is True

    defaults = validate_risk_bowtie_barrier_redundancy_and_independence(
        [
            "not-a-dict",  # type: ignore[list-item]
            {"hazard_id": "   "},
            {
                "hazard_id": "HAZ-DEFAULTS",
                "preventive_barriers_count": None,
                "mitigative_barriers_count": None,
                "common_mode_failure_present": None,
                "escalation_factors_controlled": None,
            },
        ]
    )
    assert defaults["evaluated_hazards_count"] == 1
    assert (
        defaults["bowtie_barrier_status"]
        == "BOWTIE_DEFENSE_IN_DEPTH_OPTIMAL"
    )
    assert defaults["is_bowtie_barrier_valid"] is True
    assert (
        "validate_risk_bowtie_barrier_redundancy_and_independence"
        in mod.__all__
    )


def test_validate_moscow_prioritization_must_have_inflation_and_mvp_cap_breach():
    from backend.schemas.projects import (
        validate_moscow_prioritization_must_have_inflation_and_mvp_cap,
    )

    res = validate_moscow_prioritization_must_have_inflation_and_mvp_cap(
        [
            {
                "release_id": "REL-UNPRIO",
                "must_have_effort_share_pct": 55.0,
                "could_have_effort_share_pct": 22.0,
                "wont_have_explicitly_documented": True,
                "unprioritized_backlog_items_count": 3,
            },
            {
                "release_id": "REL-NO-WONT",
                "must_have_effort_share_pct": 75.0,
                "could_have_effort_share_pct": 10.0,
                "wont_have_explicitly_documented": False,
                "unprioritized_backlog_items_count": 0,
            },
            {
                "release_id": "REL-CLEAN",
                "must_have_effort_share_pct": 58.0,
                "could_have_effort_share_pct": 22.0,
                "wont_have_explicitly_documented": True,
                "unprioritized_backlog_items_count": 0,
            },
        ]
    )
    assert res["evaluated_releases_count"] == 3
    assert res["unprioritized_or_missing_wont_have_release_ids"] == [
        "REL-UNPRIO",
        "REL-NO-WONT",
    ]
    assert res["must_have_inflated_or_low_buffer_release_ids"] == [
        "REL-NO-WONT"
    ]
    assert (
        res["moscow_prioritization_status"]
        == "MOSCOW_UNPRIORITIZED_OR_SCOPE_BOUNDARY_BREACH"
    )
    assert res["is_moscow_prioritization_valid"] is False


def test_validate_moscow_prioritization_must_have_inflation_and_mvp_cap_warning():
    from backend.schemas.projects import (
        validate_moscow_prioritization_must_have_inflation_and_mvp_cap,
    )

    res = validate_moscow_prioritization_must_have_inflation_and_mvp_cap(
        [
            {
                "release_id": "REL-INFLATED",
                "must_have_effort_share_pct": 65.0,
                "could_have_effort_share_pct": 22.0,
                "wont_have_explicitly_documented": True,
                "unprioritized_backlog_items_count": 0,
            },
            {
                "release_id": "REL-LOW-BUF",
                "must_have_effort_share_pct": 55.0,
                "could_have_effort_share_pct": 15.0,
                "wont_have_explicitly_documented": True,
                "unprioritized_backlog_items_count": 0,
            },
        ],
        max_must_have_effort_share_pct=60.0,
        min_could_have_contingency_share_pct=20.0,
    )
    assert res["evaluated_releases_count"] == 2
    assert res["unprioritized_or_missing_wont_have_release_ids"] == []
    assert res["must_have_inflated_or_low_buffer_release_ids"] == [
        "REL-INFLATED",
        "REL-LOW-BUF",
    ]
    assert (
        res["moscow_prioritization_status"]
        == "MOSCOW_MUST_HAVE_INFLATION_OR_BUFFER_WARNING"
    )
    assert res["is_moscow_prioritization_valid"] is False


def test_validate_moscow_prioritization_must_have_inflation_and_mvp_cap_optimal_and_boundaries():
    from backend.schemas.projects import (
        validate_moscow_prioritization_must_have_inflation_and_mvp_cap,
    )

    res = validate_moscow_prioritization_must_have_inflation_and_mvp_cap(
        [
            {
                "release_id": "REL-BOUNDARY",
                "must_have_effort_share_pct": 60.0,
                "could_have_effort_share_pct": 20.0,
                "wont_have_explicitly_documented": True,
                "unprioritized_backlog_items_count": 0,
            }
        ],
        max_must_have_effort_share_pct=60.0,
        min_could_have_contingency_share_pct=20.0,
    )
    assert res["evaluated_releases_count"] == 1
    assert res["unprioritized_or_missing_wont_have_release_ids"] == []
    assert res["must_have_inflated_or_low_buffer_release_ids"] == []
    assert (
        res["moscow_prioritization_status"]
        == "MOSCOW_PRIORITIZATION_BALANCE_OPTIMAL"
    )
    assert res["is_moscow_prioritization_valid"] is True


def test_validate_moscow_prioritization_must_have_inflation_and_mvp_cap_defensive_and_dunder_all():
    import backend.schemas.projects as mod
    from backend.schemas.projects import (
        validate_moscow_prioritization_must_have_inflation_and_mvp_cap,
    )

    empty = validate_moscow_prioritization_must_have_inflation_and_mvp_cap(None)
    assert empty["evaluated_releases_count"] == 0
    assert (
        empty["moscow_prioritization_status"]
        == "MOSCOW_PRIORITIZATION_BALANCE_OPTIMAL"
    )
    assert empty["is_moscow_prioritization_valid"] is True

    defaults = validate_moscow_prioritization_must_have_inflation_and_mvp_cap(
        [
            "not-a-dict",  # type: ignore[list-item]
            {"release_id": "   "},
            {
                "release_id": "REL-DEFAULTS",
                "must_have_effort_share_pct": None,
                "could_have_effort_share_pct": None,
                "wont_have_explicitly_documented": None,
                "unprioritized_backlog_items_count": None,
            },
        ]
    )
    assert defaults["evaluated_releases_count"] == 1
    assert (
        defaults["moscow_prioritization_status"]
        == "MOSCOW_PRIORITIZATION_BALANCE_OPTIMAL"
    )
    assert defaults["is_moscow_prioritization_valid"] is True
    assert (
        "validate_moscow_prioritization_must_have_inflation_and_mvp_cap"
        in mod.__all__
    )


def test_validate_work_package_8_80_rule_duration_and_effort_granularity_valid_and_milestone():
    from backend.schemas.projects import (
        validate_work_package_8_80_rule_duration_and_effort_granularity,
    )

    res = validate_work_package_8_80_rule_duration_and_effort_granularity(
        [
            {
                "wp_id": "WP-101",
                "estimated_effort_hours": 40.0,
                "duration_days": 5.0,
                "control_account_id": "CA-01",
                "owner_id": "USR-01",
                "is_milestone": False,
            },
            {
                "wp_id": "MS-01",
                "estimated_effort_hours": 0.0,
                "duration_days": 0.0,
                "control_account_ids": ["CA-01"],
                "owner_ids": ["USR-01"],
                "is_milestone": True,
            },
        ]
    )
    assert res["is_valid"] is True
    assert res["status"] == "valid"
    assert res["packages_evaluated"] == 2
    assert res["micromanaged_wp_ids"] == []
    assert res["under_decomposed_wp_ids"] == []
    assert res["accountability_violation_wp_ids"] == []
    assert res["Violations"] == []


def test_validate_work_package_8_80_rule_duration_and_effort_granularity_critical():
    from backend.schemas.projects import (
        validate_work_package_8_80_rule_duration_and_effort_granularity,
    )

    res = validate_work_package_8_80_rule_duration_and_effort_granularity(
        [
            {
                "wp_id": "WP-OVER-80",
                "estimated_effort_hours": 120.0,
                "duration_days": 15.0,
                "control_account_ids": ["CA-01", "CA-02"],
                "owner_ids": [],
            }
        ]
    )
    assert res["is_valid"] is False
    assert res["status"] == "critical"
    assert res["packages_evaluated"] == 1
    assert res["under_decomposed_wp_ids"] == ["WP-OVER-80"]
    assert res["accountability_violation_wp_ids"] == ["WP-OVER-80"]
    assert len(res["Violations"]) >= 2


def test_validate_work_package_8_80_rule_duration_and_effort_granularity_warning_micromanaged():
    from backend.schemas.projects import (
        validate_work_package_8_80_rule_duration_and_effort_granularity,
    )

    res = validate_work_package_8_80_rule_duration_and_effort_granularity(
        [
            {
                "id": "WP-TINY",
                "estimated_effort_hours": 4.0,
                "duration_days": 1.0,
                "control_account_id": "CA-01",
                "owner_id": "USR-01",
            }
        ]
    )
    assert res["is_valid"] is False
    assert res["status"] == "warning"
    assert res["micromanaged_wp_ids"] == ["WP-TINY"]
    assert res["under_decomposed_wp_ids"] == []
    assert res["accountability_violation_wp_ids"] == []


def test_validate_work_package_8_80_rule_duration_and_effort_granularity_empty_and_dunder_all():
    import backend.schemas.projects as mod
    from backend.schemas.projects import (
        validate_work_package_8_80_rule_duration_and_effort_granularity,
    )

    empty = validate_work_package_8_80_rule_duration_and_effort_granularity([])
    assert empty["is_valid"] is True
    assert empty["status"] == "valid"
    assert empty["packages_evaluated"] == 0
    assert (
        "validate_work_package_8_80_rule_duration_and_effort_granularity"
        in mod.__all__
    )


# ── validate_monte_carlo_schedule_risk_p80_buffer_and_convergence (PMBOK §11.4 & §6.5, pure helper) ──


def test_monte_carlo_p80_optimal_simulations():
    """Simulaciones con buffer suficiente (>= requerido) e iteraciones/CV saludables -> 'MONTE_CARLO_P80_GOVERNANCE_OPTIMAL'."""
    import backend.schemas.projects as projects_module
    from backend.schemas.projects import (
        validate_monte_carlo_schedule_risk_p80_buffer_and_convergence,
    )

    simulations = [
        {
            "simulation_id": "MC-001",
            "iterations_run": 5000,
            "convergence_cv_pct": 0.8,
            "deterministic_duration_days": 100.0,
            "p80_duration_days": 112.0,
            "allocated_buffer_days": 15.0,
        },
        {
            "simulation_id": "MC-002",
            # Defaults implícitos por campo: 5000 iter, CV 0.8, 100.0 det, 112.0 P80, 15.0 buffer.
        },
    ]
    res = validate_monte_carlo_schedule_risk_p80_buffer_and_convergence(simulations)
    assert res == {
        "evaluated_simulations_count": 2,
        "underbuffered_p80_simulation_ids": [],
        "unconverged_or_low_iteration_simulation_ids": [],
        "monte_carlo_status": "MONTE_CARLO_P80_GOVERNANCE_OPTIMAL",
        "is_monte_carlo_valid": True,
    }
    # Buffer asignado exactamente en el requerido (12.0) no es deficit (comparación estricta <)
    exact_buffer = validate_monte_carlo_schedule_risk_p80_buffer_and_convergence(
        [
            {
                "simulation_id": "MC-003",
                "deterministic_duration_days": 100.0,
                "p80_duration_days": 112.0,
                "allocated_buffer_days": 12.0,
            }
        ]
    )
    assert exact_buffer["monte_carlo_status"] == "MONTE_CARLO_P80_GOVERNANCE_OPTIMAL"
    assert "validate_monte_carlo_schedule_risk_p80_buffer_and_convergence" in projects_module.__all__


def test_monte_carlo_p80_buffer_deficit_breach():
    """Buffer asignado < requerido P80 -> 'P80_CONTINGENCY_BUFFER_DEFICIT_BREACH' con precedencia sobre WARNING."""
    from backend.schemas.projects import (
        validate_monte_carlo_schedule_risk_p80_buffer_and_convergence,
    )

    breach = validate_monte_carlo_schedule_risk_p80_buffer_and_convergence(
        [
            {
                "simulation_id": "MC-DEFICIT",
                "deterministic_duration_days": 100.0,
                "p80_duration_days": 112.0,
                "allocated_buffer_days": 10.0,
            },
            {
                "simulation_id": "MC-ZERO-BUFFER",
                "deterministic_duration_days": 80.0,
                "p80_duration_days": 90.0,
                "allocated_buffer_days": 0.0,
            },
        ]
    )
    assert breach["evaluated_simulations_count"] == 2
    assert breach["underbuffered_p80_simulation_ids"] == ["MC-DEFICIT", "MC-ZERO-BUFFER"]
    assert breach["monte_carlo_status"] == "P80_CONTINGENCY_BUFFER_DEFICIT_BREACH"
    assert breach["is_monte_carlo_valid"] is False

    # Breach tiene precedencia aunque también haya simulaciones sin convergencia
    mixed = validate_monte_carlo_schedule_risk_p80_buffer_and_convergence(
        [
            {"simulation_id": "MC-LOW-ITER", "iterations_run": 500},
            {"simulation_id": "MC-DEFICIT-2", "allocated_buffer_days": 5.0},
        ]
    )
    assert mixed["monte_carlo_status"] == "P80_CONTINGENCY_BUFFER_DEFICIT_BREACH"


def test_monte_carlo_convergence_or_iteration_warning():
    """Iteraciones < 1000 o CV > 1.5 (con buffer suficiente) -> 'MONTE_CARLO_CONVERGENCE_OR_ITERATION_WARNING'."""
    from backend.schemas.projects import (
        validate_monte_carlo_schedule_risk_p80_buffer_and_convergence,
    )

    warning = validate_monte_carlo_schedule_risk_p80_buffer_and_convergence(
        [
            {
                "simulation_id": "MC-LOW-ITER",
                "iterations_run": 999,
                "convergence_cv_pct": 0.5,
            },
            {
                "simulation_id": "MC-HIGH-CV",
                "iterations_run": 20000,
                "convergence_cv_pct": 1.6,
            },
        ]
    )
    assert warning["evaluated_simulations_count"] == 2
    assert warning["underbuffered_p80_simulation_ids"] == []
    assert warning["unconverged_or_low_iteration_simulation_ids"] == [
        "MC-LOW-ITER",
        "MC-HIGH-CV",
    ]
    assert warning["monte_carlo_status"] == (
        "MONTE_CARLO_CONVERGENCE_OR_ITERATION_WARNING"
    )
    assert warning["is_monte_carlo_valid"] is False

    # CV exactamente en el umbral 1.5 con iteraciones suficientes no es warning (comparación estricta >)
    at_threshold = validate_monte_carlo_schedule_risk_p80_buffer_and_convergence(
        [
            {
                "simulation_id": "MC-THRESHOLD",
                "iterations_run": 1000,
                "convergence_cv_pct": 1.5,
            }
        ]
    )
    assert at_threshold["monte_carlo_status"] == "MONTE_CARLO_P80_GOVERNANCE_OPTIMAL"

    custom = validate_monte_carlo_schedule_risk_p80_buffer_and_convergence(
        [{"simulation_id": "MC-4", "iterations_run": 5000, "convergence_cv_pct": 0.9}],
        min_iterations=6000,
        max_convergence_cv_pct=0.8,
    )
    assert custom["monte_carlo_status"] == (
        "MONTE_CARLO_CONVERGENCE_OR_ITERATION_WARNING"
    )
    assert custom["unconverged_or_low_iteration_simulation_ids"] == ["MC-4"]


def test_monte_carlo_empty_invalid_fields_and_no_simulations():
    """None / dicts inválidos se descartan; campos no numéricos revierten a defaults del spec."""
    from backend.schemas.projects import (
        validate_monte_carlo_schedule_risk_p80_buffer_and_convergence,
    )

    empty_res = validate_monte_carlo_schedule_risk_p80_buffer_and_convergence(None)
    assert empty_res == {
        "evaluated_simulations_count": 0,
        "underbuffered_p80_simulation_ids": [],
        "unconverged_or_low_iteration_simulation_ids": [],
        "monte_carlo_status": "MONTE_CARLO_P80_GOVERNANCE_OPTIMAL",
        "is_monte_carlo_valid": True,
    }

    invalid_res = validate_monte_carlo_schedule_risk_p80_buffer_and_convergence(
        [
            "no-dict",
            None,
            {"simulation_id": "   "},
            {"simulation_id": 123},
            {"iterations_run": 20000},
        ]
    )
    assert invalid_res["evaluated_simulations_count"] == 0

    bad_fields = validate_monte_carlo_schedule_risk_p80_buffer_and_convergence(
        [
            {
                "simulation_id": "MC-BAD",
                "iterations_run": "muchas",
                "convergence_cv_pct": None,
                "deterministic_duration_days": [100.0],
                "p80_duration_days": "112.0",
                "allocated_buffer_days": True,
            }
        ]
    )
    assert bad_fields == {
        "evaluated_simulations_count": 1,
        "underbuffered_p80_simulation_ids": [],
        "unconverged_or_low_iteration_simulation_ids": [],
        "monte_carlo_status": "MONTE_CARLO_P80_GOVERNANCE_OPTIMAL",
        "is_monte_carlo_valid": True,
    }


def test_validate_resource_leveling_overallocation_peak_and_float_consumption_valid():
    from backend.schemas.projects import (
        validate_resource_leveling_overallocation_peak_and_float_consumption,
    )

    res = validate_resource_leveling_overallocation_peak_and_float_consumption(
        [
            {
                "resource_id": "RES-ENG-01",
                "optimization_mode": "Smoothing",
                "peak_utilization_pct": 92.0,
                "available_free_float_days": 10.0,
                "consumed_float_days": 5.0,
                "critical_path_extended_days": 0.0,
                "ccb_baseline_change_approved": True,
            }
        ]
    )
    assert res["is_valid"] is True
    assert res["status"] == "valid"
    assert res["resources_evaluated"] == 1
    assert res["overallocated_or_illegal_extension_resource_ids"] == []
    assert res["float_exhaustion_resource_ids"] == []
    assert res["records"][0]["float_consumption_pct"] == 50.0
    assert res["Violations"] == []


def test_validate_resource_leveling_overallocation_peak_and_float_consumption_critical():
    from backend.schemas.projects import (
        validate_resource_leveling_overallocation_peak_and_float_consumption,
    )

    res = validate_resource_leveling_overallocation_peak_and_float_consumption(
        [
            {
                "resource_id": "RES-OVERLOAD",
                "optimization_mode": "smoothing",
                "peak_utilization_pct": 135.0,
                "available_free_float_days": 5.0,
                "consumed_float_days": 5.0,
                "critical_path_extended_days": 3.0,
            },
            {
                "id": "RES-LEVELING-NO-CCB",
                "optimization_mode": "leveling",
                "peak_utilization_pct": 95.0,
                "critical_path_extended_days": 4.0,
                "ccb_baseline_change_approved": False,
            },
        ]
    )
    assert res["is_valid"] is False
    assert res["status"] == "critical"
    assert res["overallocated_or_illegal_extension_resource_ids"] == [
        "RES-OVERLOAD",
        "RES-LEVELING-NO-CCB",
    ]
    assert len(res["Violations"]) >= 3


def test_validate_resource_leveling_overallocation_peak_and_float_consumption_warning():
    from backend.schemas.projects import (
        validate_resource_leveling_overallocation_peak_and_float_consumption,
    )

    res = validate_resource_leveling_overallocation_peak_and_float_consumption(
        [
            {
                "resource_id": "RES-FLOAT-BURN",
                "optimization_mode": "smoothing",
                "peak_utilization_pct": 98.0,
                "available_free_float_days": 10.0,
                "consumed_float_days": 9.0,
                "critical_path_extended_days": 0.0,
            }
        ],
        max_smoothing_float_consumption_pct=80.0,
    )
    assert res["is_valid"] is False
    assert res["status"] == "warning"
    assert res["overallocated_or_illegal_extension_resource_ids"] == []
    assert res["float_exhaustion_resource_ids"] == ["RES-FLOAT-BURN"]
    assert res["records"][0]["excessive_float_consumption"] is True


def test_validate_resource_leveling_overallocation_peak_and_float_consumption_dunder_all():
    import backend.schemas.projects as mod
    from backend.schemas.projects import (
        validate_resource_leveling_overallocation_peak_and_float_consumption,
    )

    empty = validate_resource_leveling_overallocation_peak_and_float_consumption([])
    assert empty["is_valid"] is True
    assert empty["status"] == "valid"
    assert empty["resources_evaluated"] == 0
    assert (
        "validate_resource_leveling_overallocation_peak_and_float_consumption"
        in mod.__all__
    )


# ── validate_agile_hybrid_velocity_stability_and_wip_carryover (PMBOK §6.4 & §6.6, pure helper) ──


def test_agile_hybrid_flow_optimal_iterations():
    """Iteraciones con WIP <= límite, carryover <= 15.0 y CV <= 20.0 -> 'AGILE_HYBRID_FLOW_OPTIMAL'."""
    import backend.schemas.projects as projects_module
    from backend.schemas.projects import (
        validate_agile_hybrid_velocity_stability_and_wip_carryover,
    )

    iterations = [
        {
            "iteration_id": "ITER-001",
            "active_wip_items": 6,
            "kanban_wip_limit": 8,
            "carryover_points_pct": 10.0,
            "velocity_volatility_cv_pct": 12.0,
        },
        {
            "iteration_id": "ITER-002",
            # Defaults implícitos por campo: 6 WIP, límite 8, 10.0 carryover, 12.0 CV.
        },
    ]
    res = validate_agile_hybrid_velocity_stability_and_wip_carryover(iterations)
    assert res == {
        "evaluated_iterations_count": 2,
        "wip_breach_or_high_carryover_iteration_ids": [],
        "volatile_velocity_iteration_ids": [],
        "velocity_wip_status": "AGILE_HYBRID_FLOW_OPTIMAL",
        "is_agile_flow_valid": True,
    }
    # WIP exactamente en el límite (8 == 8) no es breach (comparación estricta >)
    at_wip_limit = validate_agile_hybrid_velocity_stability_and_wip_carryover(
        [{"iteration_id": "ITER-003", "active_wip_items": 8, "kanban_wip_limit": 8}]
    )
    assert at_wip_limit["velocity_wip_status"] == "AGILE_HYBRID_FLOW_OPTIMAL"
    # Carryover exactamente en el umbral 15.0 no es breach (comparación estricta >)
    at_carryover = validate_agile_hybrid_velocity_stability_and_wip_carryover(
        [{"iteration_id": "ITER-004", "carryover_points_pct": 15.0}]
    )
    assert at_carryover["velocity_wip_status"] == "AGILE_HYBRID_FLOW_OPTIMAL"
    assert "validate_agile_hybrid_velocity_stability_and_wip_carryover" in projects_module.__all__


def test_agile_hybrid_wip_or_carryover_breach():
    """WIP activo > límite Kanban o carryover > 15.0 -> 'WIP_LIMIT_OR_CARRYOVER_DEBT_BREACH' con precedencia sobre WARNING."""
    from backend.schemas.projects import (
        validate_agile_hybrid_velocity_stability_and_wip_carryover,
    )

    breach = validate_agile_hybrid_velocity_stability_and_wip_carryover(
        [
            {
                "iteration_id": "ITER-WIP-BREACH",
                "active_wip_items": 9,
                "kanban_wip_limit": 8,
            },
            {
                "iteration_id": "ITER-CARRYOVER",
                "carryover_points_pct": 18.5,
            },
        ]
    )
    assert breach["evaluated_iterations_count"] == 2
    assert breach["wip_breach_or_high_carryover_iteration_ids"] == [
        "ITER-WIP-BREACH",
        "ITER-CARRYOVER",
    ]
    assert breach["volatile_velocity_iteration_ids"] == []
    assert breach["velocity_wip_status"] == "WIP_LIMIT_OR_CARRYOVER_DEBT_BREACH"
    assert breach["is_agile_flow_valid"] is False

    # Breach tiene precedencia aunque también haya iteraciones volátiles
    mixed = validate_agile_hybrid_velocity_stability_and_wip_carryover(
        [
            {"iteration_id": "ITER-VOLATILE", "velocity_volatility_cv_pct": 25.0},
            {"iteration_id": "ITER-WIP-BREACH-2", "active_wip_items": 10},
        ]
    )
    assert mixed["velocity_wip_status"] == "WIP_LIMIT_OR_CARRYOVER_DEBT_BREACH"

    # Carryover <= 16.0 con límite custom deja la iteración como limpia
    custom = validate_agile_hybrid_velocity_stability_and_wip_carryover(
        [{"iteration_id": "ITER-3", "carryover_points_pct": 16.0}],
        max_carryover_rate_pct=16.0,
    )
    assert custom["velocity_wip_status"] == "AGILE_HYBRID_FLOW_OPTIMAL"


def test_agile_hybrid_velocity_volatility_warning():
    """CV de velodidad > 20.0 (con WIP y carryover limpios) -> 'VELOCITY_VOLATILITY_INSTABILITY_WARNING'."""
    from backend.schemas.projects import (
        validate_agile_hybrid_velocity_stability_and_wip_carryover,
    )

    warning = validate_agile_hybrid_velocity_stability_and_wip_carryover(
        [
            {
                "iteration_id": "ITER-VOL-A",
                "velocity_volatility_cv_pct": 22.5,
            },
            {
                "iteration_id": "ITER-VOL-B",
                "velocity_volatility_cv_pct": 30.0,
            },
        ]
    )
    assert warning["evaluated_iterations_count"] == 2
    assert warning["wip_breach_or_high_carryover_iteration_ids"] == []
    assert warning["volatile_velocity_iteration_ids"] == ["ITER-VOL-A", "ITER-VOL-B"]
    assert warning["velocity_wip_status"] == "VELOCITY_VOLATILITY_INSTABILITY_WARNING"
    assert warning["is_agile_flow_valid"] is False

    # CV exactamente en el umbral 20.0 no es warning (comparación estricta >)
    at_threshold = validate_agile_hybrid_velocity_stability_and_wip_carryover(
        [{"iteration_id": "ITER-VOL-C", "velocity_volatility_cv_pct": 20.0}]
    )
    assert at_threshold["velocity_wip_status"] == "AGILE_HYBRID_FLOW_OPTIMAL"

    custom = validate_agile_hybrid_velocity_stability_and_wip_carryover(
        [{"iteration_id": "ITER-VOL-D", "velocity_volatility_cv_pct": 15.0}],
        max_velocity_volatility_cv_pct=14.0,
    )
    assert custom["velocity_wip_status"] == "VELOCITY_VOLATILITY_INSTABILITY_WARNING"
    assert custom["volatile_velocity_iteration_ids"] == ["ITER-VOL-D"]


def test_agile_hybrid_empty_invalid_and_field_reversion():
    """None / dicts inválidos se descartan; campos no numéricos revierten a defaults del spec."""
    from backend.schemas.projects import (
        validate_agile_hybrid_velocity_stability_and_wip_carryover,
    )

    empty_res = validate_agile_hybrid_velocity_stability_and_wip_carryover(None)
    assert empty_res == {
        "evaluated_iterations_count": 0,
        "wip_breach_or_high_carryover_iteration_ids": [],
        "volatile_velocity_iteration_ids": [],
        "velocity_wip_status": "AGILE_HYBRID_FLOW_OPTIMAL",
        "is_agile_flow_valid": True,
    }

    invalid_res = validate_agile_hybrid_velocity_stability_and_wip_carryover(
        ["no-dict", None, {"iteration_id": "   "}, {"iteration_id": 7}, {"active_wip_items": 20}]
    )
    assert invalid_res["evaluated_iterations_count"] == 0

    bad_fields = validate_agile_hybrid_velocity_stability_and_wip_carryover(
        [
            {
                "iteration_id": "ITER-BAD",
                "active_wip_items": "nueve",
                "kanban_wip_limit": None,
                "carryover_points_pct": "diez",
                "velocity_volatility_cv_pct": [25.0],
            }
        ]
    )
    assert bad_fields == {
        "evaluated_iterations_count": 1,
        "wip_breach_or_high_carryover_iteration_ids": [],
        "volatile_velocity_iteration_ids": [],
        "velocity_wip_status": "AGILE_HYBRID_FLOW_OPTIMAL",
        "is_agile_flow_valid": True,
    }


def test_validate_benefits_realization_npv_irr_payback_and_benefit_owner_alignment_valid():
    from backend.schemas.projects import (
        validate_benefits_realization_npv_irr_payback_and_benefit_owner_alignment,
    )

    res = validate_benefits_realization_npv_irr_payback_and_benefit_owner_alignment(
        [
            {
                "case_id": "BEN-ERP-01",
                "npv_usd": 450000.0,
                "irr_pct": 14.5,
                "wacc_discount_rate_pct": 9.0,
                "payback_period_months": 24,
                "benefit_owner_id": "VP-FIN-01",
                "realization_metric_baseline_defined": True,
            }
        ]
    )
    assert res["is_valid"] is True
    assert res["status"] == "valid"
    assert res["cases_evaluated"] == 1
    assert res["unviable_or_unowned_case_ids"] == []
    assert res["subhurdle_irr_or_payback_case_ids"] == []
    assert res["records"][0]["irr_spread_bps"] == 550.0
    assert res["Violations"] == []


def test_validate_benefits_realization_npv_irr_payback_and_benefit_owner_alignment_critical():
    from backend.schemas.projects import (
        validate_benefits_realization_npv_irr_payback_and_benefit_owner_alignment,
    )

    res = validate_benefits_realization_npv_irr_payback_and_benefit_owner_alignment(
        [
            {
                "case_id": "BEN-NEG-NPV",
                "npv_usd": -25000.0,
                "irr_pct": 12.0,
                "wacc_discount_rate_pct": 8.0,
                "payback_period_months": 18,
                "benefit_owner_id": "   ",
                "realization_metric_baseline_defined": False,
            }
        ]
    )
    assert res["is_valid"] is False
    assert res["status"] == "critical"
    assert res["unviable_or_unowned_case_ids"] == ["BEN-NEG-NPV"]
    assert len(res["Violations"]) >= 1


def test_validate_benefits_realization_npv_irr_payback_and_benefit_owner_alignment_warning():
    from backend.schemas.projects import (
        validate_benefits_realization_npv_irr_payback_and_benefit_owner_alignment,
    )

    res = validate_benefits_realization_npv_irr_payback_and_benefit_owner_alignment(
        [
            {
                "id": "BEN-SLOW-PAYBACK",
                "npv_usd": 80000.0,
                "irr_pct": 9.8,
                "wacc_discount_rate_pct": 9.0,
                "payback_period_months": 48,
                "benefit_owner_id": "DIR-OPS-02",
                "realization_metric_baseline_defined": True,
            }
        ],
        min_irr_above_wacc_bps=150.0,
        max_payback_months=36,
    )
    assert res["is_valid"] is False
    assert res["status"] == "warning"
    assert res["unviable_or_unowned_case_ids"] == []
    assert res["subhurdle_irr_or_payback_case_ids"] == ["BEN-SLOW-PAYBACK"]
    assert res["records"][0]["irr_hurdle_or_payback_exceeded"] is True


def test_validate_benefits_realization_npv_irr_payback_and_benefit_owner_alignment_dunder_all():
    import backend.schemas.projects as mod
    from backend.schemas.projects import (
        validate_benefits_realization_npv_irr_payback_and_benefit_owner_alignment,
    )

    empty = validate_benefits_realization_npv_irr_payback_and_benefit_owner_alignment(
        []
    )
    assert empty["is_valid"] is True
    assert empty["status"] == "valid"
    assert empty["cases_evaluated"] == 0
    assert (
        "validate_benefits_realization_npv_irr_payback_and_benefit_owner_alignment"
        in mod.__all__
    )


def test_validate_ccpm_buffer_fever_chart_and_feeding_buffer_erosion_green_and_yellow_valid():
    from backend.schemas.projects import (
        validate_ccpm_buffer_fever_chart_and_feeding_buffer_erosion,
    )

    res_green = validate_ccpm_buffer_fever_chart_and_feeding_buffer_erosion(
        critical_chain_completed_pct=50.0,
        project_buffer_consumed_pct=35.0,
        feeding_buffers=[
            {
                "chain_id": "FB-01",
                "feeding_chain_completed_pct": 60.0,
                "feeding_buffer_consumed_pct": 40.0,
            }
        ],
        concurrent_active_tasks_per_resource={"ENG-01": 1, "ENG-02": 1},
    )
    assert res_green["is_valid"] is True
    assert res_green["fever_chart_zone"] == "GREEN"
    assert res_green["yellow_threshold_pct"] == 50.0
    assert res_green["red_threshold_pct"] == 70.0
    assert res_green["eroded_feeding_buffers"] == []
    assert res_green["bad_multitasking_resources"] == []

    res_yellow = validate_ccpm_buffer_fever_chart_and_feeding_buffer_erosion(
        critical_chain_completed_pct=50.0,
        project_buffer_consumed_pct=60.0,
        feeding_buffers=[],
        concurrent_active_tasks_per_resource={"ENG-01": 1},
    )
    assert res_yellow["is_valid"] is True
    assert res_yellow["fever_chart_zone"] == "YELLOW"


def test_validate_ccpm_buffer_fever_chart_and_feeding_buffer_erosion_red_zone_breach():
    from backend.schemas.projects import (
        validate_ccpm_buffer_fever_chart_and_feeding_buffer_erosion,
    )

    res = validate_ccpm_buffer_fever_chart_and_feeding_buffer_erosion(
        critical_chain_completed_pct=30.0,
        project_buffer_consumed_pct=65.0,
        feeding_buffers=[],
    )
    assert res["is_valid"] is False
    assert res["fever_chart_zone"] == "RED"
    assert res["yellow_threshold_pct"] == 38.0
    assert res["red_threshold_pct"] == 58.0


def test_validate_ccpm_buffer_fever_chart_and_feeding_buffer_erosion_feeding_buffer_and_multitasking():
    from backend.schemas.projects import (
        validate_ccpm_buffer_fever_chart_and_feeding_buffer_erosion,
    )

    res = validate_ccpm_buffer_fever_chart_and_feeding_buffer_erosion(
        critical_chain_completed_pct=50.0,
        project_buffer_consumed_pct=30.0,
        feeding_buffers=[
            {
                "chain_id": "FB-CRIT-02",
                "feeding_chain_completed_pct": 20.0,
                "feeding_buffer_consumed_pct": 60.0,
            }
        ],
        concurrent_active_tasks_per_resource={"DEV-A": 1, "DEV-B": 3},
    )
    assert res["is_valid"] is False
    assert res["fever_chart_zone"] == "GREEN"
    assert res["eroded_feeding_buffers"] == ["FB-CRIT-02"]
    assert res["bad_multitasking_resources"] == ["DEV-B"]


def test_validate_ccpm_buffer_fever_chart_and_feeding_buffer_erosion_exports():
    import backend.schemas.projects as mod

    assert (
        "validate_ccpm_buffer_fever_chart_and_feeding_buffer_erosion"
        in mod.__all__
    )


def test_validate_rolling_wave_planning_horizon_decomposition_and_freeze_window_compliant():
    from backend.schemas.projects import (
        validate_rolling_wave_planning_horizon_decomposition_and_freeze_window,
    )

    res = validate_rolling_wave_planning_horizon_decomposition_and_freeze_window(
        [
            {
                "node_id": "WP-NEAR-01",
                "node_type": "WORK_PACKAGE",
                "start_offset_days": 15,
                "allocated_budget": 70000.0,
                "has_assigned_owner_and_activities": True,
                "modified_within_freeze_window": False,
            },
            {
                "node_id": "PP-FAR-02",
                "node_type": "PLANNING_PACKAGE",
                "start_offset_days": 90,
                "allocated_budget": 30000.0,
                "has_assigned_owner_and_activities": False,
                "modified_within_freeze_window": False,
            },
        ]
    )
    assert res["is_valid"] is True
    assert res["status"] == "ROLLING_WAVE_COMPLIANT"
    assert res["near_term_undecomposed_planning_package_ids"] == []
    assert res["freeze_window_churn_node_ids"] == []
    assert res["planning_package_budget_share_pct"] == 30.0
    assert res["budget_share_exceeded"] is False
    assert res["recommendations"] == []


def test_validate_rolling_wave_planning_horizon_decomposition_and_freeze_window_critical():
    from backend.schemas.projects import (
        validate_rolling_wave_planning_horizon_decomposition_and_freeze_window,
    )

    res = validate_rolling_wave_planning_horizon_decomposition_and_freeze_window(
        [
            {
                "node_id": "PP-NEAR-UNDECOMPOSED",
                "node_type": "PLANNING_PACKAGE",
                "start_offset_days": 45,
                "allocated_budget": 20000.0,
                "has_assigned_owner_and_activities": False,
            },
            {
                "node_id": "WP-NEAR-NO-OWNER",
                "node_type": "WORK_PACKAGE",
                "start_offset_days": 20,
                "allocated_budget": 80000.0,
                "has_assigned_owner_and_activities": False,
            },
        ],
        near_term_horizon_days=60,
    )
    assert res["is_valid"] is False
    assert res["status"] == "CRITICAL_NEAR_TERM_UNDECOMPOSED_BREACH"
    assert res["near_term_undecomposed_planning_package_ids"] == [
        "PP-NEAR-UNDECOMPOSED",
        "WP-NEAR-NO-OWNER",
    ]
    assert len(res["recommendations"]) >= 1


def test_validate_rolling_wave_planning_horizon_decomposition_and_freeze_window_warning():
    from backend.schemas.projects import (
        validate_rolling_wave_planning_horizon_decomposition_and_freeze_window,
    )

    res = validate_rolling_wave_planning_horizon_decomposition_and_freeze_window(
        [
            {
                "node_id": "WP-FREEZE-CHURN",
                "node_type": "WORK_PACKAGE",
                "start_offset_days": 10,
                "allocated_budget": 40000.0,
                "has_assigned_owner_and_activities": True,
                "modified_within_freeze_window": True,
            },
            {
                "node_id": "PP-FAR-HEAVY",
                "node_type": "PLANNING_PACKAGE",
                "start_offset_days": 120,
                "allocated_budget": 60000.0,
                "has_assigned_owner_and_activities": False,
                "modified_within_freeze_window": False,
            },
        ],
        freeze_window_days=30,
        max_planning_package_budget_share_pct=40.0,
    )
    assert res["is_valid"] is False
    assert res["status"] == "PLANNING_PACKAGE_SHARE_OR_FREEZE_WARNING"
    assert res["near_term_undecomposed_planning_package_ids"] == []
    assert res["freeze_window_churn_node_ids"] == ["WP-FREEZE-CHURN"]
    assert res["planning_package_budget_share_pct"] == 60.0
    assert res["budget_share_exceeded"] is True


def test_validate_rolling_wave_planning_horizon_decomposition_and_freeze_window_dunder_all():
    import backend.schemas.projects as mod
    from backend.schemas.projects import (
        validate_rolling_wave_planning_horizon_decomposition_and_freeze_window,
    )

    empty = validate_rolling_wave_planning_horizon_decomposition_and_freeze_window(
        []
    )
    assert empty["is_valid"] is True
    assert empty["status"] == "ROLLING_WAVE_COMPLIANT"
    assert empty["planning_package_budget_share_pct"] == 0.0
    assert (
        "validate_rolling_wave_planning_horizon_decomposition_and_freeze_window"
        in mod.__all__
    )


def test_validate_rbs_bowtie_barrier_redundancy_and_residual_severity_robust():
    from backend.schemas.projects import (
        validate_rbs_bowtie_barrier_redundancy_and_residual_severity,
    )

    res = validate_rbs_bowtie_barrier_redundancy_and_residual_severity(
        risk_events=[
            {
                "risk_id": "RBS-CYBER-01",
                "inherent_severity_score": 20.0,
                "active_preventive_barriers": 3,
                "active_recovery_barriers": 2,
                "common_mode_failure_spof": False,
                "residual_severity_score": 5.0,
            },
            {
                "risk_id": "RBS-SUPPLY-02",
                "inherent_severity_score": 12.0,
                "active_preventive_barriers": 1,
                "active_recovery_barriers": 1,
                "common_mode_failure_spof": False,
                "residual_severity_score": 4.0,
            },
        ]
    )
    assert res["is_valid"] is True
    assert res["total_risks"] == 2
    assert res["underprotected_bowtie_risk_ids"] == []
    assert res["spof_or_inverted_residual_risk_ids"] == []
    assert res["unacceptable_residual_risk_ids"] == []
    assert res["status"] == "BOWTIE_BARRIERS_ROBUST"


def test_validate_rbs_bowtie_barrier_redundancy_and_residual_severity_critical_deficit_and_spof():
    from backend.schemas.projects import (
        validate_rbs_bowtie_barrier_redundancy_and_residual_severity,
    )

    res = validate_rbs_bowtie_barrier_redundancy_and_residual_severity(
        risk_events=[
            {
                "risk_id": "RBS-CRIT-01",
                "inherent_severity_score": 18.0,
                "active_preventive_barriers": 1,
                "active_recovery_barriers": 2,
                "common_mode_failure_spof": True,
                "residual_severity_score": 10.0,
            }
        ]
    )
    assert res["is_valid"] is False
    assert res["underprotected_bowtie_risk_ids"] == ["RBS-CRIT-01"]
    assert res["spof_or_inverted_residual_risk_ids"] == ["RBS-CRIT-01"]
    assert res["unacceptable_residual_risk_ids"] == ["RBS-CRIT-01"]
    assert res["status"] == "CRITICAL_BOWTIE_SPOF_OR_BARRIER_DEFICIT"


def test_validate_rbs_bowtie_barrier_redundancy_and_residual_severity_residual_warning():
    from backend.schemas.projects import (
        validate_rbs_bowtie_barrier_redundancy_and_residual_severity,
    )

    res = validate_rbs_bowtie_barrier_redundancy_and_residual_severity(
        risk_events=[
            {
                "risk_id": "RBS-RES-03",
                "inherent_severity_score": 16.0,
                "active_preventive_barriers": 2,
                "active_recovery_barriers": 2,
                "common_mode_failure_spof": False,
                "residual_severity_score": 9.5,
            }
        ],
        max_acceptable_residual_score=8.0,
    )
    assert res["is_valid"] is False
    assert res["underprotected_bowtie_risk_ids"] == []
    assert res["spof_or_inverted_residual_risk_ids"] == []
    assert res["unacceptable_residual_risk_ids"] == ["RBS-RES-03"]
    assert res["status"] == "RESIDUAL_RISK_THRESHOLD_WARNING"


def test_validate_rbs_bowtie_barrier_redundancy_and_residual_severity_exports():
    import backend.schemas.projects as mod
    from backend.schemas.projects import (
        validate_rbs_bowtie_barrier_redundancy_and_residual_severity,
    )

    empty = validate_rbs_bowtie_barrier_redundancy_and_residual_severity([])
    assert empty["is_valid"] is False
    assert empty["status"] == "CRITICAL_BOWTIE_SPOF_OR_BARRIER_DEFICIT"
    assert (
        "validate_rbs_bowtie_barrier_redundancy_and_residual_severity"
        in mod.__all__
    )


def test_validate_raci_matrix_role_lists_balanced():
    from backend.schemas.projects import (
        validate_raci_matrix_single_accountable_and_role_overload,
    )

    res = validate_raci_matrix_single_accountable_and_role_overload(
        deliverables=[
            {
                "deliverable_id": "DEL-ARCH-01",
                "accountable_roles": ["Chief Architect"],
                "responsible_roles": ["Lead Backend", "SRE"],
                "consulted_roles": ["Security Officer", "DBA"],
                "informed_roles": ["PMO"],
            },
            {
                "deliverable_id": "DEL-API-02",
                "accountable_roles": ["Product Owner"],
                "responsible_roles": ["Lead Backend"],
                "consulted_roles": ["QA Lead"],
            },
        ],
        max_deliverables_per_responsible_role=5,
        max_consulted_roles_per_deliverable=4,
    )
    assert res["is_valid"] is True
    assert res["total_deliverables"] == 2
    assert res["zero_accountable_deliverables"] == []
    assert res["multiple_accountable_deliverables"] == []
    assert res["missing_responsible_deliverables"] == []
    assert res["overloaded_responsible_roles"] == []
    assert res["excessive_consulted_deliverables"] == []
    assert res["status"] == "RACI_MATRIX_BALANCED"


def test_validate_raci_matrix_role_lists_accountable_and_responsible_breach():
    from backend.schemas.projects import (
        validate_raci_matrix_single_accountable_and_role_overload,
    )

    res = validate_raci_matrix_single_accountable_and_role_overload(
        deliverables=[
            {
                "deliverable_id": "DEL-NO-A",
                "accountable_roles": [],
                "responsible_roles": ["Dev-1"],
            },
            {
                "deliverable_id": "DEL-TWO-A-NO-R",
                "accountable_roles": ["Sponsor", "PM"],
                "responsible_roles": [],
            },
        ]
    )
    assert res["is_valid"] is False
    assert res["zero_accountable_deliverables"] == ["DEL-NO-A"]
    assert res["multiple_accountable_deliverables"] == ["DEL-TWO-A-NO-R"]
    assert res["missing_responsible_deliverables"] == ["DEL-TWO-A-NO-R"]
    assert res["status"] == "CRITICAL_ACCOUNTABLE_OR_RESPONSIBLE_BREACH"


def test_validate_raci_matrix_role_lists_overload_and_consulted_bloat_warning():
    from backend.schemas.projects import (
        validate_raci_matrix_single_accountable_and_role_overload,
    )

    res = validate_raci_matrix_single_accountable_and_role_overload(
        deliverables=[
            {
                "deliverable_id": "DEL-1",
                "accountable_roles": ["PM"],
                "responsible_roles": ["Lead-Dev"],
                "consulted_roles": ["C1", "C2", "C3", "C4", "C5"],
            },
            {
                "deliverable_id": "DEL-2",
                "accountable_roles": ["PM"],
                "responsible_roles": ["Lead-Dev"],
            },
            {
                "deliverable_id": "DEL-3",
                "accountable_roles": ["PM"],
                "responsible_roles": ["Lead-Dev"],
            },
        ],
        max_deliverables_per_responsible_role=2,
        max_consulted_roles_per_deliverable=4,
    )
    assert res["is_valid"] is False
    assert res["overloaded_responsible_roles"] == ["Lead-Dev"]
    assert res["excessive_consulted_deliverables"] == ["DEL-1"]
    assert res["status"] == "ROLE_OVERLOAD_OR_CONSULTED_BLOAT_WARNING"


def test_validate_raci_matrix_role_lists_empty_and_exports():
    import backend.schemas.projects as mod
    from backend.schemas.projects import (
        validate_raci_matrix_single_accountable_and_role_overload,
    )

    empty = validate_raci_matrix_single_accountable_and_role_overload([])
    assert empty["is_valid"] is False
    assert empty["status"] == "CRITICAL_ACCOUNTABLE_OR_RESPONSIBLE_BREACH"
    assert (
        "validate_raci_matrix_single_accountable_and_role_overload"
        in mod.__all__
    )


def test_validate_contingency_and_management_reserve_emv_drawdown_sound():
    from backend.schemas.projects import (
        validate_contingency_and_management_reserve_emv_drawdown,
    )

    txs = [
        {
            "tx_id": "TX-CONT-01",
            "reserve_type": "CONTINGENCY",
            "amount": 15000.0,
            "identified_risk_id": "RISK-DB-LATENCY-04",
            "ccb_executive_sponsor_approved": False,
        },
        {
            "tx_id": "TX-MGMT-02",
            "reserve_type": "MANAGEMENT",
            "amount": 25000.0,
            "identified_risk_id": None,
            "ccb_executive_sponsor_approved": True,
        },
    ]
    res = validate_contingency_and_management_reserve_emv_drawdown(
        contingency_reserve_remaining=60000.0,
        open_risks_total_emv=45000.0,
        drawdown_transactions=txs,
        min_contingency_emv_coverage_ratio=1.0,
    )
    assert res["is_valid"] is True
    assert res["emv_coverage_ratio"] == 1.33
    assert res["contingency_underfunded"] is False
    assert res["unlinked_contingency_drawdowns"] == []
    assert res["unauthorized_management_reserve_drawdowns"] == []
    assert res["status"] == "RESERVE_GOVERNANCE_SOUND"


def test_validate_contingency_and_management_reserve_emv_drawdown_unauthorized_breach():
    from backend.schemas.projects import (
        validate_contingency_and_management_reserve_emv_drawdown,
    )

    txs = [
        {
            "tx_id": "TX-CONT-UNLINKED",
            "reserve_type": "CONTINGENCY",
            "amount": 10000.0,
            "identified_risk_id": "",
        },
        {
            "tx_id": "TX-MGMT-NO-SPONSOR",
            "reserve_type": "MANAGEMENT",
            "amount": 30000.0,
            "ccb_executive_sponsor_approved": False,
        },
    ]
    res = validate_contingency_and_management_reserve_emv_drawdown(
        contingency_reserve_remaining=50000.0,
        open_risks_total_emv=40000.0,
        drawdown_transactions=txs,
    )
    assert res["is_valid"] is False
    assert res["unlinked_contingency_drawdowns"] == ["TX-CONT-UNLINKED"]
    assert res["unauthorized_management_reserve_drawdowns"] == ["TX-MGMT-NO-SPONSOR"]
    assert res["status"] == "CRITICAL_UNAUTHORIZED_RESERVE_DRAWDOWN_BREACH"


def test_validate_contingency_and_management_reserve_emv_drawdown_underfunded_warning():
    from backend.schemas.projects import (
        validate_contingency_and_management_reserve_emv_drawdown,
    )

    res = validate_contingency_and_management_reserve_emv_drawdown(
        contingency_reserve_remaining=20000.0,
        open_risks_total_emv=50000.0,
        drawdown_transactions=[
            {
                "tx_id": "TX-CONT-OK",
                "reserve_type": "CONTINGENCY",
                "amount": 5000.0,
                "identified_risk_id": "RISK-01",
            }
        ],
        min_contingency_emv_coverage_ratio=1.0,
    )
    assert res["is_valid"] is False
    assert res["emv_coverage_ratio"] == 0.4
    assert res["contingency_underfunded"] is True
    assert res["status"] == "CONTINGENCY_EMV_COVERAGE_WARNING"


def test_validate_contingency_and_management_reserve_emv_drawdown_exports():
    import backend.schemas.projects as mod
    from backend.schemas.projects import (
        validate_contingency_and_management_reserve_emv_drawdown,
    )

    res = validate_contingency_and_management_reserve_emv_drawdown(
        contingency_reserve_remaining=10000.0,
        open_risks_total_emv=0.0,
        drawdown_transactions=[],
    )
    assert res["is_valid"] is True
    assert res["emv_coverage_ratio"] == 1.0
    assert (
        "validate_contingency_and_management_reserve_emv_drawdown"
        in mod.__all__
    )


def test_validate_monte_carlo_pert_p80_p90_and_path_convergence_bias_healthy():
    from backend.schemas.projects import (
        validate_monte_carlo_pert_p80_p90_and_path_convergence_bias,
    )

    res = validate_monte_carlo_pert_p80_p90_and_path_convergence_bias(
        [
            {
                "activity_id": "ACT-FOUNDATION-01",
                "optimistic_days": 8.0,
                "most_likely_days": 10.0,
                "pessimistic_days": 14.0,
                "deterministic_baseline_days": 10.0,
                "p80_simulated_days": 12.0,
                "p90_simulated_days": 13.0,
                "converging_predecessor_paths_count": 3,
                "merge_buffer_days": 2.5,
                "on_critical_path": True,
            },
            {
                "activity_id": "ACT-PIPING-02",
                "optimistic_days": 5.0,
                "most_likely_days": 6.0,
                "pessimistic_days": 7.0,
                "deterministic_baseline_days": 6.0,
                "p80_simulated_days": 6.5,
                "p90_simulated_days": 6.8,
                "converging_predecessor_paths_count": 1,
                "merge_buffer_days": 0.5,
                "on_critical_path": False,
            },
        ]
    )
    assert res["status"] == "HEALTHY"
    assert res["is_valid"] is True
    assert res["evaluated_activities_count"] == 2
    assert res["critical_activities"] == []
    assert res["warning_activities"] == []
    assert res["total_p80_shortfall_days"] == 0.0
    assert res["activity_evaluations"][0]["pert_mean_days"] == 10.3333
    assert res["activity_evaluations"][0]["pert_std_dev_days"] == 1.0


def test_validate_monte_carlo_pert_p80_p90_and_path_convergence_bias_critical():
    from backend.schemas.projects import (
        validate_monte_carlo_pert_p80_p90_and_path_convergence_bias,
    )

    res = validate_monte_carlo_pert_p80_p90_and_path_convergence_bias(
        [
            {
                "activity_id": "ACT-INVERTED-OMP",
                "optimistic_days": 15.0,
                "most_likely_days": 10.0,
                "pessimistic_days": 20.0,
                "deterministic_baseline_days": 12.0,
                "p80_simulated_days": 12.0,
                "p90_simulated_days": 15.0,
            },
            {
                "activity_id": "ACT-CRIT-SHORTFALL",
                "optimistic_days": 10.0,
                "most_likely_days": 12.0,
                "pessimistic_days": 20.0,
                "deterministic_baseline_days": 12.0,
                "p80_simulated_days": 16.5,
                "p90_simulated_days": 18.0,
                "converging_predecessor_paths_count": 1,
                "merge_buffer_days": 1.0,
                "on_critical_path": True,
            },
            {
                "activity_id": "ACT-UNBUFFERED-MERGE",
                "optimistic_days": 4.0,
                "most_likely_days": 5.0,
                "pessimistic_days": 6.0,
                "deterministic_baseline_days": 5.0,
                "p80_simulated_days": 5.0,
                "p90_simulated_days": 5.5,
                "converging_predecessor_paths_count": 4,
                "merge_buffer_days": 0.0,
                "on_critical_path": False,
            },
        ]
    )
    assert res["status"] == "CRITICAL"
    assert res["is_valid"] is False
    assert res["critical_activities"] == [
        "ACT-INVERTED-OMP",
        "ACT-CRIT-SHORTFALL",
        "ACT-UNBUFFERED-MERGE",
    ]
    assert res["warning_activities"] == []
    assert res["total_p80_shortfall_days"] == 3.5


def test_validate_monte_carlo_pert_p80_p90_and_path_convergence_bias_warning():
    from backend.schemas.projects import (
        validate_monte_carlo_pert_p80_p90_and_path_convergence_bias,
    )

    res = validate_monte_carlo_pert_p80_p90_and_path_convergence_bias(
        [
            {
                "activity_id": "ACT-NONCRIT-SHORTFALL",
                "optimistic_days": 5.0,
                "most_likely_days": 6.0,
                "pessimistic_days": 9.0,
                "deterministic_baseline_days": 6.0,
                "p80_simulated_days": 8.0,
                "p90_simulated_days": 8.5,
                "converging_predecessor_paths_count": 1,
                "merge_buffer_days": 0.5,
                "on_critical_path": False,
            },
            {
                "activity_id": "ACT-HIGH-CV-SKEW",
                "optimistic_days": 2.0,
                "most_likely_days": 4.0,
                "pessimistic_days": 26.0,
                "deterministic_baseline_days": 10.0,
                "p80_simulated_days": 9.5,
                "p90_simulated_days": 12.0,
                "converging_predecessor_paths_count": 1,
                "merge_buffer_days": 0.0,
                "on_critical_path": False,
            },
        ],
        max_cv_skew_ratio=0.40,
    )
    assert res["status"] == "WARNING"
    assert res["is_valid"] is False
    assert res["critical_activities"] == []
    assert res["warning_activities"] == [
        "ACT-NONCRIT-SHORTFALL",
        "ACT-HIGH-CV-SKEW",
    ]
    assert res["total_p80_shortfall_days"] == 1.5


def test_validate_monte_carlo_pert_p80_p90_and_path_convergence_bias_empty_and_exports():
    import backend.schemas.projects as mod
    from backend.schemas.projects import (
        validate_monte_carlo_pert_p80_p90_and_path_convergence_bias,
    )

    empty = validate_monte_carlo_pert_p80_p90_and_path_convergence_bias([])
    assert empty["status"] == "HEALTHY"
    assert empty["evaluated_activities_count"] == 0
    assert empty["total_p80_shortfall_days"] == 0.0
    assert (
        "validate_monte_carlo_pert_p80_p90_and_path_convergence_bias"
        in mod.__all__
    )


def test_validate_resource_leveling_and_smoothing_float_bounds_healthy():
    from backend.schemas.projects import (
        validate_resource_leveling_and_smoothing_float_bounds,
    )

    res = validate_resource_leveling_and_smoothing_float_bounds(
        [
            {
                "resource_id": "RES-CRANE-01",
                "allocated_hours": 140.0,
                "available_capacity_hours": 160.0,
                "available_total_float_days": 10.0,
                "delay_applied_days": 5.0,
                "critical_path_extended_days": 0.0,
            },
            {
                "resource_id": "RES-WELDER-02",
                "allocated_hours": 120.0,
                "available_capacity_hours": 160.0,
                "available_total_float_days": 8.0,
                "delay_applied_days": 2.0,
                "critical_path_extended_days": 0.0,
            },
        ]
    )
    assert res["status"] == "HEALTHY"
    assert res["is_valid"] is True
    assert res["evaluated_resources_count"] == 2
    assert res["critical_resources"] == []
    assert res["warning_resources"] == []
    assert res["peak_utilization_pct"] == 87.5


def test_validate_resource_leveling_and_smoothing_float_bounds_critical():
    from backend.schemas.projects import (
        validate_resource_leveling_and_smoothing_float_bounds,
    )

    res = validate_resource_leveling_and_smoothing_float_bounds(
        [
            {
                "resource_id": "RES-OVERALLOC-01",
                "allocated_hours": 180.0,
                "available_capacity_hours": 160.0,
                "available_total_float_days": 5.0,
                "delay_applied_days": 1.0,
                "critical_path_extended_days": 0.0,
            },
            {
                "resource_id": "RES-SMOOTHING-CP-SLIP",
                "allocated_hours": 130.0,
                "available_capacity_hours": 160.0,
                "available_total_float_days": 4.0,
                "delay_applied_days": 6.0,
                "critical_path_extended_days": 2.0,
            },
        ],
        smoothing_mode_only=True,
    )
    assert res["status"] == "CRITICAL"
    assert res["is_valid"] is False
    assert res["critical_resources"] == [
        "RES-OVERALLOC-01",
        "RES-SMOOTHING-CP-SLIP",
    ]
    assert res["warning_resources"] == []
    assert res["peak_utilization_pct"] == 112.5


def test_validate_resource_leveling_and_smoothing_float_bounds_warning():
    from backend.schemas.projects import (
        validate_resource_leveling_and_smoothing_float_bounds,
    )

    res = validate_resource_leveling_and_smoothing_float_bounds(
        [
            {
                "resource_id": "RES-HIGH-UTIL",
                "allocated_hours": 152.0,
                "available_capacity_hours": 160.0,
                "available_total_float_days": 10.0,
                "delay_applied_days": 3.0,
                "critical_path_extended_days": 0.0,
            },
            {
                "resource_id": "RES-LEVELING-CP-EXTENSION",
                "allocated_hours": 128.0,
                "available_capacity_hours": 160.0,
                "available_total_float_days": 5.0,
                "delay_applied_days": 5.0,
                "critical_path_extended_days": 3.0,
            },
        ],
        smoothing_mode_only=False,
    )
    assert res["status"] == "WARNING"
    assert res["is_valid"] is False
    assert res["critical_resources"] == []
    assert res["warning_resources"] == [
        "RES-HIGH-UTIL",
        "RES-LEVELING-CP-EXTENSION",
    ]
    assert res["peak_utilization_pct"] == 95.0


def test_validate_resource_leveling_and_smoothing_float_bounds_empty_and_exports():
    import backend.schemas.projects as mod
    from backend.schemas.projects import (
        validate_resource_leveling_and_smoothing_float_bounds,
    )

    empty = validate_resource_leveling_and_smoothing_float_bounds([])
    assert empty["status"] == "HEALTHY"
    assert empty["evaluated_resources_count"] == 0
    assert empty["peak_utilization_pct"] == 0.0
    assert (
        "validate_resource_leveling_and_smoothing_float_bounds"
        in mod.__all__
    )


def test_validate_agile_hybrid_wip_little_law_and_sprint_carryover_healthy():
    from backend.schemas.projects import (
        validate_agile_hybrid_wip_little_law_and_sprint_carryover,
    )

    res = validate_agile_hybrid_wip_little_law_and_sprint_carryover(
        [
            {
                "sprint_id": "SPR-2026-01",
                "active_wip_items": 6,
                "wip_limit": 8,
                "throughput_items_per_day": 1.5,
                "observed_cycle_time_days": 4.2,
                "committed_story_points": 40.0,
                "carryover_unfinished_points": 4.0,
            },
            {
                "sprint_id": "SPR-2026-02",
                "active_wip_items": 5,
                "wip_limit": 6,
                "throughput_items_per_day": 1.25,
                "observed_cycle_time_days": 3.8,
                "committed_story_points": 50.0,
                "carryover_unfinished_points": 5.0,
            },
        ]
    )
    assert res["status"] == "HEALTHY"
    assert res["is_valid"] is True
    assert res["evaluated_sprints_count"] == 2
    assert res["critical_sprints"] == []
    assert res["warning_sprints"] == []
    assert res["max_observed_carryover_pct"] == 10.0


def test_validate_agile_hybrid_wip_little_law_and_sprint_carryover_critical():
    from backend.schemas.projects import (
        validate_agile_hybrid_wip_little_law_and_sprint_carryover,
    )

    res = validate_agile_hybrid_wip_little_law_and_sprint_carryover(
        [
            {
                "sprint_id": "SPR-WIP-EXPLOSION",
                "active_wip_items": 12,
                "wip_limit": 8,
                "throughput_items_per_day": 2.0,
                "observed_cycle_time_days": 6.0,
                "committed_story_points": 40.0,
                "carryover_unfinished_points": 4.0,
            },
            {
                "sprint_id": "SPR-CARRYOVER-SURGE",
                "active_wip_items": 6,
                "wip_limit": 8,
                "throughput_items_per_day": 1.5,
                "observed_cycle_time_days": 4.0,
                "committed_story_points": 50.0,
                "carryover_unfinished_points": 20.0,
            },
        ]
    )
    assert res["status"] == "CRITICAL"
    assert res["is_valid"] is False
    assert res["critical_sprints"] == [
        "SPR-WIP-EXPLOSION",
        "SPR-CARRYOVER-SURGE",
    ]
    assert res["warning_sprints"] == []
    assert res["max_observed_carryover_pct"] == 40.0


def test_validate_agile_hybrid_wip_little_law_and_sprint_carryover_warning():
    from backend.schemas.projects import (
        validate_agile_hybrid_wip_little_law_and_sprint_carryover,
    )

    res = validate_agile_hybrid_wip_little_law_and_sprint_carryover(
        [
            {
                "sprint_id": "SPR-LITTLE-DRIFT",
                "active_wip_items": 6,
                "wip_limit": 6,
                "throughput_items_per_day": 2.0,
                "observed_cycle_time_days": 4.5,
                "committed_story_points": 40.0,
                "carryover_unfinished_points": 6.0,
            },
            {
                "sprint_id": "SPR-MILD-CARRYOVER",
                "active_wip_items": 5,
                "wip_limit": 6,
                "throughput_items_per_day": 1.0,
                "observed_cycle_time_days": 5.0,
                "committed_story_points": 40.0,
                "carryover_unfinished_points": 10.0,
            },
        ]
    )
    assert res["status"] == "WARNING"
    assert res["is_valid"] is False
    assert res["critical_sprints"] == []
    assert res["warning_sprints"] == [
        "SPR-LITTLE-DRIFT",
        "SPR-MILD-CARRYOVER",
    ]
    assert res["max_observed_carryover_pct"] == 25.0


def test_validate_agile_hybrid_wip_little_law_and_sprint_carryover_empty_and_exports():
    import backend.schemas.projects as mod
    from backend.schemas.projects import (
        validate_agile_hybrid_wip_little_law_and_sprint_carryover,
    )

    empty = validate_agile_hybrid_wip_little_law_and_sprint_carryover([])
    assert empty["status"] == "HEALTHY"
    assert empty["evaluated_sprints_count"] == 0
    assert empty["max_observed_carryover_pct"] == 0.0
    assert (
        "validate_agile_hybrid_wip_little_law_and_sprint_carryover"
        in mod.__all__
    )


def test_validate_ccpm_fever_chart_buffer_penetration_and_feeding_buffer_green():
    from backend.schemas.projects import (
        validate_ccpm_fever_chart_buffer_penetration_and_feeding_buffer,
    )

    res = validate_ccpm_fever_chart_buffer_penetration_and_feeding_buffer(
        critical_chain_completed_pct=50.0,
        project_buffer_consumed_pct=30.0,
        feeding_buffer_consumed_pct=40.0,
        resource_multitasking_index_pct=10.0,
    )
    assert res["red_zone_limit_pct"] == 66.83
    assert res["yellow_zone_limit_pct"] == 41.79
    assert res["buffer_burn_ratio"] == 0.6
    assert res["feeding_buffer_exhausted"] is False
    assert res["excessive_multitasking"] is False
    assert (
        res["fever_chart_status"]
        == "FEVER_GREEN_ZONE_FLOW_PROTECTED_CLEAN"
    )


def test_validate_ccpm_fever_chart_buffer_penetration_and_feeding_buffer_yellow():
    from backend.schemas.projects import (
        validate_ccpm_fever_chart_buffer_penetration_and_feeding_buffer,
    )

    res_pb = validate_ccpm_fever_chart_buffer_penetration_and_feeding_buffer(
        critical_chain_completed_pct=50.0,
        project_buffer_consumed_pct=50.0,
        feeding_buffer_consumed_pct=30.0,
    )
    assert (
        res_pb["fever_chart_status"]
        == "FEVER_YELLOW_ZONE_OR_MULTITASKING_CONTENTION_WARNING"
    )

    res_multi = validate_ccpm_fever_chart_buffer_penetration_and_feeding_buffer(
        critical_chain_completed_pct=50.0,
        project_buffer_consumed_pct=20.0,
        feeding_buffer_consumed_pct=80.0,
        resource_multitasking_index_pct=22.0,
    )
    assert res_multi["excessive_multitasking"] is True
    assert (
        res_multi["fever_chart_status"]
        == "FEVER_YELLOW_ZONE_OR_MULTITASKING_CONTENTION_WARNING"
    )


def test_validate_ccpm_fever_chart_buffer_penetration_and_feeding_buffer_red():
    from backend.schemas.projects import (
        validate_ccpm_fever_chart_buffer_penetration_and_feeding_buffer,
    )

    res_red = validate_ccpm_fever_chart_buffer_penetration_and_feeding_buffer(
        critical_chain_completed_pct=40.0,
        project_buffer_consumed_pct=70.0,
        feeding_buffer_consumed_pct=50.0,
    )
    assert (
        res_red["fever_chart_status"]
        == "CRITICAL_FEVER_RED_ZONE_OR_FEEDING_BUFFER_EXHAUSTED_BREACH"
    )

    res_fb = validate_ccpm_fever_chart_buffer_penetration_and_feeding_buffer(
        critical_chain_completed_pct=80.0,
        project_buffer_consumed_pct=25.0,
        feeding_buffer_consumed_pct=100.0,
    )
    assert res_fb["feeding_buffer_exhausted"] is True
    assert (
        res_fb["fever_chart_status"]
        == "CRITICAL_FEVER_RED_ZONE_OR_FEEDING_BUFFER_EXHAUSTED_BREACH"
    )


def test_validate_ccpm_fever_chart_buffer_penetration_and_feeding_buffer_coercion_and_exports():
    import backend.schemas.projects as mod
    from backend.schemas.projects import (
        validate_ccpm_fever_chart_buffer_penetration_and_feeding_buffer,
    )

    res = validate_ccpm_fever_chart_buffer_penetration_and_feeding_buffer(
        critical_chain_completed_pct=-10.0,
        project_buffer_consumed_pct="invalid",  # type: ignore[arg-type]
        feeding_buffer_consumed_pct=-5.0,
        resource_multitasking_index_pct=False,  # type: ignore[arg-type]
    )
    assert res["red_zone_limit_pct"] == 33.33
    assert res["yellow_zone_limit_pct"] == 16.66
    assert res["buffer_burn_ratio"] == 0.0
    assert res["feeding_buffer_exhausted"] is False
    assert (
        res["fever_chart_status"]
        == "FEVER_GREEN_ZONE_FLOW_PROTECTED_CLEAN"
    )
    assert (
        "validate_ccpm_fever_chart_buffer_penetration_and_feeding_buffer"
        in mod.__all__
    )


def test_validate_rolling_wave_wbs_100_percent_rule_and_planning_package_horizon_clean():
    from backend.schemas.projects import (
        validate_rolling_wave_wbs_100_percent_rule_and_planning_package_horizon,
    )

    res = validate_rolling_wave_wbs_100_percent_rule_and_planning_package_horizon(
        parent_control_account_bac=100000.0,
        child_work_packages_bac_sum=65000.0,
        child_planning_packages_bac_sum=35000.0,
        near_term_unpacked_planning_packages_count=0,
        actual_max_wp_duration_hours=60.0,
    )
    assert res["total_children_bac"] == 100000.0
    assert res["wbs_100_pct_variance_amount"] == 0.0
    assert res["wbs_100_pct_rule_violated"] is False
    assert res["planning_package_share_pct"] == 35.0
    assert res["wp_80_hour_rule_exceeded"] is False
    assert (
        res["rolling_wave_wbs_status"]
        == "ROLLING_WAVE_WBS_DECOMPOSITION_COMPLIANT_CLEAN"
    )


def test_validate_rolling_wave_wbs_100_percent_rule_and_planning_package_horizon_warning():
    from backend.schemas.projects import (
        validate_rolling_wave_wbs_100_percent_rule_and_planning_package_horizon,
    )

    res_wp = validate_rolling_wave_wbs_100_percent_rule_and_planning_package_horizon(
        parent_control_account_bac=100000.0,
        child_work_packages_bac_sum=70000.0,
        child_planning_packages_bac_sum=30000.0,
        actual_max_wp_duration_hours=120.0,
    )
    assert res_wp["wp_80_hour_rule_exceeded"] is True
    assert (
        res_wp["rolling_wave_wbs_status"]
        == "ROLLING_WAVE_WP_DURATION_OR_HIGH_PP_SHARE_WARNING"
    )

    res_pp = validate_rolling_wave_wbs_100_percent_rule_and_planning_package_horizon(
        parent_control_account_bac=100000.0,
        child_work_packages_bac_sum=25000.0,
        child_planning_packages_bac_sum=75000.0,
        actual_max_wp_duration_hours=40.0,
    )
    assert res_pp["planning_package_share_pct"] == 75.0
    assert (
        res_pp["rolling_wave_wbs_status"]
        == "ROLLING_WAVE_WP_DURATION_OR_HIGH_PP_SHARE_WARNING"
    )


def test_validate_rolling_wave_wbs_100_percent_rule_and_planning_package_horizon_critical():
    from backend.schemas.projects import (
        validate_rolling_wave_wbs_100_percent_rule_and_planning_package_horizon,
    )

    res_var = validate_rolling_wave_wbs_100_percent_rule_and_planning_package_horizon(
        parent_control_account_bac=100000.0,
        child_work_packages_bac_sum=60000.0,
        child_planning_packages_bac_sum=30000.0,
    )
    assert res_var["wbs_100_pct_variance_amount"] == 10000.0
    assert res_var["wbs_100_pct_rule_violated"] is True
    assert (
        res_var["rolling_wave_wbs_status"]
        == "CRITICAL_WBS_100_PERCENT_RULE_OR_NEAR_TERM_UNPACKED_BREACH"
    )

    res_unpacked = validate_rolling_wave_wbs_100_percent_rule_and_planning_package_horizon(
        parent_control_account_bac=100000.0,
        child_work_packages_bac_sum=70000.0,
        child_planning_packages_bac_sum=30000.0,
        near_term_unpacked_planning_packages_count=2,
    )
    assert (
        res_unpacked["rolling_wave_wbs_status"]
        == "CRITICAL_WBS_100_PERCENT_RULE_OR_NEAR_TERM_UNPACKED_BREACH"
    )


def test_validate_rolling_wave_wbs_100_percent_rule_and_planning_package_horizon_coercion_and_exports():
    import backend.schemas.projects as mod
    from backend.schemas.projects import (
        validate_rolling_wave_wbs_100_percent_rule_and_planning_package_horizon,
    )

    res = validate_rolling_wave_wbs_100_percent_rule_and_planning_package_horizon(
        parent_control_account_bac=-10.0,
        child_work_packages_bac_sum="invalid",  # type: ignore[arg-type]
        child_planning_packages_bac_sum=-5.0,
        near_term_unpacked_planning_packages_count=True,  # type: ignore[arg-type]
    )
    assert res["total_children_bac"] == 0.0
    assert res["wbs_100_pct_rule_violated"] is False
    assert (
        res["rolling_wave_wbs_status"]
        == "ROLLING_WAVE_WBS_DECOMPOSITION_COMPLIANT_CLEAN"
    )
    assert (
        "validate_rolling_wave_wbs_100_percent_rule_and_planning_package_horizon"
        in mod.__all__
    )


def test_validate_stakeholder_engagement_seam_gap_and_resistant_power_risk_clean():
    from backend.schemas.projects import (
        validate_stakeholder_engagement_seam_gap_and_resistant_power_risk,
    )

    res = validate_stakeholder_engagement_seam_gap_and_resistant_power_risk(
        high_power_resistant_count=0,
        high_power_unaware_count=0,
        desired_supportive_leading_gap_count=0,
        overdue_key_stakeholder_touchpoints_count=0,
        salience_definitive_stakeholders_unengaged_count=0,
    )
    assert res["total_high_power_at_risk"] == 0
    assert res["veto_coalition_block_risk"] is False
    assert res["seam_alignment_deficit_detected"] is False
    assert res["stakeholder_alignment_index_pct"] == 100.0
    assert res["overdue_key_stakeholder_touchpoints_count"] == 0
    assert (
        res["seam_governance_status"]
        == "STAKEHOLDER_SEAM_SUPPORTIVE_ALIGNED_CLEAN"
    )


def test_validate_stakeholder_engagement_seam_gap_and_resistant_power_risk_warning():
    from backend.schemas.projects import (
        validate_stakeholder_engagement_seam_gap_and_resistant_power_risk,
    )

    res = validate_stakeholder_engagement_seam_gap_and_resistant_power_risk(
        high_power_resistant_count=0,
        high_power_unaware_count=1,
        desired_supportive_leading_gap_count=2,
        overdue_key_stakeholder_touchpoints_count=1,
        salience_definitive_stakeholders_unengaged_count=0,
    )
    assert res["total_high_power_at_risk"] == 1
    assert res["veto_coalition_block_risk"] is False
    assert res["seam_alignment_deficit_detected"] is True
    assert res["stakeholder_alignment_index_pct"] == 63.0
    assert res["overdue_key_stakeholder_touchpoints_count"] == 1
    assert (
        res["seam_governance_status"]
        == "STAKEHOLDER_SEAM_ENGAGEMENT_GAP_OR_CADENCE_DRIFT_WARNING"
    )


def test_validate_stakeholder_engagement_seam_gap_and_resistant_power_risk_critical():
    from backend.schemas.projects import (
        validate_stakeholder_engagement_seam_gap_and_resistant_power_risk,
    )

    res_resistant = validate_stakeholder_engagement_seam_gap_and_resistant_power_risk(
        high_power_resistant_count=1,
        high_power_unaware_count=1,
        desired_supportive_leading_gap_count=1,
        overdue_key_stakeholder_touchpoints_count=2,
        salience_definitive_stakeholders_unengaged_count=0,
    )
    assert res_resistant["total_high_power_at_risk"] == 2
    assert res_resistant["veto_coalition_block_risk"] is True
    assert res_resistant["seam_alignment_deficit_detected"] is True
    assert res_resistant["stakeholder_alignment_index_pct"] == 30.0
    assert (
        res_resistant["seam_governance_status"]
        == "CRITICAL_HIGH_POWER_RESISTANT_OR_DEFINITIVE_SALIENCE_BREACH"
    )

    res_salience = validate_stakeholder_engagement_seam_gap_and_resistant_power_risk(
        high_power_resistant_count=0,
        high_power_unaware_count=0,
        salience_definitive_stakeholders_unengaged_count=4,
    )
    assert res_salience["total_high_power_at_risk"] == 4
    assert res_salience["veto_coalition_block_risk"] is True
    assert res_salience["stakeholder_alignment_index_pct"] == 0.0
    assert (
        res_salience["seam_governance_status"]
        == "CRITICAL_HIGH_POWER_RESISTANT_OR_DEFINITIVE_SALIENCE_BREACH"
    )


def test_validate_stakeholder_engagement_seam_gap_and_resistant_power_risk_coercion_and_exports():
    import backend.schemas.projects as mod
    from backend.schemas.projects import (
        validate_stakeholder_engagement_seam_gap_and_resistant_power_risk,
    )

    res = validate_stakeholder_engagement_seam_gap_and_resistant_power_risk(
        high_power_resistant_count=True,  # type: ignore[arg-type]
        high_power_unaware_count=-3,
        desired_supportive_leading_gap_count="invalid",  # type: ignore[arg-type]
        overdue_key_stakeholder_touchpoints_count=False,  # type: ignore[arg-type]
        salience_definitive_stakeholders_unengaged_count=-2,
    )
    assert res["total_high_power_at_risk"] == 0
    assert res["veto_coalition_block_risk"] is False
    assert res["seam_alignment_deficit_detected"] is False
    assert res["stakeholder_alignment_index_pct"] == 100.0
    assert res["overdue_key_stakeholder_touchpoints_count"] == 0
    assert (
        res["seam_governance_status"]
        == "STAKEHOLDER_SEAM_SUPPORTIVE_ALIGNED_CLEAN"
    )
    assert (
        "validate_stakeholder_engagement_seam_gap_and_resistant_power_risk"
        in mod.__all__
    )
