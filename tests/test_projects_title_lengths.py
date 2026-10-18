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
