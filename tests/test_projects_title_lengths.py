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



