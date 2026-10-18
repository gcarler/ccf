import csv
import io

from backend.crud.projects import (
    generate_project_expenses_csv,
    generate_project_summary_pdf,
    generate_project_tasks_csv,
)
from backend.models_projects import ProjectExpense, ProjectRisk
from tests.conftest import auth_headers, seed_admin
from tests.factories_projects import create_project_factory, create_task_factory


def test_summary_pdf_treats_project_content_as_plain_text():
    injected_image = '<img src="/etc/passwd" width="100" height="100"/>'
    report_data = {
        "project": {
            "title": f"Proyecto {injected_image}",
            "status": f"active {injected_image}",
            "owner_name": f"Líder {injected_image}",
            "health_override": injected_image,
        },
        "financial_kpis": {"by_category": {injected_image: 10.0}},
        "raid_kpis": {
            "risks": [{
                "title": injected_image,
                "category": injected_image,
                "probability": 2,
                "impact": 3,
                "mitigation_plan": injected_image,
            }],
        },
        "cpm_metrics": {"tasks": [{"is_critical": True, "title": injected_image}]},
        "time_metrics": {
            "by_member": [{"persona_name": injected_image, "total_hours": 1, "billable_hours": 1}],
        },
    }

    pdf = generate_project_summary_pdf(report_data)

    assert pdf.startswith(b"%PDF-")


def test_summary_pdf_endpoint_accepts_project_title_without_processing_markup(client, db_session):
    _, _, sede = seed_admin(db_session)
    project = create_project_factory(
        db_session,
        sede_id=sede.id,
        title='Reporte <img src="/etc/passwd" width="100" height="100"/>',
    )

    response = client.get(
        f"/api/projects/{project.id}/export/summary-pdf",
        headers=auth_headers(client),
    )

    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("application/pdf")
    assert response.content.startswith(b"%PDF-")


def test_executive_report_contract_includes_project_risks(client, db_session):
    _, _, sede = seed_admin(db_session)
    project = create_project_factory(db_session, sede_id=sede.id, title="Reporte con riesgos")
    task = create_task_factory(db_session, project.id, title="Preparar mitigación")
    db_session.add(ProjectRisk(
        project_id=project.id,
        title="Proveedor crítico",
        category="operativo",
        probability=4,
        impact=5,
        severity_score=20,
        status="active",
        mitigation_plan="Acordar alternativa de suministro",
    ))
    db_session.commit()

    response = client.get(
        f"/api/projects/{project.id}/export/executive-data",
        headers=auth_headers(client),
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["project"]["id"] == str(project.id)
    assert payload["raid_kpis"]["project_id"] == str(project.id)
    assert payload["raid_kpis"]["total_risks"] == 1
    assert payload["raid_kpis"]["active_risks"] == 1
    assert payload["raid_kpis"]["matrix_5x5"]
    assert payload["raid_kpis"]["by_category"] == {"operativo": 1}
    assert payload["tasks_metrics"]["total"] == 1
    assert payload["cpm_metrics"]["tasks"][0]["task_id"] == str(task.id)
    assert len(payload["raid_kpis"]["risks"]) == 1
    risk_data = payload["raid_kpis"]["risks"][0]
    assert risk_data == {
        "id": risk_data["id"],
        "title": "Proveedor crítico",
        "category": "operativo",
        "probability": 4,
        "impact": 5,
        "severity": 20,
        "status": "active",
        "mitigation_plan": "Acordar alternativa de suministro",
    }


def test_executive_report_and_pdf_include_pmi_governance_summary(client, db_session):
    from datetime import datetime, timezone

    from backend.models_projects import ProjectLifecycle, ProjectStakeholder
    from backend.services.project_export_service import (
        generate_project_summary_pdf,
        get_project_executive_report_data,
    )

    _, sponsor, sede = seed_admin(db_session, email="pmi-report@example.com")
    project = create_project_factory(db_session, sede_id=sede.id, title="Gobernanza PMI")
    db_session.add(ProjectLifecycle(
        project_id=project.id,
        sponsor_id=sponsor.id,
        business_case="Caso de negocio",
        strategic_justification="Alineación estratégica",
        measurable_objectives=["Objetivo 1", "Objetivo 2"],
        key_assumptions=[],
        key_constraints=[],
        high_level_risks=[],
        charter_status="authorized",
        authorized_by=sponsor.id,
        authorized_at=datetime(2026, 10, 18, tzinfo=timezone.utc),
        closure_status="closed",
        deliverables_accepted_verified=True,
        financial_reconciliation_completed=True,
        lessons_learned=[{"category": "equipo", "what_worked": "Coordinación", "what_failed": "", "recommendation": "Continuar"}],
        closed_by=sponsor.id,
        closed_at=datetime(2026, 10, 19, tzinfo=timezone.utc),
        wiki_synced=False,
    ))
    for quadrant in ("manage_closely", "keep_satisfied", "keep_informed", "monitor"):
        db_session.add(ProjectStakeholder(
            project_id=project.id,
            display_name=f"Interesado {quadrant}",
            power_level=4 if quadrant in ("manage_closely", "keep_satisfied") else 2,
            interest_level=4 if quadrant in ("manage_closely", "keep_informed") else 2,
            quadrant=quadrant,
            engagement_level="supportive",
        ))
    db_session.add(ProjectStakeholder(
        project_id=project.id,
        display_name="Interesado retirado",
        power_level=1,
        interest_level=1,
        quadrant="monitor",
        engagement_level="neutral",
        deleted_at=datetime(2026, 10, 18, tzinfo=timezone.utc),
    ))
    db_session.commit()

    report = get_project_executive_report_data(db_session, project.id, user_sede_id=sede.id)
    assert report is not None
    assert report["governance_summary"] == {
        "charter_status": "authorized",
        "sponsor_id": str(sponsor.id),
        "authorized_at": "2026-10-18T00:00:00+00:00",
        "measurable_objectives_count": 2,
        "stakeholders_total": 4,
        "stakeholders_by_quadrant": {
            "manage_closely": 1,
            "keep_satisfied": 1,
            "keep_informed": 1,
            "monitor": 1,
        },
        "closure_status": "closed",
        "deliverables_accepted_verified": True,
        "financial_reconciliation_completed": True,
        "lessons_learned_count": 1,
    }

    api_report = client.get(
        f"/api/projects/{project.id}/export/executive-data",
        headers=auth_headers(client, email="pmi-report@example.com"),
    )
    assert api_report.status_code == 200, api_report.text
    api_governance = api_report.json()["governance_summary"]
    assert {
        key: value for key, value in api_governance.items() if key != "authorized_at"
    } == {
        key: value for key, value in report["governance_summary"].items() if key != "authorized_at"
    }
    assert datetime.fromisoformat(api_governance["authorized_at"].replace("Z", "+00:00")) == datetime.fromisoformat(
        report["governance_summary"]["authorized_at"]
    )

    pdf = generate_project_summary_pdf(report)
    assert pdf.startswith(b"%PDF-")
    assert b"GOBERNANZA DEL CICLO DE VIDA PMI" in pdf
    assert b"Gestionar de cerca" in pdf


def test_tasks_csv_neutralizes_spreadsheet_formulas_in_text_fields(db_session):
    project = create_project_factory(db_session)
    create_task_factory(
        db_session,
        project.id,
        title="=HYPERLINK(\"https://example.test\")",
        description="  +SUM(1,2)",
        node="@SUM(1,2)",
    )

    rows = list(csv.reader(io.StringIO(generate_project_tasks_csv(db_session, project.id).lstrip("\ufeff"))))

    assert rows[1][1] == "'=HYPERLINK(\"https://example.test\")"
    assert rows[1][2] == "'+SUM(1,2)"
    assert rows[1][5] == "'@SUM(1,2)"


def test_expenses_csv_neutralizes_spreadsheet_formulas_in_text_fields(db_session):
    project = create_project_factory(db_session)
    db_session.add(ProjectExpense(
        project_id=project.id,
        category="-1+2",
        description="=cmd|'/C calc'!A0",
        amount=12.5,
        receipt_url="@SUM(1,2)",
    ))
    db_session.commit()

    rows = list(csv.reader(io.StringIO(generate_project_expenses_csv(db_session, project.id).lstrip("\ufeff"))))

    assert rows[1][2] == "'-1+2"
    assert rows[1][3] == "'=cmd|'/C calc'!A0"
    assert rows[1][4] == "12.50"
    assert rows[1][6] == "'@SUM(1,2)"


def test_executive_report_and_pdf_include_360_submodules_summary(client, db_session):
    from backend.models_projects import (
        ProjectAutomationRule,
        ProjectBaseline,
        ProjectTaskDependency,
    )
    from backend.services.project_export_service import (
        generate_project_summary_pdf as service_generate_pdf,
        get_project_executive_report_data as service_get_report,
    )

    _, admin_persona, sede = seed_admin(db_session)
    headers = auth_headers(client)
    project = create_project_factory(
        db_session,
        sede_id=sede.id,
        title="Proyecto 360 Submódulos",
        budget_allocated=20000.0,
    )
    task_a = create_task_factory(
        db_session,
        project.id,
        title="Tarea Crítica A",
        status="completed",
        estimated_hours=20.0,
        assignee_id=admin_persona.id,
    )
    task_b = create_task_factory(
        db_session,
        project.id,
        title="Tarea Crítica B",
        status="in_progress",
        estimated_hours=30.0,
        assignee_id=admin_persona.id,
    )

    # 1. Baseline
    baseline = ProjectBaseline(
        project_id=project.id,
        name="Línea Base Oficial Q4",
        snapshot_data={"bac": 20000.0, "progress_percentage": 25.0},
        created_by=admin_persona.id,
    )
    db_session.add(baseline)

    # 2. Dependency (CPM)
    dep = ProjectTaskDependency(
        project_id=project.id,
        predecessor_id=task_a.id,
        successor_id=task_b.id,
        dependency_type="FS",
        lag_days=0,
    )
    db_session.add(dep)

    # 3. Automation rule
    rule = ProjectAutomationRule(
        project_id=project.id,
        name="Auto Prioridad",
        trigger_event="task_created",
        condition_data={},
        action_type="set_priority",
        action_data={"priority": "high"},
        is_active=True,
        execution_count=3,
        created_by=admin_persona.id,
        sede_id=sede.id,
    )
    db_session.add(rule)
    db_session.commit()

    # 4. Supply -> Auto-generated Expense
    r_sup = client.post(
        f"/api/projects/{project.id}/tasks/{task_a.id}/supplies",
        json={
            "item_name": "Generador Eléctrico",
            "quantity": 2,
            "status": "received",
            "unit_cost": 1500.0,
            "total_cost": 3000.0,
            "auto_create_expense": True,
        },
        headers=headers,
    )
    assert r_sup.status_code == 201, r_sup.text

    # 5. Time Tracking Log
    r_log = client.post(
        f"/api/projects/{project.id}/time-logs",
        json={
            "task_id": str(task_a.id),
            "hours": 15.0,
            "description": "Instalación inicial",
            "is_billable": True,
        },
        headers=headers,
    )
    assert r_log.status_code == 201, r_log.text
    # Ensure task_a remains completed after time log sync
    task_a_db = db_session.get(type(task_a), task_a.id)
    task_a_db.status = "completed"
    db_session.commit()

    response = client.get(
        f"/api/projects/{project.id}/export/executive-data",
        headers=headers,
    )
    assert response.status_code == 200, response.text
    payload = response.json()

    assert "submodules_summary" in payload
    sub = payload["submodules_summary"]

    # a) baseline
    assert sub["baseline"]["has_active_baseline"] is True
    assert sub["baseline"]["baseline_id"] == str(baseline.id)
    assert sub["baseline"]["baseline_name"] == "Línea Base Oficial Q4"
    assert sub["baseline"]["baseline_bac"] == 20000.0
    assert sub["baseline"]["snapshots_count"] == 1
    assert "baseline_variance_cost" in sub["baseline"]
    assert "baseline_variance_schedule" in sub["baseline"]

    # b) supplies
    assert sub["supplies"]["total_supplies_count"] == 1
    assert sub["supplies"]["delivered_supplies_count"] == 1
    assert sub["supplies"]["total_supplies_cost"] == 3000.0
    assert sub["supplies"]["auto_generated_expenses_count"] == 1
    assert sub["supplies"]["auto_generated_expenses_total"] == 3000.0

    # c) time_tracking
    assert sub["time_tracking"]["logs_count"] == 1
    assert sub["time_tracking"]["billable_hours"] == 15.0
    assert sub["time_tracking"]["non_billable_hours"] == 0.0
    assert sub["time_tracking"]["total_logged_hours"] == 15.0
    assert sub["time_tracking"]["estimated_hours_total"] == 50.0
    assert sub["time_tracking"]["hours_utilization_pct"] == 30.0

    # d) workload
    assert sub["workload"]["members_with_tasks_count"] == 1
    assert sub["workload"]["overloaded_members_count"] == 0
    assert sub["workload"]["avg_utilization_pct"] == 30.0

    # e) cpm
    assert sub["cpm"]["critical_tasks_count"] == 2
    assert sub["cpm"]["critical_completed_count"] == 1
    assert sub["cpm"]["dependencies_count"] == 1

    # f) automations
    assert sub["automations"]["total_rules_count"] == 1
    assert sub["automations"]["active_rules_count"] == 1
    assert sub["automations"]["total_executions_count"] == 3

    # Verify service facade and PDF generation (both dict and (db, project_id) signatures)
    direct_report = service_get_report(db_session, project.id, user_sede_id=sede.id)
    assert direct_report is not None
    assert direct_report["submodules_summary"] == sub

    pdf_bytes = service_generate_pdf(db_session, project.id, user_sede_id=sede.id)
    assert pdf_bytes.startswith(b"%PDF-")
    assert b"Estado de Subm" in pdf_bytes
    assert b"L\xef\xbf\xbdnea Base Oficial Q4" in pdf_bytes or b"Oficial Q4" in pdf_bytes
    assert b"Estructura de Reservas" in pdf_bytes
    assert b"Regla 15% Estabilidad CPI" in pdf_bytes
    assert b"Early Warning Sentinel" in pdf_bytes

    # Verify EMV reserves, 15% CPI Stability Rule, and Early Warning Sentinel in executive report
    fin = payload["financial_kpis"]
    assert "work_packages_budget" in fin
    assert "contingency_reserve" in fin
    assert "management_reserve" in fin
    assert "total_project_budget" in fin
    assert "cpi_stability_rule" in fin and fin["cpi_stability_rule"] is not None
    assert "early_warning_sentinel" in fin and fin["early_warning_sentinel"] is not None
    assert payload["cpi_stability_rule"] == fin["cpi_stability_rule"]
    assert payload["early_warning_sentinel"] == fin["early_warning_sentinel"]

