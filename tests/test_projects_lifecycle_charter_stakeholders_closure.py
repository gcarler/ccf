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



def test_audit_charter_pm_authority_and_variance_tolerances_compliant():
    """Actas con PM asignado, limite de gasto > 0, tolerancias en (0, 25] y trigger documentado."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_charter_pm_authority_and_variance_tolerances,
    )

    charters = [
        {
            "charter_id": "CH-1",
            "pm_assigned_id": "PM-1",
            "pm_budget_signoff_limit": 50000.0,
            "cost_variance_tolerance_pct": 10.0,
            "schedule_variance_tolerance_pct": 8.0,
            "sponsor_escalation_trigger_documented": True,
        },
        {
            "id": "CH-2",
            "pm_assigned_id": "PM-2",
            "pm_budget_signoff_limit": 20000.0,
            "cost_variance_tolerance_pct": 25.0,  # borde superior inclusive.
            "schedule_variance_tolerance_pct": 25.0,
            "sponsor_escalation_trigger_documented": True,
        },
    ]
    res = audit_charter_pm_authority_and_variance_tolerances(charters)
    assert res == {
        "total_evaluated": 2,
        "unassigned_or_zero_authority_charter_ids": [],
        "invalid_tolerance_bounds_charter_ids": [],
        "missing_escalation_trigger_charter_ids": [],
        "is_charter_authority_governance_valid": True,
    }


def test_audit_charter_pm_authority_and_variance_tolerances_authority_gaps():
    """Detecta PM no asignado (id vacio tras strip) o limite de firma <= 0."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_charter_pm_authority_and_variance_tolerances,
    )

    charters = [
        {"charter_id": "A-1", "pm_assigned_id": "   ",
         "pm_budget_signoff_limit": 10000.0,
         "cost_variance_tolerance_pct": 10.0, "schedule_variance_tolerance_pct": 10.0,
         "sponsor_escalation_trigger_documented": True},
        {"charter_id": "A-2", "pm_assigned_id": "PM-3",
         "pm_budget_signoff_limit": 0.0,
         "cost_variance_tolerance_pct": 10.0, "schedule_variance_tolerance_pct": 10.0,
         "sponsor_escalation_trigger_documented": True},
        {"charter_id": "A-3", "pm_assigned_id": "PM-4",
         "pm_budget_signoff_limit": "oops",  # coercion a 0 -> autoridad cero.
         "cost_variance_tolerance_pct": 10.0, "schedule_variance_tolerance_pct": 10.0,
         "sponsor_escalation_trigger_documented": True},
    ]
    res = audit_charter_pm_authority_and_variance_tolerances(charters)
    assert res["total_evaluated"] == 3
    assert res["unassigned_or_zero_authority_charter_ids"] == ["A-1", "A-2", "A-3"]
    assert res["invalid_tolerance_bounds_charter_ids"] == []
    assert res["missing_escalation_trigger_charter_ids"] == []
    assert res["is_charter_authority_governance_valid"] is False


def test_audit_charter_pm_authority_and_variance_tolerances_invalid_bounds():
    """Tolerancias fuera de (0, 25]: <= 0, > 25 o coercion invalida a 0."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_charter_pm_authority_and_variance_tolerances,
    )

    charters = [
        {"charter_id": "T-1", "pm_assigned_id": "PM-1", "pm_budget_signoff_limit": 10000.0,
         "cost_variance_tolerance_pct": 0.0, "schedule_variance_tolerance_pct": 10.0,
         "sponsor_escalation_trigger_documented": True},
        {"charter_id": "T-2", "pm_assigned_id": "PM-2", "pm_budget_signoff_limit": 10000.0,
         "cost_variance_tolerance_pct": 25.01, "schedule_variance_tolerance_pct": 10.0,
         "sponsor_escalation_trigger_documented": True},
        {"charter_id": "T-3",
         "pm_assigned_id": "PM-3", "pm_budget_signoff_limit": 10000.0,
         "cost_variance_tolerance_pct": 10.0, "schedule_variance_tolerance_pct": -2.0,
         "sponsor_escalation_trigger_documented": True},
        {"charter_id": "T-4", "pm_assigned_id": "PM-4",
         "pm_budget_signoff_limit": 10000.0,
         "cost_variance_tolerance_pct": None,
         "schedule_variance_tolerance_pct": 10.0,
         "sponsor_escalation_trigger_documented": True},  # None -> 0 -> invalido.
        {"charter_id": "T-5", "pm_assigned_id": "PM-5", "pm_budget_signoff_limit": 10000.0,
         "cost_variance_tolerance_pct": 25.0, "schedule_variance_tolerance_pct": 25.0,
         "sponsor_escalation_trigger_documented": True},  # borde -> valido.
    ]
    res = audit_charter_pm_authority_and_variance_tolerances(charters)
    assert res["total_evaluated"] == 5
    assert res["invalid_tolerance_bounds_charter_ids"] == ["T-1", "T-2", "T-3", "T-4"]
    assert res["unassigned_or_zero_authority_charter_ids"] == []
    assert res["missing_escalation_trigger_charter_ids"] == []
    assert res["is_charter_authority_governance_valid"] is False


def test_audit_charter_pm_authority_and_variance_tolerances_trigger_and_scope():
    """Trigger de escalamiento ausente; entradas vacias/None + proxy estatico + __all__."""
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_charter_pm_authority_and_variance_tolerances,
    )
    import backend.services.project_lifecycle_pmi_service as _m

    res = audit_charter_pm_authority_and_variance_tolerances(
        [
            {"charter_id": "E-1", "pm_assigned_id": "PM-1",
             "pm_budget_signoff_limit": 10000.0,
             "cost_variance_tolerance_pct": 10.0,
             "schedule_variance_tolerance_pct": 10.0},  # trigger default False.
        ]
    )
    assert res["missing_escalation_trigger_charter_ids"] == ["E-1"]
    assert res["unassigned_or_zero_authority_charter_ids"] == []
    assert res["invalid_tolerance_bounds_charter_ids"] == []
    assert res["is_charter_authority_governance_valid"] is False

    res_none = audit_charter_pm_authority_and_variance_tolerances(None)
    assert res_none == {
        "total_evaluated": 0,
        "unassigned_or_zero_authority_charter_ids": [],
        "invalid_tolerance_bounds_charter_ids": [],
        "missing_escalation_trigger_charter_ids": [],
        "is_charter_authority_governance_valid": True,
    }
    assert audit_charter_pm_authority_and_variance_tolerances("no-seq")["total_evaluated"] == 0
    assert (
        audit_charter_pm_authority_and_variance_tolerances(
            ["no-map", {"charter_id": "   "}, {"other_id": "x"}]
        )["total_evaluated"]
        == 0
    )
    assert "audit_charter_pm_authority_and_variance_tolerances" in _m.__all__

    sample = [
        {"charter_id": "CH-1", "pm_assigned_id": "PM-1",
         "pm_budget_signoff_limit": 40000.0,
         "cost_variance_tolerance_pct": 12.0, "schedule_variance_tolerance_pct": 9.0,
         "sponsor_escalation_trigger_documented": True},
    ]
    assert (
        ProjectLifecyclePMIService.audit_charter_pm_authority_and_variance_tolerances(sample)
        == audit_charter_pm_authority_and_variance_tolerances(sample)
    )


def test_audit_stakeholder_engagement_seam_gap_and_drift_compliant():
    """Matriz SEAM alineada o con brecha mitigada por plan de acción cumple §13.3 y §13.4."""
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_stakeholder_engagement_seam_gap_and_drift,
    )

    assessments = [
        {
            "stakeholder_id": "SH-SPONSOR",
            "power_influence_level": "high",
            "previous_engagement_level": "supportive",
            "current_engagement_level": "leading",
            "desired_engagement_level": "leading",
            "engagement_action_plan_defined": True,
        },
        {
            "stakeholder_id": "SH-OPS",
            "power_influence_level": "medium",
            "previous_engagement_level": "neutral",
            "current_engagement_level": "neutral",
            "desired_engagement_level": "supportive",
            "engagement_action_plan_defined": True,
        },
    ]
    res = audit_stakeholder_engagement_seam_gap_and_drift(assessments)
    assert res == {
        "total_stakeholders": 2,
        "invalid_level_stakeholder_ids": [],
        "high_power_resistant_or_unaware_ids": [],
        "unmitigated_engagement_gap_ids": [],
        "regressing_engagement_drift_ids": [],
        "is_seam_governance_compliant": True,
    }
    assert (
        ProjectLifecyclePMIService.audit_stakeholder_engagement_seam_gap_and_drift(
            assessments
        )
        == res
    )


def test_audit_stakeholder_engagement_seam_gap_high_power_resistant_and_unaware():
    """Detecta interesados de alto poder en estado resistant o unaware."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_stakeholder_engagement_seam_gap_and_drift,
    )

    assessments = [
        {
            "stakeholder_id": "SH-REGULATOR",
            "power_influence_level": "HIGH",
            "previous_engagement_level": "resistant",
            "current_engagement_level": "Resistant",
            "desired_engagement_level": "supportive",
            "engagement_action_plan_defined": True,
        },
        {
            "stakeholder_id": "SH-VP-FIN",
            "power_influence_level": "high",
            "previous_engagement_level": None,
            "current_engagement_level": "unaware",
            "desired_engagement_level": "neutral",
            "engagement_action_plan_defined": True,
        },
    ]
    res = audit_stakeholder_engagement_seam_gap_and_drift(assessments)
    assert res["total_stakeholders"] == 2
    assert res["high_power_resistant_or_unaware_ids"] == [
        "SH-REGULATOR",
        "SH-VP-FIN",
    ]
    assert res["unmitigated_engagement_gap_ids"] == []
    assert res["regressing_engagement_drift_ids"] == []
    assert res["is_seam_governance_compliant"] is False


def test_audit_stakeholder_engagement_seam_gap_unmitigated_and_regressing_drift():
    """Detecta brechas actual < deseado sin plan de acción y regresiones respecto al nivel previo."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_stakeholder_engagement_seam_gap_and_drift,
    )

    assessments = [
        {
            "stakeholder_id": "SH-GAP-NO-PLAN",
            "power_influence_level": "medium",
            "previous_engagement_level": "neutral",
            "current_engagement_level": "neutral",
            "desired_engagement_level": "supportive",
            "engagement_action_plan_defined": False,
        },
        {
            "stakeholder_id": "SH-DRIFT-DOWN",
            "power_influence_level": "low",
            "previous_engagement_level": "leading",
            "current_engagement_level": "supportive",
            "desired_engagement_level": "supportive",
            "engagement_action_plan_defined": True,
        },
    ]
    res = audit_stakeholder_engagement_seam_gap_and_drift(assessments)
    assert res["total_stakeholders"] == 2
    assert res["unmitigated_engagement_gap_ids"] == ["SH-GAP-NO-PLAN"]
    assert res["regressing_engagement_drift_ids"] == ["SH-DRIFT-DOWN"]
    assert res["is_seam_governance_compliant"] is False


def test_audit_stakeholder_engagement_seam_gap_invalid_levels_and_export():
    """Detecta niveles fuera de la escala SEAM, ignora entradas no secuencia y verifica __all__."""
    import backend.services.project_lifecycle_pmi_service as _m
    from backend.services.project_lifecycle_pmi_service import (
        audit_stakeholder_engagement_seam_gap_and_drift,
    )

    assert "audit_stakeholder_engagement_seam_gap_and_drift" in _m.__all__
    res = audit_stakeholder_engagement_seam_gap_and_drift(
        [
            {
                "stakeholder_id": "SH-BAD-LEVEL",
                "power_influence_level": "low",
                "current_engagement_level": "champion",
                "desired_engagement_level": "leading",
            }
        ]
    )
    assert res["invalid_level_stakeholder_ids"] == ["SH-BAD-LEVEL"]
    assert res["is_seam_governance_compliant"] is False

    for bad in (None, "not-a-seq", b"bytes", [{"stakeholder_id": "  "}]):
        assert audit_stakeholder_engagement_seam_gap_and_drift(bad) == {
            "total_stakeholders": 0,
            "invalid_level_stakeholder_ids": [],
            "high_power_resistant_or_unaware_ids": [],
            "unmitigated_engagement_gap_ids": [],
            "regressing_engagement_drift_ids": [],
            "is_seam_governance_compliant": True,
        }


def test_audit_project_governance_tailoring_and_hybrid_justification_compliant():
    """Tailoring con artefactos eximibles justificados y firmados, y proyectos híbridos con mapeo cumplen §2.4 y §4.2."""
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_project_governance_tailoring_and_hybrid_justification,
    )

    records = [
        {
            "project_id": "PRJ-PRED-01",
            "delivery_approach": "predictive",
            "omitted_standard_artifacts": [],
            "tailoring_justification_documented": False,
            "pmo_or_sponsor_signoff": False,
        },
        {
            "project_id": "PRJ-AGILE-02",
            "delivery_approach": "Agile",
            "omitted_standard_artifacts": ["detailed_gantt_baseline"],
            "tailoring_justification_documented": True,
            "pmo_or_sponsor_signoff": True,
        },
        {
            "project_id": "PRJ-HYB-03",
            "delivery_approach": "hybrid",
            "omitted_standard_artifacts": ["formal_ccb_for_sprint_tasks"],
            "tailoring_justification_documented": True,
            "pmo_or_sponsor_signoff": True,
            "cadence_and_stage_gate_mapping_defined": True,
        },
    ]
    res = audit_project_governance_tailoring_and_hybrid_justification(records)
    assert res == {
        "total_projects": 3,
        "invalid_approach_project_ids": [],
        "non_waivable_artifact_omitted_project_ids": [],
        "unapproved_tailoring_omission_project_ids": [],
        "unmapped_hybrid_cadence_project_ids": [],
        "is_tailoring_governance_compliant": True,
    }
    assert (
        ProjectLifecyclePMIService.audit_project_governance_tailoring_and_hybrid_justification(
            records
        )
        == res
    )


def test_audit_project_governance_tailoring_non_waivable_and_unapproved_omission():
    """Detecta omisión de artefactos obligatorios (charter/risk_register/lessons_learned) y omisiones sin firma PMO."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_project_governance_tailoring_and_hybrid_justification,
    )

    records = [
        {
            "project_id": "PRJ-NO-CHARTER",
            "delivery_approach": "agile",
            "omitted_standard_artifacts": ["Charter", "wbs_dictionary"],
            "tailoring_justification_documented": True,
            "pmo_or_sponsor_signoff": True,
        },
        {
            "project_id": "PRJ-UNAPPROVED-OMIT",
            "delivery_approach": "predictive",
            "omitted_standard_artifacts": ["procurement_plan"],
            "tailoring_justification_documented": True,
            "pmo_or_sponsor_signoff": False,
        },
    ]
    res = audit_project_governance_tailoring_and_hybrid_justification(records)
    assert res["total_projects"] == 2
    assert res["non_waivable_artifact_omitted_project_ids"] == [
        "PRJ-NO-CHARTER"
    ]
    assert res["unapproved_tailoring_omission_project_ids"] == [
        "PRJ-UNAPPROVED-OMIT"
    ]
    assert res["is_tailoring_governance_compliant"] is False


def test_audit_project_governance_tailoring_unmapped_hybrid_and_invalid_approach():
    """Detecta enfoque híbrido sin mapeo de cadencia/stage-gate y enfoques desconocidos."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_project_governance_tailoring_and_hybrid_justification,
    )

    records = [
        {
            "project_id": "PRJ-HYB-UNMAPPED",
            "delivery_approach": "hybrid",
            "omitted_standard_artifacts": [],
            "cadence_and_stage_gate_mapping_defined": False,
        },
        {
            "project_id": "PRJ-BAD-APPROACH",
            "delivery_approach": "chaos_driven",
            "omitted_standard_artifacts": [],
        },
    ]
    res = audit_project_governance_tailoring_and_hybrid_justification(records)
    assert res["invalid_approach_project_ids"] == ["PRJ-BAD-APPROACH"]
    assert res["unmapped_hybrid_cadence_project_ids"] == ["PRJ-HYB-UNMAPPED"]
    assert res["is_tailoring_governance_compliant"] is False


def test_audit_project_governance_tailoring_invalid_inputs_and_export():
    """Maneja entradas vacías o no secuencia y verifica exportación en __all__."""
    import backend.services.project_lifecycle_pmi_service as _m
    from backend.services.project_lifecycle_pmi_service import (
        audit_project_governance_tailoring_and_hybrid_justification,
    )

    assert (
        "audit_project_governance_tailoring_and_hybrid_justification"
        in _m.__all__
    )
    for bad in (None, "not-a-seq", b"bytes", [{"project_id": "  "}]):
        assert (
            audit_project_governance_tailoring_and_hybrid_justification(bad)
            == {
                "total_projects": 0,
                "invalid_approach_project_ids": [],
                "non_waivable_artifact_omitted_project_ids": [],
                "unapproved_tailoring_omission_project_ids": [],
                "unmapped_hybrid_cadence_project_ids": [],
                "is_tailoring_governance_compliant": True,
            }
        )


def test_audit_administrative_closure_financial_and_resource_release_compliant():
    """Dossier de cierre sin POs ni devengos abiertos, códigos cerrados, recursos liberados y OPA/Sponsor firmados cumple §4.7."""
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_administrative_closure_financial_and_resource_release,
    )

    dossiers = [
        {
            "project_id": "PRJ-CLOSED-01",
            "open_purchase_orders_count": 0,
            "unreconciled_accruals_amount": 0.0,
            "charge_codes_closed": True,
            "allocated_team_members_remaining": 0,
            "lessons_learned_archived_in_opa": True,
            "final_sponsor_signoff_obtained": True,
        }
    ]
    res = audit_administrative_closure_financial_and_resource_release(dossiers)
    assert res == {
        "total_projects": 1,
        "invalid_closure_metric_project_ids": [],
        "unclosed_financial_ledger_project_ids": [],
        "unreleased_resource_allocation_project_ids": [],
        "incomplete_opa_or_signoff_project_ids": [],
        "is_administrative_closure_compliant": True,
    }
    assert (
        ProjectLifecyclePMIService.audit_administrative_closure_financial_and_resource_release(
            dossiers
        )
        == res
    )


def test_audit_administrative_closure_unclosed_financial_ledger():
    """Detecta POs abiertas, devengos sin conciliar o códigos de cargo abiertos."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_administrative_closure_financial_and_resource_release,
    )

    dossiers = [
        {
            "project_id": "PRJ-OPEN-PO",
            "open_purchase_orders_count": 2,
            "unreconciled_accruals_amount": 0.0,
            "charge_codes_closed": True,
            "allocated_team_members_remaining": 0,
            "lessons_learned_archived_in_opa": True,
            "final_sponsor_signoff_obtained": True,
        },
        {
            "project_id": "PRJ-OPEN-CHARGE-CODE",
            "open_purchase_orders_count": 0,
            "unreconciled_accruals_amount": 0.0,
            "charge_codes_closed": False,
            "allocated_team_members_remaining": 0,
            "lessons_learned_archived_in_opa": True,
            "final_sponsor_signoff_obtained": True,
        },
    ]
    res = audit_administrative_closure_financial_and_resource_release(dossiers)
    assert res["unclosed_financial_ledger_project_ids"] == [
        "PRJ-OPEN-PO",
        "PRJ-OPEN-CHARGE-CODE",
    ]
    assert res["is_administrative_closure_compliant"] is False


def test_audit_administrative_closure_unreleased_resources_and_incomplete_opa():
    """Detecta miembros del equipo aún asignados y falta de archivo OPA o firma de sponsor."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_administrative_closure_financial_and_resource_release,
    )

    dossiers = [
        {
            "project_id": "PRJ-HELD-RESOURCES",
            "open_purchase_orders_count": 0,
            "unreconciled_accruals_amount": 0.0,
            "charge_codes_closed": True,
            "allocated_team_members_remaining": 3,
            "lessons_learned_archived_in_opa": False,
            "final_sponsor_signoff_obtained": True,
        }
    ]
    res = audit_administrative_closure_financial_and_resource_release(dossiers)
    assert res["unreleased_resource_allocation_project_ids"] == [
        "PRJ-HELD-RESOURCES"
    ]
    assert res["incomplete_opa_or_signoff_project_ids"] == [
        "PRJ-HELD-RESOURCES"
    ]
    assert res["is_administrative_closure_compliant"] is False


def test_audit_administrative_closure_invalid_metrics_and_export():
    """Detecta métricas negativas, maneja entradas vacías y verifica exportación en __all__."""
    import backend.services.project_lifecycle_pmi_service as _m
    from backend.services.project_lifecycle_pmi_service import (
        audit_administrative_closure_financial_and_resource_release,
    )

    assert (
        "audit_administrative_closure_financial_and_resource_release"
        in _m.__all__
    )
    res = audit_administrative_closure_financial_and_resource_release(
        [{"project_id": "PRJ-NEG-PO", "open_purchase_orders_count": -1}]
    )
    assert res["invalid_closure_metric_project_ids"] == ["PRJ-NEG-PO"]
    assert res["is_administrative_closure_compliant"] is False

    for bad in (None, "not-a-seq", b"bytes", [{"project_id": "  "}]):
        assert (
            audit_administrative_closure_financial_and_resource_release(bad)
            == {
                "total_projects": 0,
                "invalid_closure_metric_project_ids": [],
                "unclosed_financial_ledger_project_ids": [],
                "unreleased_resource_allocation_project_ids": [],
                "incomplete_opa_or_signoff_project_ids": [],
                "is_administrative_closure_compliant": True,
            }
        )


def test_audit_steering_committee_quorum_and_decision_governance_healthy():
    """Sesiones con quorum >= 66.7, sponsor presente, sin dissent ni actas tardias."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_steering_committee_quorum_and_decision_governance,
    )

    res = audit_steering_committee_quorum_and_decision_governance(
        [
            {"meeting_id": "SC-01", "voting_members_total": 3, "voting_members_present": 3,
             "sponsor_present": True, "decisions_count": 2, "has_dissent": False,
             "dissent_documented": False, "minutes_published_days": 1},
            {"meeting_id": "SC-02", "voting_members_total": 4, "voting_members_present": 3,
             "sponsor_present": True, "decisions_count": 0, "has_dissent": False,
             "dissent_documented": False, "minutes_published_days": 3},
        ]
    )
    assert res == {
        "total_meetings": 2,
        "compliant_meetings_count": 2,
        "sub_quorum_meetings_count": 0,
        "missing_sponsor_meetings_count": 0,
        "undocumented_dissent_count": 0,
        "late_minutes_count": 0,
        "overall_quorum_compliance_pct": 100.0,
        "governance_board_status": "HEALTHY",
        "violations": [],
    }


def test_audit_steering_committee_quorum_and_decision_governance_critical():
    """Sub-quorum (borde literal 2/3) + sponsor ausente con decisiones -> CRITICAL."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_steering_committee_quorum_and_decision_governance,
    )

    edge = audit_steering_committee_quorum_and_decision_governance(
        [
            {"meeting_id": "SC-B", "voting_members_total": 3, "voting_members_present": 2,
             "sponsor_present": True, "decisions_count": 0, "has_dissent": False,
             "dissent_documented": False, "minutes_published_days": 2},
        ]
    )
    # 2/3 * 100 = 66.666..% < 66.7 -> sub-quorum literal segun spec.
    assert edge["sub_quorum_meetings_count"] == 1
    assert edge["compliant_meetings_count"] == 0
    assert edge["overall_quorum_compliance_pct"] == 0.0
    assert edge["governance_board_status"] == "CRITICAL"
    assert edge["violations"] == [
        {"meeting_id": "SC-B", "reasons": ["QUORUM_PCT_BELOW_MIN (2/3)"]},
    ]

    crit = audit_steering_committee_quorum_and_decision_governance(
        [
            {"meeting_id": "SC-03", "voting_members_total": 3, "voting_members_present": 1,
             "sponsor_present": False, "decisions_count": 1, "has_dissent": False,
             "dissent_documented": False, "minutes_published_days": 2},
        ]
    )
    assert crit["sub_quorum_meetings_count"] == 1
    assert crit["missing_sponsor_meetings_count"] == 1
    assert crit["governance_board_status"] == "CRITICAL"
    assert crit["violations"] == [
        {"meeting_id": "SC-03", "reasons": [
            "QUORUM_PCT_BELOW_MIN (1/3)", "SPONSOR_MISSING_FOR_DECISIONS"]},
    ]


def test_audit_steering_committee_quorum_and_decision_governance_at_risk():
    """Dissent sin documentar + acta tardia con quorum/sponsor OK -> AT_RISK."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_steering_committee_quorum_and_decision_governance,
    )

    risk = audit_steering_committee_quorum_and_decision_governance(
        [
            {"meeting_id": "SC-04", "voting_members_total": 4, "voting_members_present": 3,
             "sponsor_present": True, "decisions_count": 1, "has_dissent": True,
             "dissent_documented": False, "minutes_published_days": 5},
        ]
    )
    assert risk["undocumented_dissent_count"] == 1
    assert risk["late_minutes_count"] == 1
    assert risk["sub_quorum_meetings_count"] == 0
    assert risk["missing_sponsor_meetings_count"] == 0
    assert risk["compliant_meetings_count"] == 1
    assert risk["overall_quorum_compliance_pct"] == 100.0
    assert risk["governance_board_status"] == "AT_RISK"
    assert risk["violations"] == [{"meeting_id": "SC-04", "reasons": [
        "DISSENT_NOT_DOCUMENTED", "MINUTES_PUBLISHED_LATE (5>3)"]}]


def test_audit_steering_committee_quorum_and_decision_governance_thresholds_and_empty():
    """Umbrales custom, entrada vacia/None y proxy estatico + __all__."""
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_steering_committee_quorum_and_decision_governance,
    )
    import backend.services.project_lifecycle_pmi_service as mod

    # 3/4 = 75.0 >= min 75.0 -> quorum OK; acta 3 > max 2 -> tardia.
    custom = audit_steering_committee_quorum_and_decision_governance(
        [
            {"meeting_id": "SC-05", "voting_members_total": 4, "voting_members_present": 3,
             "sponsor_present": True, "decisions_count": 0, "has_dissent": False,
             "dissent_documented": False, "minutes_published_days": 3},
        ],
        min_quorum_pct=75.0,
        max_minutes_publish_days=2,
    )
    assert custom["sub_quorum_meetings_count"] == 0
    assert custom["late_minutes_count"] == 1
    assert custom["governance_board_status"] == "AT_RISK"

    empty = audit_steering_committee_quorum_and_decision_governance([])
    assert empty["total_meetings"] == 0
    assert empty["overall_quorum_compliance_pct"] == 100.0
    assert empty["governance_board_status"] == "HEALTHY"
    assert audit_steering_committee_quorum_and_decision_governance(None)["total_meetings"] == 0

    sample = [{"meeting_id": "SM", "voting_members_total": 2, "voting_members_present": 2,
               "sponsor_present": True, "decisions_count": 0, "has_dissent": False,
               "dissent_documented": False, "minutes_published_days": 1}]
    assert (
        ProjectLifecyclePMIService.audit_steering_committee_quorum_and_decision_governance(sample)
        == audit_steering_committee_quorum_and_decision_governance(sample)
    )
    assert "audit_steering_committee_quorum_and_decision_governance" in mod.__all__


def test_audit_portfolio_strategic_alignment_and_benefits_drift_healthy():
    """Verifica estado HEALTHY cuando todos los objetivos tienen entregables, gobernanza y realización de beneficios en rango."""
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_portfolio_strategic_alignment_and_benefits_drift,
    )

    objectives = [
        {
            "objective_id": "OBJ-DIG-01",
            "strategic_weight_pct": 60.0,
            "linked_deliverables_count": 3,
            "target_benefit_value": 100000.0,
            "realized_or_projected_benefit_value": 95000.0,
            "benefit_owner_assigned": True,
            "measurement_kpi_defined": True,
        },
        {
            "objective_id": "OBJ-EFF-02",
            "strategic_weight_pct": 40.0,
            "linked_deliverables_count": 2,
            "target_benefit_value": 50000.0,
            "realized_or_projected_benefit_value": 48000.0,
            "benefit_owner_assigned": True,
            "measurement_kpi_defined": True,
        },
    ]
    res = audit_portfolio_strategic_alignment_and_benefits_drift(
        objectives,
        min_strategic_weight_coverage_pct=80.0,
        max_benefit_shortfall_pct=15.0,
    )
    assert res == {
        "total_objectives": 2,
        "compliant_objectives_count": 2,
        "unlinked_objectives_count": 0,
        "missing_governance_objectives_count": 0,
        "benefit_shortfall_objectives_count": 0,
        "covered_strategic_weight_pct": 100.0,
        "strategic_alignment_status": "HEALTHY",
        "findings": [],
    }
    assert (
        ProjectLifecyclePMIService.audit_portfolio_strategic_alignment_and_benefits_drift(
            objectives
        )
        == res
    )


def test_audit_portfolio_strategic_alignment_and_benefits_drift_at_risk():
    """Verifica estado AT_RISK cuando falta dueño/KPI o existe un objetivo menor sin entregables pero cobertura >= 80%."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_portfolio_strategic_alignment_and_benefits_drift,
    )

    res = audit_portfolio_strategic_alignment_and_benefits_drift(
        [
            {
                "objective_id": "OBJ-MAIN",
                "strategic_weight_pct": 85.0,
                "linked_deliverables_count": 4,
                "target_benefit_value": 100000.0,
                "realized_or_projected_benefit_value": 92000.0,
                "benefit_owner_assigned": True,
                "measurement_kpi_defined": False,
            },
            {
                "objective_id": "OBJ-MINOR",
                "strategic_weight_pct": 15.0,
                "linked_deliverables_count": 0,
                "target_benefit_value": 20000.0,
                "realized_or_projected_benefit_value": 20000.0,
                "benefit_owner_assigned": True,
                "measurement_kpi_defined": True,
            },
        ],
        min_strategic_weight_coverage_pct=80.0,
        max_benefit_shortfall_pct=15.0,
    )
    assert res["unlinked_objectives_count"] == 1
    assert res["missing_governance_objectives_count"] == 1
    assert res["benefit_shortfall_objectives_count"] == 0
    assert res["covered_strategic_weight_pct"] == 85.0
    assert res["strategic_alignment_status"] == "AT_RISK"
    assert len(res["findings"]) == 2


def test_audit_portfolio_strategic_alignment_and_benefits_drift_critical():
    """Verifica estado CRITICAL cuando existe déficit de beneficios sobre tolerancia o cobertura estratégica insuficiente."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_portfolio_strategic_alignment_and_benefits_drift,
    )

    res = audit_portfolio_strategic_alignment_and_benefits_drift(
        [
            {
                "objective_id": "OBJ-SHORTFALL",
                "strategic_weight_pct": 90.0,
                "linked_deliverables_count": 2,
                "target_benefit_value": 100000.0,
                "realized_or_projected_benefit_value": 70000.0,
                "benefit_owner_assigned": True,
                "measurement_kpi_defined": True,
            }
        ],
        min_strategic_weight_coverage_pct=80.0,
        max_benefit_shortfall_pct=15.0,
    )
    assert res["benefit_shortfall_objectives_count"] == 1
    assert res["strategic_alignment_status"] == "CRITICAL"
    assert res["findings"][0]["benefit_shortfall_pct"] == 30.0


def test_audit_portfolio_strategic_alignment_and_benefits_drift_empty_and_export():
    """Verifica manejo de entradas vacías o no secuencia y exportación en __all__."""
    import backend.services.project_lifecycle_pmi_service as mod
    from backend.services.project_lifecycle_pmi_service import (
        audit_portfolio_strategic_alignment_and_benefits_drift,
    )

    assert "audit_portfolio_strategic_alignment_and_benefits_drift" in mod.__all__
    for bad in ([], None, "invalid"):
        assert audit_portfolio_strategic_alignment_and_benefits_drift(bad) == {
            "total_objectives": 0,
            "compliant_objectives_count": 0,
            "unlinked_objectives_count": 0,
            "missing_governance_objectives_count": 0,
            "benefit_shortfall_objectives_count": 0,
            "covered_strategic_weight_pct": 100.0,
            "strategic_alignment_status": "HEALTHY",
            "findings": [],
        }



def test_audit_stage_gate_conditional_go_remediation_sla_healthy():
    """Compuertas sin anomalías: GO limpio y CONDITIONAL_GO dentro del SLA con owner."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_stage_gate_conditional_go_remediation_sla,
    )

    res = audit_stage_gate_conditional_go_remediation_sla(
        [
            {"gate_id": "G-1", "decision": "GO", "open_conditions_count": 0,
             "days_since_conditional_approval": 0, "next_phase_execution_started": True,
             "sponsor_waiver_signed": False, "remediation_owner_assigned": False},
            {"gate_id": "G-2", "decision": "conditional_go", "open_conditions_count": 2,
             "days_since_conditional_approval": 14, "next_phase_execution_started": False,
             "sponsor_waiver_signed": False, "remediation_owner_assigned": True},
        ]
    )
    assert res == {
        "total_gates_evaluated": 2,
        "compliant_gates_count": 2,
        "expired_conditional_gates_count": 0,
        "unauthorized_phase_advancement_count": 0,
        "unassigned_remediation_gates_count": 0,
        "stage_gate_governance_status": "HEALTHY",
        "violations": [],
    }


def test_audit_stage_gate_conditional_go_remediation_sla_critical():
    """Conditional-go vencido y avance no autorizado -> CRITICAL."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_stage_gate_conditional_go_remediation_sla,
    )

    res = audit_stage_gate_conditional_go_remediation_sla(
        [
            {"gate_id": "G-3", "decision": "CONDITIONAL_GO", "open_conditions_count": 1,
             "days_since_conditional_approval": 15, "next_phase_execution_started": False,
             "sponsor_waiver_signed": False, "remediation_owner_assigned": True},
            {"gate_id": "G-4", "decision": "HOLD", "open_conditions_count": 0,
             "days_since_conditional_approval": 0, "next_phase_execution_started": True,
             "sponsor_waiver_signed": False, "remediation_owner_assigned": False},
        ]
    )
    assert res["expired_conditional_gates_count"] == 1
    assert res["unauthorized_phase_advancement_count"] == 1
    assert res["compliant_gates_count"] == 0
    assert res["stage_gate_governance_status"] == "CRITICAL"
    assert res["violations"] == [
        {"gate_id": "G-3", "reasons": ["CONDITIONAL_GO_SLA_EXPIRED (15>14, 1 condiciones abiertas)"]},
        {"gate_id": "G-4", "reasons": ["UNAUTHORIZED_PHASE_ADVANCEMENT (HOLD sin dispensa del sponsor)"]},
    ]

    # Waiver firmado mitiga el avance no autorizado (KILL con waiver -> sin hallazgo).
    waived = audit_stage_gate_conditional_go_remediation_sla(
        [
            {"gate_id": "G-5", "decision": "KILL", "open_conditions_count": 0,
             "days_since_conditional_approval": 0, "next_phase_execution_started": True,
             "sponsor_waiver_signed": True, "remediation_owner_assigned": False},
        ]
    )
    assert waived["unauthorized_phase_advancement_count"] == 0
    assert waived["stage_gate_governance_status"] == "HEALTHY"


def test_audit_stage_gate_conditional_go_remediation_sla_at_risk():
    """Condiciones abiertas sin responsable -> AT_RISK (decision NO_GO sin avance)."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_stage_gate_conditional_go_remediation_sla,
    )

    res = audit_stage_gate_conditional_go_remediation_sla(
        [
            {"gate_id": "G-6", "decision": "NO_GO", "open_conditions_count": 2,
             "days_since_conditional_approval": 0, "next_phase_execution_started": False,
             "sponsor_waiver_signed": False, "remediation_owner_assigned": False},
        ]
    )
    assert res["unassigned_remediation_gates_count"] == 1
    assert res["compliant_gates_count"] == 0
    assert res["stage_gate_governance_status"] == "AT_RISK"
    assert res["violations"] == [
        {"gate_id": "G-6", "reasons": ["REMEDIATION_OWNER_UNASSIGNED"]},
    ]


def test_audit_stage_gate_conditional_go_remediation_sla_custom_and_empty():
    """Umbrales custom, entrada vacia/None y proxy estatico + __all__."""
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_stage_gate_conditional_go_remediation_sla,
    )
    import backend.services.project_lifecycle_pmi_service as mod

    custom = audit_stage_gate_conditional_go_remediation_sla(
        [
            {"gate_id": "G-7", "decision": "CONDITIONAL_GO", "open_conditions_count": 1,
             "days_since_conditional_approval": 6, "next_phase_execution_started": False,
             "sponsor_waiver_signed": False, "remediation_owner_assigned": True},
        ],
        max_conditional_remediation_days=5,
    )
    assert custom["expired_conditional_gates_count"] == 1
    assert custom["stage_gate_governance_status"] == "CRITICAL"

    for payload in ([], None, 42):
        empty = audit_stage_gate_conditional_go_remediation_sla(payload)
        assert empty["total_gates_evaluated"] == 0
        assert empty["stage_gate_governance_status"] == "HEALTHY"
        assert empty["violations"] == []

    sample = [{"gate_id": "SM", "decision": "GO", "open_conditions_count": 0,
               "days_since_conditional_approval": 0, "next_phase_execution_started": False,
               "sponsor_waiver_signed": False, "remediation_owner_assigned": False}]
    assert (
        ProjectLifecyclePMIService.audit_stage_gate_conditional_go_remediation_sla(sample)
        == audit_stage_gate_conditional_go_remediation_sla(sample)
    )
    assert "audit_stage_gate_conditional_go_remediation_sla" in mod.__all__


def test_audit_team_virtual_overlap_and_onboarding_readiness_healthy():
    """Equipo con traslape remoto >= 3h, accesos provisionados en <= 5d y Team Charter firmado -> HEALTHY."""
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_team_virtual_overlap_and_onboarding_readiness,
    )

    members = [
        {
            "member_id": "DEV-01",
            "is_remote": True,
            "daily_core_overlap_hours": 4.5,
            "access_and_tooling_provisioned": True,
            "onboarding_lead_days": 3,
            "team_charter_acknowledged": True,
        },
        {
            "member_id": "QA-02",
            "is_remote": False,
            "daily_core_overlap_hours": 0.0,
            "access_and_tooling_provisioned": True,
            "onboarding_lead_days": 5,
            "team_charter_acknowledged": True,
        },
    ]
    res = audit_team_virtual_overlap_and_onboarding_readiness(members)
    assert res == {
        "total_team_members": 2,
        "ready_members_count": 2,
        "insufficient_overlap_members_count": 0,
        "delayed_onboarding_members_count": 0,
        "unacknowledged_charter_members_count": 0,
        "team_readiness_pct": 100.0,
        "team_onboarding_governance_status": "HEALTHY",
        "violations": [],
    }
    assert (
        ProjectLifecyclePMIService.audit_team_virtual_overlap_and_onboarding_readiness(
            members
        )
        == res
    )


def test_audit_team_virtual_overlap_and_onboarding_readiness_critical_onboarding():
    """Detecta falta de provision de herramientas o demora de onboarding > max_onboarding_lead_days como CRITICAL."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_team_virtual_overlap_and_onboarding_readiness,
    )

    res = audit_team_virtual_overlap_and_onboarding_readiness(
        [
            {
                "member_id": "DEV-UNPROV",
                "is_remote": True,
                "daily_core_overlap_hours": 4.0,
                "access_and_tooling_provisioned": False,
                "onboarding_lead_days": 2,
                "team_charter_acknowledged": True,
            },
            {
                "member_id": "DEV-SLOW",
                "is_remote": False,
                "daily_core_overlap_hours": 8.0,
                "access_and_tooling_provisioned": True,
                "onboarding_lead_days": 9,
                "team_charter_acknowledged": True,
            },
        ],
        min_daily_overlap_hours=3.0,
        max_onboarding_lead_days=5,
    )
    assert res["total_team_members"] == 2
    assert res["ready_members_count"] == 0
    assert res["delayed_onboarding_members_count"] == 2
    assert res["team_readiness_pct"] == 0.0
    assert res["team_onboarding_governance_status"] == "CRITICAL"
    assert len(res["violations"]) == 2
    assert res["violations"][0]["member_id"] == "DEV-UNPROV"
    assert "delayed_or_unprovisioned_onboarding" in res["violations"][0]["reasons"]
    assert res["violations"][1]["member_id"] == "DEV-SLOW"
    assert "delayed_or_unprovisioned_onboarding" in res["violations"][1]["reasons"]


def test_audit_team_virtual_overlap_and_onboarding_readiness_at_risk_overlap_or_charter():
    """Detecta traslape horario insuficiente en remoto o falta de firma del Team Charter sin bloqueo de accesos como AT_RISK."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_team_virtual_overlap_and_onboarding_readiness,
    )

    res = audit_team_virtual_overlap_and_onboarding_readiness(
        [
            {
                "member_id": "REM-LOW-OVERLAP",
                "is_remote": True,
                "daily_core_overlap_hours": 1.5,
                "access_and_tooling_provisioned": True,
                "onboarding_lead_days": 2,
                "team_charter_acknowledged": True,
            },
            {
                "member_id": "COLOC-NO-CHARTER",
                "is_remote": False,
                "daily_core_overlap_hours": 8.0,
                "access_and_tooling_provisioned": True,
                "onboarding_lead_days": 1,
                "team_charter_acknowledged": False,
            },
            {
                "member_id": "REM-READY",
                "is_remote": True,
                "daily_core_overlap_hours": 5.0,
                "access_and_tooling_provisioned": True,
                "onboarding_lead_days": 2,
                "team_charter_acknowledged": True,
            },
        ],
        min_daily_overlap_hours=3.0,
        max_onboarding_lead_days=5,
    )
    assert res["total_team_members"] == 3
    assert res["ready_members_count"] == 1
    assert res["insufficient_overlap_members_count"] == 1
    assert res["delayed_onboarding_members_count"] == 0
    assert res["unacknowledged_charter_members_count"] == 1
    assert res["team_readiness_pct"] == 33.33
    assert res["team_onboarding_governance_status"] == "AT_RISK"
    assert len(res["violations"]) == 2


def test_audit_team_virtual_overlap_and_onboarding_readiness_empty_and_export():
    """Maneja entradas vacias o invalidas devolviendo 100.0% HEALTHY y verifica exportacion en __all__."""
    import backend.services.project_lifecycle_pmi_service as mod
    from backend.services.project_lifecycle_pmi_service import (
        audit_team_virtual_overlap_and_onboarding_readiness,
    )

    assert "audit_team_virtual_overlap_and_onboarding_readiness" in mod.__all__
    for payload in ([], None, "invalid"):
        empty = audit_team_virtual_overlap_and_onboarding_readiness(payload)  # type: ignore[arg-type]
        assert empty == {
            "total_team_members": 0,
            "ready_members_count": 0,
            "insufficient_overlap_members_count": 0,
            "delayed_onboarding_members_count": 0,
            "unacknowledged_charter_members_count": 0,
            "team_readiness_pct": 100.0,
            "team_onboarding_governance_status": "HEALTHY",
            "violations": [],
        }



def test_audit_post_implementation_handover_healthy():
    """Items con owner BAU, runbook al minimo, hypercare firmado, PIR y beneficio alcanzado."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_post_implementation_benefits_sustainment_and_handover,
    )

    res = audit_post_implementation_benefits_sustainment_and_handover(
        [
            {"item_id": "T-1", "bau_owner_assigned": True, "runbook_coverage_pct": 95.0,
             "hypercare_days": 30, "hypercare_exit_signed": True, "pir_completed": True,
             "realized_benefit_pct": 85.0},
            {"item_id": "T-2", "bau_owner_assigned": True, "runbook_coverage_pct": 90.0,
             "hypercare_days": 60, "hypercare_exit_signed": True, "pir_completed": True,
             "realized_benefit_pct": 80.0},
        ]
    )
    assert res == {
        "total_items": 2,
        "compliant_items_count": 2,
        "unowned_or_undocumented_handover_count": 0,
        "hypercare_or_pir_gap_count": 0,
        "benefits_sustainment_shortfall_count": 0,
        "sustainment_governance_status": "HEALTHY",
        "violations": [],
    }


def test_audit_post_implementation_handover_critical():
    """Owner ausente + runbook bajo minimo + shortfall de beneficios -> CRITICAL."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_post_implementation_benefits_sustainment_and_handover,
    )

    crit = audit_post_implementation_benefits_sustainment_and_handover(
        [
            {"item_id": "T-3", "bau_owner_assigned": False, "runbook_coverage_pct": 70.0,
             "hypercare_days": 30, "hypercare_exit_signed": True, "pir_completed": True,
             "realized_benefit_pct": 60.0},
        ]
    )
    assert crit["unowned_or_undocumented_handover_count"] == 1
    assert crit["benefits_sustainment_shortfall_count"] == 1
    assert crit["hypercare_or_pir_gap_count"] == 0
    assert crit["compliant_items_count"] == 0
    assert crit["sustainment_governance_status"] == "CRITICAL"
    assert crit["violations"][0]["reasons"] == [
        "BAU_OWNER_UNASSIGNED",
        "RUNBOOK_COVERAGE_UNDER_MIN (70.0<90.0)",
        "BENEFIT_REALIZATION_SHORTFALL (60.0<80.0)",
    ]


def test_audit_post_implementation_handover_at_risk_and_borders():
    """Hypercare vencido / exit sin firmar / PIR incompleta -> AT_RISK; bordes inclusivos."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_post_implementation_benefits_sustainment_and_handover,
    )

    risk = audit_post_implementation_benefits_sustainment_and_handover(
        [
            {"item_id": "T-4", "bau_owner_assigned": True, "runbook_coverage_pct": 95.0,
             "hypercare_days": 61, "hypercare_exit_signed": False, "pir_completed": False,
             "realized_benefit_pct": 85.0},
        ]
    )
    assert risk["hypercare_or_pir_gap_count"] == 1
    assert risk["compliant_items_count"] == 0
    assert risk["sustainment_governance_status"] == "AT_RISK"
    assert risk["violations"][0]["reasons"] == [
        "HYPERCARE_OVER_MAX (61>60)", "HYPERCARE_EXIT_UNSIGNED", "PIR_NOT_COMPLETED",
    ]

    # Bordes inclusivos: hypercare == max, coverage == min, benefit == min -> HEALTHY.
    border = audit_post_implementation_benefits_sustainment_and_handover(
        [
            {"item_id": "T-5", "bau_owner_assigned": True, "runbook_coverage_pct": 90.0,
             "hypercare_days": 60, "hypercare_exit_signed": True, "pir_completed": True,
             "realized_benefit_pct": 80.0},
        ]
    )
    assert border["sustainment_governance_status"] == "HEALTHY"

    # Umbral custom: hypercare 11 > max 10 -> gap -> AT_RISK.
    custom = audit_post_implementation_benefits_sustainment_and_handover(
        [
            {"item_id": "T-6", "bau_owner_assigned": True, "runbook_coverage_pct": 100.0,
             "hypercare_days": 11, "hypercare_exit_signed": True, "pir_completed": True,
             "realized_benefit_pct": 95.0},
        ],
        min_runbook_coverage_pct=100.0,
        max_hypercare_days=10,
        min_benefit_realization_pct=90.0,
    )
    assert custom["hypercare_or_pir_gap_count"] == 1
    assert custom["sustainment_governance_status"] == "AT_RISK"

    # Coverage 99.5 < min 100 -> unowned -> CRITICAL (per spec el unowned gl cae en CRITICAL).
    few = audit_post_implementation_benefits_sustainment_and_handover(
        [
            {"item_id": "T-7", "bau_owner_assigned": True, "runbook_coverage_pct": 99.5,
             "hypercare_days": 5, "hypercare_exit_signed": True, "pir_completed": True,
             "realized_benefit_pct": 90.0},
        ],
        min_runbook_coverage_pct=100.0,
        max_hypercare_days=10,
        min_benefit_realization_pct=90.0,
    )
    assert few["unowned_or_undocumented_handover_count"] == 1
    assert few["sustainment_governance_status"] == "CRITICAL"
    assert few["violations"][0]["reasons"] == ["RUNBOOK_COVERAGE_UNDER_MIN (99.5<100.0)"]


def test_audit_post_implementation_handover_custom_and_empty():
    """Entrada vacia/None/no-lista y proxy estatico + __all__."""
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_post_implementation_benefits_sustainment_and_handover,
    )
    import backend.services.project_lifecycle_pmi_service as mod

    for payload in ([], None, 42, ["x"]):
        empty = audit_post_implementation_benefits_sustainment_and_handover(payload)
        assert empty["total_items"] == 0
        assert empty["sustainment_governance_status"] == "HEALTHY"
        assert empty["violations"] == []

    sample = [{"item_id": "SM", "bau_owner_assigned": True, "runbook_coverage_pct": 95.0,
               "hypercare_days": 10, "hypercare_exit_signed": True, "pir_completed": True,
               "realized_benefit_pct": 85.0}]
    assert (
        ProjectLifecyclePMIService.audit_post_implementation_benefits_sustainment_and_handover(sample)
        == audit_post_implementation_benefits_sustainment_and_handover(sample)
    )
    assert "audit_post_implementation_benefits_sustainment_and_handover" in mod.__all__


def test_audit_project_charter_measurable_criteria_and_authority_healthy():
    """Secciones de Charter completas con KPIs medibles, criterios de salida, autoridad del PM y firma independiente del Sponsor."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_project_charter_measurable_criteria_and_authority,
    )

    sections = [
        {
            "id": "CHR-01",
            "measurable_kpis_count": 2,
            "exit_criteria_defined": True,
            "pm_authority_documented": True,
            "sponsor_signed": True,
            "assigned_pm_is_also_sponsor": False,
        },
        {
            "id": "CHR-02",
            "measurable_kpis_count": 3,
            "exit_criteria_defined": True,
            "pm_authority_documented": True,
            "sponsor_signed": True,
            "assigned_pm_is_also_sponsor": False,
        },
    ]
    res = audit_project_charter_measurable_criteria_and_authority(sections)
    assert res["total_sections"] == 2
    assert res["compliant_sections"] == 2
    assert res["unmeasurable_objective_ids"] == []
    assert res["missing_pm_authority_ids"] == []
    assert res["unauthorized_or_conflicted_signoff_ids"] == []
    assert res["charter_maturity_score"] == 100.0
    assert res["charter_governance_health"] == "healthy"
    assert res["is_compliant"] is True
    assert res["recommendations"] == []


def test_audit_project_charter_measurable_criteria_and_authority_at_risk():
    """Detecta unmeasurable_objective_ids y missing_pm_authority_ids (charter_governance_health == 'at_risk')."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_project_charter_measurable_criteria_and_authority,
    )

    sections = [
        {
            "section_id": "CHR-10",
            "measurable_kpis_count": 0,
            "exit_criteria_defined": False,
            "pm_authority_documented": True,
            "sponsor_signed": True,
            "assigned_pm_is_also_sponsor": False,
        },
        {
            "section_id": "CHR-11",
            "measurable_kpis_count": 2,
            "exit_criteria_defined": True,
            "pm_authority_documented": False,
            "sponsor_signed": True,
            "assigned_pm_is_also_sponsor": False,
        },
    ]
    res = audit_project_charter_measurable_criteria_and_authority(sections)
    assert res["total_sections"] == 2
    assert res["compliant_sections"] == 0
    assert res["unmeasurable_objective_ids"] == ["CHR-10"]
    assert res["missing_pm_authority_ids"] == ["CHR-11"]
    assert res["unauthorized_or_conflicted_signoff_ids"] == []
    assert res["charter_maturity_score"] == 0.0
    assert res["charter_governance_health"] == "at_risk"
    assert res["is_compliant"] is False
    assert len(res["recommendations"]) >= 2


def test_audit_project_charter_measurable_criteria_and_authority_critical_signoff():
    """Detecta falta de firma del sponsor o conflicto de segregación de funciones (assigned_pm_is_also_sponsor=True -> 'critical')."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_project_charter_measurable_criteria_and_authority,
    )

    sections = [
        {
            "objective_id": "CHR-20",
            "measurable_kpis_count": 1,
            "exit_criteria_defined": True,
            "pm_authority_documented": True,
            "sponsor_signed": False,
            "assigned_pm_is_also_sponsor": False,
        },
        {
            "objective_id": "CHR-21",
            "measurable_kpis_count": 2,
            "exit_criteria_defined": True,
            "pm_authority_documented": True,
            "sponsor_signed": True,
            "assigned_pm_is_also_sponsor": True,
        },
    ]
    res = audit_project_charter_measurable_criteria_and_authority(sections)
    assert res["total_sections"] == 2
    assert res["compliant_sections"] == 0
    assert res["unauthorized_or_conflicted_signoff_ids"] == ["CHR-20", "CHR-21"]
    assert res["charter_governance_health"] == "critical"
    assert res["is_compliant"] is False
    assert len(res["recommendations"]) >= 1


def test_audit_project_charter_measurable_criteria_and_authority_empty_and_service_binding():
    """Manejo defensivo de entradas vacías/no-secuencia y exposición en ProjectLifecyclePMIService y __all__."""
    import backend.services.project_lifecycle_pmi_service as mod
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_project_charter_measurable_criteria_and_authority,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = audit_project_charter_measurable_criteria_and_authority(payload)  # type: ignore[arg-type]
        assert empty["total_sections"] == 0
        assert empty["compliant_sections"] == 0
        assert empty["charter_maturity_score"] == 100.0
        assert empty["charter_governance_health"] == "healthy"
        assert empty["is_compliant"] is True
        assert empty["recommendations"] == []

    sample = [
        {
            "id": "CHR-99",
            "measurable_kpis_count": 1,
            "exit_criteria_defined": True,
            "pm_authority_documented": True,
            "sponsor_signed": True,
            "assigned_pm_is_also_sponsor": False,
        }
    ]
    assert (
        ProjectLifecyclePMIService.audit_project_charter_measurable_criteria_and_authority(
            sample
        )
        == audit_project_charter_measurable_criteria_and_authority(sample)
    )
    assert "audit_project_charter_measurable_criteria_and_authority" in mod.__all__


def test_audit_stakeholder_power_interest_and_salience_drift_healthy():
    """Valida cumplimiento en los 4 cuadrantes Poder-Interés sin resistencia ni abandono de cadencia."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_stakeholder_power_interest_and_salience_drift,
    )

    stakeholders = [
        {
            "id": "STK-01",
            "power_score": 5,
            "interest_score": 5,
            "assigned_strategy": "manage_closely",
            "current_engagement": "leading",
            "desired_engagement": "supportive",
            "days_since_last_touchpoint": 7,
        },
        {
            "id": "STK-02",
            "power_score": 4,
            "interest_score": 2,
            "assigned_strategy": "keep_satisfied",
            "current_engagement": "supportive",
            "desired_engagement": "supportive",
            "days_since_last_touchpoint": 20,
        },
        {
            "id": "STK-03",
            "power_score": 2,
            "interest_score": 5,
            "assigned_strategy": "keep_informed",
            "current_engagement": "supportive",
            "desired_engagement": "supportive",
            "days_since_last_touchpoint": 10,
        },
        {
            "id": "STK-04",
            "power_score": 1,
            "interest_score": 2,
            "assigned_strategy": "monitor",
            "current_engagement": "neutral",
            "desired_engagement": "neutral",
            "days_since_last_touchpoint": 30,
        },
    ]
    res = audit_stakeholder_power_interest_and_salience_drift(stakeholders)
    assert res["total_stakeholders"] == 4
    assert res["compliant_stakeholders"] == 4
    assert res["quadrant_strategy_mismatch_ids"] == []
    assert res["high_power_resistant_or_gap_ids"] == []
    assert res["neglected_manage_closely_ids"] == []
    assert res["stakeholder_governance_health"] == "healthy"
    assert res["is_compliant"] is True
    assert res["recommendations"] == []


def test_audit_stakeholder_power_interest_and_salience_drift_at_risk():
    """Detecta desalineación de cuadrante y abandono de touchpoint en manage_closely sin brecha de alto poder ('at_risk')."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_stakeholder_power_interest_and_salience_drift,
    )

    stakeholders = [
        {
            "stakeholder_id": "STK-10",
            "power_score": 2,
            "interest_score": 5,
            "assigned_strategy": "monitor",
            "current_engagement": "supportive",
            "desired_engagement": "supportive",
            "days_since_last_touchpoint": 5,
        },
        {
            "stakeholder_id": "STK-11",
            "power_score": 5,
            "interest_score": 4,
            "assigned_strategy": "manage_closely",
            "current_engagement": "leading",
            "desired_engagement": "leading",
            "days_since_last_touchpoint": 21,
        },
    ]
    res = audit_stakeholder_power_interest_and_salience_drift(stakeholders)
    assert res["total_stakeholders"] == 2
    assert res["compliant_stakeholders"] == 0
    assert res["quadrant_strategy_mismatch_ids"] == ["STK-10"]
    assert res["high_power_resistant_or_gap_ids"] == []
    assert res["neglected_manage_closely_ids"] == ["STK-11"]
    assert res["stakeholder_governance_health"] == "at_risk"
    assert res["is_compliant"] is False
    assert len(res["recommendations"]) >= 2


def test_audit_stakeholder_power_interest_and_salience_drift_critical_high_power():
    """Detecta interesado de alto poder resistente o con brecha current < desired ('critical')."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_stakeholder_power_interest_and_salience_drift,
    )

    stakeholders = [
        {
            "id": "STK-20",
            "power_score": 5,
            "interest_score": 5,
            "assigned_strategy": "manage_closely",
            "current_engagement": "resistant",
            "desired_engagement": "resistant",
            "days_since_last_touchpoint": 3,
        },
        {
            "id": "STK-21",
            "power_score": 4,
            "interest_score": 2,
            "assigned_strategy": "keep_satisfied",
            "current_engagement": "neutral",
            "desired_engagement": "supportive",
            "days_since_last_touchpoint": 5,
        },
    ]
    res = audit_stakeholder_power_interest_and_salience_drift(stakeholders)
    assert res["total_stakeholders"] == 2
    assert res["compliant_stakeholders"] == 0
    assert res["high_power_resistant_or_gap_ids"] == ["STK-20", "STK-21"]
    assert res["stakeholder_governance_health"] == "critical"
    assert res["is_compliant"] is False
    assert len(res["recommendations"]) >= 1


def test_audit_stakeholder_power_interest_and_salience_drift_empty_and_service_binding():
    """Manejo defensivo de entradas vacías/no-secuencia y exposición en ProjectLifecyclePMIService y __all__."""
    import backend.services.project_lifecycle_pmi_service as mod
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_stakeholder_power_interest_and_salience_drift,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = audit_stakeholder_power_interest_and_salience_drift(payload)  # type: ignore[arg-type]
        assert empty["total_stakeholders"] == 0
        assert empty["compliant_stakeholders"] == 0
        assert empty["quadrant_strategy_mismatch_ids"] == []
        assert empty["high_power_resistant_or_gap_ids"] == []
        assert empty["neglected_manage_closely_ids"] == []
        assert empty["stakeholder_governance_health"] == "healthy"
        assert empty["is_compliant"] is True
        assert empty["recommendations"] == []

    sample = [
        {
            "id": "STK-99",
            "power_score": 5,
            "interest_score": 5,
            "assigned_strategy": "manage_closely",
            "current_engagement": "supportive",
            "desired_engagement": "supportive",
            "days_since_last_touchpoint": 4,
        }
    ]
    assert (
        ProjectLifecyclePMIService.audit_stakeholder_power_interest_and_salience_drift(
            sample
        )
        == audit_stakeholder_power_interest_and_salience_drift(sample)
    )
    assert "audit_stakeholder_power_interest_and_salience_drift" in mod.__all__




def test_ocm_adkar_adoption_healthy_and_critical():
    """Unidad conforme -> compliant; champion ausente + go-live prematuro -> CRITICAL."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_organizational_change_management_adkar_and_adoption,
    )

    healthy = audit_organizational_change_management_adkar_and_adoption(
        [
            {
                "unit_id": "BU-1",
                "change_champion_assigned": True,
                "training_completion_pct": 90.0,
                "active_adoption_pct": 80.0,
                "min_adkar_score": 4.0,
                "go_live_approved": True,
            }
        ]
    )
    assert healthy["total_units"] == 1
    assert healthy["compliant_units_count"] == 1
    assert healthy["unchampioned_or_premature_golive_count"] == 0
    assert healthy["adkar_barrier_or_training_gap_count"] == 0
    assert healthy["post_launch_adoption_shortfall_count"] == 0
    assert healthy["ocm_governance_status"] == "HEALTHY"
    assert healthy["violations"] == []

    critical = audit_organizational_change_management_adkar_and_adoption(
        [
            {
                "unit_id": "BU-2",
                "change_champion_assigned": False,
                "training_completion_pct": 40.0,
                "active_adoption_pct": 30.0,
                "min_adkar_score": 2.0,
                "go_live_approved": True,
            }
        ]
    )
    assert critical["violations"][0]["unit_id"] == "BU-2"
    assert critical["violations"][0]["reasons"] == [
        "unchampioned_or_premature_golive",
        "adkar_barrier_or_training_gap",
        "post_launch_adoption_shortfall",
    ]
    assert critical["unchampioned_or_premature_golive_count"] == 1
    assert critical["post_launch_adoption_shortfall_count"] == 1
    assert critical["ocm_governance_status"] == "CRITICAL"

    # Champion asignado y adopción OK, pero go_live con entrenamiento insuficiente.
    premature = audit_organizational_change_management_adkar_and_adoption(
        [
            {
                "unit_id": "BU-3",
                "change_champion_assigned": True,
                "training_completion_pct": 84.9,
                "active_adoption_pct": 90.0,
                "min_adkar_score": 4.0,
                "go_live_approved": True,
            }
        ]
    )
    assert premature["violations"][0]["reasons"] == [
        "unchampioned_or_premature_golive",
        "adkar_barrier_or_training_gap",
    ]
    assert premature["adkar_barrier_or_training_gap_count"] == 1
    assert premature["ocm_governance_status"] == "CRITICAL"


def test_ocm_adkar_adoption_at_risk_and_thresholds():
    """Solo barrera ADKAR o brecha de entrenamiento -> AT_RISK; umbrales custom; límites."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_organizational_change_management_adkar_and_adoption,
    )

    at_risk = audit_organizational_change_management_adkar_and_adoption(
        [
            {
                "unit_id": "BU-4",
                "change_champion_assigned": True,
                "training_completion_pct": 80.0,
                "min_adkar_score": 4.0,
            }
        ]
    )
    assert at_risk["adkar_barrier_or_training_gap_count"] == 1
    assert at_risk["violations"][0]["reasons"] == ["adkar_barrier_or_training_gap"]
    assert at_risk["ocm_governance_status"] == "AT_RISK"

    adkar_only = audit_organizational_change_management_adkar_and_adoption(
        [{"unit_id": "BU-5", "change_champion_assigned": True, "min_adkar_score": 3.4}]
    )
    assert adkar_only["adkar_barrier_or_training_gap_count"] == 1
    assert adkar_only["ocm_governance_status"] == "AT_RISK"

    total = audit_organizational_change_management_adkar_and_adoption(
        [
            {
                "unit_id": "BU-6",
                "change_champion_assigned": True,
                "training_completion_pct": 90.0,
                "min_adkar_score": 4.5,
                "go_live_approved": True,
                "active_adoption_pct": 80.0,
            }
        ],
        min_adkar_dimension_score=4.8,
    )
    assert total["adkar_barrier_or_training_gap_count"] == 1
    assert total["ocm_governance_status"] == "AT_RISK"

    # Sin go_live aprobado no hay shortfall de adopción aunque la adopción baje:
    not_launched = audit_organizational_change_management_adkar_and_adoption(
        [
            {
                "unit_id": "BU-7",
                "change_champion_assigned": True,
                "training_completion_pct": 90.0,
                "min_adkar_score": 4.0,
                "active_adoption_pct": 10.0,
            }
        ]
    )
    assert not_launched["post_launch_adoption_shortfall_count"] == 0
    assert not_launched["ocm_governance_status"] == "HEALTHY"

    # Límites exactos: min_adkar_score == umbral NO barrera; adopt pct == min NO shortfall.
    boundary = audit_organizational_change_management_adkar_and_adoption(
        [
            {
                "unit_id": "BU-8",
                "change_champion_assigned": True,
                "training_completion_pct": 85.0,
                "min_adkar_score": 3.5,
                "go_live_approved": True,
                "active_adoption_pct": 75.0,
            }
        ]
    )
    assert boundary["ocm_governance_status"] == "HEALTHY"
    assert boundary["compliant_units_count"] == 1


def test_ocm_adkar_adoption_ignores_bad_entries():
    """No-lista/None -> vacío; elementos no-dict ignorados; dict sin champion -> regla 1."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_organizational_change_management_adkar_and_adoption,
    )

    for payload in (None, "not-a-list", 42):
        empty = audit_organizational_change_management_adkar_and_adoption(payload)
        assert empty["total_units"] == 0
        assert empty["compliant_units_count"] == 0
        assert empty["ocm_governance_status"] == "HEALTHY"
        assert empty["violations"] == []

    mixed = audit_organizational_change_management_adkar_and_adoption(
        [
            "no-dict",
            42,
            None,
            {
                "unit_id": "BU-9",
                "change_champion_assigned": True,
                "training_completion_pct": 100.0,
                "min_adkar_score": 5.0,
            },
        ]
    )
    assert mixed["total_units"] == 1
    assert mixed["compliant_units_count"] == 1
    assert mixed["violations"] == []

    # Sin champion: regla 1 dispara pese a métricas sanas.
    bare = audit_organizational_change_management_adkar_and_adoption(
        [
            {
                "unit_id": "BU-10",
                "training_completion_pct": 100.0,
                "min_adkar_score": 5.0,
            }
        ]
    )
    assert bare["violations"][0]["reasons"] == ["unchampioned_or_premature_golive"]
    assert bare["ocm_governance_status"] == "CRITICAL"


def test_ocm_adkar_adoption_precedence_and_binding():
    """Precedencia CRITICAL > AT_RISK; proxy @staticmethod y __all__."""
    import backend.services.project_lifecycle_pmi_service as mod
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_organizational_change_management_adkar_and_adoption,
    )

    # Champion OK + múltiple shortfall solo vía adopción -> 2 conteos distintos correlacionados.
    multi_units = audit_organizational_change_management_adkar_and_adoption(
        [
            {
                "unit_id": "BU-11",
                "change_champion_assigned": True,
                "training_completion_pct": 90.0,
                "min_adkar_score": 4.0,
                "go_live_approved": True,
                "active_adoption_pct": 20.0,
            }
        ]
    )
    assert multi_units["post_launch_adoption_shortfall_count"] == 1
    assert multi_units["ocm_governance_status"] == "CRITICAL"

    # AT_RISK se reporta solo si NO hay nada critical.
    at_risk_mixed = audit_organizational_change_management_adkar_and_adoption(
        [
            {
                "unit_id": "BU-12",
                "change_champion_assigned": True,
                "training_completion_pct": 50.0,
                "min_adkar_score": 4.0,
            },
            {
                "unit_id": "BU-13",
                "change_champion_assigned": True,
                "training_completion_pct": 90.0,
                "min_adkar_score": 1.0,
            },
        ]
    )
    assert at_risk_mixed["adkar_barrier_or_training_gap_count"] == 2
    assert at_risk_mixed["unchampioned_or_premature_golive_count"] == 0
    assert at_risk_mixed["ocm_governance_status"] == "AT_RISK"

    sample = [
        {
            "unit_id": "BU-14",
            "change_champion_assigned": False,
        }
    ]
    assert (
        ProjectLifecyclePMIService.audit_organizational_change_management_adkar_and_adoption(sample)
        == audit_organizational_change_management_adkar_and_adoption(sample)
    )
    assert "audit_organizational_change_management_adkar_and_adoption" in mod.__all__


def test_audit_project_administrative_and_contract_closure_readiness_healthy():
    """Valida expediente de cierre completo con aceptación final, 0 reclamos, cuentas cerradas, OPA archivado y liberación de equipo."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_project_administrative_and_contract_closure_readiness,
    )

    dossiers = [
        {
            "id": "CLS-01",
            "final_product_acceptance_signed": True,
            "open_procurement_claims_count": 0,
            "financial_charge_codes_closed": True,
            "lessons_archived_in_opa": True,
            "team_resources_formally_released": True,
        }
    ]
    res = audit_project_administrative_and_contract_closure_readiness(dossiers)
    assert res["total_dossiers"] == 1
    assert res["compliant_dossiers"] == 1
    assert res["unaccepted_or_open_claims_ids"] == []
    assert res["open_charge_codes_ghost_billing_ids"] == []
    assert res["incomplete_opa_or_resource_release_ids"] == []
    assert res["closure_governance_health"] == "healthy"
    assert res["is_compliant"] is True
    assert res["recommendations"] == []


def test_audit_project_administrative_and_contract_closure_readiness_at_risk():
    """Detecta falta de archivo en OPA o recursos de equipo no liberados sin reclamos ni cuentas abiertas ('at_risk')."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_project_administrative_and_contract_closure_readiness,
    )

    dossiers = [
        {
            "dossier_id": "CLS-10",
            "final_product_acceptance_signed": True,
            "open_procurement_claims_count": 0,
            "financial_charge_codes_closed": True,
            "lessons_archived_in_opa": False,
            "team_resources_formally_released": True,
        },
        {
            "dossier_id": "CLS-11",
            "final_product_acceptance_signed": True,
            "open_procurement_claims_count": 0,
            "financial_charge_codes_closed": True,
            "lessons_archived_in_opa": True,
            "team_resources_formally_released": False,
        },
    ]
    res = audit_project_administrative_and_contract_closure_readiness(dossiers)
    assert res["total_dossiers"] == 2
    assert res["compliant_dossiers"] == 0
    assert res["incomplete_opa_or_resource_release_ids"] == ["CLS-10", "CLS-11"]
    assert res["unaccepted_or_open_claims_ids"] == []
    assert res["open_charge_codes_ghost_billing_ids"] == []
    assert res["closure_governance_health"] == "at_risk"
    assert res["is_compliant"] is False
    assert len(res["recommendations"]) >= 1


def test_audit_project_administrative_and_contract_closure_readiness_critical():
    """Detecta producto sin aceptación/reclamos abiertos y códigos de cargo financiero abiertos ('critical')."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_project_administrative_and_contract_closure_readiness,
    )

    dossiers = [
        {
            "dossier_id": "CLS-20",
            "final_product_acceptance_signed": False,
            "open_procurement_claims_count": 2,
            "financial_charge_codes_closed": True,
            "lessons_archived_in_opa": True,
            "team_resources_formally_released": True,
        },
        {
            "dossier_id": "CLS-21",
            "final_product_acceptance_signed": True,
            "open_procurement_claims_count": 0,
            "financial_charge_codes_closed": False,
            "lessons_archived_in_opa": True,
            "team_resources_formally_released": True,
        },
    ]
    res = audit_project_administrative_and_contract_closure_readiness(dossiers)
    assert res["total_dossiers"] == 2
    assert res["compliant_dossiers"] == 0
    assert res["unaccepted_or_open_claims_ids"] == ["CLS-20"]
    assert res["open_charge_codes_ghost_billing_ids"] == ["CLS-21"]
    assert res["closure_governance_health"] == "critical"
    assert res["is_compliant"] is False
    assert len(res["recommendations"]) >= 2


def test_audit_project_administrative_and_contract_closure_readiness_empty_and_service_binding():
    """Manejo defensivo de entradas vacías/no-secuencia y exposición en ProjectLifecyclePMIService y __all__."""
    import backend.services.project_lifecycle_pmi_service as mod
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_project_administrative_and_contract_closure_readiness,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = audit_project_administrative_and_contract_closure_readiness(payload)  # type: ignore[arg-type]
        assert empty["total_dossiers"] == 0
        assert empty["compliant_dossiers"] == 0
        assert empty["unaccepted_or_open_claims_ids"] == []
        assert empty["open_charge_codes_ghost_billing_ids"] == []
        assert empty["incomplete_opa_or_resource_release_ids"] == []
        assert empty["closure_governance_health"] == "healthy"
        assert empty["is_compliant"] is True
        assert empty["recommendations"] == []

    sample = [
        {
            "id": "CLS-99",
            "final_product_acceptance_signed": True,
            "open_procurement_claims_count": 0,
            "financial_charge_codes_closed": True,
            "lessons_archived_in_opa": True,
            "team_resources_formally_released": True,
        }
    ]
    assert (
        ProjectLifecyclePMIService.audit_project_administrative_and_contract_closure_readiness(
            sample
        )
        == audit_project_administrative_and_contract_closure_readiness(sample)
    )
    assert (
        "audit_project_administrative_and_contract_closure_readiness"
        in mod.__all__
    )



def test_portfolio_strategic_alignment_esg_aligned_and_misaligned():
    """Cobertura 100% + ESG completo -> ALIGNED; lista vacía/ESG sin mitigar/cobertura baja -> MISALIGNED."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_portfolio_strategic_alignment_and_esg_sustainability,
    )

    aligned = audit_portfolio_strategic_alignment_and_esg_sustainability(
        [
            {
                "objective_id": "O-1",
                "weight_pct": 60.0,
                "has_measurable_kr": True,
                "kr_confidence_pct": 85.0,
                "is_aligned": True,
            },
            {
                "objective_id": "O-2",
                "weight_pct": 40.0,
                "has_measurable_kr": True,
                "kr_confidence_pct": 90.0,
                "is_aligned": True,
            },
        ],
        esg_pillars={
            "environmental_impact_assessed": True,
            "social_community_benefit_documented": True,
            "governance_ethics_cleared": True,
            "high_carbon_or_social_risk_unmitigated": False,
        },
    )
    assert aligned["total_objectives"] == 2
    assert aligned["covered_weight_pct"] == 100.0
    assert aligned["unaligned_objective_ids"] == []
    assert aligned["low_confidence_objective_ids"] == []
    assert aligned["esg_missing_pillars"] == []
    assert aligned["esg_unmitigated_risk"] is False
    assert aligned["alignment_status"] == "ALIGNED"
    assert aligned["is_strategically_viable"] is True

    low_cover = audit_portfolio_strategic_alignment_and_esg_sustainability(
        [
            {
                "objective_id": "O-3",
                "weight_pct": 50.0,
                "has_measurable_kr": True,
                "kr_confidence_pct": 90.0,
                "is_aligned": True,
            },
            {
                "objective_id": "O-4",
                "weight_pct": 50.0,
                "has_measurable_kr": False,
                "kr_confidence_pct": 90.0,
                "is_aligned": False,
            },
        ]
    )
    assert low_cover["covered_weight_pct"] == 50.0
    assert low_cover["unaligned_objective_ids"] == ["O-4"]
    assert low_cover["alignment_status"] == "MISALIGNED"
    assert low_cover["is_strategically_viable"] is False

    empty = audit_portfolio_strategic_alignment_and_esg_sustainability([])
    assert empty["covered_weight_pct"] == 0.0
    assert empty["alignment_status"] == "MISALIGNED"

    for payload in (None, "not-a-list", 42):
        neutral = audit_portfolio_strategic_alignment_and_esg_sustainability(payload)
        assert neutral["alignment_status"] == "MISALIGNED"
        assert neutral["is_strategically_viable"] is False

    esg_risk = audit_portfolio_strategic_alignment_and_esg_sustainability(
        [
            {
                "objective_id": "O-5",
                "weight_pct": 100.0,
                "has_measurable_kr": True,
                "kr_confidence_pct": 90.0,
                "is_aligned": True,
            }
        ],
        esg_pillars={
            "environmental_impact_assessed": True,
            "social_community_benefit_documented": True,
            "governance_ethics_cleared": True,
            "high_carbon_or_social_risk_unmitigated": True,
        },
    )
    assert esg_risk["esg_unmitigated_risk"] is True
    assert esg_risk["alignment_status"] == "MISALIGNED"


def test_portfolio_strategic_alignment_esg_at_risk_and_thresholds():
    """Cobertura OK pero confidencia baja o pilares ESG incompletos -> AT_RISK; umbrales custom."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_portfolio_strategic_alignment_and_esg_sustainability,
    )

    low_conf = audit_portfolio_strategic_alignment_and_esg_sustainability(
        [
            {
                "objective_id": "O-6",
                "weight_pct": 100.0,
                "has_measurable_kr": True,
                "kr_confidence_pct": 69.9,
                "is_aligned": True,
            }
        ]
    )
    assert low_conf["low_confidence_objective_ids"] == ["O-6"]
    assert low_conf["covered_weight_pct"] == 100.0
    assert low_conf["alignment_status"] == "AT_RISK"
    assert low_conf["is_strategically_viable"] is False

    # Confidencia exactamente en el umbral: no es baja.
    at_limit = audit_portfolio_strategic_alignment_and_esg_sustainability(
        [
            {
                "objective_id": "O-7",
                "weight_pct": 100.0,
                "has_measurable_kr": True,
                "kr_confidence_pct": 70.0,
                "is_aligned": True,
            }
        ]
    )
    assert at_limit["low_confidence_objective_ids"] == []
    assert at_limit["alignment_status"] == "ALIGNED"

    missing_pillars = audit_portfolio_strategic_alignment_and_esg_sustainability(
        [
            {
                "objective_id": "O-8",
                "weight_pct": 100.0,
                "has_measurable_kr": True,
                "kr_confidence_pct": 90.0,
                "is_aligned": True,
            }
        ],
        esg_pillars={
            "environmental_impact_assessed": False,
            "social_community_benefit_documented": False,
            "governance_ethics_cleared": True,
        },
    )
    assert missing_pillars["esg_missing_pillars"] == ["environmental", "social"]
    assert missing_pillars["alignment_status"] == "AT_RISK"

    # Sin esg_pillars proveído: no missing ni unmitigated.
    no_esg = audit_portfolio_strategic_alignment_and_esg_sustainability(
        [
            {
                "objective_id": "O-9",
                "weight_pct": 100.0,
                "has_measurable_kr": True,
                "kr_confidence_pct": 90.0,
                "is_aligned": True,
            }
        ]
    )
    assert no_esg["esg_missing_pillars"] == []
    assert no_esg["esg_unmitigated_risk"] is False
    assert no_esg["alignment_status"] == "ALIGNED"

    # Umbral de cobertura custom: 85% con min 90 -> MISALIGNED.
    custom = audit_portfolio_strategic_alignment_and_esg_sustainability(
        [
            {
                "objective_id": "O-10",
                "weight_pct": 85.0,
                "has_measurable_kr": True,
                "kr_confidence_pct": 90.0,
                "is_aligned": True,
            }
        ],
        min_strategic_weight_coverage_pct=90.0,
    )
    assert custom["covered_weight_pct"] == 85.0
    assert custom["alignment_status"] == "MISALIGNED"

    # Umbral de cobertura custom: 85% con min 80 -> dentro.
    ok_custom = audit_portfolio_strategic_alignment_and_esg_sustainability(
        [
            {
                "objective_id": "O-11",
                "weight_pct": 85.0,
                "has_measurable_kr": True,
                "kr_confidence_pct": 90.0,
                "is_aligned": True,
            }
        ],
        min_strategic_weight_coverage_pct=80.0,
    )
    assert ok_custom["covered_weight_pct"] == 85.0
    assert ok_custom["alignment_status"] == "ALIGNED"


def test_portfolio_strategic_alignment_esg_rounding_and_edge_cases():
    """Peso agregado redondeado a 2 decimales; bools no suman; informative fields."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_portfolio_strategic_alignment_and_esg_sustainability,
    )

    rounded = audit_portfolio_strategic_alignment_and_esg_sustainability(
        [
            {
                "objective_id": "O-12",
                "weight_pct": 33.333333,
                "has_measurable_kr": True,
                "kr_confidence_pct": 90.0,
                "is_aligned": True,
            },
            {
                "objective_id": "O-13",
                "weight_pct": 33.333333,
                "has_measurable_kr": True,
                "kr_confidence_pct": 90.0,
                "is_aligned": True,
            },
            {
                "objective_id": "O-14",
                "weight_pct": 33.333333,
                "has_measurable_kr": True,
                "kr_confidence_pct": 90.0,
                "is_aligned": True,
            },
        ]
    )
    assert rounded["covered_weight_pct"] == 100.0
    assert rounded["total_objectives"] == 3

    bool_weight = audit_portfolio_strategic_alignment_and_esg_sustainability(
        [
            {
                "objective_id": "O-15",
                "weight_pct": True,
                "has_measurable_kr": True,
                "kr_confidence_pct": 90.0,
                "is_aligned": True,
            },
            {
                "objective_id": "O-16",
                "weight_pct": 40.0,
                "has_measurable_kr": True,
                "kr_confidence_pct": 90.0,
                "is_aligned": True,
            },
        ]
    )
    # weight_pct=True (bool) se EXCLUYE de la aritmética numérica deliberadamente:
    # solo queda el peso real (40.0) y el status es MISALIGNED por cobertura.
    assert bool_weight["covered_weight_pct"] == 40.0
    assert bool_weight["alignment_status"] == "MISALIGNED"  # 40 < 80

    # is_aligned False pero weight alto: NO suma al coverage aunque weight este.
    no_contrib = audit_portfolio_strategic_alignment_and_esg_sustainability(
        [
            {
                "objective_id": "O-17",
                "weight_pct": 95.0,
                "has_measurable_kr": False,
                "kr_confidence_pct": 90.0,
                "is_aligned": True,
            }
        ]
    )
    assert no_contrib["covered_weight_pct"] == 0.0
    assert no_contrib["alignment_status"] == "MISALIGNED"


def test_portfolio_strategic_alignment_esg_precedence_and_binding():
    """Cadena precedence MISALIGNED > AT_RISK > ALIGNED; proxy @staticmethod."""
    import backend.services.project_lifecycle_pmi_service as mod
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_portfolio_strategic_alignment_and_esg_sustainability,
    )

    # MISALIGNED domina aunque haya AT_RISK signals.
    dominates = audit_portfolio_strategic_alignment_and_esg_sustainability(
        [
            {
                "objective_id": "O-18",
                "weight_pct": 40.0,
                "has_measurable_kr": True,
                "kr_confidence_pct": 10.0,
                "is_aligned": True,
            }
        ]
    )
    assert dominates["covered_weight_pct"] == 40.0
    assert dominates["alignment_status"] == "MISALIGNED"

    mixed = audit_portfolio_strategic_alignment_and_esg_sustainability(
        [
            {
                "objective_id": "O-19",
                "weight_pct": 100.0,
                "has_measurable_kr": True,
                "kr_confidence_pct": 20.0,
                "is_aligned": True,
            }
        ]
    )
    # 100% cobertura -> no MISALIGNED por cobertura; confidencia baja -> AT_RISK.
    assert mixed["alignment_status"] == "AT_RISK"

    sample = [
        {
            "objective_id": "O-20",
            "weight_pct": 100.0,
            "has_measurable_kr": True,
            "kr_confidence_pct": 90.0,
            "is_aligned": True,
        }
    ]
    assert (
        ProjectLifecyclePMIService.audit_portfolio_strategic_alignment_and_esg_sustainability(sample)
        == audit_portfolio_strategic_alignment_and_esg_sustainability(sample)
    )
    assert "audit_portfolio_strategic_alignment_and_esg_sustainability" in mod.__all__


def test_audit_steering_committee_quorum_and_escalation_sla_effective():
    """Valida sesiones con quórum >= 66.7%, actas publicadas, escalamientos resueltos y SLA cumplido ('EFFECTIVE')."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_steering_committee_quorum_and_escalation_sla,
    )

    sessions = [
        {
            "session_id": "SES-01",
            "voting_members_total": 6,
            "voting_members_present": 5,
            "minutes_published": True,
            "escalations_submitted": 2,
            "escalations_resolved": 2,
            "max_escalation_age_days": 4,
        },
        {
            "session_id": "SES-02",
            "voting_members_total": 3,
            "voting_members_present": 3,
            "minutes_published": True,
            "escalations_submitted": 0,
            "escalations_resolved": 0,
            "max_escalation_age_days": 0,
        },
    ]
    res = audit_steering_committee_quorum_and_escalation_sla(sessions)
    assert res["total_sessions"] == 2
    assert res["quorum_breach_session_ids"] == []
    assert res["missing_minutes_session_ids"] == []
    assert res["sla_breach_session_ids"] == []
    assert res["unresolved_escalations_total"] == 0
    assert res["governance_cadence_status"] == "EFFECTIVE"
    assert res["is_governance_healthy"] is True
    assert res["issues"] == []


def test_audit_steering_committee_quorum_and_escalation_sla_non_compliant():
    """Detecta falta de quórum y violación del SLA de resolución de escalamientos ('NON_COMPLIANT')."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_steering_committee_quorum_and_escalation_sla,
    )

    sessions = [
        {
            "session_id": "SES-10",
            "voting_members_total": 6,
            "voting_members_present": 3,
            "minutes_published": True,
            "escalations_submitted": 1,
            "escalations_resolved": 1,
            "max_escalation_age_days": 3,
        },
        {
            "session_id": "SES-11",
            "voting_members_total": 5,
            "voting_members_present": 4,
            "minutes_published": True,
            "escalations_submitted": 2,
            "escalations_resolved": 1,
            "max_escalation_age_days": 10,
        },
    ]
    res = audit_steering_committee_quorum_and_escalation_sla(sessions)
    assert res["total_sessions"] == 2
    assert res["quorum_breach_session_ids"] == ["SES-10"]
    assert res["sla_breach_session_ids"] == ["SES-11"]
    assert res["unresolved_escalations_total"] == 1
    assert res["governance_cadence_status"] == "NON_COMPLIANT"
    assert res["is_governance_healthy"] is False
    assert len(res["issues"]) >= 3


def test_audit_steering_committee_quorum_and_escalation_sla_degraded():
    """Detecta falta de actas publicadas o escalamientos sin resolver dentro de SLA ('DEGRADED')."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_steering_committee_quorum_and_escalation_sla,
    )

    sessions = [
        {
            "session_id": "SES-20",
            "voting_members_total": 4,
            "voting_members_present": 3,
            "minutes_published": False,
            "escalations_submitted": 3,
            "escalations_resolved": 1,
            "max_escalation_age_days": 5,
        }
    ]
    res = audit_steering_committee_quorum_and_escalation_sla(sessions)
    assert res["total_sessions"] == 1
    assert res["quorum_breach_session_ids"] == []
    assert res["sla_breach_session_ids"] == []
    assert res["missing_minutes_session_ids"] == ["SES-20"]
    assert res["unresolved_escalations_total"] == 2
    assert res["governance_cadence_status"] == "DEGRADED"
    assert res["is_governance_healthy"] is False
    assert len(res["issues"]) == 2


def test_audit_steering_committee_quorum_and_escalation_sla_empty_and_binding():
    """Verifica manejo defensivo de entradas vacías/no-secuencia y enlace en ProjectLifecyclePMIService y __all__."""
    import backend.services.project_lifecycle_pmi_service as mod
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_steering_committee_quorum_and_escalation_sla,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = audit_steering_committee_quorum_and_escalation_sla(payload)  # type: ignore[arg-type]
        assert empty["total_sessions"] == 0
        assert empty["quorum_breach_session_ids"] == []
        assert empty["missing_minutes_session_ids"] == []
        assert empty["sla_breach_session_ids"] == []
        assert empty["unresolved_escalations_total"] == 0
        assert empty["governance_cadence_status"] == "EFFECTIVE"
        assert empty["is_governance_healthy"] is True
        assert empty["issues"] == []

    sample = [
        {
            "session_id": "SES-99",
            "voting_members_total": 5,
            "voting_members_present": 4,
            "minutes_published": True,
            "escalations_submitted": 1,
            "escalations_resolved": 1,
            "max_escalation_age_days": 2,
        }
    ]
    assert (
        ProjectLifecyclePMIService.audit_steering_committee_quorum_and_escalation_sla(
            sample
        )
        == audit_steering_committee_quorum_and_escalation_sla(sample)
    )
    assert (
        "audit_steering_committee_quorum_and_escalation_sla"
        in mod.__all__
    )


def test_business_case_npv_irr_payback_viable():
    """Caso 1: NPV > 0, IRR >= hurdle, payback en límite y BCR >= mínimo -> INVESTMENT_VIABLE."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_business_case_npv_irr_and_payback_viability,
    )

    res = audit_business_case_npv_irr_and_payback_viability(
        net_present_value_usd=250000.0,
        internal_rate_of_return_pct=18.5,
        hurdle_discount_rate_pct=12.0,
        payback_period_months=24.0,
        max_acceptable_payback_months=36.0,
        benefit_cost_ratio_bcr=1.45,
        min_required_bcr=1.1,
    )
    assert res["npv_positive_or_zero"] is True
    assert res["irr_exceeds_hurdle"] is True
    assert res["irr_spread_pct"] == 6.5
    assert res["payback_within_limit"] is True
    assert res["bcr_viable"] is True
    assert res["failed_criteria"] == []
    assert res["investment_decision_status"] == "INVESTMENT_VIABLE"
    assert res["is_financially_justified"] is True
    assert res["issues"] == []


def test_business_case_npv_irr_payback_marginal_watch():
    """Caso 2: NPV >= 0 e IRR >= hurdle pero payback excedido o BCR bajo -> MARGINAL_WATCH."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_business_case_npv_irr_and_payback_viability,
    )

    res = audit_business_case_npv_irr_and_payback_viability(
        net_present_value_usd=15000.0,
        internal_rate_of_return_pct=12.0,
        hurdle_discount_rate_pct=12.0,
        payback_period_months=42.0,
        max_acceptable_payback_months=36.0,
        benefit_cost_ratio_bcr=1.05,
        min_required_bcr=1.2,
    )
    assert res["npv_positive_or_zero"] is True
    assert res["irr_exceeds_hurdle"] is True
    assert res["irr_spread_pct"] == 0.0
    assert res["payback_within_limit"] is False
    assert res["bcr_viable"] is False
    assert res["failed_criteria"] == ["payback_exceeded", "bcr_below_minimum"]
    assert res["investment_decision_status"] == "MARGINAL_WATCH"
    assert res["is_financially_justified"] is False
    assert len(res["issues"]) >= 2


def test_business_case_npv_irr_payback_reject_or_re_scope():
    """Caso 3: NPV negativo o IRR < hurdle -> REJECT_OR_RE_SCOPE."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_business_case_npv_irr_and_payback_viability,
    )

    res = audit_business_case_npv_irr_and_payback_viability(
        net_present_value_usd=-50000.0,
        internal_rate_of_return_pct=7.25,
        hurdle_discount_rate_pct=10.0,
        payback_period_months=18.0,
        max_acceptable_payback_months=36.0,
        benefit_cost_ratio_bcr=1.3,
        min_required_bcr=1.0,
    )
    assert res["npv_positive_or_zero"] is False
    assert res["irr_exceeds_hurdle"] is False
    assert res["irr_spread_pct"] == -2.75
    assert res["payback_within_limit"] is True
    assert res["bcr_viable"] is True
    assert res["failed_criteria"] == ["npv_negative", "irr_below_hurdle"]
    assert res["investment_decision_status"] == "REJECT_OR_RE_SCOPE"
    assert res["is_financially_justified"] is False
    assert len(res["issues"]) >= 2


def test_business_case_npv_irr_payback_defaults_and_binding():
    """Caso 4: Defaults, payback <= 0 no válido y binding en ProjectLifecyclePMIService + __all__."""
    import backend.services.project_lifecycle_pmi_service as mod
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_business_case_npv_irr_and_payback_viability,
    )

    defaults = audit_business_case_npv_irr_and_payback_viability()
    assert defaults["npv_positive_or_zero"] is True
    assert defaults["irr_exceeds_hurdle"] is False
    assert defaults["irr_spread_pct"] == -10.0
    assert defaults["payback_within_limit"] is False
    assert defaults["bcr_viable"] is True
    assert defaults["failed_criteria"] == ["irr_below_hurdle", "payback_exceeded"]
    assert defaults["investment_decision_status"] == "REJECT_OR_RE_SCOPE"
    assert defaults["is_financially_justified"] is False

    kwargs = {
        "net_present_value_usd": 100000.0,
        "internal_rate_of_return_pct": 15.0,
        "hurdle_discount_rate_pct": 10.0,
        "payback_period_months": 20.0,
        "max_acceptable_payback_months": 36.0,
        "benefit_cost_ratio_bcr": 1.25,
        "min_required_bcr": 1.0,
    }
    assert (
        ProjectLifecyclePMIService.audit_business_case_npv_irr_and_payback_viability(
            **kwargs
        )
        == audit_business_case_npv_irr_and_payback_viability(**kwargs)
    )
    assert "audit_business_case_npv_irr_and_payback_viability" in mod.__all__


def test_audit_team_tuckman_maturity_high_performing():
    """Caso 1: Equipos en etapas válidas, seguridad >= 3.8, sin conflictos y CV <= 25% -> HIGH_PERFORMING."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_team_tuckman_maturity_and_psychological_safety,
    )

    squads = [
        {
            "squad_id": "SQ-ALPHA",
            "tuckman_stage": "performing",
            "psychological_safety_score": 4.5,
            "velocity_cv_pct": 12.0,
            "unresolved_interpersonal_conflicts": 0,
        },
        {
            "squad_id": "SQ-BETA",
            "tuckman_stage": "norming",
            "psychological_safety_score": 4.0,
            "velocity_cv_pct": 18.5,
            "unresolved_interpersonal_conflicts": 0,
        },
    ]
    res = audit_team_tuckman_maturity_and_psychological_safety(
        squads, min_safety_score_1_to_5=3.8, max_velocity_volatility_cv_pct=25.0
    )
    assert res["total_squads"] == 2
    assert res["invalid_stage_squad_ids"] == []
    assert res["low_safety_squad_ids"] == []
    assert res["storming_conflict_squad_ids"] == []
    assert res["unstable_velocity_squad_ids"] == []
    assert res["team_health_status"] == "HIGH_PERFORMING"
    assert res["is_team_healthy"] is True
    assert res["issues"] == []


def test_audit_team_tuckman_maturity_volatile_cadence():
    """Caso 2: Seguridad saludable y etapa norming/forming sin conflictos pero CV > 25% -> VOLATILE_CADENCE."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_team_tuckman_maturity_and_psychological_safety,
    )

    squads = [
        {
            "squad_id": "SQ-GAMMA",
            "tuckman_stage": "forming",
            "psychological_safety_score": 4.1,
            "velocity_cv_pct": 32.0,
            "unresolved_interpersonal_conflicts": 0,
        }
    ]
    res = audit_team_tuckman_maturity_and_psychological_safety(
        squads, min_safety_score_1_to_5=3.8, max_velocity_volatility_cv_pct=25.0
    )
    assert res["total_squads"] == 1
    assert res["invalid_stage_squad_ids"] == []
    assert res["low_safety_squad_ids"] == []
    assert res["storming_conflict_squad_ids"] == []
    assert res["unstable_velocity_squad_ids"] == ["SQ-GAMMA"]
    assert res["team_health_status"] == "VOLATILE_CADENCE"
    assert res["is_team_healthy"] is False
    assert len(res["issues"]) >= 1


def test_audit_team_tuckman_maturity_dysfunctional_risk():
    """Caso 3: Etapa inválida, baja seguridad psicológica o conflicto storming -> DYSFUNCTIONAL_RISK."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_team_tuckman_maturity_and_psychological_safety,
    )

    squads = [
        {
            "squad_id": "SQ-BAD-STAGE",
            "tuckman_stage": "chaotic",
            "psychological_safety_score": 4.2,
            "velocity_cv_pct": 10.0,
            "unresolved_interpersonal_conflicts": 0,
        },
        {
            "squad_id": "SQ-LOW-SAFE",
            "tuckman_stage": "storming",
            "psychological_safety_score": 2.9,
            "velocity_cv_pct": 30.0,
            "unresolved_interpersonal_conflicts": 2,
        },
    ]
    res = audit_team_tuckman_maturity_and_psychological_safety(
        squads, min_safety_score_1_to_5=3.8, max_velocity_volatility_cv_pct=25.0
    )
    assert res["total_squads"] == 2
    assert res["invalid_stage_squad_ids"] == ["SQ-BAD-STAGE"]
    assert res["low_safety_squad_ids"] == ["SQ-LOW-SAFE"]
    assert res["storming_conflict_squad_ids"] == ["SQ-LOW-SAFE"]
    assert res["unstable_velocity_squad_ids"] == ["SQ-LOW-SAFE"]
    assert res["team_health_status"] == "DYSFUNCTIONAL_RISK"
    assert res["is_team_healthy"] is False
    assert len(res["issues"]) >= 3


def test_audit_team_tuckman_maturity_empty_and_binding():
    """Caso 4: Entradas vacías/inválidas y binding en ProjectLifecyclePMIService + __all__."""
    import backend.services.project_lifecycle_pmi_service as mod
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_team_tuckman_maturity_and_psychological_safety,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = audit_team_tuckman_maturity_and_psychological_safety(payload)  # type: ignore[arg-type]
        assert empty["total_squads"] == 0
        assert empty["invalid_stage_squad_ids"] == []
        assert empty["low_safety_squad_ids"] == []
        assert empty["storming_conflict_squad_ids"] == []
        assert empty["unstable_velocity_squad_ids"] == []
        assert empty["team_health_status"] == "HIGH_PERFORMING"
        assert empty["is_team_healthy"] is True
        assert empty["issues"] == []

    sample = [
        {
            "squad_id": "SQ-99",
            "tuckman_stage": "adjourning",
            "psychological_safety_score": 4.4,
            "velocity_cv_pct": 10.0,
            "unresolved_interpersonal_conflicts": 0,
        }
    ]
    assert (
        ProjectLifecyclePMIService.audit_team_tuckman_maturity_and_psychological_safety(
            sample
        )
        == audit_team_tuckman_maturity_and_psychological_safety(sample)
    )
    assert (
        "audit_team_tuckman_maturity_and_psychological_safety" in mod.__all__
    )




def test_audit_project_premortem_early_warning_triggered_precedence():
    """Caso 1: señal disparada domina sobre kill-switch ausente -> EARLY_WARNING_TRIGGERED."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_project_premortem_scenarios_and_kill_switch_criteria,
    )

    res = audit_project_premortem_scenarios_and_kill_switch_criteria(
        [
            {
                "scenario_id": "SC-01",
                "failure_mode_description": "Baja retención y abandono masivo de estudiantes en cohorte inicial",
                "early_warning_signal": "Asistencia semanal < 60%",
                "preventive_countermeasure": "Plan de re-engagement con líderes de célula",
                "signal_currently_triggered": True,
                "owner_id": "U-100",
            },
            {
                "scenario_id": "SC-02",
                "failure_mode_description": "Corte de presupuesto del ministerio",
                "early_warning_signal": None,
                "preventive_countermeasure": "Fondo de contingencia",
                "signal_currently_triggered": False,
                "owner_id": "U-200",
            },
        ],
        has_explicit_project_kill_switch_criteria=False,
    )
    assert res["total_scenarios"] == 2
    assert res["missing_signal_or_countermeasure_ids"] == ["SC-02"]
    assert res["triggered_early_warning_ids"] == ["SC-01"]
    assert res["insufficient_scenario_depth"] is True
    assert res["premortem_governance_status"] == "EARLY_WARNING_TRIGGERED"
    assert res["is_premortem_ready"] is False


def test_audit_project_premortem_incomplete_negative_precedences():
    """Caso 2: sin señales disparadas, kill-switch ausente / profundidad insuficiente / gaps -> INCOMPLETE_PREMORTEM."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_project_premortem_scenarios_and_kill_switch_criteria,
    )

    res_no_killswitch = audit_project_premortem_scenarios_and_kill_switch_criteria(
        [],
        has_explicit_project_kill_switch_criteria=False,
        min_required_scenarios=3,
    )
    assert res_no_killswitch["total_scenarios"] == 0
    assert res_no_killswitch["insufficient_scenario_depth"] is True
    assert res_no_killswitch["premortem_governance_status"] == "INCOMPLETE_PREMORTEM"
    assert res_no_killswitch["is_premortem_ready"] is False

    res_depth = audit_project_premortem_scenarios_and_kill_switch_criteria(
        [
            {
                "scenario_id": "SC-01",
                "failure_mode_description": "Voluntarios clave abandonan",
                "early_warning_signal": "Turnos sin cubrir",
                "preventive_countermeasure": "Bench de voluntarios",
                "signal_currently_triggered": False,
                "owner_id": "U-300",
            },
            {
                "scenario_id": "SC-02",
                "failure_mode_description": "Ciberataque bloquea la plataforma",
                "early_warning_signal": "Alertas SOC",
                "preventive_countermeasure": "Plan DR",
                "signal_currently_triggered": False,
                "owner_id": "U-400",
            },
        ],
        min_required_scenarios=3,
    )
    assert res_depth["total_scenarios"] == 2
    assert res_depth["insufficient_scenario_depth"] is True
    assert res_depth["missing_signal_or_countermeasure_ids"] == []
    assert res_depth["premortem_governance_status"] == "INCOMPLETE_PREMORTEM"

    res_gaps = audit_project_premortem_scenarios_and_kill_switch_criteria(
        [
            {
                "scenario_id": "SC-01",
                "failure_mode_description": "Escenario sin contramedida",
                "early_warning_signal": "Signal",
                "preventive_countermeasure": None,
                "signal_currently_triggered": False,
                "owner_id": "U-500",
            }
        ],
        min_required_scenarios=1,
    )
    assert res_gaps["missing_signal_or_countermeasure_ids"] == ["SC-01"]
    assert res_gaps["premortem_governance_status"] == "INCOMPLETE_PREMORTEM"


def test_audit_project_premortem_prepared_full_compliance():
    """Caso 3: escenarios completos sin señales disparadas con kill-switch -> PREPARED."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_project_premortem_scenarios_and_kill_switch_criteria,
    )

    res = audit_project_premortem_scenarios_and_kill_switch_criteria(
        [
            {
                "scenario_id": "SC-01",
                "failure_mode_description": "Voluntarios clave abandonan",
                "early_warning_signal": "Turnos sin cubrir",
                "preventive_countermeasure": "Bench de voluntarios",
                "signal_currently_triggered": False,
                "owner_id": "U-300",
            },
            {
                "scenario_id": "SC-02",
                "failure_mode_description": "Ciberataque bloquea la plataforma",
                "early_warning_signal": "Alertas SOC",
                "preventive_countermeasure": "Plan DR",
                "signal_currently_triggered": False,
                "owner_id": "U-400",
            },
            {
                "scenario_id": "SC-03",
                "failure_mode_description": "Sede bloquea plazos de entrega",
                "early_warning_signal": "SLA sin respuesta",
                "preventive_countermeasure": "Plan A de migración estable",
                "signal_currently_triggered": False,
                "owner_id": "U-500",
            },
        ],
        has_explicit_project_kill_switch_criteria=True,
        min_required_scenarios=3,
    )
    assert res["total_scenarios"] == 3
    assert res["missing_signal_or_countermeasure_ids"] == []
    assert res["triggered_early_warning_ids"] == []
    assert res["insufficient_scenario_depth"] is False
    assert res["premortem_governance_status"] == "PREPARED"
    assert res["is_premortem_ready"] is True


def test_audit_project_premortem_invalid_entries_and_binding():
    """Caso 4: entradas no-lista/no-dict y binding + __all__."""
    import backend.services.project_lifecycle_pmi_service as mod
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_project_premortem_scenarios_and_kill_switch_criteria,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = audit_project_premortem_scenarios_and_kill_switch_criteria(
            payload,  # type: ignore[arg-type]
            min_required_scenarios=3,
        )
        assert empty["total_scenarios"] == 0
        assert empty["missing_signal_or_countermeasure_ids"] == []
        assert empty["triggered_early_warning_ids"] == []
        assert empty["insufficient_scenario_depth"] is True
        assert empty["premortem_governance_status"] == "INCOMPLETE_PREMORTEM"
        assert empty["is_premortem_ready"] is False

    sample = [
        {
            "scenario_id": "SC-01",
            "failure_mode_description": "x",
            "early_warning_signal": "s",
            "preventive_countermeasure": "c",
            "signal_currently_triggered": False,
            "owner_id": "U-1",
        },
        {
            "scenario_id": "SC-02",
            "failure_mode_description": "x",
            "early_warning_signal": "s",
            "preventive_countermeasure": "c",
            "signal_currently_triggered": False,
            "owner_id": "U-2",
        },
        {
            "scenario_id": "SC-03",
            "failure_mode_description": "x",
            "early_warning_signal": "s",
            "preventive_countermeasure": "c",
            "signal_currently_triggered": False,
            "owner_id": "U-3",
        },
    ]
    assert (
        ProjectLifecyclePMIService.audit_project_premortem_scenarios_and_kill_switch_criteria(
            sample
        )
        == audit_project_premortem_scenarios_and_kill_switch_criteria(sample)
    )
    assert "audit_project_premortem_scenarios_and_kill_switch_criteria" in mod.__all__


def test_audit_project_closure_hypercare_and_bau_handover_ready():
    """Caso 1: Todos los ítems BAU aceptados, runbook verificado, KT completo, hypercare >= 14d y sin incidentes bloqueantes -> READY_FOR_BAU."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_project_closure_hypercare_and_bau_handover_readiness,
    )

    items = [
        {
            "item_id": "HND-01",
            "domain": "RUNBOOK",
            "bau_owner_accepted": True,
            "runbook_verified": True,
            "kt_session_completed": True,
        },
        {
            "item_id": "HND-02",
            "domain": "MONITORING_ALERTS",
            "bau_owner_accepted": True,
            "runbook_verified": True,
            "kt_session_completed": True,
        },
    ]
    res = audit_project_closure_hypercare_and_bau_handover_readiness(
        items,
        hypercare_days_configured=30,
        min_hypercare_days=14,
        open_sev1_incidents=0,
        open_sev2_incidents=1,
        max_allowed_sev2_incidents=1,
    )
    assert res["total_handover_items"] == 2
    assert res["unaccepted_bau_item_ids"] == []
    assert res["unverified_runbook_item_ids"] == []
    assert res["incomplete_kt_item_ids"] == []
    assert res["insufficient_hypercare_window"] is False
    assert res["incident_gate_blocked"] is False
    assert res["handover_governance_status"] == "READY_FOR_BAU"
    assert res["is_bau_handover_ready"] is True
    assert res["recommendations"] == []


def test_audit_project_closure_hypercare_and_bau_handover_conditional():
    """Caso 2: BAU aceptado y sin incidentes bloqueantes pero falta verificar runbook, KT o ventana hypercare < 14d -> CONDITIONAL_HYPERCARE."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_project_closure_hypercare_and_bau_handover_readiness,
    )

    items = [
        {
            "item_id": "HND-10",
            "domain": "ON_CALL_ROSTER",
            "bau_owner_accepted": True,
            "runbook_verified": False,
            "kt_session_completed": False,
        }
    ]
    res = audit_project_closure_hypercare_and_bau_handover_readiness(
        items,
        hypercare_days_configured=7,
        min_hypercare_days=14,
        open_sev1_incidents=0,
        open_sev2_incidents=0,
    )
    assert res["total_handover_items"] == 1
    assert res["unaccepted_bau_item_ids"] == []
    assert res["unverified_runbook_item_ids"] == ["HND-10"]
    assert res["incomplete_kt_item_ids"] == ["HND-10"]
    assert res["insufficient_hypercare_window"] is True
    assert res["incident_gate_blocked"] is False
    assert res["handover_governance_status"] == "CONDITIONAL_HYPERCARE"
    assert res["is_bau_handover_ready"] is False
    assert len(res["recommendations"]) >= 3


def test_audit_project_closure_hypercare_and_bau_handover_blocked():
    """Caso 3: Propietario BAU no acepta o hay incidentes SEV-1 / exceso de SEV-2 -> BLOCKED."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_project_closure_hypercare_and_bau_handover_readiness,
    )

    items = [
        {
            "item_id": "HND-20",
            "domain": "SLA_WARRANTY",
            "bau_owner_accepted": False,
            "runbook_verified": True,
            "kt_session_completed": True,
        }
    ]
    res = audit_project_closure_hypercare_and_bau_handover_readiness(
        items,
        hypercare_days_configured=30,
        min_hypercare_days=14,
        open_sev1_incidents=1,
        open_sev2_incidents=3,
        max_allowed_sev2_incidents=1,
    )
    assert res["total_handover_items"] == 1
    assert res["unaccepted_bau_item_ids"] == ["HND-20"]
    assert res["incident_gate_blocked"] is True
    assert res["handover_governance_status"] == "BLOCKED"
    assert res["is_bau_handover_ready"] is False
    assert len(res["recommendations"]) >= 2


def test_audit_project_closure_hypercare_and_bau_handover_empty_and_binding():
    """Caso 4: Entradas vacías/inválidas y binding en ProjectLifecyclePMIService + __all__."""
    import backend.services.project_lifecycle_pmi_service as mod
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_project_closure_hypercare_and_bau_handover_readiness,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = audit_project_closure_hypercare_and_bau_handover_readiness(payload)  # type: ignore[arg-type]
        assert empty["total_handover_items"] == 0
        assert empty["unaccepted_bau_item_ids"] == []
        assert empty["unverified_runbook_item_ids"] == []
        assert empty["incomplete_kt_item_ids"] == []
        assert empty["insufficient_hypercare_window"] is False
        assert empty["incident_gate_blocked"] is False
        assert empty["handover_governance_status"] == "READY_FOR_BAU"
        assert empty["is_bau_handover_ready"] is True
        assert empty["recommendations"] == []

    sample = [
        {
            "item_id": "HND-99",
            "domain": "ARCHIVAL",
            "bau_owner_accepted": True,
            "runbook_verified": True,
            "kt_session_completed": True,
        }
    ]
    assert (
        ProjectLifecyclePMIService.audit_project_closure_hypercare_and_bau_handover_readiness(
            sample
        )
        == audit_project_closure_hypercare_and_bau_handover_readiness(sample)
    )
    assert (
        "audit_project_closure_hypercare_and_bau_handover_readiness" in mod.__all__
    )



def test_audit_adkar_adoption_resistance_blocked_paths():
    """Caso 1: 2+ cohortes barrera o barrera + sin entrenar -> RESISTANCE_BLOCKED."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_organizational_change_adkar_adoption_readiness,
    )

    res = audit_organizational_change_adkar_adoption_readiness(
        [
            {
                "cohort_id": "C-01",
                "headcount": 12,
                "awareness_score": 2.0,
                "desire_score": 1.5,
                "knowledge_score": 3.0,
                "ability_score": 3.0,
                "reinforcement_score": 3.0,
                "training_completion_pct": 100.0,
                "has_change_champion": True,
            },
            {
                "cohort_id": "C-02",
                "headcount": 8,
                "awareness_score": 3.0,
                "desire_score": 3.0,
                "knowledge_score": 3.0,
                "ability_score": 2.5,
                "reinforcement_score": 3.0,
                "training_completion_pct": 100.0,
                "has_change_champion": True,
            },
        ]
    )
    assert res["total_cohorts"] == 2
    assert res["total_impacted_users"] == 20
    assert res["champion_coverage_pct"] == 100.0
    assert res["barrier_point_cohort_ids"] == ["C-01", "C-02"]
    assert res["untrained_cohort_ids"] == []
    assert res["unchampioned_cohort_ids"] == []
    assert res["ocm_governance_status"] == "RESISTANCE_BLOCKED"
    assert res["is_adoption_ready"] is False

    # Barrera + sin entrenar con una sola cohorte también bloquea.
    res_mixed = audit_organizational_change_adkar_adoption_readiness(
        [
            {
                "cohort_id": "C-10",
                "headcount": 5,
                "awareness_score": 4.0,
                "desire_score": 3.0,
                "knowledge_score": 4.0,
                "ability_score": 4.0,
                "reinforcement_score": 4.0,
                "training_completion_pct": 40.0,
                "has_change_champion": True,
            },
        ]
    )
    assert res_mixed["barrier_point_cohort_ids"] == ["C-10"]
    assert res_mixed["untrained_cohort_ids"] == ["C-10"]
    assert res_mixed["ocm_governance_status"] == "RESISTANCE_BLOCKED"


def test_audit_adkar_adoption_at_risk_paths():
    """Caso 2: una barrera, sin entrenar o cobertura de champions baja -> AT_RISK."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_organizational_change_adkar_adoption_readiness,
    )

    res_barrier = audit_organizational_change_adkar_adoption_readiness(
        [
            {
                "cohort_id": "C-20",
                "headcount": 10,
                "awareness_score": 4.8,
                "desire_score": 4.5,
                "knowledge_score": 3.2,
                "ability_score": 4.0,
                "reinforcement_score": 4.0,
                "training_completion_pct": 100.0,
                "has_change_champion": True,
            },
        ]
    )
    assert res_barrier["barrier_point_cohort_ids"] == ["C-20"]
    assert res_barrier["untrained_cohort_ids"] == []
    assert res_barrier["ocm_governance_status"] == "AT_RISK"

    res_untrained = audit_organizational_change_adkar_adoption_readiness(
        [
            {
                "cohort_id": "C-21",
                "headcount": 6,
                "awareness_score": 4.0,
                "desire_score": 4.0,
                "knowledge_score": 4.0,
                "ability_score": 4.0,
                "reinforcement_score": 4.0,
                "training_completion_pct": 70.0,
                "has_change_champion": True,
            },
        ]
    )
    assert res_untrained["untrained_cohort_ids"] == ["C-21"]
    assert res_untrained["ocm_governance_status"] == "AT_RISK"

    res_no_champion = audit_organizational_change_adkar_adoption_readiness(
        [
            {
                "cohort_id": "C-22",
                "headcount": 4,
                "awareness_score": 4.0,
                "desire_score": 4.0,
                "knowledge_score": 4.0,
                "ability_score": 4.0,
                "reinforcement_score": 4.0,
                "training_completion_pct": 100.0,
                "has_change_champion": False,
            },
        ]
    )
    assert res_no_champion["unchampioned_cohort_ids"] == ["C-22"]
    assert res_no_champion["champion_coverage_pct"] == 0.0
    assert res_no_champion["ocm_governance_status"] == "AT_RISK"
    assert res_no_champion["is_adoption_ready"] is False


def test_audit_adkar_adoption_ready_and_champion_coverage():
    """Caso 3: cohortes completas con cobertura de champions >= umbral -> ADOPTION_READY."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_organizational_change_adkar_adoption_readiness,
    )

    res = audit_organizational_change_adkar_adoption_readiness(
        [
            {
                "cohort_id": "C-30",
                "headcount": 15,
                "awareness_score": 4.0,
                "desire_score": 3.5,
                "knowledge_score": 3.5,
                "ability_score": 3.6,
                "reinforcement_score": 4.0,
                "training_completion_pct": 85.0,
                "has_change_champion": True,
            },
            {
                "cohort_id": "C-31",
                "headcount": 9,
                "awareness_score": 3.6,
                "desire_score": 3.8,
                "knowledge_score": 3.5,
                "ability_score": 3.5,
                "reinforcement_score": 3.5,
                "training_completion_pct": 90.0,
                "has_change_champion": True,
            },
            {
                "cohort_id": "C-32",
                "headcount": 6,
                "awareness_score": 3.5,
                "desire_score": 3.5,
                "knowledge_score": 3.5,
                "ability_score": 3.5,
                "reinforcement_score": 3.5,
                "training_completion_pct": 85.0,
                "has_change_champion": True,
            },
        ],
        min_champion_coverage_pct=75.0,
    )
    assert res["total_cohorts"] == 3
    assert res["total_impacted_users"] == 30
    assert res["champion_coverage_pct"] == 100.0
    assert res["barrier_point_cohort_ids"] == []
    assert res["untrained_cohort_ids"] == []
    assert res["unchampioned_cohort_ids"] == []
    assert res["ocm_governance_status"] == "ADOPTION_READY"
    assert res["is_adoption_ready"] is True
    assert res["recommendations"] == []
    # 2 de 3 cohortes con champion: 66.67% < 75% -> AT_RISK a pesar de scores completos.
    res_partial = audit_organizational_change_adkar_adoption_readiness(
        [
            {**res_item, "has_change_champion": True} if i == 0 else {**res_item, "has_change_champion": False}
            for i, res_item in enumerate([
                {
                    "cohort_id": "C-30",
                    "headcount": 15,
                    "awareness_score": 4.0,
                    "desire_score": 3.5,
                    "knowledge_score": 3.5,
                    "ability_score": 3.6,
                    "reinforcement_score": 4.0,
                    "training_completion_pct": 85.0,
                },
                {
                    "cohort_id": "C-31",
                    "headcount": 9,
                    "awareness_score": 3.7,
                    "desire_score": 3.8,
                    "knowledge_score": 3.6,
                    "ability_score": 3.5,
                    "reinforcement_score": 3.6,
                    "training_completion_pct": 90.0,
                },
                {
                    "cohort_id": "C-32",
                    "headcount": 6,
                    "awareness_score": 3.5,
                    "desire_score": 3.5,
                    "knowledge_score": 3.5,
                    "ability_score": 3.5,
                    "reinforcement_score": 3.5,
                    "training_completion_pct": 85.0,
                },
            ])
        ],
    )
    assert res_partial["champion_coverage_pct"] == round(1 / 3 * 100, 2)
    assert res_partial["ocm_governance_status"] == "AT_RISK"


def test_audit_adkar_adoption_invalid_entries_and_binding():
    """Caso 4: entradas no-lista/no-dict y binding + __all__."""
    import backend.services.project_lifecycle_pmi_service as mod
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_organizational_change_adkar_adoption_readiness,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = audit_organizational_change_adkar_adoption_readiness(payload)  # type: ignore[arg-type]
        assert empty["total_cohorts"] == 0
        assert empty["total_impacted_users"] == 0
        assert empty["champion_coverage_pct"] == 100.0
        assert empty["barrier_point_cohort_ids"] == []
        assert empty["untrained_cohort_ids"] == []
        assert empty["unchampioned_cohort_ids"] == []
        assert empty["ocm_governance_status"] == "ADOPTION_READY"
        assert empty["is_adoption_ready"] is True
        assert empty["recommendations"] == []

    sample = [
        {
            "cohort_id": "C-40",
            "headcount": 3,
            "awareness_score": 4.0,
            "desire_score": 4.0,
            "knowledge_score": 4.0,
            "ability_score": 4.0,
            "reinforcement_score": 4.0,
            "training_completion_pct": 100.0,
            "has_change_champion": True,
        },
    ]
    assert (
        ProjectLifecyclePMIService.audit_organizational_change_adkar_adoption_readiness(sample)
        == audit_organizational_change_adkar_adoption_readiness(sample)
    )
    assert "audit_organizational_change_adkar_adoption_readiness" in mod.__all__


def test_audit_benefits_realization_post_implementation_harvesting_on_track():
    """Caso 1: Todos los beneficios con owner, medición reciente y realización >=80% -> HARVESTING_ON_TRACK."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_benefits_realization_post_implementation_harvesting,
    )

    register = [
        {
            "benefit_id": "BEN-01",
            "target_annual_value": 100000.0,
            "realized_annualized_value": 92000.0,
            "benefit_owner_id": "OWN-FIN-01",
            "days_since_last_measurement": 15,
            "is_strategic_benefit": True,
        },
        {
            "benefit_id": "BEN-02",
            "target_annual_value": 50000.0,
            "realized_annualized_value": 45000.0,
            "benefit_owner_id": "OWN-OPS-02",
            "days_since_last_measurement": 20,
            "is_strategic_benefit": False,
        },
    ]
    res = audit_benefits_realization_post_implementation_harvesting(
        register, min_realization_rate_pct=80.0, max_measurement_lag_days=45
    )
    assert res["total_benefits"] == 2
    assert res["total_target_value"] == 150000.0
    assert res["total_realized_value"] == 137000.0
    assert res["portfolio_realization_rate_pct"] == 91.33
    assert res["unowned_benefit_ids"] == []
    assert res["underperforming_benefit_ids"] == []
    assert res["stale_measurement_benefit_ids"] == []
    assert res["missed_strategic_benefit_ids"] == []
    assert res["brm_governance_status"] == "HARVESTING_ON_TRACK"
    assert res["is_brm_healthy"] is True
    assert res["recommendations"] == []


def test_audit_benefits_realization_post_implementation_harvesting_warning():
    """Caso 2: Beneficio no estratégico bajo 80% o medición vencida (>45d), pero portafolio global >=80% y con owners -> WARNING."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_benefits_realization_post_implementation_harvesting,
    )

    register = [
        {
            "benefit_id": "BEN-CORE",
            "target_annual_value": 200000.0,
            "realized_annualized_value": 195000.0,
            "benefit_owner_id": "OWN-01",
            "days_since_last_measurement": 60,
            "is_strategic_benefit": True,
        },
        {
            "benefit_id": "BEN-MINOR",
            "target_annual_value": 20000.0,
            "realized_annualized_value": 12000.0,
            "benefit_owner_id": "OWN-02",
            "days_since_last_measurement": 10,
            "is_strategic_benefit": False,
        },
    ]
    res = audit_benefits_realization_post_implementation_harvesting(
        register, min_realization_rate_pct=80.0, max_measurement_lag_days=45
    )
    assert res["total_benefits"] == 2
    assert res["portfolio_realization_rate_pct"] == 94.09
    assert res["unowned_benefit_ids"] == []
    assert res["underperforming_benefit_ids"] == ["BEN-MINOR"]
    assert res["stale_measurement_benefit_ids"] == ["BEN-CORE"]
    assert res["missed_strategic_benefit_ids"] == []
    assert res["brm_governance_status"] == "WARNING"
    assert res["is_brm_healthy"] is False
    assert len(res["recommendations"]) >= 2


def test_audit_benefits_realization_post_implementation_harvesting_value_leakage():
    """Caso 3: Beneficio sin owner y beneficio estratégico incumplido -> VALUE_LEAKAGE."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_benefits_realization_post_implementation_harvesting,
    )

    register = [
        {
            "benefit_id": "BEN-STRAT-FAIL",
            "target_annual_value": 100000.0,
            "realized_annualized_value": 45000.0,
            "benefit_owner_id": None,
            "days_since_last_measurement": 90,
            "is_strategic_benefit": True,
        }
    ]
    res = audit_benefits_realization_post_implementation_harvesting(register)
    assert res["total_benefits"] == 1
    assert res["portfolio_realization_rate_pct"] == 45.0
    assert res["unowned_benefit_ids"] == ["BEN-STRAT-FAIL"]
    assert res["underperforming_benefit_ids"] == ["BEN-STRAT-FAIL"]
    assert res["missed_strategic_benefit_ids"] == ["BEN-STRAT-FAIL"]
    assert res["brm_governance_status"] == "VALUE_LEAKAGE"
    assert res["is_brm_healthy"] is False
    assert len(res["recommendations"]) >= 3


def test_audit_benefits_realization_post_implementation_harvesting_empty_and_binding():
    """Caso 4: Entradas vacías/inválidas y binding en ProjectLifecyclePMIService + __all__."""
    import backend.services.project_lifecycle_pmi_service as mod
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_benefits_realization_post_implementation_harvesting,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = audit_benefits_realization_post_implementation_harvesting(payload)  # type: ignore[arg-type]
        assert empty["total_benefits"] == 0
        assert empty["total_target_value"] == 0.0
        assert empty["total_realized_value"] == 0.0
        assert empty["portfolio_realization_rate_pct"] == 100.0
        assert empty["unowned_benefit_ids"] == []
        assert empty["underperforming_benefit_ids"] == []
        assert empty["stale_measurement_benefit_ids"] == []
        assert empty["missed_strategic_benefit_ids"] == []
        assert empty["brm_governance_status"] == "HARVESTING_ON_TRACK"
        assert empty["is_brm_healthy"] is True
        assert empty["recommendations"] == []

    sample = [
        {
            "benefit_id": "BEN-99",
            "target_annual_value": 50000.0,
            "realized_annualized_value": 50000.0,
            "benefit_owner_id": "OWN-99",
            "days_since_last_measurement": 5,
            "is_strategic_benefit": True,
        }
    ]
    assert (
        ProjectLifecyclePMIService.audit_benefits_realization_post_implementation_harvesting(
            sample
        )
        == audit_benefits_realization_post_implementation_harvesting(sample)
    )
    assert (
        "audit_benefits_realization_post_implementation_harvesting" in mod.__all__
    )


def test_audit_contract_claims_dispute_adr_and_liquidated_damages_controlled():
    """Caso 1: Reclamaciones cubiertas por reserva legal, negociación <=45d, con evidencia y sin penalidades -> CONTROLLED."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_contract_claims_dispute_adr_and_liquidated_damages,
    )

    claims = [
        {
            "claim_id": "CLM-01",
            "claimed_amount": 30000.0,
            "liquidated_damages_accrued": 0.0,
            "days_in_direct_negotiation": 20,
            "adr_mediation_initiated": False,
            "escalated_to_litigation": False,
            "has_contemporaneous_evidence_log": True,
        }
    ]
    res = audit_contract_claims_dispute_adr_and_liquidated_damages(
        claims, legal_contingency_reserve=50000.0, max_negotiation_days_before_adr=45
    )
    assert res["total_claims"] == 1
    assert res["total_claimed_amount"] == 30000.0
    assert res["total_liquidated_damages"] == 0.0
    assert res["total_dispute_exposure"] == 30000.0
    assert res["unfunded_dispute_exposure"] == 0.0
    assert res["overdue_adr_escalation_claim_ids"] == []
    assert res["unsubstantiated_evidence_claim_ids"] == []
    assert res["litigation_claim_ids"] == []
    assert res["claims_governance_status"] == "CONTROLLED"
    assert res["is_claims_controlled"] is True
    assert res["recommendations"] == []


def test_audit_contract_claims_dispute_adr_and_liquidated_damages_warning():
    """Caso 2: Negociación directa >45d sin iniciar ADR y daños liquidados >0 cubiertos por reserva -> WARNING."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_contract_claims_dispute_adr_and_liquidated_damages,
    )

    claims = [
        {
            "claim_id": "CLM-DELAY-10",
            "claimed_amount": 25000.0,
            "liquidated_damages_accrued": 5000.0,
            "days_in_direct_negotiation": 60,
            "adr_mediation_initiated": False,
            "escalated_to_litigation": False,
            "has_contemporaneous_evidence_log": True,
        }
    ]
    res = audit_contract_claims_dispute_adr_and_liquidated_damages(
        claims, legal_contingency_reserve=40000.0, max_negotiation_days_before_adr=45
    )
    assert res["total_claims"] == 1
    assert res["total_dispute_exposure"] == 30000.0
    assert res["unfunded_dispute_exposure"] == 0.0
    assert res["overdue_adr_escalation_claim_ids"] == ["CLM-DELAY-10"]
    assert res["unsubstantiated_evidence_claim_ids"] == []
    assert res["litigation_claim_ids"] == []
    assert res["claims_governance_status"] == "WARNING"
    assert res["is_claims_controlled"] is False
    assert len(res["recommendations"]) >= 2


def test_audit_contract_claims_dispute_adr_and_liquidated_damages_litigation_risk():
    """Caso 3: Litigio activo, falta de evidencia contemporánea y exposición no cubierta por reserva -> LITIGATION_OR_INSOLVENCY_RISK."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_contract_claims_dispute_adr_and_liquidated_damages,
    )

    claims = [
        {
            "claim_id": "CLM-COURT-20",
            "claimed_amount": 80000.0,
            "liquidated_damages_accrued": 20000.0,
            "days_in_direct_negotiation": 90,
            "adr_mediation_initiated": True,
            "escalated_to_litigation": True,
            "has_contemporaneous_evidence_log": False,
        }
    ]
    res = audit_contract_claims_dispute_adr_and_liquidated_damages(
        claims, legal_contingency_reserve=30000.0
    )
    assert res["total_claims"] == 1
    assert res["total_dispute_exposure"] == 100000.0
    assert res["unfunded_dispute_exposure"] == 70000.0
    assert res["unsubstantiated_evidence_claim_ids"] == ["CLM-COURT-20"]
    assert res["litigation_claim_ids"] == ["CLM-COURT-20"]
    assert res["claims_governance_status"] == "LITIGATION_OR_INSOLVENCY_RISK"
    assert res["is_claims_controlled"] is False
    assert len(res["recommendations"]) >= 3


def test_audit_contract_claims_dispute_adr_and_liquidated_damages_empty_and_binding():
    """Caso 4: Entradas vacías/inválidas y binding en ProjectLifecyclePMIService + __all__."""
    import backend.services.project_lifecycle_pmi_service as mod
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_contract_claims_dispute_adr_and_liquidated_damages,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = audit_contract_claims_dispute_adr_and_liquidated_damages(payload)  # type: ignore[arg-type]
        assert empty["total_claims"] == 0
        assert empty["total_claimed_amount"] == 0.0
        assert empty["total_liquidated_damages"] == 0.0
        assert empty["total_dispute_exposure"] == 0.0
        assert empty["unfunded_dispute_exposure"] == 0.0
        assert empty["overdue_adr_escalation_claim_ids"] == []
        assert empty["unsubstantiated_evidence_claim_ids"] == []
        assert empty["litigation_claim_ids"] == []
        assert empty["claims_governance_status"] == "CONTROLLED"
        assert empty["is_claims_controlled"] is True
        assert empty["recommendations"] == []

    sample = [
        {
            "claim_id": "CLM-99",
            "claimed_amount": 10000.0,
            "liquidated_damages_accrued": 0.0,
            "days_in_direct_negotiation": 10,
            "adr_mediation_initiated": False,
            "escalated_to_litigation": False,
            "has_contemporaneous_evidence_log": True,
        }
    ]
    assert (
        ProjectLifecyclePMIService.audit_contract_claims_dispute_adr_and_liquidated_damages(
            sample, legal_contingency_reserve=20000.0
        )
        == audit_contract_claims_dispute_adr_and_liquidated_damages(
            sample, legal_contingency_reserve=20000.0
        )
    )
    assert (
        "audit_contract_claims_dispute_adr_and_liquidated_damages" in mod.__all__
    )


def test_audit_stakeholder_salience_drift_and_resistance_escalation_critical_resistance():
    from backend.services.project_lifecycle_pmi_service import (
        audit_stakeholder_salience_drift_and_resistance_escalation,
    )

    res = audit_stakeholder_salience_drift_and_resistance_escalation(
        [
            {
                "stakeholder_id": "SH-VP-SEC",
                "name": "VP Security",
                "power_level": "HIGH",
                "interest_level": "HIGH",
                "current_engagement": "RESISTANT",
                "desired_engagement": "SUPPORTIVE",
                "days_since_last_touchpoint": 20,
                "has_mitigation_action_plan": False,
            },
            {
                "stakeholder_id": "SH-PMO",
                "name": "PMO Lead",
                "power_level": "MEDIUM",
                "interest_level": "HIGH",
                "current_engagement": "SUPPORTIVE",
                "desired_engagement": "SUPPORTIVE",
                "days_since_last_touchpoint": 5,
                "has_mitigation_action_plan": True,
            },
        ],
        max_days_without_touchpoint_high_power=14,
        max_unresolved_resistance_pct=15.0,
    )
    assert res["total_stakeholders"] == 2
    assert res["high_power_count"] == 1
    assert res["engagement_gap_count"] == 1
    assert res["stale_high_power_touchpoint_ids"] == ["SH-VP-SEC"]
    assert res["unmitigated_high_power_resistance_ids"] == ["SH-VP-SEC"]
    assert res["resistant_or_unaware_pct"] == 50.0
    assert res["salience_health_status"] == "CRITICAL_RESISTANCE"
    assert res["is_stakeholder_engagement_compliant"] is False


def test_audit_stakeholder_salience_drift_and_resistance_escalation_drifting():
    from backend.services.project_lifecycle_pmi_service import (
        audit_stakeholder_salience_drift_and_resistance_escalation,
    )

    res = audit_stakeholder_salience_drift_and_resistance_escalation(
        [
            {
                "stakeholder_id": "SH-SPONSOR",
                "name": "Exec Sponsor",
                "power_level": "HIGH",
                "interest_level": "HIGH",
                "current_engagement": "SUPPORTIVE",
                "desired_engagement": "LEADING",
                "days_since_last_touchpoint": 18,
                "has_mitigation_action_plan": True,
            }
        ],
        max_days_without_touchpoint_high_power=14,
        max_unresolved_resistance_pct=15.0,
    )
    assert res["total_stakeholders"] == 1
    assert res["high_power_count"] == 1
    assert res["engagement_gap_count"] == 1
    assert res["stale_high_power_touchpoint_ids"] == ["SH-SPONSOR"]
    assert res["unmitigated_high_power_resistance_ids"] == []
    assert res["resistant_or_unaware_pct"] == 0.0
    assert res["salience_health_status"] == "DRIFTING"
    assert res["is_stakeholder_engagement_compliant"] is False


def test_audit_stakeholder_salience_drift_and_resistance_escalation_optimal_and_empty():
    from backend.services.project_lifecycle_pmi_service import (
        audit_stakeholder_salience_drift_and_resistance_escalation,
    )

    empty = audit_stakeholder_salience_drift_and_resistance_escalation(
        [{"stakeholder_id": "   "}, "invalid"]  # type: ignore[list-item]
    )
    assert empty["total_stakeholders"] == 0
    assert empty["high_power_count"] == 0
    assert empty["engagement_gap_count"] == 0
    assert empty["resistant_or_unaware_pct"] == 0.0
    assert empty["salience_health_status"] == "OPTIMAL"
    assert empty["is_stakeholder_engagement_compliant"] is True

    optimal = audit_stakeholder_salience_drift_and_resistance_escalation(
        [
            {
                "stakeholder_id": "SH-01",
                "name": "Product Owner",
                "power_level": "HIGH",
                "interest_level": "HIGH",
                "current_engagement": "LEADING",
                "desired_engagement": "LEADING",
                "days_since_last_touchpoint": 4,
                "has_mitigation_action_plan": True,
            }
        ]
    )
    assert optimal["total_stakeholders"] == 1
    assert optimal["engagement_gap_count"] == 0
    assert optimal["stale_high_power_touchpoint_ids"] == []
    assert optimal["unmitigated_high_power_resistance_ids"] == []
    assert optimal["salience_health_status"] == "OPTIMAL"
    assert optimal["is_stakeholder_engagement_compliant"] is True


def test_audit_stakeholder_salience_drift_and_resistance_escalation_staticmethod_and_dunder_all():
    import backend.services.project_lifecycle_pmi_service as mod
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_stakeholder_salience_drift_and_resistance_escalation,
    )

    sample = [
        {
            "stakeholder_id": "SH-99",
            "power_level": "LOW",
            "interest_level": "MEDIUM",
            "current_engagement": "NEUTRAL",
            "desired_engagement": "NEUTRAL",
            "days_since_last_touchpoint": 5,
        }
    ]
    assert (
        ProjectLifecyclePMIService.audit_stakeholder_salience_drift_and_resistance_escalation(
            sample
        )
        == audit_stakeholder_salience_drift_and_resistance_escalation(sample)
    )
    assert (
        "audit_stakeholder_salience_drift_and_resistance_escalation" in mod.__all__
    )


def test_audit_procurement_rfp_bid_solvency_and_vendor_concentration_award_blocked():
    from backend.services.project_lifecycle_pmi_service import (
        audit_procurement_rfp_bid_solvency_and_vendor_concentration,
    )

    res = audit_procurement_rfp_bid_solvency_and_vendor_concentration(
        [
            {
                "bid_id": "BID-101",
                "vendor_id": "VND-A",
                "technical_evaluation_score": 58.0,
                "altman_z_solvency_score": 1.2,
                "proposed_contract_value": 120000.0,
                "is_awarded_winner": True,
                "has_conflict_of_interest_declaration": True,
            },
            {
                "bid_id": "BID-102",
                "vendor_id": "VND-B",
                "technical_evaluation_score": 88.0,
                "altman_z_solvency_score": 3.1,
                "proposed_contract_value": 100000.0,
                "is_awarded_winner": False,
                "has_conflict_of_interest_declaration": False,
            },
        ],
        min_technical_score=70.0,
        min_altman_z_solvency_score=1.8,
        max_single_vendor_spend_share_pct=60.0,
    )
    assert res["total_bids_evaluated"] == 2
    assert res["awarded_bids_count"] == 1
    assert res["total_awarded_spend"] == 120000.0
    assert res["technically_unqualified_award_ids"] == ["BID-101"]
    assert res["insolvent_vendor_award_ids"] == ["BID-101"]
    assert res["missing_coi_declaration_bid_ids"] == ["BID-102"]
    assert res["concentrated_vendor_ids"] == ["VND-A"]
    assert res["procurement_governance_status"] == "AWARD_BLOCKED"
    assert res["is_procurement_compliant"] is False


def test_audit_procurement_rfp_bid_solvency_and_vendor_concentration_concentration_warning():
    from backend.services.project_lifecycle_pmi_service import (
        audit_procurement_rfp_bid_solvency_and_vendor_concentration,
    )

    res = audit_procurement_rfp_bid_solvency_and_vendor_concentration(
        [
            {
                "bid_id": "BID-201",
                "vendor_id": "VND-DOMINANT",
                "technical_evaluation_score": 85.0,
                "altman_z_solvency_score": 2.9,
                "proposed_contract_value": 80000.0,
                "is_awarded_winner": True,
                "has_conflict_of_interest_declaration": True,
            },
            {
                "bid_id": "BID-202",
                "vendor_id": "VND-SECONDARY",
                "technical_evaluation_score": 82.0,
                "altman_z_solvency_score": 2.4,
                "proposed_contract_value": 20000.0,
                "is_awarded_winner": True,
                "has_conflict_of_interest_declaration": True,
            },
        ],
        min_technical_score=70.0,
        min_altman_z_solvency_score=1.8,
        max_single_vendor_spend_share_pct=60.0,
    )
    assert res["awarded_bids_count"] == 2
    assert res["total_awarded_spend"] == 100000.0
    assert res["technically_unqualified_award_ids"] == []
    assert res["insolvent_vendor_award_ids"] == []
    assert res["missing_coi_declaration_bid_ids"] == []
    assert res["concentrated_vendor_ids"] == ["VND-DOMINANT"]
    assert res["procurement_governance_status"] == "CONCENTRATION_RISK_WARNING"
    assert res["is_procurement_compliant"] is False


def test_audit_procurement_rfp_bid_solvency_and_vendor_concentration_compliant_and_empty():
    from backend.services.project_lifecycle_pmi_service import (
        audit_procurement_rfp_bid_solvency_and_vendor_concentration,
    )

    empty = audit_procurement_rfp_bid_solvency_and_vendor_concentration(
        [{"bid_id": "   "}, "invalid"]  # type: ignore[list-item]
    )
    assert empty["total_bids_evaluated"] == 0
    assert empty["awarded_bids_count"] == 0
    assert empty["total_awarded_spend"] == 0.0
    assert empty["procurement_governance_status"] == "PROCUREMENT_COMPLIANT"
    assert empty["is_procurement_compliant"] is True

    compliant = audit_procurement_rfp_bid_solvency_and_vendor_concentration(
        [
            {
                "bid_id": "BID-301",
                "vendor_id": "VND-1",
                "technical_evaluation_score": 90.0,
                "altman_z_solvency_score": 3.0,
                "proposed_contract_value": 50000.0,
                "is_awarded_winner": True,
                "has_conflict_of_interest_declaration": True,
            },
            {
                "bid_id": "BID-302",
                "vendor_id": "VND-2",
                "technical_evaluation_score": 88.0,
                "altman_z_solvency_score": 2.7,
                "proposed_contract_value": 50000.0,
                "is_awarded_winner": True,
                "has_conflict_of_interest_declaration": True,
            },
        ],
        max_single_vendor_spend_share_pct=60.0,
    )
    assert compliant["awarded_bids_count"] == 2
    assert compliant["concentrated_vendor_ids"] == []
    assert compliant["procurement_governance_status"] == "PROCUREMENT_COMPLIANT"
    assert compliant["is_procurement_compliant"] is True


def test_audit_procurement_rfp_bid_solvency_and_vendor_concentration_staticmethod_and_dunder_all():
    import backend.services.project_lifecycle_pmi_service as mod
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_procurement_rfp_bid_solvency_and_vendor_concentration,
    )

    sample = [
        {
            "bid_id": "BID-99",
            "vendor_id": "VND-99",
            "technical_evaluation_score": 80.0,
            "altman_z_solvency_score": 2.5,
            "proposed_contract_value": 10000.0,
            "is_awarded_winner": False,
            "has_conflict_of_interest_declaration": True,
        }
    ]
    assert (
        ProjectLifecyclePMIService.audit_procurement_rfp_bid_solvency_and_vendor_concentration(
            sample
        )
        == audit_procurement_rfp_bid_solvency_and_vendor_concentration(sample)
    )
    assert (
        "audit_procurement_rfp_bid_solvency_and_vendor_concentration"
        in mod.__all__
    )


def test_audit_steering_committee_quorum_and_decision_latency_effective():
    """Caso 1: Sesiones con quórum >= 75%, bloqueos resueltos <= 5 días y actas firmadas -> EFFECTIVE_STEERING."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_steering_committee_quorum_and_decision_latency,
    )

    sessions = [
        {
            "session_id": "STEER-2026-01",
            "voting_members_invited": 8,
            "voting_members_present": 7,  # 87.5%
            "blocker_escalation_age_days": 2.5,
            "has_signed_minutes_and_action_owners": True,
            "was_critical_decision_deferred_without_owner": False,
        },
        {
            "session_id": "STEER-2026-02",
            "voting_members_invited": 4,
            "voting_members_present": 3,  # 75.0%
            "blocker_escalation_age_days": 5.0,
            "has_signed_minutes_and_action_owners": True,
            "was_critical_decision_deferred_without_owner": False,
        },
    ]
    res = audit_steering_committee_quorum_and_decision_latency(
        sessions, min_quorum_attendance_pct=75.0, max_blocker_decision_days=5.0
    )
    assert res["total_sessions_evaluated"] == 2
    assert res["quorum_failed_session_ids"] == []
    assert res["decision_sla_breach_session_ids"] == []
    assert res["unrecorded_minutes_session_ids"] == []
    assert res["steering_governance_status"] == "EFFECTIVE_STEERING"
    assert res["is_steering_compliant"] is True


def test_audit_steering_committee_quorum_and_decision_latency_minutes_warning():
    """Caso 2: Quórum y SLA cumplidos pero falta acta firmada y responsables -> MINUTES_HYGIENE_WARNING."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_steering_committee_quorum_and_decision_latency,
    )

    sessions = [
        {
            "session_id": "STEER-2026-03",
            "voting_members_invited": 5,
            "voting_members_present": 5,
            "blocker_escalation_age_days": 1.0,
            "has_signed_minutes_and_action_owners": False,
            "was_critical_decision_deferred_without_owner": False,
        }
    ]
    res = audit_steering_committee_quorum_and_decision_latency(
        sessions, min_quorum_attendance_pct=75.0, max_blocker_decision_days=5.0
    )
    assert res["total_sessions_evaluated"] == 1
    assert res["quorum_failed_session_ids"] == []
    assert res["decision_sla_breach_session_ids"] == []
    assert res["unrecorded_minutes_session_ids"] == ["STEER-2026-03"]
    assert res["steering_governance_status"] == "MINUTES_HYGIENE_WARNING"
    assert res["is_steering_compliant"] is False


def test_audit_steering_committee_quorum_and_decision_latency_paralysis():
    """Caso 3: Falta de quórum (<75%), bloqueo >5 días o decisión diferida sin responsable -> GOVERNANCE_PARALYSIS."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_steering_committee_quorum_and_decision_latency,
    )

    sessions = [
        {
            "session_id": "STEER-NO-QUORUM",
            "voting_members_invited": 6,
            "voting_members_present": 3,  # 50% < 75%
            "blocker_escalation_age_days": 8.0,  # > 5d
            "has_signed_minutes_and_action_owners": False,
            "was_critical_decision_deferred_without_owner": False,
        },
        {
            "session_id": "STEER-DEFERRED",
            "voting_members_invited": 4,
            "voting_members_present": 4,
            "blocker_escalation_age_days": 2.0,
            "has_signed_minutes_and_action_owners": True,
            "was_critical_decision_deferred_without_owner": True,
        },
    ]
    res = audit_steering_committee_quorum_and_decision_latency(
        sessions, min_quorum_attendance_pct=75.0, max_blocker_decision_days=5.0
    )
    assert res["total_sessions_evaluated"] == 2
    assert res["quorum_failed_session_ids"] == ["STEER-NO-QUORUM"]
    assert res["decision_sla_breach_session_ids"] == [
        "STEER-NO-QUORUM",
        "STEER-DEFERRED",
    ]
    assert res["unrecorded_minutes_session_ids"] == ["STEER-NO-QUORUM"]
    assert res["steering_governance_status"] == "GOVERNANCE_PARALYSIS"
    assert res["is_steering_compliant"] is False


def test_audit_steering_committee_quorum_and_decision_latency_empty_and_binding():
    """Caso 4: Entradas vacías/inválidas y binding en ProjectLifecyclePMIService + __all__."""
    import backend.services.project_lifecycle_pmi_service as mod
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_steering_committee_quorum_and_decision_latency,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = audit_steering_committee_quorum_and_decision_latency(payload)  # type: ignore[arg-type]
        assert empty["total_sessions_evaluated"] == 0
        assert empty["quorum_failed_session_ids"] == []
        assert empty["decision_sla_breach_session_ids"] == []
        assert empty["unrecorded_minutes_session_ids"] == []
        assert empty["steering_governance_status"] == "EFFECTIVE_STEERING"
        assert empty["is_steering_compliant"] is True

    sample = [
        {
            "session_id": "STEER-99",
            "voting_members_invited": 4,
            "voting_members_present": 4,
            "blocker_escalation_age_days": 1.0,
            "has_signed_minutes_and_action_owners": True,
            "was_critical_decision_deferred_without_owner": False,
        }
    ]
    assert (
        ProjectLifecyclePMIService.audit_steering_committee_quorum_and_decision_latency(
            sample
        )
        == audit_steering_committee_quorum_and_decision_latency(sample)
    )
    assert (
        "audit_steering_committee_quorum_and_decision_latency" in mod.__all__
    )



def test_audit_warranty_escrow_breach_paths():
    """Caso 1: escrow prematuro en condiciones de riesgo -> ESCROW_OR_DEFECT_BREACH."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_warranty_defect_liability_and_escrow_release_gate,
    )

    res = audit_warranty_defect_liability_and_escrow_release_gate(
        [
            {
                "contract_id": "CTR-01",
                "warranty_elapsed_days": 30,
                "open_sev1_sev2_latent_defects": 0,
                "max_defect_resolution_hours_observed": 12.0,
                "escrow_released_prematurely": True,
                "has_final_lien_waiver_signed": True,
            },
            {
                "contract_id": "CTR-02",
                "warranty_elapsed_days": 120,
                "open_sev1_sev2_latent_defects": 0,
                "max_defect_resolution_hours_observed": 20.0,
                "escrow_released_prematurely": False,
                "has_final_lien_waiver_signed": False,
            },
        ]
    )
    assert res["total_contracts_evaluated"] == 2
    # CTR-01: escrow liberado con DLP 30 < 90 -> prematuro.
    assert res["premature_escrow_release_contract_ids"] == ["CTR-01"]
    assert res["unresolved_latent_defect_contract_ids"] == []
    assert res["sla_breach_defect_contract_ids"] == []
    assert res["missing_lien_waiver_contract_ids"] == ["CTR-02"]
    assert res["warranty_escrow_status"] == "ESCROW_OR_DEFECT_BREACH"
    assert res["is_escrow_release_compliant"] is False

    # Escrow prematuro disparado SOLO por defectos abiertos (DLP vencido y lien firmado).
    res_defect = audit_warranty_defect_liability_and_escrow_release_gate(
        [
            {
                "contract_id": "CTR-03",
                "warranty_elapsed_days": 150,
                "open_sev1_sev2_latent_defects": 2,
                "max_defect_resolution_hours_observed": 10.0,
                "escrow_released_prematurely": True,
                "has_final_lien_waiver_signed": True,
            },
        ]
    )
    assert res_defect["premature_escrow_release_contract_ids"] == ["CTR-03"]
    assert res_defect["unresolved_latent_defect_contract_ids"] == ["CTR-03"]
    assert res_defect["warranty_escrow_status"] == "ESCROW_OR_DEFECT_BREACH"


def test_audit_warranty_escrow_sla_warning_only():
    """Caso 2: solo SLA de remediación excedido -> REMEDIATION_SLA_WARNING."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_warranty_defect_liability_and_escrow_release_gate,
    )

    res = audit_warranty_defect_liability_and_escrow_release_gate(
        [
            {
                "contract_id": "CTR-10",
                "warranty_elapsed_days": 100,
                "open_sev1_sev2_latent_defects": 0,
                "max_defect_resolution_hours_observed": 72.0,
                "escrow_released_prematurely": False,
                "has_final_lien_waiver_signed": True,
            },
        ]
    )
    # SLA: 72.0 > 48.0; sin defectos, DLP vencido, lien firmado, escrow en regla.
    assert res["total_contracts_evaluated"] == 1
    assert res["premature_escrow_release_contract_ids"] == []
    assert res["unresolved_latent_defect_contract_ids"] == []
    assert res["sla_breach_defect_contract_ids"] == ["CTR-10"]
    assert res["missing_lien_waiver_contract_ids"] == []
    assert res["warranty_escrow_status"] == "REMEDIATION_SLA_WARNING"
    assert res["is_escrow_release_compliant"] is False

    # Precisión: ESCROW_OR_DEFECT_BREACH domina sobre SLA WARNING.
    res_mixed = audit_warranty_defect_liability_and_escrow_release_gate(
        [
            {
                "contract_id": "CTR-11",
                "warranty_elapsed_days": 100,
                "open_sev1_sev2_latent_defects": 0,
                "max_defect_resolution_hours_observed": 72.0,
                "has_final_lien_waiver_signed": False,
            },
        ]
    )
    assert res_mixed["sla_breach_defect_contract_ids"] == ["CTR-11"]
    assert res_mixed["missing_lien_waiver_contract_ids"] == ["CTR-11"]
    assert res_mixed["warranty_escrow_status"] == "ESCROW_OR_DEFECT_BREACH"


def test_audit_warranty_escrow_ready_and_boundaries():
    """Caso 3: fronteras exactas (DLP = 90, SLA = 48.0 inclusive) -> WARRANTY_RELEASE_READY."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_warranty_defect_liability_and_escrow_release_gate,
    )

    res = audit_warranty_defect_liability_and_escrow_release_gate(
        [
            {
                "contract_id": "CTR-20",
                "warranty_elapsed_days": 90,
                "open_sev1_sev2_latent_defects": 0,
                "max_defect_resolution_hours_observed": 48.0,
                "escrow_released_prematurely": False,
                "has_final_lien_waiver_signed": True,
            },
            {
                "contract_id": "CTR-21",
                "warranty_elapsed_days": 365,
                "open_sev1_sev2_latent_defects": 0,
                "max_defect_resolution_hours_observed": 6.0,
            },
        ]
    )
    # CTR-20: DLP 90 no < 90; SLA 48.0 no > 48.0. CTR-21: defaults correctos.
    assert res["total_contracts_evaluated"] == 2
    assert res["premature_escrow_release_contract_ids"] == []
    assert res["unresolved_latent_defect_contract_ids"] == []
    assert res["sla_breach_defect_contract_ids"] == []
    assert res["missing_lien_waiver_contract_ids"] == []
    assert res["warranty_escrow_status"] == "WARRANTY_RELEASE_READY"
    assert res["is_escrow_release_compliant"] is True


def test_audit_warranty_escrow_invalid_and_binding():
    """Caso 4: entradas no-lista/no-dict y binding + __all__."""
    import backend.services.project_lifecycle_pmi_service as mod
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_warranty_defect_liability_and_escrow_release_gate,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = audit_warranty_defect_liability_and_escrow_release_gate(payload)  # type: ignore[arg-type]
        assert empty["total_contracts_evaluated"] == 0
        assert empty["premature_escrow_release_contract_ids"] == []
        assert empty["unresolved_latent_defect_contract_ids"] == []
        assert empty["sla_breach_defect_contract_ids"] == []
        assert empty["missing_lien_waiver_contract_ids"] == []
        assert empty["warranty_escrow_status"] == "WARRANTY_RELEASE_READY"
        assert empty["is_escrow_release_compliant"] is True

    sample = [
        {
            "contract_id": "CTR-30",
            "warranty_elapsed_days": 200,
            "open_sev1_sev2_latent_defects": 0,
            "max_defect_resolution_hours_observed": 10.0,
            "has_final_lien_waiver_signed": True,
        },
    ]
    assert (
        ProjectLifecyclePMIService.audit_warranty_defect_liability_and_escrow_release_gate(sample)
        == audit_warranty_defect_liability_and_escrow_release_gate(sample)
    )
    assert "audit_warranty_defect_liability_and_escrow_release_gate" in mod.__all__


def test_audit_regulatory_permits_and_statutory_compliance_readiness_shutdown_risk():
    from backend.services.project_lifecycle_pmi_service import (
        audit_regulatory_permits_and_statutory_compliance_readiness,
    )

    res = audit_regulatory_permits_and_statutory_compliance_readiness(
        [
            {
                "permit_id": "PRM-ENV-01",
                "days_until_expiration": 0,
                "is_mandatory_for_operation": True,
                "has_renewal_application_submitted": True,
                "has_evidentiary_audit_trail": True,
                "potential_statutory_fine_amount": 50000.0,
            },
            {
                "permit_id": "PRM-DATA-02",
                "days_until_expiration": 60,
                "is_mandatory_for_operation": True,
                "has_renewal_application_submitted": False,
                "has_evidentiary_audit_trail": False,
                "potential_statutory_fine_amount": 25000.0,
            },
        ],
        min_renewal_buffer_days=30,
    )
    assert res["total_permits_evaluated"] == 2
    assert res["expired_mandatory_permit_ids"] == ["PRM-ENV-01"]
    assert res["unsubmitted_renewal_at_risk_permit_ids"] == []
    assert res["missing_audit_trail_permit_ids"] == ["PRM-DATA-02"]
    assert res["total_statutory_fine_exposure"] == 75000.0
    assert res["regulatory_governance_status"] == "STATUTORY_SHUTDOWN_RISK"
    assert res["is_regulatory_compliant"] is False


def test_audit_regulatory_permits_and_statutory_compliance_readiness_renewal_warning():
    from backend.services.project_lifecycle_pmi_service import (
        audit_regulatory_permits_and_statutory_compliance_readiness,
    )

    res = audit_regulatory_permits_and_statutory_compliance_readiness(
        [
            {
                "permit_id": "PRM-MUNICIPAL-10",
                "days_until_expiration": 15,
                "is_mandatory_for_operation": True,
                "has_renewal_application_submitted": False,
                "has_evidentiary_audit_trail": True,
                "potential_statutory_fine_amount": 12000.0,
            }
        ],
        min_renewal_buffer_days=30,
    )
    assert res["expired_mandatory_permit_ids"] == []
    assert res["unsubmitted_renewal_at_risk_permit_ids"] == ["PRM-MUNICIPAL-10"]
    assert res["missing_audit_trail_permit_ids"] == []
    assert res["total_statutory_fine_exposure"] == 12000.0
    assert res["regulatory_governance_status"] == "RENEWAL_BUFFER_WARNING"
    assert res["is_regulatory_compliant"] is False


def test_audit_regulatory_permits_and_statutory_compliance_readiness_compliant_and_empty():
    from backend.services.project_lifecycle_pmi_service import (
        audit_regulatory_permits_and_statutory_compliance_readiness,
    )

    empty = audit_regulatory_permits_and_statutory_compliance_readiness(
        [{"permit_id": "   "}, "invalid"]  # type: ignore[list-item]
    )
    assert empty["total_permits_evaluated"] == 0
    assert empty["total_statutory_fine_exposure"] == 0.0
    assert empty["regulatory_governance_status"] == "REGULATORY_COMPLIANT"
    assert empty["is_regulatory_compliant"] is True

    compliant = audit_regulatory_permits_and_statutory_compliance_readiness(
        [
            {
                "permit_id": "PRM-CLEAN-01",
                "days_until_expiration": 120,
                "is_mandatory_for_operation": True,
                "has_renewal_application_submitted": False,
                "has_evidentiary_audit_trail": True,
                "potential_statutory_fine_amount": 40000.0,
            },
            {
                "permit_id": "PRM-RENEWING-02",
                "days_until_expiration": 10,
                "is_mandatory_for_operation": True,
                "has_renewal_application_submitted": True,
                "has_evidentiary_audit_trail": True,
                "potential_statutory_fine_amount": 15000.0,
            },
        ],
        min_renewal_buffer_days=30,
    )
    assert compliant["total_permits_evaluated"] == 2
    assert compliant["total_statutory_fine_exposure"] == 0.0
    assert compliant["regulatory_governance_status"] == "REGULATORY_COMPLIANT"
    assert compliant["is_regulatory_compliant"] is True


def test_audit_regulatory_permits_and_statutory_compliance_readiness_staticmethod_and_dunder_all():
    import backend.services.project_lifecycle_pmi_service as mod
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_regulatory_permits_and_statutory_compliance_readiness,
    )

    sample = [
        {
            "permit_id": "PRM-99",
            "days_until_expiration": 90,
            "is_mandatory_for_operation": True,
            "has_evidentiary_audit_trail": True,
        }
    ]
    assert (
        ProjectLifecyclePMIService.audit_regulatory_permits_and_statutory_compliance_readiness(
            sample
        )
        == audit_regulatory_permits_and_statutory_compliance_readiness(sample)
    )
    assert (
        "audit_regulatory_permits_and_statutory_compliance_readiness"
        in mod.__all__
    )


def test_audit_charter_business_case_irr_wacc_spread_and_payback_blocked():
    from backend.services.project_lifecycle_pmi_service import (
        audit_charter_business_case_irr_wacc_spread_and_payback,
    )

    res = audit_charter_business_case_irr_wacc_spread_and_payback(
        [
            {
                "charter_id": "CHT-LOW-IRR",
                "projected_irr_pct": 10.5,
                "corporate_wacc_hurdle_pct": 10.0,
                "payback_period_months": 24,
                "has_executive_sponsor_signature": True,
                "has_measurable_success_criteria": True,
            },
            {
                "charter_id": "CHT-UNSIGNED",
                "projected_irr_pct": 18.0,
                "corporate_wacc_hurdle_pct": 10.0,
                "payback_period_months": 18,
                "has_executive_sponsor_signature": False,
                "has_measurable_success_criteria": True,
            },
        ],
        min_irr_over_wacc_spread_pct=2.0,
        max_payback_months=36,
    )
    assert res["total_charters_evaluated"] == 2
    assert res["value_destroying_charter_ids"] == ["CHT-LOW-IRR"]
    assert res["unsigned_or_unmeasurable_charter_ids"] == ["CHT-UNSIGNED"]
    assert res["excessive_payback_charter_ids"] == []
    assert res["charter_viability_status"] == "CHARTER_AUTHORIZATION_BLOCKED"
    assert res["is_charter_viable"] is False


def test_audit_charter_business_case_irr_wacc_spread_and_payback_payback_warning():
    from backend.services.project_lifecycle_pmi_service import (
        audit_charter_business_case_irr_wacc_spread_and_payback,
    )

    res = audit_charter_business_case_irr_wacc_spread_and_payback(
        [
            {
                "charter_id": "CHT-LONG-HORIZON",
                "projected_irr_pct": 16.0,
                "corporate_wacc_hurdle_pct": 10.0,
                "payback_period_months": 48,
                "has_executive_sponsor_signature": True,
                "has_measurable_success_criteria": True,
            }
        ],
        min_irr_over_wacc_spread_pct=2.0,
        max_payback_months=36,
    )
    assert res["value_destroying_charter_ids"] == []
    assert res["unsigned_or_unmeasurable_charter_ids"] == []
    assert res["excessive_payback_charter_ids"] == ["CHT-LONG-HORIZON"]
    assert res["charter_viability_status"] == "PAYBACK_HORIZON_WARNING"
    assert res["is_charter_viable"] is False


def test_audit_charter_business_case_irr_wacc_spread_and_payback_sound_and_empty():
    from backend.services.project_lifecycle_pmi_service import (
        audit_charter_business_case_irr_wacc_spread_and_payback,
    )

    empty = audit_charter_business_case_irr_wacc_spread_and_payback(
        [{"charter_id": "   "}, "invalid"]  # type: ignore[list-item]
    )
    assert empty["total_charters_evaluated"] == 0
    assert empty["charter_viability_status"] == "CHARTER_INVESTMENT_SOUND"
    assert empty["is_charter_viable"] is True

    sound = audit_charter_business_case_irr_wacc_spread_and_payback(
        [
            {
                "charter_id": "CHT-PRIME-01",
                "projected_irr_pct": 15.5,
                "corporate_wacc_hurdle_pct": 10.0,
                "payback_period_months": 20,
                "has_executive_sponsor_signature": True,
                "has_measurable_success_criteria": True,
            }
        ],
        min_irr_over_wacc_spread_pct=2.0,
        max_payback_months=36,
    )
    assert sound["total_charters_evaluated"] == 1
    assert sound["charter_viability_status"] == "CHARTER_INVESTMENT_SOUND"
    assert sound["is_charter_viable"] is True


def test_audit_charter_business_case_irr_wacc_spread_and_payback_staticmethod_and_dunder_all():
    import backend.services.project_lifecycle_pmi_service as mod
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_charter_business_case_irr_wacc_spread_and_payback,
    )

    sample = [
        {
            "charter_id": "CHT-99",
            "projected_irr_pct": 14.0,
            "corporate_wacc_hurdle_pct": 10.0,
            "payback_period_months": 24,
        }
    ]
    assert (
        ProjectLifecyclePMIService.audit_charter_business_case_irr_wacc_spread_and_payback(
            sample
        )
        == audit_charter_business_case_irr_wacc_spread_and_payback(sample)
    )
    assert (
        "audit_charter_business_case_irr_wacc_spread_and_payback"
        in mod.__all__
    )


def test_audit_project_closure_lessons_learned_and_pir_archival_breaches():
    from backend.services.project_lifecycle_pmi_service import (
        audit_project_closure_lessons_learned_and_pir_archival,
    )

    result = audit_project_closure_lessons_learned_and_pir_archival(
        [
            {
                "package_id": "CLS-001",
                "days_since_handover_to_pir": 15,
                "pir_completed": True,
                "actionable_lessons_documented_count": 4,
                "indexed_in_organizational_process_assets": False,
                "sponsor_final_archival_signed": True,
            },
            {
                "package_id": "CLS-002",
                "days_since_handover_to_pir": 20,
                "pir_completed": True,
                "actionable_lessons_documented_count": 5,
                "indexed_in_organizational_process_assets": True,
                "sponsor_final_archival_signed": False,
            },
            {
                "package_id": "CLS-003",
                "days_since_handover_to_pir": 45,
                "pir_completed": True,
                "actionable_lessons_documented_count": 6,
                "indexed_in_organizational_process_assets": True,
                "sponsor_final_archival_signed": True,
            },
            {
                "package_id": "CLS-004",
                "days_since_handover_to_pir": 10,
                "pir_completed": False,
                "actionable_lessons_documented_count": 3,
                "indexed_in_organizational_process_assets": True,
                "sponsor_final_archival_signed": True,
            },
        ],
        max_days_to_pir_completion=30,
        min_actionable_lessons_count=3,
    )
    assert result["evaluated_closure_packages_count"] == 4
    assert result["unarchived_or_unsigned_package_ids"] == ["CLS-001", "CLS-002"]
    assert result["overdue_or_incomplete_pir_package_ids"] == ["CLS-003", "CLS-004"]
    assert result["insufficient_lessons_package_ids"] == []
    assert result["closure_archival_status"] == "CLOSURE_ARCHIVAL_GOVERNANCE_BREACH"
    assert result["is_closure_archival_compliant"] is False


def test_audit_project_closure_lessons_learned_and_pir_archival_warning():
    from backend.services.project_lifecycle_pmi_service import (
        audit_project_closure_lessons_learned_and_pir_archival,
    )

    result = audit_project_closure_lessons_learned_and_pir_archival(
        [
            {
                "package_id": "CLS-WARN-1",
                "days_since_handover_to_pir": 30,
                "pir_completed": True,
                "actionable_lessons_documented_count": 2,
                "indexed_in_organizational_process_assets": True,
                "sponsor_final_archival_signed": True,
            }
        ],
        max_days_to_pir_completion=30,
        min_actionable_lessons_count=3,
    )
    assert result["evaluated_closure_packages_count"] == 1
    assert result["unarchived_or_unsigned_package_ids"] == []
    assert result["overdue_or_incomplete_pir_package_ids"] == []
    assert result["insufficient_lessons_package_ids"] == ["CLS-WARN-1"]
    assert result["closure_archival_status"] == "CLOSURE_LESSONS_DENSITY_WARNING"
    assert result["is_closure_archival_compliant"] is False


def test_audit_project_closure_lessons_learned_and_pir_archival_optimal_and_empty():
    from backend.services.project_lifecycle_pmi_service import (
        audit_project_closure_lessons_learned_and_pir_archival,
    )

    empty = audit_project_closure_lessons_learned_and_pir_archival(
        [{"package_id": "   "}, "invalid"]  # type: ignore[list-item]
    )
    assert empty["evaluated_closure_packages_count"] == 0
    assert empty["closure_archival_status"] == "CLOSURE_OPA_ARCHIVED_OPTIMAL"
    assert empty["is_closure_archival_compliant"] is True

    optimal = audit_project_closure_lessons_learned_and_pir_archival(
        [
            {
                "package_id": "CLS-OPT-1",
                "days_since_handover_to_pir": 25,
                "pir_completed": True,
                "actionable_lessons_documented_count": 5,
                "indexed_in_organizational_process_assets": True,
                "sponsor_final_archival_signed": True,
            }
        ],
        max_days_to_pir_completion=30,
        min_actionable_lessons_count=3,
    )
    assert optimal["evaluated_closure_packages_count"] == 1
    assert optimal["closure_archival_status"] == "CLOSURE_OPA_ARCHIVED_OPTIMAL"
    assert optimal["is_closure_archival_compliant"] is True


def test_audit_project_closure_lessons_learned_and_pir_archival_staticmethod_and_dunder_all():
    import backend.services.project_lifecycle_pmi_service as mod
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_project_closure_lessons_learned_and_pir_archival,
    )

    sample = [
        {
            "package_id": "CLS-99",
            "days_since_handover_to_pir": 12,
            "pir_completed": True,
            "actionable_lessons_documented_count": 3,
            "indexed_in_organizational_process_assets": True,
            "sponsor_final_archival_signed": True,
        }
    ]
    assert (
        ProjectLifecyclePMIService.audit_project_closure_lessons_learned_and_pir_archival(
            sample
        )
        == audit_project_closure_lessons_learned_and_pir_archival(sample)
    )
    assert (
        "audit_project_closure_lessons_learned_and_pir_archival"
        in mod.__all__
    )


def test_audit_organizational_change_adkar_readiness_and_training_breach():
    from backend.services.project_lifecycle_pmi_service import (
        audit_organizational_change_adkar_readiness_and_training,
    )

    result = audit_organizational_change_adkar_readiness_and_training(
        [
            {
                "unit_id": "BU-OPS-1",
                "adkar_average_score": 2.1,
                "training_completion_pct": 95.0,
                "change_champions_assigned": True,
                "hypercare_floor_support_staffed": True,
                "cutover_blocking_resistance_logged": False,
            },
            {
                "unit_id": "BU-FIN-2",
                "adkar_average_score": 4.2,
                "training_completion_pct": 90.0,
                "change_champions_assigned": True,
                "hypercare_floor_support_staffed": False,
                "cutover_blocking_resistance_logged": True,
            },
        ],
        min_adkar_readiness_score=3.5,
        min_training_completion_pct=85.0,
    )
    assert result["evaluated_units_count"] == 2
    assert result["cutover_blocked_or_unstaffed_unit_ids"] == [
        "BU-OPS-1",
        "BU-FIN-2",
    ]
    assert result["low_training_or_readiness_unit_ids"] == ["BU-OPS-1"]
    assert (
        result["ocm_readiness_status"]
        == "OCM_CUTOVER_BLOCKED_OR_HYPERCARE_BREACH"
    )
    assert result["is_ocm_cutover_ready"] is False


def test_audit_organizational_change_adkar_readiness_and_training_warning():
    from backend.services.project_lifecycle_pmi_service import (
        audit_organizational_change_adkar_readiness_and_training,
    )

    result = audit_organizational_change_adkar_readiness_and_training(
        [
            {
                "unit_id": "BU-SALES",
                "adkar_average_score": 3.2,
                "training_completion_pct": 70.0,
                "change_champions_assigned": False,
                "hypercare_floor_support_staffed": True,
                "cutover_blocking_resistance_logged": False,
            }
        ],
        min_adkar_readiness_score=3.5,
        min_training_completion_pct=85.0,
    )
    assert result["evaluated_units_count"] == 1
    assert result["cutover_blocked_or_unstaffed_unit_ids"] == []
    assert result["low_training_or_readiness_unit_ids"] == ["BU-SALES"]
    assert result["ocm_readiness_status"] == "OCM_TRAINING_OR_ADKAR_WARNING"
    assert result["is_ocm_cutover_ready"] is False


def test_audit_organizational_change_adkar_readiness_and_training_optimal_and_empty():
    from backend.services.project_lifecycle_pmi_service import (
        audit_organizational_change_adkar_readiness_and_training,
    )

    empty = audit_organizational_change_adkar_readiness_and_training(
        [{"unit_id": "   "}, "invalid"]  # type: ignore[list-item]
    )
    assert empty["evaluated_units_count"] == 0
    assert empty["ocm_readiness_status"] == "OCM_ADOPTION_READY_OPTIMAL"
    assert empty["is_ocm_cutover_ready"] is True

    optimal = audit_organizational_change_adkar_readiness_and_training(
        [
            {
                "unit_id": "BU-CORE",
                "adkar_average_score": 4.4,
                "training_completion_pct": 92.0,
                "change_champions_assigned": True,
                "hypercare_floor_support_staffed": True,
                "cutover_blocking_resistance_logged": False,
            }
        ],
        min_adkar_readiness_score=3.5,
        min_training_completion_pct=85.0,
    )
    assert optimal["evaluated_units_count"] == 1
    assert optimal["ocm_readiness_status"] == "OCM_ADOPTION_READY_OPTIMAL"
    assert optimal["is_ocm_cutover_ready"] is True


def test_audit_organizational_change_adkar_readiness_and_training_staticmethod_and_dunder_all():
    import backend.services.project_lifecycle_pmi_service as mod
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_organizational_change_adkar_readiness_and_training,
    )

    sample = [
        {
            "unit_id": "BU-99",
            "adkar_average_score": 4.0,
            "training_completion_pct": 90.0,
        }
    ]
    assert (
        ProjectLifecyclePMIService.audit_organizational_change_adkar_readiness_and_training(
            sample
        )
        == audit_organizational_change_adkar_readiness_and_training(sample)
    )
    assert (
        "audit_organizational_change_adkar_readiness_and_training"
        in mod.__all__
    )


def test_audit_ip_escrow_deposit_cadence_and_license_assignment_breach():
    from backend.services.project_lifecycle_pmi_service import (
        audit_ip_escrow_deposit_cadence_and_license_assignment,
    )

    result = audit_ip_escrow_deposit_cadence_and_license_assignment(
        [
            {
                "deliverable_id": "DLV-UNSIGNED-IP",
                "requires_source_code_escrow": True,
                "days_since_last_escrow_deposit": 20,
                "independent_escrow_build_verified": True,
                "ip_assignment_and_patent_waiver_signed": False,
                "copyleft_contamination_detected": False,
            },
            {
                "deliverable_id": "DLV-AGPL-CONTAM",
                "requires_source_code_escrow": True,
                "days_since_last_escrow_deposit": 20,
                "independent_escrow_build_verified": True,
                "ip_assignment_and_patent_waiver_signed": True,
                "copyleft_contamination_detected": True,
            },
        ],
        max_days_since_escrow_deposit=90,
    )
    assert result["evaluated_deliverables_count"] == 2
    assert result["unassigned_ip_or_copyleft_deliverable_ids"] == [
        "DLV-UNSIGNED-IP",
        "DLV-AGPL-CONTAM",
    ]
    assert result["stale_or_unverified_escrow_deliverable_ids"] == []
    assert (
        result["ip_escrow_governance_status"]
        == "IP_ASSIGNMENT_OR_COPYLEFT_BREACH"
    )
    assert result["is_ip_escrow_compliant"] is False


def test_audit_ip_escrow_deposit_cadence_and_license_assignment_warning():
    from backend.services.project_lifecycle_pmi_service import (
        audit_ip_escrow_deposit_cadence_and_license_assignment,
    )

    result = audit_ip_escrow_deposit_cadence_and_license_assignment(
        [
            {
                "deliverable_id": "DLV-STALE-ESCROW",
                "requires_source_code_escrow": True,
                "days_since_last_escrow_deposit": 120,
                "independent_escrow_build_verified": True,
                "ip_assignment_and_patent_waiver_signed": True,
                "copyleft_contamination_detected": False,
            },
            {
                "deliverable_id": "DLV-UNVERIFIED-BUILD",
                "requires_source_code_escrow": True,
                "days_since_last_escrow_deposit": 30,
                "independent_escrow_build_verified": False,
                "ip_assignment_and_patent_waiver_signed": True,
                "copyleft_contamination_detected": False,
            },
            {
                "deliverable_id": "DLV-NO-ESCROW-REQ",
                "requires_source_code_escrow": False,
                "days_since_last_escrow_deposit": 999,
                "independent_escrow_build_verified": False,
                "ip_assignment_and_patent_waiver_signed": True,
                "copyleft_contamination_detected": False,
            },
        ],
        max_days_since_escrow_deposit=90,
    )
    assert result["evaluated_deliverables_count"] == 3
    assert result["unassigned_ip_or_copyleft_deliverable_ids"] == []
    assert result["stale_or_unverified_escrow_deliverable_ids"] == [
        "DLV-STALE-ESCROW",
        "DLV-UNVERIFIED-BUILD",
    ]
    assert (
        result["ip_escrow_governance_status"]
        == "IP_ESCROW_DEPOSIT_OR_BUILD_WARNING"
    )
    assert result["is_ip_escrow_compliant"] is False


def test_audit_ip_escrow_deposit_cadence_and_license_assignment_optimal_and_empty():
    from backend.services.project_lifecycle_pmi_service import (
        audit_ip_escrow_deposit_cadence_and_license_assignment,
    )

    empty = audit_ip_escrow_deposit_cadence_and_license_assignment(
        [{"deliverable_id": "   "}, "invalid"]  # type: ignore[list-item]
    )
    assert empty["evaluated_deliverables_count"] == 0
    assert (
        empty["ip_escrow_governance_status"] == "IP_ESCROW_GOVERNANCE_OPTIMAL"
    )
    assert empty["is_ip_escrow_compliant"] is True

    optimal = audit_ip_escrow_deposit_cadence_and_license_assignment(
        [
            {
                "deliverable_id": "DLV-GOLD-1",
                "requires_source_code_escrow": True,
                "days_since_last_escrow_deposit": 30,
                "independent_escrow_build_verified": True,
                "ip_assignment_and_patent_waiver_signed": True,
                "copyleft_contamination_detected": False,
            }
        ],
        max_days_since_escrow_deposit=90,
    )
    assert optimal["evaluated_deliverables_count"] == 1
    assert (
        optimal["ip_escrow_governance_status"]
        == "IP_ESCROW_GOVERNANCE_OPTIMAL"
    )
    assert optimal["is_ip_escrow_compliant"] is True


def test_audit_ip_escrow_deposit_cadence_and_license_assignment_staticmethod_and_dunder_all():
    import backend.services.project_lifecycle_pmi_service as mod
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_ip_escrow_deposit_cadence_and_license_assignment,
    )

    sample = [
        {
            "deliverable_id": "DLV-99",
            "requires_source_code_escrow": True,
            "days_since_last_escrow_deposit": 45,
        }
    ]
    assert (
        ProjectLifecyclePMIService.audit_ip_escrow_deposit_cadence_and_license_assignment(
            sample
        )
        == audit_ip_escrow_deposit_cadence_and_license_assignment(sample)
    )
    assert (
        "audit_ip_escrow_deposit_cadence_and_license_assignment"
        in mod.__all__
    )



def test_jv_consortium_default_or_step_in_breach():
    from backend.services.project_lifecycle_pmi_service import (
        audit_joint_venture_consortium_solvency_and_step_in_rights,
    )

    res = audit_joint_venture_consortium_solvency_and_step_in_rights(
        [
            {
                "partner_id": "PARTNER-DEFAULT",
                "active_default_or_insolvency_notice": True,
            },
            {
                "partner_id": "PARTNER-NO-LIABILITY",
                "joint_and_several_liability_signed": False,
            },
            {
                "partner_id": "PARTNER-UNENFORCEABLE",
                "step_in_rights_clause_enforceable": False,
            },
        ],
        min_liquidity_current_ratio=1.2,
        max_single_partner_scope_share_pct=65.0,
    )
    assert res["evaluated_partners_count"] == 3
    assert res["default_or_unenforceable_step_in_partner_ids"] == [
        "PARTNER-DEFAULT",
        "PARTNER-NO-LIABILITY",
        "PARTNER-UNENFORCEABLE",
    ]
    assert res["low_liquidity_or_concentration_partner_ids"] == []
    assert (
        res["consortium_governance_status"]
        == "JV_PARTNER_DEFAULT_OR_STEP_IN_BREACH"
    )
    assert res["is_consortium_compliant"] is False


def test_jv_consortium_liquidity_or_concentration_warning():
    from backend.services.project_lifecycle_pmi_service import (
        audit_joint_venture_consortium_solvency_and_step_in_rights,
    )

    res = audit_joint_venture_consortium_solvency_and_step_in_rights(
        [
            {
                "partner_id": "PARTNER-ILLIQUID",
                "liquidity_current_ratio": 0.8,
            },
            {
                "partner_id": "PARTNER-DOMINANT",
                "scope_work_share_pct": 72.0,
            },
        ],
        min_liquidity_current_ratio=1.2,
        max_single_partner_scope_share_pct=65.0,
    )
    assert res["evaluated_partners_count"] == 2
    assert res["default_or_unenforceable_step_in_partner_ids"] == []
    assert res["low_liquidity_or_concentration_partner_ids"] == [
        "PARTNER-ILLIQUID",
        "PARTNER-DOMINANT",
    ]
    assert (
        res["consortium_governance_status"]
        == "JV_LIQUIDITY_OR_CONCENTRATION_WARNING"
    )
    assert res["is_consortium_compliant"] is False


def test_jv_consortium_boundaries_optimal_and_defaults():
    from backend.services.project_lifecycle_pmi_service import (
        audit_joint_venture_consortium_solvency_and_step_in_rights,
    )

    res = audit_joint_venture_consortium_solvency_and_step_in_rights(
        [
            {
                "partner_id": "PARTNER-BOUNDARY",
                "liquidity_current_ratio": 1.2,
                "scope_work_share_pct": 65.0,
            },
            {"partner_id": "PARTNER-ALL-DEFAULTS"},
        ],
        min_liquidity_current_ratio=1.2,
        max_single_partner_scope_share_pct=65.0,
    )
    assert res["evaluated_partners_count"] == 2
    assert res["default_or_unenforceable_step_in_partner_ids"] == []
    assert res["low_liquidity_or_concentration_partner_ids"] == []
    assert (
        res["consortium_governance_status"]
        == "JV_CONSORTIUM_GOVERNANCE_OPTIMAL"
    )
    assert res["is_consortium_compliant"] is True


def test_jv_consortium_invalid_and_binding():
    import backend.services.project_lifecycle_pmi_service as mod
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_joint_venture_consortium_solvency_and_step_in_rights,
    )

    empty = audit_joint_venture_consortium_solvency_and_step_in_rights(None)
    assert empty["evaluated_partners_count"] == 0
    assert empty["default_or_unenforceable_step_in_partner_ids"] == []
    assert empty["low_liquidity_or_concentration_partner_ids"] == []
    assert (
        empty["consortium_governance_status"]
        == "JV_CONSORTIUM_GOVERNANCE_OPTIMAL"
    )
    assert empty["is_consortium_compliant"] is True

    invalid = audit_joint_venture_consortium_solvency_and_step_in_rights(
        [42, "not-a-dict", None, {"partner_id": "   "}]  # type: ignore[list-item]
    )
    assert invalid["evaluated_partners_count"] == 0

    defaults = audit_joint_venture_consortium_solvency_and_step_in_rights(
        [
            {
                "partner_id": "PARTNER-DEFAULTS",
                "scope_work_share_pct": None,
                "liquidity_current_ratio": None,
                "joint_and_several_liability_signed": None,
                "step_in_rights_clause_enforceable": None,
                "active_default_or_insolvency_notice": None,
            }
        ]
    )
    assert defaults["evaluated_partners_count"] == 1
    assert (
        defaults["consortium_governance_status"]
        == "JV_CONSORTIUM_GOVERNANCE_OPTIMAL"
    )
    assert defaults["is_consortium_compliant"] is True

    sample = [
        {
            "partner_id": "PARTNER-1",
            "liquidity_current_ratio": 1.6,
            "scope_work_share_pct": 40.0,
        }
    ]
    assert (
        ProjectLifecyclePMIService.audit_joint_venture_consortium_solvency_and_step_in_rights(
            sample
        )
        == audit_joint_venture_consortium_solvency_and_step_in_rights(sample)
    )
    assert (
        "audit_joint_venture_consortium_solvency_and_step_in_rights"
        in mod.__all__
    )


def test_audit_force_majeure_claim_substantiation_and_mitigation_breach():
    from backend.services.project_lifecycle_pmi_service import (
        audit_force_majeure_claim_substantiation_and_mitigation,
    )

    result = audit_force_majeure_claim_substantiation_and_mitigation(
        [
            {
                "claim_id": "FM-LATE-NOTICE",
                "days_elapsed_before_written_notice": 21,
                "impacts_critical_path_directly": True,
                "contemporaneous_evidence_attached": True,
                "duty_to_mitigate_plan_executed": True,
                "concurrent_contractor_culpable_delay": False,
            },
            {
                "claim_id": "FM-NO-EVIDENCE",
                "days_elapsed_before_written_notice": 5,
                "impacts_critical_path_directly": True,
                "contemporaneous_evidence_attached": False,
                "duty_to_mitigate_plan_executed": True,
                "concurrent_contractor_culpable_delay": False,
            },
            {
                "claim_id": "FM-NO-MITIGATION",
                "days_elapsed_before_written_notice": 5,
                "impacts_critical_path_directly": True,
                "contemporaneous_evidence_attached": True,
                "duty_to_mitigate_plan_executed": False,
                "concurrent_contractor_culpable_delay": False,
            },
        ],
        max_notice_days_after_event=14,
    )
    assert result["evaluated_claims_count"] == 3
    assert result["time_barred_or_unsubstantiated_claim_ids"] == [
        "FM-LATE-NOTICE",
        "FM-NO-EVIDENCE",
        "FM-NO-MITIGATION",
    ]
    assert result["non_critical_or_concurrent_fault_claim_ids"] == []
    assert (
        result["force_majeure_governance_status"]
        == "FORCE_MAJEURE_TIME_BARRED_OR_UNMITIGATED_BREACH"
    )
    assert result["is_force_majeure_claim_compliant"] is False


def test_audit_force_majeure_claim_substantiation_and_mitigation_warning():
    from backend.services.project_lifecycle_pmi_service import (
        audit_force_majeure_claim_substantiation_and_mitigation,
    )

    result = audit_force_majeure_claim_substantiation_and_mitigation(
        [
            {
                "claim_id": "FM-NON-CP",
                "days_elapsed_before_written_notice": 5,
                "impacts_critical_path_directly": False,
                "contemporaneous_evidence_attached": True,
                "duty_to_mitigate_plan_executed": True,
                "concurrent_contractor_culpable_delay": False,
            },
            {
                "claim_id": "FM-CONCURRENT-FAULT",
                "days_elapsed_before_written_notice": 5,
                "impacts_critical_path_directly": True,
                "contemporaneous_evidence_attached": True,
                "duty_to_mitigate_plan_executed": True,
                "concurrent_contractor_culpable_delay": True,
            },
        ],
        max_notice_days_after_event=14,
    )
    assert result["evaluated_claims_count"] == 2
    assert result["time_barred_or_unsubstantiated_claim_ids"] == []
    assert result["non_critical_or_concurrent_fault_claim_ids"] == [
        "FM-NON-CP",
        "FM-CONCURRENT-FAULT",
    ]
    assert (
        result["force_majeure_governance_status"]
        == "FORCE_MAJEURE_CONCURRENT_FAULT_OR_FLOAT_WARNING"
    )
    assert result["is_force_majeure_claim_compliant"] is False


def test_audit_force_majeure_claim_substantiation_and_mitigation_optimal_and_empty():
    from backend.services.project_lifecycle_pmi_service import (
        audit_force_majeure_claim_substantiation_and_mitigation,
    )

    empty = audit_force_majeure_claim_substantiation_and_mitigation(
        [{"claim_id": "   "}, "invalid"]  # type: ignore[list-item]
    )
    assert empty["evaluated_claims_count"] == 0
    assert (
        empty["force_majeure_governance_status"]
        == "FORCE_MAJEURE_CLAIM_VALIDATED_OPTIMAL"
    )
    assert empty["is_force_majeure_claim_compliant"] is True

    optimal = audit_force_majeure_claim_substantiation_and_mitigation(
        [
            {
                "claim_id": "FM-VALID-01",
                "days_elapsed_before_written_notice": 3,
                "impacts_critical_path_directly": True,
                "contemporaneous_evidence_attached": True,
                "duty_to_mitigate_plan_executed": True,
                "concurrent_contractor_culpable_delay": False,
            }
        ],
        max_notice_days_after_event=14,
    )
    assert optimal["evaluated_claims_count"] == 1
    assert (
        optimal["force_majeure_governance_status"]
        == "FORCE_MAJEURE_CLAIM_VALIDATED_OPTIMAL"
    )
    assert optimal["is_force_majeure_claim_compliant"] is True


def test_audit_force_majeure_claim_substantiation_and_mitigation_staticmethod_and_dunder_all():
    import backend.services.project_lifecycle_pmi_service as mod
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_force_majeure_claim_substantiation_and_mitigation,
    )

    sample = [
        {
            "claim_id": "FM-99",
            "days_elapsed_before_written_notice": 4,
            "impacts_critical_path_directly": True,
        }
    ]
    assert (
        ProjectLifecyclePMIService.audit_force_majeure_claim_substantiation_and_mitigation(
            sample
        )
        == audit_force_majeure_claim_substantiation_and_mitigation(sample)
    )
    assert (
        "audit_force_majeure_claim_substantiation_and_mitigation"
        in mod.__all__
    )


def test_audit_adr_dispute_escalation_ladder_and_claim_aging_breach():
    from backend.services.project_lifecycle_pmi_service import (
        audit_adr_dispute_escalation_ladder_and_claim_aging,
    )

    result = audit_adr_dispute_escalation_ladder_and_claim_aging(
        [
            {
                "dispute_id": "DSP-SKIPPED-LADDER",
                "days_in_current_stage": 12,
                "total_dispute_age_days": 25,
                "followed_contractual_escalation_ladder": False,
                "quantum_and_entitlement_substantiated": True,
                "executive_mediation_attempted_before_arbitration": True,
            },
            {
                "dispute_id": "DSP-UNSUBSTANTIATED",
                "days_in_current_stage": 10,
                "total_dispute_age_days": 20,
                "followed_contractual_escalation_ladder": True,
                "quantum_and_entitlement_substantiated": False,
                "executive_mediation_attempted_before_arbitration": True,
            },
            {
                "dispute_id": "DSP-NO-MEDIATION",
                "days_in_current_stage": 15,
                "total_dispute_age_days": 30,
                "followed_contractual_escalation_ladder": True,
                "quantum_and_entitlement_substantiated": True,
                "executive_mediation_attempted_before_arbitration": False,
            },
        ],
        max_negotiation_days_before_mediation=30,
        max_total_dispute_age_days=90,
    )
    assert result["evaluated_disputes_count"] == 3
    assert result["premature_litigation_or_unsubstantiated_dispute_ids"] == [
        "DSP-SKIPPED-LADDER",
        "DSP-UNSUBSTANTIATED",
        "DSP-NO-MEDIATION",
    ]
    assert result["stagnant_negotiation_or_aged_dispute_ids"] == []
    assert (
        result["adr_governance_status"]
        == "ADR_ESCALATION_BYPASS_OR_UNSUBSTANTIATED_BREACH"
    )
    assert result["is_adr_governance_compliant"] is False


def test_audit_adr_dispute_escalation_ladder_and_claim_aging_warning():
    from backend.services.project_lifecycle_pmi_service import (
        audit_adr_dispute_escalation_ladder_and_claim_aging,
    )

    result = audit_adr_dispute_escalation_ladder_and_claim_aging(
        [
            {
                "dispute_id": "DSP-STAGE-STAGNANT",
                "days_in_current_stage": 42,
                "total_dispute_age_days": 60,
                "followed_contractual_escalation_ladder": True,
                "quantum_and_entitlement_substantiated": True,
                "executive_mediation_attempted_before_arbitration": True,
            },
            {
                "dispute_id": "DSP-OVERALL-AGED",
                "days_in_current_stage": 20,
                "total_dispute_age_days": 115,
                "followed_contractual_escalation_ladder": True,
                "quantum_and_entitlement_substantiated": True,
                "executive_mediation_attempted_before_arbitration": True,
            },
        ],
        max_negotiation_days_before_mediation=30,
        max_total_dispute_age_days=90,
    )
    assert result["evaluated_disputes_count"] == 2
    assert result["premature_litigation_or_unsubstantiated_dispute_ids"] == []
    assert result["stagnant_negotiation_or_aged_dispute_ids"] == [
        "DSP-STAGE-STAGNANT",
        "DSP-OVERALL-AGED",
    ]
    assert (
        result["adr_governance_status"] == "ADR_NEGOTIATION_STAGNATION_WARNING"
    )
    assert result["is_adr_governance_compliant"] is False


def test_audit_adr_dispute_escalation_ladder_and_claim_aging_optimal_and_empty():
    from backend.services.project_lifecycle_pmi_service import (
        audit_adr_dispute_escalation_ladder_and_claim_aging,
    )

    empty = audit_adr_dispute_escalation_ladder_and_claim_aging(
        [{"dispute_id": "   "}, "invalid"]  # type: ignore[list-item]
    )
    assert empty["evaluated_disputes_count"] == 0
    assert empty["adr_governance_status"] == "ADR_DISPUTE_RESOLUTION_OPTIMAL"
    assert empty["is_adr_governance_compliant"] is True

    optimal = audit_adr_dispute_escalation_ladder_and_claim_aging(
        [
            {
                "dispute_id": "DSP-CLEAN-01",
                "days_in_current_stage": 14,
                "total_dispute_age_days": 35,
                "followed_contractual_escalation_ladder": True,
                "quantum_and_entitlement_substantiated": True,
                "executive_mediation_attempted_before_arbitration": True,
            }
        ],
        max_negotiation_days_before_mediation=30,
        max_total_dispute_age_days=90,
    )
    assert optimal["evaluated_disputes_count"] == 1
    assert optimal["premature_litigation_or_unsubstantiated_dispute_ids"] == []
    assert optimal["stagnant_negotiation_or_aged_dispute_ids"] == []
    assert optimal["adr_governance_status"] == "ADR_DISPUTE_RESOLUTION_OPTIMAL"
    assert optimal["is_adr_governance_compliant"] is True


def test_audit_adr_dispute_escalation_ladder_and_claim_aging_staticmethod_and_dunder_all():
    import backend.services.project_lifecycle_pmi_service as mod
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_adr_dispute_escalation_ladder_and_claim_aging,
    )

    sample = [
        {
            "dispute_id": "DSP-99",
            "days_in_current_stage": 8,
            "total_dispute_age_days": 15,
        }
    ]
    assert (
        ProjectLifecyclePMIService.audit_adr_dispute_escalation_ladder_and_claim_aging(
            sample
        )
        == audit_adr_dispute_escalation_ladder_and_claim_aging(sample)
    )
    assert (
        "audit_adr_dispute_escalation_ladder_and_claim_aging"
        in mod.__all__
    )


def test_audit_operational_readiness_orat_and_day2_handover_breach():
    from backend.services.project_lifecycle_pmi_service import (
        audit_operational_readiness_orat_and_day2_handover,
    )

    result = audit_operational_readiness_orat_and_day2_handover(
        [
            {
                "gate_id": "ORAT-SEV-DEFECT",
                "orat_scenarios_pass_rate_pct": 99.0,
                "sre_oncall_shadowing_hours_completed": 20.0,
                "day2_monitoring_alerts_verified": True,
                "operations_director_acceptance_signed": True,
                "open_sev1_or_sev2_defects_count": 2,
            },
            {
                "gate_id": "ORAT-UNSIGNED",
                "orat_scenarios_pass_rate_pct": 100.0,
                "sre_oncall_shadowing_hours_completed": 24.0,
                "day2_monitoring_alerts_verified": True,
                "operations_director_acceptance_signed": False,
                "open_sev1_or_sev2_defects_count": 0,
            },
            {
                "gate_id": "ORAT-UNVERIFIED-ALERTS",
                "orat_scenarios_pass_rate_pct": 99.5,
                "sre_oncall_shadowing_hours_completed": 18.0,
                "day2_monitoring_alerts_verified": False,
                "operations_director_acceptance_signed": True,
                "open_sev1_or_sev2_defects_count": 0,
            },
        ],
        min_orat_pass_rate_pct=98.0,
        min_oncall_shadowing_hours=16.0,
    )
    assert result["evaluated_gates_count"] == 3
    assert result["blocked_handover_or_sev_defect_gate_ids"] == [
        "ORAT-SEV-DEFECT",
        "ORAT-UNSIGNED",
        "ORAT-UNVERIFIED-ALERTS",
    ]
    assert result["incomplete_orat_or_shadowing_gate_ids"] == []
    assert (
        result["orat_handover_status"]
        == "ORAT_SEV_DEFECT_OR_UNSIGNED_HANDOVER_BREACH"
    )
    assert result["is_orat_handover_ready"] is False


def test_audit_operational_readiness_orat_and_day2_handover_warning():
    from backend.services.project_lifecycle_pmi_service import (
        audit_operational_readiness_orat_and_day2_handover,
    )

    result = audit_operational_readiness_orat_and_day2_handover(
        [
            {
                "gate_id": "ORAT-LOW-PASS",
                "orat_scenarios_pass_rate_pct": 94.5,
                "sre_oncall_shadowing_hours_completed": 20.0,
                "day2_monitoring_alerts_verified": True,
                "operations_director_acceptance_signed": True,
                "open_sev1_or_sev2_defects_count": 0,
            },
            {
                "gate_id": "ORAT-LOW-SHADOWING",
                "orat_scenarios_pass_rate_pct": 99.0,
                "sre_oncall_shadowing_hours_completed": 8.0,
                "day2_monitoring_alerts_verified": True,
                "operations_director_acceptance_signed": True,
                "open_sev1_or_sev2_defects_count": 0,
            },
        ],
        min_orat_pass_rate_pct=98.0,
        min_oncall_shadowing_hours=16.0,
    )
    assert result["evaluated_gates_count"] == 2
    assert result["blocked_handover_or_sev_defect_gate_ids"] == []
    assert result["incomplete_orat_or_shadowing_gate_ids"] == [
        "ORAT-LOW-PASS",
        "ORAT-LOW-SHADOWING",
    ]
    assert (
        result["orat_handover_status"] == "ORAT_PASS_RATE_OR_SHADOWING_WARNING"
    )
    assert result["is_orat_handover_ready"] is False


def test_audit_operational_readiness_orat_and_day2_handover_optimal_and_empty():
    from backend.services.project_lifecycle_pmi_service import (
        audit_operational_readiness_orat_and_day2_handover,
    )

    empty = audit_operational_readiness_orat_and_day2_handover(
        [{"gate_id": "   "}, "invalid"]  # type: ignore[list-item]
    )
    assert empty["evaluated_gates_count"] == 0
    assert (
        empty["orat_handover_status"] == "ORAT_DAY2_HANDOVER_READY_OPTIMAL"
    )
    assert empty["is_orat_handover_ready"] is True

    optimal = audit_operational_readiness_orat_and_day2_handover(
        [
            {
                "gate_id": "ORAT-READY-01",
                "orat_scenarios_pass_rate_pct": 99.2,
                "sre_oncall_shadowing_hours_completed": 24.0,
                "day2_monitoring_alerts_verified": True,
                "operations_director_acceptance_signed": True,
                "open_sev1_or_sev2_defects_count": 0,
            }
        ],
        min_orat_pass_rate_pct=98.0,
        min_oncall_shadowing_hours=16.0,
    )
    assert optimal["evaluated_gates_count"] == 1
    assert optimal["blocked_handover_or_sev_defect_gate_ids"] == []
    assert optimal["incomplete_orat_or_shadowing_gate_ids"] == []
    assert (
        optimal["orat_handover_status"] == "ORAT_DAY2_HANDOVER_READY_OPTIMAL"
    )
    assert optimal["is_orat_handover_ready"] is True


def test_audit_operational_readiness_orat_and_day2_handover_staticmethod_and_dunder_all():
    import backend.services.project_lifecycle_pmi_service as mod
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_operational_readiness_orat_and_day2_handover,
    )

    sample = [
        {
            "gate_id": "ORAT-99",
            "orat_scenarios_pass_rate_pct": 100.0,
            "sre_oncall_shadowing_hours_completed": 20.0,
        }
    ]
    assert (
        ProjectLifecyclePMIService.audit_operational_readiness_orat_and_day2_handover(
            sample
        )
        == audit_operational_readiness_orat_and_day2_handover(sample)
    )
    assert (
        "audit_operational_readiness_orat_and_day2_handover"
        in mod.__all__
    )


def test_audit_steering_committee_quorum_and_decision_velocity_breach():
    from backend.services.project_lifecycle_pmi_service import (
        audit_steering_committee_quorum_and_decision_velocity,
    )

    result = audit_steering_committee_quorum_and_decision_velocity(
        [
            {
                "meeting_id": "MTG-LOW-QUORUM",
                "voting_quorum_pct": 60.0,
                "minutes_signed_and_published": True,
                "max_overdue_action_days": 0,
                "deferred_critical_decisions_count": 0,
            },
            {
                "meeting_id": "MTG-UNSIGNED-MINUTES",
                "voting_quorum_pct": 90.0,
                "minutes_signed_and_published": False,
                "max_overdue_action_days": 0,
                "deferred_critical_decisions_count": 0,
            },
        ],
        min_voting_quorum_pct=75.0,
        max_action_item_overdue_days=14,
    )
    assert result["evaluated_meetings_count"] == 2
    assert result["quorum_or_unsigned_minutes_meeting_ids"] == [
        "MTG-LOW-QUORUM",
        "MTG-UNSIGNED-MINUTES",
    ]
    assert result["stale_action_or_deferred_decision_meeting_ids"] == []
    assert (
        result["steering_governance_status"]
        == "STEERING_QUORUM_OR_MINUTES_BREACH"
    )
    assert result["is_steering_governance_compliant"] is False


def test_audit_steering_committee_quorum_and_decision_velocity_warning():
    from backend.services.project_lifecycle_pmi_service import (
        audit_steering_committee_quorum_and_decision_velocity,
    )

    result = audit_steering_committee_quorum_and_decision_velocity(
        [
            {
                "meeting_id": "MTG-STALE-ACTIONS",
                "voting_quorum_pct": 85.0,
                "minutes_signed_and_published": True,
                "max_overdue_action_days": 22,
                "deferred_critical_decisions_count": 0,
            },
            {
                "meeting_id": "MTG-DEFERRED-DECISION",
                "voting_quorum_pct": 88.0,
                "minutes_signed_and_published": True,
                "max_overdue_action_days": 4,
                "deferred_critical_decisions_count": 2,
            },
        ],
        min_voting_quorum_pct=75.0,
        max_action_item_overdue_days=14,
    )
    assert result["evaluated_meetings_count"] == 2
    assert result["quorum_or_unsigned_minutes_meeting_ids"] == []
    assert result["stale_action_or_deferred_decision_meeting_ids"] == [
        "MTG-STALE-ACTIONS",
        "MTG-DEFERRED-DECISION",
    ]
    assert (
        result["steering_governance_status"]
        == "STEERING_DECISION_VELOCITY_WARNING"
    )
    assert result["is_steering_governance_compliant"] is False


def test_audit_steering_committee_quorum_and_decision_velocity_optimal_and_empty():
    from backend.services.project_lifecycle_pmi_service import (
        audit_steering_committee_quorum_and_decision_velocity,
    )

    empty = audit_steering_committee_quorum_and_decision_velocity(
        [{"meeting_id": "   "}, "invalid"]  # type: ignore[list-item]
    )
    assert empty["evaluated_meetings_count"] == 0
    assert (
        empty["steering_governance_status"] == "STEERING_GOVERNANCE_OPTIMAL"
    )
    assert empty["is_steering_governance_compliant"] is True

    optimal = audit_steering_committee_quorum_and_decision_velocity(
        [
            {
                "meeting_id": "MTG-STEER-Q3",
                "voting_quorum_pct": 95.0,
                "minutes_signed_and_published": True,
                "max_overdue_action_days": 3,
                "deferred_critical_decisions_count": 0,
            }
        ],
        min_voting_quorum_pct=75.0,
        max_action_item_overdue_days=14,
    )
    assert optimal["evaluated_meetings_count"] == 1
    assert optimal["quorum_or_unsigned_minutes_meeting_ids"] == []
    assert optimal["stale_action_or_deferred_decision_meeting_ids"] == []
    assert (
        optimal["steering_governance_status"] == "STEERING_GOVERNANCE_OPTIMAL"
    )
    assert optimal["is_steering_governance_compliant"] is True


def test_audit_steering_committee_quorum_and_decision_velocity_staticmethod_and_dunder_all():
    import backend.services.project_lifecycle_pmi_service as mod
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_steering_committee_quorum_and_decision_velocity,
    )

    sample = [
        {
            "meeting_id": "MTG-99",
            "voting_quorum_pct": 100.0,
        }
    ]
    assert (
        ProjectLifecyclePMIService.audit_steering_committee_quorum_and_decision_velocity(
            sample
        )
        == audit_steering_committee_quorum_and_decision_velocity(sample)
    )
    assert (
        "audit_steering_committee_quorum_and_decision_velocity"
        in mod.__all__
    )


def test_audit_procurement_bid_integrity_and_coi_recusal_breach():
    from backend.services.project_lifecycle_pmi_service import (
        audit_procurement_bid_integrity_and_coi_recusal,
    )

    res = audit_procurement_bid_integrity_and_coi_recusal(
        [
            {
                "tender_id": "  RFP-01  ",
                "sealed_bid_opening_verified": False,
                "coi_declarations_and_recusals_complete": True,
                "qualified_bidders_count": 4,
                "sole_source_justification_approved": False,
                "winning_bid_igce_variance_pct": 5.0,
            },
            {
                "tender_id": "RFP-02",
                "sealed_bid_opening_verified": True,
                "coi_declarations_and_recusals_complete": False,
                "qualified_bidders_count": 2,
                "sole_source_justification_approved": False,
                "winning_bid_igce_variance_pct": -25.0,
            },
            {
                "tender_id": "RFP-03",
                "sealed_bid_opening_verified": True,
                "coi_declarations_and_recusals_complete": True,
                "qualified_bidders_count": 3,
                "sole_source_justification_approved": False,
                "winning_bid_igce_variance_pct": 20.0,
            },
        ]
    )
    assert res["evaluated_tenders_count"] == 3
    assert res["compromised_seal_or_coi_tender_ids"] == ["RFP-01", "RFP-02"]
    assert res["low_competition_or_igce_variance_tender_ids"] == ["RFP-02"]
    assert (
        res["procurement_integrity_status"]
        == "PROCUREMENT_BID_SEAL_OR_COI_BREACH"
    )
    assert res["is_procurement_integrity_compliant"] is False


def test_audit_procurement_bid_integrity_and_coi_recusal_warning():
    from backend.services.project_lifecycle_pmi_service import (
        audit_procurement_bid_integrity_and_coi_recusal,
    )

    res = audit_procurement_bid_integrity_and_coi_recusal(
        [
            {
                "tender_id": "RFP-LOW-COMP",
                "sealed_bid_opening_verified": True,
                "coi_declarations_and_recusals_complete": True,
                "qualified_bidders_count": 2,
                "sole_source_justification_approved": False,
                "winning_bid_igce_variance_pct": 10.0,
            },
            {
                "tender_id": "RFP-IGCE-SKEW",
                "sealed_bid_opening_verified": True,
                "coi_declarations_and_recusals_complete": True,
                "qualified_bidders_count": 1,
                "sole_source_justification_approved": True,
                "winning_bid_igce_variance_pct": -20.1,
            },
            {
                "tender_id": "RFP-SOLE-APPROVED",
                "sealed_bid_opening_verified": True,
                "coi_declarations_and_recusals_complete": True,
                "qualified_bidders_count": 1,
                "sole_source_justification_approved": True,
                "winning_bid_igce_variance_pct": -20.0,
            },
        ],
        min_qualified_bidders=3,
        max_winning_bid_variance_from_igce_pct=20.0,
    )
    assert res["evaluated_tenders_count"] == 3
    assert res["compromised_seal_or_coi_tender_ids"] == []
    assert res["low_competition_or_igce_variance_tender_ids"] == [
        "RFP-LOW-COMP",
        "RFP-IGCE-SKEW",
    ]
    assert (
        res["procurement_integrity_status"]
        == "PROCUREMENT_COMPETITION_OR_IGCE_WARNING"
    )
    assert res["is_procurement_integrity_compliant"] is False


def test_audit_procurement_bid_integrity_and_coi_recusal_optimal_and_defensive():
    from backend.services.project_lifecycle_pmi_service import (
        audit_procurement_bid_integrity_and_coi_recusal,
    )

    empty = audit_procurement_bid_integrity_and_coi_recusal(None)
    assert empty["evaluated_tenders_count"] == 0
    assert empty["compromised_seal_or_coi_tender_ids"] == []
    assert empty["low_competition_or_igce_variance_tender_ids"] == []
    assert (
        empty["procurement_integrity_status"]
        == "PROCUREMENT_BID_INTEGRITY_OPTIMAL"
    )
    assert empty["is_procurement_integrity_compliant"] is True

    optimal = audit_procurement_bid_integrity_and_coi_recusal(
        [
            "not-a-dict",  # type: ignore[list-item]
            {"tender_id": "   "},
            {
                "tender_id": "RFP-DEFAULTS",
                "sealed_bid_opening_verified": None,
                "coi_declarations_and_recusals_complete": None,
                "qualified_bidders_count": None,
                "sole_source_justification_approved": None,
                "winning_bid_igce_variance_pct": None,
            },
        ]
    )
    assert optimal["evaluated_tenders_count"] == 1
    assert optimal["compromised_seal_or_coi_tender_ids"] == []
    assert optimal["low_competition_or_igce_variance_tender_ids"] == []
    assert (
        optimal["procurement_integrity_status"]
        == "PROCUREMENT_BID_INTEGRITY_OPTIMAL"
    )
    assert optimal["is_procurement_integrity_compliant"] is True


def test_audit_procurement_bid_integrity_and_coi_recusal_staticmethod_and_dunder_all():
    import backend.services.project_lifecycle_pmi_service as mod
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_procurement_bid_integrity_and_coi_recusal,
    )

    sample = [
        {
            "tender_id": "RFP-99",
            "qualified_bidders_count": 4,
            "winning_bid_igce_variance_pct": 4.5,
        }
    ]
    assert (
        ProjectLifecyclePMIService.audit_procurement_bid_integrity_and_coi_recusal(
            sample
        )
        == audit_procurement_bid_integrity_and_coi_recusal(sample)
    )
    assert "audit_procurement_bid_integrity_and_coi_recusal" in mod.__all__


def test_audit_warranty_latent_defect_and_retention_bond_release_breach():
    from backend.services.project_lifecycle_pmi_service import (
        audit_warranty_latent_defect_and_retention_bond_release,
    )

    res = audit_warranty_latent_defect_and_retention_bond_release(
        [
            {
                "contract_id": "  CNT-UNINSURED  ",
                "open_punchlist_items_count": 0,
                "performance_bond_released_prematurely": False,
                "latent_defect_liability_insured": False,
                "max_defect_remediation_days": 5,
            },
            {
                "contract_id": "CNT-PREMATURE-BOND",
                "open_punchlist_items_count": 0,
                "performance_bond_released_prematurely": True,
                "latent_defect_liability_insured": True,
                "max_defect_remediation_days": 20,
            },
            {
                "contract_id": "CNT-HOLDBACK-RELEASED",
                "open_punchlist_items_count": 2,
                "performance_bond_released_prematurely": False,
                "latent_defect_liability_insured": True,
                "max_defect_remediation_days": 5,
                "retention_holdback_released": True,
            },
            {
                "contract_id": "CNT-CLEAN",
                "open_punchlist_items_count": 0,
                "performance_bond_released_prematurely": False,
                "latent_defect_liability_insured": True,
                "max_defect_remediation_days": 15,
            },
        ]
    )
    assert res["evaluated_contracts_count"] == 4
    assert res["premature_bond_or_uninsured_latent_contract_ids"] == [
        "CNT-UNINSURED",
        "CNT-PREMATURE-BOND",
        "CNT-HOLDBACK-RELEASED",
    ]
    assert res["slow_remediation_or_open_punchlist_contract_ids"] == [
        "CNT-PREMATURE-BOND",
        "CNT-HOLDBACK-RELEASED",
    ]
    assert (
        res["warranty_retention_status"]
        == "WARRANTY_BOND_RELEASE_OR_LATENT_INSURANCE_BREACH"
    )
    assert res["is_warranty_retention_compliant"] is False


def test_audit_warranty_latent_defect_and_retention_bond_release_warning():
    from backend.services.project_lifecycle_pmi_service import (
        audit_warranty_latent_defect_and_retention_bond_release,
    )

    res = audit_warranty_latent_defect_and_retention_bond_release(
        [
            {
                "contract_id": "CNT-SLOW-REMED",
                "open_punchlist_items_count": 0,
                "performance_bond_released_prematurely": False,
                "latent_defect_liability_insured": True,
                "max_defect_remediation_days": 16,
            },
            {
                "contract_id": "CNT-OPEN-PUNCH",
                "open_punchlist_items_count": 1,
                "performance_bond_released_prematurely": False,
                "latent_defect_liability_insured": True,
                "max_defect_remediation_days": 15,
                "retention_holdback_released": False,
            },
        ],
        max_latent_defect_remediation_days=15,
        require_punchlist_zero_before_bond_release=True,
    )
    assert res["evaluated_contracts_count"] == 2
    assert res["premature_bond_or_uninsured_latent_contract_ids"] == []
    assert res["slow_remediation_or_open_punchlist_contract_ids"] == [
        "CNT-SLOW-REMED",
        "CNT-OPEN-PUNCH",
    ]
    assert (
        res["warranty_retention_status"]
        == "WARRANTY_REMEDIATION_SLA_OR_PUNCHLIST_WARNING"
    )
    assert res["is_warranty_retention_compliant"] is False


def test_audit_warranty_latent_defect_and_retention_bond_release_optimal_and_defensive():
    from backend.services.project_lifecycle_pmi_service import (
        audit_warranty_latent_defect_and_retention_bond_release,
    )

    empty = audit_warranty_latent_defect_and_retention_bond_release(None)
    assert empty["evaluated_contracts_count"] == 0
    assert empty["premature_bond_or_uninsured_latent_contract_ids"] == []
    assert empty["slow_remediation_or_open_punchlist_contract_ids"] == []
    assert (
        empty["warranty_retention_status"]
        == "WARRANTY_AND_RETENTION_RELEASE_OPTIMAL"
    )
    assert empty["is_warranty_retention_compliant"] is True

    optimal = audit_warranty_latent_defect_and_retention_bond_release(
        [
            "not-a-dict",  # type: ignore[list-item]
            {"contract_id": "   "},
            {
                "contract_id": "CNT-DEFAULTS",
                "open_punchlist_items_count": None,
                "performance_bond_released_prematurely": None,
                "latent_defect_liability_insured": None,
                "max_defect_remediation_days": None,
            },
        ]
    )
    assert optimal["evaluated_contracts_count"] == 1
    assert optimal["premature_bond_or_uninsured_latent_contract_ids"] == []
    assert optimal["slow_remediation_or_open_punchlist_contract_ids"] == []
    assert (
        optimal["warranty_retention_status"]
        == "WARRANTY_AND_RETENTION_RELEASE_OPTIMAL"
    )
    assert optimal["is_warranty_retention_compliant"] is True


def test_audit_warranty_latent_defect_and_retention_bond_release_staticmethod_and_dunder_all():
    import backend.services.project_lifecycle_pmi_service as mod
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_warranty_latent_defect_and_retention_bond_release,
    )

    sample = [
        {
            "contract_id": "CNT-99",
            "open_punchlist_items_count": 0,
            "max_defect_remediation_days": 7,
        }
    ]
    assert (
        ProjectLifecyclePMIService.audit_warranty_latent_defect_and_retention_bond_release(
            sample
        )
        == audit_warranty_latent_defect_and_retention_bond_release(sample)
    )
    assert (
        "audit_warranty_latent_defect_and_retention_bond_release"
        in mod.__all__
    )


def test_audit_regulatory_permit_renewal_and_stop_work_compliance_breach():
    from backend.services.project_lifecycle_pmi_service import (
        audit_regulatory_permit_renewal_and_stop_work_compliance,
    )

    res = audit_regulatory_permit_renewal_and_stop_work_compliance(
        [
            {
                "permit_id": "  PRM-EXPIRED  ",
                "days_until_expiration": 0,
                "renewal_application_submitted": True,
                "stop_work_order_active": False,
                "open_minor_citations_count": 0,
            },
            {
                "permit_id": "PRM-STOP-WORK",
                "days_until_expiration": 90,
                "renewal_application_submitted": True,
                "stop_work_order_active": True,
                "open_minor_citations_count": 4,
            },
            {
                "permit_id": "PRM-CLEAN",
                "days_until_expiration": 45,
                "renewal_application_submitted": False,
                "stop_work_order_active": False,
                "open_minor_citations_count": 2,
            },
        ]
    )
    assert res["evaluated_permits_count"] == 3
    assert res["expired_or_stop_work_permit_ids"] == [
        "PRM-EXPIRED",
        "PRM-STOP-WORK",
    ]
    assert res["renewal_window_or_citation_permit_ids"] == ["PRM-STOP-WORK"]
    assert (
        res["regulatory_permit_status"]
        == "PERMIT_EXPIRATION_OR_STOP_WORK_BREACH"
    )
    assert res["is_regulatory_permit_compliant"] is False


def test_audit_regulatory_permit_renewal_and_stop_work_compliance_warning():
    from backend.services.project_lifecycle_pmi_service import (
        audit_regulatory_permit_renewal_and_stop_work_compliance,
    )

    res = audit_regulatory_permit_renewal_and_stop_work_compliance(
        [
            {
                "permit_id": "PRM-UNRENEWED-WINDOW",
                "days_until_expiration": 44,
                "renewal_application_submitted": False,
                "stop_work_order_active": False,
                "open_minor_citations_count": 2,
            },
            {
                "permit_id": "PRM-CITATIONS",
                "days_until_expiration": 100,
                "renewal_application_submitted": True,
                "stop_work_order_active": False,
                "open_minor_citations_count": 3,
            },
            {
                "permit_id": "PRM-RENEWED-IN-WINDOW",
                "days_until_expiration": 10,
                "renewal_application_submitted": True,
                "stop_work_order_active": False,
                "open_minor_citations_count": 2,
            },
        ],
        min_renewal_lead_time_days=45,
        max_open_minor_citations=2,
    )
    assert res["evaluated_permits_count"] == 3
    assert res["expired_or_stop_work_permit_ids"] == []
    assert res["renewal_window_or_citation_permit_ids"] == [
        "PRM-UNRENEWED-WINDOW",
        "PRM-CITATIONS",
    ]
    assert (
        res["regulatory_permit_status"]
        == "PERMIT_RENEWAL_LEAD_TIME_OR_CITATION_WARNING"
    )
    assert res["is_regulatory_permit_compliant"] is False


def test_audit_regulatory_permit_renewal_and_stop_work_compliance_optimal_and_defensive():
    from backend.services.project_lifecycle_pmi_service import (
        audit_regulatory_permit_renewal_and_stop_work_compliance,
    )

    empty = audit_regulatory_permit_renewal_and_stop_work_compliance(None)
    assert empty["evaluated_permits_count"] == 0
    assert empty["expired_or_stop_work_permit_ids"] == []
    assert empty["renewal_window_or_citation_permit_ids"] == []
    assert (
        empty["regulatory_permit_status"]
        == "PERMIT_REGULATORY_COMPLIANCE_OPTIMAL"
    )
    assert empty["is_regulatory_permit_compliant"] is True

    optimal = audit_regulatory_permit_renewal_and_stop_work_compliance(
        [
            "not-a-dict",  # type: ignore[list-item]
            {"permit_id": "   "},
            {
                "permit_id": "PRM-DEFAULTS",
                "days_until_expiration": None,
                "renewal_application_submitted": None,
                "stop_work_order_active": None,
                "open_minor_citations_count": None,
            },
        ]
    )
    assert optimal["evaluated_permits_count"] == 1
    assert optimal["expired_or_stop_work_permit_ids"] == []
    assert optimal["renewal_window_or_citation_permit_ids"] == []
    assert (
        optimal["regulatory_permit_status"]
        == "PERMIT_REGULATORY_COMPLIANCE_OPTIMAL"
    )
    assert optimal["is_regulatory_permit_compliant"] is True


def test_audit_regulatory_permit_renewal_and_stop_work_compliance_staticmethod_and_dunder_all():
    import backend.services.project_lifecycle_pmi_service as mod
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_regulatory_permit_renewal_and_stop_work_compliance,
    )

    sample = [
        {
            "permit_id": "PRM-99",
            "days_until_expiration": 180,
            "open_minor_citations_count": 0,
        }
    ]
    assert (
        ProjectLifecyclePMIService.audit_regulatory_permit_renewal_and_stop_work_compliance(
            sample
        )
        == audit_regulatory_permit_renewal_and_stop_work_compliance(sample)
    )
    assert (
        "audit_regulatory_permit_renewal_and_stop_work_compliance"
        in mod.__all__
    )






def test_demob_hazmat_or_sanitization_breach():
    from backend.services.project_lifecycle_pmi_service import (
        audit_site_demobilization_environmental_clearance_and_asset_disposal,
    )

    res = audit_site_demobilization_environmental_clearance_and_asset_disposal(
        [
            {
                "site_id": "SITE-NO-HAZMAT",
                "environmental_hazmat_clearance_signed": False,
            },
            {
                "site_id": "SITE-UNSANITIZED",
                "it_assets_nist_800_88_sanitized": False,
            },
        ],
        max_demobilization_overrun_days=10,
        require_hazmat_clearance_and_data_wipe=True,
    )
    assert res["evaluated_sites_count"] == 2
    assert res["uncleared_hazmat_or_unsanitized_asset_site_ids"] == [
        "SITE-NO-HAZMAT",
        "SITE-UNSANITIZED",
    ]
    assert res["delayed_demob_or_unreconciled_surplus_site_ids"] == []
    assert (
        res["demobilization_status"]
        == "DEMOB_HAZMAT_CLEARANCE_OR_DATA_SANITIZATION_BREACH"
    )
    assert res["is_demobilization_compliant"] is False

    optional = audit_site_demobilization_environmental_clearance_and_asset_disposal(
        [
            {
                "site_id": "SITE-FLAG-OFF",
                "environmental_hazmat_clearance_signed": False,
                "it_assets_nist_800_88_sanitized": False,
            }
        ],
        max_demobilization_overrun_days=10,
        require_hazmat_clearance_and_data_wipe=False,
    )
    assert optional["uncleared_hazmat_or_unsanitized_asset_site_ids"] == []


def test_demob_schedule_or_surplus_inventory_warning():
    from backend.services.project_lifecycle_pmi_service import (
        audit_site_demobilization_environmental_clearance_and_asset_disposal,
    )

    res = audit_site_demobilization_environmental_clearance_and_asset_disposal(
        [
            {
                "site_id": "SITE-OVERRUN",
                "demobilization_overrun_days": 14,
            },
            {
                "site_id": "SITE-UNRECONCILED",
                "surplus_inventory_reconciled": False,
            },
        ],
        max_demobilization_overrun_days=10,
        require_hazmat_clearance_and_data_wipe=True,
    )
    assert res["evaluated_sites_count"] == 2
    assert res["uncleared_hazmat_or_unsanitized_asset_site_ids"] == []
    assert res["delayed_demob_or_unreconciled_surplus_site_ids"] == [
        "SITE-OVERRUN",
        "SITE-UNRECONCILED",
    ]
    assert (
        res["demobilization_status"]
        == "DEMOB_SCHEDULE_OR_SURPLUS_INVENTORY_WARNING"
    )
    assert res["is_demobilization_compliant"] is False


def test_demob_boundaries_optimal_and_defaults():
    from backend.services.project_lifecycle_pmi_service import (
        audit_site_demobilization_environmental_clearance_and_asset_disposal,
    )

    res = audit_site_demobilization_environmental_clearance_and_asset_disposal(
        [
            {
                "site_id": "SITE-BOUNDARY",
                "demobilization_overrun_days": 10,
            },
            {"site_id": "SITE-ALL-DEFAULTS"},
        ],
        max_demobilization_overrun_days=10,
        require_hazmat_clearance_and_data_wipe=True,
    )
    assert res["evaluated_sites_count"] == 2
    assert res["uncleared_hazmat_or_unsanitized_asset_site_ids"] == []
    assert res["delayed_demob_or_unreconciled_surplus_site_ids"] == []
    assert (
        res["demobilization_status"] == "DEMOB_AND_ASSET_DISPOSAL_OPTIMAL"
    )
    assert res["is_demobilization_compliant"] is True


def test_demob_invalid_and_binding():
    import backend.services.project_lifecycle_pmi_service as mod
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_site_demobilization_environmental_clearance_and_asset_disposal,
    )

    empty = audit_site_demobilization_environmental_clearance_and_asset_disposal(
        None
    )
    assert empty["evaluated_sites_count"] == 0
    assert empty["uncleared_hazmat_or_unsanitized_asset_site_ids"] == []
    assert empty["delayed_demob_or_unreconciled_surplus_site_ids"] == []
    assert (
        empty["demobilization_status"] == "DEMOB_AND_ASSET_DISPOSAL_OPTIMAL"
    )
    assert empty["is_demobilization_compliant"] is True

    invalid = audit_site_demobilization_environmental_clearance_and_asset_disposal(
        [42, "not-a-dict", None, {"site_id": "   "}]  # type: ignore[list-item]
    )
    assert invalid["evaluated_sites_count"] == 0

    defaults = audit_site_demobilization_environmental_clearance_and_asset_disposal(
        [
            {
                "site_id": "SITE-DEFAULTS",
                "environmental_hazmat_clearance_signed": None,
                "it_assets_nist_800_88_sanitized": None,
                "demobilization_overrun_days": None,
                "surplus_inventory_reconciled": None,
            }
        ]
    )
    assert defaults["evaluated_sites_count"] == 1
    assert (
        defaults["demobilization_status"]
        == "DEMOB_AND_ASSET_DISPOSAL_OPTIMAL"
    )
    assert defaults["is_demobilization_compliant"] is True

    sample = [
        {
            "site_id": "SITE-1",
            "demobilization_overrun_days": 2,
        }
    ]
    assert (
        ProjectLifecyclePMIService.audit_site_demobilization_environmental_clearance_and_asset_disposal(
            sample
        )
        == audit_site_demobilization_environmental_clearance_and_asset_disposal(
            sample
        )
    )
    assert (
        "audit_site_demobilization_environmental_clearance_and_asset_disposal"
        in mod.__all__
    )


def test_audit_team_burnout_overtime_and_bus_factor_redundancy_breach():
    from backend.services.project_lifecycle_pmi_service import (
        audit_team_burnout_overtime_and_bus_factor_redundancy,
    )

    res = audit_team_burnout_overtime_and_bus_factor_redundancy(
        [
            {
                "squad_id": "  SQD-SPOF  ",
                "bus_factor_qualified_owners": 1,
                "retaliation_free_incident_culture_verified": True,
                "sustained_overtime_pct": 5.0,
                "unplanned_attrition_last_quarter_count": 0,
            },
            {
                "squad_id": "SQD-TOXIC",
                "bus_factor_qualified_owners": 3,
                "retaliation_free_incident_culture_verified": False,
                "sustained_overtime_pct": 22.0,
                "unplanned_attrition_last_quarter_count": 2,
            },
            {
                "squad_id": "SQD-CLEAN",
                "bus_factor_qualified_owners": 2,
                "retaliation_free_incident_culture_verified": True,
                "sustained_overtime_pct": 15.0,
                "unplanned_attrition_last_quarter_count": 0,
            },
        ]
    )
    assert res["evaluated_squads_count"] == 3
    assert res["single_point_bus_factor_or_toxic_culture_squad_ids"] == [
        "SQD-SPOF",
        "SQD-TOXIC",
    ]
    assert res["high_overtime_or_attrition_squad_ids"] == ["SQD-TOXIC"]
    assert (
        res["team_sustainability_status"] == "TEAM_BUS_FACTOR_OR_SAFETY_BREACH"
    )
    assert res["is_team_sustainability_compliant"] is False


def test_audit_team_burnout_overtime_and_bus_factor_redundancy_warning():
    from backend.services.project_lifecycle_pmi_service import (
        audit_team_burnout_overtime_and_bus_factor_redundancy,
    )

    res = audit_team_burnout_overtime_and_bus_factor_redundancy(
        [
            {
                "squad_id": "SQD-OVERTIME",
                "bus_factor_qualified_owners": 2,
                "retaliation_free_incident_culture_verified": True,
                "sustained_overtime_pct": 15.1,
                "unplanned_attrition_last_quarter_count": 0,
            },
            {
                "squad_id": "SQD-ATTRITION",
                "bus_factor_qualified_owners": 2,
                "retaliation_free_incident_culture_verified": True,
                "sustained_overtime_pct": 15.0,
                "unplanned_attrition_last_quarter_count": 1,
            },
        ],
        max_sustained_overtime_pct=15.0,
        min_bus_factor_owners=2,
    )
    assert res["evaluated_squads_count"] == 2
    assert res["single_point_bus_factor_or_toxic_culture_squad_ids"] == []
    assert res["high_overtime_or_attrition_squad_ids"] == [
        "SQD-OVERTIME",
        "SQD-ATTRITION",
    ]
    assert (
        res["team_sustainability_status"]
        == "TEAM_OVERTIME_OR_ATTRITION_WARNING"
    )
    assert res["is_team_sustainability_compliant"] is False


def test_audit_team_burnout_overtime_and_bus_factor_redundancy_optimal_and_defensive():
    from backend.services.project_lifecycle_pmi_service import (
        audit_team_burnout_overtime_and_bus_factor_redundancy,
    )

    empty = audit_team_burnout_overtime_and_bus_factor_redundancy(None)
    assert empty["evaluated_squads_count"] == 0
    assert (
        empty["team_sustainability_status"]
        == "TEAM_SUSTAINABILITY_AND_REDUNDANCY_OPTIMAL"
    )
    assert empty["is_team_sustainability_compliant"] is True

    defaults = audit_team_burnout_overtime_and_bus_factor_redundancy(
        [
            "not-a-dict",  # type: ignore[list-item]
            {"squad_id": "   "},
            {
                "squad_id": "SQD-DEFAULTS",
                "bus_factor_qualified_owners": None,
                "retaliation_free_incident_culture_verified": None,
                "sustained_overtime_pct": None,
                "unplanned_attrition_last_quarter_count": None,
            },
        ]
    )
    assert defaults["evaluated_squads_count"] == 1
    assert (
        defaults["team_sustainability_status"]
        == "TEAM_SUSTAINABILITY_AND_REDUNDANCY_OPTIMAL"
    )
    assert defaults["is_team_sustainability_compliant"] is True


def test_audit_team_burnout_overtime_and_bus_factor_redundancy_staticmethod_and_dunder_all():
    import backend.services.project_lifecycle_pmi_service as mod
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_team_burnout_overtime_and_bus_factor_redundancy,
    )

    sample = [{"squad_id": "SQD-99", "sustained_overtime_pct": 4.0}]
    assert (
        ProjectLifecyclePMIService.audit_team_burnout_overtime_and_bus_factor_redundancy(
            sample
        )
        == audit_team_burnout_overtime_and_bus_factor_redundancy(sample)
    )
    assert (
        "audit_team_burnout_overtime_and_bus_factor_redundancy"
        in mod.__all__
    )


def test_audit_lessons_learned_retrospective_cadence_and_capa_closure_efficacy_compliant():
    from backend.services.project_lifecycle_pmi_service import (
        audit_lessons_learned_retrospective_cadence_and_capa_closure_efficacy,
    )

    res = audit_lessons_learned_retrospective_cadence_and_capa_closure_efficacy(
        [
            {
                "lesson_id": "LL-101",
                "days_since_retrospective": 14,
                "root_cause_documented": True,
                "capa_status": "verified_closed",
                "capa_effectiveness_score": 92.0,
                "recurrence_count": 0,
                "archived_to_opa_repository": True,
            }
        ]
    )
    assert res["is_compliant"] is True
    assert res["status"] == "compliant"
    assert res["lessons_evaluated"] == 1
    assert res["overdue_retrospective_lesson_ids"] == []
    assert res["ineffective_capa_lesson_ids"] == []
    assert res["Violations"] == []


def test_audit_lessons_learned_retrospective_cadence_and_capa_closure_efficacy_critical():
    from backend.services.project_lifecycle_pmi_service import (
        audit_lessons_learned_retrospective_cadence_and_capa_closure_efficacy,
    )

    res = audit_lessons_learned_retrospective_cadence_and_capa_closure_efficacy(
        [
            {
                "lesson_id": "LL-NO-RCA",
                "days_since_retrospective": 10,
                "root_cause_documented": False,
                "capa_status": "open",
                "capa_effectiveness_score": 50.0,
                "recurrence_count": 2,
                "archived_to_opa_repository": True,
            }
        ]
    )
    assert res["is_compliant"] is False
    assert res["status"] == "critical"
    assert res["ineffective_capa_lesson_ids"] == ["LL-NO-RCA"]
    assert len(res["Violations"]) >= 2


def test_audit_lessons_learned_retrospective_cadence_and_capa_closure_efficacy_warning():
    from backend.services.project_lifecycle_pmi_service import (
        audit_lessons_learned_retrospective_cadence_and_capa_closure_efficacy,
    )

    res = audit_lessons_learned_retrospective_cadence_and_capa_closure_efficacy(
        [
            {
                "id": "LL-OVERDUE",
                "days_since_retrospective": 45,
                "root_cause_documented": True,
                "capa_status": "closed",
                "capa_effectiveness_score": 85.0,
                "recurrence_count": 0,
                "archived_to_opa_repository": False,
            }
        ],
        max_days_since_retrospective=30,
        require_opa_repository_archival=True,
    )
    assert res["is_compliant"] is False
    assert res["status"] == "warning"
    assert res["overdue_retrospective_lesson_ids"] == ["LL-OVERDUE"]
    assert res["ineffective_capa_lesson_ids"] == []
    assert res["records"][0]["opa_archival_missing"] is True


def test_audit_lessons_learned_retrospective_cadence_and_capa_closure_efficacy_staticmethod_and_dunder_all():
    import backend.services.project_lifecycle_pmi_service as mod
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_lessons_learned_retrospective_cadence_and_capa_closure_efficacy,
    )

    sample = [{"lesson_id": "LL-99", "days_since_retrospective": 5}]
    assert (
        ProjectLifecyclePMIService.audit_lessons_learned_retrospective_cadence_and_capa_closure_efficacy(
            sample
        )
        == audit_lessons_learned_retrospective_cadence_and_capa_closure_efficacy(
            sample
        )
    )
    assert (
        "audit_lessons_learned_retrospective_cadence_and_capa_closure_efficacy"
        in mod.__all__
    )


def test_audit_force_majeure_relief_event_notice_and_duty_to_mitigate_compliant():
    from backend.services.project_lifecycle_pmi_service import (
        audit_force_majeure_relief_event_notice_and_duty_to_mitigate,
    )

    res = audit_force_majeure_relief_event_notice_and_duty_to_mitigate(
        [
            {
                "event_id": "FM-101",
                "notice_delay_days": 5,
                "continuous_disruption_days": 20,
                "duty_to_mitigate_documented": True,
                "independent_authority_certificate_attached": True,
                "termination_option_triggered": False,
            }
        ]
    )
    assert res["status"] == "compliant"
    assert res["is_compliant"] is True
    assert res["events_evaluated"] == 1
    assert res["time_barred_or_unsubstantiated_event_ids"] == []
    assert res["long_stop_breach_event_ids"] == []
    assert res["Violations"] == []


def test_audit_force_majeure_relief_event_notice_and_duty_to_mitigate_critical():
    from backend.services.project_lifecycle_pmi_service import (
        audit_force_majeure_relief_event_notice_and_duty_to_mitigate,
    )

    res = audit_force_majeure_relief_event_notice_and_duty_to_mitigate(
        [
            {
                "event_id": "FM-LATE-NO-PROOF",
                "notice_delay_days": 25,
                "continuous_disruption_days": 30,
                "duty_to_mitigate_documented": False,
                "independent_authority_certificate_attached": False,
            }
        ],
        max_notice_delay_days=14,
    )
    assert res["status"] == "critical"
    assert res["is_compliant"] is False
    assert res["time_barred_or_unsubstantiated_event_ids"] == ["FM-LATE-NO-PROOF"]
    assert len(res["Violations"]) >= 2


def test_audit_force_majeure_relief_event_notice_and_duty_to_mitigate_warning():
    from backend.services.project_lifecycle_pmi_service import (
        audit_force_majeure_relief_event_notice_and_duty_to_mitigate,
    )

    res = audit_force_majeure_relief_event_notice_and_duty_to_mitigate(
        [
            {
                "id": "FM-LONG-STOP",
                "notice_delay_days": 7,
                "continuous_disruption_days": 120,
                "duty_to_mitigate_documented": True,
                "independent_authority_certificate_attached": True,
                "termination_option_triggered": False,
            }
        ],
        long_stop_duration_days=90,
    )
    assert res["status"] == "warning"
    assert res["is_compliant"] is False
    assert res["time_barred_or_unsubstantiated_event_ids"] == []
    assert res["long_stop_breach_event_ids"] == ["FM-LONG-STOP"]
    assert res["records"][0]["long_stop_exceeded_without_termination_review"] is True


def test_audit_force_majeure_relief_event_notice_and_duty_to_mitigate_staticmethod_and_dunder_all():
    import backend.services.project_lifecycle_pmi_service as mod
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_force_majeure_relief_event_notice_and_duty_to_mitigate,
    )

    sample = [{"event_id": "FM-1", "notice_delay_days": 3}]
    assert (
        ProjectLifecyclePMIService.audit_force_majeure_relief_event_notice_and_duty_to_mitigate(
            sample
        )
        == audit_force_majeure_relief_event_notice_and_duty_to_mitigate(
            sample
        )
    )
    assert (
        "audit_force_majeure_relief_event_notice_and_duty_to_mitigate"
        in mod.__all__
    )


def test_audit_stakeholder_escalation_sla_and_ombudsman_dispute_resolution_compliant():
    from backend.services.project_lifecycle_pmi_service import (
        audit_stakeholder_escalation_sla_and_ombudsman_dispute_resolution,
    )

    res = audit_stakeholder_escalation_sla_and_ombudsman_dispute_resolution(
        [
            {
                "case_id": "GRV-101",
                "initial_response_hours": 8.0,
                "resolution_cycle_days": 7,
                "escalated_to_litigation": False,
                "adr_mediation_attempted": True,
                "retaliation_safeguard_verified": True,
                "sponsor_signoff_recorded": True,
            }
        ]
    )
    assert res["status"] == "compliant"
    assert res["is_compliant"] is True
    assert res["cases_evaluated"] == 1
    assert res["adr_or_retaliation_breach_case_ids"] == []
    assert res["sla_overdue_case_ids"] == []
    assert res["Violations"] == []


def test_audit_stakeholder_escalation_sla_and_ombudsman_dispute_resolution_critical():
    from backend.services.project_lifecycle_pmi_service import (
        audit_stakeholder_escalation_sla_and_ombudsman_dispute_resolution,
    )

    res = audit_stakeholder_escalation_sla_and_ombudsman_dispute_resolution(
        [
            {
                "case_id": "GRV-LITIGATE",
                "initial_response_hours": 12.0,
                "resolution_cycle_days": 10,
                "escalated_to_litigation": True,
                "adr_mediation_attempted": False,
                "retaliation_safeguard_verified": False,
                "sponsor_signoff_recorded": True,
            }
        ]
    )
    assert res["status"] == "critical"
    assert res["is_compliant"] is False
    assert res["adr_or_retaliation_breach_case_ids"] == ["GRV-LITIGATE"]
    assert len(res["Violations"]) >= 1


def test_audit_stakeholder_escalation_sla_and_ombudsman_dispute_resolution_warning():
    from backend.services.project_lifecycle_pmi_service import (
        audit_stakeholder_escalation_sla_and_ombudsman_dispute_resolution,
    )

    res = audit_stakeholder_escalation_sla_and_ombudsman_dispute_resolution(
        [
            {
                "id": "GRV-SLOW",
                "initial_response_hours": 36.0,
                "resolution_cycle_days": 22,
                "escalated_to_litigation": False,
                "adr_mediation_attempted": True,
                "retaliation_safeguard_verified": True,
                "sponsor_signoff_recorded": False,
            }
        ],
        max_initial_response_hours=24.0,
        max_resolution_cycle_days=15,
    )
    assert res["status"] == "warning"
    assert res["is_compliant"] is False
    assert res["adr_or_retaliation_breach_case_ids"] == []
    assert res["sla_overdue_case_ids"] == ["GRV-SLOW"]
    assert res["records"][0]["initial_response_sla_breach"] is True
    assert res["records"][0]["resolution_cycle_overdue_or_unsigned"] is True


def test_audit_stakeholder_escalation_sla_and_ombudsman_dispute_resolution_staticmethod_and_dunder_all():
    import backend.services.project_lifecycle_pmi_service as mod
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_stakeholder_escalation_sla_and_ombudsman_dispute_resolution,
    )

    sample = [{"case_id": "GRV-1", "initial_response_hours": 4.0}]
    assert (
        ProjectLifecyclePMIService.audit_stakeholder_escalation_sla_and_ombudsman_dispute_resolution(
            sample
        )
        == audit_stakeholder_escalation_sla_and_ombudsman_dispute_resolution(
            sample
        )
    )
    assert (
        "audit_stakeholder_escalation_sla_and_ombudsman_dispute_resolution"
        in mod.__all__
    )


def test_audit_commissioning_punch_list_a_items_and_holdback_multiplier_compliant():
    from backend.services.project_lifecycle_pmi_service import (
        audit_commissioning_punch_list_a_items_and_holdback_multiplier,
    )

    res = audit_commissioning_punch_list_a_items_and_holdback_multiplier(
        [
            {
                "system_id": "SYS-HVAC-01",
                "open_category_a_safety_items": 0,
                "open_category_b_minor_items_cost": 10000.0,
                "retained_holdback_amount": 16000.0,
                "b_item_cure_window_days": 15,
                "joint_walkdown_signed": True,
            }
        ]
    )
    assert res["status"] == "compliant"
    assert res["is_compliant"] is True
    assert res["systems_evaluated"] == 1
    assert res["blocked_a_item_system_ids"] == []
    assert res["underheld_or_unsigned_system_ids"] == []
    assert res["Violations"] == []


def test_audit_commissioning_punch_list_a_items_and_holdback_multiplier_critical():
    from backend.services.project_lifecycle_pmi_service import (
        audit_commissioning_punch_list_a_items_and_holdback_multiplier,
    )

    res = audit_commissioning_punch_list_a_items_and_holdback_multiplier(
        [
            {
                "system_id": "SYS-FIRE-02",
                "open_category_a_safety_items": 2,
                "open_category_b_minor_items_cost": 5000.0,
                "retained_holdback_amount": 10000.0,
                "b_item_cure_window_days": 10,
                "joint_walkdown_signed": True,
            }
        ]
    )
    assert res["status"] == "critical"
    assert res["is_compliant"] is False
    assert res["blocked_a_item_system_ids"] == ["SYS-FIRE-02"]
    assert res["records"][0]["open_category_a_blocking_substantial_completion"] is True
    assert len(res["Violations"]) >= 1


def test_audit_commissioning_punch_list_a_items_and_holdback_multiplier_warning():
    from backend.services.project_lifecycle_pmi_service import (
        audit_commissioning_punch_list_a_items_and_holdback_multiplier,
    )

    res = audit_commissioning_punch_list_a_items_and_holdback_multiplier(
        [
            {
                "id": "SYS-ELEC-03",
                "open_category_a_safety_items": 0,
                "open_category_b_minor_items_cost": 20000.0,
                "retained_holdback_amount": 25000.0,
                "b_item_cure_window_days": 45,
                "joint_walkdown_signed": False,
            }
        ],
        min_b_item_holdback_multiplier=1.5,
        max_b_item_cure_days=30,
    )
    assert res["status"] == "warning"
    assert res["is_compliant"] is False
    assert res["blocked_a_item_system_ids"] == []
    assert res["underheld_or_unsigned_system_ids"] == ["SYS-ELEC-03"]
    assert res["records"][0]["insufficient_b_item_holdback_escrow"] is True
    assert res["records"][0]["excessive_b_item_cure_window"] is True
    assert res["records"][0]["missing_joint_walkdown_signoff"] is True


def test_audit_commissioning_punch_list_a_items_and_holdback_multiplier_staticmethod_and_dunder_all():
    import backend.services.project_lifecycle_pmi_service as mod
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_commissioning_punch_list_a_items_and_holdback_multiplier,
    )

    sample = [{"system_id": "SYS-01", "open_category_a_safety_items": 0}]
    assert (
        ProjectLifecyclePMIService.audit_commissioning_punch_list_a_items_and_holdback_multiplier(
            sample
        )
        == audit_commissioning_punch_list_a_items_and_holdback_multiplier(sample)
    )
    assert (
        "audit_commissioning_punch_list_a_items_and_holdback_multiplier"
        in mod.__all__
    )



# ── audit_jv_consortium_equity_split_and_deadlock_cure (PMBOK §12.1 & §9.3, pure helper) ──


def test_jv_consortium_governance_optimal_agreements():
    """JVs con equity == 100.0 (+/- 0.01), responsabilidad mancomunada, SLA <= 10 días y dilución activa -> 'JV_CONSORTIUM_GOVERNANCE_OPTIMAL'."""
    import backend.services.project_lifecycle_pmi_service as lifecycle_module
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_jv_consortium_equity_split_and_deadlock_cure,
    )

    agreements = [
        {
            "jv_id": "JV-001",
            "total_equity_share_pct": 100.0,
            "joint_and_several_liability_bound": True,
            "deadlock_escalation_days": 5,
            "defaulting_partner_dilution_clause_active": True,
        },
        {
            "jv_id": "JV-002",
            # Defaults implícitos por campo: equity 100.0, True, 5 días, dilución True.
        },
    ]
    res = audit_jv_consortium_equity_split_and_deadlock_cure(agreements)
    assert res == {
        "evaluated_jvs_count": 2,
        "unbalanced_equity_or_unbound_liability_jv_ids": [],
        "slow_deadlock_or_missing_dilution_jv_ids": [],
        "jv_governance_status": "JV_CONSORTIUM_GOVERNANCE_OPTIMAL",
        "is_jv_compliant": True,
    }
    # Equity dentro de la tolerancia +/- 0.01 (100.005 / 99.995) no es breach
    at_tolerance = audit_jv_consortium_equity_split_and_deadlock_cure(
        [{"jv_id": "JV-003", "total_equity_share_pct": 100.005}]
    )
    assert at_tolerance["jv_governance_status"] == "JV_CONSORTIUM_GOVERNANCE_OPTIMAL"
    at_tolerance_below = audit_jv_consortium_equity_split_and_deadlock_cure(
        [{"jv_id": "JV-003B", "total_equity_share_pct": 99.995}]
    )
    assert at_tolerance_below["jv_governance_status"] == "JV_CONSORTIUM_GOVERNANCE_OPTIMAL"
    # Equity 100.01 excede la tolerancia en aritmética float (diff ≈ 0.0100000000093) -> breach literal
    over_tolerance = audit_jv_consortium_equity_split_and_deadlock_cure(
        [{"jv_id": "JV-003C", "total_equity_share_pct": 100.01}]
    )
    assert over_tolerance["jv_governance_status"] == "JV_EQUITY_OR_LIABILITY_BREACH"
    # Escalación exactamente en el máximo 10 días no es warning (comparación estricta >)
    at_sla = audit_jv_consortium_equity_split_and_deadlock_cure(
        [{"jv_id": "JV-004", "deadlock_escalation_days": 10}]
    )
    assert at_sla["jv_governance_status"] == "JV_CONSORTIUM_GOVERNANCE_OPTIMAL"
    assert (
        ProjectLifecyclePMIService.audit_jv_consortium_equity_split_and_deadlock_cure(
            agreements
        )
        == res
    )
    assert "audit_jv_consortium_equity_split_and_deadlock_cure" in lifecycle_module.__all__


def test_jv_equity_or_liability_breach():
    """Equity desviado > 0.01 de 100.0 o responsabilidad no mancomunada -> 'JV_EQUITY_OR_LIABILITY_BREACH' con precedencia sobre WARNING."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_jv_consortium_equity_split_and_deadlock_cure,
    )

    breach = audit_jv_consortium_equity_split_and_deadlock_cure(
        [
            {
                "jv_id": "JV-OVER",
                "total_equity_share_pct": 101.5,
                "joint_and_several_liability_bound": True,
            },
            {
                "jv_id": "JV-UNBOUND",
                "total_equity_share_pct": 100.0,
                "joint_and_several_liability_bound": False,
            },
        ]
    )
    assert breach["evaluated_jvs_count"] == 2
    assert breach["unbalanced_equity_or_unbound_liability_jv_ids"] == [
        "JV-OVER",
        "JV-UNBOUND",
    ]
    assert breach["jv_governance_status"] == "JV_EQUITY_OR_LIABILITY_BREACH"
    assert breach["is_jv_compliant"] is False

    # Breach tiene precedencia aunque también haya JVs con SLA lento / dilución ausente
    mixed = audit_jv_consortium_equity_split_and_deadlock_cure(
        [
            {"jv_id": "JV-SLOW-SLA", "deadlock_escalation_days": 21},
            {"jv_id": "JV-OVER-2", "total_equity_share_pct": 103.3},
        ]
    )
    assert mixed["jv_governance_status"] == "JV_EQUITY_OR_LIABILITY_BREACH"


def test_jv_deadlock_or_dilution_warning():
    """Escalación de deadlock > 10 días o cláusula de dilución inactiva (con equity/liabilidad limpios) -> 'JV_DEADLOCK_OR_DILUTION_WARNING'."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_jv_consortium_equity_split_and_deadlock_cure,
    )

    warning = audit_jv_consortium_equity_split_and_deadlock_cure(
        [
            {
                "jv_id": "JV-SLOW-ESCALATION",
                "deadlock_escalation_days": 12,
                "defaulting_partner_dilution_clause_active": True,
            },
            {
                "jv_id": "JV-NO-DILUTION",
                "deadlock_escalation_days": 5,
                "defaulting_partner_dilution_clause_active": False,
            },
        ]
    )
    assert warning["evaluated_jvs_count"] == 2
    assert warning["unbalanced_equity_or_unbound_liability_jv_ids"] == []
    assert warning["slow_deadlock_or_missing_dilution_jv_ids"] == [
        "JV-SLOW-ESCALATION",
        "JV-NO-DILUTION",
    ]
    assert warning["jv_governance_status"] == "JV_DEADLOCK_OR_DILUTION_WARNING"
    assert warning["is_jv_compliant"] is False

    custom = audit_jv_consortium_equity_split_and_deadlock_cure(
        [{"jv_id": "JV-4", "deadlock_escalation_days": 8}],
        max_deadlock_escalation_days=7,
    )
    assert custom["jv_governance_status"] == "JV_DEADLOCK_OR_DILUTION_WARNING"
    assert custom["slow_deadlock_or_missing_dilution_jv_ids"] == ["JV-4"]


def test_jv_empty_invalid_and_field_reversion():
    """None / dicts inválidos se descartan; campos no numéricos/no bool revierten a defaults del spec."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_jv_consortium_equity_split_and_deadlock_cure,
    )

    empty_res = audit_jv_consortium_equity_split_and_deadlock_cure(None)
    assert empty_res == {
        "evaluated_jvs_count": 0,
        "unbalanced_equity_or_unbound_liability_jv_ids": [],
        "slow_deadlock_or_missing_dilution_jv_ids": [],
        "jv_governance_status": "JV_CONSORTIUM_GOVERNANCE_OPTIMAL",
        "is_jv_compliant": True,
    }

    invalid_res = audit_jv_consortium_equity_split_and_deadlock_cure(
        ["no-dict", None, {"jv_id": "   "}, {"jv_id": 22}, {"deadlock_escalation_days": 30}]
    )
    assert invalid_res["evaluated_jvs_count"] == 0

    bad_fields = audit_jv_consortium_equity_split_and_deadlock_cure(
        [
            {
                "jv_id": "JV-BAD",
                "total_equity_share_pct": "cien",
                "joint_and_several_liability_bound": "sí",
                "deadlock_escalation_days": None,
                "defaulting_partner_dilution_clause_active": 1,
            }
        ]
    )
    assert bad_fields == {
        "evaluated_jvs_count": 1,
        "unbalanced_equity_or_unbound_liability_jv_ids": [],
        "slow_deadlock_or_missing_dilution_jv_ids": [],
        "jv_governance_status": "JV_CONSORTIUM_GOVERNANCE_OPTIMAL",
        "is_jv_compliant": True,
    }


def test_audit_final_lien_waiver_unconditional_release_and_mechanics_lien_exposure_lien_free():
    from backend.services.project_lifecycle_pmi_service import (
        audit_final_lien_waiver_unconditional_release_and_mechanics_lien_exposure,
    )

    res = audit_final_lien_waiver_unconditional_release_and_mechanics_lien_exposure(
        contractors=[
            {
                "contractor_id": "GC-01",
                "contract_final_amount": 500000.0,
                "paid_to_date_amount": 500000.0,
                "unconditional_final_waiver_signed": True,
                "sub_tier_affidavits_complete": True,
                "recorded_mechanics_lien_amount": 0.0,
            },
            {
                "contractor_id": "MEP-02",
                "contract_final_amount": 250000.0,
                "paid_to_date_amount": 240000.0,
                "unconditional_final_waiver_signed": True,
                "sub_tier_affidavits_complete": True,
                "recorded_mechanics_lien_amount": 0.0,
            },
        ],
        retainage_escrow_balance=25000.0,
    )
    assert res["is_valid"] is True
    assert res["status"] == "LIEN_FREE_READY_FOR_CLOSEOUT"
    assert res["total_contractors"] == 2
    assert res["missing_waiver_or_affidavit_contractors"] == []
    assert res["active_mechanics_liens"] == []
    assert res["total_mechanics_lien_amount"] == 0.0
    assert res["required_lien_discharge_bond_amount"] == 0.0
    assert res["unpaid_balance_total"] == 10000.0
    assert res["escrow_covers_lien_bond"] is True


def test_audit_final_lien_waiver_unconditional_release_and_mechanics_lien_exposure_hold_pending_waivers():
    from backend.services.project_lifecycle_pmi_service import (
        audit_final_lien_waiver_unconditional_release_and_mechanics_lien_exposure,
    )

    res = audit_final_lien_waiver_unconditional_release_and_mechanics_lien_exposure(
        contractors=[
            {
                "contractor_id": "SUB-HVAC",
                "contract_final_amount": 120000.0,
                "paid_to_date_amount": 100000.0,
                "unconditional_final_waiver_signed": False,
                "sub_tier_affidavits_complete": True,
                "recorded_mechanics_lien_amount": 0.0,
            }
        ],
        retainage_escrow_balance=20000.0,
    )
    assert res["is_valid"] is False
    assert res["status"] == "HOLD_FINAL_RELEASE_PENDING_WAIVERS"
    assert res["missing_waiver_or_affidavit_contractors"] == ["SUB-HVAC"]
    assert res["active_mechanics_liens"] == []
    assert res["unpaid_balance_total"] == 20000.0


def test_audit_final_lien_waiver_unconditional_release_and_mechanics_lien_exposure_critical_mechanics_lien():
    from backend.services.project_lifecycle_pmi_service import (
        audit_final_lien_waiver_unconditional_release_and_mechanics_lien_exposure,
    )

    res = audit_final_lien_waiver_unconditional_release_and_mechanics_lien_exposure(
        contractors=[
            {
                "contractor_id": "SUB-STEEL",
                "contract_final_amount": 300000.0,
                "paid_to_date_amount": 250000.0,
                "unconditional_final_waiver_signed": False,
                "sub_tier_affidavits_complete": False,
                "recorded_mechanics_lien_amount": 40000.0,
            }
        ],
        retainage_escrow_balance=50000.0,
        lien_bonding_off_multiplier=1.50,
    )
    assert res["is_valid"] is False
    assert res["status"] == "CRITICAL_MECHANICS_LIEN_ENCUMBRANCE"
    assert res["active_mechanics_liens"] == ["SUB-STEEL"]
    assert res["total_mechanics_lien_amount"] == 40000.0
    assert res["required_lien_discharge_bond_amount"] == 60000.0
    assert res["escrow_covers_lien_bond"] is False


def test_audit_final_lien_waiver_unconditional_release_and_mechanics_lien_exposure_staticmethod_and_exports():
    import backend.services.project_lifecycle_pmi_service as mod
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_final_lien_waiver_unconditional_release_and_mechanics_lien_exposure,
    )

    assert (
        "audit_final_lien_waiver_unconditional_release_and_mechanics_lien_exposure"
        in mod.__all__
    )
    sample = [
        {
            "contractor_id": "GC-1",
            "contract_final_amount": 10000.0,
            "paid_to_date_amount": 10000.0,
            "unconditional_final_waiver_signed": True,
            "sub_tier_affidavits_complete": True,
            "recorded_mechanics_lien_amount": 0.0,
        }
    ]
    assert (
        ProjectLifecyclePMIService.audit_final_lien_waiver_unconditional_release_and_mechanics_lien_exposure(
            sample
        )
        == audit_final_lien_waiver_unconditional_release_and_mechanics_lien_exposure(
            sample
        )
    )


def test_audit_dlp_warranty_callout_sla_and_retention_bond_stepdown_approved():
    from backend.services.project_lifecycle_pmi_service import (
        audit_dlp_warranty_callout_sla_and_retention_bond_stepdown,
    )

    res = audit_dlp_warranty_callout_sla_and_retention_bond_stepdown(
        warranty_claims=[
            {
                "claim_id": "DLP-01",
                "severity": "MAJOR_FUNCTIONAL",
                "response_hours_elapsed": 12.0,
                "sla_target_hours": 24.0,
                "recurrence_count": 1,
                "resolved": True,
            },
            {
                "claim_id": "DLP-02",
                "severity": "MINOR_COSMETIC",
                "response_hours_elapsed": 48.0,
                "sla_target_hours": 72.0,
                "recurrence_count": 1,
                "resolved": True,
            },
        ],
        retention_bank_guarantee_amount=150000.0,
        estimated_unresolved_remediation_cost=0.0,
        chronic_recurrence_threshold=3,
    )
    assert res["is_valid"] is True
    assert res["total_claims"] == 2
    assert res["sla_breached_claims"] == []
    assert res["chronic_latent_defect_claims"] == []
    assert res["open_emergency_safety_claims"] == []
    assert res["guarantee_covers_remediation"] is True
    assert res["stepdown_decision"] == "APPROVE_FINAL_CERTIFICATE_AND_BOND_RELEASE"


def test_audit_dlp_warranty_callout_sla_and_retention_bond_stepdown_block_and_call_guarantee():
    from backend.services.project_lifecycle_pmi_service import (
        audit_dlp_warranty_callout_sla_and_retention_bond_stepdown,
    )

    res = audit_dlp_warranty_callout_sla_and_retention_bond_stepdown(
        warranty_claims=[
            {
                "claim_id": "DLP-EMERG-99",
                "severity": "EMERGENCY_SAFETY",
                "response_hours_elapsed": 6.0,
                "sla_target_hours": 4.0,
                "recurrence_count": 4,
                "resolved": False,
            }
        ],
        retention_bank_guarantee_amount=40000.0,
        estimated_unresolved_remediation_cost=75000.0,
        chronic_recurrence_threshold=3,
    )
    assert res["is_valid"] is False
    assert res["sla_breached_claims"] == ["DLP-EMERG-99"]
    assert res["chronic_latent_defect_claims"] == ["DLP-EMERG-99"]
    assert res["open_emergency_safety_claims"] == ["DLP-EMERG-99"]
    assert res["guarantee_covers_remediation"] is False
    assert res["stepdown_decision"] == "BLOCK_RELEASE_AND_CALL_BANK_GUARANTEE"


def test_audit_dlp_warranty_callout_sla_and_retention_bond_stepdown_hold_pending_sla():
    from backend.services.project_lifecycle_pmi_service import (
        audit_dlp_warranty_callout_sla_and_retention_bond_stepdown,
    )

    res = audit_dlp_warranty_callout_sla_and_retention_bond_stepdown(
        warranty_claims=[
            {
                "claim_id": "DLP-SLA-LATE",
                "severity": "MAJOR_FUNCTIONAL",
                "response_hours_elapsed": 30.0,
                "sla_target_hours": 24.0,
                "recurrence_count": 1,
                "resolved": False,
            }
        ],
        retention_bank_guarantee_amount=100000.0,
        estimated_unresolved_remediation_cost=20000.0,
    )
    assert res["is_valid"] is False
    assert res["sla_breached_claims"] == ["DLP-SLA-LATE"]
    assert res["chronic_latent_defect_claims"] == []
    assert res["open_emergency_safety_claims"] == []
    assert res["guarantee_covers_remediation"] is True
    assert res["stepdown_decision"] == "HOLD_STEPDOWN_PENDING_SLA_REMEDIATION"


def test_audit_dlp_warranty_callout_sla_and_retention_bond_stepdown_staticmethod_and_dunder_all():
    import backend.services.project_lifecycle_pmi_service as mod
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_dlp_warranty_callout_sla_and_retention_bond_stepdown,
    )

    sample = [
        {
            "claim_id": "DLP-1",
            "severity": "MINOR_COSMETIC",
            "response_hours_elapsed": 10.0,
            "sla_target_hours": 24.0,
            "recurrence_count": 1,
            "resolved": True,
        }
    ]
    assert (
        ProjectLifecyclePMIService.audit_dlp_warranty_callout_sla_and_retention_bond_stepdown(
            sample
        )
        == audit_dlp_warranty_callout_sla_and_retention_bond_stepdown(sample)
    )
    assert (
        "audit_dlp_warranty_callout_sla_and_retention_bond_stepdown"
        in mod.__all__
    )


def test_audit_software_escrow_deposit_verification_and_release_trigger_verified():
    from backend.services.project_lifecycle_pmi_service import (
        audit_software_escrow_deposit_verification_and_release_trigger,
    )

    res = audit_software_escrow_deposit_verification_and_release_trigger(
        escrow_deposits=[
            {
                "deposit_id": "ESC-CORE-V4",
                "days_since_last_deposit": 12,
                "clean_room_reproducible_build_verified": True,
                "cryptographic_sbom_hash_matched": True,
                "vendor_insolvency_or_sla_abandonment_triggered": False,
                "beneficiary_release_executed": False,
            },
            {
                "deposit_id": "ESC-LEGACY-V2",
                "days_since_last_deposit": 5,
                "clean_room_reproducible_build_verified": True,
                "cryptographic_sbom_hash_matched": True,
                "vendor_insolvency_or_sla_abandonment_triggered": True,
                "beneficiary_release_executed": True,
            },
        ],
        max_deposit_staleness_days=30,
    )
    assert res["is_valid"] is True
    assert res["total_deposits"] == 2
    assert res["unverified_build_or_hash_deposits"] == []
    assert res["stale_escrow_deposits"] == []
    assert res["blocked_release_trigger_deposits"] == []
    assert res["escrow_governance_status"] == "ESCROW_CONTINUITY_VERIFIED"


def test_audit_software_escrow_deposit_verification_and_release_trigger_critical_breach():
    from backend.services.project_lifecycle_pmi_service import (
        audit_software_escrow_deposit_verification_and_release_trigger,
    )

    res = audit_software_escrow_deposit_verification_and_release_trigger(
        escrow_deposits=[
            {
                "deposit_id": "ESC-BROKEN-BUILD",
                "days_since_last_deposit": 10,
                "clean_room_reproducible_build_verified": False,
                "cryptographic_sbom_hash_matched": True,
                "vendor_insolvency_or_sla_abandonment_triggered": True,
                "beneficiary_release_executed": False,
            }
        ]
    )
    assert res["is_valid"] is False
    assert res["unverified_build_or_hash_deposits"] == ["ESC-BROKEN-BUILD"]
    assert res["blocked_release_trigger_deposits"] == ["ESC-BROKEN-BUILD"]
    assert res["escrow_governance_status"] == "CRITICAL_UNVERIFIED_BUILD_OR_BLOCKED_RELEASE"


def test_audit_software_escrow_deposit_verification_and_release_trigger_stale_warning():
    from backend.services.project_lifecycle_pmi_service import (
        audit_software_escrow_deposit_verification_and_release_trigger,
    )

    res = audit_software_escrow_deposit_verification_and_release_trigger(
        escrow_deposits=[
            {
                "deposit_id": "ESC-STALE-01",
                "days_since_last_deposit": 45,
                "clean_room_reproducible_build_verified": True,
                "cryptographic_sbom_hash_matched": True,
            }
        ],
        max_deposit_staleness_days=30,
    )
    assert res["is_valid"] is False
    assert res["unverified_build_or_hash_deposits"] == []
    assert res["stale_escrow_deposits"] == ["ESC-STALE-01"]
    assert res["blocked_release_trigger_deposits"] == []
    assert res["escrow_governance_status"] == "STALE_DEPOSIT_SYNC_WARNING"


def test_audit_software_escrow_deposit_verification_and_release_trigger_staticmethod_and_dunder_all():
    import backend.services.project_lifecycle_pmi_service as mod
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_software_escrow_deposit_verification_and_release_trigger,
    )

    empty = audit_software_escrow_deposit_verification_and_release_trigger([])
    assert empty["is_valid"] is False
    assert empty["escrow_governance_status"] == "CRITICAL_UNVERIFIED_BUILD_OR_BLOCKED_RELEASE"

    sample = [
        {
            "deposit_id": "ESC-1",
            "days_since_last_deposit": 5,
            "clean_room_reproducible_build_verified": True,
            "cryptographic_sbom_hash_matched": True,
        }
    ]
    assert (
        ProjectLifecyclePMIService.audit_software_escrow_deposit_verification_and_release_trigger(
            sample
        )
        == audit_software_escrow_deposit_verification_and_release_trigger(sample)
    )
    assert (
        "audit_software_escrow_deposit_verification_and_release_trigger"
        in mod.__all__
    )


def test_audit_ppp_concession_handback_residual_life_and_reserve_escrow_compliant():
    from backend.services.project_lifecycle_pmi_service import (
        audit_ppp_concession_handback_residual_life_and_reserve_escrow,
    )

    res = audit_ppp_concession_handback_residual_life_and_reserve_escrow(
        concession_assets=[
            {
                "asset_id": "BRIDGE-DECK-01",
                "assessed_residual_design_life_years": 12.5,
                "contracted_min_residual_life_years": 10.0,
                "rehabilitation_capex_required": 100000.0,
                "independent_engineer_certified": True,
            },
            {
                "asset_id": "TUNNEL-VENT-02",
                "assessed_residual_design_life_years": 8.0,
                "contracted_min_residual_life_years": 5.0,
                "rehabilitation_capex_required": 60000.0,
                "independent_engineer_certified": True,
            },
        ],
        handback_reserve_escrow_balance=250000.0,
        required_escrow_coverage_ratio=1.25,
    )
    assert res["is_valid"] is True
    assert res["total_assets"] == 2
    assert res["deficient_residual_life_assets"] == []
    assert res["uncertified_handback_assets"] == []
    assert res["total_rehabilitation_capex"] == 160000.0
    assert res["required_handback_escrow"] == 200000.0
    assert res["escrow_sufficient"] is True
    assert res["handback_status"] == "PPP_HANDBACK_COMPLIANT"


def test_audit_ppp_concession_handback_residual_life_and_reserve_escrow_critical_deficiency():
    from backend.services.project_lifecycle_pmi_service import (
        audit_ppp_concession_handback_residual_life_and_reserve_escrow,
    )

    res = audit_ppp_concession_handback_residual_life_and_reserve_escrow(
        concession_assets=[
            {
                "asset_id": "PAVEMENT-SEC-04",
                "assessed_residual_design_life_years": 3.5,
                "contracted_min_residual_life_years": 7.0,
                "rehabilitation_capex_required": 400000.0,
                "independent_engineer_certified": False,
            }
        ],
        handback_reserve_escrow_balance=300000.0,
        required_escrow_coverage_ratio=1.25,
    )
    assert res["is_valid"] is False
    assert res["deficient_residual_life_assets"] == ["PAVEMENT-SEC-04"]
    assert res["uncertified_handback_assets"] == ["PAVEMENT-SEC-04"]
    assert res["required_handback_escrow"] == 500000.0
    assert res["escrow_sufficient"] is False
    assert (
        res["handback_status"]
        == "CRITICAL_HANDBACK_DEFICIENCY_OR_ESCROW_SHORTFALL"
    )


def test_audit_ppp_concession_handback_residual_life_and_reserve_escrow_pending_ie_signoff():
    from backend.services.project_lifecycle_pmi_service import (
        audit_ppp_concession_handback_residual_life_and_reserve_escrow,
    )

    res = audit_ppp_concession_handback_residual_life_and_reserve_escrow(
        concession_assets=[
            {
                "asset_id": "TOLL-GANTRY-01",
                "assessed_residual_design_life_years": 9.0,
                "contracted_min_residual_life_years": 5.0,
                "rehabilitation_capex_required": 0.0,
                "independent_engineer_certified": False,
            }
        ],
        handback_reserve_escrow_balance=50000.0,
    )
    assert res["is_valid"] is False
    assert res["deficient_residual_life_assets"] == []
    assert res["uncertified_handback_assets"] == ["TOLL-GANTRY-01"]
    assert res["escrow_sufficient"] is True
    assert res["handback_status"] == "PENDING_INDEPENDENT_ENGINEER_SIGNOFF"


def test_audit_ppp_concession_handback_residual_life_and_reserve_escrow_staticmethod_and_dunder_all():
    import backend.services.project_lifecycle_pmi_service as mod
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_ppp_concession_handback_residual_life_and_reserve_escrow,
    )

    empty = audit_ppp_concession_handback_residual_life_and_reserve_escrow([])
    assert empty["is_valid"] is False
    assert (
        empty["handback_status"]
        == "CRITICAL_HANDBACK_DEFICIENCY_OR_ESCROW_SHORTFALL"
    )

    sample = [
        {
            "asset_id": "AST-1",
            "assessed_residual_design_life_years": 10.0,
            "contracted_min_residual_life_years": 5.0,
        }
    ]
    assert (
        ProjectLifecyclePMIService.audit_ppp_concession_handback_residual_life_and_reserve_escrow(
            sample
        )
        == audit_ppp_concession_handback_residual_life_and_reserve_escrow(sample)
    )
    assert (
        "audit_ppp_concession_handback_residual_life_and_reserve_escrow"
        in mod.__all__
    )


def test_audit_eia_environmental_permit_conditions_and_chance_find_stop_work_compliant():
    from backend.services.project_lifecycle_pmi_service import (
        audit_eia_environmental_permit_conditions_and_chance_find_stop_work,
    )

    res = audit_eia_environmental_permit_conditions_and_chance_find_stop_work(
        [
            {
                "zone_id": "WETLAND-BUFFER-A",
                "permit_active": True,
                "measured_turbidity_ntu": 14.2,
                "measured_noise_db": 72.5,
                "cultural_chance_find_triggered": False,
                "work_halted_for_archaeologist": True,
            },
            {
                "zone_id": "EXCAVATION-SECTOR-B",
                "permit_active": True,
                "measured_turbidity_ntu": 18.0,
                "measured_noise_db": 81.0,
                "cultural_chance_find_triggered": True,
                "work_halted_for_archaeologist": True,
            },
        ]
    )
    assert res["is_valid"] is True
    assert res["total_zones"] == 2
    assert res["stop_work_breach_zones"] == []
    assert res["threshold_exceedance_zones"] == []
    assert res["eia_compliance_status"] == "EIA_PERMIT_COMPLIANT"
    assert res["recommendations"] == []


def test_audit_eia_environmental_permit_conditions_and_chance_find_stop_work_critical_breach():
    from backend.services.project_lifecycle_pmi_service import (
        audit_eia_environmental_permit_conditions_and_chance_find_stop_work,
    )

    res = audit_eia_environmental_permit_conditions_and_chance_find_stop_work(
        [
            {
                "zone_id": "RIVER-CROSSING-01",
                "permit_active": False,
                "measured_turbidity_ntu": 12.0,
                "measured_noise_db": 70.0,
            },
            {
                "zone_id": "TRENCH-HERITAGE-02",
                "permit_active": True,
                "measured_turbidity_ntu": 15.0,
                "measured_noise_db": 75.0,
                "cultural_chance_find_triggered": True,
                "work_halted_for_archaeologist": False,
            },
        ]
    )
    assert res["is_valid"] is False
    assert res["stop_work_breach_zones"] == [
        "RIVER-CROSSING-01",
        "TRENCH-HERITAGE-02",
    ]
    assert res["threshold_exceedance_zones"] == []
    assert (
        res["eia_compliance_status"]
        == "CRITICAL_UNPERMITTED_OR_CHANCE_FIND_BREACH"
    )
    assert len(res["recommendations"]) == 1


def test_audit_eia_environmental_permit_conditions_and_chance_find_stop_work_threshold_warning():
    from backend.services.project_lifecycle_pmi_service import (
        audit_eia_environmental_permit_conditions_and_chance_find_stop_work,
    )

    res = audit_eia_environmental_permit_conditions_and_chance_find_stop_work(
        [
            {
                "zone_id": "ESTUARY-DREDGE-01",
                "permit_active": True,
                "measured_turbidity_ntu": 38.5,
                "measured_noise_db": 79.0,
            },
            {
                "zone_id": "PILE-DRIVING-02",
                "permit_active": True,
                "measured_turbidity_ntu": 19.0,
                "measured_noise_db": 94.0,
            },
        ],
        max_turbidity_ntu=25.0,
        max_noise_db=85.0,
    )
    assert res["is_valid"] is False
    assert res["stop_work_breach_zones"] == []
    assert res["threshold_exceedance_zones"] == [
        "ESTUARY-DREDGE-01",
        "PILE-DRIVING-02",
    ]
    assert (
        res["eia_compliance_status"]
        == "ENVIRONMENTAL_THRESHOLD_EXCEEDANCE_WARNING"
    )
    assert len(res["recommendations"]) == 1


def test_audit_eia_environmental_permit_conditions_and_chance_find_stop_work_staticmethod_and_dunder_all():
    import backend.services.project_lifecycle_pmi_service as mod
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_eia_environmental_permit_conditions_and_chance_find_stop_work,
    )

    sample = [
        {
            "zone_id": "Z-1",
            "permit_active": True,
            "measured_turbidity_ntu": 10.0,
            "measured_noise_db": 65.0,
        }
    ]
    assert (
        ProjectLifecyclePMIService.audit_eia_environmental_permit_conditions_and_chance_find_stop_work(
            sample
        )
        == audit_eia_environmental_permit_conditions_and_chance_find_stop_work(
            sample
        )
    )
    assert (
        "audit_eia_environmental_permit_conditions_and_chance_find_stop_work"
        in mod.__all__
    )


def test_audit_decommissioning_hazmat_manifest_and_site_remediation_clearance_healthy():
    from backend.services.project_lifecycle_pmi_service import (
        audit_decommissioning_hazmat_manifest_and_site_remediation_clearance,
    )

    records = [
        {
            "zone_id": "ZONE-ASBESTOS-01",
            "hazmat_class": "asbestos",
            "disposal_manifests_completed": 12,
            "disposal_manifests_required": 12,
            "post_remediation_contaminant_ppm": 0.004,
            "regulatory_threshold_ppm": 0.01,
            "uncontained_spill_incident": False,
            "licensed_epa_tsdf_facility": True,
            "estimated_salvage_value": 50000.0,
            "realized_salvage_value": 45000.0,
            "regulatory_clearance_certificate_issued": True,
        }
    ]
    res = audit_decommissioning_hazmat_manifest_and_site_remediation_clearance(records)
    assert res["status"] == "HEALTHY"
    assert res["evaluated_zones_count"] == 1
    assert res["critical_zones"] == []
    assert res["warning_zones"] == []
    assert res["overall_salvage_recovery_ratio"] == 0.9
    assert res["zone_evaluations"][0]["manifest_chain_custody_pct"] == 100.0
    assert res["zone_evaluations"][0]["contaminant_ppm_ratio"] == 0.4


def test_audit_decommissioning_hazmat_manifest_and_site_remediation_clearance_warning():
    from backend.services.project_lifecycle_pmi_service import (
        audit_decommissioning_hazmat_manifest_and_site_remediation_clearance,
    )

    records = [
        {
            "zone_id": "ZONE-LEAD-02",
            "hazmat_class": "lead",
            "disposal_manifests_completed": 8,
            "disposal_manifests_required": 8,
            "post_remediation_contaminant_ppm": 15.0,
            "regulatory_threshold_ppm": 50.0,
            "uncontained_spill_incident": False,
            "licensed_epa_tsdf_facility": True,
            "estimated_salvage_value": 100000.0,
            "realized_salvage_value": 65000.0,
            "regulatory_clearance_certificate_issued": False,
        }
    ]
    res = audit_decommissioning_hazmat_manifest_and_site_remediation_clearance(
        records, min_salvage_recovery_ratio=0.80
    )
    assert res["status"] == "WARNING"
    assert res["critical_zones"] == []
    assert res["warning_zones"] == ["ZONE-LEAD-02"]
    assert res["overall_salvage_recovery_ratio"] == 0.65
    assert res["zone_evaluations"][0]["clearance_or_salvage_warning"] is True


def test_audit_decommissioning_hazmat_manifest_and_site_remediation_clearance_critical():
    from backend.services.project_lifecycle_pmi_service import (
        audit_decommissioning_hazmat_manifest_and_site_remediation_clearance,
    )

    records = [
        {
            "zone_id": "ZONE-PCB-SPILL",
            "hazmat_class": "pcb",
            "disposal_manifests_completed": 7,
            "disposal_manifests_required": 10,
            "post_remediation_contaminant_ppm": 85.0,
            "regulatory_threshold_ppm": 50.0,
            "uncontained_spill_incident": True,
            "licensed_epa_tsdf_facility": False,
            "estimated_salvage_value": 20000.0,
            "realized_salvage_value": 18000.0,
            "regulatory_clearance_certificate_issued": False,
        }
    ]
    res = audit_decommissioning_hazmat_manifest_and_site_remediation_clearance(records)
    assert res["status"] == "CRITICAL"
    assert res["critical_zones"] == ["ZONE-PCB-SPILL"]
    assert res["warning_zones"] == []
    assert res["zone_evaluations"][0]["critical_hazmat_breach"] is True


def test_audit_decommissioning_hazmat_manifest_and_site_remediation_clearance_empty_and_binding():
    import backend.services.project_lifecycle_pmi_service as mod
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_decommissioning_hazmat_manifest_and_site_remediation_clearance,
    )

    empty = audit_decommissioning_hazmat_manifest_and_site_remediation_clearance([])
    assert empty["status"] == "HEALTHY"
    assert empty["evaluated_zones_count"] == 0
    assert empty["overall_salvage_recovery_ratio"] == 1.0
    assert (
        ProjectLifecyclePMIService.audit_decommissioning_hazmat_manifest_and_site_remediation_clearance(
            []
        )
        == empty
    )
    assert (
        "audit_decommissioning_hazmat_manifest_and_site_remediation_clearance"
        in mod.__all__
    )


def test_audit_joint_venture_consortium_liability_and_step_in_rights_healthy():
    from backend.services.project_lifecycle_pmi_service import (
        audit_joint_venture_consortium_liability_and_step_in_rights,
    )

    res = audit_joint_venture_consortium_liability_and_step_in_rights(
        [
            {
                "partner_id": "JV-LEAD-A",
                "equity_share_pct": 60.0,
                "capital_call_due_amount": 3000000.0,
                "capital_call_paid_amount": 3000000.0,
                "days_past_due_cash_call": 0,
                "insolvency_or_sanction_event": False,
                "cross_indemnity_agreement_signed": True,
                "step_in_assumption_capacity_verified": True,
            },
            {
                "partner_id": "JV-CO-B",
                "equity_share_pct": 40.0,
                "capital_call_due_amount": 2000000.0,
                "capital_call_paid_amount": 2000000.0,
                "days_past_due_cash_call": 0,
                "insolvency_or_sanction_event": False,
                "cross_indemnity_agreement_signed": True,
                "step_in_assumption_capacity_verified": True,
            },
        ]
    )
    assert res["status"] == "HEALTHY"
    assert res["evaluated_partners_count"] == 2
    assert res["total_equity_share_pct"] == 100.0
    assert res["equity_allocation_valid"] is True
    assert res["defaulting_partners"] == []
    assert res["warning_partners"] == []
    assert res["total_unfunded_cash_call_amount"] == 0.0


def test_audit_joint_venture_consortium_liability_and_step_in_rights_warning():
    from backend.services.project_lifecycle_pmi_service import (
        audit_joint_venture_consortium_liability_and_step_in_rights,
    )

    res = audit_joint_venture_consortium_liability_and_step_in_rights(
        [
            {
                "partner_id": "JV-LEAD-A",
                "equity_share_pct": 55.0,
                "capital_call_due_amount": 1000000.0,
                "capital_call_paid_amount": 900000.0,
                "days_past_due_cash_call": 10,
                "insolvency_or_sanction_event": False,
                "cross_indemnity_agreement_signed": True,
                "step_in_assumption_capacity_verified": True,
            },
            {
                "partner_id": "JV-CO-B",
                "equity_share_pct": 45.0,
                "capital_call_due_amount": 800000.0,
                "capital_call_paid_amount": 800000.0,
                "days_past_due_cash_call": 0,
                "insolvency_or_sanction_event": False,
                "cross_indemnity_agreement_signed": True,
                "step_in_assumption_capacity_verified": False,
            },
        ],
        steering_committee_deadlock_days=12,
    )
    assert res["status"] == "WARNING"
    assert res["equity_allocation_valid"] is True
    assert res["defaulting_partners"] == []
    assert res["warning_partners"] == ["JV-LEAD-A", "JV-CO-B"]
    assert res["total_unfunded_cash_call_amount"] == 100000.0


def test_audit_joint_venture_consortium_liability_and_step_in_rights_critical():
    from backend.services.project_lifecycle_pmi_service import (
        audit_joint_venture_consortium_liability_and_step_in_rights,
    )

    res = audit_joint_venture_consortium_liability_and_step_in_rights(
        [
            {
                "partner_id": "JV-INSOLVENT",
                "equity_share_pct": 50.0,
                "capital_call_due_amount": 1500000.0,
                "capital_call_paid_amount": 500000.0,
                "days_past_due_cash_call": 25,
                "insolvency_or_sanction_event": True,
                "cross_indemnity_agreement_signed": False,
                "step_in_assumption_capacity_verified": False,
            },
            {
                "partner_id": "JV-MINOR",
                "equity_share_pct": 30.0,
                "capital_call_due_amount": 900000.0,
                "capital_call_paid_amount": 900000.0,
                "days_past_due_cash_call": 0,
                "insolvency_or_sanction_event": False,
                "cross_indemnity_agreement_signed": True,
                "step_in_assumption_capacity_verified": True,
            },
        ],
        steering_committee_deadlock_days=35,
    )
    assert res["status"] == "CRITICAL"
    assert res["total_equity_share_pct"] == 80.0
    assert res["equity_allocation_valid"] is False
    assert res["defaulting_partners"] == ["JV-INSOLVENT"]
    assert res["total_unfunded_cash_call_amount"] == 1000000.0


def test_audit_joint_venture_consortium_liability_and_step_in_rights_empty_and_binding():
    import backend.services.project_lifecycle_pmi_service as mod
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_joint_venture_consortium_liability_and_step_in_rights,
    )

    empty = audit_joint_venture_consortium_liability_and_step_in_rights([])
    assert empty["status"] == "HEALTHY"
    assert empty["evaluated_partners_count"] == 0
    assert empty["total_equity_share_pct"] == 0.0
    assert empty["equity_allocation_valid"] is True
    assert empty["total_unfunded_cash_call_amount"] == 0.0
    assert (
        ProjectLifecyclePMIService.audit_joint_venture_consortium_liability_and_step_in_rights(
            []
        )
        == empty
    )
    assert (
        "audit_joint_venture_consortium_liability_and_step_in_rights"
        in mod.__all__
    )


def test_audit_ip_patent_assignment_chain_and_copyleft_contamination_healthy():
    from backend.services.project_lifecycle_pmi_service import (
        audit_ip_patent_assignment_chain_and_copyleft_contamination,
    )

    res = audit_ip_patent_assignment_chain_and_copyleft_contamination(
        [
            {
                "deliverable_id": "DELIV-CORE-SDK",
                "proprietary_distribution": True,
                "total_contributors": 12,
                "signed_ip_assignment_contributors": 12,
                "strong_copyleft_agpl_gpl_detected": False,
                "background_ip_license_documented": True,
                "third_party_notice_attribution_complete": True,
                "pending_patent_encumbrance_litigation": False,
            }
        ]
    )
    assert res["status"] == "HEALTHY"
    assert res["evaluated_deliverables_count"] == 1
    assert res["critical_deliverables"] == []
    assert res["warning_deliverables"] == []
    assert res["copyleft_contaminated_count"] == 0
    assert res["deliverable_evaluations"][0]["assignment_coverage_pct"] == 100.0


def test_audit_ip_patent_assignment_chain_and_copyleft_contamination_warning():
    from backend.services.project_lifecycle_pmi_service import (
        audit_ip_patent_assignment_chain_and_copyleft_contamination,
    )

    res = audit_ip_patent_assignment_chain_and_copyleft_contamination(
        [
            {
                "deliverable_id": "DELIV-UI-MODULE",
                "proprietary_distribution": True,
                "total_contributors": 8,
                "signed_ip_assignment_contributors": 8,
                "strong_copyleft_agpl_gpl_detected": False,
                "background_ip_license_documented": False,
                "third_party_notice_attribution_complete": False,
                "pending_patent_encumbrance_litigation": False,
            }
        ]
    )
    assert res["status"] == "WARNING"
    assert res["critical_deliverables"] == []
    assert res["warning_deliverables"] == ["DELIV-UI-MODULE"]
    assert res["copyleft_contaminated_count"] == 0
    assert res["deliverable_evaluations"][0]["ip_hygiene_warning"] is True


def test_audit_ip_patent_assignment_chain_and_copyleft_contamination_critical():
    from backend.services.project_lifecycle_pmi_service import (
        audit_ip_patent_assignment_chain_and_copyleft_contamination,
    )

    res = audit_ip_patent_assignment_chain_and_copyleft_contamination(
        [
            {
                "deliverable_id": "DELIV-AGPL-TAINTED",
                "proprietary_distribution": True,
                "total_contributors": 10,
                "signed_ip_assignment_contributors": 8,
                "strong_copyleft_agpl_gpl_detected": True,
                "background_ip_license_documented": True,
                "third_party_notice_attribution_complete": True,
                "pending_patent_encumbrance_litigation": True,
            }
        ]
    )
    assert res["status"] == "CRITICAL"
    assert res["critical_deliverables"] == ["DELIV-AGPL-TAINTED"]
    assert res["copyleft_contaminated_count"] == 1
    assert res["deliverable_evaluations"][0]["assignment_coverage_pct"] == 80.0
    assert res["deliverable_evaluations"][0]["critical_ip_breach"] is True


def test_audit_ip_patent_assignment_chain_and_copyleft_contamination_empty_and_binding():
    import backend.services.project_lifecycle_pmi_service as mod
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_ip_patent_assignment_chain_and_copyleft_contamination,
    )

    empty = audit_ip_patent_assignment_chain_and_copyleft_contamination([])
    assert empty["status"] == "HEALTHY"
    assert empty["evaluated_deliverables_count"] == 0
    assert empty["copyleft_contaminated_count"] == 0
    assert (
        ProjectLifecyclePMIService.audit_ip_patent_assignment_chain_and_copyleft_contamination(
            []
        )
        == empty
    )
    assert (
        "audit_ip_patent_assignment_chain_and_copyleft_contamination"
        in mod.__all__
    )


def test_audit_pir_hypercare_burn_in_and_bau_support_handover_healthy():
    from backend.services.project_lifecycle_pmi_service import (
        audit_pir_hypercare_burn_in_and_bau_support_handover,
    )

    res = audit_pir_hypercare_burn_in_and_bau_support_handover(
        [
            {
                "stream_id": "STREAM-ERP-FINANCE",
                "p1_p2_escaped_defects_open": 0,
                "kt_sessions_completed": 10,
                "kt_sessions_planned": 10,
                "consecutive_stable_burn_in_days": 21,
                "bau_ops_team_signoff_granted": True,
                "sla_breaches_during_hypercare": 0,
                "project_team_prematurely_demobilized": False,
            }
        ]
    )
    assert res["status"] == "HEALTHY"
    assert res["evaluated_streams_count"] == 1
    assert res["critical_streams"] == []
    assert res["warning_streams"] == []
    assert res["total_open_p1_p2_defects"] == 0
    assert res["stream_evaluations"][0]["kt_completion_pct"] == 100.0


def test_audit_pir_hypercare_burn_in_and_bau_support_handover_warning():
    from backend.services.project_lifecycle_pmi_service import (
        audit_pir_hypercare_burn_in_and_bau_support_handover,
    )

    res = audit_pir_hypercare_burn_in_and_bau_support_handover(
        [
            {
                "stream_id": "STREAM-CRM-PORTAL",
                "p1_p2_escaped_defects_open": 0,
                "kt_sessions_completed": 9,
                "kt_sessions_planned": 10,
                "consecutive_stable_burn_in_days": 10,
                "bau_ops_team_signoff_granted": True,
                "sla_breaches_during_hypercare": 2,
                "project_team_prematurely_demobilized": False,
            }
        ]
    )
    assert res["status"] == "WARNING"
    assert res["critical_streams"] == []
    assert res["warning_streams"] == ["STREAM-CRM-PORTAL"]
    assert res["stream_evaluations"][0]["kt_completion_pct"] == 90.0
    assert res["stream_evaluations"][0]["hypercare_warning"] is True


def test_audit_pir_hypercare_burn_in_and_bau_support_handover_critical():
    from backend.services.project_lifecycle_pmi_service import (
        audit_pir_hypercare_burn_in_and_bau_support_handover,
    )

    res = audit_pir_hypercare_burn_in_and_bau_support_handover(
        [
            {
                "stream_id": "STREAM-CORE-BILLING",
                "p1_p2_escaped_defects_open": 3,
                "kt_sessions_completed": 5,
                "kt_sessions_planned": 10,
                "consecutive_stable_burn_in_days": 4,
                "bau_ops_team_signoff_granted": False,
                "sla_breaches_during_hypercare": 5,
                "project_team_prematurely_demobilized": True,
            }
        ]
    )
    assert res["status"] == "CRITICAL"
    assert res["critical_streams"] == ["STREAM-CORE-BILLING"]
    assert res["total_open_p1_p2_defects"] == 3
    assert res["stream_evaluations"][0]["kt_completion_pct"] == 50.0
    assert res["stream_evaluations"][0]["critical_handover_breach"] is True


def test_audit_pir_hypercare_burn_in_and_bau_support_handover_empty_and_binding():
    import backend.services.project_lifecycle_pmi_service as mod
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_pir_hypercare_burn_in_and_bau_support_handover,
    )

    empty = audit_pir_hypercare_burn_in_and_bau_support_handover([])
    assert empty["status"] == "HEALTHY"
    assert empty["evaluated_streams_count"] == 0
    assert empty["total_open_p1_p2_defects"] == 0
    assert (
        ProjectLifecyclePMIService.audit_pir_hypercare_burn_in_and_bau_support_handover(
            []
        )
        == empty
    )
    assert (
        "audit_pir_hypercare_burn_in_and_bau_support_handover"
        in mod.__all__
    )


def test_audit_cross_border_customs_incoterms_and_export_control_compliance_healthy():
    from backend.services.project_lifecycle_pmi_service import (
        audit_cross_border_customs_incoterms_and_export_control_compliance,
    )

    res = audit_cross_border_customs_incoterms_and_export_control_compliance(
        [
            {
                "shipment_id": "SHIP-TURBINE-DDP-01",
                "incoterm_2020": "DDP",
                "hs_code_verified": True,
                "dual_use_eccn_or_itar_controlled": True,
                "export_license_granted": True,
                "sanctioned_entity_or_embargoed_port_hit": False,
                "port_demurrage_days": 2,
                "certificate_of_origin_attached": True,
                "customs_bond_active": True,
            }
        ]
    )
    assert res["status"] == "HEALTHY"
    assert res["evaluated_shipments_count"] == 1
    assert res["critical_shipments"] == []
    assert res["warning_shipments"] == []
    assert res["total_demurrage_days"] == 2
    assert res["shipment_evaluations"][0]["valid_incoterm"] is True


def test_audit_cross_border_customs_incoterms_and_export_control_compliance_warning():
    from backend.services.project_lifecycle_pmi_service import (
        audit_cross_border_customs_incoterms_and_export_control_compliance,
    )

    res = audit_cross_border_customs_incoterms_and_export_control_compliance(
        [
            {
                "shipment_id": "SHIP-CABLE-CIF-02",
                "incoterm_2020": "CIF",
                "hs_code_verified": True,
                "dual_use_eccn_or_itar_controlled": False,
                "export_license_granted": True,
                "sanctioned_entity_or_embargoed_port_hit": False,
                "port_demurrage_days": 8,
                "certificate_of_origin_attached": False,
                "customs_bond_active": True,
            }
        ]
    )
    assert res["status"] == "WARNING"
    assert res["critical_shipments"] == []
    assert res["warning_shipments"] == ["SHIP-CABLE-CIF-02"]
    assert res["total_demurrage_days"] == 8
    assert res["shipment_evaluations"][0]["trade_logistics_warning"] is True


def test_audit_cross_border_customs_incoterms_and_export_control_compliance_critical():
    from backend.services.project_lifecycle_pmi_service import (
        audit_cross_border_customs_incoterms_and_export_control_compliance,
    )

    res = audit_cross_border_customs_incoterms_and_export_control_compliance(
        [
            {
                "shipment_id": "SHIP-SANCTIONED-ITAR",
                "incoterm_2020": "DDU-LEGACY",
                "hs_code_verified": False,
                "dual_use_eccn_or_itar_controlled": True,
                "export_license_granted": False,
                "sanctioned_entity_or_embargoed_port_hit": True,
                "port_demurrage_days": 14,
                "certificate_of_origin_attached": False,
                "customs_bond_active": False,
            }
        ]
    )
    assert res["status"] == "CRITICAL"
    assert res["critical_shipments"] == ["SHIP-SANCTIONED-ITAR"]
    assert res["total_demurrage_days"] == 14
    assert res["shipment_evaluations"][0]["valid_incoterm"] is False
    assert res["shipment_evaluations"][0]["critical_trade_breach"] is True


def test_audit_cross_border_customs_incoterms_and_export_control_compliance_empty_and_binding():
    import backend.services.project_lifecycle_pmi_service as mod
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_cross_border_customs_incoterms_and_export_control_compliance,
    )

    empty = audit_cross_border_customs_incoterms_and_export_control_compliance([])
    assert empty["status"] == "HEALTHY"
    assert empty["evaluated_shipments_count"] == 0
    assert empty["total_demurrage_days"] == 0
    assert (
        ProjectLifecyclePMIService.audit_cross_border_customs_incoterms_and_export_control_compliance(
            []
        )
        == empty
    )
    assert (
        "audit_cross_border_customs_incoterms_and_export_control_compliance"
        in mod.__all__
    )


def test_audit_sovereign_political_risk_miga_insurance_and_arbitration_seat_healthy():
    from backend.services.project_lifecycle_pmi_service import (
        audit_sovereign_political_risk_miga_insurance_and_arbitration_seat,
    )

    res = audit_sovereign_political_risk_miga_insurance_and_arbitration_seat(
        [
            {
                "jurisdiction_id": "JUR-LATAM-PORT-CONCESSION",
                "capital_at_risk_amount": 50000000.0,
                "miga_pri_insured_amount": 47500000.0,
                "creeping_expropriation_or_nationalization_notice": False,
                "currency_inconvertibility_block_active": False,
                "fx_repatriation_delay_days": 7,
                "neutral_icsid_uncitral_arbitration_clause": True,
                "sovereign_immunity_waiver_signed": True,
                "stabilization_tax_clause_active": True,
            }
        ]
    )
    assert res["status"] == "HEALTHY"
    assert res["evaluated_jurisdictions_count"] == 1
    assert res["critical_jurisdictions"] == []
    assert res["warning_jurisdictions"] == []
    assert res["overall_pri_coverage_ratio"] == 0.95


def test_audit_sovereign_political_risk_miga_insurance_and_arbitration_seat_warning():
    from backend.services.project_lifecycle_pmi_service import (
        audit_sovereign_political_risk_miga_insurance_and_arbitration_seat,
    )

    res = audit_sovereign_political_risk_miga_insurance_and_arbitration_seat(
        [
            {
                "jurisdiction_id": "JUR-SOLAR-IPP-FX-DELAY",
                "capital_at_risk_amount": 20000000.0,
                "miga_pri_insured_amount": 18500000.0,
                "creeping_expropriation_or_nationalization_notice": False,
                "currency_inconvertibility_block_active": False,
                "fx_repatriation_delay_days": 45,
                "neutral_icsid_uncitral_arbitration_clause": True,
                "sovereign_immunity_waiver_signed": True,
                "stabilization_tax_clause_active": False,
            }
        ]
    )
    assert res["status"] == "WARNING"
    assert res["critical_jurisdictions"] == []
    assert res["warning_jurisdictions"] == ["JUR-SOLAR-IPP-FX-DELAY"]
    assert res["overall_pri_coverage_ratio"] == 0.925


def test_audit_sovereign_political_risk_miga_insurance_and_arbitration_seat_critical():
    from backend.services.project_lifecycle_pmi_service import (
        audit_sovereign_political_risk_miga_insurance_and_arbitration_seat,
    )

    res = audit_sovereign_political_risk_miga_insurance_and_arbitration_seat(
        [
            {
                "jurisdiction_id": "JUR-EXPROPRIATION-RISK",
                "capital_at_risk_amount": 40000000.0,
                "miga_pri_insured_amount": 20000000.0,
                "creeping_expropriation_or_nationalization_notice": True,
                "currency_inconvertibility_block_active": True,
                "fx_repatriation_delay_days": 90,
                "neutral_icsid_uncitral_arbitration_clause": False,
                "sovereign_immunity_waiver_signed": False,
                "stabilization_tax_clause_active": False,
            }
        ]
    )
    assert res["status"] == "CRITICAL"
    assert res["critical_jurisdictions"] == ["JUR-EXPROPRIATION-RISK"]
    assert res["overall_pri_coverage_ratio"] == 0.5
    assert res["jurisdiction_evaluations"][0]["critical_sovereign_breach"] is True


def test_audit_sovereign_political_risk_miga_insurance_and_arbitration_seat_empty_and_binding():
    import backend.services.project_lifecycle_pmi_service as mod
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_sovereign_political_risk_miga_insurance_and_arbitration_seat,
    )

    empty = audit_sovereign_political_risk_miga_insurance_and_arbitration_seat([])
    assert empty["status"] == "HEALTHY"
    assert empty["evaluated_jurisdictions_count"] == 0
    assert empty["overall_pri_coverage_ratio"] == 1.0
    assert (
        ProjectLifecyclePMIService.audit_sovereign_political_risk_miga_insurance_and_arbitration_seat(
            []
        )
        == empty
    )
    assert (
        "audit_sovereign_political_risk_miga_insurance_and_arbitration_seat"
        in mod.__all__
    )


def test_audit_epc_performance_guarantee_capacity_test_and_minimum_acceptance_healthy():
    from backend.services.project_lifecycle_pmi_service import (
        audit_epc_performance_guarantee_capacity_test_and_minimum_acceptance,
    )

    res = audit_epc_performance_guarantee_capacity_test_and_minimum_acceptance(
        [
            {
                "unit_id": "TURBINE-CCGT-BLOCK-01",
                "measured_net_output_pct": 100.8,
                "measured_heat_rate_efficiency_ok": True,
                "emissions_nox_sox_within_permit": True,
                "continuous_reliability_run_hours": 72,
                "required_reliability_run_hours": 72,
                "accrued_performance_ld_pct_of_contract": 0.0,
            }
        ]
    )
    assert res["status"] == "HEALTHY"
    assert res["evaluated_units_count"] == 1
    assert res["critical_units"] == []
    assert res["warning_units"] == []
    assert res["min_observed_output_pct"] == 100.8
    assert res["unit_evaluations"][0]["below_minimum_rejection_floor"] is False


def test_audit_epc_performance_guarantee_capacity_test_and_minimum_acceptance_warning():
    from backend.services.project_lifecycle_pmi_service import (
        audit_epc_performance_guarantee_capacity_test_and_minimum_acceptance,
    )

    res = audit_epc_performance_guarantee_capacity_test_and_minimum_acceptance(
        [
            {
                "unit_id": "SOLAR-BESS-INVERTER-02",
                "measured_net_output_pct": 97.4,
                "measured_heat_rate_efficiency_ok": False,
                "emissions_nox_sox_within_permit": True,
                "continuous_reliability_run_hours": 72,
                "required_reliability_run_hours": 72,
                "accrued_performance_ld_pct_of_contract": 4.5,
            }
        ]
    )
    assert res["status"] == "WARNING"
    assert res["critical_units"] == []
    assert res["warning_units"] == ["SOLAR-BESS-INVERTER-02"]
    assert res["min_observed_output_pct"] == 97.4
    assert (
        res["unit_evaluations"][0]["below_guaranteed_but_acceptable"] is True
    )
    assert res["unit_evaluations"][0]["epc_performance_ld_warning"] is True


def test_audit_epc_performance_guarantee_capacity_test_and_minimum_acceptance_critical():
    from backend.services.project_lifecycle_pmi_service import (
        audit_epc_performance_guarantee_capacity_test_and_minimum_acceptance,
    )

    res = audit_epc_performance_guarantee_capacity_test_and_minimum_acceptance(
        [
            {
                "unit_id": "BOILER-DESAL-UNIT-03",
                "measured_net_output_pct": 89.2,
                "measured_heat_rate_efficiency_ok": False,
                "emissions_nox_sox_within_permit": False,
                "continuous_reliability_run_hours": 36,
                "required_reliability_run_hours": 72,
                "accrued_performance_ld_pct_of_contract": 18.0,
            }
        ]
    )
    assert res["status"] == "CRITICAL"
    assert res["critical_units"] == ["BOILER-DESAL-UNIT-03"]
    assert res["warning_units"] == []
    assert res["min_observed_output_pct"] == 89.2
    assert res["unit_evaluations"][0]["below_minimum_rejection_floor"] is True
    assert res["unit_evaluations"][0]["critical_epc_breach"] is True


def test_audit_epc_performance_guarantee_capacity_test_and_minimum_acceptance_empty_and_binding():
    import backend.services.project_lifecycle_pmi_service as mod
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_epc_performance_guarantee_capacity_test_and_minimum_acceptance,
    )

    empty = audit_epc_performance_guarantee_capacity_test_and_minimum_acceptance(
        []
    )
    assert empty["status"] == "HEALTHY"
    assert empty["evaluated_units_count"] == 0
    assert empty["min_observed_output_pct"] == 100.0
    assert (
        ProjectLifecyclePMIService.audit_epc_performance_guarantee_capacity_test_and_minimum_acceptance(
            []
        )
        == empty
    )
    assert (
        "audit_epc_performance_guarantee_capacity_test_and_minimum_acceptance"
        in mod.__all__
    )


def test_audit_spv_project_finance_dscr_llcr_covenant_and_equity_lockup_healthy():
    from backend.services.project_lifecycle_pmi_service import (
        audit_spv_project_finance_dscr_llcr_covenant_and_equity_lockup,
    )

    tranches = [
        {
            "tranche_id": "SPV-SENIOR-TERM-A",
            "cfads_amount": 14500000.0,
            "scheduled_debt_service_amount": 10000000.0,
            "npv_future_cfads": 150000000.0,
            "outstanding_senior_debt": 100000000.0,
            "dsra_funded_months": 6.0,
            "required_dsra_months": 6.0,
            "equity_dividend_distributed_during_lockup": False,
        },
        {
            "tranche_id": "SPV-SENIOR-TERM-B",
            "cfads_amount": 6600000.0,
            "scheduled_debt_service_amount": 5000000.0,
            "npv_future_cfads": 70000000.0,
            "outstanding_senior_debt": 50000000.0,
            "dsra_funded_months": 6.0,
            "required_dsra_months": 6.0,
            "equity_dividend_distributed_during_lockup": False,
        },
    ]
    res = audit_spv_project_finance_dscr_llcr_covenant_and_equity_lockup(tranches)
    assert res["status"] == "healthy"
    assert res["total_tranches"] == 2
    assert res["healthy_count"] == 2
    assert res["warning_count"] == 0
    assert res["critical_count"] == 0
    assert res["covenant_compliance_rate_pct"] == 100.0
    assert res["recommendations"] == []


def test_audit_spv_project_finance_dscr_llcr_covenant_and_equity_lockup_warning():
    from backend.services.project_lifecycle_pmi_service import (
        audit_spv_project_finance_dscr_llcr_covenant_and_equity_lockup,
    )

    tranches = [
        {
            "tranche_id": "SPV-SOLAR-LOCKUP-TRANCHE",
            "cfads_amount": 11200000.0,
            "scheduled_debt_service_amount": 10000000.0,
            "npv_future_cfads": 125000000.0,
            "outstanding_senior_debt": 100000000.0,
            "dsra_funded_months": 4.5,
            "required_dsra_months": 6.0,
            "equity_dividend_distributed_during_lockup": False,
        }
    ]
    res = audit_spv_project_finance_dscr_llcr_covenant_and_equity_lockup(tranches)
    assert res["status"] == "warning"
    assert res["total_tranches"] == 1
    assert res["warning_count"] == 1
    assert res["critical_count"] == 0
    assert res["lockup_triggered_count"] == 1
    assert res["illegal_dividend_leakage_count"] == 0
    assert res["tranches"][0]["dscr_ratio"] == 1.12
    assert res["tranches"][0]["llcr_ratio"] == 1.25
    assert res["tranches"][0]["tranche_status"] == "warning"
    assert len(res["recommendations"]) >= 1


def test_audit_spv_project_finance_dscr_llcr_covenant_and_equity_lockup_critical():
    from backend.services.project_lifecycle_pmi_service import (
        audit_spv_project_finance_dscr_llcr_covenant_and_equity_lockup,
    )

    tranches = [
        {
            "tranche_id": "SPV-TOLLROAD-DEFAULT-LEAK",
            "cfads_amount": 9800000.0,
            "scheduled_debt_service_amount": 10000000.0,
            "npv_future_cfads": 110000000.0,
            "outstanding_senior_debt": 100000000.0,
            "dsra_funded_months": 2.0,
            "required_dsra_months": 6.0,
            "equity_dividend_distributed_during_lockup": True,
        }
    ]
    res = audit_spv_project_finance_dscr_llcr_covenant_and_equity_lockup(tranches)
    assert res["status"] == "critical"
    assert res["total_tranches"] == 1
    assert res["critical_count"] == 1
    assert res["default_dscr_breach_count"] == 1
    assert res["lockup_triggered_count"] == 1
    assert res["illegal_dividend_leakage_count"] == 1
    assert res["covenant_compliance_rate_pct"] == 0.0
    assert res["tranches"][0]["tranche_status"] == "critical"
    assert len(res["recommendations"]) >= 2


def test_audit_spv_project_finance_dscr_llcr_covenant_and_equity_lockup_empty_and_binding():
    import backend.services.project_lifecycle_pmi_service as mod
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_spv_project_finance_dscr_llcr_covenant_and_equity_lockup,
    )

    empty = audit_spv_project_finance_dscr_llcr_covenant_and_equity_lockup([])
    assert empty["status"] == "healthy"
    assert empty["total_tranches"] == 0
    assert empty["covenant_compliance_rate_pct"] == 100.0
    assert (
        ProjectLifecyclePMIService.audit_spv_project_finance_dscr_llcr_covenant_and_equity_lockup(
            []
        )
        == empty
    )
    assert (
        "audit_spv_project_finance_dscr_llcr_covenant_and_equity_lockup"
        in mod.__all__
    )


def test_audit_ppp_concession_availability_payment_and_handback_residual_life_healthy():
    from backend.services.project_lifecycle_pmi_service import (
        audit_ppp_concession_availability_payment_and_handback_residual_life,
    )

    assets = [
        {
            "asset_id": "PPP-HIGHWAY-CORRIDOR-01",
            "gross_availability_payment_usd": 5000000.0,
            "sla_unavailability_deduction_usd": 150000.0,
            "inspected_residual_life_at_handback_years": 8.5,
            "handback_escrow_reserve_funded": True,
            "concessionaire_default_termination_threshold_pct": 25.0,
        },
        {
            "asset_id": "PPP-HOSPITAL-WING-02",
            "gross_availability_payment_usd": 3000000.0,
            "sla_unavailability_deduction_usd": 60000.0,
            "inspected_residual_life_at_handback_years": 12.0,
            "handback_escrow_reserve_funded": True,
            "concessionaire_default_termination_threshold_pct": 25.0,
        },
    ]
    res = audit_ppp_concession_availability_payment_and_handback_residual_life(
        assets
    )
    assert res["status"] == "healthy"
    assert res["total_assets"] == 2
    assert res["healthy_count"] == 2
    assert res["warning_count"] == 0
    assert res["critical_count"] == 0
    assert res["ppp_compliance_rate_pct"] == 100.0
    assert res["recommendations"] == []


def test_audit_ppp_concession_availability_payment_and_handback_residual_life_warning():
    from backend.services.project_lifecycle_pmi_service import (
        audit_ppp_concession_availability_payment_and_handback_residual_life,
    )

    assets = [
        {
            "asset_id": "PPP-BRIDGE-DECK-03",
            "gross_availability_payment_usd": 4000000.0,
            "sla_unavailability_deduction_usd": 720000.0,
            "inspected_residual_life_at_handback_years": 3.5,
            "handback_escrow_reserve_funded": True,
            "concessionaire_default_termination_threshold_pct": 25.0,
        }
    ]
    res = audit_ppp_concession_availability_payment_and_handback_residual_life(
        assets
    )
    assert res["status"] == "warning"
    assert res["total_assets"] == 1
    assert res["warning_count"] == 1
    assert res["critical_count"] == 0
    assert res["excessive_deduction_count"] == 1
    assert res["handback_shortfall_count"] == 1
    assert res["unfunded_handback_count"] == 0
    assert res["assets"][0]["deduction_penalty_pct"] == 18.0
    assert res["assets"][0]["asset_status"] == "warning"
    assert len(res["recommendations"]) >= 2


def test_audit_ppp_concession_availability_payment_and_handback_residual_life_critical():
    from backend.services.project_lifecycle_pmi_service import (
        audit_ppp_concession_availability_payment_and_handback_residual_life,
    )

    assets = [
        {
            "asset_id": "PPP-TUNNEL-VENT-DEFAULT",
            "gross_availability_payment_usd": 2000000.0,
            "sla_unavailability_deduction_usd": 600000.0,
            "inspected_residual_life_at_handback_years": 2.0,
            "handback_escrow_reserve_funded": False,
            "concessionaire_default_termination_threshold_pct": 25.0,
        }
    ]
    res = audit_ppp_concession_availability_payment_and_handback_residual_life(
        assets
    )
    assert res["status"] == "critical"
    assert res["total_assets"] == 1
    assert res["critical_count"] == 1
    assert res["default_threshold_breach_count"] == 1
    assert res["unfunded_handback_count"] == 1
    assert res["ppp_compliance_rate_pct"] == 0.0
    assert res["assets"][0]["asset_status"] == "critical"
    assert len(res["recommendations"]) >= 2


def test_audit_ppp_concession_availability_payment_and_handback_residual_life_empty_and_binding():
    import backend.services.project_lifecycle_pmi_service as mod
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_ppp_concession_availability_payment_and_handback_residual_life,
    )

    empty = (
        audit_ppp_concession_availability_payment_and_handback_residual_life([])
    )
    assert empty["status"] == "healthy"
    assert empty["total_assets"] == 0
    assert empty["ppp_compliance_rate_pct"] == 100.0
    assert (
        ProjectLifecyclePMIService.audit_ppp_concession_availability_payment_and_handback_residual_life(
            []
        )
        == empty
    )
    assert (
        "audit_ppp_concession_availability_payment_and_handback_residual_life"
        in mod.__all__
    )


def test_audit_esg_scope_emissions_cap_and_green_bond_proceeds_healthy():
    from backend.services.project_lifecycle_pmi_service import (
        audit_esg_scope_emissions_cap_and_green_bond_proceeds,
    )

    packages = [
        {
            "package_id": "WP-SOLAR-ROOFTOP-01",
            "baseline_tco2e": 500.0,
            "actual_tco2e": 520.0,
            "retired_verified_carbon_offsets_tco2e": 10.0,
            "green_taxonomy_aligned_spend_pct": 96.5,
            "third_party_esg_assurance_verified": True,
            "fossil_fuel_exclusion_violated": False,
        },
        {
            "package_id": "WP-LOW-CARBON-CONCRETE-02",
            "baseline_tco2e": 1000.0,
            "actual_tco2e": 980.0,
            "retired_verified_carbon_offsets_tco2e": 0.0,
            "green_taxonomy_aligned_spend_pct": 92.0,
            "third_party_esg_assurance_verified": True,
            "fossil_fuel_exclusion_violated": False,
        },
    ]
    res = audit_esg_scope_emissions_cap_and_green_bond_proceeds(packages)
    assert res["status"] == "healthy"
    assert res["total_packages"] == 2
    assert res["healthy_count"] == 2
    assert res["warning_count"] == 0
    assert res["critical_count"] == 0
    assert res["esg_compliance_rate_pct"] == 100.0
    assert res["recommendations"] == []


def test_audit_esg_scope_emissions_cap_and_green_bond_proceeds_warning():
    from backend.services.project_lifecycle_pmi_service import (
        audit_esg_scope_emissions_cap_and_green_bond_proceeds,
    )

    packages = [
        {
            "package_id": "WP-STEEL-FOUNDATION-03",
            "baseline_tco2e": 400.0,
            "actual_tco2e": 480.0,
            "retired_verified_carbon_offsets_tco2e": 0.0,
            "green_taxonomy_aligned_spend_pct": 95.0,
            "third_party_esg_assurance_verified": True,
            "fossil_fuel_exclusion_violated": False,
        }
    ]
    res = audit_esg_scope_emissions_cap_and_green_bond_proceeds(packages)
    assert res["status"] == "warning"
    assert res["total_packages"] == 1
    assert res["warning_count"] == 1
    assert res["critical_count"] == 0
    assert res["carbon_cap_breach_count"] == 1
    assert res["taxonomy_shortfall_count"] == 0
    assert res["packages"][0]["carbon_overrun_pct"] == 20.0
    assert res["packages"][0]["package_status"] == "warning"
    assert len(res["recommendations"]) >= 1


def test_audit_esg_scope_emissions_cap_and_green_bond_proceeds_critical():
    from backend.services.project_lifecycle_pmi_service import (
        audit_esg_scope_emissions_cap_and_green_bond_proceeds,
    )

    packages = [
        {
            "package_id": "WP-DIESEL-GENSET-GREENWASH",
            "baseline_tco2e": 300.0,
            "actual_tco2e": 450.0,
            "retired_verified_carbon_offsets_tco2e": 50.0,
            "green_taxonomy_aligned_spend_pct": 60.0,
            "third_party_esg_assurance_verified": False,
            "fossil_fuel_exclusion_violated": True,
        }
    ]
    res = audit_esg_scope_emissions_cap_and_green_bond_proceeds(packages)
    assert res["status"] == "critical"
    assert res["total_packages"] == 1
    assert res["critical_count"] == 1
    assert res["greenwashing_breach_count"] == 1
    assert res["carbon_cap_breach_count"] == 1
    assert res["taxonomy_shortfall_count"] == 1
    assert res["esg_compliance_rate_pct"] == 0.0
    assert res["packages"][0]["package_status"] == "critical"
    assert len(res["recommendations"]) >= 2


def test_audit_esg_scope_emissions_cap_and_green_bond_proceeds_empty_and_binding():
    import backend.services.project_lifecycle_pmi_service as mod
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_esg_scope_emissions_cap_and_green_bond_proceeds,
    )

    empty = audit_esg_scope_emissions_cap_and_green_bond_proceeds([])
    assert empty["status"] == "healthy"
    assert empty["total_packages"] == 0
    assert empty["esg_compliance_rate_pct"] == 100.0
    assert (
        ProjectLifecyclePMIService.audit_esg_scope_emissions_cap_and_green_bond_proceeds(
            []
        )
        == empty
    )
    assert (
        "audit_esg_scope_emissions_cap_and_green_bond_proceeds"
        in mod.__all__
    )


def test_audit_safety_critical_nqa1_hold_point_and_cfsi_quarantine_healthy():
    from backend.services.project_lifecycle_pmi_service import (
        audit_safety_critical_nqa1_hold_point_and_cfsi_quarantine,
    )

    inspections = [
        {
            "inspection_id": "nqa1-weld-vessel-01",
            "mandatory_hold_point_bypassed": False,
            "independent_ani_witness_signed": True,
            "cfsi_suspect_part_detected": False,
            "cfsi_segregated_in_quarantine": True,
            "open_ncr_age_days": 5,
            "material_traceability_mtr_verified": True,
        },
        {
            "inspection_id": "nqa1-valve-hydro-02",
            "mandatory_hold_point_bypassed": False,
            "independent_ani_witness_signed": True,
            "cfsi_suspect_part_detected": False,
            "cfsi_segregated_in_quarantine": True,
            "open_ncr_age_days": 12,
            "material_traceability_mtr_verified": True,
        },
    ]
    res = audit_safety_critical_nqa1_hold_point_and_cfsi_quarantine(inspections)
    assert res["status"] == "healthy"
    assert res["total_inspections"] == 2
    assert res["healthy_count"] == 2
    assert res["warning_count"] == 0
    assert res["critical_count"] == 0
    assert res["nqa1_compliance_rate_pct"] == 100.0
    assert res["recommendations"] == []


def test_audit_safety_critical_nqa1_hold_point_and_cfsi_quarantine_warning():
    from backend.services.project_lifecycle_pmi_service import (
        audit_safety_critical_nqa1_hold_point_and_cfsi_quarantine,
    )

    inspections = [
        {
            "inspection_id": "nqa1-fastener-lot-09",
            "mandatory_hold_point_bypassed": False,
            "independent_ani_witness_signed": True,
            "cfsi_suspect_part_detected": True,
            "cfsi_segregated_in_quarantine": True,
            "open_ncr_age_days": 45,
            "material_traceability_mtr_verified": True,
        }
    ]
    res = audit_safety_critical_nqa1_hold_point_and_cfsi_quarantine(inspections)
    assert res["status"] == "warning"
    assert res["total_inspections"] == 1
    assert res["warning_count"] == 1
    assert res["critical_count"] == 0
    assert res["overdue_ncr_count"] == 1
    assert res["inspections"][0]["inspection_status"] == "warning"
    assert len(res["recommendations"]) >= 1


def test_audit_safety_critical_nqa1_hold_point_and_cfsi_quarantine_critical():
    from backend.services.project_lifecycle_pmi_service import (
        audit_safety_critical_nqa1_hold_point_and_cfsi_quarantine,
    )

    inspections = [
        {
            "inspection_id": "nqa1-containment-flange-99",
            "mandatory_hold_point_bypassed": True,
            "independent_ani_witness_signed": False,
            "cfsi_suspect_part_detected": True,
            "cfsi_segregated_in_quarantine": False,
            "open_ncr_age_days": 60,
            "material_traceability_mtr_verified": False,
        }
    ]
    res = audit_safety_critical_nqa1_hold_point_and_cfsi_quarantine(inspections)
    assert res["status"] == "critical"
    assert res["total_inspections"] == 1
    assert res["critical_count"] == 1
    assert res["hold_point_violation_count"] == 1
    assert res["unquarantined_cfsi_count"] == 1
    assert res["missing_mtr_count"] == 1
    assert res["nqa1_compliance_rate_pct"] == 0.0
    assert res["inspections"][0]["inspection_status"] == "critical"
    assert len(res["recommendations"]) >= 3


def test_audit_safety_critical_nqa1_hold_point_and_cfsi_quarantine_empty_and_binding():
    import backend.services.project_lifecycle_pmi_service as mod
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_safety_critical_nqa1_hold_point_and_cfsi_quarantine,
    )

    empty = audit_safety_critical_nqa1_hold_point_and_cfsi_quarantine([])
    assert empty["status"] == "healthy"
    assert empty["total_inspections"] == 0
    assert empty["nqa1_compliance_rate_pct"] == 100.0
    assert (
        ProjectLifecyclePMIService.audit_safety_critical_nqa1_hold_point_and_cfsi_quarantine(
            []
        )
        == empty
    )
    assert (
        "audit_safety_critical_nqa1_hold_point_and_cfsi_quarantine"
        in mod.__all__
    )


def test_audit_ma_post_merger_tsa_exit_and_synergy_realization_healthy():
    from backend.services.project_lifecycle_pmi_service import (
        audit_ma_post_merger_tsa_exit_and_synergy_realization,
    )

    workstreams = [
        {
            "workstream_id": "ma-ws-erp-consolidation",
            "target_run_rate_synergy_usd": 500000.0,
            "realized_run_rate_synergy_usd": 475000.0,
            "tsa_extension_months": 1,
            "tsa_holdover_penalty_active": False,
            "day1_legal_entity_cutover_ready": True,
            "key_talent_retention_breach": False,
        },
        {
            "workstream_id": "ma-ws-cloud-procurement",
            "target_run_rate_synergy_usd": 300000.0,
            "realized_run_rate_synergy_usd": 290000.0,
            "tsa_extension_months": 0,
            "tsa_holdover_penalty_active": False,
            "day1_legal_entity_cutover_ready": True,
            "key_talent_retention_breach": False,
        },
    ]
    res = audit_ma_post_merger_tsa_exit_and_synergy_realization(workstreams)
    assert res["status"] == "healthy"
    assert res["total_workstreams"] == 2
    assert res["healthy_count"] == 2
    assert res["warning_count"] == 0
    assert res["critical_count"] == 0
    assert res["ma_integration_rate_pct"] == 100.0
    assert res["recommendations"] == []


def test_audit_ma_post_merger_tsa_exit_and_synergy_realization_warning():
    from backend.services.project_lifecycle_pmi_service import (
        audit_ma_post_merger_tsa_exit_and_synergy_realization,
    )

    workstreams = [
        {
            "workstream_id": "ma-ws-hris-payroll",
            "target_run_rate_synergy_usd": 200000.0,
            "realized_run_rate_synergy_usd": 140000.0,
            "tsa_extension_months": 5,
            "tsa_holdover_penalty_active": False,
            "day1_legal_entity_cutover_ready": True,
            "key_talent_retention_breach": False,
        }
    ]
    res = audit_ma_post_merger_tsa_exit_and_synergy_realization(workstreams)
    assert res["status"] == "warning"
    assert res["total_workstreams"] == 1
    assert res["warning_count"] == 1
    assert res["critical_count"] == 0
    assert res["synergy_shortfall_count"] == 1
    assert res["tsa_extension_exceeded_count"] == 1
    assert res["workstreams"][0]["workstream_status"] == "warning"
    assert len(res["recommendations"]) >= 2


def test_audit_ma_post_merger_tsa_exit_and_synergy_realization_critical():
    from backend.services.project_lifecycle_pmi_service import (
        audit_ma_post_merger_tsa_exit_and_synergy_realization,
    )

    workstreams = [
        {
            "workstream_id": "ma-ws-treasury-carveout",
            "target_run_rate_synergy_usd": 400000.0,
            "realized_run_rate_synergy_usd": 180000.0,
            "tsa_extension_months": 6,
            "tsa_holdover_penalty_active": True,
            "day1_legal_entity_cutover_ready": False,
            "key_talent_retention_breach": True,
        }
    ]
    res = audit_ma_post_merger_tsa_exit_and_synergy_realization(workstreams)
    assert res["status"] == "critical"
    assert res["total_workstreams"] == 1
    assert res["critical_count"] == 1
    assert res["day1_or_holdover_crisis_count"] == 1
    assert res["synergy_shortfall_count"] == 1
    assert res["talent_retention_breach_count"] == 1
    assert res["ma_integration_rate_pct"] == 0.0
    assert res["workstreams"][0]["workstream_status"] == "critical"
    assert len(res["recommendations"]) >= 3


def test_audit_ma_post_merger_tsa_exit_and_synergy_realization_empty_and_binding():
    import backend.services.project_lifecycle_pmi_service as mod
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_ma_post_merger_tsa_exit_and_synergy_realization,
    )

    empty = audit_ma_post_merger_tsa_exit_and_synergy_realization([])
    assert empty["status"] == "healthy"
    assert empty["total_workstreams"] == 0
    assert empty["ma_integration_rate_pct"] == 100.0
    assert (
        ProjectLifecyclePMIService.audit_ma_post_merger_tsa_exit_and_synergy_realization(
            []
        )
        == empty
    )
    assert (
        "audit_ma_post_merger_tsa_exit_and_synergy_realization"
        in mod.__all__
    )


def test_t4c_settlement_clean_case():
    """Sin costos indirectos ni excepciones -> 'T4C_SETTLEMENT_CLEAN_UNDER_FAR_52_249_2'."""
    import backend.services.project_lifecycle_pmi_service as lse_module
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_contract_termination_for_convenience_t4c_settlement_and_demobilization,
    )

    res = audit_contract_termination_for_convenience_t4c_settlement_and_demobilization(
        100000.0,   # obra ejecutada
        0.0,        # no recuperables
        0.0,        # subcontratistas
        0.0,        # desmovilización
    )
    assert res == {
        "gross_completed_work_value": 110000.0,
        "unrecoverable_direct_costs": 0.0,
        "subcontractor_cancellation_settlements": 0.0,
        "demobilization_expenses": 0.0,
        "profit_percentage_on_completed_work": 10.0,
        "advance_payments_received": 0.0,
        "max_contract_ceiling_value": None,
        "total_settlement_amount": 110000.0,
        "net_settlement_after_advance_deduction": 110000.0,
        "settlement_payable_within_ceiling": 110000.0,
        "settlement_beyond_contract_ceiling_amount": 0.0,
        "settlement_audit_exception_breach": False,
        "indirect_settlement_components_present": False,
        "settlement_audit_status": "T4C_SETTLEMENT_CLEAN_UNDER_FAR_52_249_2",
        "is_t4c_settlement_audited": True,
    }
    assert (
        ProjectLifecyclePMIService
        .audit_contract_termination_for_convenience_t4c_settlement_and_demobilization
        is not None
    )
    assert (
        "audit_contract_termination_for_convenience_t4c_settlement_and_demobilization"
        in lse_module.__all__
    )


def test_t4c_settlement_subcontractor_and_demobilization_warning():
    """Liquidaciones de subcontratistas o desmovilización > 0 sin techo ni flag -> WARNING."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_contract_termination_for_convenience_t4c_settlement_and_demobilization,
    )

    res = audit_contract_termination_for_convenience_t4c_settlement_and_demobilization(
        200000.0,       # obra ejecutada
        15000.0,        # no recuperables
        40000.0,        # liquidaciones de subcontratistas
        25000.0,        # desmovilización
        profit_percentage_on_completed_work=10.0,
        advance_payments_received=30000.0,
    )
    # gross = 200000 * 1.10 = 220000; total = 220000 + 15000 + 40000 + 25000 = 300000;
    # net = 300000 - 30000 = 270000.
    assert res["gross_completed_work_value"] == 220000.0
    assert res["total_settlement_amount"] == 300000.0
    assert res["net_settlement_after_advance_deduction"] == 270000.0
    assert res["settlement_audit_exception_breach"] is False
    assert res["indirect_settlement_components_present"] is True
    assert res["settlement_audit_status"] == "T4C_SUBCONTRACTOR_AND_DEMOBILIZATION_SETTLEMENT_WARNING"
    assert res["is_t4c_settlement_audited"] is False


def test_t4c_settlement_critical_ceiling_and_exception_flag():
    """Techo excedido o flag de excepciones -> CRITICAL con precedencia."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_contract_termination_for_convenience_t4c_settlement_and_demobilization,
    )

    # Techo contractual 250000 < net 270000 -> exceso 20000 -> CRITICAL.
    over_ceiling = audit_contract_termination_for_convenience_t4c_settlement_and_demobilization(
        200000.0, 15000.0, 40000.0, 25000.0,
        advance_payments_received=30000.0,
        max_contract_ceiling_value=250000.0,
    )
    assert over_ceiling["settlement_payable_within_ceiling"] == 250000.0
    assert over_ceiling["settlement_beyond_contract_ceiling_amount"] == 20000.0
    assert over_ceiling["settlement_audit_exception_breach"] is True
    assert over_ceiling["settlement_audit_status"] == "CRITICAL_T4C_SETTLEMENT_AUDIT_EXCEPTION_OR_CEILING_BREACH"

    # Flag de excepciones activa fuerza CRITICAL incluso sin exceso de techo.
    flagged = audit_contract_termination_for_convenience_t4c_settlement_and_demobilization(
        100000.0, 0.0, 0.0, 0.0,
        settlement_audit_exceptions_flag=True,
    )
    assert flagged["settlement_audit_exception_breach"] is True
    assert flagged["settlement_audit_status"] == "CRITICAL_T4C_SETTLEMENT_AUDIT_EXCEPTION_OR_CEILING_BREACH"


def test_t4c_settlement_field_coercion_and_zero_advance_loss():
    """Negativos e inválidos se clamp a 0.0; bools revierten a defaults; anticipos nunca producen pago negativo."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_contract_termination_for_convenience_t4c_settlement_and_demobilization,
    )

    # Anticipo 500000 > total 110000 -> net floor 0.0, sin estado adverso.
    overpaid = audit_contract_termination_for_convenience_t4c_settlement_and_demobilization(
        100000.0, 0.0, 0.0, 0.0,
        advance_payments_received=500000.0,
    )
    assert overpaid["net_settlement_after_advance_deduction"] == 0.0
    assert overpaid["settlement_payable_within_ceiling"] == 0.0
    assert overpaid["settlement_audit_status"] == "T4C_SETTLEMENT_CLEAN_UNDER_FAR_52_249_2"

    # Coerción completa: negativos -> 0.0, bools excluidos, tipos inválidos a defaults.
    coerced = audit_contract_termination_for_convenience_t4c_settlement_and_demobilization(
        -100000.0,          # no-float/precio negativo -> 0.0
        " debts",           # no-float -> 0.0
        True,               # bool excluido -> 0.0
        None,               # no-float -> 0.0
        profit_percentage_on_completed_work=-5.0,     # negativo -> default 10.0
        advance_payments_received="advance",           # no-float -> 0.0
        max_contract_ceiling_value="ceiling",          # no-float -> None
        settlement_audit_exceptions_flag="trigger",    # no-bool -> False
    )
    assert coerced == {
        "gross_completed_work_value": 0.0,
        "unrecoverable_direct_costs": 0.0,
        "subcontractor_cancellation_settlements": 0.0,
        "demobilization_expenses": 0.0,
        "profit_percentage_on_completed_work": 10.0,
        "advance_payments_received": 0.0,
        "max_contract_ceiling_value": None,
        "total_settlement_amount": 0.0,
        "net_settlement_after_advance_deduction": 0.0,
        "settlement_payable_within_ceiling": 0.0,
        "settlement_beyond_contract_ceiling_amount": 0.0,
        "settlement_audit_exception_breach": False,
        "indirect_settlement_components_present": False,
        "settlement_audit_status": "T4C_SETTLEMENT_CLEAN_UNDER_FAR_52_249_2",
        "is_t4c_settlement_audited": True,
    }

def _mc_activity(activity_id: str, *, optimistic=5, most_likely=20, pessimistic=35,
                 is_critical=True, total_float=0.0):
    """Actividad de cronograma con distribución triangular [5, 20, 35]: media PERT 20 y varianza 25."""
    return {
        "activity_id": activity_id,
        "optimistic_days": optimistic,
        "most_likely_days": most_likely,
        "pessimistic_days": pessimistic,
        "is_critical_path": is_critical,
        "total_float_days": total_float,
    }


def test_monte_carlo_schedule_confidence_healthy_clean_case():
    """Compromiso 30d cubre P90 26.41d -> 'HEALTHY_SCHEDULE_CONFIDENCE_OPTIMAL'; la actividad no crítica no agrega al plan."""
    import backend.services.project_lifecycle_pmi_service as lse_module
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_monte_carlo_schedule_float_variance_and_confidence_interval,
    )

    res = audit_monte_carlo_schedule_float_variance_and_confidence_interval(
        [
            _mc_activity("A"),
            _mc_activity("B", optimistic=0, most_likely=18, pessimistic=36,
                         is_critical=False, total_float=5.0),
        ],
        committed_contractual_finish_days=30.0,
    )
    assert res == {
        "activities_evaluated": 2,
        "critical_activity_ids": ["A"],
        "contradictory_critical_float_activity_ids": [],
        "negative_total_float_activity_ids": [],
        "normalized_distribution_activity_ids": [],
        "skipped_invalid_activity_entries": 0,
        "expected_duration_days": 20.0,
        "schedule_variance_days2": 25.0,
        "schedule_std_dev_days": 5.0,
        "p50_days": 20.0,
        "p80_days": 24.21,
        "p90_days": 26.41,
        "target_confidence_percentile": 80.0,
        "target_confidence_days": 24.21,
        "committed_contractual_finish_days": 30.0,
        "schedule_buffer_to_p90_days": 3.59,
        "contingency_buffer_required_days": 6.41,
        "required_buffer_to_target_days": 4.21,
        "critical_path_total_float_days": 0.0,
        "critical_path_total_float_variance_days2": 0.0,
        "records": [
            {
                "activity_id": "A",
                "optimistic_days": 5.0,
                "most_likely_days": 20.0,
                "pessimistic_days": 35.0,
                "pert_expected_days": 20.0,
                "pert_variance_days2": 25.0,
                "total_float_days": 0.0,
                "is_critical_path": True,
                "distribution_order_normalized": False,
            },
            {
                "activity_id": "B",
                "optimistic_days": 0.0,
                "most_likely_days": 18.0,
                "pessimistic_days": 36.0,
                "pert_expected_days": 18.0,
                "pert_variance_days2": 36.0,
                "total_float_days": 5.0,
                "is_critical_path": False,
                "distribution_order_normalized": False,
            },
        ],
        "schedule_confidence_status": "HEALTHY_SCHEDULE_CONFIDENCE_OPTIMAL",
        "is_schedule_confidence_healthy": True,
    }
    assert (
        ProjectLifecyclePMIService
        .audit_monte_carlo_schedule_float_variance_and_confidence_interval
        is not None
    )
    assert (
        "audit_monte_carlo_schedule_float_variance_and_confidence_interval"
        in lse_module.__all__
    )


def test_monte_carlo_schedule_confidence_warning_erosion_and_contradictory_float():
    """Compromiso entre P50 y P80 erosiona la confianza y holgura positiva en ruta crítica es contradictoria: WARNING."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_monte_carlo_schedule_float_variance_and_confidence_interval,
    )

    # Compromiso 22d: 20 <= 22 < P80 24.21 -> WARNING; buffer a P90 = -4.41.
    erosion = audit_monte_carlo_schedule_float_variance_and_confidence_interval(
        [_mc_activity("A")],
        committed_contractual_finish_days=22.0,
    )
    assert erosion["p50_days"] == 20.0
    assert erosion["p80_days"] == 24.21
    assert erosion["target_confidence_days"] == 24.21
    assert erosion["schedule_buffer_to_p90_days"] == -4.41
    assert erosion["contingency_buffer_required_days"] == 6.41
    assert erosion["schedule_confidence_status"] == "WARNING_SCHEDULE_CONTINGENCY_EROSION"
    assert erosion["is_schedule_confidence_healthy"] is False

    # Dos críticas con holguras 8.0 y 10.0 superan la tolerancia 0.0 -> WARNING
    # contradictorio sin compromiso; varianza de holgura poblacional 1.0.
    contradictory = audit_monte_carlo_schedule_float_variance_and_confidence_interval(
        [_mc_activity("A", total_float=8.0), _mc_activity("D", total_float=10.0)],
    )
    assert contradictory["contradictory_critical_float_activity_ids"] == ["A", "D"]
    assert contradictory["critical_path_total_float_days"] == 18.0
    assert contradictory["critical_path_total_float_variance_days2"] == 1.0
    assert contradictory["negative_total_float_activity_ids"] == []
    assert contradictory["committed_contractual_finish_days"] is None
    assert contradictory["schedule_confidence_status"] == "WARNING_SCHEDULE_CONTINGENCY_EROSION"


def test_monte_carlo_schedule_confidence_critical_breach_and_precedence():
    """Compromiso bajo la mediana P50 20d no garantiza ni el 50% de confianza y holgura negativa rompe restricciones: CRITICAL con precedencia sobre WARNING."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_monte_carlo_schedule_float_variance_and_confidence_interval,
    )

    # Compromiso 15d < P50 20 (y también bajo P90 26.41): CRITICAL.
    breach = audit_monte_carlo_schedule_float_variance_and_confidence_interval(
        [_mc_activity("A")],
        committed_contractual_finish_days=15.0,
    )
    assert breach["schedule_buffer_to_p90_days"] == -11.41
    assert breach["schedule_confidence_status"] == "CRITICAL_SCHEDULE_CONFIDENCE_BREACH"
    assert breach["negative_total_float_activity_ids"] == []

    # Borde superior del WARNING: compromiso 25d cubre P50 20 y P80 24.21 pero
    # no P90 26.41 -> la reserva para 90% está erosionada: WARNING, no CRITICAL.
    late_warning = audit_monte_carlo_schedule_float_variance_and_confidence_interval(
        [_mc_activity("A")],
        committed_contractual_finish_days=25.0,
    )
    assert late_warning["schedule_buffer_to_p90_days"] == -1.41
    assert late_warning["schedule_confidence_status"] == "WARNING_SCHEDULE_CONTINGENCY_EROSION"

    # Borde exacto: compromiso igual a la mediana P50 20d entra en WARNING (inclusivo).
    median_edge = audit_monte_carlo_schedule_float_variance_and_confidence_interval(
        [_mc_activity("A")],
        committed_contractual_finish_days=20.0,
    )
    assert median_edge["schedule_buffer_to_p90_days"] == -6.41
    assert median_edge["schedule_confidence_status"] == "WARNING_SCHEDULE_CONTINGENCY_EROSION"

    # Holgura negativa -3.0 sin compromiso: restricciones rotas -> CRITICAL.
    negative = audit_monte_carlo_schedule_float_variance_and_confidence_interval(
        [_mc_activity("A", total_float=-3.0)],
    )
    assert negative["negative_total_float_activity_ids"] == ["A"]
    assert negative["contradictory_critical_float_activity_ids"] == []
    assert negative["schedule_confidence_status"] == "CRITICAL_SCHEDULE_CONFIDENCE_BREACH"

    # Precedencia: holgura negativa CRITICAL domina sobre la holgura
    # contradictoria WARNING en el mismo plan.
    precedence = audit_monte_carlo_schedule_float_variance_and_confidence_interval(
        [_mc_activity("A", total_float=-3.0), _mc_activity("D", total_float=10.0)],
    )
    assert precedence["schedule_confidence_status"] == "CRITICAL_SCHEDULE_CONFIDENCE_BREACH"

    # Borde exacto: compromiso igual a P90 no incumple (>=) -> HEALTHY con buffer 0.
    borderline = audit_monte_carlo_schedule_float_variance_and_confidence_interval(
        [_mc_activity("A")],
        committed_contractual_finish_days=26.41,
    )
    assert borderline["schedule_buffer_to_p90_days"] == 0.0
    assert borderline["schedule_confidence_status"] == "HEALTHY_SCHEDULE_CONFIDENCE_OPTIMAL"


def test_monte_carlo_schedule_variance_field_coercion_and_empty_collection():
    """Colecciones y tipos inválidos reverten a defaults seguros; tríadas desordenadas se normalizan y percentiles objetivo se acotan."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_monte_carlo_schedule_float_variance_and_confidence_interval,
    )

    empty = audit_monte_carlo_schedule_float_variance_and_confidence_interval("cycles")
    assert empty == {
        "activities_evaluated": 0,
        "critical_activity_ids": [],
        "contradictory_critical_float_activity_ids": [],
        "negative_total_float_activity_ids": [],
        "normalized_distribution_activity_ids": [],
        "skipped_invalid_activity_entries": 0,
        "expected_duration_days": 0.0,
        "schedule_variance_days2": 0.0,
        "schedule_std_dev_days": 0.0,
        "p50_days": 0.0,
        "p80_days": 0.0,
        "p90_days": 0.0,
        "target_confidence_percentile": 80.0,
        "target_confidence_days": 0.0,
        "committed_contractual_finish_days": None,
        "schedule_buffer_to_p90_days": None,
        "contingency_buffer_required_days": 0.0,
        "required_buffer_to_target_days": 0.0,
        "critical_path_total_float_days": 0.0,
        "critical_path_total_float_variance_days2": 0.0,
        "records": [],
        "schedule_confidence_status": "HEALTHY_SCHEDULE_CONFIDENCE_OPTIMAL",
        "is_schedule_confidence_healthy": True,
    }
    assert audit_monte_carlo_schedule_float_variance_and_confidence_interval([]) == empty

    # Coerción: entradas no dict y sin activity_id se saltan; duraciones no
    # numéricas (bool excluido) a 0.0; float no numérico a 0.0;
    # is_critical_path ausente revierte a True; compromiso no numérico a None;
    # percentil bool a 80.0 y acotado a [50, 99]; tolerancia negativa a 0.0;
    # tríada invertida se normaliza (5, 20, 35).
    coerced = audit_monte_carlo_schedule_float_variance_and_confidence_interval(
        [
            "rotten",
            {"optimistic_days": 5, "most_likely_days": 20, "pessimistic_days": 35},
            {
                "activity_id": "X",
                "optimistic_days": 35,
                "most_likely_days": 20,
                "pessimistic_days": 5,
                "total_float_days": 4.0,  # holgura positiva critic con tolerancia 0 -> WARNING
            },
        ],
        committed_contractual_finish_days="soon",
        target_confidence_percentile=True,
        critical_path_float_tolerance_days=-2,
    )
    assert coerced["skipped_invalid_activity_entries"] == 2
    assert coerced["activities_evaluated"] == 1
    assert coerced["critical_activity_ids"] == ["X"]  # ausente -> True conservador
    assert coerced["normalized_distribution_activity_ids"] == ["X"]
    assert coerced["committed_contractual_finish_days"] is None
    assert coerced["schedule_buffer_to_p90_days"] is None
    assert coerced["target_confidence_percentile"] == 80.0
    assert coerced["records"][0] == {
        "activity_id": "X",
        "optimistic_days": 5.0,
        "most_likely_days": 20.0,
        "pessimistic_days": 35.0,
        "pert_expected_days": 20.0,
        "pert_variance_days2": 25.0,
        "total_float_days": 4.0,
        "is_critical_path": True,
        "distribution_order_normalized": True,
    }
    assert coerced["contradictory_critical_float_activity_ids"] == ["X"]
    assert coerced["p50_days"] == 20.0
    assert coerced["p90_days"] == 26.41
    assert coerced["schedule_confidence_status"] == "WARNING_SCHEDULE_CONTINGENCY_EROSION"

    # Duraciones totalmente inválidas -> plan de 0.0 dias; bools excluidos;
    # compromiso negativo a None; percentil acotado a 50.
    fully_invalid = audit_monte_carlo_schedule_float_variance_and_confidence_interval(
        [{"activity_id": "Y", "optimistic_days": "5", "most_likely_days": True,
          "pessimistic_days": None, "total_float_days": "late"}],
        committed_contractual_finish_days=-5.0,
        target_confidence_percentile=-20,
    )
    assert fully_invalid["records"][0]["pert_expected_days"] == 0.0
    assert fully_invalid["records"][0]["pert_variance_days2"] == 0.0
    assert fully_invalid["p50_days"] == 0.0
    assert fully_invalid["committed_contractual_finish_days"] is None
    assert fully_invalid["target_confidence_percentile"] == 50.0
    assert fully_invalid["target_confidence_days"] == 0.0
    assert fully_invalid["schedule_confidence_status"] == "HEALTHY_SCHEDULE_CONFIDENCE_OPTIMAL"

    clamped_high = audit_monte_carlo_schedule_float_variance_and_confidence_interval(
        [_mc_activity("A")],
        target_confidence_percentile=150,
    )
    assert clamped_high["target_confidence_percentile"] == 99.0
    assert clamped_high["target_confidence_days"] == 31.63

    explicit_90 = audit_monte_carlo_schedule_float_variance_and_confidence_interval(
        [_mc_activity("A")],
        target_confidence_percentile=90,
    )
    assert explicit_90["target_confidence_percentile"] == 90.0
    assert explicit_90["target_confidence_days"] == 26.41


def test_unallowable_costs_far31_healthy_clean_case():
    """Solo costos admisibles con base CAS 401 explícita en el indirecto -> 'HEALTHY_FAR_PART_31_COMPLIANT'."""
    import backend.services.project_lifecycle_pmi_service as lse_module
    from backend.services.project_lifecycle_pmi_service import (
        ProjectLifecyclePMIService,
        audit_project_lifecycle_unallowable_costs_and_cost_accounting_standards_cas,
    )

    res = audit_project_lifecycle_unallowable_costs_and_cost_accounting_standards_cas(
        [
            {"item_id": "LAB-05", "amount": 10000.0, "category": "direct_labor",
             "is_indirect": False, "allocation_basis": ""},
            {"item_id": "OHI-06", "amount": 3000.0, "category": "other_indirect",
             "is_indirect": True, "allocation_basis": "machine_hours"},
        ],
    )
    assert res == {
        "items_evaluated": 2,
        "skipped_invalid_entries": 0,
        "total_cost_amount": 13000.0,
        "direct_costs_total": 10000.0,
        "indirect_costs_total": 3000.0,
        "unallowable_item_ids": [],
        "unallowable_costs_total": 0.0,
        "executive_compensation_item_ids": [],
        "executive_compensation_cap_amount": None,
        "executive_compensation_cap_excess_item_ids": [],
        "executive_compensation_cap_excess_amount": 0.0,
        "cas_401_missing_basis_item_ids": [],
        "cas_401_inconsistent_basis_item_ids": [],
        "cas_401_allocation_basis_inconsistent": False,
        "net_allowable_ceiling_amount": 13000.0,
        "records": [
            {
                "item_id": "LAB-05",
                "amount": 10000.0,
                "category": "direct_labor",
                "is_indirect": False,
                "allocation_basis": "",
                "is_fully_unallowable": False,
                "cap_excess_unallowable_amount": 0.0,
                "cas_401_missing_basis": False,
            },
            {
                "item_id": "OHI-06",
                "amount": 3000.0,
                "category": "other_indirect",
                "is_indirect": True,
                "allocation_basis": "machine_hours",
                "is_fully_unallowable": False,
                "cap_excess_unallowable_amount": 0.0,
                "cas_401_missing_basis": False,
            },
        ],
        "compliance_status": "HEALTHY_FAR_PART_31_COMPLIANT",
        "is_far_31_compliant": True,
    }
    assert (
        ProjectLifecyclePMIService
        .audit_project_lifecycle_unallowable_costs_and_cost_accounting_standards_cas
        is not None
    )
    assert (
        "audit_project_lifecycle_unallowable_costs_and_cost_accounting_standards_cas"
        in lse_module.__all__
    )


def test_unallowable_costs_far31_critical_exposure_and_precedence():
    """Alcohol/ocio 500, sanciones 1200, cabildeo 800 y exceso ejecutivo 500 sobre tope 2000 -> 'CRITICAL_UNALLOWABLE_COST_EXPOSURE' con precedencia sobre deficiencias CAS 401."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_project_lifecycle_unallowable_costs_and_cost_accounting_standards_cas,
    )

    res = audit_project_lifecycle_unallowable_costs_and_cost_accounting_standards_cas(
        [
            {"item_id": "ALC-01", "amount": 500.0, "category": "alcohol_entertainment"},
            {"item_id": "FINE-02", "amount": 1200.0, "category": "fines_penalties"},
            {"item_id": "LOB-03", "amount": 800.0, "category": "lobbying"},
            {"item_id": "EXE-04", "amount": 2500.0, "category": "executive_compensation"},
            {"item_id": "LAB-05", "amount": 10000.0, "category": "direct_labor"},
            {"item_id": "OHI-06", "amount": 3000.0, "category": "other_indirect",
             "is_indirect": True, "allocation_basis": "machine_hours"},
        ],
        executive_compensation_cap_amount=2000.0,
    )
    assert res["total_cost_amount"] == 18000.0
    assert res["direct_costs_total"] == 15000.0
    assert res["indirect_costs_total"] == 3000.0
    assert res["unallowable_item_ids"] == ["ALC-01", "FINE-02", "LOB-03"]
    assert res["unallowable_costs_total"] == 2500.0
    assert res["executive_compensation_cap_excess_item_ids"] == ["EXE-04"]
    assert res["executive_compensation_cap_excess_amount"] == 500.0
    assert res["net_allowable_ceiling_amount"] == 15000.0  # 18000 - 2500 - 500
    assert res["compliance_status"] == "CRITICAL_UNALLOWABLE_COST_EXPOSURE"
    assert res["is_far_31_compliant"] is False
    assert res["records"][3]["cap_excess_unallowable_amount"] == 500.0

    # Precedencia: costos inadmisibles (CRITICAL) dominan la deficiencia CAS 401
    # concurrente (indirecto sin base).
    precedence = audit_project_lifecycle_unallowable_costs_and_cost_accounting_standards_cas(
        [
            {"item_id": "ALC-01", "amount": 500.0, "category": "alcohol_entertainment"},
            {"item_id": "OHI-06", "amount": 3000.0, "is_indirect": True},
        ],
    )
    assert precedence["cas_401_missing_basis_item_ids"] == ["OHI-06"]
    assert precedence["compliance_status"] == "CRITICAL_UNALLOWABLE_COST_EXPOSURE"


def test_unallowable_costs_far31_cas401_warning_and_cap_edges():
    """Indirecto sin base y bases múltiples inconsistentes -> 'WARNING_CAS_401_ALLOCATION_DEFICIENCY'; tope exacto no genera exceso y tope inválido revierte a None."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_project_lifecycle_unallowable_costs_and_cost_accounting_standards_cas,
    )

    missing = audit_project_lifecycle_unallowable_costs_and_cost_accounting_standards_cas(
        [
            {"item_id": "LAB-05", "amount": 10000.0, "category": "direct_labor"},
            {"item_id": "OHI-06", "amount": 3000.0, "category": "other_indirect",
             "is_indirect": True},
        ],
    )
    assert missing["total_cost_amount"] == 13000.0
    assert missing["cas_401_missing_basis_item_ids"] == ["OHI-06"]
    assert missing["net_allowable_ceiling_amount"] == 13000.0
    assert missing["compliance_status"] == "WARNING_CAS_401_ALLOCATION_DEFICIENCY"
    assert missing["is_far_31_compliant"] is False

    inconsistent = audit_project_lifecycle_unallowable_costs_and_cost_accounting_standards_cas(
        [
            {"item_id": "OHI-06", "amount": 2000.0, "is_indirect": True,
             "allocation_basis": "machine_hours"},
            {"item_id": "OHI-07", "amount": 1500.0, "is_indirect": True,
             "allocation_basis": "labor_hours"},
        ],
    )
    assert inconsistent["cas_401_inconsistent_basis_item_ids"] == ["OHI-07"]
    assert inconsistent["cas_401_allocation_basis_inconsistent"] is True
    assert inconsistent["indirect_costs_total"] == 3500.0
    assert inconsistent["compliance_status"] == "WARNING_CAS_401_ALLOCATION_DEFICIENCY"

    # Borde exacto: compensación ejecutiva igual al tope no genera exceso.
    at_cap = audit_project_lifecycle_unallowable_costs_and_cost_accounting_standards_cas(
        [{"item_id": "EXE-04", "amount": 2000.0, "category": "executive_compensation"}],
        executive_compensation_cap_amount=2000.0,
    )
    assert at_cap["executive_compensation_cap_excess_amount"] == 0.0
    assert at_cap["net_allowable_ceiling_amount"] == 2000.0
    assert at_cap["compliance_status"] == "HEALTHY_FAR_PART_31_COMPLIANT"

    # Sin tope (inválido -> None): compensación ejecutiva íntegra admisible.
    no_cap = audit_project_lifecycle_unallowable_costs_and_cost_accounting_standards_cas(
        [{"item_id": "EXE-04", "amount": 2500.0, "category": "executive_compensation"}],
        executive_compensation_cap_amount="cap",
    )
    assert no_cap["executive_compensation_cap_amount"] is None
    assert no_cap["net_allowable_ceiling_amount"] == 2500.0
    assert no_cap["compliance_status"] == "HEALTHY_FAR_PART_31_COMPLIANT"


def test_unallowable_costs_far31_field_coercion_and_empty_collection():
    """Colecciones y tipos inválidos reverten a defaults; montos negativos clamp a 0.0 y categorías canónicas sin importar mayúsculas."""
    from backend.services.project_lifecycle_pmi_service import (
        audit_project_lifecycle_unallowable_costs_and_cost_accounting_standards_cas,
    )

    empty = audit_project_lifecycle_unallowable_costs_and_cost_accounting_standards_cas(
        "costs"
    )
    assert empty == {
        "items_evaluated": 0,
        "skipped_invalid_entries": 0,
        "total_cost_amount": 0.0,
        "direct_costs_total": 0.0,
        "indirect_costs_total": 0.0,
        "unallowable_item_ids": [],
        "unallowable_costs_total": 0.0,
        "executive_compensation_item_ids": [],
        "executive_compensation_cap_amount": None,
        "executive_compensation_cap_excess_item_ids": [],
        "executive_compensation_cap_excess_amount": 0.0,
        "cas_401_missing_basis_item_ids": [],
        "cas_401_inconsistent_basis_item_ids": [],
        "cas_401_allocation_basis_inconsistent": False,
        "net_allowable_ceiling_amount": 0.0,
        "records": [],
        "compliance_status": "HEALTHY_FAR_PART_31_COMPLIANT",
        "is_far_31_compliant": True,
    }
    assert (audit_project_lifecycle_unallowable_costs_and_cost_accounting_standards_cas([])
            == empty)

    # Coerción: entradas no dict y sin item_id se saltan; monto no numérico ->
    # 0.0; categoría no string -> "other"; is_indirect no bool -> False;
    # basis no string -> ""; tope negativo -> None; categoría canónica en
    # minúsculas aunque venga en mayúsculas y con espacios; monto negativo
    # clamp a 0.0 (el item queda marcado inadmisible por categoría con
    # exposición 0.0).
    coerced = audit_project_lifecycle_unallowable_costs_and_cost_accounting_standards_cas(
        [
            {"item_id": "", "amount": 10.0},
            "rotten",
            {"item_id": "BAD-09", "amount": "amount", "category": True,
             "is_indirect": "yes", "allocation_basis": 3},
            {"item_id": "NEG-10", "amount": -250.0, "category": "ALCOHOL_ENTERTAINMENT "},
        ],
        executive_compensation_cap_amount=-100,
    )
    assert coerced["skipped_invalid_entries"] == 2
    assert coerced["items_evaluated"] == 2
    assert coerced["records"][0] == {
        "item_id": "BAD-09",
        "amount": 0.0,
        "category": "other",
        "is_indirect": False,
        "allocation_basis": "",
        "is_fully_unallowable": False,
        "cap_excess_unallowable_amount": 0.0,
        "cas_401_missing_basis": False,
    }
    assert coerced["records"][1] == {
        "item_id": "NEG-10",
        "amount": 0.0,
        "category": "alcohol_entertainment",
        "is_indirect": False,
        "allocation_basis": "",
        "is_fully_unallowable": True,
        "cap_excess_unallowable_amount": 0.0,
        "cas_401_missing_basis": False,
    }
    assert coerced["unallowable_item_ids"] == ["NEG-10"]
    assert coerced["unallowable_costs_total"] == 0.0
    assert coerced["net_allowable_ceiling_amount"] == 0.0
    assert coerced["executive_compensation_cap_amount"] is None
    assert coerced["compliance_status"] == "CRITICAL_UNALLOWABLE_COST_EXPOSURE"

    # Bools excluidos de montos: True no es un monto válido.
    bool_amount = audit_project_lifecycle_unallowable_costs_and_cost_accounting_standards_cas(
        [{"item_id": "B-01", "amount": True}],
        executive_compensation_cap_amount=True,
    )
    assert bool_amount["records"][0]["amount"] == 0.0
    assert bool_amount["executive_compensation_cap_amount"] is None
    assert bool_amount["total_cost_amount"] == 0.0
    assert bool_amount["compliance_status"] == "HEALTHY_FAR_PART_31_COMPLIANT"
