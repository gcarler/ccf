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


def test_audit_team_charter_and_tuckman_governance_high_performing():
    """4 pilares completos, etapa performing/norming y 0 conflictos -> HIGH_PERFORMING_TEAM_GOVERNANCE."""
    charter = {
        "core_values": ["Transparencia", "Excelencia técnica", "Servicio"],
        "communication_guidelines": "Daily standup 9:00 AM y canal asíncrono oficial.",
        "decision_making_criteria": "Consenso técnico con desempate por arquitecto líder.",
        "conflict_resolution_process": "Mediación directa -> Facilitación PM -> Comité PMO.",
        "tuckman_stage": "performing",
        "unresolved_conflicts_count": 0,
    }
    res = project_lifecycle_pmi_service.audit_team_charter_and_tuckman_governance(
        charter
    )
    assert res == {
        "charter_completeness_pct": 100.0,
        "missing_charter_pillars": [],
        "tuckman_stage": "PERFORMING",
        "unresolved_conflicts_count": 0,
        "is_healthy": True,
        "team_posture": "HIGH_PERFORMING_TEAM_GOVERNANCE",
    }
    assert (
        project_lifecycle_pmi_service.ProjectLifecyclePMIService.audit_team_charter_and_tuckman_governance(
            charter
        )
        == res
    )


def test_audit_team_charter_and_tuckman_governance_incomplete_agreements():
    """Faltan 1 o más pilares del Team Charter -> INCOMPLETE_TEAM_CHARTER_AGREEMENTS."""
    charter = {
        "valores": "Respeto mutuo y responsabilidad",
        "pautas_comunicacion": "Reuniones semanales de sincronización",
        "criterios_decision": "   ",
        "resolucion_conflictos": [],
        "maturity_stage": "norming",
    }
    res = project_lifecycle_pmi_service.audit_team_charter_and_tuckman_governance(
        charter
    )
    assert res["charter_completeness_pct"] == 50.0
    assert res["missing_charter_pillars"] == [
        "decision_making_criteria",
        "conflict_resolution_process",
    ]
    assert res["tuckman_stage"] == "NORMING"
    assert res["unresolved_conflicts_count"] == 0
    assert res["is_healthy"] is False
    assert res["team_posture"] == "INCOMPLETE_TEAM_CHARTER_AGREEMENTS"


def test_audit_team_charter_and_tuckman_governance_storming_and_forming():
    """4 pilares en storming o con conflictos -> STORMING_OR_CONFLICT_FRICTION; en forming -> EARLY_FORMING_ALIGNMENT."""
    base_pillars = {
        "core_values": "Colaboración",
        "communication_guidelines": "Canal de proyecto",
        "decision_making_criteria": "Votación ponderada",
        "conflict_resolution_process": "Escalamiento al PM",
    }
    res_storming = project_lifecycle_pmi_service.audit_team_charter_and_tuckman_governance(
        {**base_pillars, "tuckman_stage": "storming", "open_conflicts": 2}
    )
    assert res_storming["charter_completeness_pct"] == 100.0
    assert res_storming["missing_charter_pillars"] == []
    assert res_storming["tuckman_stage"] == "STORMING"
    assert res_storming["unresolved_conflicts_count"] == 2
    assert res_storming["is_healthy"] is False
    assert res_storming["team_posture"] == "STORMING_OR_CONFLICT_FRICTION"

    res_forming = project_lifecycle_pmi_service.audit_team_charter_and_tuckman_governance(
        {**base_pillars, "tuckman_stage": "Forming", "unresolved_conflicts_count": 0}
    )
    assert res_forming["charter_completeness_pct"] == 100.0
    assert res_forming["tuckman_stage"] == "FORMING"
    assert res_forming["unresolved_conflicts_count"] == 0
    assert res_forming["is_healthy"] is False
    assert res_forming["team_posture"] == "EARLY_FORMING_ALIGNMENT"


def test_audit_team_charter_and_tuckman_governance_missing_team_charter():
    """None, dict vacío o 0 pilares -> MISSING_TEAM_CHARTER."""
    for payload in (None, {}, {"tuckman_stage": "performing"}):
        res = project_lifecycle_pmi_service.audit_team_charter_and_tuckman_governance(
            payload
        )
        assert res["charter_completeness_pct"] == 0.0
        assert res["missing_charter_pillars"] == [
            "core_values",
            "communication_guidelines",
            "decision_making_criteria",
            "conflict_resolution_process",
        ]
        assert res["is_healthy"] is False
        assert res["team_posture"] == "MISSING_TEAM_CHARTER"


def test_audit_phase_gate_transition_readiness_rigorous_governance():
    """Stage-Gates aprobados con aprobador, 100% criterios cumplidos y 0 bloqueantes -> RIGOROUS_STAGE_GATE_GOVERNANCE."""
    gates = [
        {
            "id": "GATE-INIT",
            "gate_decision": "approved",
            "approver": "Comité Directivo PMO",
            "criteria_total": 5,
            "criteria_met": 5,
            "open_blockers_count": 0,
        },
        {
            "gate_id": "GATE-PLAN",
            "status": "GO",
            "decided_by": "Patrocinador Ejecutivo",
            "total_criteria": 8,
            "passed_criteria": 8,
            "blockers": 0,
        },
        {
            "phase_name": "GATE-EXEC",
            "gate_decision": "pending",
            "approver": "",
            "criteria_total": 10,
            "criteria_met": 4,
            "open_blockers_count": 2,
        },
    ]
    res = project_lifecycle_pmi_service.audit_phase_gate_transition_readiness(gates)
    assert res == {
        "total_gates": 3,
        "approved_gates_count": 2,
        "bypassed_exit_criteria_gate_ids": [],
        "unapproved_governance_gate_ids": [],
        "blocked_transition_gate_ids": [],
        "is_gate_compliant": True,
        "gate_posture": "RIGOROUS_STAGE_GATE_GOVERNANCE",
    }
    assert (
        project_lifecycle_pmi_service.ProjectLifecyclePMIService.audit_phase_gate_transition_readiness(
            gates
        )
        == res
    )


def test_audit_phase_gate_transition_readiness_blocked_force_passed():
    """Stage-Gate aprobado con open_blockers_count > 0 -> BLOCKED_GATE_TRANSITION_FORCE_PASSED."""
    gates = [
        {
            "id": "GATE-QA",
            "gate_decision": "passed",
            "approver": "Director Técnico",
            "criteria_total": 6,
            "criteria_met": 6,
            "open_blockers_count": 2,
        }
    ]
    res = project_lifecycle_pmi_service.audit_phase_gate_transition_readiness(gates)
    assert res["total_gates"] == 1
    assert res["approved_gates_count"] == 1
    assert res["blocked_transition_gate_ids"] == ["GATE-QA"]
    assert res["is_gate_compliant"] is False
    assert res["gate_posture"] == "BLOCKED_GATE_TRANSITION_FORCE_PASSED"


def test_audit_phase_gate_transition_readiness_bypass_and_missing_signoff():
    """Criterios incompletos -> EXIT_CRITERIA_BYPASS_DETECTED; sin approver -> MISSING_GATE_GOVERNANCE_SIGNOFF."""
    res_bypass = project_lifecycle_pmi_service.audit_phase_gate_transition_readiness(
        [
            {
                "id": "GATE-UAT",
                "status": "aprobado",
                "approver": "Líder Funcional",
                "criteria_total": 10,
                "criteria_met": 7,
                "open_blockers_count": 0,
            }
        ],
        min_exit_criteria_pass_pct=100.0,
    )
    assert res_bypass["bypassed_exit_criteria_gate_ids"] == ["GATE-UAT"]
    assert res_bypass["unapproved_governance_gate_ids"] == []
    assert res_bypass["blocked_transition_gate_ids"] == []
    assert res_bypass["is_gate_compliant"] is False
    assert res_bypass["gate_posture"] == "EXIT_CRITERIA_BYPASS_DETECTED"

    res_unsigned = project_lifecycle_pmi_service.audit_phase_gate_transition_readiness(
        [
            {
                "id": "GATE-CLOSE",
                "gate_decision": "cerrado",
                "approver": "   ",
                "criteria_total": 4,
                "criteria_met": 4,
                "open_blockers_count": 0,
            }
        ]
    )
    assert res_unsigned["bypassed_exit_criteria_gate_ids"] == []
    assert res_unsigned["unapproved_governance_gate_ids"] == ["GATE-CLOSE"]
    assert res_unsigned["blocked_transition_gate_ids"] == []
    assert res_unsigned["is_gate_compliant"] is False
    assert res_unsigned["gate_posture"] == "MISSING_GATE_GOVERNANCE_SIGNOFF"


def test_audit_phase_gate_transition_readiness_empty_or_none():
    """Lista vacía, None o entradas no-dict -> NO_PHASE_GATES_EVALUATED."""
    for payload in (None, [], ["invalid", 42]):
        res = project_lifecycle_pmi_service.audit_phase_gate_transition_readiness(
            payload  # type: ignore[arg-type]
        )
        assert res == {
            "total_gates": 0,
            "approved_gates_count": 0,
            "bypassed_exit_criteria_gate_ids": [],
            "unapproved_governance_gate_ids": [],
            "blocked_transition_gate_ids": [],
            "is_gate_compliant": True,
            "gate_posture": "NO_PHASE_GATES_EVALUATED",
        }


def test_audit_make_or_buy_and_vendor_bids_sound_selection():
    """Decisiones make y buy competitivas (o con sole_source_justification) y score >= 70 -> SOUND_PROCUREMENT_SOURCE_SELECTION."""
    decisions = [
        {
            "id": "MOB-01",
            "decision": "make",
        },
        {
            "decision_id": "MOB-02",
            "strategy": "buy",
            "bids_received": 3,
            "selected_vendor_score": 88.5,
        },
        {
            "item_id": "MOB-03",
            "decision": "comprar",
            "bids_count": 1,
            "sole_source_justification": "Proveedor certificado exclusivo de hardware biométrico",
            "evaluation_score": 75.0,
        },
    ]
    res = project_lifecycle_pmi_service.audit_make_or_buy_and_vendor_bids(decisions)
    assert res == {
        "total_decisions": 3,
        "buy_decisions_count": 2,
        "unjustified_decision_ids": [],
        "non_competitive_buy_ids": [],
        "low_scoring_vendor_award_ids": [],
        "is_compliant": True,
        "procurement_decision_posture": "SOUND_PROCUREMENT_SOURCE_SELECTION",
    }
    assert (
        project_lifecycle_pmi_service.ProjectLifecyclePMIService.audit_make_or_buy_and_vendor_bids(
            decisions
        )
        == res
    )


def test_audit_make_or_buy_and_vendor_bids_unjustified_choice():
    """Decisión con estrategia inválida o vacía -> UNJUSTIFIED_MAKE_OR_BUY_CHOICE."""
    res = project_lifecycle_pmi_service.audit_make_or_buy_and_vendor_bids(
        [
            {"id": "MOB-BAD", "decision": "maybe_lease"},
            {"id": "MOB-OK", "decision": "hacer"},
        ]
    )
    assert res["total_decisions"] == 2
    assert res["buy_decisions_count"] == 0
    assert res["unjustified_decision_ids"] == ["MOB-BAD"]
    assert res["non_competitive_buy_ids"] == []
    assert res["low_scoring_vendor_award_ids"] == []
    assert res["is_compliant"] is False
    assert res["procurement_decision_posture"] == "UNJUSTIFIED_MAKE_OR_BUY_CHOICE"


def test_audit_make_or_buy_and_vendor_bids_non_competitive_and_low_score():
    """Buy con 1 oferta sin justificación -> NON_COMPETITIVE_SINGLE_BID_RISK; score < 70 -> SUBTHRESHOLD_VENDOR_TECHNICAL_SCORE."""
    non_comp_res = project_lifecycle_pmi_service.audit_make_or_buy_and_vendor_bids(
        [
            {
                "id": "MOB-SINGLE",
                "decision": "buy",
                "bids_received": 1,
                "sole_source_justification": "   ",
                "selected_vendor_score": 82.0,
            }
        ],
        min_competitive_bids=2,
    )
    assert non_comp_res["non_competitive_buy_ids"] == ["MOB-SINGLE"]
    assert non_comp_res["low_scoring_vendor_award_ids"] == []
    assert non_comp_res["is_compliant"] is False
    assert (
        non_comp_res["procurement_decision_posture"]
        == "NON_COMPETITIVE_SINGLE_BID_RISK"
    )

    low_score_res = project_lifecycle_pmi_service.audit_make_or_buy_and_vendor_bids(
        [
            {
                "id": "MOB-LOW",
                "decision": "buy",
                "bids_received": 3,
                "selected_vendor_score": 64.0,
            }
        ]
    )
    assert low_score_res["non_competitive_buy_ids"] == []
    assert low_score_res["low_scoring_vendor_award_ids"] == ["MOB-LOW"]
    assert low_score_res["is_compliant"] is False
    assert (
        low_score_res["procurement_decision_posture"]
        == "SUBTHRESHOLD_VENDOR_TECHNICAL_SCORE"
    )


def test_audit_make_or_buy_and_vendor_bids_empty_or_none():
    """Lista vacía o None -> NO_MAKE_OR_BUY_DECISIONS."""
    for payload in (None, [], ["invalid", 99]):
        res = project_lifecycle_pmi_service.audit_make_or_buy_and_vendor_bids(
            payload  # type: ignore[arg-type]
        )
        assert res == {
            "total_decisions": 0,
            "buy_decisions_count": 0,
            "unjustified_decision_ids": [],
            "non_competitive_buy_ids": [],
            "low_scoring_vendor_award_ids": [],
            "is_compliant": True,
            "procurement_decision_posture": "NO_MAKE_OR_BUY_DECISIONS",
        }


def test_audit_risk_appetite_and_threshold_governance_within_and_governed():
    """Riesgos dentro del apetito -> WITHIN_RISK_APPETITE_THRESHOLDS; brecha gobernada -> GOVERNED_THRESHOLD_ESCALATION."""
    within_res = project_lifecycle_pmi_service.audit_risk_appetite_and_threshold_governance(
        [
            {"id": "RSK-1", "status": "open", "cost_impact_pct": 3.0, "schedule_impact_days": 5.0},
            {"id": "RSK-2", "status": "closed", "cost_impact_pct": 12.0, "schedule_impact_days": 20.0},
        ],
        max_cost_threshold_pct=5.0,
        max_schedule_threshold_days=10.0,
    )
    assert within_res == {
        "total_risks": 2,
        "threshold_breach_count": 0,
        "unescalated_breach_risk_ids": [],
        "unbuffered_breach_risk_ids": [],
        "is_threshold_governed": True,
        "threshold_posture": "WITHIN_RISK_APPETITE_THRESHOLDS",
    }

    governed_risks = [
        {
            "id": "RSK-HIGH",
            "status": "open",
            "cost_impact_pct": 8.5,
            "schedule_impact_days": 14.0,
            "escalation_owner": "Patrocinador Ejecutivo",
            "contingency_plan": "Activar proveedor secundario y turno extra",
            "contingency_reserve": 15000.0,
        }
    ]
    gov_res = project_lifecycle_pmi_service.audit_risk_appetite_and_threshold_governance(
        governed_risks
    )
    assert gov_res == {
        "total_risks": 1,
        "threshold_breach_count": 1,
        "unescalated_breach_risk_ids": [],
        "unbuffered_breach_risk_ids": [],
        "is_threshold_governed": True,
        "threshold_posture": "GOVERNED_THRESHOLD_ESCALATION",
    }
    assert (
        project_lifecycle_pmi_service.ProjectLifecyclePMIService.audit_risk_appetite_and_threshold_governance(
            governed_risks
        )
        == gov_res
    )


def test_audit_risk_appetite_and_threshold_governance_unescalated_breach():
    """Brecha de umbral sin dueño de escalamiento -> UNESCALATED_THRESHOLD_BREACH."""
    res = project_lifecycle_pmi_service.audit_risk_appetite_and_threshold_governance(
        [
            {
                "id": "RSK-NO-OWNER",
                "status": "open",
                "cost_impact_pct": 9.0,
                "escalation_owner": "   ",
                "contingency_plan": "Plan de contingencia documentado",
                "contingency_reserve": 5000.0,
            }
        ]
    )
    assert res["threshold_breach_count"] == 1
    assert res["unescalated_breach_risk_ids"] == ["RSK-NO-OWNER"]
    assert res["unbuffered_breach_risk_ids"] == []
    assert res["is_threshold_governed"] is False
    assert res["threshold_posture"] == "UNESCALATED_THRESHOLD_BREACH"


def test_audit_risk_appetite_and_threshold_governance_unbuffered_breach():
    """Brecha con dueño pero sin plan de contingencia o reserva <= 0 -> UNBUFFERED_CONTINGENCY_BREACH."""
    res = project_lifecycle_pmi_service.audit_risk_appetite_and_threshold_governance(
        [
            {
                "id": "RSK-NO-PLAN",
                "status": "open",
                "schedule_impact_days": 15.0,
                "owner": "Director PMO",
                "contingency_plan": "tbd",
                "contingency_reserve": 4000.0,
            },
            {
                "id": "RSK-NO-RES",
                "status": "open",
                "exceeds_appetite": True,
                "owner": "Director PMO",
                "response_plan": "Reasignar cuadrilla de infraestructura",
                "allocated_reserve": 0.0,
            },
        ]
    )
    assert res["threshold_breach_count"] == 2
    assert res["unescalated_breach_risk_ids"] == []
    assert res["unbuffered_breach_risk_ids"] == ["RSK-NO-PLAN", "RSK-NO-RES"]
    assert res["is_threshold_governed"] is False
    assert res["threshold_posture"] == "UNBUFFERED_CONTINGENCY_BREACH"


def test_audit_risk_appetite_and_threshold_governance_empty_or_none():
    """Lista vacía o None -> NO_RISKS_EVALUATED."""
    for payload in (None, [], ["invalid", 42]):
        res = project_lifecycle_pmi_service.audit_risk_appetite_and_threshold_governance(
            payload  # type: ignore[arg-type]
        )
        assert res == {
            "total_risks": 0,
            "threshold_breach_count": 0,
            "unescalated_breach_risk_ids": [],
            "unbuffered_breach_risk_ids": [],
            "is_threshold_governed": True,
            "threshold_posture": "NO_RISKS_EVALUATED",
        }


def test_audit_assumption_and_constraint_log_governance_governed():
    """> 0 entradas con dueño, criterios e invalidado vinculado -> GOVERNED log."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_assumption_and_constraint_log_governance as audit_fn,
    )

    res = audit_fn(
        [
            {
                "id": "ASM-1",
                "owner": "Oficina de Proyectos",
                "validation_method": "Verificación semanal contra métricas",
            },
            {
                "entry_id": "ASM-2",
                "validation_owner": "Coordinación Técnica",
                "verification_criteria": "Log de rendimiento < 2s por consulta",
                "state": "invalidated",
                "linked_risk_id": "RSK-7",
            },
        ]
    )
    assert res["total_entries"] == 2
    assert res["invalidated_count"] == 1
    assert res["unowned_entry_ids"] == []
    assert res["unverifiable_entry_ids"] == []
    assert res["unlinked_invalidated_ids"] == []
    assert res["is_assumption_log_governed"] is True
    assert res["assumption_log_posture"] == "GOVERNED_ASSUMPTION_LOG"


def test_audit_assumption_and_constraint_log_governance_unlinked_invalidated():
    """> Invalidado/roto sin vínculo a riesgo ni CR -> UNLINKED_INVALIDATED_ASSUMPTION."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_assumption_and_constraint_log_governance as audit_fn,
    )

    res = audit_fn(
        [
            {
                "id": "ASM-OK",
                "owner": "Oficina de Proyectos",
                "validation_method": "Revisión mensual",
            },
            {
                "id": "ASM-BROKEN",
                "owner": "Coordinación Médica",
                "verification_criteria": "Cobertura mínima 90%",
                "status": "broken",
            },
        ]
    )
    assert res["total_entries"] == 2
    assert res["invalidated_count"] == 1
    assert res["unlinked_invalidated_ids"] == ["ASM-BROKEN"]
    assert res["unowned_entry_ids"] == []
    assert res["unverifiable_entry_ids"] == []
    assert res["is_assumption_log_governed"] is False
    assert res["assumption_log_posture"] == "UNLINKED_INVALIDATED_ASSUMPTION"


def test_audit_assumption_and_constraint_log_governance_unowned_and_unverifiable():
    """> Sin dueño (precedencia) y sin criterio/fecha de validación por pilar."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_assumption_and_constraint_log_governance as audit_fn,
    )

    res = audit_fn(
        [
            {
                "id": "ASM-NOOWNER",
                "validation_method": "Auditoría trimestral",
            },
            {
                "id": "ASM-NOCRIT",
                "owner": "Consejo Pastoral",
                "status": "violated",
                "linked_cr_id": "CR-88",
            },
        ]
    )
    assert res["total_entries"] == 2
    assert res["invalidated_count"] == 1
    assert res["unowned_entry_ids"] == ["ASM-NOOWNER"]
    assert res["unverifiable_entry_ids"] == ["ASM-NOCRIT"]
    assert res["unlinked_invalidated_ids"] == []
    assert res["is_assumption_log_governed"] is False
    # Precedencia: unlinked invalidated > unowned > unverifiable.
    assert res["assumption_log_posture"] == "UNOWNED_ASSUMPTION_ENTRY"


def test_audit_assumption_and_constraint_log_governance_empty_or_none():
    """None, lista vacía o entradas no-dict -> NO_ASSUMPTIONS_LOGGED."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_assumption_and_constraint_log_governance as audit_fn,
    )

    for payload in (None, [], ["invalid", 42, None]):
        res = audit_fn(payload)  # type: ignore[arg-type]
        assert res == {
            "total_entries": 0,
            "invalidated_count": 0,
            "unowned_entry_ids": [],
            "unverifiable_entry_ids": [],
            "unlinked_invalidated_ids": [],
            "is_assumption_log_governed": True,
            "assumption_log_posture": "NO_ASSUMPTIONS_LOGGED",
        }


def test_audit_stakeholder_engagement_assessment_matrix_aligned():
    """SEAM alineada o con brecha moderada cubierta por estrategia -> ALIGNED_STAKEHOLDER_ENGAGEMENT."""
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_stakeholder_engagement_assessment_matrix,
    )

    stakeholders = [
        {
            "id": "SH-SPONSOR",
            "power": "high",
            "current_engagement": "supportive",
            "desired_engagement": "leading",
            "engagement_strategy": "Reuniones quincenales de comité ejecutivo",
        },
        {
            "stakeholder_id": "SH-LEAD",
            "influence": "medium",
            "current_level": "supportive",
            "desired_level": "supportive",
        },
    ]
    res = audit_stakeholder_engagement_assessment_matrix(stakeholders)
    assert res["total_stakeholders"] == 2
    assert res["engagement_gap_count"] == 1
    assert res["critical_resistant_stakeholder_ids"] == []
    assert res["unaddressed_gap_stakeholder_ids"] == []
    assert res["misaligned_desired_state_ids"] == []
    assert res["is_seam_governed"] is True
    assert res["seam_posture"] == "ALIGNED_STAKEHOLDER_ENGAGEMENT"
    assert (
        ProjectLifecyclePMIService.audit_stakeholder_engagement_assessment_matrix(
            stakeholders
        )["seam_posture"]
        == "ALIGNED_STAKEHOLDER_ENGAGEMENT"
    )


def test_audit_stakeholder_engagement_assessment_matrix_critical_high_power_resistance():
    """Interesado de alto poder en estado resistant o unaware -> CRITICAL_HIGH_POWER_RESISTANCE."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_stakeholder_engagement_assessment_matrix,
    )

    res = audit_stakeholder_engagement_assessment_matrix(
        [
            {
                "id": "SH-DIR",
                "power": "critical",
                "current_engagement": "resistant",
                "desired_engagement": "supportive",
                "action_plan": "Sesión de alineación estratégica",
            },
            {
                "id": "SH-FIN",
                "power": "alta",
                "current_engagement": "desconocedor",
                "desired_engagement": "partidario",
                "action_plan": "Presentación de caso de negocio",
            },
        ]
    )
    assert res["total_stakeholders"] == 2
    assert res["engagement_gap_count"] == 2
    assert res["critical_resistant_stakeholder_ids"] == ["SH-DIR", "SH-FIN"]
    assert res["unaddressed_gap_stakeholder_ids"] == []
    assert res["misaligned_desired_state_ids"] == []
    assert res["is_seam_governed"] is False
    assert res["seam_posture"] == "CRITICAL_HIGH_POWER_RESISTANCE"


def test_audit_stakeholder_engagement_assessment_matrix_unaddressed_gap_and_misaligned():
    """Brecha sin estrategia -> UNADDRESSED_ENGAGEMENT_GAP; alto poder con meta < supportive -> MISALIGNED_DESIRED_ENGAGEMENT."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_stakeholder_engagement_assessment_matrix,
    )

    res_gap = audit_stakeholder_engagement_assessment_matrix(
        [
            {
                "id": "SH-OPS",
                "power": "medium",
                "current_engagement": "neutral",
                "desired_engagement": "supportive",
                "engagement_strategy": "",
            }
        ]
    )
    assert res_gap["engagement_gap_count"] == 1
    assert res_gap["unaddressed_gap_stakeholder_ids"] == ["SH-OPS"]
    assert res_gap["is_seam_governed"] is False
    assert res_gap["seam_posture"] == "UNADDRESSED_ENGAGEMENT_GAP"

    res_mis = audit_stakeholder_engagement_assessment_matrix(
        [
            {
                "id": "SH-VP",
                "power_level": "high",
                "current_engagement": "neutral",
                "desired_engagement": "neutral",
            }
        ]
    )
    assert res_mis["engagement_gap_count"] == 0
    assert res_mis["misaligned_desired_state_ids"] == ["SH-VP"]
    assert res_mis["is_seam_governed"] is False
    assert res_mis["seam_posture"] == "MISALIGNED_DESIRED_ENGAGEMENT"


def test_audit_stakeholder_engagement_assessment_matrix_empty_or_none():
    """Lista vacía o None -> NO_STAKEHOLDERS_EVALUATED e is_seam_governed=True."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_stakeholder_engagement_assessment_matrix,
    )

    for payload in (None, [], ["invalid", 123]):
        res = audit_stakeholder_engagement_assessment_matrix(payload)  # type: ignore[arg-type]
        assert res == {
            "total_stakeholders": 0,
            "engagement_gap_count": 0,
            "critical_resistant_stakeholder_ids": [],
            "unaddressed_gap_stakeholder_ids": [],
            "misaligned_desired_state_ids": [],
            "is_seam_governed": True,
            "seam_posture": "NO_STAKEHOLDERS_EVALUATED",
        }


def test_audit_risk_residual_exposure_and_triggers_governed():
    """Riesgos activos con exposición residual < inherente, <= max_residual_emv y con trigger/owner -> GOVERNED_RESIDUAL_RISK_POSTURE."""
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_risk_residual_exposure_and_triggers,
    )

    risks = [
        {
            "id": "RSK-1",
            "status": "OPEN",
            "inherent_probability": 0.6,
            "inherent_impact": 20000.0,
            "residual_probability": 0.2,
            "residual_impact": 15000.0,
            "response_strategy": "MITIGATE",
            "trigger_condition": "Latencia p99 > 400ms sostenida por 10m",
            "risk_owner_id": "USR-SRE-1",
        },
        {
            "risk_id": "RSK-CLOSED",
            "status": "CLOSED",
            "inherent_probability": 0.9,
            "inherent_impact": 50000.0,
            "residual_probability": 0.9,
            "residual_impact": 60000.0,
        },
    ]
    res = audit_risk_residual_exposure_and_triggers(risks, max_residual_emv=5000.0)
    assert res == {
        "total_active_risks": 1,
        "total_inherent_emv": 12000.0,
        "total_residual_emv": 3000.0,
        "inverted_residual_risk_ids": [],
        "excessive_residual_risk_ids": [],
        "missing_trigger_or_owner_ids": [],
        "is_residual_governance_valid": True,
        "residual_posture": "GOVERNED_RESIDUAL_RISK_POSTURE",
    }
    assert (
        ProjectLifecyclePMIService.audit_risk_residual_exposure_and_triggers(
            risks, max_residual_emv=5000.0
        )
        == res
    )


def test_audit_risk_residual_exposure_and_triggers_inverted_residual():
    """Exposición residual > inherente -> RESIDUAL_EXCEEDS_INHERENT_EXPOSURE."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_risk_residual_exposure_and_triggers,
    )

    res = audit_risk_residual_exposure_and_triggers(
        [
            {
                "id": "RSK-INV",
                "status": "ACTIVE",
                "inherent_probability": 0.2,
                "inherent_impact": 10000.0,
                "residual_probability": 0.5,
                "residual_impact": 10000.0,
                "response_strategy": "MITIGATE",
                "trigger_condition": "Falla primaria",
                "risk_owner_id": "USR-1",
            }
        ],
        max_residual_emv=6000.0,
    )
    assert res["inverted_residual_risk_ids"] == ["RSK-INV"]
    assert res["is_residual_governance_valid"] is False
    assert res["residual_posture"] == "RESIDUAL_EXCEEDS_INHERENT_EXPOSURE"


def test_audit_risk_residual_exposure_and_triggers_excessive_and_missing_trigger():
    """Exposición residual > umbral -> EXCESSIVE_RESIDUAL_EXPOSURE; falta trigger/owner -> MISSING_RISK_TRIGGER_OR_OWNER."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_risk_residual_exposure_and_triggers,
    )

    res_exc = audit_risk_residual_exposure_and_triggers(
        [
            {
                "id": "RSK-HIGH",
                "status": "MITIGATING",
                "inherent_probability": 0.8,
                "inherent_impact": 20000.0,
                "residual_probability": 0.5,
                "residual_impact": 15000.0,
                "response_strategy": "CONTINGENCY",
                "trigger_condition": "Retraso aduanero > 5 días",
                "risk_owner_id": "USR-LOG",
            }
        ],
        max_residual_emv=5000.0,
    )
    assert res_exc["excessive_residual_risk_ids"] == ["RSK-HIGH"]
    assert res_exc["is_residual_governance_valid"] is False
    assert res_exc["residual_posture"] == "EXCESSIVE_RESIDUAL_EXPOSURE"

    res_trig = audit_risk_residual_exposure_and_triggers(
        [
            {
                "id": "RSK-NOTRIG",
                "status": "OPEN",
                "inherent_probability": 0.5,
                "inherent_impact": 8000.0,
                "residual_probability": 0.2,
                "residual_impact": 8000.0,
                "response_strategy": "FALLBACK",
                "trigger_condition": "",
                "risk_owner_id": "USR-1",
            }
        ],
        max_residual_emv=5000.0,
    )
    assert res_trig["missing_trigger_or_owner_ids"] == ["RSK-NOTRIG"]
    assert res_trig["is_residual_governance_valid"] is False
    assert res_trig["residual_posture"] == "MISSING_RISK_TRIGGER_OR_OWNER"


def test_audit_risk_residual_exposure_and_triggers_no_active_risks():
    """Lista vacía, None o sin riesgos activos -> NO_ACTIVE_RISKS."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_risk_residual_exposure_and_triggers,
    )

    for payload in (None, [], [{"id": "RSK-1", "status": "CLOSED"}]):
        res = audit_risk_residual_exposure_and_triggers(payload)
        assert res == {
            "total_active_risks": 0,
            "total_inherent_emv": 0.0,
            "total_residual_emv": 0.0,
            "inverted_residual_risk_ids": [],
            "excessive_residual_risk_ids": [],
            "missing_trigger_or_owner_ids": [],
            "is_residual_governance_valid": False,
            "residual_posture": "NO_ACTIVE_RISKS",
        }


def test_audit_charter_funding_limit_reconciliation_reconciled():
    """Periodos dentro de su límite y suma <= presupuesto del Acta -> RECONCILED_FUNDING_SCHEDULE."""
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_charter_funding_limit_reconciliation,
    )

    periods = [
        {"period_id": "2026-Q1", "planned_outlay": 30000.0, "funding_limit": 35000.0},
        {"id": "2026-Q2", "planned_outlay": 45000.0, "funding_limit": 50000.0},
        {"period_id": "2026-Q3", "planned_outlay": 20000.0, "funding_limit": 25000.0},
    ]
    res = audit_charter_funding_limit_reconciliation(
        periods, charter_authorized_budget=100000.0
    )
    assert res == {
        "total_periods": 3,
        "total_planned_outlay": 95000.0,
        "charter_authorized_budget": 100000.0,
        "unallocated_charter_margin": 5000.0,
        "period_cap_breach_ids": [],
        "exceeds_charter_budget": False,
        "is_funding_reconciled": True,
        "funding_posture": "RECONCILED_FUNDING_SCHEDULE",
    }
    assert (
        ProjectLifecyclePMIService.audit_charter_funding_limit_reconciliation(
            periods, charter_authorized_budget=100000.0
        )
        == res
    )


def test_audit_charter_funding_limit_reconciliation_charter_ceiling_exceeded():
    """Suma planificada supera presupuesto autorizado del Acta -> CHARTER_BUDGET_CEILING_EXCEEDED."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_charter_funding_limit_reconciliation,
    )

    res = audit_charter_funding_limit_reconciliation(
        [
            {"period_id": "2026-Q1", "planned_outlay": 60000.0, "funding_limit": 70000.0},
            {"period_id": "2026-Q2", "planned_outlay": 55000.0, "funding_limit": 60000.0},
        ],
        charter_authorized_budget=100000.0,
    )
    assert res["total_periods"] == 2
    assert res["total_planned_outlay"] == 115000.0
    assert res["unallocated_charter_margin"] == -15000.0
    assert res["exceeds_charter_budget"] is True
    assert res["is_funding_reconciled"] is False
    assert res["funding_posture"] == "CHARTER_BUDGET_CEILING_EXCEEDED"


def test_audit_charter_funding_limit_reconciliation_period_cap_breach():
    """Desembolso trimestral supera límite del periodo pero total <= presupuesto Acta -> PERIOD_FUNDING_LIMIT_BREACH."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_charter_funding_limit_reconciliation,
    )

    res = audit_charter_funding_limit_reconciliation(
        [
            {"period_id": "2026-Q1", "planned_outlay": 42000.0, "funding_limit": 35000.0},
            {"period_id": "2026-Q2", "planned_outlay": 30000.0, "funding_limit": 40000.0},
        ],
        charter_authorized_budget=100000.0,
    )
    assert res["period_cap_breach_ids"] == ["2026-Q1"]
    assert res["exceeds_charter_budget"] is False
    assert res["is_funding_reconciled"] is False
    assert res["funding_posture"] == "PERIOD_FUNDING_LIMIT_BREACH"


def test_audit_charter_funding_limit_reconciliation_no_schedule_or_zero_budget():
    """Sin periodos o presupuesto autorizado <= 0 -> NO_FUNDING_SCHEDULE_DEFINED."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_charter_funding_limit_reconciliation,
    )

    res_empty = audit_charter_funding_limit_reconciliation(
        None, charter_authorized_budget=50000.0
    )
    assert res_empty == {
        "total_periods": 0,
        "total_planned_outlay": 0.0,
        "charter_authorized_budget": 50000.0,
        "unallocated_charter_margin": 50000.0,
        "period_cap_breach_ids": [],
        "exceeds_charter_budget": False,
        "is_funding_reconciled": False,
        "funding_posture": "NO_FUNDING_SCHEDULE_DEFINED",
    }

    res_zero_budget = audit_charter_funding_limit_reconciliation(
        [{"period_id": "2026-Q1", "planned_outlay": 10000.0, "funding_limit": 15000.0}],
        charter_authorized_budget=0.0,
    )
    assert res_zero_budget["is_funding_reconciled"] is False
    assert res_zero_budget["funding_posture"] == "NO_FUNDING_SCHEDULE_DEFINED"


def test_audit_lessons_learned_actionable_followup_governed():
    """Recomendaciones accionables, HIGH con dueño y cierres institucionalizados -> GOVERNED."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_lessons_learned_actionable_followup as audit_fn,
    )

    res = audit_fn(
        [
            {
                "id": "LL-1",
                "impact_level": "high",
                "recommendation": "Duplicar la cobertura de retención en horarios nocturnos",
                "action_owner_id": "USR-12",
                "status": "OPEN",
            },
            {
                "lesson_id": "LL-2",
                "recommendation": "Documentar el flujo de salas por sede",
                "opa_updated": True,
                "status": "INSTITUTIONALIZED",
            },
            {
                "id": "LL-3",
                "impact_level": "LOW",
                "recommendation": "Refrescar los enlaces de la wiki",
                "status": "CLOSED",
                "opa_updated": True,
            },
        ]
    )
    assert res["total_lessons"] == 3
    assert res["missing_recommendation_ids"] == []
    assert res["unassigned_high_impact_ids"] == []
    assert res["uninstitutionalized_closed_ids"] == []
    assert res["is_lessons_followup_governed"] is True
    assert res["lessons_followup_posture"] == "GOVERNED_LESSONS_FOLLOWUP"


def test_audit_lessons_learned_actionable_followup_uninstitutionalized_closure():
    """Cierro/INSTITUTIONALIZED sin OPA actualizada -> UNINSTITUTIONALIZED_OPA_CLOSURE."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_lessons_learned_actionable_followup as audit_fn,
    )

    res = audit_fn(
        [
            {
                "id": "LL-OK",
                "impact_level": "MEDIUM",
                "recommendation": "Estandarizar el checklist de despliegues",
                "opa_updated": True,
                "status": "ARCHIVED",
            },
            {
                "id": "LL-BAD",
                "impact_level": "CRITICAL",
                "recommendation": "Añadir respaldo ante caídas de stream",
                "action_owner_id": "USR-7",
                "status": "CLOSED",
            },
        ]
    )
    assert res["total_lessons"] == 2
    assert res["uninstitutionalized_closed_ids"] == ["LL-BAD"]
    assert res["missing_recommendation_ids"] == []
    assert res["unassigned_high_impact_ids"] == []
    assert res["is_lessons_followup_governed"] is False
    assert res["lessons_followup_posture"] == "UNINSTITUTIONALIZED_OPA_CLOSURE"


def test_audit_lessons_learned_actionable_followup_high_unassigned_and_missing_rec():
    """> HIGH sin dueño (precedencia) y lección sin recomendación por pilar."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_lessons_learned_actionable_followup as audit_fn,
    )

    res = audit_fn(
        [
            {
                "id": "LL-HIGH",
                "impact_level": "HIGH",
                "recommendation": "Activar voluntariado de apoyo en navidad",
                "status": "OPEN",
            },
            {
                "id": "LL-NOREC",
                "impact_level": "LOW",
                "status": "OPEN",
            },
        ]
    )
    assert res["total_lessons"] == 2
    assert res["unassigned_high_impact_ids"] == ["LL-HIGH"]
    assert res["missing_recommendation_ids"] == ["LL-NOREC"]
    assert res["uninstitutionalized_closed_ids"] == []
    assert res["is_lessons_followup_governed"] is False
    # Precedencia: uninstitutionalized > unassigned high > missing recommendation.
    assert res["lessons_followup_posture"] == "UNASSIGNED_HIGH_IMPACT_LESSON"


def test_audit_lessons_learned_actionable_followup_empty_or_none():
    """None, lista vacía, registros no-dict o sin lesson_id -> NO_LESSONS_RECORDED."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_lessons_learned_actionable_followup as audit_fn,
    )

    for payload in (None, [], ["invalid", 42, {"status": "OPEN"}]):
        res = audit_fn(payload)  # type: ignore[arg-type]
        assert res == {
            "total_lessons": 0,
            "missing_recommendation_ids": [],
            "unassigned_high_impact_ids": [],
            "uninstitutionalized_closed_ids": [],
            "is_lessons_followup_governed": False,
            "lessons_followup_posture": "NO_LESSONS_RECORDED",
        }


def test_audit_team_tuckman_and_skill_redundancy_resilient():
    """Habilidades críticas con >= 2 integrantes capacitados, etapa válida y 0 conflictos -> RESILIENT_CROSS_TRAINED_TEAM."""
    import backend.services.project_lifecycle_pmi_service as lifecycle_module
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_team_tuckman_and_skill_redundancy,
    )

    skills = [
        {"skill_id": "SKL-POSTGRES", "qualified_members_count": 3},
        {"id": "SKL-NEXTJS", "qualified_member_ids": ["USR-1", "USR-2"]},
    ]
    res = audit_team_tuckman_and_skill_redundancy(
        skills,
        tuckman_stage="performing",
        unresolved_team_conflicts=0,
        min_qualified_members=2,
    )
    assert res == {
        "total_critical_skills": 2,
        "tuckman_stage": "PERFORMING",
        "unresolved_team_conflicts": 0,
        "spof_skill_ids": [],
        "is_team_resilient": True,
        "team_posture": "RESILIENT_CROSS_TRAINED_TEAM",
    }
    assert (
        ProjectLifecyclePMIService.audit_team_tuckman_and_skill_redundancy(
            skills,
            tuckman_stage="performing",
            unresolved_team_conflicts=0,
            min_qualified_members=2,
        )
        == res
    )
    assert "audit_team_tuckman_and_skill_redundancy" in lifecycle_module.__all__


def test_audit_team_tuckman_and_skill_redundancy_spof_and_conflicts():
    """Competencia con 1 solo miembro -> SINGLE_POINT_OF_FAILURE_SKILL_GAP; conflictos abiertos -> UNRESOLVED_TEAM_CONFLICT_ESCALATION."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_team_tuckman_and_skill_redundancy,
    )

    res_spof = audit_team_tuckman_and_skill_redundancy(
        [
            {"skill_id": "SKL-K8S", "qualified_members_count": 1},
            {"skill_id": "SKL-FASTAPI", "qualified_members_count": 2},
        ],
        tuckman_stage="NORMING",
        unresolved_team_conflicts=2,
    )
    assert res_spof["spof_skill_ids"] == ["SKL-K8S"]
    assert res_spof["is_team_resilient"] is False
    assert res_spof["team_posture"] == "SINGLE_POINT_OF_FAILURE_SKILL_GAP"

    res_conflict = audit_team_tuckman_and_skill_redundancy(
        [{"skill_id": "SKL-FASTAPI", "qualified_members_count": 2}],
        tuckman_stage="STORMING",
        unresolved_team_conflicts=3,
    )
    assert res_conflict["spof_skill_ids"] == []
    assert res_conflict["unresolved_team_conflicts"] == 3
    assert res_conflict["is_team_resilient"] is False
    assert res_conflict["team_posture"] == "UNRESOLVED_TEAM_CONFLICT_ESCALATION"


def test_audit_team_tuckman_and_skill_redundancy_invalid_stage():
    """Etapa fuera del modelo de Tuckman -> INVALID_TUCKMAN_STAGE."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_team_tuckman_and_skill_redundancy,
    )

    res = audit_team_tuckman_and_skill_redundancy(
        [{"skill_id": "SKL-DB", "qualified_members_count": 3}],
        tuckman_stage="CHAOTIC_STAGE",
        unresolved_team_conflicts=0,
    )
    assert res["tuckman_stage"] == "CHAOTIC_STAGE"
    assert res["is_team_resilient"] is False
    assert res["team_posture"] == "INVALID_TUCKMAN_STAGE"


def test_audit_team_tuckman_and_skill_redundancy_no_skills():
    """Sin habilidades críticas mapeadas -> NO_CRITICAL_SKILLS_MAPPED."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_team_tuckman_and_skill_redundancy,
    )

    for payload in (None, [], [{"skill_id": ""}]):
        res = audit_team_tuckman_and_skill_redundancy(payload)
        assert res == {
            "total_critical_skills": 0,
            "tuckman_stage": "FORMING",
            "unresolved_team_conflicts": 0,
            "spof_skill_ids": [],
            "is_team_resilient": False,
            "team_posture": "NO_CRITICAL_SKILLS_MAPPED",
        }



def test_audit_stakeholder_escalation_matrix_readiness_ready():
    """> Matriz completa con Tier 1, dueños/SPOF, SLA y canales correctos -> is_ready."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_stakeholder_escalation_matrix_readiness as audit_fn,
    )

    res = audit_fn(
        [
            {
                "tier_level": 1,
                "primary_owner_id": "u-lead",
                "backup_owner_id": "u-backup",
                "max_response_hours": 4.0,
                "notification_channels": ["correo", "sms"],
            },
            {
                "tier_level": 2,
                "primary_owner_id": "u-mgr",
                "backup_owner_id": "u-lead",
                "max_response_hours": 24,
                "notification_channels": ["correo"],
            },
        ]
    )
    assert res["evaluated_tier_count"] == 2
    assert res["has_tier_1"] is True
    assert res["missing_primary_owner_tiers"] == []
    assert res["single_point_of_failure_tiers"] == []
    assert res["invalid_sla_tiers"] == []
    assert res["unconfigured_channel_tiers"] == []
    assert res["readiness_score_pct"] == 100.0
    assert res["is_ready"] is True


def test_audit_stakeholder_escalation_matrix_readiness_missing_owner_and_spof():
    """> Dueño primario ausente y backup vacío/igual al primario -> SPOF."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_stakeholder_escalation_matrix_readiness as audit_fn,
    )

    res = audit_fn(
        [
            {
                "tier_level": 1,
                "primary_owner_id": "  ",
                "backup_owner_id": "u-backup",
                "max_response_hours": 2.0,
                "notification_channels": ["correo"],
            },
            {
                "tier_level": 2,
                "primary_owner_id": "u-mgr",
                "backup_owner_id": "",
                "max_response_hours": 24.0,
                "notification_channels": ["correo"],
            },
            {
                "tier_level": 3,
                "primary_owner_id": "u-dir",
                "backup_owner_id": "u-dir",
                "max_response_hours": 48.0,
                "notification_channels": ["correo"],
            },
        ]
    )
    assert res["evaluated_tier_count"] == 3
    assert res["missing_primary_owner_tiers"] == [1]
    assert res["single_point_of_failure_tiers"] == [2, 3]
    assert res["invalid_sla_tiers"] == []
    assert res["unconfigured_channel_tiers"] == []
    assert res["readiness_score_pct"] == 0.0
    assert res["is_ready"] is False


def test_audit_stakeholder_escalation_matrix_readiness_tier1_sla_violation():
    """> Tier 1 con SLA arriba del tope configurable (default 4.0h) -> invalid_sla."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_stakeholder_escalation_matrix_readiness as audit_fn,
    )

    res = audit_fn(
        [
            {
                "tier_level": 1,
                "primary_owner_id": "u-lead",
                "backup_owner_id": "u-backup",
                "max_response_hours": 6.0,
                "notification_channels": ["correo"],
            },
            {
                "tier_level": 2,
                "primary_owner_id": "u-mgr",
                "backup_owner_id": "u-lead",
                "max_response_hours": 0.0,
                "notification_channels": ["correo"],
            },
        ]
    )
    assert res["evaluated_tier_count"] == 2
    assert res["invalid_sla_tiers"] == [1, 2]
    assert res["is_ready"] is False

    # Con tope ampliado, el mismo Tier 1 queda conforme pero Tier 2 sigue roto.
    res_relaxed = audit_fn(
        [
            {
                "tier_level": 1,
                "primary_owner_id": "u-lead",
                "backup_owner_id": "u-backup",
                "max_response_hours": 6.0,
                "notification_channels": ["correo"],
            },
        ],
        max_tier1_response_hours=6.0,
    )
    assert res_relaxed["invalid_sla_tiers"] == []
    assert res_relaxed["readiness_score_pct"] == 100.0
    assert res_relaxed["is_ready"] is True


def test_audit_stakeholder_escalation_matrix_readiness_channels_or_missing_tier1():
    """> Sin canales configurados o sin Tier 1 en la matriz -> is_ready False."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_stakeholder_escalation_matrix_readiness as audit_fn,
    )

    res_no_channels = audit_fn(
        [
            {
                "tier_level": 1,
                "primary_owner_id": "u-lead",
                "backup_owner_id": "u-backup",
                "max_response_hours": 4.0,
                "notification_channels": ["  ", None],
            },
        ]
    )
    assert res_no_channels["unconfigured_channel_tiers"] == [1]
    assert res_no_channels["is_ready"] is False

    res_no_tier1 = audit_fn(
        [
            {
                "tier_level": 2,
                "primary_owner_id": "u-mgr",
                "backup_owner_id": "u-lead",
                "max_response_hours": 24.0,
                "notification_channels": ["correo"],
            },
            "invalid-entry",
            {"tier_level": 0},
        ]
    )
    assert res_no_tier1["evaluated_tier_count"] == 1
    assert res_no_tier1["has_tier_1"] is False
    assert res_no_tier1["is_ready"] is False

    for payload in (None, [], [None, 42]):
        assert audit_fn(payload) == {  # type: ignore[arg-type]
            "evaluated_tier_count": 0,
            "has_tier_1": False,
            "missing_primary_owner_tiers": [],
            "single_point_of_failure_tiers": [],
            "invalid_sla_tiers": [],
            "unconfigured_channel_tiers": [],
            "readiness_score_pct": 0.0,
            "is_ready": False,
        }


def test_audit_team_calendar_burnout_contention_sustainable():
    """Integrantes con utilización <= 85%, proyectos concurrentes <= 3 y 0 conflictos PTO -> is_sustainable True."""
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_team_calendar_burnout_contention,
    )

    allocations = [
        {
            "member_id": "MEM-1",
            "available_hours": 40.0,
            "allocated_hours": 32.0,
            "concurrent_project_count": 2,
            "pto_conflict_hours": 0.0,
        },
        {
            "member_id": "MEM-2",
            "available_hours": 40.0,
            "allocated_hours": 28.0,
            "concurrent_project_count": 3,
            "pto_conflict_hours": 0.0,
        },
    ]
    res = audit_team_calendar_burnout_contention(allocations)
    assert res == {
        "evaluated_member_count": 2,
        "burnout_risk_member_ids": [],
        "context_switching_member_ids": [],
        "pto_conflict_member_ids": [],
        "invalid_calendar_member_ids": [],
        "average_utilization_pct": 75.0,
        "is_sustainable": True,
    }
    assert (
        ProjectLifecyclePMIService.audit_team_calendar_burnout_contention(
            allocations
        )
        == res
    )


def test_audit_team_calendar_burnout_contention_burnout_context_and_pto():
    """Utilización > 85%, proyectos > 3 y horas PTO > 0 -> listas de problemas pobladas e is_sustainable False."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_team_calendar_burnout_contention,
    )

    res = audit_team_calendar_burnout_contention(
        [
            {
                "member_id": "MEM-BURN",
                "available_hours": 40.0,
                "allocated_hours": 38.0,
                "concurrent_project_count": 2,
                "pto_conflict_hours": 0.0,
            },
            {
                "member_id": "MEM-CTX-PTO",
                "available_hours": 40.0,
                "allocated_hours": 30.0,
                "concurrent_project_count": 5,
                "pto_conflict_hours": 8.0,
            },
        ],
        max_sustainable_utilization_pct=85.0,
        max_concurrent_projects=3,
    )
    assert res == {
        "evaluated_member_count": 2,
        "burnout_risk_member_ids": ["MEM-BURN"],
        "context_switching_member_ids": ["MEM-CTX-PTO"],
        "pto_conflict_member_ids": ["MEM-CTX-PTO"],
        "invalid_calendar_member_ids": [],
        "average_utilization_pct": 85.0,
        "is_sustainable": False,
    }


def test_audit_team_calendar_burnout_contention_invalid_calendar():
    """available_hours <= 0 o allocated_hours < 0 -> invalid_calendar_member_ids poblado."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_team_calendar_burnout_contention,
    )

    res = audit_team_calendar_burnout_contention(
        [
            {"member_id": "MEM-ZERO-AVAIL", "available_hours": 0.0, "allocated_hours": 20.0},
            {"member_id": "MEM-NEG-ALLOC", "available_hours": 40.0, "allocated_hours": -5.0},
            {"member_id": "MEM-OK", "available_hours": 40.0, "allocated_hours": 20.0},
        ]
    )
    assert res["evaluated_member_count"] == 3
    assert res["invalid_calendar_member_ids"] == ["MEM-ZERO-AVAIL", "MEM-NEG-ALLOC"]
    assert res["average_utilization_pct"] == 50.0
    assert res["is_sustainable"] is False


def test_audit_team_calendar_burnout_contention_empty_or_none():
    """Lista vacía, None o entradas sin member_id -> evaluated_member_count 0, is_sustainable False."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_team_calendar_burnout_contention,
    )

    for payload in (None, [], [{"member_id": "  "}], ["invalid"]):
        res = audit_team_calendar_burnout_contention(payload)  # type: ignore[arg-type]
        assert res == {
            "evaluated_member_count": 0,
            "burnout_risk_member_ids": [],
            "context_switching_member_ids": [],
            "pto_conflict_member_ids": [],
            "invalid_calendar_member_ids": [],
            "average_utilization_pct": 0.0,
            "is_sustainable": False,
        }


def test_audit_charter_assumption_log_validity_compliant():
    """Supuestos y restricciones con dueño, validados/en plazo o invalidados convertidos en riesgo -> is_valid True."""
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_charter_assumption_log_validity,
    )

    entries = [
        {
            "entry_id": "ASM-01",
            "entry_type": "Assumption",
            "owner_id": "USR-PM",
            "validation_status": "unvalidated",
            "days_until_validation_due": 10,
        },
        {
            "entry_id": "ASM-02",
            "entry_type": "assumption",
            "owner_id": "USR-ARCH",
            "validation_status": "Invalidated",
            "days_until_validation_due": -5,
            "converted_risk_id": "RSK-104",
        },
        {
            "entry_id": "CON-01",
            "entry_type": "CONSTRAINT",
            "owner_id": "USR-FIN",
            "validation_status": "validated",
        },
    ]
    res = audit_charter_assumption_log_validity(entries)
    assert res == {
        "evaluated_entry_count": 3,
        "unowned_entry_ids": [],
        "overdue_unvalidated_assumption_ids": [],
        "unconverted_invalidated_assumption_ids": [],
        "invalid_entry_ids": [],
        "is_valid": True,
    }
    assert ProjectLifecyclePMIService.audit_charter_assumption_log_validity(entries) == res


def test_audit_charter_assumption_log_validity_unowned_overdue_and_unconverted():
    """Detecta registros sin owner_id, supuestos no validados vencidos e invalidados sin riesgo vinculado."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_charter_assumption_log_validity,
    )

    res = audit_charter_assumption_log_validity(
        [
            {
                "entry_id": "ASM-UNOWNED-OVERDUE",
                "entry_type": "assumption",
                "owner_id": "   ",
                "validation_status": "unvalidated",
                "days_until_validation_due": -3,
            },
            {
                "entry_id": "ASM-INVALIDATED-NO-RISK",
                "entry_type": "assumption",
                "owner_id": "USR-1",
                "validation_status": "invalidated",
                "converted_risk_id": "",
            },
        ]
    )
    assert res == {
        "evaluated_entry_count": 2,
        "unowned_entry_ids": ["ASM-UNOWNED-OVERDUE"],
        "overdue_unvalidated_assumption_ids": ["ASM-UNOWNED-OVERDUE"],
        "unconverted_invalidated_assumption_ids": ["ASM-INVALIDATED-NO-RISK"],
        "invalid_entry_ids": [],
        "is_valid": False,
    }


def test_audit_charter_assumption_log_validity_invalid_type_or_status():
    """Tipos o estados fuera del catálogo se reportan en invalid_entry_ids."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_charter_assumption_log_validity,
    )

    res = audit_charter_assumption_log_validity(
        [
            {
                "entry_id": "ENT-BAD-TYPE",
                "entry_type": "dependency",
                "owner_id": "USR-1",
                "validation_status": "validated",
            },
            {
                "entry_id": "ENT-BAD-STATUS",
                "entry_type": "constraint",
                "owner_id": "USR-1",
                "validation_status": "pending_review",
            },
        ]
    )
    assert res == {
        "evaluated_entry_count": 2,
        "unowned_entry_ids": [],
        "overdue_unvalidated_assumption_ids": [],
        "unconverted_invalidated_assumption_ids": [],
        "invalid_entry_ids": ["ENT-BAD-TYPE", "ENT-BAD-STATUS"],
        "is_valid": False,
    }


def test_audit_charter_assumption_log_validity_empty_or_none():
    """Lista vacía, None o entradas sin entry_id -> evaluated_entry_count 0, is_valid False."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_charter_assumption_log_validity,
    )

    for payload in (None, [], [{"entry_id": "  "}], ["invalid"]):
        assert audit_charter_assumption_log_validity(payload) == {  # type: ignore[arg-type]
            "evaluated_entry_count": 0,
            "unowned_entry_ids": [],
            "overdue_unvalidated_assumption_ids": [],
            "unconverted_invalidated_assumption_ids": [],
            "invalid_entry_ids": [],
            "is_valid": False,
        }


def test_audit_project_closure_handover_and_release_readiness_all_gates_passed():
    """Paquete de cierre completo con los 6 criterios cumplidos retorna 100% e is_ready_for_administrative_closure=True."""
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_project_closure_handover_and_release_readiness,
    )

    pkg = {
        "final_acceptance_signed": True,
        "open_claims_count": 0,
        "unreleased_retention_amount": 0.0,
        "operations_handover_accepted": True,
        "resources_released_pct": 100.0,
        "final_report_archived": True,
    }
    res = audit_project_closure_handover_and_release_readiness(pkg)
    assert res == {
        "open_claims_count": 0,
        "unreleased_retention_amount": 0.0,
        "resources_released_pct": 100.0,
        "blocking_gates": [],
        "closure_readiness_pct": 100.0,
        "is_ready_for_administrative_closure": True,
    }
    assert (
        ProjectLifecyclePMIService.audit_project_closure_handover_and_release_readiness(
            pkg
        )
        == res
    )


def test_audit_project_closure_handover_and_release_readiness_procurement_blockers():
    """Detecta reclamos abiertos y retención financiera pendiente de liberación."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_project_closure_handover_and_release_readiness,
    )

    res = audit_project_closure_handover_and_release_readiness(
        {
            "final_acceptance_signed": True,
            "open_claims_count": 2,
            "unreleased_retention_amount": 15000.5,
            "operations_handover_accepted": True,
            "resources_released_pct": 100.0,
            "final_report_archived": True,
        }
    )
    assert res == {
        "open_claims_count": 2,
        "unreleased_retention_amount": 15000.5,
        "resources_released_pct": 100.0,
        "blocking_gates": [
            "unresolved_procurement_claims",
            "unreleased_financial_retention",
        ],
        "closure_readiness_pct": 66.67,
        "is_ready_for_administrative_closure": False,
    }


def test_audit_project_closure_handover_and_release_readiness_handover_and_release_blockers():
    """Detecta falta de transferencia a operaciones, liberación parcial de equipo y reporte final sin archivar."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_project_closure_handover_and_release_readiness,
    )

    res = audit_project_closure_handover_and_release_readiness(
        {
            "final_acceptance_signed": True,
            "open_claims_count": 0,
            "unreleased_retention_amount": 0.0,
            "operations_handover_accepted": False,
            "resources_released_pct": 75.0,
            "final_report_archived": False,
        }
    )
    assert res == {
        "open_claims_count": 0,
        "unreleased_retention_amount": 0.0,
        "resources_released_pct": 75.0,
        "blocking_gates": [
            "pending_operations_handover",
            "incomplete_team_resource_release",
            "unarchived_final_project_report",
        ],
        "closure_readiness_pct": 50.0,
        "is_ready_for_administrative_closure": False,
    }


def test_audit_project_closure_handover_and_release_readiness_empty_or_none():
    """Diccionario vacío o None activa las 4 compuertas booleanas/porcentuales faltantes."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_project_closure_handover_and_release_readiness,
    )

    for payload in (None, {}, "invalid"):
        assert audit_project_closure_handover_and_release_readiness(payload) == {  # type: ignore[arg-type]
            "open_claims_count": 0,
            "unreleased_retention_amount": 0.0,
            "resources_released_pct": 0.0,
            "blocking_gates": [
                "missing_final_acceptance_signoff",
                "pending_operations_handover",
                "incomplete_team_resource_release",
                "unarchived_final_project_report",
            ],
            "closure_readiness_pct": 33.33,
            "is_ready_for_administrative_closure": False,
        }




def test_audit_stakeholder_salience_mitchell_classification_ready():
    """> Definitivos (3/3) y expectantes (1 atributo) con plan -> ready + staticmethod."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_stakeholder_salience_mitchell_classification,
        ProjectLifecyclePMIService,
    )

    res = audit_stakeholder_salience_mitchell_classification(
        [
            {
                "stakeholder_id": "STK-DEF",
                "has_power": True,
                "has_urgency": True,
                "has_legitimacy": True,
                "engagement_plan": "gobernanza conjunto con el sponsor",
            },
            {
                "stakeholder_id": "STK-DEMAND",
                "has_urgency": True,
                "engagement_plan": "seguimiento semanal",
            },
            {
                "stakeholder_id": "STK-DORMANT",
                "has_power": True,
                "engagement_plan": "informe trimestral",
            },
        ]
    )
    assert res["total_stakeholders"] == 3
    assert res["definitive_stakeholder_ids"] == ["STK-DEF"]
    assert res["dangerous_stakeholder_ids"] == []
    assert res["non_stakeholder_ids"] == []
    assert res["unmanaged_high_salience_ids"] == []
    assert res["is_salience_governance_ready"] is True

    static_res = ProjectLifecyclePMIService.audit_stakeholder_salience_mitchell_classification(
        [
            {
                "stakeholder_id": "STK-DEF",
                "has_power": True,
                "has_urgency": True,
                "has_legitimacy": True,
                "engagement_plan": "plan",
            },
        ]
    )
    assert static_res["is_salience_governance_ready"] is True


def test_audit_stakeholder_salience_mitchell_classification_dangerous_and_unmanaged():
    """> Peligrosos (poder+urgencia sin legitimidad) y >=2 atributos sin plan."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_stakeholder_salience_mitchell_classification,
    )

    res = audit_stakeholder_salience_mitchell_classification(
        [
            {
                "stakeholder_id": "STK-DANGEROUS",
                "has_power": True,
                "has_urgency": True,
            },
            {
                "stakeholder_id": "STK-DEF-Noplan",
                "has_power": True,
                "has_urgency": True,
                "has_legitimacy": True,
            },
            {
                "stakeholder_id": "STK-DEPENDABLE-PLAN",
                "has_power": True,
                "has_urgency": True,
                "engagement_plan": "  ",
            },
        ]
    )
    assert res["total_stakeholders"] == 3
    # Ambas sin legitimidad y con plan en blanco son peligrosas (literal del spec).
    assert res["dangerous_stakeholder_ids"] == ["STK-DANGEROUS", "STK-DEPENDABLE-PLAN"]
    assert res["definitive_stakeholder_ids"] == ["STK-DEF-Noplan"]
    assert res["unmanaged_high_salience_ids"] == [
        "STK-DANGEROUS",
        "STK-DEF-Noplan",
        "STK-DEPENDABLE-PLAN",
    ]
    assert res["is_salience_governance_ready"] is False


def test_audit_stakeholder_salience_mitchell_classification_non_stakeholders():
    """> 0 atributos -> non_stakeholder (ready False); 1 atributo no es non-stakeholder."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_stakeholder_salience_mitchell_classification,
    )

    res = audit_stakeholder_salience_mitchell_classification(
        [
            {"stakeholder_id": "STK-GHOST"},
            {
                "stakeholder_id": "STK-ONLY-LEGIT",
                "has_legitimacy": True,
                "engagement_plan": "bajo perfil",
            },
            {
                "stakeholder_id": "STK-NONE-PLAN",
                "engagement_plan": "doc sin atributos",
            },
        ]
    )
    assert res["total_stakeholders"] == 3
    assert res["non_stakeholder_ids"] == ["STK-GHOST", "STK-NONE-PLAN"]
    assert res["unmanaged_high_salience_ids"] == []
    assert res["is_salience_governance_ready"] is False


def test_audit_stakeholder_salience_mitchell_classification_empty_or_none():
    """None, no-secuencia, str, Mapping, 42 o basura -> 0 interesados."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_stakeholder_salience_mitchell_classification,
    )

    empty_result = {
        "total_stakeholders": 0,
        "definitive_stakeholder_ids": [],
        "dangerous_stakeholder_ids": [],
        "non_stakeholder_ids": [],
        "unmanaged_high_salience_ids": [],
        "is_salience_governance_ready": False,
    }

    for payload in (
        None,
        "stakeholders-string",
        {"stakeholder_id": "X"},
        42,
        [],
        ["no-dict", {"has_power": True}],
        [{"stakeholder_id": "   "}],
    ):
        assert audit_stakeholder_salience_mitchell_classification(payload) == empty_result  # type: ignore[arg-type]


def test_audit_business_case_financial_viability_governance_viable():
    """NPV > 0, IRR >= hurdle_rate > 0, BCR >= 1.0 y 0 < payback <= max_payback -> viable."""
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_business_case_financial_viability_governance,
    )

    bc = {
        "npv": 150000.0,
        "irr_pct": 18.5,
        "hurdle_rate_pct": 12.0,
        "bcr": 1.45,
        "payback_months": 18.0,
        "max_payback_months": 24.0,
    }
    res = audit_business_case_financial_viability_governance(bc)
    assert res == {
        "npv": 150000.0,
        "irr_pct": 18.5,
        "hurdle_rate_pct": 12.0,
        "bcr": 1.45,
        "payback_months": 18.0,
        "viability_breaches": [],
        "is_financially_viable": True,
    }
    assert (
        ProjectLifecyclePMIService.audit_business_case_financial_viability_governance(
            bc
        )
        == res
    )


def test_audit_business_case_financial_viability_governance_npv_and_irr_breaches():
    """NPV <= 0 e IRR < hurdle_rate_pct se reportan en orden canónico."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_business_case_financial_viability_governance,
    )

    res = audit_business_case_financial_viability_governance(
        {
            "npv": -5000.0,
            "irr_pct": 8.0,
            "hurdle_rate_pct": 12.0,
            "bcr": 1.2,
            "payback_months": 12.0,
            "max_payback_months": 24.0,
        }
    )
    assert res == {
        "npv": -5000.0,
        "irr_pct": 8.0,
        "hurdle_rate_pct": 12.0,
        "bcr": 1.2,
        "payback_months": 12.0,
        "viability_breaches": [
            "non_positive_npv",
            "irr_below_hurdle_rate",
        ],
        "is_financially_viable": False,
    }


def test_audit_business_case_financial_viability_governance_bcr_and_payback_breaches():
    """BCR < 1.0 y payback_months > max_payback_months se reportan en viability_breaches."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_business_case_financial_viability_governance,
    )

    res = audit_business_case_financial_viability_governance(
        {
            "npv": 10000.0,
            "irr_pct": 15.0,
            "hurdle_rate_pct": 10.0,
            "bcr": 0.85,
            "payback_months": 36.0,
            "max_payback_months": 24.0,
        }
    )
    assert res == {
        "npv": 10000.0,
        "irr_pct": 15.0,
        "hurdle_rate_pct": 10.0,
        "bcr": 0.85,
        "payback_months": 36.0,
        "viability_breaches": [
            "benefit_cost_ratio_below_unity",
            "payback_exceeds_horizon",
        ],
        "is_financially_viable": False,
    }


def test_audit_business_case_financial_viability_governance_empty_or_non_mapping():
    """Entrada None, vacía o no Mapping activa las 4 brechas canónicas."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_business_case_financial_viability_governance,
    )

    for payload in (None, {}, "invalid", []):
        assert audit_business_case_financial_viability_governance(payload) == {  # type: ignore[arg-type]
            "npv": 0.0,
            "irr_pct": 0.0,
            "hurdle_rate_pct": 0.0,
            "bcr": 0.0,
            "payback_months": 0.0,
            "viability_breaches": [
                "non_positive_npv",
                "irr_below_hurdle_rate",
                "benefit_cost_ratio_below_unity",
                "payback_exceeds_horizon",
            ],
            "is_financially_viable": False,
        }


def test_audit_team_conflict_resolution_governance_healthy():
    """Conflictos resueltos con modos constructivos, acuerdos documentados y <= 5 días pasan is_conflict_governance_healthy=True."""
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_team_conflict_resolution_governance,
    )

    conflicts = [
        {
            "conflict_id": "CNF-01",
            "resolution_mode": "Collaborate",
            "severity": "critical",
            "agreement_documented": True,
            "escalated_unresolved_days": 2.0,
        },
        {
            "conflict_id": "CNF-02",
            "resolution_mode": "compromise",
            "severity": "medium",
            "agreement_documented": False,
            "escalated_unresolved_days": 3.5,
        },
    ]
    res = audit_team_conflict_resolution_governance(conflicts)
    assert res == {
        "total_conflicts": 2,
        "invalid_mode_conflict_ids": [],
        "destructive_high_severity_conflict_ids": [],
        "stalled_or_undocumented_conflict_ids": [],
        "collaborative_resolution_rate_pct": 50.0,
        "is_conflict_governance_healthy": True,
    }
    assert (
        ProjectLifecyclePMIService.audit_team_conflict_resolution_governance(
            conflicts
        )
        == res
    )


def test_audit_team_conflict_resolution_governance_invalid_and_destructive():
    """Detecta modo inválido y uso de force/withdraw en conflictos de alta severidad."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_team_conflict_resolution_governance,
    )

    res = audit_team_conflict_resolution_governance(
        [
            {
                "conflict_id": "CNF-BAD-MODE",
                "resolution_mode": "ignore_and_hope",
                "severity": "low",
                "agreement_documented": True,
            },
            {
                "conflict_id": "CNF-FORCE-CRIT",
                "resolution_mode": "force",
                "severity": "critical",
                "agreement_documented": True,
            },
        ]
    )
    assert res == {
        "total_conflicts": 2,
        "invalid_mode_conflict_ids": ["CNF-BAD-MODE"],
        "destructive_high_severity_conflict_ids": ["CNF-FORCE-CRIT"],
        "stalled_or_undocumented_conflict_ids": [],
        "collaborative_resolution_rate_pct": 0.0,
        "is_conflict_governance_healthy": False,
    }


def test_audit_team_conflict_resolution_governance_stalled_and_undocumented():
    """Detecta conflictos con escalated_unresolved_days > 5.0 o alta severidad sin acuerdo documentado."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_team_conflict_resolution_governance,
    )

    res = audit_team_conflict_resolution_governance(
        [
            {
                "conflict_id": "CNF-STALLED",
                "resolution_mode": "problem_solve",
                "severity": "medium",
                "agreement_documented": True,
                "escalated_unresolved_days": 8.0,
            },
            {
                "conflict_id": "CNF-HIGH-UNDOC",
                "resolution_mode": "collaborate",
                "severity": "high",
                "agreement_documented": False,
                "escalated_unresolved_days": 1.0,
            },
        ]
    )
    assert res == {
        "total_conflicts": 2,
        "invalid_mode_conflict_ids": [],
        "destructive_high_severity_conflict_ids": [],
        "stalled_or_undocumented_conflict_ids": [
            "CNF-STALLED",
            "CNF-HIGH-UNDOC",
        ],
        "collaborative_resolution_rate_pct": 50.0,
        "is_conflict_governance_healthy": False,
    }


def test_audit_team_conflict_resolution_governance_empty_or_invalid():
    """Entrada None, vacía o no secuencial retorna total_conflicts=0 e is_conflict_governance_healthy=False."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_team_conflict_resolution_governance,
    )

    for payload in (None, [], "invalid", {"conflict_id": "C-1"}, [{"conflict_id": "  "}]):
        assert audit_team_conflict_resolution_governance(payload) == {  # type: ignore[arg-type]
            "total_conflicts": 0,
            "invalid_mode_conflict_ids": [],
            "destructive_high_severity_conflict_ids": [],
            "stalled_or_undocumented_conflict_ids": [],
            "collaborative_resolution_rate_pct": 0.0,
            "is_conflict_governance_healthy": False,
        }


def test_audit_stage_gate_phase_transition_governance_healthy():
    """Compuertas Stage-Gate íntegras con firma de patrocinador, entregables verificados y caso de negocio revalidado -> healthy."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_stage_gate_phase_transition_governance,
    )

    gates = [
        {
            "gate_id": "GATE-INIT-PLAN",
            "decision": "go",
            "deliverables_verified": True,
            "sponsor_signed_off": True,
            "business_case_revalidated": True,
            "open_blocker_count": 0,
            "next_phase_started": True,
        },
        {
            "phase_id": "GATE-PLAN-EXEC",
            "decision": "conditional_go",
            "deliverables_verified": True,
            "sponsor_signed_off": True,
            "business_case_revalidated": True,
            "open_blocker_count": 0,
            "next_phase_started": True,
            "remediation_plan": "Cerrar observaciones menores de arquitectura",
            "remediation_due_date": "2026-11-15",
        },
    ]
    res = audit_stage_gate_phase_transition_governance(gates)
    assert res == {
        "total_gates": 2,
        "approved_gates_count": 2,
        "premature_phase_transitions": [],
        "unvalidated_business_case_gates": [],
        "conditional_go_missing_action_plan_gates": [],
        "is_stage_gate_compliant": True,
        "status": "healthy",
        "recommendations": [],
    }


def test_audit_stage_gate_phase_transition_governance_premature_transition_critical():
    """Transición prematura de fase con bloqueadores abiertos o sin aprobación del patrocinador -> critical."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_stage_gate_phase_transition_governance,
    )

    res = audit_stage_gate_phase_transition_governance(
        [
            {
                "gate_id": "GATE-01",
                "decision": "go",
                "deliverables_verified": True,
                "sponsor_signed_off": False,
                "business_case_revalidated": True,
                "open_blocker_count": 0,
                "next_phase_started": True,
            },
            {
                "gate_id": "GATE-02",
                "decision": "go",
                "deliverables_verified": True,
                "sponsor_signed_off": True,
                "business_case_revalidated": True,
                "open_blocker_count": 2,
                "next_phase_started": True,
            },
        ]
    )
    assert res["premature_phase_transitions"] == ["GATE-01", "GATE-02"]
    assert res["is_stage_gate_compliant"] is False
    assert res["status"] == "critical"
    assert len(res["recommendations"]) >= 1


def test_audit_stage_gate_phase_transition_governance_conditional_go_and_unvalidated_warning():
    """conditional_go sin plan/fecha de remediación o sin revalidación de caso de negocio -> warning."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_stage_gate_phase_transition_governance,
    )

    res = audit_stage_gate_phase_transition_governance(
        [
            {
                "gate_id": "GATE-COND",
                "decision": "conditional_go",
                "deliverables_verified": True,
                "sponsor_signed_off": True,
                "business_case_revalidated": False,
                "open_blocker_count": 0,
                "next_phase_started": False,
                "remediation_plan": "",
                "remediation_due_date": "",
            }
        ]
    )
    assert res["premature_phase_transitions"] == []
    assert res["unvalidated_business_case_gates"] == ["GATE-COND"]
    assert res["conditional_go_missing_action_plan_gates"] == ["GATE-COND"]
    assert res["is_stage_gate_compliant"] is False
    assert res["status"] == "warning"
    assert len(res["recommendations"]) == 2


def test_audit_stage_gate_phase_transition_governance_empty_and_service_staticmethod():
    """Entradas vacías/None e invocación vía ProjectLifecyclePMIService.audit_stage_gate_phase_transition_governance."""
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_stage_gate_phase_transition_governance,
    )

    for payload in (None, [], "invalid", [{"gate_id": "   "}]):
        res = audit_stage_gate_phase_transition_governance(payload)  # type: ignore[arg-type]
        assert res["total_gates"] == 0
        assert res["approved_gates_count"] == 0
        assert res["is_stage_gate_compliant"] is True
        assert res["status"] == "healthy"

    gates = [
        {
            "gate_id": "G-1",
            "decision": "go",
            "deliverables_verified": True,
            "sponsor_signed_off": False,
            "business_case_revalidated": True,
            "open_blocker_count": 0,
            "next_phase_started": True,
        }
    ]
    assert (
        ProjectLifecyclePMIService.audit_stage_gate_phase_transition_governance(
            gates, require_sponsor_signoff=False
        )
        == audit_stage_gate_phase_transition_governance(
            gates, require_sponsor_signoff=False
        )
    )


def test_audit_stakeholder_engagement_seam_drift_healthy():
    """Interesados en su nivel deseado (supportive/leading) -> healthy."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_stakeholder_engagement_seam_drift,
    )

    stakeholders = [
        {
            "stakeholder_id": "SH-01",
            "current_engagement": "leading",
            "desired_engagement": "leading",
            "previous_engagement": "supportive",
            "is_high_power_or_impact": True,
        },
        {
            "stakeholder_id": "SH-02",
            "current_engagement": "supportive",
            "desired_engagement": "supportive",
            "previous_engagement": "supportive",
            "is_high_power_or_impact": False,
        },
    ]
    res = audit_stakeholder_engagement_seam_drift(stakeholders)
    assert res == {
        "total_evaluated": 2,
        "engagement_gap_stakeholder_ids": [],
        "unmitigated_gap_stakeholder_ids": [],
        "high_impact_resistant_stakeholder_ids": [],
        "regressing_engagement_stakeholder_ids": [],
        "invalid_level_stakeholder_ids": [],
        "is_seam_governance_healthy": True,
        "status": "healthy",
        "recommendations": [],
    }


def test_audit_stakeholder_engagement_seam_drift_warning_and_critical_gaps():
    """Brecha SEAM con plan de acción (warning) vs brecha sin plan o resistente de alto impacto (critical)."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_stakeholder_engagement_seam_drift,
    )

    # Warning: brecha mitigada con plan de acción
    mitigated = [
        {
            "stakeholder_id": "SH-GAP-OK",
            "current_engagement": "neutral",
            "desired_engagement": "supportive",
            "engagement_action_plan": "Sesiones quincenales de co-diseño con PMO.",
            "is_high_power_or_impact": True,
        }
    ]
    res_warn = audit_stakeholder_engagement_seam_drift(mitigated)
    assert res_warn["total_evaluated"] == 1
    assert res_warn["engagement_gap_stakeholder_ids"] == ["SH-GAP-OK"]
    assert res_warn["unmitigated_gap_stakeholder_ids"] == []
    assert res_warn["high_impact_resistant_stakeholder_ids"] == []
    assert res_warn["is_seam_governance_healthy"] is True
    assert res_warn["status"] == "warning"
    assert len(res_warn["recommendations"]) >= 1

    # Critical: brecha sin plan + resistente de alto impacto
    critical_list = [
        {
            "stakeholder_id": "SH-UNMIT",
            "current_engagement": "unaware",
            "desired_engagement": "supportive",
            "engagement_action_plan": "   ",
        },
        {
            "stakeholder_id": "SH-RES-HIGH",
            "current_engagement": "resistant",
            "desired_engagement": "neutral",
            "engagement_action_plan": "Reunión ejecutiva 1:1",
            "is_high_power_or_impact": True,
        },
    ]
    res_crit = audit_stakeholder_engagement_seam_drift(critical_list)
    assert res_crit["total_evaluated"] == 2
    assert res_crit["engagement_gap_stakeholder_ids"] == ["SH-UNMIT", "SH-RES-HIGH"]
    assert res_crit["unmitigated_gap_stakeholder_ids"] == ["SH-UNMIT"]
    assert res_crit["high_impact_resistant_stakeholder_ids"] == ["SH-RES-HIGH"]
    assert res_crit["is_seam_governance_healthy"] is False
    assert res_crit["status"] == "critical"
    assert len(res_crit["recommendations"]) >= 2


def test_audit_stakeholder_engagement_seam_drift_regression_and_invalid_levels():
    """Regresión respecto a previous_engagement y detección de niveles fuera de la escala SEAM."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_stakeholder_engagement_seam_drift,
    )

    # Caso regresión sin brecha no mitigada -> warning
    regressing = [
        {
            "stakeholder_id": "SH-REG",
            "current_engagement": "supportive",
            "desired_engagement": "supportive",
            "previous_engagement": "leading",
        }
    ]
    res_reg = audit_stakeholder_engagement_seam_drift(regressing)
    assert res_reg["regressing_engagement_stakeholder_ids"] == ["SH-REG"]
    assert res_reg["is_seam_governance_healthy"] is False
    assert res_reg["status"] == "warning"

    # Caso nivel inválido -> critical
    invalid = [
        {
            "stakeholder_id": "SH-BAD",
            "current_engagement": "hostile",
            "desired_engagement": "supportive",
        }
    ]
    res_bad = audit_stakeholder_engagement_seam_drift(invalid)
    assert res_bad["invalid_level_stakeholder_ids"] == ["SH-BAD"]
    assert res_bad["is_seam_governance_healthy"] is False
    assert res_bad["status"] == "critical"


def test_audit_stakeholder_engagement_seam_drift_empty_and_service_staticmethod():
    """Entradas vacías/None e invocación vía ProjectLifecyclePMIService.audit_stakeholder_engagement_seam_drift."""
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_stakeholder_engagement_seam_drift,
    )

    for payload in (None, [], "invalid", [{"id": "  "}]):
        res = audit_stakeholder_engagement_seam_drift(payload)  # type: ignore[arg-type]
        assert res["total_evaluated"] == 0
        assert res["is_seam_governance_healthy"] is True
        assert res["status"] == "healthy"

    sample = [
        {
            "id": "SH-10",
            "current_engagement": "supportive",
            "desired_engagement": "supportive",
        }
    ]
    assert (
        ProjectLifecyclePMIService.audit_stakeholder_engagement_seam_drift(sample)
        == audit_stakeholder_engagement_seam_drift(sample)
    )


def test_audit_communications_management_plan_matrix_healthy():
    """Matriz de comunicaciones completa con métodos PMI (interactive, push, pull), protección confidencial y SLA -> healthy."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_communications_management_plan_matrix,
    )

    channels = [
        {
            "channel_id": "COMM-STEERING",
            "target_audience": "Comité Directivo y Patrocinador",
            "sender_owner": "Director de Proyecto",
            "frequency": "biweekly",
            "communication_method": "interactive",
            "is_confidential_or_executive": True,
            "encryption_or_access_control_enabled": True,
            "escalation_time_frame_hours": 24,
        },
        {
            "channel_id": "COMM-EVM-REPORT",
            "target_audience": "PMO y Líderes de Cuenta de Control",
            "sender_owner": "Analista EVM",
            "frequency": "weekly",
            "communication_method": "push",
            "is_confidential_or_executive": False,
            "escalation_time_frame_hours": 48.0,
        },
        {
            "channel_id": "COMM-WIKI-PORTAL",
            "target_audience": "Equipo de Proyecto Ampliado",
            "sender_owner": "PMO Steward",
            "frequency": "real_time",
            "communication_method": "pull",
            "is_confidential_or_executive": False,
            "escalation_time_frame_hours": 72,
        },
    ]
    res = audit_communications_management_plan_matrix(channels)
    assert res == {
        "total_channels": 3,
        "missing_owner_or_audience_channel_ids": [],
        "invalid_frequency_or_method_channel_ids": [],
        "unsecured_confidential_channel_ids": [],
        "missing_escalation_sla_channel_ids": [],
        "is_communications_plan_compliant": True,
        "status": "healthy",
        "recommendations": [],
    }


def test_audit_communications_management_plan_matrix_critical_unsecured_or_unowned():
    """Canal confidencial sin cifrado/control de acceso o canal sin dueño/audiencia -> critical."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_communications_management_plan_matrix,
    )

    channels = [
        {
            "channel_id": "COMM-EXEC-LEAK",
            "target_audience": "Junta Directiva",
            "sender_owner": "Sponsor",
            "frequency": "monthly",
            "communication_method": "push",
            "is_confidential_or_executive": True,
            "encryption_or_access_control_enabled": False,
            "escalation_time_frame_hours": 12,
        },
        {
            "channel_id": "COMM-NO-OWNER",
            "target_audience": "   ",
            "sender_owner": "",
            "frequency": "weekly",
            "communication_method": "interactive",
            "escalation_time_frame_hours": 24,
        },
    ]
    res = audit_communications_management_plan_matrix(channels)
    assert res["total_channels"] == 2
    assert res["unsecured_confidential_channel_ids"] == ["COMM-EXEC-LEAK"]
    assert res["missing_owner_or_audience_channel_ids"] == ["COMM-NO-OWNER"]
    assert res["is_communications_plan_compliant"] is False
    assert res["status"] == "critical"
    assert len(res["recommendations"]) == 2


def test_audit_communications_management_plan_matrix_warning_invalid_method_or_missing_sla():
    """Frecuencia/método fuera de catálogo PMI o falta de escalation_time_frame_hours -> warning."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_communications_management_plan_matrix,
    )

    channels = [
        {
            "channel_id": "COMM-BAD-METHOD",
            "target_audience": "Proveedores",
            "sender_owner": "Líder de Adquisiciones",
            "frequency": "whenever_possible",
            "communication_method": "telepathy",
            "escalation_time_frame_hours": 0,
        }
    ]
    res = audit_communications_management_plan_matrix(channels)
    assert res["total_channels"] == 1
    assert res["missing_owner_or_audience_channel_ids"] == []
    assert res["unsecured_confidential_channel_ids"] == []
    assert res["invalid_frequency_or_method_channel_ids"] == ["COMM-BAD-METHOD"]
    assert res["missing_escalation_sla_channel_ids"] == ["COMM-BAD-METHOD"]
    assert res["is_communications_plan_compliant"] is False
    assert res["status"] == "warning"
    assert len(res["recommendations"]) == 2


def test_audit_communications_management_plan_matrix_empty_and_service_staticmethod():
    """Entradas vacías/None e invocación vía ProjectLifecyclePMIService.audit_communications_management_plan_matrix."""
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_communications_management_plan_matrix,
    )

    for payload in (None, [], "invalid", [{"id": "  "}]):
        res = audit_communications_management_plan_matrix(payload)  # type: ignore[arg-type]
        assert res["total_channels"] == 0
        assert res["is_communications_plan_compliant"] is True
        assert res["status"] == "healthy"

    sample = [
        {
            "id": "COMM-1",
            "target_audience": "Stakeholders",
            "sender_owner": "PM",
            "frequency": "daily",
            "communication_method": "interactive",
            "escalation_time_frame_hours": 8,
        }
    ]
    assert (
        ProjectLifecyclePMIService.audit_communications_management_plan_matrix(sample)
        == audit_communications_management_plan_matrix(sample)
    )


def test_audit_risk_response_secondary_and_fallback_readiness_compliant():
    """Respuestas con dueño activo, fallback en alto riesgo residual y secundarios mitigados -> ready True."""
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_risk_response_secondary_and_fallback_readiness,
    )

    responses = [
        {
            "risk_id": "RSK-101",
            "response_strategy": "mitigate",
            "residual_severity_score": 14.0,
            "residual_threshold_score": 10.0,
            "has_fallback_plan": True,
            "secondary_risks_identified": True,
            "secondary_risk_mitigation_linked": True,
            "action_owner_id": "OWN-1",
        },
        {
            "id": "RSK-102",
            "response_strategy": "accept",
            "residual_severity_score": 5.0,
            "residual_threshold_score": 10.0,
            "has_fallback_plan": False,
            "secondary_risks_identified": False,
            "secondary_risk_mitigation_linked": False,
            "action_owner_id": "",
        },
    ]
    res = audit_risk_response_secondary_and_fallback_readiness(responses)
    assert res == {
        "total_evaluated": 2,
        "missing_fallback_high_residual_risk_ids": [],
        "unmitigated_secondary_risk_ids": [],
        "unassigned_active_response_risk_ids": [],
        "is_risk_response_execution_ready": True,
    }
    assert (
        ProjectLifecyclePMIService.audit_risk_response_secondary_and_fallback_readiness(
            responses
        )
        == res
    )


def test_audit_risk_response_secondary_and_fallback_readiness_missing_fallback_and_secondary():
    """Detecta riesgo residual sobre umbral sin fallback y riesgos secundarios sin mitigación vinculada."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_risk_response_secondary_and_fallback_readiness,
    )

    responses = [
        {
            "risk_id": "RSK-HIGH-RES",
            "response_strategy": "mitigate",
            "residual_severity_score": 15.0,
            "residual_threshold_score": 10.0,
            "has_fallback_plan": False,
            "secondary_risks_identified": False,
            "action_owner_id": "OWN-1",
        },
        {
            "risk_id": "RSK-SEC-UNLINKED",
            "response_strategy": "transfer",
            "residual_severity_score": 6.0,
            "residual_threshold_score": 10.0,
            "has_fallback_plan": False,
            "secondary_risks_identified": True,
            "secondary_risk_mitigation_linked": False,
            "action_owner_id": "OWN-2",
        },
    ]
    res = audit_risk_response_secondary_and_fallback_readiness(responses)
    assert res["total_evaluated"] == 2
    assert res["missing_fallback_high_residual_risk_ids"] == ["RSK-HIGH-RES"]
    assert res["unmitigated_secondary_risk_ids"] == ["RSK-SEC-UNLINKED"]
    assert res["unassigned_active_response_risk_ids"] == []
    assert res["is_risk_response_execution_ready"] is False


def test_audit_risk_response_secondary_and_fallback_readiness_unassigned_active_strategy():
    """Estrategia activa (avoid/exploit/enhance/share/mitigate/transfer) sin action_owner_id -> unassigned."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_risk_response_secondary_and_fallback_readiness,
    )

    responses = [
        {
            "risk_id": "RSK-NO-OWNER",
            "response_strategy": "avoid",
            "residual_severity_score": 2.0,
            "residual_threshold_score": 10.0,
            "has_fallback_plan": False,
            "action_owner_id": "   ",
        }
    ]
    res = audit_risk_response_secondary_and_fallback_readiness(responses)
    assert res["total_evaluated"] == 1
    assert res["missing_fallback_high_residual_risk_ids"] == []
    assert res["unmitigated_secondary_risk_ids"] == []
    assert res["unassigned_active_response_risk_ids"] == ["RSK-NO-OWNER"]
    assert res["is_risk_response_execution_ready"] is False


def test_audit_risk_response_secondary_and_fallback_readiness_invalid_inputs_and_export():
    """Ignora entradas no secuencia o sin risk_id válido y verifica exportación en __all__."""
    import backend.services.project_lifecycle_pmi_service as _m
    from backend.services.project_lifecycle_pmi_service import (
        audit_risk_response_secondary_and_fallback_readiness,
    )

    assert "audit_risk_response_secondary_and_fallback_readiness" in _m.__all__
    for bad in (None, "not-a-seq", b"bytes", bytearray(b"abc"), [{"risk_id": "  "}, 123]):
        res = audit_risk_response_secondary_and_fallback_readiness(bad)
        assert res == {
            "total_evaluated": 0,
            "missing_fallback_high_residual_risk_ids": [],
            "unmitigated_secondary_risk_ids": [],
            "unassigned_active_response_risk_ids": [],
            "is_risk_response_execution_ready": True,
        }


def test_audit_steering_committee_quorum_and_escalation_governance_compliant():
    """Sesiones con quórum >= min_quorum_pct, patrocinador presente, actas firmadas y bloqueadores resueltos."""
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_steering_committee_quorum_and_escalation_governance,
    )

    sessions = [
        {
            "session_id": "SC-2026-Q1",
            "voting_members_invited": 8,
            "voting_members_present": 7,
            "sponsor_present": True,
            "decisions_ratified_count": 3,
            "minutes_signed_and_published": True,
            "escalated_blockers_count": 2,
            "escalated_blockers_assigned_resolution": 2,
        },
        {
            "id": "SC-2026-Q2",
            "voting_members_invited": 4,
            "voting_members_present": 3,
            "sponsor_present": False,
            "decisions_ratified_count": 0,
            "minutes_signed_and_published": False,
            "escalated_blockers_count": 0,
            "escalated_blockers_assigned_resolution": 0,
        },
    ]
    res = audit_steering_committee_quorum_and_escalation_governance(
        sessions, min_quorum_pct=75.0
    )
    assert res == {
        "total_evaluated": 2,
        "quorum_breach_session_ids": [],
        "unrecorded_decision_session_ids": [],
        "unresolved_escalation_session_ids": [],
        "is_steering_governance_compliant": True,
    }
    assert (
        ProjectLifecyclePMIService.audit_steering_committee_quorum_and_escalation_governance(
            sessions
        )
        == res
    )


def test_audit_steering_committee_quorum_and_sponsor_breaches():
    """Detecta falta de quórum (< min_quorum_pct, invitados <= 0) o decisiones ratificadas sin patrocinador."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_steering_committee_quorum_and_escalation_governance,
    )

    sessions = [
        {
            "session_id": "SC-LOW-QUORUM",
            "voting_members_invited": 10,
            "voting_members_present": 6,
            "sponsor_present": True,
            "decisions_ratified_count": 1,
            "minutes_signed_and_published": True,
        },
        {
            "session_id": "SC-NO-SPONSOR",
            "voting_members_invited": 4,
            "voting_members_present": 4,
            "sponsor_present": False,
            "decisions_ratified_count": 2,
            "minutes_signed_and_published": True,
        },
        {
            "session_id": "SC-ZERO-INVITED",
            "voting_members_invited": 0,
            "voting_members_present": 0,
        },
    ]
    res = audit_steering_committee_quorum_and_escalation_governance(
        sessions, min_quorum_pct=75.0
    )
    assert res["total_evaluated"] == 3
    assert res["quorum_breach_session_ids"] == [
        "SC-LOW-QUORUM",
        "SC-NO-SPONSOR",
        "SC-ZERO-INVITED",
    ]
    assert res["unrecorded_decision_session_ids"] == []
    assert res["unresolved_escalation_session_ids"] == []
    assert res["is_steering_governance_compliant"] is False


def test_audit_steering_committee_unrecorded_decisions_and_unresolved_escalations():
    """Detecta decisiones ratificadas sin acta publicada y bloqueadores escalados sin resolución asignada."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_steering_committee_quorum_and_escalation_governance,
    )

    sessions = [
        {
            "session_id": "SC-UNSIGNED-MINUTES",
            "voting_members_invited": 6,
            "voting_members_present": 6,
            "sponsor_present": True,
            "decisions_ratified_count": 4,
            "minutes_signed_and_published": False,
            "escalated_blockers_count": 3,
            "escalated_blockers_assigned_resolution": 1,
        }
    ]
    res = audit_steering_committee_quorum_and_escalation_governance(sessions)
    assert res["total_evaluated"] == 1
    assert res["quorum_breach_session_ids"] == []
    assert res["unrecorded_decision_session_ids"] == ["SC-UNSIGNED-MINUTES"]
    assert res["unresolved_escalation_session_ids"] == ["SC-UNSIGNED-MINUTES"]
    assert res["is_steering_governance_compliant"] is False


def test_audit_steering_committee_invalid_inputs_and_export():
    """Ignora entradas no secuencia o sin session_id válido y verifica exportación en __all__."""
    import backend.services.project_lifecycle_pmi_service as _m
    from backend.services.project_lifecycle_pmi_service import (
        audit_steering_committee_quorum_and_escalation_governance,
    )

    assert (
        "audit_steering_committee_quorum_and_escalation_governance" in _m.__all__
    )
    for bad in (None, "not-a-seq", b"bytes", bytearray(b"123"), [{"session_id": "  "}, 42]):
        assert audit_steering_committee_quorum_and_escalation_governance(bad) == {
            "total_evaluated": 0,
            "quorum_breach_session_ids": [],
            "unrecorded_decision_session_ids": [],
            "unresolved_escalation_session_ids": [],
            "is_steering_governance_compliant": True,
        }

