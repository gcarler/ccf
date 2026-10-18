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
