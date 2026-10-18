from __future__ import annotations

import uuid

from backend import models
from backend.services import project_evm_service, project_lifecycle_pmi_service
from tests.conftest import auth_headers, seed_admin


def _project(db_session, sede_id):
    project = models.Project(id=uuid.uuid4(), title="PMI lifecycle test", sede_id=sede_id)
    db_session.add(project)
    db_session.commit()
    return project


def test_charter_authorization_and_closure_finalize(client, db_session):
    user, persona, sede = seed_admin(db_session, email="pmi-lifecycle@example.com")
    headers = auth_headers(client, email="pmi-lifecycle@example.com")
    project = _project(db_session, sede.id)

    initial = client.get(f"/api/projects/{project.id}/charter", headers=headers)
    assert initial.status_code == 200, initial.text
    assert initial.json()["charter_status"] == "draft"
    assert initial.json()["development_approach"] == "hybrid"
    assert initial.json()["pmo_type"] == "controlling"

    charter = client.put(
        f"/api/projects/{project.id}/charter",
        headers=headers,
        json={
            "sponsor_id": str(persona.id),
            "business_case": "Mejorar coordinación",
            "strategic_justification": "Alineado al plan ministerial",
            "measurable_objectives": ["Reducir tiempos"],
            "key_assumptions": ["Disponibilidad de voluntarios"],
            "key_constraints": ["Presupuesto anual"],
            "high_level_risks": ["Rotación de equipo"],
            "preliminary_budget": 1000,
            "development_approach": "predictive",
            "pmo_type": "directive",
            "charter_status": "authorized",
            "authorized_by": str(uuid.uuid4()),
        },
    )
    assert charter.status_code == 200, charter.text
    assert charter.json()["authorized_by"] == str(persona.id)
    assert charter.json()["authorized_at"] is not None
    assert charter.json()["development_approach"] == "predictive"
    assert charter.json()["pmo_type"] == "directive"

    downgrade = client.put(
        f"/api/projects/{project.id}/charter",
        headers=headers,
        json={"charter_status": "draft"},
    )
    assert downgrade.status_code == 409

    initial_closure = client.get(f"/api/projects/{project.id}/closure", headers=headers)
    assert initial_closure.status_code == 200
    assert initial_closure.json()["closure_status"] == "open"
    finalized = client.post(
        f"/api/projects/{project.id}/closure/finalize",
        headers=headers,
        json={
            "deliverables_accepted_verified": True,
            "financial_reconciliation_completed": True,
            "final_bac": 1000,
            "final_ac": 850,
            "operational_handover_to": "Ministerio de Servicio",
            "lessons_learned": [
                {
                    "category": "comunicación",
                    "what_worked": "Reuniones semanales",
                    "what_failed": "Avisos tardíos",
                    "recommendation": "Definir calendario al inicio",
                }
            ],
            "closed_by": str(uuid.uuid4()),
        },
    )
    assert finalized.status_code == 200, finalized.text
    assert finalized.json()["closure_status"] == "closed"
    assert finalized.json()["closed_by"] == str(persona.id)
    assert finalized.json()["final_variance"] == 150
    assert finalized.json()["lessons_learned"][0]["category"] == "comunicación"
    assert finalized.json()["wiki_synced"] is False


def test_stakeholder_quadrants_patch_and_soft_delete(client, db_session):
    _, _, sede = seed_admin(db_session, email="pmi-stakeholder@example.com")
    headers = auth_headers(client, email="pmi-stakeholder@example.com")
    project = _project(db_session, sede.id)

    created = client.post(
        f"/api/projects/{project.id}/stakeholders",
        headers=headers,
        json={
            "display_name": "Líder de sede",
            "role_title": "Sponsor",
            "organization_or_ministry": "Operaciones",
            "power_level": 5,
            "interest_level": 2,
            "engagement_level": "supportive",
            "management_strategy": "Mantener satisfecho",
        },
    )
    assert created.status_code == 201, created.text
    stakeholder_id = created.json()["id"]
    assert created.json()["quadrant"] == "keep_satisfied"

    patched = client.patch(
        f"/api/projects/{project.id}/stakeholders/{stakeholder_id}",
        headers=headers,
        json={"interest_level": 4},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["quadrant"] == "manage_closely"

    deleted = client.delete(f"/api/projects/{project.id}/stakeholders/{stakeholder_id}", headers=headers)
    assert deleted.status_code == 204
    assert client.get(f"/api/projects/{project.id}/stakeholders", headers=headers).json() == []


def test_project_lifecycle_respects_sede_scope(client, db_session):
    _, _, sede_a = seed_admin(db_session, email="pmi-sede-a@example.com")
    headers_a = auth_headers(client, email="pmi-sede-a@example.com")
    project = _project(db_session, sede_a.id)

    _, _, sede_b = seed_admin(db_session, email="pmi-sede-b@example.com")
    # The second seeded account authenticates on the same client but obtains its own token.
    headers_b = auth_headers(client, email="pmi-sede-b@example.com")
    assert sede_a.id != sede_b.id
    for path in ("charter", "stakeholders", "closure"):
        response = client.get(f"/api/projects/{project.id}/{path}", headers=headers_b)
        assert response.status_code == 404, response.text


def test_pmo_portfolio_matrix_classifies_quadrants_and_isolates_sede(client, db_session, monkeypatch):
    _, _, sede_a = seed_admin(db_session, email="pmo-portfolio-a@example.com")
    headers_a = auth_headers(client, email="pmo-portfolio-a@example.com")
    expected_metrics = {
        "Portfolio Optimal": {"bac": 1000, "ev": 900, "ac": 900, "pv": 900, "cpi": 1.0, "spi": 1.0, "progress_percentage": 90},
        "Portfolio Cost Acceleration": {"bac": 2000, "ev": 800, "ac": 1000, "pv": 700, "cpi": 0.8, "spi": 1.14, "progress_percentage": 40},
        "Portfolio Underutilized": {"bac": 3000, "ev": 1100, "ac": 1000, "pv": 1300, "cpi": 1.1, "spi": 0.85, "progress_percentage": 36},
        "Portfolio Critical": {"bac": 4000, "ev": 800, "ac": 1000, "pv": 1100, "cpi": 0.8, "spi": 0.73, "progress_percentage": 20},
    }
    local_projects = []
    for title in expected_metrics:
        project = models.Project(id=uuid.uuid4(), title=title, sede_id=sede_a.id, status="active")
        local_projects.append(project)
        db_session.add(project)
    db_session.add(models.ProjectLifecycle(
        project_id=local_projects[0].id,
        development_approach="agile",
        pmo_type="supportive",
        charter_status="authorized",
    ))

    _, _, sede_b = seed_admin(db_session, email="pmo-portfolio-b@example.com")
    headers_b = auth_headers(client, email="pmo-portfolio-b@example.com")
    outside_project = models.Project(
        id=uuid.uuid4(), title="Sede B confidential project", sede_id=sede_b.id, status="active"
    )
    db_session.add(outside_project)
    db_session.commit()

    monkeypatch.setattr(
        project_evm_service,
        "calculate_project_evm",
        lambda _db, project: expected_metrics.get(
            project.title,
            {"bac": 9000, "ev": 9000, "ac": 1, "pv": 1, "cpi": 9000, "spi": 9000, "progress_percentage": 100},
        ),
    )

    response = client.get("/api/projects/pmo-portfolio-matrix", headers=headers_a)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["portfolio_totals"]["total_projects"] == 4
    assert payload["portfolio_totals"]["total_bac"] == 10000
    assert payload["quadrants_distribution"] == {
        "q1_optimal": 1,
        "q2_cost_acceleration": 1,
        "q3_underutilized_capacity": 1,
        "q4_critical_emergency": 1,
    }
    matrix_by_title = {project["title"]: project for project in payload["projects_matrix"]}
    assert "Sede B confidential project" not in matrix_by_title
    assert matrix_by_title["Portfolio Optimal"]["development_approach"] == "agile"
    assert matrix_by_title["Portfolio Optimal"]["pmo_type"] == "supportive"
    assert matrix_by_title["Portfolio Optimal"]["charter_status"] == "authorized"
    assert matrix_by_title["Portfolio Critical"]["quadrant"] == "q4_critical_emergency"

    response_b = client.get("/api/projects/pmo-portfolio-matrix", headers=headers_b)
    assert response_b.status_code == 200, response_b.text
    assert [project["title"] for project in response_b.json()["projects_matrix"]] == [outside_project.title]


def test_compute_closure_readiness_and_governance_maturity_pure_helpers():
    assert project_lifecycle_pmi_service.compute_closure_readiness_pct(
        deliverables_accepted_verified=False,
        financial_reconciliation_completed=False,
        lessons_learned_count=0,
        closure_status="open",
    ) == 0.0
    assert project_lifecycle_pmi_service.compute_closure_readiness_pct(
        deliverables_accepted_verified=True,
        financial_reconciliation_completed=False,
        lessons_learned_count=0,
        closure_status="open",
    ) == 40.0
    assert project_lifecycle_pmi_service.compute_closure_readiness_pct(
        deliverables_accepted_verified=True,
        financial_reconciliation_completed=False,
        lessons_learned_count=2,
        closure_status="open",
    ) == 60.0
    assert project_lifecycle_pmi_service.compute_closure_readiness_pct(
        deliverables_accepted_verified=True,
        financial_reconciliation_completed=True,
        lessons_learned_count=0,
        closure_status="open",
    ) == 80.0
    assert project_lifecycle_pmi_service.compute_closure_readiness_pct(
        deliverables_accepted_verified=False,
        financial_reconciliation_completed=False,
        lessons_learned_count=0,
        closure_status="closed",
    ) == 100.0

    assert project_lifecycle_pmi_service.compute_governance_maturity_pct(
        charter_status="draft",
        measurable_objectives_count=0,
        stakeholders_total=0,
        closure_readiness_pct=0.0,
    ) == 0.0
    assert project_lifecycle_pmi_service.compute_governance_maturity_pct(
        charter_status="authorized",
        measurable_objectives_count=2,
        stakeholders_total=3,
        closure_readiness_pct=100.0,
    ) == 100.0


def test_evaluate_governance_health_lifecycle_progression(client, db_session):
    _, persona, sede = seed_admin(db_session, email="pmi-governance-health@example.com")
    headers = auth_headers(client, email="pmi-governance-health@example.com")
    project = _project(db_session, sede.id)

    initial_summary = project_lifecycle_pmi_service.build_governance_summary(db_session, project.id)
    initial_health = project_lifecycle_pmi_service.evaluate_governance_health(initial_summary)
    assert initial_health == {
        "closure_readiness_pct": 0.0,
        "governance_maturity_pct": 0.0,
        "maturity_tier": "initial",
    }

    charter_res = client.put(
        f"/api/projects/{project.id}/charter",
        headers=headers,
        json={
            "sponsor_id": str(persona.id),
            "business_case": "Fortalecer trazabilidad ministerial",
            "strategic_justification": "Gobernanza PMI estándar",
            "measurable_objectives": ["Cumplir cronograma al 95%"],
            "charter_status": "authorized",
        },
    )
    assert charter_res.status_code == 200, charter_res.text

    managed_summary = project_lifecycle_pmi_service.build_governance_summary(db_session, project.id)
    managed_health = project_lifecycle_pmi_service.evaluate_governance_health(managed_summary)
    assert managed_health["governance_maturity_pct"] == 60.0
    assert managed_health["maturity_tier"] == "managed"

    stakeholder_res = client.post(
        f"/api/projects/{project.id}/stakeholders",
        headers=headers,
        json={
            "display_name": "Coordinador General",
            "role_title": "Sponsor",
            "power_level": 5,
            "interest_level": 5,
            "engagement_level": "leading",
        },
    )
    assert stakeholder_res.status_code == 201, stakeholder_res.text

    closure_res = client.post(
        f"/api/projects/{project.id}/closure/finalize",
        headers=headers,
        json={
            "deliverables_accepted_verified": True,
            "financial_reconciliation_completed": True,
            "final_bac": 2000,
            "final_ac": 1950,
            "lessons_learned": [
                {
                    "category": "alcance",
                    "what_worked": "Desglose WBS temprano",
                    "what_failed": "Cambios menores sin comité",
                    "recommendation": "Formalizar control de cambios",
                }
            ],
        },
    )
    assert closure_res.status_code == 200, closure_res.text

    final_summary = project_lifecycle_pmi_service.build_governance_summary(db_session, project.id)
    final_health = project_lifecycle_pmi_service.evaluate_governance_health(final_summary)
    assert final_health == {
        "closure_readiness_pct": 100.0,
        "governance_maturity_pct": 100.0,
        "maturity_tier": "optimized",
    }


# ── evaluate_stakeholder_engagement_gaps (PMBOK §13.2.2.5, pure helper) ─────


def test_stakeholder_engagement_gaps_aligned_portfolio():
    """Interesados al nivel deseado (o superior) → 'aligned' con 100%."""
    stakeholders = [
        {"current_engagement": "supportive", "desired_engagement": "supportive", "power_level": "high"},
        {"engagement_level": "leading", "target_engagement": "supportive", "power": 2},
        {"current_engagement": "neutral", "desired_engagement": "neutral", "power_level": "low"},
    ]
    result = project_lifecycle_pmi_service.evaluate_stakeholder_engagement_gaps(stakeholders)

    assert result == {
        "total_stakeholders": 3,
        "high_power_count": 1,
        "engagement_gap_count": 0,
        "critical_resistant_count": 0,
        "alignment_pct": 100.0,
        "engagement_health": "aligned",
    }


def test_stakeholder_engagement_gaps_critical_resistance():
    """Alto poder en 'unaware' o 'resistant' → 'critical_resistance' (prioriza sobre aligned)."""
    stakeholders = [
        {"current_engagement": "unaware", "desired_engagement": "supportive", "power_level": "high"},
        {"current_engagement": "resistant", "desired_engagement": "supportive", "power": 5},
        {"current_engagement": "supportive", "desired_engagement": "supportive", "power_level": "low"},
    ]
    result = project_lifecycle_pmi_service.evaluate_stakeholder_engagement_gaps(stakeholders)

    assert result["total_stakeholders"] == 3
    assert result["high_power_count"] == 2
    assert result["engagement_gap_count"] == 2
    assert result["critical_resistant_count"] == 2
    # 1 de 3 alineado → 33.33 px
    assert result["alignment_pct"] == 33.33
    assert result["engagement_health"] == "critical_resistance"


def test_stakeholder_engagement_gaps_needs_outreach():
    """Brechas moderadas sin resistencia crítica y < 80% alineado → 'needs_outreach'."""
    stakeholders = [
        {"current_engagement": "neutral", "desired_engagement": "supportive", "power_level": "low"},
        {"current_engagement": "neutral", "desired_engagement": "supportive", "power_level": "low"},
        {"current_engagement": "unaware", "desired_engagement": "supportive", "power_level": "low"},
    ]
    result = project_lifecycle_pmi_service.evaluate_stakeholder_engagement_gaps(stakeholders)

    assert result == {
        "total_stakeholders": 3,
        "high_power_count": 0,
        "engagement_gap_count": 3,
        "critical_resistant_count": 0,
        "alignment_pct": 0.0,
        "engagement_health": "needs_outreach",
    }
    # Caso borde 80% exacto sin brechas críticas → 'aligned'
    borderline = [
        {"current_engagement": "supportive", "desired_engagement": "supportive", "power_level": "low"},
        {"current_engagement": "neutral", "desired_engagement": "supportive", "power_level": "low"},
        {"current_engagement": "supportive", "desired_engagement": "supportive", "power_level": 3},  # poder 3 < 4, no es high
        {"current_engagement": "leading", "desired_engagement": "supportive", "power_level": "low"},
        {"current_engagement": "supportive", "desired_engagement": "supportive", "power_level": "low"},
    ]
    result_80 = project_lifecycle_pmi_service.evaluate_stakeholder_engagement_gaps(borderline)
    assert result_80["alignment_pct"] == 80.0
    assert result_80["engagement_health"] == "aligned"


def test_stakeholder_engagement_gaps_unmapped_status():
    """None y [] → 'unmapped' con alignment_pct 100.0."""
    result = project_lifecycle_pmi_service.evaluate_stakeholder_engagement_gaps(None)
    assert result["total_stakeholders"] == 0
    assert result["alignment_pct"] == 100.0
    assert result["engagement_health"] == "unmapped"

    result_empty = project_lifecycle_pmi_service.evaluate_stakeholder_engagement_gaps([])
    assert result_empty["total_stakeholders"] == 0
    assert result_empty["alignment_pct"] == 100.0
    assert result_empty["engagement_health"] == "unmapped"


def test_stakeholder_engagement_gaps_defaults_and_class_facade():
    """Defaults: actual 'neutral', deseado 'supportive'; el facade expone la misma función."""
    stakeholders = [{"power_level": "medium"}]
    result = project_lifecycle_pmi_service.evaluate_stakeholder_engagement_gaps(stakeholders)
    assert result == {
        "total_stakeholders": 1,
        "high_power_count": 0,
        "engagement_gap_count": 1,
        "critical_resistant_count": 0,
        "alignment_pct": 0.0,
        "engagement_health": "needs_outreach",
    }

    facade = project_lifecycle_pmi_service.ProjectLifecyclePMIService.evaluate_stakeholder_engagement_gaps(stakeholders)
    assert facade == result
    assert callable(
        project_lifecycle_pmi_service.evaluate_stakeholder_engagement_gaps
    )


def test_charter_authorization_readiness_authorized_complete():
    """5/5 pilares cumplidos con autorización formal → 'authorized_complete' y 100.0%."""
    charter = {
        "business_case": "Optimización de infraestructura pastoral y administrativa",
        "measurable_objectives": ["Reducir costos operativos 15%", "Certificar 100% de entregables DoD"],
        "high_level_risks": ["Retraso de suministros importados"],
        "sponsor_id": "11111111-2222-3333-4444-555555555555",
        "charter_status": "authorized",
    }
    res = project_lifecycle_pmi_service.evaluate_charter_authorization_readiness(charter)
    assert res == {
        "has_business_case": True,
        "has_measurable_objectives": True,
        "has_high_level_risks_or_assumptions": True,
        "has_assigned_sponsor": True,
        "is_formally_authorized": True,
        "pillars_satisfied_count": 5,
        "readiness_score_pct": 100.0,
        "charter_gate_verdict": "authorized_complete",
    }


def test_charter_authorization_readiness_premature_authorization():
    """Autorizado formalmente pero sin caso de negocio ni objetivos medibles → 'premature_authorization'."""
    charter = {
        "business_case": "   ",
        "measurable_objectives": [],
        "high_level_risks": "Riesgo regulatorio menor",
        "sponsor_name": "Director General PMO",
        "status": "approved",
    }
    res = project_lifecycle_pmi_service.ProjectLifecyclePMIService.evaluate_charter_authorization_readiness(charter)
    assert res["is_formally_authorized"] is True
    assert res["has_business_case"] is False
    assert res["has_measurable_objectives"] is False
    assert res["pillars_satisfied_count"] == 3
    assert res["readiness_score_pct"] == 60.0
    assert res["charter_gate_verdict"] == "premature_authorization"


def test_charter_authorization_readiness_ready_for_signoff():
    """4/5 pilares técnicos completos en estado draft/under_review → 'ready_for_signoff' y 80.0%."""
    charter = {
        "business_case": "Caso de negocio validado por comité financiero",
        "measurable_objectives": ["Meta trimestral Q4"],
        "assumptions_and_constraints": "Presupuesto tope $120,000 USD",
        "sponsor_id": "aaaa1111-bbbb-2222-cccc-333344445555",
        "charter_status": "under_review",
    }
    res = project_lifecycle_pmi_service.evaluate_charter_authorization_readiness(charter)
    assert res["is_formally_authorized"] is False
    assert res["pillars_satisfied_count"] == 4
    assert res["readiness_score_pct"] == 80.0
    assert res["charter_gate_verdict"] == "ready_for_signoff"


def test_charter_authorization_readiness_draft_incomplete():
    """Diccionario vacío o None → 0 pilares, 0.0% y 'draft_incomplete'."""
    for empty_val in (None, {}, {"charter_status": "draft", "measurable_objectives": [""]}):
        res = project_lifecycle_pmi_service.evaluate_charter_authorization_readiness(empty_val)
        assert res == {
            "has_business_case": False,
            "has_measurable_objectives": False,
            "has_high_level_risks_or_assumptions": False,
            "has_assigned_sponsor": False,
            "is_formally_authorized": False,
            "pillars_satisfied_count": 0,
            "readiness_score_pct": 0.0,
            "charter_gate_verdict": "draft_incomplete",
        }


# ── evaluate_administrative_closure_audit (PMI PMBOK §4.7) ────────────────────


def test_evaluate_administrative_closure_audit_ready_for_archive():
    """Los 5 pilares de cierre completos → 100%, can_archive_project=True y 'ready_for_archive'."""
    payload = {
        "deliverables_accepted_verified": True,
        "financial_reconciliation_completed": True,
        "procurement_contracts_closed": True,
        "team_resources_released": True,
        "lessons_learned": [{"summary": "Early stakeholder alignment prevented scope creep"}],
        "final_report_summary": "Project completed on schedule and within BAC.",
    }
    res = project_lifecycle_pmi_service.evaluate_administrative_closure_audit(payload)
    assert res == {
        "completed_pillars_count": 5,
        "closure_index_pct": 100.0,
        "lessons_learned_count": 1,
        "missing_pillars": [],
        "can_archive_project": True,
        "closure_verdict": "ready_for_archive",
    }
    assert (
        project_lifecycle_pmi_service.ProjectLifecyclePMIService.evaluate_administrative_closure_audit(
            payload
        )
        == res
    )


def test_evaluate_administrative_closure_audit_pending_signoff():
    """Entregables y finanzas cerrados pero recursos no liberados → 'pending_SignOff'."""
    payload = {
        "deliverables_accepted_verified": True,
        "financial_reconciliation_completed": True,
        "procurement_contracts_closed": True,
        "team_resources_released": False,
        "lessons_learned": [{"lesson": "Automated gates reduced regression incidents"}],
        "final_report_summary": "All deliverables verified and accepted by sponsor.",
    }
    res = project_lifecycle_pmi_service.evaluate_administrative_closure_audit(payload)
    assert res["completed_pillars_count"] == 4
    assert res["closure_index_pct"] == 80.0
    assert "resource_release" in res["missing_pillars"]
    assert res["can_archive_project"] is False
    assert res["closure_verdict"] == "pending_SignOff"


def test_evaluate_administrative_closure_audit_blocked_open_obligations():
    """Entregables o finanzas pendientes → 'blocked_open_obligations'."""
    payload = {
        "deliverables_accepted_verified": True,
        "financial_reconciliation_completed": False,
        "procurement_contracts_closed": False,
        "team_resources_released": True,
        "lessons_learned_count": 2,
        "final_report_summary": "Pending vendor invoice reconciliation before final archive.",
    }
    res = project_lifecycle_pmi_service.evaluate_administrative_closure_audit(payload)
    assert res["completed_pillars_count"] == 3
    assert res["closure_index_pct"] == 60.0
    assert res["missing_pillars"] == ["financial_reconciliation", "contractual_closure"]
    assert res["can_archive_project"] is False
    assert res["closure_verdict"] == "blocked_open_obligations"


def test_evaluate_administrative_closure_audit_empty_or_none():
    """None o {} → solo contractual_closure por defecto (1/5 = 20.0%) y 'blocked_open_obligations'."""
    for empty_val in (None, {}):
        res = project_lifecycle_pmi_service.evaluate_administrative_closure_audit(empty_val)
        assert res == {
            "completed_pillars_count": 1,
            "closure_index_pct": 20.0,
            "lessons_learned_count": 0,
            "missing_pillars": [
                "deliverables_acceptance",
                "financial_reconciliation",
                "resource_release",
                "lessons_learned_repository",
            ],
            "can_archive_project": False,
            "closure_verdict": "blocked_open_obligations",
        }


# ── evaluate_pmo_portfolio_health_balance (PMI PMBOK §1.2.3.3) ────────────────


def test_evaluate_pmo_portfolio_health_balance_balanced_healthy():
    """Proyectos con CPI >= 0.95 y SPI >= 0.95 -> 'balanced_healthy' y budget_at_risk_pct=0.0."""
    projects = [
        {"bac": 50000.0, "cpi": 1.05, "spi": 1.00},
        {"budget": 30000.0, "cpi": 0.98, "spi": 0.97},
        {"bac": 20000.0, "cpi": 0.92, "spi": 0.98},
    ]
    res = project_lifecycle_pmi_service.evaluate_pmo_portfolio_health_balance(projects)
    assert res == {
        "total_projects": 3,
        "healthy_projects_count": 2,
        "watchlist_projects_count": 1,
        "critical_projects_count": 0,
        "total_portfolio_bac": 100000.0,
        "budget_at_risk_bac": 0.0,
        "budget_at_risk_pct": 0.0,
        "portfolio_status": "balanced_healthy",
    }
    assert (
        project_lifecycle_pmi_service.ProjectLifecyclePMIService.evaluate_pmo_portfolio_health_balance(
            projects
        )
        == res
    )


def test_evaluate_pmo_portfolio_health_balance_elevated_exposure():
    """1 proyecto crítico con 10% del BAC (< 30%) y 3 proyectos sanos -> 'elevated_exposure'."""
    projects = [
        {"bac": 10000.0, "cpi": 0.78, "spi": 0.95},
        {"bac": 30000.0, "cpi": 1.02, "spi": 1.01},
        {"bac": 30000.0, "cpi": 1.00, "spi": 0.99},
        {"bac": 30000.0, "cpi": 1.04, "spi": 1.02},
    ]
    res = project_lifecycle_pmi_service.evaluate_pmo_portfolio_health_balance(projects)
    assert res["total_projects"] == 4
    assert res["healthy_projects_count"] == 3
    assert res["critical_projects_count"] == 1
    assert res["budget_at_risk_bac"] == 10000.0
    assert res["budget_at_risk_pct"] == 10.0
    assert res["portfolio_status"] == "elevated_exposure"


def test_evaluate_pmo_portfolio_health_balance_systemic_distress():
    """Proyecto crítico concentra >= 30% del BAC del portafolio -> 'systemic_distress'."""
    projects = [
        {"bac": 45000.0, "cpi": 0.96, "spi": 0.96, "health_status": "critical"},
        {"bac": 55000.0, "cpi": 1.05, "spi": 1.02},
    ]
    res = project_lifecycle_pmi_service.evaluate_pmo_portfolio_health_balance(projects)
    assert res["critical_projects_count"] == 1
    assert res["budget_at_risk_pct"] == 45.0
    assert res["portfolio_status"] == "systemic_distress"


def test_evaluate_pmo_portfolio_health_balance_empty_or_none():
    """None o [] -> 'empty_portfolio' y total_projects=0."""
    for empty_val in (None, []):
        res = project_lifecycle_pmi_service.evaluate_pmo_portfolio_health_balance(empty_val)
        assert res == {
            "total_projects": 0,
            "healthy_projects_count": 0,
            "watchlist_projects_count": 0,
            "critical_projects_count": 0,
            "total_portfolio_bac": 0.0,
            "budget_at_risk_bac": 0.0,
            "budget_at_risk_pct": 0.0,
            "portfolio_status": "empty_portfolio",
        }


def test_evaluate_phase_gate_transition_readiness_proceed():
    """Fase con 100% de paquetes completados, 0 riesgos críticos, 0 CCB y criterios verificados -> proceed_to_next_phase."""
    res = project_lifecycle_pmi_service.evaluate_phase_gate_transition_readiness(
        phase_tasks_total=10,
        phase_tasks_completed=10,
        open_critical_risks=0,
        pending_ccb_changes=0,
        exit_criteria_verified=True,
    )
    assert res == {
        "phase_tasks_total": 10,
        "phase_tasks_completed": 10,
        "completion_pct": 100.0,
        "open_critical_risks": 0,
        "pending_ccb_changes": 0,
        "exit_criteria_verified": True,
        "gate_blockers": [],
        "can_transition_cleanly": True,
        "gate_decision": "proceed_to_next_phase",
    }
    assert (
        project_lifecycle_pmi_service.ProjectLifecyclePMIService.evaluate_phase_gate_transition_readiness(
            10, 10, 0, 0, True
        )
        == res
    )


def test_evaluate_phase_gate_transition_readiness_conditional_proceed():
    """Fase con >= 90% de avance, 0 riesgos críticos y <= 1 CCB pendiente -> conditional_proceed_with_action_plan."""
    res = project_lifecycle_pmi_service.evaluate_phase_gate_transition_readiness(
        phase_tasks_total=20,
        phase_tasks_completed=19,
        open_critical_risks=0,
        pending_ccb_changes=1,
        exit_criteria_verified=False,
    )
    assert res["completion_pct"] == 95.0
    assert res["can_transition_cleanly"] is False
    assert res["gate_blockers"] == [
        "incomplete_work_packages",
        "pending_ccb_decisions",
        "unverified_exit_criteria",
    ]
    assert res["gate_decision"] == "conditional_proceed_with_action_plan"


def test_evaluate_phase_gate_transition_readiness_hold_by_critical_risk_or_low_completion():
    """Bloqueo por riesgo crítico abierto o baja completitud (< 90%) -> hold_at_current_phase."""
    by_risk = project_lifecycle_pmi_service.evaluate_phase_gate_transition_readiness(
        phase_tasks_total=10,
        phase_tasks_completed=10,
        open_critical_risks=1,
        pending_ccb_changes=0,
        exit_criteria_verified=True,
    )
    assert "open_critical_risks" in by_risk["gate_blockers"]
    assert by_risk["can_transition_cleanly"] is False
    assert by_risk["gate_decision"] == "hold_at_current_phase"

    by_low_completion = (
        project_lifecycle_pmi_service.evaluate_phase_gate_transition_readiness(
            phase_tasks_total=10,
            phase_tasks_completed=6,
            open_critical_risks=0,
            pending_ccb_changes=0,
            exit_criteria_verified=True,
        )
    )
    assert by_low_completion["completion_pct"] == 60.0
    assert "incomplete_work_packages" in by_low_completion["gate_blockers"]
    assert by_low_completion["gate_decision"] == "hold_at_current_phase"


def test_evaluate_phase_gate_transition_readiness_empty_phase():
    """Fase sin alcance (total=0) -> empty_phase_scope y hold_at_current_phase."""
    res = project_lifecycle_pmi_service.evaluate_phase_gate_transition_readiness(
        phase_tasks_total=0,
        phase_tasks_completed=0,
        open_critical_risks=0,
        pending_ccb_changes=0,
        exit_criteria_verified=True,
    )
    assert res["phase_tasks_total"] == 0
    assert res["completion_pct"] == 0.0
    assert "empty_phase_scope" in res["gate_blockers"]
    assert res["can_transition_cleanly"] is False
    assert res["gate_decision"] == "hold_at_current_phase"


# ─── evaluate_lessons_learned_institutional_reuse (pure helper) ────────────


def test_lessons_learned_reuse_institutionalized_opa_learning():
    """Lecciones accionables >= 75% y reuso OPA >= 50% -> INSTITUTIONALIZED_OPA_LEARNING."""
    lessons = [
        {
            "action_item": "Estandarizar el cierre con checklist OPA",
            "category": "Integration Management",
            "reused": True,
        },
        {
            "recommendation": "Automatizar la conciliación financiera mensual",
            "knowledge_area": "Cost Management",
            "applied_to_opa": True,
        },
        {"action_item": "Validar calendario con stakeholders antes", "category": "Comms"},
    ]

    res = project_lifecycle_pmi_service.evaluate_lessons_learned_institutional_reuse(
        lessons
    )

    assert res["total_lessons"] == 3
    assert res["actionable_count"] == 3
    assert res["categorized_count"] == 3
    assert res["reused_or_applied_count"] == 2
    assert res["actionability_rate"] == 100.0
    assert res["opa_reuse_rate"] == 66.67
    assert res["posture"] == "INSTITUTIONALIZED_OPA_LEARNING"


def test_lessons_learned_reuse_passive_archive():
    """Accionables >= 50% pero reuso OPA < 50% -> PASSIVE_ARCHIVE."""
    lessons = [
        {"action_item": "Documentar el proceso de cierre definitivo"},
        {"action_item": "Revisar métricas EVM antes del corte"},
        {"description": "Retrospectiva sin acción concretadifusa"},
    ]

    res = project_lifecycle_pmi_service.evaluate_lessons_learned_institutional_reuse(
        lessons
    )

    assert res["total_lessons"] == 3
    assert res["actionable_count"] == 2
    assert res["categorized_count"] == 0
    assert res["reused_or_applied_count"] == 0
    assert res["actionability_rate"] == 66.67
    assert res["opa_reuse_rate"] == 0.0
    assert res["posture"] == "PASSIVE_ARCHIVE"


def test_lessons_learned_reuse_low_quality_retrospective():
    """Accionables < 50% -> LOW_QUALITY_RETROSPECTIVE aunque haya reuso OPA."""
    lessons = [
        {"action_item": "ok", "reused": True},
        {"category": "Risk"},
        {"description": "muy corto"},
    ]

    res = project_lifecycle_pmi_service.evaluate_lessons_learned_institutional_reuse(
        lessons
    )

    assert res["total_lessons"] == 3
    assert res["actionable_count"] == 0
    assert res["categorized_count"] == 1
    assert res["reused_or_applied_count"] == 1
    assert res["actionability_rate"] == 0.0
    assert res["opa_reuse_rate"] == 33.33
    assert res["posture"] == "LOW_QUALITY_RETROSPECTIVE"


def test_lessons_learned_reuse_no_lessons_recorded():
    """None, lista vacía o items no-dict -> NO_LESSONS_RECORDED con tasas 0.0."""
    for lessons in (None, [], ["no soy un dict", 42]):
        res = project_lifecycle_pmi_service.evaluate_lessons_learned_institutional_reuse(
            lessons
        )
        assert res == {
            "total_lessons": 0,
            "actionable_count": 0,
            "categorized_count": 0,
            "reused_or_applied_count": 0,
            "actionability_rate": 0.0,
            "opa_reuse_rate": 0.0,
            "posture": "NO_LESSONS_RECORDED",
        }


def test_lessons_learned_reuse_facade_delegates():
    """La fachada ProjectLifecyclePMIService delega al helper puro."""
    lessons = [{"action_item": "Estandarizar cierre con OPAs", "reused": True}]

    assert (
        project_lifecycle_pmi_service.ProjectLifecyclePMIService.
        evaluate_lessons_learned_institutional_reuse(lessons)
        == project_lifecycle_pmi_service.evaluate_lessons_learned_institutional_reuse(
            lessons
        )
    )


# ─── audit_charter_measurable_objectives (pure helper) ────────────────


def test_charter_objectives_smart_governance_aligned():
    """Objetivos SMART (meta + plazo + descripción >= 10) -> SMART_GOVERNANCE_ALIGNED."""
    objectives = [
        {
            "description": "Aumentar la asistencia dominical",
            "target_value": 1200,
            "metric": "asistentes",
            "deadline": "2026-12-31",
        },
        {
            "title": "Reducir costo operativo mensual",
            "metric": "reducción del 15%",
            "due_date": "enero 2027",
        },
        {
            "description": "Alcanzar meta de ofrenda con marco temporal definido",
            "target": "$50,000 USD",
            "timeframe": "Q1 2027",
        },
    ]

    res = project_lifecycle_pmi_service.audit_charter_measurable_objectives(objectives)

    assert res["total_objectives"] == 3
    assert res["quantified_target_count"] == 3
    assert res["time_bound_count"] == 3
    assert res["smart_compliant_count"] == 3
    assert res["smart_compliance_rate"] == 100.0
    assert res["posture"] == "SMART_GOVERNANCE_ALIGNED"


def test_charter_objectives_partially_measurable():
    """Algunos objetivos cuantificados, otros vagos -> PARTIALLY_MEASURABLE (rate >= 40)."""
    objectives = [
        {
            "description": "Incrementar nuevos discípulos activos",
            "target_value": 300,
            "deadline": "junio 2027",
        },
        {"description": "Sostener la comunión de las células semanalmente"},
    ]

    res = project_lifecycle_pmi_service.audit_charter_measurable_objectives(objectives)

    assert res["total_objectives"] == 2
    assert res["quantified_target_count"] == 1
    assert res["time_bound_count"] == 1
    assert res["smart_compliant_count"] == 1
    assert res["smart_compliance_rate"] == 50.0
    assert res["posture"] == "PARTIALLY_MEASURABLE"


def test_charter_objectives_smart_requires_quantified_timebound_and_description():
    """Falla cualquier pilar SMART (meta, plazo o descripción corta) -> no cuenta, y rate bajo -> VAGUE."""
    objectives = [
        {"description": "Meta sin plazo temporal alguno", "target_value": 5},
        {"metric": "80%", "deadline": "2026-11-01"},  # sin descripción
        {"description": "Aspiración difusa", "deadline": "2026-12-01"},  # sin meta
    ]

    res = project_lifecycle_pmi_service.audit_charter_measurable_objectives(objectives)

    assert res["total_objectives"] == 3
    assert res["quantified_target_count"] == 2
    assert res["time_bound_count"] == 2
    assert res["smart_compliant_count"] == 0
    assert res["smart_compliance_rate"] == 0.0
    assert res["posture"] == "VAGUE_UNMEASURABLE_OBJECTIVES"


def test_charter_objectives_no_objectives_recorded():
    """None, lista vacía o items no-dict -> NO_CHARTER_OBJECTIVES con rate 0.0."""
    for objectives in (None, [], ["no dict", 7]):
        res = project_lifecycle_pmi_service.audit_charter_measurable_objectives(
            objectives
        )
        assert res == {
            "total_objectives": 0,
            "quantified_target_count": 0,
            "time_bound_count": 0,
            "smart_compliant_count": 0,
            "smart_compliance_rate": 0.0,
            "posture": "NO_CHARTER_OBJECTIVES",
        }


# ─── audit_stakeholder_communication_cadence (pure helper) ──────────


def test_stakeholder_communication_cadence_governed_plan():
    """Canal + cadencia válida (aliases diario/semanal/mensual/hito) -> GOVERNED_COMMUNICATION_PLAN."""
    stakeholders = [
        {"channel": "email", "cadence": "weekly"},
        {"preferred_channel": "meeting", "frequency": "semanal"},
        {"canal": "tablero", "cadence": "MENSUAL"},
        {"channel": "nexus", "cadence": "por_hito"},
    ]

    res = project_lifecycle_pmi_service.audit_stakeholder_communication_cadence(
        stakeholders
    )

    assert res["total_stakeholders"] == 4
    assert res["channel_defined_count"] == 4
    assert res["cadence_defined_count"] == 4
    assert res["fully_planned_count"] == 4
    assert res["coverage_rate"] == 100.0
    assert res["posture"] == "GOVERNED_COMMUNICATION_PLAN"


def test_stakeholder_communication_cadence_partial_plan():
    """Solo la mitad con canal + cadencia -> PARTIAL_COMMUNICATION_PLAN (coverage 50)."""
    stakeholders = [
        {"channel": "email", "cadence": "weekly"},
        {"channel": "chat"},  # sin cadencia
        {"cadence": "daily"},  # sin canal
        {"channel": "voz", "frequency": "mensual"},
    ]

    res = project_lifecycle_pmi_service.audit_stakeholder_communication_cadence(
        stakeholders
    )

    assert res["total_stakeholders"] == 4
    assert res["channel_defined_count"] == 3
    assert res["cadence_defined_count"] == 3
    assert res["fully_planned_count"] == 2
    assert res["coverage_rate"] == 50.0
    assert res["posture"] == "PARTIAL_COMMUNICATION_PLAN"


def test_stakeholder_communication_cadence_invalid_values_and_unplanned():
    """Canales vacíos y cadencias fuera de gramática (< 40% coverage) -> UNPLANNED_STAKEHOLDER_OUTREACH."""
    stakeholders = [
        {"channel": " ", "cadence": "cuando-los-vientos-faborezcan"},
        {"preferred_channel": "pizarra", "frequency": "cada tanto"},
        {"canal": "email", "cadence": "transcurrido el quinquenio"},
    ]

    res = project_lifecycle_pmi_service.audit_stakeholder_communication_cadence(
        stakeholders
    )

    assert res["total_stakeholders"] == 3
    assert res["channel_defined_count"] == 2
    assert res["cadence_defined_count"] == 0
    assert res["fully_planned_count"] == 0
    assert res["coverage_rate"] == 0.0
    assert res["posture"] == "UNPLANNED_STAKEHOLDER_OUTREACH"


def test_stakeholder_communication_cadence_no_stakeholders_registered():
    """None, lista vacía o items no-dict -> NO_STAKEHOLDERS_REGISTERED con coverage 0.0."""
    for stakeholders in (None, [], ["no dict", 99]):
        res = project_lifecycle_pmi_service.audit_stakeholder_communication_cadence(
            stakeholders
        )
        assert res == {
            "total_stakeholders": 0,
            "channel_defined_count": 0,
            "cadence_defined_count": 0,
            "fully_planned_count": 0,
            "coverage_rate": 0.0,
            "posture": "NO_STAKEHOLDERS_REGISTERED",
        }


def test_evaluate_benefits_realization_posture_sustained_value():
    """Todos con owner, sin riesgo y realization_rate >= 75.0 -> 'SUSTAINED_VALUE_REALIZATION'."""
    benefits = [
        {"benefit_owner": "PMO", "target_value": 100.0, "actual_value": 110.0},
        {"owner": "Sponsor", "status": "realized"},
        {"responsable": "Director", "status": "logrado"},
        {"owner": "Operaciones", "target_value": 50.0, "actual_value": 25.0, "status": "in_progress"},
    ]
    res = project_lifecycle_pmi_service.ProjectLifecyclePMIService.evaluate_benefits_realization_posture(
        benefits
    )
    assert res == {
        "total_benefits": 4,
        "owner_assigned_count": 4,
        "realized_count": 3,
        "at_risk_count": 0,
        "realization_rate": 75.0,
        "posture": "SUSTAINED_VALUE_REALIZATION",
    }


def test_evaluate_benefits_realization_posture_at_risk():
    """Al menos un beneficio en riesgo o sin owner asignado -> 'BENEFITS_REALIZATION_AT_RISK'."""
    with_at_risk = [
        {"owner": "Sponsor", "status": "achieved"},
        {"owner": "Finanzas", "status": "en_riesgo"},
    ]
    res_risk = project_lifecycle_pmi_service.evaluate_benefits_realization_posture(
        with_at_risk
    )
    assert res_risk["at_risk_count"] == 1
    assert res_risk["owner_assigned_count"] == 2
    assert res_risk["posture"] == "BENEFITS_REALIZATION_AT_RISK"

    missing_owner = [
        {"owner": "Sponsor", "status": "cumplido"},
        {"owner": "  ", "status": "cumplido"},
    ]
    res_no_owner = project_lifecycle_pmi_service.evaluate_benefits_realization_posture(
        missing_owner
    )
    assert res_no_owner["at_risk_count"] == 0
    assert res_no_owner["owner_assigned_count"] == 1
    assert res_no_owner["realization_rate"] == 100.0
    assert res_no_owner["posture"] == "BENEFITS_REALIZATION_AT_RISK"


def test_evaluate_benefits_realization_posture_tracking_in_progress():
    """Todos con owner y sin riesgo pero realization_rate < 75.0 -> 'BENEFITS_TRACKING_IN_PROGRESS'."""
    benefits = [
        {"benefit_owner": "Líder 1", "target_value": 100.0, "actual_value": 100.0},
        {"benefit_owner": "Líder 2", "target_value": 100.0, "actual_value": 40.0, "status": "tracking"},
        {"benefit_owner": "Líder 3", "target_value": 100.0, "actual_value": 20.0, "status": "tracking"},
    ]
    res = project_lifecycle_pmi_service.evaluate_benefits_realization_posture(benefits)
    assert res["total_benefits"] == 3
    assert res["owner_assigned_count"] == 3
    assert res["realized_count"] == 1
    assert res["at_risk_count"] == 0
    assert res["realization_rate"] == 33.33
    assert res["posture"] == "BENEFITS_TRACKING_IN_PROGRESS"


def test_evaluate_benefits_realization_posture_no_benefits_defined():
    """Lista vacía, None o entradas no-dict -> 'NO_BENEFITS_DEFINED'."""
    for empty_input in (None, [], ["invalid", 42]):
        res = project_lifecycle_pmi_service.evaluate_benefits_realization_posture(
            empty_input
        )
        assert res == {
            "total_benefits": 0,
            "owner_assigned_count": 0,
            "realized_count": 0,
            "at_risk_count": 0,
            "realization_rate": 0.0,
            "posture": "NO_BENEFITS_DEFINED",
        }


# ─── audit_assumption_and_constraint_log (pure helper) ───────────


def test_assumption_log_governed_with_defaults_and_coverage():
    """Default type 'assumption', alias español y validados con dueño -> GOVERNED_ASSUMPTION_LOG."""
    entries = [
        {"status": "validated", "owner": "PM"},  # type ausente -> assumption
        {"type": "supuesto", "status": "VALIDADO", "responsable": "Pastor"},
        {"kind": "restricción", "status": "activo", "owner": "COO"},
        {"type": "hipotesis", "status": "confirmed", "owner": "Tesorero"},
        {"type": "constraint", "status": "pending", "owner": "Obras"},
    ]

    res = project_lifecycle_pmi_service.audit_assumption_and_constraint_log(entries)

    assert res["total_entries"] == 5
    assert res["assumptions_count"] == 3
    assert res["constraints_count"] == 2
    assert res["validated_or_active_count"] == 4
    assert res["invalidated_count"] == 0
    assert res["governance_coverage_rate"] == 80.0
    assert res["posture"] == "GOVERNED_ASSUMPTION_LOG"


def test_assumption_log_unconvertated_invalidated_takes_precedence():
    """Invalidados sin convertir a riesgo -> UNCONVERTED_INVALIDATED_ASSUMPTIONS aunque haya alta cobertura."""
    entries = [
        {"type": "assumption", "status": "validated", "owner": "PM"},
        {"type": "assumption", "status": "invalidated", "owner": "PM"},
        {"type": "supuesto", "status": "escalated_to_risk", "owner": "DBA"},
    ]

    res = project_lifecycle_pmi_service.audit_assumption_and_constraint_log(entries)

    assert res["total_entries"] == 3
    assert res["validated_or_active_count"] == 1
    assert res["invalidated_count"] == 2
    assert res["governance_coverage_rate"] == 33.33
    assert res["posture"] == "UNCONVERTED_INVALIDATED_ASSUMPTIONS"


def test_assumption_log_unvalidated_without_owner_or_status():
    """Validados sin dueño o sin status no cuentan; < 80% cobertura -> UNVALIDATED_ASSUMPTION_EXPOSURE."""
    entries = [
        {"status": "validated"},  # sin dueño -> no cuenta
        {"owner": "PM"},  # sin status -> no cuenta
        {"type": "restriccion", "status": "confirmado", "owner": "Finanzas"},
        {"type": "assumption", "status": "pending", "owner": "PM"},
    ]

    res = project_lifecycle_pmi_service.audit_assumption_and_constraint_log(entries)

    assert res["total_entries"] == 4
    assert res["assumptions_count"] == 3
    assert res["constraints_count"] == 1
    assert res["validated_or_active_count"] == 1
    assert res["invalidated_count"] == 0
    assert res["governance_coverage_rate"] == 25.0
    assert res["posture"] == "UNVALIDATED_ASSUMPTION_EXPOSURE"


def test_assumption_log_empty_and_non_dict_entries():
    """None, lista vacía o items no-dict -> EMPTY_ASSUMPTION_LOG con coverage 0.0."""
    for entries in (None, [], ["no dict", 13]):
        res = project_lifecycle_pmi_service.audit_assumption_and_constraint_log(
            entries  # type: ignore[arg-type]
        )
        assert res == {
            "total_entries": 0,
            "assumptions_count": 0,
            "constraints_count": 0,
            "validated_or_active_count": 0,
            "invalidated_count": 0,
            "governance_coverage_rate": 0.0,
            "posture": "EMPTY_ASSUMPTION_LOG",
        }


# ─── audit_project_procurement_and_handover_closeout (pure helper) ───


def test_audit_procurement_and_handover_closeout_ready():
    """Contratos cerrados/liquidados con factura final pagada y traspaso operativo completo -> ADMINISTRATIVE_CLOSURE_READY."""
    contracts = [
        {
            "id": "CTR-101",
            "status": "CLOSED",
            "open_claims": 0,
            "final_invoice_paid": True,
        },
        {
            "contract_id": "CTR-102",
            "status": "settled",
            "open_claims": False,
            "final_invoice_paid": True,
        },
    ]
    handover_items = [
        {
            "id": "DEL-01",
            "transferred_to_operations": True,
            "operations_owner": "Dirección de Infraestructura",
        },
        {
            "deliverable_id": "DEL-02",
            "transferred_to_operations": True,
            "operations_owner": "Soporte Ministerial TI",
        },
    ]

    res = project_lifecycle_pmi_service.ProjectLifecyclePMIService.audit_project_procurement_and_handover_closeout(
        contracts=contracts, handover_items=handover_items
    )
    assert res["total_contracts"] == 2
    assert res["open_contract_ids"] == []
    assert res["disputed_contract_ids"] == []
    assert res["total_handover_items"] == 2
    assert res["pending_handover_ids"] == []
    assert res["ready_for_administrative_closure"] is True
    assert res["closeout_posture"] == "ADMINISTRATIVE_CLOSURE_READY"
    assert len(res["recommendations"]) >= 1
    assert (
        "audit_project_procurement_and_handover_closeout"
        in project_lifecycle_pmi_service.__all__
    )


def test_audit_procurement_and_handover_closeout_claims_blocked():
    """Contratos en disputa o con reclamos abiertos -> PROCUREMENT_CLAIMS_BLOCKED."""
    contracts = [
        {
            "id": "CTR-201",
            "status": "DISPUTED",
            "open_claims": 2,
            "final_invoice_paid": False,
        },
        {
            "contract_id": "CTR-202",
            "status": "CLOSED",
            "open_claims": True,
            "final_invoice_paid": True,
        },
    ]
    handover_items = [
        {
            "id": "DEL-10",
            "transferred_to_operations": True,
            "operations_owner": "Equipo Operaciones",
        }
    ]

    res = project_lifecycle_pmi_service.audit_project_procurement_and_handover_closeout(
        contracts=contracts, handover_items=handover_items
    )
    assert res["total_contracts"] == 2
    assert res["open_contract_ids"] == ["CTR-201"]
    assert res["disputed_contract_ids"] == ["CTR-201", "CTR-202"]
    assert res["pending_handover_ids"] == []
    assert res["ready_for_administrative_closure"] is False
    assert res["closeout_posture"] == "PROCUREMENT_CLAIMS_BLOCKED"
    assert any("CTR-201" in rec for rec in res["recommendations"])


def test_audit_procurement_and_handover_closeout_pending_contract_or_handover():
    """Sin disputas pero con factura pendiente o traspaso operativo incompleto -> PENDING_CONTRACT_OR_HANDOVER_CLOSEOUT."""
    contracts = [
        {
            "id": "CTR-301",
            "status": "CLOSED",
            "open_claims": 0,
            "final_invoice_paid": False,
        },
        {
            "id": "CTR-302",
            "status": "OPEN",
            "open_claims": 0,
            "final_invoice_paid": True,
        },
    ]
    handover_items = [
        {
            "id": "DEL-20",
            "transferred_to_operations": False,
            "operations_owner": "Operaciones Sede Norte",
        },
        {
            "deliverable_id": "DEL-21",
            "transferred_to_operations": True,
            "operations_owner": "TBD",
        },
        {
            "id": "DEL-22",
            "transferred_to_operations": True,
            "operations_owner": "SIN ASIGNAR",
        },
    ]

    res = project_lifecycle_pmi_service.audit_project_procurement_and_handover_closeout(
        contracts=contracts, handover_items=handover_items
    )
    assert res["total_contracts"] == 2
    assert res["open_contract_ids"] == ["CTR-301", "CTR-302"]
    assert res["disputed_contract_ids"] == []
    assert res["total_handover_items"] == 3
    assert res["pending_handover_ids"] == ["DEL-20", "DEL-21", "DEL-22"]
    assert res["ready_for_administrative_closure"] is False
    assert res["closeout_posture"] == "PENDING_CONTRACT_OR_HANDOVER_CLOSEOUT"
    assert len(res["recommendations"]) == 2


def test_audit_procurement_and_handover_closeout_no_artifacts():
    """Sin contratos ni entregables de traspaso -> NO_CLOSEOUT_ARTIFACTS."""
    for c_in, h_in in ((None, None), ([], []), (["bad"], [123])):
        res = project_lifecycle_pmi_service.audit_project_procurement_and_handover_closeout(
            contracts=c_in, handover_items=h_in  # type: ignore[arg-type]
        )
        assert res["total_contracts"] == 0
        assert res["open_contract_ids"] == []
        assert res["disputed_contract_ids"] == []
        assert res["total_handover_items"] == 0
        assert res["pending_handover_ids"] == []
        assert res["ready_for_administrative_closure"] is False
        assert res["closeout_posture"] == "NO_CLOSEOUT_ARTIFACTS"
        assert len(res["recommendations"]) == 1


# ─── audit_stakeholder_engagement_transition_gaps (pure helper) ───────


def test_stakeholder_engagement_transition_gaps_aligned_matrix():
    """Todos en/o sobre su nivel deseado -> ALIGNED_ENGAGEMENT_MATRIX con alignment 100/66.67."""
    res = project_lifecycle_pmi_service.audit_stakeholder_engagement_transition_gaps(
        [
            # current >= desired: sin gap
            {"id": "SH-1", "current_engagement": "supportive", "desired_engagement": "neutral"},
            # defaults: current NEUTRAL(3), desired SUPPORTIVE(4) -> gap PERO hay plan >= 8 chars
            {"name": "RGV Norte", "action_plan": "Presentar avances mensuales"},
            {"id": "SH-3", "current_level": "líder", "desired_level": "5", "influence": 5},
        ]
    )

    assert res["total_stakeholders"] == 3
    assert res["gap_count"] == 1
    assert res["high_power_resistant_ids"] == []
    assert res["unaddressed_gap_ids"] == []
    assert res["alignment_rate_pct"] == 66.67
    assert res["seam_posture"] == "ALIGNED_ENGAGEMENT_MATRIX"
    assert len(res["recommendations"]) == 1


def test_stakeholder_engagement_transition_gaps_critical_high_power_resistance():
    """Resistente con poder alto (texto o int >= 4) -> CRITICAL_HIGH_POWER_RESISTANCE precede a gaps."""
    res = project_lifecycle_pmi_service.audit_stakeholder_engagement_transition_gaps(
        [
            {"id": "CEO", "current_engagement": "Resistente", "influence": "HIGH"},
            {"id": "Ministerio", "current_level": "unaware", "power": 4},
            {"id": "Liderador", "current_engagement": "supportive"},
        ]
    )

    assert res["total_stakeholders"] == 3
    assert res["gap_count"] == 2
    assert res["high_power_resistant_ids"] == ["CEO", "Ministerio"]
    assert res["unaddressed_gap_ids"] == ["CEO", "Ministerio"]
    assert res["alignment_rate_pct"] == 33.33
    assert res["seam_posture"] == "CRITICAL_HIGH_POWER_RESISTANCE"
    assert len(res["recommendations"]) == 1  # una por postura final


def test_stakeholder_engagement_transition_gaps_unaddressed_gaps():
    """Gaps con poder bajo y sin plan (< 8 chars) -> UNADDRESSED_ENGAGEMENT_GAPS."""
    res = project_lifecycle_pmi_service.audit_stakeholder_engagement_transition_gaps(
        [
            {"id": "Vol", "current_engagement": "neutral", "desired_engagement": "apoyo"},
            {"id": "Vec", "current_level": "desconocedor", "desired_level": "partidario", "influence": "baja", "action_plan": "ok"},
            {"id": "Coord", "current_engagement": "resistente", "desired_engagement": "supportive", "influence": 3, "action_plan": "Invitar a sesión de cadrte"},
        ]
    )

    assert res["total_stakeholders"] == 3
    assert res["gap_count"] == 3
    assert res["high_power_resistant_ids"] == []
    assert res["unaddressed_gap_ids"] == ["Vol", "Vec"]
    assert res["alignment_rate_pct"] == 0.0
    assert res["seam_posture"] == "UNADDRESSED_ENGAGEMENT_GAPS"
    assert len(res["recommendations"]) == 1


def test_stakeholder_engagement_transition_gaps_empty_matrix():
    """None, lista vacía o no-dicts -> EMPTY_STAKEHOLDER_MATRIX con alignment 0.0."""
    for stakeholders in (None, [], ["no dict", 9]):
        res = project_lifecycle_pmi_service.audit_stakeholder_engagement_transition_gaps(
            stakeholders  # type: ignore[arg-type]
        )
        assert res == {
            "total_stakeholders": 0,
            "gap_count": 0,
            "high_power_resistant_ids": [],
            "unaddressed_gap_ids": [],
            "alignment_rate_pct": 0.0,
            "seam_posture": "EMPTY_STAKEHOLDER_MATRIX",
            "recommendations": [
                "Registrar los interesados con niveles actual y deseado para iniciar la matriz SEAM."
            ],
        }


def test_audit_project_tailoring_and_opa_compliance_governed():
    """Decisiones aprobadas con justificación >= 10 chars y OPAs obligatorias cubiertas -> GOVERNED_METHODOLOGY_TAILORING."""
    decisions = [
        {
            "process_area": "Scope & WBS",
            "approach": "HYBRID",
            "justification": "Iteraciones quincenales para UI con línea base fija de infraestructura.",
            "pmo_approved": True,
            "opa_template_ref": "OPA-TPL-CHARTER-V3",
        },
        {
            "knowledge_area": "Schedule Management",
            "approach": "agile",
            "justification": "Tablero Kanban acoplado a hitos trimestrales del comité directivo.",
            "pmo_approved": True,
            "opa_template_ref": "opa-tpl-raid-v2",
        },
    ]
    mandatory = ["OPA-TPL-CHARTER-V3", "OPA-TPL-RAID-V2"]

    res = project_lifecycle_pmi_service.audit_project_tailoring_and_opa_compliance(
        decisions, mandatory_opa_templates=mandatory
    )
    assert res["total_tailoring_decisions"] == 2
    assert res["unjustified_or_unapproved_areas"] == []
    assert res["missing_mandatory_opas"] == []
    assert res["compliance_rate_pct"] == 100.0
    assert res["tailoring_posture"] == "GOVERNED_METHODOLOGY_TAILORING"
    assert len(res["recommendations"]) == 1
    assert (
        project_lifecycle_pmi_service.ProjectLifecyclePMIService.audit_project_tailoring_and_opa_compliance(
            decisions, mandatory_opa_templates=mandatory
        )
        == res
    )


def test_audit_project_tailoring_and_opa_compliance_missing_mandatory_opas():
    """Plantillas OPA obligatorias no referenciadas -> MISSING_MANDATORY_OPA_TEMPLATES."""
    decisions = [
        {
            "process_area": "Cost & EVM",
            "approach": "PREDICTIVE",
            "justification": "Control mensual de valor ganado exigido por patrocinador financiero.",
            "pmo_approved": True,
            "opa_template_ref": "OPA-TPL-EVM-01",
        },
    ]
    mandatory = ["OPA-TPL-EVM-01", "OPA-TPL-CLOSURE-04"]

    res = project_lifecycle_pmi_service.audit_project_tailoring_and_opa_compliance(
        decisions, mandatory_opa_templates=mandatory
    )
    assert res["total_tailoring_decisions"] == 1
    assert res["unjustified_or_unapproved_areas"] == []
    assert res["missing_mandatory_opas"] == ["OPA-TPL-CLOSURE-04"]
    assert res["compliance_rate_pct"] == 100.0
    assert res["tailoring_posture"] == "MISSING_MANDATORY_OPA_TEMPLATES"
    assert any("OPA-TPL-CLOSURE-04" in r for r in res["recommendations"])


def test_audit_project_tailoring_and_opa_compliance_unapproved_deviations():
    """Áreas sin aprobación PMO o con justificación < 10 chars -> UNAPPROVED_TAILORING_DEVIATIONS."""
    decisions = [
        {
            "process_area": "Quality Assurance",
            "approach": "HYBRID",
            "justification": "Revisiones cruzadas automatizadas en CI/CD y auditoría DoD por sprint.",
            "pmo_approved": True,
            "opa_template_ref": "OPA-QA-01",
        },
        {
            "process_area": "Risk Management",
            "approach": "AGILE",
            "justification": "Corto",
            "pmo_approved": True,
            "opa_template_ref": "OPA-RISK-02",
        },
        {
            "knowledge_area": "Procurement",
            "approach": "PREDICTIVE",
            "justification": "Licitación directa abreviada por proveedor único homologado.",
            "pmo_approved": False,
        },
    ]

    res = project_lifecycle_pmi_service.audit_project_tailoring_and_opa_compliance(
        decisions, mandatory_opa_templates=["OPA-QA-01"]
    )
    assert res["total_tailoring_decisions"] == 3
    assert res["unjustified_or_unapproved_areas"] == ["Risk Management", "Procurement"]
    assert res["missing_mandatory_opas"] == []
    assert res["compliance_rate_pct"] == 33.33
    assert res["tailoring_posture"] == "UNAPPROVED_TAILORING_DEVIATIONS"
    assert any(
        "Risk Management" in r and "Procurement" in r for r in res["recommendations"]
    )


def test_audit_project_tailoring_and_opa_compliance_no_tailoring_recorded():
    """Sin decisiones ni OPAs obligatorias pendientes -> NO_TAILORING_RECORDED."""
    for payload in (None, [], ["invalid", 42]):
        res = project_lifecycle_pmi_service.audit_project_tailoring_and_opa_compliance(
            payload, mandatory_opa_templates=None  # type: ignore[arg-type]
        )
        assert res["total_tailoring_decisions"] == 0
        assert res["unjustified_or_unapproved_areas"] == []
        assert res["missing_mandatory_opas"] == []
        assert res["compliance_rate_pct"] == 0.0
        assert res["tailoring_posture"] == "NO_TAILORING_RECORDED"
        assert len(res["recommendations"]) == 1


def test_audit_benefits_realization_sustainability_sustainable():
    """Beneficios con dueño, cadencia, metas > 0 y realización >= umbral -> SUSTAINABLE_BENEFITS_REALIZATION."""
    benefits = [
        {
            "id": "BEN-101",
            "benefit_owner": "Dirección Operativa",
            "measurement_cadence": "QUARTERLY",
            "target_value": 100.0,
            "realized_value": 90.0,
        },
        {
            "benefit_id": "BEN-102",
            "owner": "PMO Pastoral",
            "review_horizon": "6M_POST_GO_LIVE",
            "target": 200.0,
            "actual_value": 180.0,
        },
    ]

    res = project_lifecycle_pmi_service.audit_benefits_realization_sustainability(
        benefits, min_realization_ratio_pct=80.0
    )
    assert res == {
        "total_benefits": 2,
        "overall_realization_pct": 90.0,
        "unowned_or_unscheduled_benefit_ids": [],
        "unquantified_benefit_ids": [],
        "underperforming_benefit_ids": [],
        "is_sustainable": True,
        "benefits_posture": "SUSTAINABLE_BENEFITS_REALIZATION",
    }
    assert (
        project_lifecycle_pmi_service.ProjectLifecyclePMIService.audit_benefits_realization_sustainability(
            benefits, min_realization_ratio_pct=80.0
        )
        == res
    )


def test_audit_benefits_realization_sustainability_missing_ownership_or_cadence():
    """Beneficios sin dueño o sin cadencia de revisión -> MISSING_BENEFIT_OWNERSHIP_OR_CADENCE."""
    benefits = [
        {
            "id": "BEN-201",
            "benefit_owner": "",
            "measurement_cadence": "MONTHLY",
            "target_value": 100.0,
            "realized_value": 95.0,
        },
        {
            "id": "BEN-202",
            "owner": "Coordinación General",
            "review_horizon": "   ",
            "target_value": 100.0,
            "realized_value": 85.0,
        },
    ]

    res = project_lifecycle_pmi_service.audit_benefits_realization_sustainability(
        benefits
    )
    assert res["total_benefits"] == 2
    assert res["overall_realization_pct"] == 90.0
    assert res["unowned_or_unscheduled_benefit_ids"] == ["BEN-201", "BEN-202"]
    assert res["unquantified_benefit_ids"] == []
    assert res["underperforming_benefit_ids"] == []
    assert res["is_sustainable"] is False
    assert res["benefits_posture"] == "MISSING_BENEFIT_OWNERSHIP_OR_CADENCE"


def test_audit_benefits_realization_sustainability_unquantified_and_shortfall():
    """Meta <= 0 -> UNQUANTIFIED_BENEFIT_TARGETS; realización < umbral -> BENEFITS_REALIZATION_SHORTFALL."""
    unquantified = [
        {
            "id": "BEN-301",
            "owner": "Líder de Área",
            "measurement_cadence": "QUARTERLY",
            "target_value": 0.0,
            "realized_value": 10.0,
        },
        {
            "id": "BEN-302",
            "owner": "Líder de Área",
            "measurement_cadence": "QUARTERLY",
            "target_value": 100.0,
            "realized_value": 50.0,
        },
    ]
    res_unq = project_lifecycle_pmi_service.audit_benefits_realization_sustainability(
        unquantified, min_realization_ratio_pct=80.0
    )
    assert res_unq["unquantified_benefit_ids"] == ["BEN-301"]
    assert res_unq["underperforming_benefit_ids"] == ["BEN-302"]
    assert res_unq["is_sustainable"] is False
    assert res_unq["benefits_posture"] == "UNQUANTIFIED_BENEFIT_TARGETS"

    shortfall = [
        {
            "id": "BEN-303",
            "owner": "Finanzas",
            "measurement_cadence": "ANNUAL",
            "target_value": 100.0,
            "realized_value": 90.0,
        },
        {
            "id": "BEN-304",
            "owner": "Operaciones",
            "measurement_cadence": "QUARTERLY",
            "target_value": 100.0,
            "realized_value": 60.0,
        },
    ]
    res_short = project_lifecycle_pmi_service.audit_benefits_realization_sustainability(
        shortfall, min_realization_ratio_pct=80.0
    )
    assert res_short["total_benefits"] == 2
    assert res_short["overall_realization_pct"] == 75.0
    assert res_short["unowned_or_unscheduled_benefit_ids"] == []
    assert res_short["unquantified_benefit_ids"] == []
    assert res_short["underperforming_benefit_ids"] == ["BEN-304"]
    assert res_short["is_sustainable"] is False
    assert res_short["benefits_posture"] == "BENEFITS_REALIZATION_SHORTFALL"


def test_audit_benefits_realization_sustainability_no_benefits_registered():
    """Lista vacía, None o entradas no-dict -> NO_BENEFITS_REGISTERED."""
    for payload in (None, [], ["invalid", 99]):
        res = project_lifecycle_pmi_service.audit_benefits_realization_sustainability(
            payload  # type: ignore[arg-type]
        )
        assert res == {
            "total_benefits": 0,
            "overall_realization_pct": 0.0,
            "unowned_or_unscheduled_benefit_ids": [],
            "unquantified_benefit_ids": [],
            "underperforming_benefit_ids": [],
            "is_sustainable": False,
            "benefits_posture": "NO_BENEFITS_REGISTERED",
        }
