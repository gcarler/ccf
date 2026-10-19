import pytest
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


def test_executive_report_and_pdf_include_ccb_and_quality_summary(client, db_session):
    """El informe ejecutivo y el PDF incluyen el bloque ccb_and_quality_summary (CCB + DoD / CoQ)."""
    _, _, sede = seed_admin(db_session)
    project = create_project_factory(db_session, sede_id=sede.id, title="Reporte CCB CoQ", budget_allocated=100000.0)
    create_task_factory(db_session, project.id, title="Entregable DoD Reporte")

    # ── CCB: 1 CR aprobada (Δ$20000, Δ15d) + 1 pendiente del Comité ──
    headers = auth_headers(client)
    cr1 = client.post(
        f"/api/projects/{project.id}/change-requests",
        json={"title": "CR Reporte", "justification": "Ampliación", "change_type": "budget",
              "cost_impact_delta": 20000.0, "schedule_impact_days": 15},
        headers=headers,
    )
    assert cr1.status_code == 201, cr1.text
    decided = client.post(
        f"/api/projects/{project.id}/change-requests/{cr1.json()['id']}/decide",
        json={"decision": "approved", "review_notes": "Ok"}, headers=headers,
    )
    assert decided.status_code == 200, decided.text
    client.post(
        f"/api/projects/{project.id}/change-requests",
        json={"title": "CR pendiente", "justification": "Pendiente", "change_type": "scope"},
        headers=headers,
    )

    # ── DoD: entregable aceptado con CoQ prevención $250 ──
    task_do_d = create_task_factory(db_session, project.id, title="DoD Reporte CoQ")
    dod = client.post(
        f"/api/projects/{project.id}/tasks/{task_do_d.id}/dod-acceptance",
        json={"specification_met": True, "tests_no_critical_failures": True,
              "evidence_archived": True, "supervisor_sign_off": True,
              "coq_classification": "prevention", "coq_amount": 250.0},
        headers=headers,
    )
    assert dod.status_code == 200, dod.text

    endpoint = client.get(
        f"/api/projects/{project.id}/export/executive-data",
        headers=headers,
    )
    assert endpoint.status_code == 200, endpoint.text
    payload = endpoint.json()
    ccb_block = payload["ccb_and_quality_summary"]
    assert ccb_block["total_change_requests"] == 2
    assert ccb_block["approved_count"] == 1
    assert ccb_block["pending_ccb_count"] == 1
    assert ccb_block["net_approved_cost_delta"] == pytest.approx(20000.0)
    assert ccb_block["net_approved_schedule_days"] == 15
    assert ccb_block["tasks_dod_accepted_count"] == 1
    assert ccb_block["total_coq_cost"] == pytest.approx(250.0)
    assert ccb_block["coq_by_category"]["prevention"] == pytest.approx(250.0)

    # ── PDF: se genera sin error con la sección CCB/DoD/CoQ incluida ──
    pdf_endpoint = client.get(
        f"/api/projects/{project.id}/export/summary-pdf",
        headers=headers,
    )
    assert pdf_endpoint.status_code == 200, pdf_endpoint.text
    assert pdf_endpoint.headers["content-type"].startswith("application/pdf")
    assert pdf_endpoint.content.startswith(b"%PDF-")

    pdf_bytes = generate_project_summary_pdf(payload)
    assert pdf_bytes.startswith(b"%PDF-")


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


def test_evaluate_executive_report_completeness_audit_readiness(client, db_session):
    from backend.services.project_export_service import (
        ProjectExportService,
        evaluate_executive_report_completeness,
    )

    none_result = evaluate_executive_report_completeness(None)
    assert none_result == {
        "has_project_header": False,
        "has_evm_financials": False,
        "has_raid_risks": False,
        "has_cpm_schedule": False,
        "has_pmi_governance": False,
        "has_ccb_quality": False,
        "sections_present_count": 0,
        "completeness_pct": 0.0,
        "is_audit_ready": False,
    }

    empty_result = ProjectExportService.evaluate_executive_report_completeness({})
    assert empty_result["sections_present_count"] == 0
    assert empty_result["completeness_pct"] == 0.0
    assert empty_result["is_audit_ready"] is False

    partial_result = ProjectExportService.evaluate_executive_report_completeness(
        {
            "project": {"title": "Proyecto Parcial PMI"},
            "financial_kpis": {"bac": 5000.0},
            "raid_kpis": {"risks": []},
        }
    )
    assert partial_result["has_project_header"] is True
    assert partial_result["has_evm_financials"] is True
    assert partial_result["has_raid_risks"] is True
    assert partial_result["has_cpm_schedule"] is False
    assert partial_result["has_pmi_governance"] is False
    assert partial_result["has_ccb_quality"] is False
    assert partial_result["sections_present_count"] == 3
    assert partial_result["completeness_pct"] == 50.0
    assert partial_result["is_audit_ready"] is False

    _, _, sede = seed_admin(db_session)
    project = create_project_factory(
        db_session,
        sede_id=sede.id,
        title="Proyecto Auditoría PMI 360",
    )
    full_report = ProjectExportService.get_project_executive_report_data(
        db_session,
        project.id,
        user_sede_id=sede.id,
    )
    full_result = ProjectExportService.evaluate_executive_report_completeness(
        full_report
    )
    assert full_result["has_project_header"] is True
    assert full_result["has_evm_financials"] is True
    assert full_result["has_raid_risks"] is True
    assert full_result["has_cpm_schedule"] is True
    assert full_result["has_pmi_governance"] is True
    assert full_result["has_ccb_quality"] is True
    assert full_result["sections_present_count"] == 6
    assert full_result["completeness_pct"] == 100.0
    assert full_result["is_audit_ready"] is True


def test_audit_csv_export_integrity_valid_bom_and_required_headers(db_session):
    from backend.services.project_export_service import (
        ProjectExportService,
        audit_csv_export_integrity,
    )

    csv_with_bom = "\ufeffID,Título,Estado\r\n1,Tarea A,completed\r\n2,Tarea B,in_progress\r\n"
    result = audit_csv_export_integrity(
        csv_with_bom,
        required_headers=["ID", "Título", "Estado"],
    )
    assert result == {
        "has_utf8_bom": True,
        "header_columns": ["ID", "Título", "Estado"],
        "data_row_count": 2,
        "ragged_row_count": 0,
        "missing_required_headers": [],
        "is_rfc4180_compliant": True,
    }

    project = create_project_factory(db_session)
    create_task_factory(db_session, project.id, title="Tarea RFC 4180")
    tasks_csv = ProjectExportService.generate_project_tasks_csv(db_session, project.id)
    tasks_audit = ProjectExportService.audit_csv_export_integrity(tasks_csv)
    assert tasks_audit["has_utf8_bom"] is True
    assert len(tasks_audit["header_columns"]) > 0
    assert tasks_audit["data_row_count"] == 1
    assert tasks_audit["ragged_row_count"] == 0
    assert tasks_audit["missing_required_headers"] == []
    assert tasks_audit["is_rfc4180_compliant"] is True


def test_audit_csv_export_integrity_missing_required_headers():
    from backend.services.project_export_service import audit_csv_export_integrity

    csv_text = "ID,Título\n1,Tarea 1\n"
    result = audit_csv_export_integrity(
        csv_text,
        required_headers=["ID", "Estado", "Prioridad", "Título"],
    )
    assert result["has_utf8_bom"] is False
    assert result["header_columns"] == ["ID", "Título"]
    assert result["data_row_count"] == 1
    assert result["ragged_row_count"] == 0
    assert result["missing_required_headers"] == ["Estado", "Prioridad"]
    assert result["is_rfc4180_compliant"] is False


def test_audit_csv_export_integrity_ragged_rows():
    from backend.services.project_export_service import ProjectExportService

    ragged_csv = "\ufeffCol1,Col2,Col3\nA,B,C\nD,E\nF,G,H,I\n"
    result = ProjectExportService.audit_csv_export_integrity(
        ragged_csv,
        required_headers=["Col1", "Col2"],
    )
    assert result["has_utf8_bom"] is True
    assert result["header_columns"] == ["Col1", "Col2", "Col3"]
    assert result["data_row_count"] == 3
    assert result["ragged_row_count"] == 2
    assert result["missing_required_headers"] == []
    assert result["is_rfc4180_compliant"] is False


def test_audit_csv_export_integrity_empty_and_none():
    from backend.services.project_export_service import audit_csv_export_integrity

    none_res = audit_csv_export_integrity(None, required_headers=["ID", "Monto"])
    assert none_res == {
        "has_utf8_bom": False,
        "header_columns": [],
        "data_row_count": 0,
        "ragged_row_count": 0,
        "missing_required_headers": ["ID", "Monto"],
        "is_rfc4180_compliant": False,
    }

    empty_bom_res = audit_csv_export_integrity("\ufeff   ")
    assert empty_bom_res == {
        "has_utf8_bom": True,
        "header_columns": [],
        "data_row_count": 0,
        "ragged_row_count": 0,
        "missing_required_headers": [],
        "is_rfc4180_compliant": False,
    }


def test_audit_pdf_export_binary_real_generated_pdf():
    from backend.services.project_export_service import (
        ProjectExportService,
        audit_pdf_export_binary,
    )

    report_data = {
        "project": {
            "title": "Proyecto Auditoría Binaria PDF PMI",
            "status": "active",
            "owner_name": "Director PMO",
        },
        "financial_kpis": {"by_category": {"Infraestructura": 50000.0}},
        "raid_kpis": {"risks": []},
        "cpm_metrics": {"tasks": []},
        "time_metrics": {"by_member": []},
    }
    pdf_bytes = ProjectExportService.generate_project_summary_pdf(report_data)
    audit = audit_pdf_export_binary(pdf_bytes)
    assert audit["is_valid_pdf_header"] is True
    assert audit["has_eof_marker"] is True
    assert audit["byte_size"] == len(pdf_bytes)
    assert audit["byte_size"] >= 100
    assert audit["estimated_page_count"] >= 1
    assert audit["is_export_ready"] is True


def test_audit_pdf_export_binary_multipage_synthetic():
    from backend.services.project_export_service import ProjectExportService

    synthetic_pdf = (
        b"%PDF-1.4\n"
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        b"2 0 obj << /Type /Pages /Kids [3 0 R 4 0 R] /Count 2 >> endobj\n"
        b"3 0 obj << /Type /Page /Parent 2 0 R >> endobj\n"
        b"4 0 obj << /Type /Page /Parent 2 0 R >> endobj\n"
        b"xref\n0 5\ntrailer << /Root 1 0 R >>\nstartxref\n0\n%%EOF\n"
    )
    audit = ProjectExportService.audit_pdf_export_binary(bytearray(synthetic_pdf))
    assert audit == {
        "is_valid_pdf_header": True,
        "has_eof_marker": True,
        "byte_size": len(synthetic_pdf),
        "estimated_page_count": 2,
        "is_export_ready": True,
    }


def test_audit_pdf_export_binary_truncated_without_eof():
    from backend.services.project_export_service import audit_pdf_export_binary

    truncated_pdf = (
        b"%PDF-1.4\n"
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        b"2 0 obj << /Type /Page /Parent 1 0 R >> endobj\n"
        b"stream truncated before footer marker..."
    )
    audit = audit_pdf_export_binary(truncated_pdf)
    assert audit["is_valid_pdf_header"] is True
    assert audit["has_eof_marker"] is False
    assert audit["estimated_page_count"] == 1
    assert audit["is_export_ready"] is False


def test_audit_pdf_export_binary_empty_none_or_non_pdf():
    from backend.services.project_export_service import audit_pdf_export_binary

    for empty_val in (None, b"", bytearray(), "not-bytes"):
        res = audit_pdf_export_binary(empty_val)  # type: ignore[arg-type]
        assert res == {
            "is_valid_pdf_header": False,
            "has_eof_marker": False,
            "byte_size": 0,
            "estimated_page_count": 0,
            "is_export_ready": False,
        }

    non_pdf_bytes = b"PK\x03\x04 fake zip archive with /Type /Page and %%EOF" + (b"x" * 120)
    non_pdf_res = audit_pdf_export_binary(non_pdf_bytes)
    assert non_pdf_res["is_valid_pdf_header"] is False
    assert non_pdf_res["estimated_page_count"] == 0
    assert non_pdf_res["is_export_ready"] is False


# ── summarize_executive_report_risk_posture (PMBOK §11.7, pure helper) ─────


def test_risk_posture_unassessed():
    """Sin RISK RAID ni CCB pendientes → 'unassessed' con población 0."""
    from backend.services.project_export_service import summarize_executive_report_risk_posture

    for report in (None, {}, {"raid_kpis": {}, "ccb_and_quality_summary": {}}):
        result = summarize_executive_report_risk_posture(report)
        assert result == {
            "total_risks": 0,
            "critical_risks": 0,
            "high_risks": 0,
            "elevated_risks_count": 0,
            "elevated_risk_share_pct": 0.0,
            "pending_ccb_changes": 0,
            "requires_sponsor_escalation": False,
            "risk_posture_status": "unassessed",
        }
    # RAID no-dict se ignora
    assert summarize_executive_report_risk_posture({"raid_kpis": "n/a"})["risk_posture_status"] == "unassessed"


def test_risk_posture_controlled():
    """Riesgos mapeados sin elevados ni pendientes CCB → 'controlled'."""
    from backend.services.project_export_service import summarize_executive_report_risk_posture

    result = summarize_executive_report_risk_posture(
        {
            "raid_kpis": {"total_risks": 4, "critical_risks_count": 0, "high_risks_count": 0},
            "ccb_and_quality_summary": {"pending_ccb_count": 0},
        }
    )
    assert result == {
        "total_risks": 4,
        "critical_risks": 0,
        "high_risks": 0,
        "elevated_risks_count": 0,
        "elevated_risk_share_pct": 0.0,
        "pending_ccb_changes": 0,
        "requires_sponsor_escalation": False,
        "risk_posture_status": "controlled",
    }
    # 1 riesgo alto sin otros pendientes → 'watch_list' (per spec)
    watch = summarize_executive_report_risk_posture(
        {
            "raid_kpis": {"total_risks": 4, "critical_risks_count": 0, "high_risks_count": 1},
            "ccb_and_quality_summary": {"pending_ccb_count": 0},
        }
    )
    assert watch["elevated_risk_share_pct"] == 25.0
    assert watch["risk_posture_status"] == "watch_list"


def test_risk_posture_watch_list():
    """Riesgo elevado o pendiente CCB (sin umbral de escalado) → 'watch_list'."""
    from backend.services.project_export_service import (
        ProjectExportService,
        summarize_executive_report_risk_posture,
    )

    result_altas = summarize_executive_report_risk_posture(
        {
            "raid_kpis": {"total_risks": 6, "critical_risks_count": 0, "high_risks_count": 2},
            "ccb_and_quality_summary": {"pending_ccb_count": 1},
        }
    )
    assert result_altas["elevated_risks_count"] == 2
    assert result_altas["elevated_risk_share_pct"] == round(2 / 6 * 100.0, 2)
    assert result_altas["requires_sponsor_escalation"] is False
    assert result_altas["risk_posture_status"] == "watch_list"

    result_pendiente = summarize_executive_report_risk_posture(
        {
            "raid_kpis": {"total_risks": 2, "high_risks": 0},
            "ccb_and_quality_summary": {"pending_ccb_count": 2},
        }
    )
    assert result_pendiente["pending_ccb_changes"] == 2
    assert result_pendiente["risk_posture_status"] == "watch_list"

    # Facade de clase expone el mismo resultado
    facade = ProjectExportService.summarize_executive_report_risk_posture(
        result_altas if False else {
            "raid_kpis": {"total_risks": 6, "critical_risks_count": 0, "high_risks_count": 2},
            "ccb_and_quality_summary": {"pending_ccb_count": 1},
        }
    )
    assert facade == result_altas


def test_risk_posture_sponsor_escalation_by_critical_risk():
    """1 riesgo crítico → 'sponsor_escalation' (se expone en __all__)."""
    import backend.services.project_export_service as export_module
    from backend.services.project_export_service import summarize_executive_report_risk_posture

    result = summarize_executive_report_risk_posture(
        {
            "raid_kpis": {"total_risks": 5, "critical_risks_count": 1, "high_risks_count": 1},
            "ccb_and_quality_summary": {"pending_ccb_count": 1},
        }
    )
    assert result["elevated_risks_count"] == 2
    assert result["requires_sponsor_escalation"] is True
    assert result["risk_posture_status"] == "sponsor_escalation"

    # high_risks >= 3 también escala
    result_altas = summarize_executive_report_risk_posture(
        {"raid_kpis": {"total_risks": 3, "high_risks_count": 3}}
    )
    assert result_altas["requires_sponsor_escalation"] is True
    assert result_altas["risk_posture_status"] == "sponsor_escalation"

    assert "summarize_executive_report_risk_posture" in export_module.__all__


def test_risk_posture_sponsor_escalation_by_pending_ccb():
    """≥ 3 CRs pendientes de dictamen → 'sponsor_escalation' aún con 0 riesgos."""
    from backend.services.project_export_service import summarize_executive_report_risk_posture

    result = summarize_executive_report_risk_posture(
        {"ccb_and_quality_summary": {"pending_ccb_count": 3}}
    )
    assert result["pending_ccb_changes"] == 3
    assert result["requires_sponsor_escalation"] is True
    # total_risks == 0 pero pending > 0 → no 'unassessed'
    assert result["risk_posture_status"] == "sponsor_escalation"


# ── audit_expenses_csv_financial_totals (PMBOK §7.4, pure helper) ───────────


def test_audit_expenses_csv_financial_totals_reconciled():
    """CSV con BOM UTF-8 y columna Monto reconciliado contra AC esperado -> 'reconciled'."""
    from backend.services.project_export_service import (
        ProjectExportService,
        audit_expenses_csv_financial_totals,
    )

    csv_text = "\ufeffID,Categoría,Monto,Estado\n1,Equipos,1250.50,paid\n2,Servicios,'$749.50,paid\n"
    res = audit_expenses_csv_financial_totals(csv_text, expected_ac_total=2000.0)
    assert res == {
        "amount_column_name": "Monto",
        "valid_amount_rows": 2,
        "invalid_amount_rows": 0,
        "csv_sum_amount": 2000.0,
        "expected_ac_total": 2000.0,
        "reconciliation_delta": 0.0,
        "is_reconciled": True,
        "reconciliation_status": "reconciled",
    }
    assert (
        ProjectExportService.audit_expenses_csv_financial_totals(
            csv_text.encode("utf-8"), expected_ac_total=2000.0
        )
        == res
    )


def test_audit_expenses_csv_financial_totals_discrepancy_detected():
    """Suma CSV distinta del AC esperado fuera de tolerancia -> 'discrepancy_detected'."""
    from backend.services.project_export_service import audit_expenses_csv_financial_totals

    csv_text = "ID,Amount\n1,1000.00\n2,500.00\n"
    res = audit_expenses_csv_financial_totals(csv_text, expected_ac_total=1800.0)
    assert res["csv_sum_amount"] == 1500.0
    assert res["expected_ac_total"] == 1800.0
    assert res["reconciliation_delta"] == -300.0
    assert res["is_reconciled"] is False
    assert res["reconciliation_status"] == "discrepancy_detected"


def test_audit_expenses_csv_financial_totals_parse_errors_and_missing_column():
    """Fila con importe inválido ('N/A') -> 'parse_errors_detected', y sin columna de importe -> 'missing_amount_column'."""
    from backend.services.project_export_service import audit_expenses_csv_financial_totals

    bad_row_csv = "ID,Monto\n1,500.00\n2,N/A\n"
    bad_res = audit_expenses_csv_financial_totals(bad_row_csv, expected_ac_total=500.0)
    assert bad_res["valid_amount_rows"] == 1
    assert bad_res["invalid_amount_rows"] == 1
    assert bad_res["is_reconciled"] is False
    assert bad_res["reconciliation_status"] == "parse_errors_detected"

    no_col_csv = "ID,Título,Estado\n1,Gasto A,paid\n"
    no_col_res = audit_expenses_csv_financial_totals(no_col_csv, expected_ac_total=0.0)
    assert no_col_res["amount_column_name"] is None
    assert no_col_res["is_reconciled"] is False
    assert no_col_res["reconciliation_status"] == "missing_amount_column"


def test_audit_expenses_csv_financial_totals_empty_or_none():
    """None o cadena vacía -> 'empty_export' e is_reconciled=False."""
    from backend.services.project_export_service import audit_expenses_csv_financial_totals

    for empty_val in (None, "", "   \n  ", b""):
        res = audit_expenses_csv_financial_totals(empty_val, expected_ac_total=100.0)
        assert res["amount_column_name"] is None
        assert res["csv_sum_amount"] == 0.0
        assert res["is_reconciled"] is False
        assert res["reconciliation_status"] == "empty_export"


# ── audit_tasks_csv_schedule_completeness (PMBOK §6.5 / §9.3, pure helper) ──


def test_audit_tasks_csv_schedule_completeness_fully_baselined():
    """Todas las filas tienen Responsable y Fecha Límite válidos -> 'fully_baselined' con 100.0%."""
    from backend.services.project_export_service import (
        ProjectExportService,
        audit_tasks_csv_schedule_completeness,
    )

    csv_text = (
        "\ufeffID,Título,Responsable,Fecha Límite\n"
        "1,Diseño WBS,Ana Gómez,2026-10-20\n"
        "2,Aprobación Charter,Carlos Ruiz,2026-10-25\n"
    )
    res = audit_tasks_csv_schedule_completeness(csv_text)
    assert res == {
        "total_tasks": 2,
        "dated_tasks_count": 2,
        "assigned_tasks_count": 2,
        "fully_scheduled_tasks_count": 2,
        "unscheduled_tasks_count": 0,
        "schedule_coverage_pct": 100.0,
        "schedule_completeness_status": "fully_baselined",
    }
    assert (
        ProjectExportService.audit_tasks_csv_schedule_completeness(
            csv_text.encode("utf-8")
        )
        == res
    )


def test_audit_tasks_csv_schedule_completeness_partial_and_critical_gaps():
    """Valida cobertura del 75% ('partial_schedule_gaps') y 25% ('critical_unscheduled_backlog')."""
    from backend.services.project_export_service import (
        audit_tasks_csv_schedule_completeness,
    )

    partial_csv = (
        "ID,Título,Responsable,Fecha Límite\n"
        "1,Tarea 1,Ana,2026-10-20\n"
        "2,Tarea 2,Luis,2026-10-21\n"
        "3,Tarea 3,Pedro,2026-10-22\n"
        "4,Tarea 4,Sin asignar,N/A\n"
    )
    partial_res = audit_tasks_csv_schedule_completeness(partial_csv)
    assert partial_res["total_tasks"] == 4
    assert partial_res["fully_scheduled_tasks_count"] == 3
    assert partial_res["unscheduled_tasks_count"] == 1
    assert partial_res["schedule_coverage_pct"] == 75.0
    assert partial_res["schedule_completeness_status"] == "partial_schedule_gaps"

    critical_csv = (
        "ID,Título,Responsable,Fecha Límite\n"
        "1,Tarea 1,Ana,2026-10-20\n"
        "2,Tarea 2,Sin asignar,2026-10-21\n"
        "3,Tarea 3,Luis,N/A\n"
        "4,Tarea 4,-,Sin fecha\n"
    )
    critical_res = audit_tasks_csv_schedule_completeness(critical_csv)
    assert critical_res["total_tasks"] == 4
    assert critical_res["dated_tasks_count"] == 2
    assert critical_res["assigned_tasks_count"] == 2
    assert critical_res["fully_scheduled_tasks_count"] == 1
    assert critical_res["unscheduled_tasks_count"] == 3
    assert critical_res["schedule_coverage_pct"] == 25.0
    assert (
        critical_res["schedule_completeness_status"] == "critical_unscheduled_backlog"
    )


def test_audit_tasks_csv_schedule_completeness_missing_columns():
    """CSV sin columna de fecha o responsable -> 'missing_schedule_columns'."""
    from backend.services.project_export_service import (
        audit_tasks_csv_schedule_completeness,
    )

    no_due_csv = "ID,Título,Responsable\n1,Tarea A,Ana Gómez\n"
    res = audit_tasks_csv_schedule_completeness(no_due_csv)
    assert res["total_tasks"] == 1
    assert res["dated_tasks_count"] == 0
    assert res["assigned_tasks_count"] == 1
    assert res["fully_scheduled_tasks_count"] == 0
    assert res["schedule_completeness_status"] == "missing_schedule_columns"


def test_audit_tasks_csv_schedule_completeness_empty_or_headers_only():
    """None, cadena vacía o solo encabezados sin tareas -> 'empty_export' con total_tasks == 0."""
    from backend.services.project_export_service import (
        audit_tasks_csv_schedule_completeness,
    )

    for val in (None, "", "   \n ", "ID,Título,Responsable,Fecha Límite\n"):
        res = audit_tasks_csv_schedule_completeness(val)
        assert res["total_tasks"] == 0
        assert res["schedule_coverage_pct"] == 0.0
        assert res["schedule_completeness_status"] == "empty_export"


# ── audit_executive_report_milestone_coverage (PMBOK §10.2, pure helper) ────


def test_audit_executive_report_milestone_coverage_comprehensive():
    """Hitos, KPIs financieros y marcadores de completitud sin atrasos -> 'COMPREHENSIVE_EXECUTIVE_SUMMARY' (100.0)."""
    from backend.services.project_export_service import (
        ProjectExportService,
        audit_executive_report_milestone_coverage,
    )

    html = (
        "<h2>Hitos del Cronograma</h2>"
        "<p>Fase 1 completada al 100%. Entregable finalizado y cumplido.</p>"
        "<p>Indicadores EVM: Presupuesto BAC $50,000, CPI 1.05, SPI 1.02.</p>"
    )
    res = audit_executive_report_milestone_coverage(html)
    assert res == {
        "has_milestone_section": True,
        "completed_markers_count": 4,
        "overdue_or_delayed_markers_count": 0,
        "financial_kpi_mentions": 4,
        "coverage_score": 100.0,
        "posture": "COMPREHENSIVE_EXECUTIVE_SUMMARY",
    }
    assert ProjectExportService.audit_executive_report_milestone_coverage(html) == res


def test_audit_executive_report_milestone_coverage_executive_attention_required():
    """Cualquier marcador de atraso o bloqueo activa 'EXECUTIVE_ATTENTION_REQUIRED' incluso con score 100.0."""
    from backend.services.project_export_service import (
        audit_executive_report_milestone_coverage,
    )

    html = (
        "<h2>Seguimiento de Milestone</h2>"
        "<p>Hito 1 completado, pero el entregable 2 está retrasado y vencido por bloqueo externo.</p>"
        "<p>Presupuesto y gasto monitoreados con EAC y VAC.</p>"
    )
    res = audit_executive_report_milestone_coverage(html)
    assert res["has_milestone_section"] is True
    assert res["completed_markers_count"] == 1
    assert res["overdue_or_delayed_markers_count"] == 2
    assert res["financial_kpi_mentions"] == 4
    assert res["coverage_score"] == 100.0
    assert res["posture"] == "EXECUTIVE_ATTENTION_REQUIRED"


def test_audit_executive_report_milestone_coverage_partial_coverage():
    """Reporte parcial sin algunas dimensiones y sin atrasos -> 'PARTIAL_REPORT_COVERAGE' (< 80.0)."""
    from backend.services.project_export_service import (
        audit_executive_report_milestone_coverage,
    )

    only_milestone_html = "<h2>Cronograma de Fases</h2><p>Planificación preliminar en curso.</p>"
    res_m = audit_executive_report_milestone_coverage(only_milestone_html)
    assert res_m == {
        "has_milestone_section": True,
        "completed_markers_count": 0,
        "overdue_or_delayed_markers_count": 0,
        "financial_kpi_mentions": 0,
        "coverage_score": 40.0,
        "posture": "PARTIAL_REPORT_COVERAGE",
    }

    milestone_and_finance_html = (
        "<h2>Hitos del Proyecto</h2><p>Presupuesto aprobado con CPI 1.00.</p>"
    )
    res_mf = audit_executive_report_milestone_coverage(milestone_and_finance_html)
    assert res_mf["coverage_score"] == 70.0
    assert res_mf["posture"] == "PARTIAL_REPORT_COVERAGE"


def test_audit_executive_report_milestone_coverage_empty_or_none():
    """None o texto en blanco -> 'EMPTY_REPORT' con coverage_score 0.0."""
    from backend.services.project_export_service import (
        audit_executive_report_milestone_coverage,
    )

    for empty_val in (None, "", "   \n\t  "):
        res = audit_executive_report_milestone_coverage(empty_val)
        assert res == {
            "has_milestone_section": False,
            "completed_markers_count": 0,
            "overdue_or_delayed_markers_count": 0,
            "financial_kpi_mentions": 0,
            "coverage_score": 0.0,
            "posture": "EMPTY_REPORT",
        }


# ── audit_risks_csv_register_completeness (PMBOK §11.2, pure helper) ────────


def test_audit_risks_csv_register_completeness_audit_ready():
    """Mitigación >= 80% y 100% responsables y puntajes P×I -> 'AUDIT_READY_RISK_REGISTER'."""
    import backend.services.project_export_service as export_module
    from backend.services.project_export_service import (
        ProjectExportService,
        audit_risks_csv_register_completeness,
    )

    csv_text = (
        "\ufeffID,Riesgo,Probabilidad,Impacto,Responsable,Mitigación\n"
        "1,Falla eléctrica,3,4,Ana Gómez,Planta de respaldo UPS\n"
        "2,Retraso aduana,2,3,Carlos Ruiz,Compra local anticipada\n"
        "3,Rotación clave,2,4,Elena Paz,Documentación cruzada\n"
        "4,Cambio alcance,1,2,Luis Mora,Control estricto CCB\n"
        "5,Riesgo menor,1,1,Pedro Gil,N/A\n"
    )
    res = audit_risks_csv_register_completeness(csv_text)
    assert res == {
        "total_rows": 5,
        "mitigation_documented_rows": 4,
        "owner_assigned_rows": 5,
        "scored_rows": 5,
        "mitigation_coverage_pct": 80.0,
        "posture": "AUDIT_READY_RISK_REGISTER",
    }
    assert ProjectExportService.audit_risks_csv_register_completeness(csv_text) == res
    assert "audit_risks_csv_register_completeness" in export_module.__all__


def test_audit_risks_csv_register_completeness_unmitigated_exposure_gaps():
    """Cobertura de mitigación < 50% -> 'UNMITIGATED_EXPOSURE_GAPS'."""
    from backend.services.project_export_service import (
        audit_risks_csv_register_completeness,
    )

    csv_text = (
        "ID,Probability,Impact,Owner,Mitigation_Plan\n"
        "1,4,5,Ana,Contrato redundante activo\n"
        "2,3,4,Luis,TBD\n"
        "3,2,3,Pedro,\n"
    )
    res = audit_risks_csv_register_completeness(csv_text)
    assert res == {
        "total_rows": 3,
        "mitigation_documented_rows": 1,
        "owner_assigned_rows": 3,
        "scored_rows": 3,
        "mitigation_coverage_pct": 33.33,
        "posture": "UNMITIGATED_EXPOSURE_GAPS",
    }


def test_audit_risks_csv_register_completeness_partial_governance():
    """Mitigación >= 50% pero faltan responsables o puntajes (o mitigación < 80%) -> 'PARTIAL_REGISTER_GOVERNANCE'."""
    from backend.services.project_export_service import (
        audit_risks_csv_register_completeness,
    )

    csv_text = (
        "ID,Probabilidad,Impacto,Propietario,Plan_Mitigacion\n"
        "1,3,4,Ana,Plan de contingencia A\n"
        "2,2,,   ,Plan de contingencia B\n"
    )
    res = audit_risks_csv_register_completeness(csv_text)
    assert res == {
        "total_rows": 2,
        "mitigation_documented_rows": 2,
        "owner_assigned_rows": 1,
        "scored_rows": 1,
        "mitigation_coverage_pct": 100.0,
        "posture": "PARTIAL_REGISTER_GOVERNANCE",
    }


def test_audit_risks_csv_register_completeness_empty_export():
    """None, cadena vacía o solo cabeceras sin filas de datos -> 'EMPTY_RISK_EXPORT'."""
    from backend.services.project_export_service import (
        audit_risks_csv_register_completeness,
    )

    for empty_val in (
        None,
        "",
        "   \n ",
        "ID,Probabilidad,Impacto,Responsable,Mitigación\n",
        "ID,Probabilidad,Impacto,Responsable,Mitigación\n,,,,\n",
    ):
        res = audit_risks_csv_register_completeness(empty_val)
        assert res == {
            "total_rows": 0,
            "mitigation_documented_rows": 0,
            "owner_assigned_rows": 0,
            "scored_rows": 0,
            "mitigation_coverage_pct": 0.0,
            "posture": "EMPTY_RISK_EXPORT",
        }


# ─── audit_stakeholders_csv_engagement_gaps (pure helper) ─────────


def test_stakeholders_csv_engagement_strong_coalition():
    """Mayoría supportive/líder (>= 75%) sin resistentes -> STRONG_STAKEHOLDER_COALITION."""
    from backend.services.project_export_service import (
        audit_stakeholders_csv_engagement_gaps,
    )

    csv_content = (
        "Nombre,Poder,Engagement\n"
        "Pastor,High,Leading\n"
        "CEO,Alta,Apoyo\n"
        "Tesorero,critical,Líder\n"
        "Voluntario,low,Neutral\n"
    )

    res = audit_stakeholders_csv_engagement_gaps(csv_content)

    assert res["total_rows"] == 4
    # 'influencia' puede también barajearse vía alias: 3 de 4 en high/alta/critical.
    assert res["high_power_rows"] == 3
    assert res["supportive_or_leading_rows"] == 3
    assert res["resistant_or_unaware_rows"] == 0
    assert res["alignment_rate"] == 75.0
    assert res["posture"] == "STRONG_STAKEHOLDER_COALITION"


def test_stakeholders_csv_engagement_critical_resistance():
    """Filas resistant/unaware -> CRITICAL_ENGAGEMENT_RESISTANCE aunque haya mayoría positiva."""
    from backend.services.project_export_service import (
        audit_stakeholders_csv_engagement_gaps,
    )

    csv_content = (
        "Nombre,Influencia,Compromiso\n"
        "Ministro,5,Resistente\n"
        "Encargado,4,Desconocedor\n"
        "Lider,high,Apoyo\n"
    )

    res = audit_stakeholders_csv_engagement_gaps(csv_content)

    assert res["total_rows"] == 3
    assert res["high_power_rows"] == 3
    assert res["resistant_or_unaware_rows"] == 2
    assert res["supportive_or_leading_rows"] == 1
    assert res["alignment_rate"] == 33.33
    assert res["posture"] == "CRITICAL_ENGAGEMENT_RESISTANCE"


def test_stakeholders_csv_engagement_neutral_single_and_aliases():
    """Sin resistentes y < 75% alignment -> NEUTRAL_ENGAGEMENT_POSTURE; aliases españoles soportados."""
    from backend.services.project_export_service import (
        audit_stakeholders_csv_engagement_gaps,
    )

    csv_content = (
        "Nombre,Poder,Postura\n"
        "Anciano,low,apoyo\n"
        "Vecino,low,neutral\n"
    )

    res = audit_stakeholders_csv_engagement_gaps(csv_content)

    assert res["total_rows"] == 2
    assert res["high_power_rows"] == 0
    assert res["supportive_or_leading_rows"] == 1
    assert res["alignment_rate"] == 50.0
    assert res["posture"] == "NEUTRAL_ENGAGEMENT_POSTURE"


def test_stakeholders_csv_engagement_empty_export():
    """None, cadena vacía, BOM o solo cabeceras/filas vacías -> EMPTY_STAKEHOLDER_EXPORT."""
    from backend.services.project_export_service import (
        audit_stakeholders_csv_engagement_gaps,
    )

    for empty_val in (
        None,
        "",
        "   \n ",
        "\ufeffNombre,Poder,Engagement\n",
        "Nombre,Poder,Engagement\n,,\n",
    ):
        res = audit_stakeholders_csv_engagement_gaps(empty_val)
        assert res == {
            "total_rows": 0,
            "high_power_rows": 0,
            "resistant_or_unaware_rows": 0,
            "supportive_or_leading_rows": 0,
            "alignment_rate": 0.0,
            "posture": "EMPTY_STAKEHOLDER_EXPORT",
        }


def test_audit_expenses_vendor_concentration_diversified():
    """Todas las filas con proveedor y ninguno concentra >= 70% (con >= 2 filas) -> 'DIVERSIFIED_PROCUREMENT_POSTURE'."""
    from backend.services.project_export_service import (
        ProjectExportService,
        audit_expenses_vendor_concentration,
    )

    csv_content = (
        "Concepto,Proveedor,Monto\n"
        'Licencias Cloud,AWS,"$4,000.00"\n'
        'Consultoría QA,DevSecOps SAS,"$3,500.00"\n'
        'Hardware, TechCorp ,"$2,500.00"\n'
    )
    res = ProjectExportService.audit_expenses_vendor_concentration(csv_content)
    assert res == {
        "total_rows": 3,
        "total_spend": 10000.0,
        "vendor_documented_rows": 3,
        "unique_vendors_count": 3,
        "top_vendor_share_pct": 40.0,
        "posture": "DIVERSIFIED_PROCUREMENT_POSTURE",
    }
    assert audit_expenses_vendor_concentration(csv_content) == res


def test_audit_expenses_vendor_concentration_single_source_risk():
    """Todas con proveedor, >= 2 filas y top_vendor_share_pct >= 70.0 -> 'SINGLE_SOURCE_CONCENTRATION_RISK'."""
    from backend.services.project_export_service import (
        audit_expenses_vendor_concentration,
    )

    csv_content = (
        "Item,Vendor,Amount\n"
        "Fase 1,MegaVendor,5000\n"
        "Fase 2,megavendor,3000\n"
        "Soporte,OtroProveedor,2000\n"
    )
    res = audit_expenses_vendor_concentration(csv_content)
    assert res["total_rows"] == 3
    assert res["total_spend"] == 10000.0
    assert res["vendor_documented_rows"] == 3
    assert res["unique_vendors_count"] == 2
    assert res["top_vendor_share_pct"] == 80.0
    assert res["posture"] == "SINGLE_SOURCE_CONCENTRATION_RISK"


def test_audit_expenses_vendor_concentration_unattributed_vendor():
    """Al menos una fila sin proveedor documentado -> 'UNATTRIBUTED_VENDOR_SPEND'."""
    from backend.services.project_export_service import (
        audit_expenses_vendor_concentration,
    )

    csv_content = (
        "Concepto,Beneficiario,Importe\n"
        "Suministros,Proveedor A,1500.50\n"
        "Caja menor,   ,499.50\n"
    )
    res = audit_expenses_vendor_concentration(csv_content)
    assert res["total_rows"] == 2
    assert res["total_spend"] == 2000.0
    assert res["vendor_documented_rows"] == 1
    assert res["unique_vendors_count"] == 1
    assert res["top_vendor_share_pct"] == 75.02
    assert res["posture"] == "UNATTRIBUTED_VENDOR_SPEND"


def test_audit_expenses_vendor_concentration_empty_export():
    """CSV vacío, None o solo encabezados -> 'EMPTY_EXPENSES_EXPORT'."""
    from backend.services.project_export_service import (
        audit_expenses_vendor_concentration,
    )

    for empty_csv in (None, "", "  \n ", "Concepto,Proveedor,Monto\n,,\n"):
        res = audit_expenses_vendor_concentration(empty_csv)
        assert res == {
            "total_rows": 0,
            "total_spend": 0.0,
            "vendor_documented_rows": 0,
            "unique_vendors_count": 0,
            "top_vendor_share_pct": 0.0,
            "posture": "EMPTY_EXPENSES_EXPORT",
        }


def test_audit_executive_report_change_governance_baseline_governed():
    """Decisiones con acta CCB y pendientes < 50% -> 'BASELINE_GOVERNED'."""
    from backend.services.project_export_service import (
        ProjectExportService,
        audit_executive_report_change_governance,
    )

    report_data = {
        "baseline_version": "v2.1",
        "baseline_locked": True,
        "change_requests": [
            {
                "id": "CR-101",
                "status": "APPROVED",
                "cost_impact": 12500.5,
                "schedule_impact_days": 5,
                "ccb_minutes_ref": "ACTA-CCB-2026-01",
            },
            {
                "code": "CR-102",
                "status": "approved",
                "cost_impact": -2500.25,
                "schedule_impact_days": 2.5,
                "has_ccb_minutes": True,
            },
            {
                "id": "CR-103",
                "status": "REJECTED",
                "cost_impact": 50000.0,
                "schedule_impact_days": 20,
                "has_ccb_minutes": True,
            },
            {
                "id": "CR-104",
                "status": "PENDING",
                "cost_impact": 3000.0,
                "schedule_impact_days": 1,
            },
        ],
    }

    res = ProjectExportService.audit_executive_report_change_governance(report_data)
    assert res["total_requests"] == 4
    assert res["approved_count"] == 2
    assert res["rejected_count"] == 1
    assert res["pending_count"] == 1
    assert res["untraceable_decisions"] == []
    assert res["net_approved_cost_impact"] == 10000.25
    assert res["net_approved_schedule_days"] == 7.5
    assert res["governance_posture"] == "BASELINE_GOVERNED"
    assert isinstance(res["recommendations"], list) and len(res["recommendations"]) >= 1
    assert audit_executive_report_change_governance(report_data) == res


def test_audit_executive_report_change_governance_uncontrolled_changes():
    """Solicitudes APPROVED o REJECTED sin acta CCB -> 'UNCONTROLLED_CHANGES'."""
    from backend.services.project_export_service import (
        audit_executive_report_change_governance,
    )

    report_data = {
        "ccb_requests": [
            {
                "id": "CR-201",
                "status": "APPROVED",
                "cost_impact": 8000.0,
                "schedule_impact_days": 4,
                "has_ccb_minutes": False,
                "ccb_minutes_ref": "   ",
            },
            {
                "code": "CR-202",
                "status": "REJECTED",
                "cost_impact": 1500.0,
                "schedule_impact_days": 0,
            },
            {
                "id": "CR-203",
                "status": "PENDING",
                "cost_impact": 500.0,
                "schedule_impact_days": 1,
            },
        ]
    }

    res = audit_executive_report_change_governance(report_data)
    assert res["total_requests"] == 3
    assert res["approved_count"] == 1
    assert res["rejected_count"] == 1
    assert res["pending_count"] == 1
    assert res["untraceable_decisions"] == ["CR-201", "CR-202"]
    assert res["net_approved_cost_impact"] == 8000.0
    assert res["net_approved_schedule_days"] == 4.0
    assert res["governance_posture"] == "UNCONTROLLED_CHANGES"
    assert len(res["recommendations"]) >= 1


def test_audit_executive_report_change_governance_pending_backlog_bottleneck():
    """Sin decisiones sin traza pero pending_count / total_requests >= 0.5 -> 'PENDING_BACKLOG_BOTTLENECK'."""
    from backend.services.project_export_service import (
        audit_executive_report_change_governance,
    )

    report_data = {
        "change_requests": [
            {
                "id": "CR-301",
                "status": "APPROVED",
                "cost_impact": 4200.0,
                "schedule_impact_days": 3,
                "ccb_minutes_ref": "CCB-MIN-09",
            },
            {"id": "CR-302", "status": "PENDING", "cost_impact": 1000.0},
            {"id": "CR-303", "status": "pending", "schedule_impact_days": 5},
            {"id": "CR-304", "status": "DEFERRED"},
        ]
    }

    res = audit_executive_report_change_governance(report_data)
    assert res["total_requests"] == 4
    assert res["approved_count"] == 1
    assert res["pending_count"] == 2
    assert res["untraceable_decisions"] == []
    assert res["net_approved_cost_impact"] == 4200.0
    assert res["net_approved_schedule_days"] == 3.0
    assert res["governance_posture"] == "PENDING_BACKLOG_BOTTLENECK"


def test_audit_executive_report_change_governance_no_change_activity():
    """Sin solicitudes de cambio o payload None/vacío -> 'NO_CHANGE_ACTIVITY'."""
    from backend.services.project_export_service import (
        audit_executive_report_change_governance,
    )

    for empty_payload in (None, {}, {"change_requests": []}):
        res = audit_executive_report_change_governance(empty_payload)
        assert res["total_requests"] == 0
        assert res["approved_count"] == 0
        assert res["rejected_count"] == 0
        assert res["pending_count"] == 0
        assert res["untraceable_decisions"] == []
        assert res["net_approved_cost_impact"] == 0.0
        assert res["net_approved_schedule_days"] == 0.0
        assert res["governance_posture"] == "NO_CHANGE_ACTIVITY"
        assert isinstance(res["recommendations"], list)


# ── PMI PMBOK §8.2 & §10.2 Executive Report Quality Disclosure Auditor ───────


def test_audit_executive_report_quality_disclosure_proactive_governance():
    """Conformidad >= no conformidad y cobertura DoD >= 80% -> 'PROACTIVE_QUALITY_GOVERNANCE'."""
    import backend.services.project_export_service as export_module
    from backend.services.project_export_service import (
        ProjectExportService,
        audit_executive_report_quality_disclosure,
    )

    report_data = {
        "ccb_quality_summary": {
            "coq_by_category": {
                "prevention": 3500.0,
                "appraisal": 1500.0,
                "internal_failure": 800.0,
                "external_failure": 200.0,
            },
            "tasks_dod_accepted_count": 9,
            "total_completed_tasks": 10,
        }
    }

    res = ProjectExportService.audit_executive_report_quality_disclosure(report_data)
    assert res["conformance_cost"] == 5000.0
    assert res["nonconformance_cost"] == 1000.0
    assert res["total_coq_cost"] == 6000.0
    assert res["conformance_ratio_pct"] == 83.33
    assert res["dod_acceptance_coverage_pct"] == 90.0
    assert res["quality_disclosure_posture"] == "PROACTIVE_QUALITY_GOVERNANCE"
    assert len(res["recommendations"]) >= 1
    assert audit_executive_report_quality_disclosure(report_data) == res
    assert "audit_executive_report_quality_disclosure" in export_module.__all__


def test_audit_executive_report_quality_disclosure_failure_cost_dominated():
    """nonconformance_cost > conformance_cost -> 'FAILURE_COST_DOMINATED'."""
    from backend.services.project_export_service import (
        audit_executive_report_quality_disclosure,
    )

    report_data = {
        "quality_kpis": {
            "prevention": 600.0,
            "appraisal": 400.0,
            "internal_failure": 1800.0,
            "external_failure": 1200.0,
            "tasks_dod_accepted_count": 8,
            "total_completed_tasks": 8,
        }
    }

    res = audit_executive_report_quality_disclosure(report_data)
    assert res["conformance_cost"] == 1000.0
    assert res["nonconformance_cost"] == 3000.0
    assert res["total_coq_cost"] == 4000.0
    assert res["conformance_ratio_pct"] == 25.0
    assert res["dod_acceptance_coverage_pct"] == 100.0
    assert res["quality_disclosure_posture"] == "FAILURE_COST_DOMINATED"
    assert len(res["recommendations"]) >= 1


def test_audit_executive_report_quality_disclosure_unverified_completed_deliverables():
    """CoQ balanceado pero cobertura DoD < 80% -> 'UNVERIFIED_COMPLETED_DELIVERABLES'."""
    from backend.services.project_export_service import (
        audit_executive_report_quality_disclosure,
    )

    report_data = {
        "coq_by_category": {
            "prevention": 2000.0,
            "appraisal": 1000.0,
            "internal_failure": 500.0,
            "external_failure": 0.0,
        },
        "tasks_dod_accepted_count": 3,
        "total_completed_tasks": 5,
    }

    res = audit_executive_report_quality_disclosure(report_data)
    assert res["conformance_cost"] == 3000.0
    assert res["nonconformance_cost"] == 500.0
    assert res["total_coq_cost"] == 3500.0
    assert res["conformance_ratio_pct"] == 85.71
    assert res["dod_acceptance_coverage_pct"] == 60.0
    assert res["quality_disclosure_posture"] == "UNVERIFIED_COMPLETED_DELIVERABLES"
    assert len(res["recommendations"]) >= 1


def test_audit_executive_report_quality_disclosure_no_metrics_disclosed():
    """Sin costos CoQ ni tareas completadas/aceptadas -> 'NO_QUALITY_METRICS_DISCLOSED'."""
    from backend.services.project_export_service import (
        audit_executive_report_quality_disclosure,
    )

    for payload in (None, {}, {"ccb_quality_summary": {}}):
        res = audit_executive_report_quality_disclosure(payload)
        assert res["conformance_cost"] == 0.0
        assert res["nonconformance_cost"] == 0.0
        assert res["total_coq_cost"] == 0.0
        assert res["conformance_ratio_pct"] == 0.0
        assert res["dod_acceptance_coverage_pct"] == 0.0
        assert res["quality_disclosure_posture"] == "NO_QUALITY_METRICS_DISCLOSED"
        assert len(res["recommendations"]) == 1


# ── PMI PMBOK §9.6 & §10.2 Executive Report Resource Workload Auditor ────────


def test_audit_executive_report_resource_workload_balanced_capacity():
    """Todos los miembros con utilization_pct <= 100.0 -> 'BALANCED_TEAM_CAPACITY'."""
    import backend.services.project_export_service as export_module
    from backend.services.project_export_service import (
        ProjectExportService,
        audit_executive_report_resource_workload,
    )

    report_data = {
        "resource_allocations": [
            {"id": "MEM-01", "utilization_pct": 85.0, "overdue_tasks": 0},
            {
                "member_id": "MEM-02",
                "allocated_hours": 32.0,
                "capacity_hours": 40.0,
                "overdue_tasks": 1,
            },
            {"name": "MEM-03", "utilization_pct": 25.0, "overdue_tasks": 0},
        ]
    }

    res = ProjectExportService.audit_executive_report_resource_workload(report_data)
    assert res["total_members"] == 3
    assert res["overallocated_member_ids"] == []
    assert res["underutilized_member_ids"] == ["MEM-03"]
    assert res["bottleneck_member_ids"] == []
    assert res["average_utilization_pct"] == 63.33
    assert res["workload_posture"] == "BALANCED_TEAM_CAPACITY"
    assert len(res["recommendations"]) >= 1
    assert audit_executive_report_resource_workload(report_data) == res
    assert "audit_executive_report_resource_workload" in export_module.__all__


def test_audit_executive_report_resource_workload_critical_bottleneck_overload():
    """Al menos un miembro con utilization_pct > 100.0 y overdue_tasks > 0 -> 'CRITICAL_BOTTLENECK_OVERLOAD'."""
    from backend.services.project_export_service import (
        audit_executive_report_resource_workload,
    )

    report_data = {
        "team_workload": [
            {"id": "MEM-10", "utilization_pct": 125.0, "overdue_tasks": 3},
            {"id": "MEM-11", "utilization_pct": 110.0, "overdue_tasks": 0},
            {"id": "MEM-12", "utilization_pct": 20.0, "overdue_tasks": 0},
        ]
    }

    res = audit_executive_report_resource_workload(report_data)
    assert res["total_members"] == 3
    assert res["overallocated_member_ids"] == ["MEM-10", "MEM-11"]
    assert res["underutilized_member_ids"] == ["MEM-12"]
    assert res["bottleneck_member_ids"] == ["MEM-10"]
    assert res["average_utilization_pct"] == 85.0
    assert res["workload_posture"] == "CRITICAL_BOTTLENECK_OVERLOAD"
    assert any("MEM-10" in rec for rec in res["recommendations"])


def test_audit_executive_report_resource_workload_overallocation_risk():
    """Miembros con utilization_pct > 100.0 pero sin overdue_tasks -> 'RESOURCE_OVERALLOCATION_RISK'."""
    from backend.services.project_export_service import (
        audit_executive_report_resource_workload,
    )

    report_data = {
        "resource_allocations": [
            {
                "id": "MEM-20",
                "allocated_hours": 48.0,
                "capacity_hours": 40.0,
                "overdue_tasks": 0,
            },
            {"id": "MEM-21", "utilization_pct": 75.0, "overdue_tasks": 0},
        ]
    }

    res = audit_executive_report_resource_workload(report_data)
    assert res["total_members"] == 2
    assert res["overallocated_member_ids"] == ["MEM-20"]
    assert res["underutilized_member_ids"] == []
    assert res["bottleneck_member_ids"] == []
    assert res["average_utilization_pct"] == 97.5
    assert res["workload_posture"] == "RESOURCE_OVERALLOCATION_RISK"
    assert len(res["recommendations"]) >= 1


def test_audit_executive_report_resource_workload_no_data():
    """Sin miembros asignados o payload None/vacío -> 'NO_RESOURCE_WORKLOAD_DATA'."""
    from backend.services.project_export_service import (
        audit_executive_report_resource_workload,
    )

    for payload in (None, {}, {"resource_allocations": []}):
        res = audit_executive_report_resource_workload(payload)
        assert res["total_members"] == 0
        assert res["overallocated_member_ids"] == []
        assert res["underutilized_member_ids"] == []
        assert res["bottleneck_member_ids"] == []
        assert res["average_utilization_pct"] == 0.0
        assert res["workload_posture"] == "NO_RESOURCE_WORKLOAD_DATA"
        assert len(res["recommendations"]) == 1


# ── PMI PMBOK §12.3 & §10.2 Executive Report Procurement & Vendor SLA Auditor ─


def test_audit_executive_report_procurement_slas_governed_portfolio():
    """Contratos con SLA cumplido, topes respetados y TM acotado -> 'GOVERNED_PROCUREMENT_PORTFOLIO'."""
    import backend.services.project_export_service as export_module
    from backend.services.project_export_service import (
        ProjectExportService,
        audit_executive_report_procurement_slas,
    )

    report_data = {
        "vendor_contracts": [
            {
                "id": "CTR-101",
                "contract_type": "FFP",
                "sla_met_pct": 99.0,
                "sla_target_pct": 95.0,
                "budget_ceiling": 50000.0,
                "invoiced_amount": 42000.0,
            },
            {
                "contract_id": "CTR-102",
                "contract_type": "tm",
                "delivery_score_pct": 96.5,
                "sla_target_pct": 95.0,
                "not_to_exceed_limit": 25000.0,
                "invoiced_amount": 18000.0,
            },
        ]
    }

    res = ProjectExportService.audit_executive_report_procurement_slas(report_data)
    assert res["total_contracts"] == 2
    assert res["sla_breach_contract_ids"] == []
    assert res["ceiling_exceeded_contract_ids"] == []
    assert res["unbounded_tm_contract_ids"] == []
    assert res["average_sla_pct"] == 97.75
    assert res["procurement_posture"] == "GOVERNED_PROCUREMENT_PORTFOLIO"
    assert len(res["recommendations"]) == 1
    assert audit_executive_report_procurement_slas(report_data) == res
    assert "audit_executive_report_procurement_slas" in export_module.__all__


def test_audit_executive_report_procurement_slas_ceiling_overrun():
    """Contrato con invoiced_amount > budget_ceiling (>0) -> 'CONTRACT_CEILING_OVERRUN' (prioridad máxima)."""
    from backend.services.project_export_service import (
        audit_executive_report_procurement_slas,
    )

    report_data = {
        "procurement_kpis": [
            {
                "vendor": "CloudOps SAS",
                "contract_type": "CPFF",
                "sla_met_pct": 90.0,
                "sla_target_pct": 95.0,
                "budget_ceiling": 30000.0,
                "invoiced_amount": 34500.0,
            },
            {
                "id": "CTR-202",
                "contract_type": "TM",
                "sla_met_pct": 98.0,
                "budget_ceiling": 0.0,
                "invoiced_amount": 5000.0,
            },
        ]
    }

    res = audit_executive_report_procurement_slas(report_data)
    assert res["total_contracts"] == 2
    assert res["sla_breach_contract_ids"] == ["CloudOps SAS"]
    assert res["ceiling_exceeded_contract_ids"] == ["CloudOps SAS"]
    assert res["unbounded_tm_contract_ids"] == ["CTR-202"]
    assert res["average_sla_pct"] == 94.0
    assert res["procurement_posture"] == "CONTRACT_CEILING_OVERRUN"
    assert any("CloudOps SAS" in r for r in res["recommendations"])


def test_audit_executive_report_procurement_slas_unbounded_tm_and_sla_breach():
    """Contrato TM sin tope -> 'UNBOUNDED_TIME_AND_MATERIALS_RISK'; si solo hay SLA breach -> 'VENDOR_SLA_BREACH_DETECTED'."""
    from backend.services.project_export_service import (
        audit_executive_report_procurement_slas,
    )

    unbounded_payload = {
        "vendor_contracts": [
            {
                "id": "CTR-301",
                "contract_type": "TM",
                "sla_met_pct": 92.0,
                "sla_target_pct": 95.0,
                "budget_ceiling": 0.0,
                "invoiced_amount": 12000.0,
            }
        ]
    }
    res_tm = audit_executive_report_procurement_slas(unbounded_payload)
    assert res_tm["unbounded_tm_contract_ids"] == ["CTR-301"]
    assert res_tm["sla_breach_contract_ids"] == ["CTR-301"]
    assert res_tm["procurement_posture"] == "UNBOUNDED_TIME_AND_MATERIALS_RISK"

    sla_breach_payload = {
        "vendor_contracts": [
            {
                "id": "CTR-302",
                "contract_type": "FFP",
                "sla_met_pct": 88.5,
                "sla_target_pct": 95.0,
                "budget_ceiling": 40000.0,
                "invoiced_amount": 35000.0,
            },
            {
                "id": "CTR-303",
                "contract_type": "CPIF",
                "sla_met_pct": 97.5,
                "sla_target_pct": 95.0,
                "budget_ceiling": 20000.0,
                "invoiced_amount": 19000.0,
            },
        ]
    }
    res_sla = audit_executive_report_procurement_slas(sla_breach_payload)
    assert res_sla["total_contracts"] == 2
    assert res_sla["sla_breach_contract_ids"] == ["CTR-302"]
    assert res_sla["ceiling_exceeded_contract_ids"] == []
    assert res_sla["unbounded_tm_contract_ids"] == []
    assert res_sla["average_sla_pct"] == 93.0
    assert res_sla["procurement_posture"] == "VENDOR_SLA_BREACH_DETECTED"
    assert any("CTR-302" in r for r in res_sla["recommendations"])


def test_audit_executive_report_procurement_slas_no_contracts():
    """Sin contratos o payload None/vacío -> 'NO_PROCUREMENT_CONTRACTS'."""
    from backend.services.project_export_service import (
        audit_executive_report_procurement_slas,
    )

    for payload in (None, {}, {"vendor_contracts": []}, {"procurement_kpis": ["bad"]}):
        res = audit_executive_report_procurement_slas(payload)
        assert res["total_contracts"] == 0
        assert res["sla_breach_contract_ids"] == []
        assert res["ceiling_exceeded_contract_ids"] == []
        assert res["unbounded_tm_contract_ids"] == []
        assert res["average_sla_pct"] == 0.0
        assert res["procurement_posture"] == "NO_PROCUREMENT_CONTRACTS"
        assert len(res["recommendations"]) == 1


# ── PMI PMBOK §10.2 & §13.3 Executive Report Stakeholder Communications Auditor


def test_audit_executive_report_stakeholder_communications_transparent():
    """Interesados comprometidos o resistentes con action_plan y comunicaciones al día -> TRANSPARENT_STAKEHOLDER_ENGAGEMENT."""
    import backend.services.project_export_service as export_module
    from backend.services.project_export_service import (
        ProjectExportService,
        audit_executive_report_stakeholder_communications,
    )

    payload = {
        "stakeholders": [
            {"id": "STK-01", "engagement_level": "supportive"},
            {
                "stakeholder_id": "STK-02",
                "current_engagement": "resistant",
                "action_plan": "Sesión semanal de alineación ejecutiva",
            },
        ],
        "communications": [
            {"id": "COMM-01", "status": "sent"},
            {"comm_id": "COMM-02", "delivery_status": "scheduled"},
        ],
    }

    res = ProjectExportService.audit_executive_report_stakeholder_communications(
        payload
    )
    assert res == {
        "total_stakeholders": 2,
        "total_communications": 2,
        "unmitigated_resistant_stakeholder_ids": [],
        "overdue_communication_ids": [],
        "is_transparent": True,
        "communication_posture": "TRANSPARENT_STAKEHOLDER_ENGAGEMENT",
    }
    assert audit_executive_report_stakeholder_communications(payload) == res
    assert "audit_executive_report_stakeholder_communications" in export_module.__all__


def test_audit_executive_report_stakeholder_communications_unmitigated_resistance():
    """Interesados en resistant/unaware sin action_plan -> UNMITIGATED_STAKEHOLDER_RESISTANCE."""
    from backend.services.project_export_service import (
        audit_executive_report_stakeholder_communications,
    )

    payload = {
        "stakeholder_summary": [
            {"id": "STK-10", "engagement_level": "Resistente"},
            {"name": "STK-11", "current_engagement": "unaware", "action_plan": "   "},
            {
                "id": "STK-12",
                "engagement_level": "desconocedor",
                "engagement_strategy": "Taller de inducción",
            },
        ],
        "communication_log": [
            {"id": "COMM-10", "status": "overdue"},
        ],
    }

    res = audit_executive_report_stakeholder_communications(payload)
    assert res["total_stakeholders"] == 3
    assert res["total_communications"] == 1
    assert res["unmitigated_resistant_stakeholder_ids"] == ["STK-10", "STK-11"]
    assert res["overdue_communication_ids"] == ["COMM-10"]
    assert res["is_transparent"] is False
    assert res["communication_posture"] == "UNMITIGATED_STAKEHOLDER_RESISTANCE"


def test_audit_executive_report_stakeholder_communications_overdue_deliverables():
    """Sin resistencia desatendida pero con comunicaciones en overdue/missed -> OVERDUE_COMMUNICATION_DELIVERABLES."""
    from backend.services.project_export_service import (
        audit_executive_report_stakeholder_communications,
    )

    payload = {
        "interesados": [
            {"id": "STK-20", "engagement_level": "leading"},
        ],
        "comunicaciones": [
            {"id": "COMM-20", "status": "overdue"},
            {"channel": "Boletín Mensual", "delivery_status": "no_enviada"},
            {"id": "COMM-22", "status": "delivered"},
        ],
    }

    res = audit_executive_report_stakeholder_communications(payload)
    assert res["total_stakeholders"] == 1
    assert res["total_communications"] == 3
    assert res["unmitigated_resistant_stakeholder_ids"] == []
    assert res["overdue_communication_ids"] == ["COMM-20", "Boletín Mensual"]
    assert res["is_transparent"] is False
    assert res["communication_posture"] == "OVERDUE_COMMUNICATION_DELIVERABLES"


def test_audit_executive_report_stakeholder_communications_missing_data():
    """Payload vacío, None o sin listas de interesados/comunicaciones -> MISSING_STAKEHOLDER_COMMUNICATIONS_DATA."""
    from backend.services.project_export_service import (
        audit_executive_report_stakeholder_communications,
    )

    for payload in (
        None,
        {},
        {"stakeholders": [], "communications": []},
        {"stakeholders": ["invalid"]},
    ):
        res = audit_executive_report_stakeholder_communications(payload)
        assert res == {
            "total_stakeholders": 0,
            "total_communications": 0,
            "unmitigated_resistant_stakeholder_ids": [],
            "overdue_communication_ids": [],
            "is_transparent": False,
            "communication_posture": "MISSING_STAKEHOLDER_COMMUNICATIONS_DATA",
        }


def test_audit_executive_report_risk_burndown_effective():
    """Riesgos activos con dueño, reducción <= 60% y cerrados ignorados -> EFFECTIVE_RESIDUAL_RISK_BURNDOWN."""
    import backend.services.project_export_service as export_module
    from backend.services.project_export_service import (
        ProjectExportService,
        audit_executive_report_risk_burndown,
    )

    payload = {
        "risks": [
            {
                "id": "RSK-01",
                "status": "active",
                "owner": "Líder Infraestructura",
                "initial_score": 20.0,
                "residual_score": 8.0,
            },
            {
                "risk_id": "RSK-02",
                "status": "open",
                "risk_owner": "Arquitecto Seguridad",
                "inherent_score": 15.0,
                "residual_score": 6.0,
            },
            {
                "code": "RSK-03",
                "status": "closed",
                "owner": "",
                "initial_score": 25.0,
                "residual_score": None,
            },
        ]
    }
    res = ProjectExportService.audit_executive_report_risk_burndown(
        payload, max_residual_to_initial_ratio_pct=60.0
    )
    assert res == {
        "total_risks": 3,
        "active_risks_count": 2,
        "residual_ratio_pct": 40.0,
        "unowned_active_risk_ids": [],
        "unassessed_residual_risk_ids": [],
        "stagnant_mitigation_risk_ids": [],
        "is_effective": True,
        "risk_burndown_posture": "EFFECTIVE_RESIDUAL_RISK_BURNDOWN",
    }
    assert audit_executive_report_risk_burndown(payload) == res
    assert "audit_executive_report_risk_burndown" in export_module.__all__


def test_audit_executive_report_risk_burndown_unowned_or_unassessed():
    """Riesgos activos sin dueño o sin residual_score -> UNOWNED_OR_UNASSESSED_ACTIVE_RISKS."""
    from backend.services.project_export_service import (
        audit_executive_report_risk_burndown,
    )

    payload = {
        "risk_register": [
            {
                "id": "RSK-10",
                "status": "open",
                "owner": "   ",
                "initial_score": 16.0,
                "residual_score": 4.0,
            },
            {
                "id": "RSK-11",
                "status": "active",
                "owner": "PMO",
                "initial_score": 12.0,
                "residual_score": None,
            },
        ]
    }
    res = audit_executive_report_risk_burndown(payload)
    assert res["total_risks"] == 2
    assert res["active_risks_count"] == 2
    assert res["unowned_active_risk_ids"] == ["RSK-10"]
    assert res["unassessed_residual_risk_ids"] == ["RSK-11"]
    assert res["is_effective"] is False
    assert res["risk_burndown_posture"] == "UNOWNED_OR_UNASSESSED_ACTIVE_RISKS"


def test_audit_executive_report_risk_burndown_ineffective_mitigation():
    """Mitigación estancada (residual >= initial) o ratio > umbral -> INEFFECTIVE_RISK_MITIGATION_BURNDOWN."""
    from backend.services.project_export_service import (
        audit_executive_report_risk_burndown,
    )

    payload = {
        "raid_kpis": {
            "risks": [
                {
                    "id": "RSK-20",
                    "status": "open",
                    "owner": "Coordinador Técnico",
                    "initial_score": 15.0,
                    "residual_score": 15.0,
                },
                {
                    "id": "RSK-21",
                    "status": "active",
                    "owner": "Analista Financiero",
                    "initial_score": 10.0,
                    "residual_score": 5.0,
                },
            ]
        }
    }
    res = audit_executive_report_risk_burndown(
        payload, max_residual_to_initial_ratio_pct=60.0
    )
    assert res["total_risks"] == 2
    assert res["active_risks_count"] == 2
    assert res["residual_ratio_pct"] == 80.0
    assert res["stagnant_mitigation_risk_ids"] == ["RSK-20"]
    assert res["is_effective"] is False
    assert res["risk_burndown_posture"] == "INEFFECTIVE_RISK_MITIGATION_BURNDOWN"


def test_audit_executive_report_risk_burndown_no_risks_disclosed():
    """Payload vacío, None o sin riesgos -> NO_RISKS_DISCLOSED."""
    from backend.services.project_export_service import (
        audit_executive_report_risk_burndown,
    )

    for payload in (None, {}, {"risks": []}, {"raid_kpis": {"risks": ["invalid"]}}):
        res = audit_executive_report_risk_burndown(payload)
        assert res == {
            "total_risks": 0,
            "active_risks_count": 0,
            "residual_ratio_pct": 0.0,
            "unowned_active_risk_ids": [],
            "unassessed_residual_risk_ids": [],
            "stagnant_mitigation_risk_ids": [],
            "is_effective": False,
            "risk_burndown_posture": "NO_RISKS_DISCLOSED",
        }



def test_audit_executive_report_milestone_deliverables_verified_governance():
    """Hitos programados, completados con signoff y sin vencidos -> VERIFIED governance."""
    from backend.services.project_export_service import (
        audit_executive_report_milestone_deliverables as audit_fn,
    )

    res = audit_fn(
        {
            "milestones": [
                {
                    "id": "MS-1",
                    "due_date": "2026-09-30",
                    "status": "completed",
                    "accepted_by": "Directoría de Evangelismo",
                },
                {
                    "milestone_id": "MS-2",
                    "target_date": "2026-12-15",
                    "status": "in_progress",
                },
            ]
        }
    )
    assert res["is_traceable"] is True
    assert res["total_milestones"] == 2
    assert res["completed_milestones_count"] == 1
    assert res["unscheduled_milestone_ids"] == []
    assert res["unverified_completed_milestone_ids"] == []
    assert res["overdue_milestone_ids"] == []
    assert res["milestone_posture"] == "VERIFIED_MILESTONE_DELIVERY_GOVERNANCE"


def test_audit_executive_report_milestone_deliverables_unverified_completed():
    """Hito completado sin evidencia de signoff -> UNVERIFIED_COMPLETED_MILESTONES."""
    from backend.services.project_export_service import (
        audit_executive_report_milestone_deliverables as audit_fn,
    )

    res = audit_fn(
        {
            "milestone_summary": [
                {
                    "code": "MS-A",
                    "baseline_date": "2026-08-31",
                    "status": "completado",
                },
                {
                    "code": "MS-B",
                    "baseline_date": "2026-10-01",
                    "status": "achieved",
                    "signoff_ref": "ACTA-2026-77",
                },
            ]
        }
    )
    assert res["is_traceable"] is False
    assert res["total_milestones"] == 2
    assert res["completed_milestones_count"] == 2
    assert res["unscheduled_milestone_ids"] == []
    assert res["unverified_completed_milestone_ids"] == ["MS-A"]
    assert res["overdue_milestone_ids"] == []
    assert res["milestone_posture"] == "UNVERIFIED_COMPLETED_MILESTONES"


def test_audit_executive_report_milestone_deliverables_unscheduled_and_overdue():
    """Hito sin fecha (precedencia) y hito vencido identificados por pilar."""
    from backend.services.project_export_service import (
        audit_executive_report_milestone_deliverables as audit_fn,
    )

    res = audit_fn(
        {
            "cpm_schedule": {
                "milestones": [
                    {
                        "id": "MS-X",
                        "status": "in_progress",
                    },
                    {
                        "id": "MS-Y",
                        "due_date": "2026-07-01",
                        "is_overdue": True,
                    },
                    {
                        "id": "MS-Z",
                        "target_date": "2026-11-30",
                        "status": "retrasado",
                    },
                ]
            }
        }
    )
    assert res["is_traceable"] is False
    assert res["total_milestones"] == 3
    assert res["completed_milestones_count"] == 0
    assert res["unscheduled_milestone_ids"] == ["MS-X"]
    assert res["unverified_completed_milestone_ids"] == []
    assert res["overdue_milestone_ids"] == ["MS-Y", "MS-Z"]
    assert res["milestone_posture"] == "UNSCHEDULED_MILESTONE_BASELINES"


def test_audit_executive_report_milestone_deliverables_empty_or_none():
    """Payload no-dict, sin hitos o lista vacía -> NO_MILESTONES_DISCLOSED."""
    from backend.services.project_export_service import (
        audit_executive_report_milestone_deliverables as audit_fn,
    )

    for payload in (None, "not-a-dict", {}, {"milestones": []}, {"milestones": ["nope", 42]}):
        res = audit_fn(payload)  # type: ignore[arg-type]
        assert res == {
            "total_milestones": 0,
            "completed_milestones_count": 0,
            "unscheduled_milestone_ids": [],
            "unverified_completed_milestone_ids": [],
            "overdue_milestone_ids": [],
            "is_traceable": False,
            "milestone_posture": "NO_MILESTONES_DISCLOSED",
        }


def test_audit_executive_report_change_control_log_traceable():
    """Solicitudes CCB aprobadas cuantificadas, rechazadas justificadas y pendientes en SLA -> TRACEABLE_CCB_DECISION_LOG."""
    from backend.services.project_export_service import (
        ProjectExportService,
        audit_executive_report_change_control_log,
    )

    payload = {
        "change_requests": [
            {
                "id": "CR-101",
                "status": "approved",
                "cost_impact": 4500.0,
                "schedule_days_impact": 5,
                "approved_by": "CCB-Comite-Central",
            },
            {
                "cr_id": "CR-102",
                "decision": "rejected",
                "rationale": "Fuera del alcance autorizado en el Project Charter",
            },
            {
                "code": "CR-103",
                "state": "pending",
                "pending_days": 6,
            },
        ]
    }
    res = audit_executive_report_change_control_log(payload, max_pending_days=14)
    assert res == {
        "total_change_requests": 3,
        "approved_count": 1,
        "unquantified_approved_cr_ids": [],
        "overdue_pending_cr_ids": [],
        "undocumented_decision_cr_ids": [],
        "traceability_rate_pct": 100.0,
        "is_ccb_log_compliant": True,
        "ccb_log_posture": "TRACEABLE_CCB_DECISION_LOG",
    }
    assert (
        ProjectExportService.audit_executive_report_change_control_log(
            payload, max_pending_days=14
        )
        == res
    )


def test_audit_executive_report_change_control_log_unquantified_approved():
    """CR aprobada sin impacto cuantificado o sin aprobador CCB -> UNQUANTIFIED_APPROVED_BASELINE_CHANGE."""
    from backend.services.project_export_service import (
        audit_executive_report_change_control_log,
    )

    res = audit_executive_report_change_control_log(
        {
            "ccb_log": [
                {
                    "id": "CR-NO-IMPACT",
                    "status": "aprobado",
                    "approved_by": "Director PMO",
                },
                {
                    "id": "CR-NO-SIGN",
                    "status": "implemented",
                    "cost_impact": 1200.0,
                    "approved_by": "   ",
                },
            ]
        }
    )
    assert res["total_change_requests"] == 2
    assert res["approved_count"] == 2
    assert res["unquantified_approved_cr_ids"] == ["CR-NO-IMPACT", "CR-NO-SIGN"]
    assert res["traceability_rate_pct"] == 0.0
    assert res["is_ccb_log_compliant"] is False
    assert res["ccb_log_posture"] == "UNQUANTIFIED_APPROVED_BASELINE_CHANGE"


def test_audit_executive_report_change_control_log_overdue_and_undocumented():
    """CR pendiente > max_pending_days -> OVERDUE_CCB_PENDING_DECISIONS; rechazo sin justificación -> UNDOCUMENTED_CCB_REJECTION_RATIONALE."""
    from backend.services.project_export_service import (
        audit_executive_report_change_control_log,
    )

    overdue_res = audit_executive_report_change_control_log(
        {
            "changes": [
                {"id": "CR-STALE", "status": "under_review", "age_days": 21},
            ]
        },
        max_pending_days=14,
    )
    assert overdue_res["overdue_pending_cr_ids"] == ["CR-STALE"]
    assert overdue_res["is_ccb_log_compliant"] is False
    assert overdue_res["ccb_log_posture"] == "OVERDUE_CCB_PENDING_DECISIONS"

    undoc_res = audit_executive_report_change_control_log(
        {
            "change_requests": [
                {"id": "CR-REJ", "status": "deferred", "rejection_reason": "no"},
            ]
        }
    )
    assert undoc_res["undocumented_decision_cr_ids"] == ["CR-REJ"]
    assert undoc_res["is_ccb_log_compliant"] is False
    assert undoc_res["ccb_log_posture"] == "UNDOCUMENTED_CCB_REJECTION_RATIONALE"


def test_audit_executive_report_change_control_log_empty_or_none():
    """Payload vacío, None o sin solicitudes de cambio -> NO_CHANGE_REQUESTS_LOGGED."""
    from backend.services.project_export_service import (
        audit_executive_report_change_control_log,
    )

    for payload in (None, {}, {"change_requests": []}, {"ccb_log": ["invalid", 99]}):
        res = audit_executive_report_change_control_log(payload)  # type: ignore[arg-type]
        assert res == {
            "total_change_requests": 0,
            "approved_count": 0,
            "unquantified_approved_cr_ids": [],
            "overdue_pending_cr_ids": [],
            "undocumented_decision_cr_ids": [],
            "traceability_rate_pct": 100.0,
            "is_ccb_log_compliant": True,
            "ccb_log_posture": "NO_CHANGE_REQUESTS_LOGGED",
        }


def test_audit_executive_report_benefits_realization_on_track():
    """Beneficios con dueño, meta medible y realización >= 80% -> STRATEGIC on track."""
    from backend.services.project_export_service import (
        audit_executive_report_benefits_realization as audit_fn,
    )

    res = audit_fn(
        {
            "benefits": [
                {
                    "id": "BEN-1",
                    "benefit_owner": "Secretaría General",
                    "target_value": 1000.0,
                    "actual_value": 850.0,
                },
                {
                    "benefit_id": "BEN-2",
                    "owner": "Coordinación Discipulado",
                    "target": 500.0,
                    "realized_value": 600.0,
                },
            ]
        }
    )
    assert res["is_benefits_on_track"] is True
    assert res["total_benefits"] == 2
    assert res["average_realization_pct"] == 92.5
    assert res["unowned_benefit_ids"] == []
    assert res["unmeasurable_benefit_ids"] == []
    assert res["underperforming_benefit_ids"] == []
    assert res["benefits_posture"] == "STRATEGIC_BENEFITS_ON_TRACK"


def test_audit_executive_report_benefits_realization_unowned_or_unmeasurable():
    """Sin dueño o meta <= 0/None -> UNOWNED_OR_UNMEASURABLE (precedencia posture)."""
    from backend.services.project_export_service import (
        audit_executive_report_benefits_realization as audit_fn,
    )

    res = audit_fn(
        {
            "benefits_register": [
                {
                    "id": "BEN-NOOWNER",
                    "target_value": 100.0,
                    "actual_value": 95.0,
                },
                {
                    "id": "BEN-NOTARGET",
                    "benefit_owner": "Dirección",
                },
                {
                    "id": "BEN-ZERO",
                    "benefit_owner": "Dirección",
                    "target_value": 0.0,
                    "actual_value": 50.0,
                },
            ]
        }
    )
    assert res["is_benefits_on_track"] is False
    assert res["total_benefits"] == 3
    assert res["unowned_benefit_ids"] == ["BEN-NOOWNER"]
    assert res["unmeasurable_benefit_ids"] == ["BEN-NOTARGET", "BEN-ZERO"]
    assert res["underperforming_benefit_ids"] == []
    assert res["benefits_posture"] == "UNOWNED_OR_UNMEASURABLE_BENEFIT"


def test_audit_executive_report_benefits_realization_shortfall():
    """Medibles y con dueño pero bajo el umbral -> BENEFITS_REALIZATION_SHORTFALL."""
    from backend.services.project_export_service import (
        audit_executive_report_benefits_realization as audit_fn,
    )

    res = audit_fn(
        {
            "strategic_kpis": [
                {
                    "id": "BEN-LOW",
                    "benefit_owner": "Encargado de Proyectos",
                    "target_value": 1000.0,
                    "actual_value": 400.0,
                },
                {
                    "id": "BEN-OK",
                    "benefit_owner": "Encargado de Proyectos",
                    "target_value": 100.0,
                    "actual_value": 80.0,
                },
            ]
        }
    )
    assert res["is_benefits_on_track"] is False
    assert res["total_benefits"] == 2
    assert res["unowned_benefit_ids"] == []
    assert res["unmeasurable_benefit_ids"] == []
    assert res["underperforming_benefit_ids"] == ["BEN-LOW"]
    # BEN-LOW ratio 40.0; BEN-OK ratio 80.0 -> promedio 60.0.
    assert res["average_realization_pct"] == 60.0
    assert res["benefits_posture"] == "BENEFITS_REALIZATION_SHORTFALL"


def test_audit_executive_report_benefits_realization_empty_or_none():
    """Payload None, sin beneficios o lista vacía -> NO_BENEFITS_REPORTED."""
    from backend.services.project_export_service import (
        audit_executive_report_benefits_realization as audit_fn,
    )

    for payload in (None, {}, {"benefits": []}, {"benefits": ["nope", 42]}):
        res = audit_fn(payload)  # type: ignore[arg-type]
        assert res == {
            "total_benefits": 0,
            "average_realization_pct": 0.0,
            "unowned_benefit_ids": [],
            "unmeasurable_benefit_ids": [],
            "underperforming_benefit_ids": [],
            "is_benefits_on_track": True,
            "benefits_posture": "NO_BENEFITS_REPORTED",
        }


def test_audit_executive_report_resource_spof_and_utilization_balanced():
    """Recursos asignados, dentro de capacidad y roles críticos con respaldo -> BALANCED_RESILIENT_RESOURCE_PLAN."""
    from backend.services.project_export_service import (
        ProjectExportService,
        audit_executive_report_resource_spof_and_utilization,
    )

    payload = {
        "resource_allocations": [
            {
                "id": "RES-ARCH",
                "resource_name": "Carlos Méndez",
                "utilization_pct": 85.0,
                "is_critical_role": True,
                "backup_resource": "Elena Vargas",
            },
            {
                "resource_id": "RES-DEV",
                "assignee": "Elena Vargas",
                "allocation_pct": 75.0,
                "is_critical_role": False,
            },
        ]
    }
    res = audit_executive_report_resource_spof_and_utilization(payload, max_utilization_pct=100.0)
    assert res["total_allocations"] == 2
    assert res["average_utilization_pct"] == 80.0
    assert res["unassigned_role_ids"] == []
    assert res["overallocated_resource_ids"] == []
    assert res["unbacked_spof_resource_ids"] == []
    assert res["is_resource_plan_healthy"] is True
    assert res["resource_posture"] == "BALANCED_RESILIENT_RESOURCE_PLAN"
    assert (
        ProjectExportService.audit_executive_report_resource_spof_and_utilization(payload)[
            "resource_posture"
        ]
        == "BALANCED_RESILIENT_RESOURCE_PLAN"
    )


def test_audit_executive_report_resource_spof_and_utilization_unbacked_spof():
    """Rol crítico sin recurso de respaldo -> UNBACKED_KEY_PERSON_SPOF."""
    from backend.services.project_export_service import (
        audit_executive_report_resource_spof_and_utilization,
    )

    res = audit_executive_report_resource_spof_and_utilization(
        {
            "resources": [
                {
                    "id": "RES-DBA",
                    "resource_name": "Mateo Ruiz",
                    "utilization_pct": 90.0,
                    "critical_skill": True,
                    "backup_resource": "",
                },
                {
                    "id": "RES-QA",
                    "resource_name": "Sofía Castro",
                    "utilization_pct": 70.0,
                    "critical_skill": False,
                },
            ]
        }
    )
    assert res["total_allocations"] == 2
    assert res["average_utilization_pct"] == 80.0
    assert res["unassigned_role_ids"] == []
    assert res["overallocated_resource_ids"] == []
    assert res["unbacked_spof_resource_ids"] == ["RES-DBA"]
    assert res["is_resource_plan_healthy"] is False
    assert res["resource_posture"] == "UNBACKED_KEY_PERSON_SPOF"


def test_audit_executive_report_resource_spof_and_utilization_unassigned_and_overallocated():
    """Roles sin asignar y sobreasignación -> UNASSIGNED_CRITICAL_ROLE y RESOURCE_OVERALLOCATION_ALERT."""
    from backend.services.project_export_service import (
        audit_executive_report_resource_spof_and_utilization,
    )

    res_unassigned = audit_executive_report_resource_spof_and_utilization(
        {
            "team_allocations": [
                {
                    "role_id": "RES-SEC",
                    "resource_name": "",
                    "utilization_pct": 100.0,
                    "key_person": True,
                    "deputy": "Respaldo",
                },
                {
                    "role_id": "RES-OPS",
                    "member": "Luis Gómez",
                    "allocation_pct": 120.0,
                },
            ]
        },
        max_utilization_pct=100.0,
    )
    assert res_unassigned["unassigned_role_ids"] == ["RES-SEC"]
    assert res_unassigned["overallocated_resource_ids"] == ["RES-OPS"]
    assert res_unassigned["is_resource_plan_healthy"] is False
    assert res_unassigned["resource_posture"] == "UNASSIGNED_CRITICAL_ROLE"

    res_over = audit_executive_report_resource_spof_and_utilization(
        {
            "team_allocations": [
                {
                    "role_id": "RES-OPS",
                    "member": "Luis Gómez",
                    "allocation_pct": 115.0,
                }
            ]
        },
        max_utilization_pct=100.0,
    )
    assert res_over["unassigned_role_ids"] == []
    assert res_over["overallocated_resource_ids"] == ["RES-OPS"]
    assert res_over["is_resource_plan_healthy"] is False
    assert res_over["resource_posture"] == "RESOURCE_OVERALLOCATION_ALERT"


def test_audit_executive_report_resource_spof_and_utilization_empty_or_none():
    """Payload None o sin asignaciones -> NO_RESOURCES_REPORTED e is_resource_plan_healthy=True."""
    from backend.services.project_export_service import (
        audit_executive_report_resource_spof_and_utilization,
    )

    for payload in (None, {}, {"resources": []}, {"resource_allocations": ["invalid", 99]}):
        res = audit_executive_report_resource_spof_and_utilization(payload)  # type: ignore[arg-type]
        assert res == {
            "total_allocations": 0,
            "average_utilization_pct": 0.0,
            "unassigned_role_ids": [],
            "overallocated_resource_ids": [],
            "unbacked_spof_resource_ids": [],
            "is_resource_plan_healthy": True,
            "resource_posture": "NO_RESOURCES_REPORTED",
        }


def test_audit_executive_report_closure_readiness_ready():
    """Entregables aceptados, contratos liquidados y signoff administrativo completo -> READY_FOR_ADMINISTRATIVE_CLOSURE."""
    from backend.services.project_export_service import (
        ProjectExportService,
        audit_executive_report_closure_readiness,
    )

    payload = {
        "deliverables": [
            {"id": "DEL-1", "acceptance_status": "accepted"},
            {"deliverable_id": "DEL-2", "status": "signed_off"},
        ],
        "contracts": [
            {"id": "CNT-1", "status": "closed", "has_open_claims": False},
            {"contract_id": "CNT-2", "closeout_status": "settled"},
        ],
        "closure_summary": {
            "lessons_learned_archived": True,
            "sponsor_signoff": True,
        },
    }
    res = audit_executive_report_closure_readiness(payload)
    assert res == {
        "total_deliverables": 2,
        "total_contracts": 2,
        "unaccepted_deliverable_ids": [],
        "unsettled_contract_ids": [],
        "has_administrative_signoff": True,
        "is_ready_for_closure": True,
        "closure_posture": "READY_FOR_ADMINISTRATIVE_CLOSURE",
    }
    assert ProjectExportService.audit_executive_report_closure_readiness(payload) == res


def test_audit_executive_report_closure_readiness_unaccepted_deliverables():
    """Entregables pendientes de aceptación formal -> UNACCEPTED_FINAL_DELIVERABLES."""
    from backend.services.project_export_service import (
        audit_executive_report_closure_readiness,
    )

    res = audit_executive_report_closure_readiness(
        {
            "final_deliverables": [
                {"id": "DEL-OK", "acceptance_status": "accepted"},
                {"id": "DEL-PEND", "acceptance_status": "in_review"},
            ],
            "contracts": [{"id": "CNT-1", "status": "closed"}],
        }
    )
    assert res["total_deliverables"] == 2
    assert res["unaccepted_deliverable_ids"] == ["DEL-PEND"]
    assert res["unsettled_contract_ids"] == []
    assert res["is_ready_for_closure"] is False
    assert res["closure_posture"] == "UNACCEPTED_FINAL_DELIVERABLES"


def test_audit_executive_report_closure_readiness_open_contracts_and_pending_signoff():
    """Contratos con reclamos o sin liquidar -> OPEN_PROCUREMENT_CLAIMS_OR_CONTRACTS; falta de signoff -> PENDING_ADMINISTRATIVE_SIGNOFF."""
    from backend.services.project_export_service import (
        audit_executive_report_closure_readiness,
    )

    res_cnt = audit_executive_report_closure_readiness(
        {
            "deliverables": [{"id": "DEL-1", "status": "approved"}],
            "procurements": [
                {"id": "CNT-CLAIM", "status": "closed", "has_open_claims": True},
                {"id": "CNT-OPEN", "status": "active"},
            ],
        }
    )
    assert res_cnt["unaccepted_deliverable_ids"] == []
    assert res_cnt["unsettled_contract_ids"] == ["CNT-CLAIM", "CNT-OPEN"]
    assert res_cnt["is_ready_for_closure"] is False
    assert res_cnt["closure_posture"] == "OPEN_PROCUREMENT_CLAIMS_OR_CONTRACTS"

    res_signoff = audit_executive_report_closure_readiness(
        {
            "deliverables": [{"id": "DEL-1", "status": "accepted"}],
            "contracts": [{"id": "CNT-1", "status": "settled"}],
            "lessons_learned_archived": False,
            "sponsor_signoff": True,
        }
    )
    assert res_signoff["has_administrative_signoff"] is False
    assert res_signoff["is_ready_for_closure"] is False
    assert res_signoff["closure_posture"] == "PENDING_ADMINISTRATIVE_SIGNOFF"


def test_audit_executive_report_closure_readiness_empty_or_none():
    """Payload vacío o None -> NO_CLOSURE_DATA_REPORTED e is_ready_for_closure=True."""
    from backend.services.project_export_service import (
        audit_executive_report_closure_readiness,
    )

    for payload in (None, {}, {"deliverables": [], "contracts": []}):
        res = audit_executive_report_closure_readiness(payload)
        assert res == {
            "total_deliverables": 0,
            "total_contracts": 0,
            "unaccepted_deliverable_ids": [],
            "unsettled_contract_ids": [],
            "has_administrative_signoff": True,
            "is_ready_for_closure": True,
            "closure_posture": "NO_CLOSURE_DATA_REPORTED",
        }


def test_audit_executive_report_distribution_cadence_governed():
    """Todos los destinatarios obligatorios despachados en cadencia con acuse >= 80% -> GOVERNED_EXECUTIVE_DISTRIBUTION."""
    from backend.services.project_export_service import (
        ProjectExportService,
        audit_executive_report_distribution_cadence,
    )

    payload = {
        "distribution_governance": {
            "days_since_last_dispatch": 7,
            "recipients": [
                {"id": "STK-1", "mandatory": True, "dispatched": True, "acknowledged": True},
                {"id": "STK-2", "mandatory": True, "dispatched": True, "acknowledged": True},
                {"id": "STK-3", "mandatory": True, "dispatched": True, "acknowledged": True},
                {"id": "STK-4", "mandatory": True, "dispatched": True, "acknowledged": True},
                {"recipient_id": "STK-5", "mandatory": False, "dispatched": True, "acknowledged": False},
            ],
        }
    }
    res = audit_executive_report_distribution_cadence(payload, max_days_since_last_dispatch=14, min_ack_rate_pct=80.0)
    assert res == {
        "total_recipients": 5,
        "dispatched_count": 5,
        "acknowledged_count": 4,
        "ack_rate_pct": 80.0,
        "undispatched_mandatory_recipient_ids": [],
        "unacknowledged_recipient_ids": ["STK-5"],
        "is_cadence_overdue": False,
        "is_distribution_governed": True,
        "distribution_posture": "GOVERNED_EXECUTIVE_DISTRIBUTION",
    }
    assert ProjectExportService.audit_executive_report_distribution_cadence(payload) == res


def test_audit_executive_report_distribution_cadence_undispatched_mandatory():
    """Destinatario obligatorio sin envío -> UNDISPATCHED_MANDATORY_STAKEHOLDERS."""
    from backend.services.project_export_service import (
        audit_executive_report_distribution_cadence,
    )

    res = audit_executive_report_distribution_cadence(
        {
            "distribution_governance": {
                "days_since_last_dispatch": 5,
                "recipients": [
                    {"id": "STK-SPONSOR", "mandatory": True, "dispatched": False, "acknowledged": False},
                    {"id": "STK-PMO", "mandatory": True, "dispatched": True, "acknowledged": True},
                ],
            }
        }
    )
    assert res["total_recipients"] == 2
    assert res["dispatched_count"] == 1
    assert res["acknowledged_count"] == 1
    assert res["ack_rate_pct"] == 100.0
    assert res["undispatched_mandatory_recipient_ids"] == ["STK-SPONSOR"]
    assert res["is_cadence_overdue"] is False
    assert res["is_distribution_governed"] is False
    assert res["distribution_posture"] == "UNDISPATCHED_MANDATORY_STAKEHOLDERS"


def test_audit_executive_report_distribution_cadence_overdue_and_low_ack():
    """Cadencia vencida -> REPORT_DISPATCH_CADENCE_OVERDUE; baja tasa de acuse -> LOW_STAKEHOLDER_ACKNOWLEDGMENT_RATE."""
    from backend.services.project_export_service import (
        audit_executive_report_distribution_cadence,
    )

    res_overdue = audit_executive_report_distribution_cadence(
        {
            "distribution_governance": {
                "days_since_last_dispatch": 21,
                "recipients": [
                    {"id": "STK-1", "mandatory": True, "dispatched": True, "acknowledged": True},
                ],
            }
        },
        max_days_since_last_dispatch=14,
    )
    assert res_overdue["is_cadence_overdue"] is True
    assert res_overdue["is_distribution_governed"] is False
    assert res_overdue["distribution_posture"] == "REPORT_DISPATCH_CADENCE_OVERDUE"

    res_low_ack = audit_executive_report_distribution_cadence(
        {
            "distribution_governance": {
                "days_since_last_dispatch": 4,
                "recipients": [
                    {"id": "STK-1", "mandatory": True, "dispatched": True, "acknowledged": True},
                    {"id": "STK-2", "mandatory": True, "dispatched": True, "acknowledged": False},
                ],
            }
        },
        min_ack_rate_pct=80.0,
    )
    assert res_low_ack["ack_rate_pct"] == 50.0
    assert res_low_ack["unacknowledged_recipient_ids"] == ["STK-2"]
    assert res_low_ack["is_cadence_overdue"] is False
    assert res_low_ack["is_distribution_governed"] is False
    assert res_low_ack["distribution_posture"] == "LOW_STAKEHOLDER_ACKNOWLEDGMENT_RATE"


def test_audit_executive_report_distribution_cadence_empty_or_none():
    """Sin destinatarios o payload vacío/None -> NO_DISTRIBUTION_RECIPIENTS."""
    from backend.services.project_export_service import (
        audit_executive_report_distribution_cadence,
    )

    for payload in (None, {}, {"distribution_governance": {"recipients": []}}):
        res = audit_executive_report_distribution_cadence(payload)
        assert res == {
            "total_recipients": 0,
            "dispatched_count": 0,
            "acknowledged_count": 0,
            "ack_rate_pct": 0.0,
            "undispatched_mandatory_recipient_ids": [],
            "unacknowledged_recipient_ids": [],
            "is_cadence_overdue": True,
            "is_distribution_governed": False,
            "distribution_posture": "NO_DISTRIBUTION_RECIPIENTS",
        }


def test_audit_executive_report_procurement_sla_and_holdbacks_governed():
    """SLA cumplido, penalizaciones coherentes y retenciones suficientes -> GOVERNED."""
    from backend.services.project_export_service import (
        audit_executive_report_procurement_sla_and_holdbacks as audit_fn,
    )

    res = audit_fn(
        {
            "procurement_governance": {
                "contracts": [
                    {
                        "id": "CTR-1",
                        "contract_value": 100000.0,
                        "holdback_retained": 8000.0,
                        "sla_met": True,
                    },
                    {
                        "contract_id": "CTR-2",
                        "contract_value": 50000.0,
                        "holdback_retained": 4000.0,
                        "sla_met": False,
                        "penalty_applied": True,
                    },
                ]
            }
        }
    )
    assert res["total_contracts"] == 2
    assert res["total_contract_value"] == 150000.0
    assert res["total_holdback_retained"] == 12000.0
    assert res["premature_holdback_release_ids"] == []
    assert res["unpenalized_sla_breach_ids"] == []
    assert res["insufficient_holdback_ids"] == []
    assert res["is_procurement_sla_governed"] is True
    assert res["procurement_sla_posture"] == "GOVERNED_PROCUREMENT_SLA_AND_HOLDBACKS"


def test_audit_executive_report_procurement_sla_and_holdbacks_premature_release():
    """Retención liberada sin entregables verificados -> PREMATURE release (precedencia)."""
    from backend.services.project_export_service import (
        audit_executive_report_procurement_sla_and_holdbacks as audit_fn,
    )

    res = audit_fn(
        {
            "procurement_governance": {
                "contracts": [
                    {
                        "id": "CTR-PREM",
                        "contract_value": 20000.0,
                        "holdback_retained": 2000.0,
                        "holdback_released": True,
                        "deliverables_verified": False,
                        "sla_met": True,
                    }
                ]
            }
        }
    )
    assert res["total_contracts"] == 1
    assert res["total_contract_value"] == 20000.0
    assert res["total_holdback_retained"] == 2000.0
    assert res["premature_holdback_release_ids"] == ["CTR-PREM"]
    assert res["unpenalized_sla_breach_ids"] == []
    assert res["insufficient_holdback_ids"] == []
    assert res["is_procurement_sla_governed"] is False
    assert res["procurement_sla_posture"] == "PREMATURE_WARRANTY_HOLDBACK_RELEASE"


def test_audit_executive_report_procurement_sla_and_holdbacks_breach_and_insufficient():
    """SLA incumplido sin penalización y retención insuficiente identificados por pilar."""
    from backend.services.project_export_service import (
        audit_executive_report_procurement_sla_and_holdbacks as audit_fn,
    )

    res = audit_fn(
        {
            "procurement_governance": {
                "contracts": [
                    {
                        "contract_id": "CTR-BREACH",
                        "contract_value": 30000.0,
                        "holdback_retained": 2000.0,
                        "sla_met": False,
                    },
                    {
                        "id": "CTR-THIN",
                        "contract_value": 60000.0,
                        "holdback_retained": 1500.0,
                        "sla_met": True,
                    },
                ]
            }
        }
    )
    assert res["total_contracts"] == 2
    assert res["unpenalized_sla_breach_ids"] == ["CTR-BREACH"]
    assert res["insufficient_holdback_ids"] == ["CTR-THIN"]
    assert res["premature_holdback_release_ids"] == []
    assert res["is_procurement_sla_governed"] is False
    assert res["procurement_sla_posture"] == "UNPENALIZED_VENDOR_SLA_BREACH"


def test_audit_executive_report_procurement_sla_and_holdbacks_empty_or_none():
    """Payload None/sin contratos/entradas no dict o sin id -> NO_PROCUREMENT_CONTRACTS."""
    from backend.services.project_export_service import (
        audit_executive_report_procurement_sla_and_holdbacks as audit_fn,
    )

    for payload in (
        None,
        {},
        {"procurement_governance": {}},
        {"procurement_governance": {"contracts": "not-a-list"}},
        {"procurement_governance": {"contracts": [{"contract_value": 100.0}, "nope", 42]}},
    ):
        res = audit_fn(payload)  # type: ignore[arg-type]
        assert res == {
            "total_contracts": 0,
            "total_contract_value": 0.0,
            "total_holdback_retained": 0.0,
            "premature_holdback_release_ids": [],
            "unpenalized_sla_breach_ids": [],
            "insufficient_holdback_ids": [],
            "is_procurement_sla_governed": False,
            "procurement_sla_posture": "NO_PROCUREMENT_CONTRACTS",
        }


def test_audit_executive_report_risk_contingency_coverage_adequate():
    """Reserva de contingencia >= EMV activo y amenazas críticas con plan de respuesta -> ADEQUATE_RISK_CONTINGENCY_COVERAGE."""
    from backend.services.project_export_service import (
        ProjectExportService,
        audit_executive_report_risk_contingency_coverage,
    )

    payload = {
        "raid_kpis": {
            "remaining_contingency_reserve": 30000.0,
            "risks": [
                {
                    "id": "RSK-01",
                    "status": "OPEN",
                    "probability": 0.5,
                    "monetary_impact": 30000.0,
                    "severity": "CRITICAL",
                    "response_plan": "Contratar proveedor de respaldo precalificado",
                },
                {
                    "risk_id": "RSK-02",
                    "status": "MITIGATING",
                    "probability": 0.25,
                    "monetary_impact": 20000.0,
                    "severity": "MEDIUM",
                    "response_plan": "",
                },
                {
                    "id": "RSK-CLOSED",
                    "status": "CLOSED",
                    "probability": 0.9,
                    "monetary_impact": 90000.0,
                    "severity": "CRITICAL",
                    "response_plan": "",
                },
            ],
        }
    }
    res = audit_executive_report_risk_contingency_coverage(payload, min_coverage_ratio=1.0)
    assert res == {
        "active_threats_count": 2,
        "total_active_emv": 20000.0,
        "remaining_contingency_reserve": 30000.0,
        "reserve_shortfall": 0.0,
        "coverage_ratio": 1.5,
        "unplanned_critical_threat_ids": [],
        "is_contingency_adequate": True,
        "contingency_posture": "ADEQUATE_RISK_CONTINGENCY_COVERAGE",
    }
    assert (
        ProjectExportService.audit_executive_report_risk_contingency_coverage(payload)
        == res
    )


def test_audit_executive_report_risk_contingency_coverage_unplanned_critical_threat():
    """Amenaza activa con EMV >= 10000 o severity == CRITICAL sin response_plan -> UNPLANNED_CRITICAL_THREAT_EXPOSURE."""
    from backend.services.project_export_service import (
        audit_executive_report_risk_contingency_coverage,
    )

    res = audit_executive_report_risk_contingency_coverage(
        {
            "raid_kpis": {
                "remaining_contingency_reserve": 50000.0,
                "risks": [
                    {
                        "id": "RSK-EMV-HIGH",
                        "status": "ACTIVE",
                        "probability": 0.5,
                        "monetary_impact": 25000.0,
                        "severity": "HIGH",
                        "response_plan": "   ",
                    },
                    {
                        "id": "RSK-CRIT-SEV",
                        "status": "OPEN",
                        "probability": 0.1,
                        "monetary_impact": 20000.0,
                        "severity": "CRITICAL",
                        "response_plan": "",
                    },
                ],
            }
        }
    )
    assert res["active_threats_count"] == 2
    assert res["total_active_emv"] == 14500.0
    assert res["unplanned_critical_threat_ids"] == ["RSK-EMV-HIGH", "RSK-CRIT-SEV"]
    assert res["is_contingency_adequate"] is False
    assert res["contingency_posture"] == "UNPLANNED_CRITICAL_THREAT_EXPOSURE"


def test_audit_executive_report_risk_contingency_coverage_underfunded():
    """Planes de respuesta completos pero reserva < EMV total -> CONTINGENCY_RESERVE_UNDERFUNDED."""
    from backend.services.project_export_service import (
        audit_executive_report_risk_contingency_coverage,
    )

    res = audit_executive_report_risk_contingency_coverage(
        {
            "raid_kpis": {
                "remaining_contingency_reserve": 8000.0,
                "risks": [
                    {
                        "id": "RSK-10",
                        "status": "OPEN",
                        "probability": 0.4,
                        "monetary_impact": 30000.0,
                        "severity": "CRITICAL",
                        "response_plan": "Activar póliza y cuadrilla alterna",
                    }
                ],
            }
        },
        min_coverage_ratio=1.0,
    )
    assert res == {
        "active_threats_count": 1,
        "total_active_emv": 12000.0,
        "remaining_contingency_reserve": 8000.0,
        "reserve_shortfall": 4000.0,
        "coverage_ratio": 0.6667,
        "unplanned_critical_threat_ids": [],
        "is_contingency_adequate": False,
        "contingency_posture": "CONTINGENCY_RESERVE_UNDERFUNDED",
    }


def test_audit_executive_report_risk_contingency_coverage_no_active_threats():
    """Sin riesgos activos o payload vacío -> NO_ACTIVE_THREATS_REPORTED."""
    from backend.services.project_export_service import (
        audit_executive_report_risk_contingency_coverage,
    )

    for payload in (
        None,
        {},
        {"raid_kpis": {"remaining_contingency_reserve": 5000.0, "risks": []}},
        {
            "raid_kpis": {
                "remaining_contingency_reserve": 5000.0,
                "risks": [{"id": "RSK-C", "status": "CLOSED", "probability": 0.5, "monetary_impact": 10000.0}],
            }
        },
    ):
        res = audit_executive_report_risk_contingency_coverage(payload)
        assert res["active_threats_count"] == 0
        assert res["total_active_emv"] == 0.0
        assert res["reserve_shortfall"] == 0.0
        assert res["coverage_ratio"] == 1.0
        assert res["unplanned_critical_threat_ids"] == []
        assert res["is_contingency_adequate"] is False
        assert res["contingency_posture"] == "NO_ACTIVE_THREATS_REPORTED"


def test_audit_executive_report_scope_creep_governance_protected_baseline():
    """Paquetes de trabajo dentro de línea base o con CR aprobada y sin gold plating -> PROTECTED_SCOPE_BASELINE."""
    from backend.services.project_export_service import (
        ProjectExportService,
        audit_executive_report_scope_creep_governance,
    )

    payload = {
        "scope_governance": {
            "work_packages": [
                {"id": "WP-1", "effort_hours": 120.0, "added_post_baseline": False},
                {
                    "wp_id": "WP-2",
                    "effort_hours": 80.0,
                    "added_post_baseline": True,
                    "approved_cr_id": "CR-2026-04",
                    "is_gold_plating": False,
                },
            ]
        }
    }
    res = audit_executive_report_scope_creep_governance(
        payload, max_unbaselined_scope_pct=5.0
    )
    assert res == {
        "total_work_packages": 2,
        "total_effort_hours": 200.0,
        "unapproved_effort_hours": 0.0,
        "scope_creep_effort_pct": 0.0,
        "unapproved_scope_creep_ids": [],
        "gold_plating_package_ids": [],
        "is_scope_baseline_protected": True,
        "scope_creep_posture": "PROTECTED_SCOPE_BASELINE",
    }
    assert (
        ProjectExportService.audit_executive_report_scope_creep_governance(payload)
        == res
    )


def test_audit_executive_report_scope_creep_governance_unapproved_scope_creep():
    """Paquete añadido post-baseline sin approved_cr_id -> UNAPPROVED_SCOPE_CREEP_DETECTED."""
    from backend.services.project_export_service import (
        audit_executive_report_scope_creep_governance,
    )

    res = audit_executive_report_scope_creep_governance(
        {
            "scope_governance": {
                "work_packages": [
                    {"id": "WP-BASE", "effort_hours": 80.0, "added_post_baseline": False},
                    {
                        "id": "WP-CREEP",
                        "effort_hours": 20.0,
                        "added_post_baseline": True,
                        "approved_cr_id": "   ",
                    },
                ]
            }
        }
    )
    assert res == {
        "total_work_packages": 2,
        "total_effort_hours": 100.0,
        "unapproved_effort_hours": 20.0,
        "scope_creep_effort_pct": 20.0,
        "unapproved_scope_creep_ids": ["WP-CREEP"],
        "gold_plating_package_ids": [],
        "is_scope_baseline_protected": False,
        "scope_creep_posture": "UNAPPROVED_SCOPE_CREEP_DETECTED",
    }


def test_audit_executive_report_scope_creep_governance_gold_plating():
    """Paquete con is_gold_plating=True -> UNAUTHORIZED_GOLD_PLATING_DETECTED."""
    from backend.services.project_export_service import (
        audit_executive_report_scope_creep_governance,
    )

    res = audit_executive_report_scope_creep_governance(
        {
            "scope_governance": {
                "work_packages": [
                    {
                        "id": "WP-GOLD",
                        "effort_hours": 50.0,
                        "added_post_baseline": False,
                        "is_gold_plating": True,
                    }
                ]
            }
        }
    )
    assert res["gold_plating_package_ids"] == ["WP-GOLD"]
    assert res["is_scope_baseline_protected"] is False
    assert res["scope_creep_posture"] == "UNAUTHORIZED_GOLD_PLATING_DETECTED"


def test_audit_executive_report_scope_creep_governance_no_packages():
    """Payload vacío o sin paquetes -> NO_SCOPE_PACKAGES_REPORTED."""
    from backend.services.project_export_service import (
        audit_executive_report_scope_creep_governance,
    )

    for payload in (None, {}, {"scope_governance": {"work_packages": []}}):
        res = audit_executive_report_scope_creep_governance(payload)
        assert res == {
            "total_work_packages": 0,
            "total_effort_hours": 0.0,
            "unapproved_effort_hours": 0.0,
            "scope_creep_effort_pct": 0.0,
            "unapproved_scope_creep_ids": [],
            "gold_plating_package_ids": [],
            "is_scope_baseline_protected": False,
            "scope_creep_posture": "NO_SCOPE_PACKAGES_REPORTED",
        }


def test_audit_executive_report_stakeholder_engagement_drift_healthy_and_mitigated():
    """Interesados de alta influencia con brecha mitigada (action_plan_defined=True) y sin resistentes críticos -> is_engagement_healthy True."""
    from backend.services.project_export_service import (
        ProjectExportService,
        audit_executive_report_stakeholder_engagement_drift,
    )

    assessments = [
        {
            "stakeholder_id": "STK-1",
            "influence_level": "critical",
            "previous_engagement": "neutral",
            "current_engagement": "supportive",
            "desired_engagement": "leading",
            "action_plan_defined": True,
        },
        {
            "stakeholder_id": "STK-2",
            "influence_level": "medium",
            "previous_engagement": "unaware",
            "current_engagement": "supportive",
            "desired_engagement": "supportive",
            "action_plan_defined": False,
        },
    ]
    res = audit_executive_report_stakeholder_engagement_drift(assessments)
    assert res == {
        "evaluated_stakeholder_count": 2,
        "engagement_gap_ids": ["STK-1"],
        "regressing_stakeholder_ids": [],
        "high_influence_resistant_ids": [],
        "unmitigated_high_influence_gap_ids": [],
        "invalid_assessment_ids": [],
        "is_engagement_healthy": True,
    }
    assert (
        ProjectExportService.audit_executive_report_stakeholder_engagement_drift(
            assessments
        )
        == res
    )


def test_audit_executive_report_stakeholder_engagement_drift_regression_and_unmitigated_gap():
    """Regresión de nivel y brecha de alta influencia sin plan de acción -> regressing_stakeholder_ids, unmitigated_high_influence_gap_ids, is_engagement_healthy False."""
    from backend.services.project_export_service import (
        audit_executive_report_stakeholder_engagement_drift,
    )

    res = audit_executive_report_stakeholder_engagement_drift(
        [
            {
                "stakeholder_id": "STK-REG",
                "influence_level": "high",
                "previous_engagement": "supportive",
                "current_engagement": "neutral",
                "desired_engagement": "supportive",
                "action_plan_defined": False,
            },
            {
                "stakeholder_id": "STK-RES",
                "influence_level": "critical",
                "previous_engagement": "neutral",
                "current_engagement": "resistant",
                "desired_engagement": "supportive",
                "action_plan_defined": True,
            },
        ]
    )
    assert res == {
        "evaluated_stakeholder_count": 2,
        "engagement_gap_ids": ["STK-REG", "STK-RES"],
        "regressing_stakeholder_ids": ["STK-REG", "STK-RES"],
        "high_influence_resistant_ids": ["STK-RES"],
        "unmitigated_high_influence_gap_ids": ["STK-REG"],
        "invalid_assessment_ids": [],
        "is_engagement_healthy": False,
    }


def test_audit_executive_report_stakeholder_engagement_drift_invalid_levels():
    """Niveles de involucramiento desconocidos -> invalid_assessment_ids poblado, is_engagement_healthy False."""
    from backend.services.project_export_service import (
        audit_executive_report_stakeholder_engagement_drift,
    )

    res = audit_executive_report_stakeholder_engagement_drift(
        [
            {
                "stakeholder_id": "STK-BAD-CUR",
                "influence_level": "low",
                "current_engagement": "hostile",
                "desired_engagement": "supportive",
            },
            {
                "stakeholder_id": "STK-BAD-PREV",
                "influence_level": "low",
                "previous_engagement": "unknown_state",
                "current_engagement": "supportive",
                "desired_engagement": "supportive",
            },
        ]
    )
    assert res["evaluated_stakeholder_count"] == 2
    assert res["invalid_assessment_ids"] == ["STK-BAD-CUR", "STK-BAD-PREV"]
    assert res["is_engagement_healthy"] is False


def test_audit_executive_report_stakeholder_engagement_drift_empty_or_none():
    """Lista vacía, None o entradas sin stakeholder_id -> evaluated_stakeholder_count 0, is_engagement_healthy False."""
    from backend.services.project_export_service import (
        audit_executive_report_stakeholder_engagement_drift,
    )

    for payload in (None, [], [{"stakeholder_id": "   "}], ["invalid"]):
        res = audit_executive_report_stakeholder_engagement_drift(payload)  # type: ignore[arg-type]
        assert res == {
            "evaluated_stakeholder_count": 0,
            "engagement_gap_ids": [],
            "regressing_stakeholder_ids": [],
            "high_influence_resistant_ids": [],
            "unmitigated_high_influence_gap_ids": [],
            "invalid_assessment_ids": [],
            "is_engagement_healthy": False,
        }


def test_audit_executive_report_contract_type_risk_allocation_aligned():
    """Contratos FFP con alcance bien definido, T&M con techo y cláusula de auditoría, todos con SOW -> is_risk_aligned True."""
    from backend.services.project_export_service import (
        ProjectExportService,
        audit_executive_report_contract_type_risk_allocation,
    )

    contracts = [
        {
            "contract_id": "CTR-FFP-1",
            "contract_type": "FFP",
            "scope_definition_maturity": "well_defined",
            "has_statement_of_work": True,
        },
        {
            "contract_id": "CTR-TM-2",
            "contract_type": "tm",
            "scope_definition_maturity": "evolving",
            "has_ceiling_price": True,
            "has_statement_of_work": True,
            "buyer_audit_rights_clause": True,
        },
    ]
    res = audit_executive_report_contract_type_risk_allocation(contracts)
    assert res == {
        "evaluated_contract_count": 2,
        "missing_sow_contract_ids": [],
        "mismatched_fixed_price_uncertainty_ids": [],
        "uncapped_time_and_materials_ids": [],
        "missing_buyer_audit_clause_ids": [],
        "invalid_contract_ids": [],
        "is_risk_aligned": True,
    }
    assert (
        ProjectExportService.audit_executive_report_contract_type_risk_allocation(
            contracts
        )
        == res
    )


def test_audit_executive_report_contract_type_risk_allocation_mismatched_and_uncapped():
    """FFP con alcance incierto, T&M sin techo ni cláusula de auditoría, CPFF sin SOW -> violaciones detectadas."""
    from backend.services.project_export_service import (
        audit_executive_report_contract_type_risk_allocation,
    )

    res = audit_executive_report_contract_type_risk_allocation(
        [
            {
                "contract_id": "CTR-FFP-UNC",
                "contract_type": "ffp",
                "scope_definition_maturity": "uncertain",
                "has_statement_of_work": True,
            },
            {
                "contract_id": "CTR-TM-OPEN",
                "contract_type": "tm",
                "scope_definition_maturity": "evolving",
                "has_ceiling_price": False,
                "has_statement_of_work": True,
                "buyer_audit_rights_clause": False,
            },
            {
                "contract_id": "CTR-CPFF-NOSOW",
                "contract_type": "cpff",
                "scope_definition_maturity": "uncertain",
                "has_statement_of_work": False,
                "buyer_audit_rights_clause": True,
            },
        ]
    )
    assert res == {
        "evaluated_contract_count": 3,
        "missing_sow_contract_ids": ["CTR-CPFF-NOSOW"],
        "mismatched_fixed_price_uncertainty_ids": ["CTR-FFP-UNC"],
        "uncapped_time_and_materials_ids": ["CTR-TM-OPEN"],
        "missing_buyer_audit_clause_ids": ["CTR-TM-OPEN"],
        "invalid_contract_ids": [],
        "is_risk_aligned": False,
    }


def test_audit_executive_report_contract_type_risk_allocation_invalid_contract():
    """Tipo de contrato o madurez de alcance desconocido -> invalid_contract_ids poblado."""
    from backend.services.project_export_service import (
        audit_executive_report_contract_type_risk_allocation,
    )

    res = audit_executive_report_contract_type_risk_allocation(
        [
            {
                "contract_id": "CTR-BAD-TYPE",
                "contract_type": "cost_plus_percentage",
                "scope_definition_maturity": "well_defined",
                "has_statement_of_work": True,
            },
            {
                "contract_id": "CTR-BAD-MAT",
                "contract_type": "ffp",
                "scope_definition_maturity": "unknown_maturity",
                "has_statement_of_work": True,
            },
        ]
    )
    assert res["evaluated_contract_count"] == 2
    assert res["invalid_contract_ids"] == ["CTR-BAD-TYPE", "CTR-BAD-MAT"]
    assert res["is_risk_aligned"] is False


def test_audit_executive_report_contract_type_risk_allocation_empty_or_none():
    """Lista vacía, None o entradas sin contract_id -> evaluated_contract_count 0, is_risk_aligned False."""
    from backend.services.project_export_service import (
        audit_executive_report_contract_type_risk_allocation,
    )

    for payload in (None, [], [{"contract_id": "  "}], ["invalid"]):
        res = audit_executive_report_contract_type_risk_allocation(payload)  # type: ignore[arg-type]
        assert res == {
            "evaluated_contract_count": 0,
            "missing_sow_contract_ids": [],
            "mismatched_fixed_price_uncertainty_ids": [],
            "uncapped_time_and_materials_ids": [],
            "missing_buyer_audit_clause_ids": [],
            "invalid_contract_ids": [],
            "is_risk_aligned": False,
        }


def test_audit_executive_report_lessons_learned_institutionalization_ready():
    """Lecciones completas (causa raíz + acción + ref OPA) -> is_opa_ready 100%."""
    from backend.services.project_export_service import (
        audit_executive_report_lessons_learned_institutionalization,
        ProjectExportService,
    )

    res = audit_executive_report_lessons_learned_institutionalization(
        {
            "lessons_learned": [
                {
                    "lesson_id": "LL-1",
                    "root_cause_documented": True,
                    "preventive_action": "Checklist de despliegue obligatorio",
                    "opa_repository_ref": "OPA/LL/2026/001",
                },
                {
                    "lesson_id": "LL-2",
                    "root_cause_documented": True,
                    "preventive_action": "Doble aprobación de scope",
                    "opa_repository_ref": "OPA/LL/2026/002",
                },
            ]
        }
    )
    assert res["total_lessons"] == 2
    assert res["missing_root_cause_lesson_ids"] == []
    assert res["missing_action_plan_lesson_ids"] == []
    assert res["unlinked_opa_lesson_ids"] == []
    assert res["institutionalization_rate_pct"] == 100.0
    assert res["is_opa_ready"] is True

    static_res = ProjectExportService.audit_executive_report_lessons_learned_institutionalization(
        {
            "lessons_learned": [
                {
                    "lesson_id": "LL-1",
                    "root_cause_documented": True,
                    "preventive_action": "Checklist",
                    "opa_repository_ref": "OPA/LL/1",
                },
            ]
        }
    )
    assert static_res["is_opa_ready"] is True


def test_audit_executive_report_lessons_learned_institutionalization_root_cause_and_action_gaps():
    """Faltan causa raíz y/o acción preventiva -> listas de brechas + tasa parcial."""
    from backend.services.project_export_service import (
        audit_executive_report_lessons_learned_institutionalization,
    )

    res = audit_executive_report_lessons_learned_institutionalization(
        {
            "lessons_learned": [
                {
                    "lesson_id": "LL-NO-RC",
                    "preventive_action": "acción ok",
                    "opa_repository_ref": "OPA/LL/1",
                },
                {
                    "lesson_id": "LL-NO-ACTION",
                    "root_cause_documented": True,
                    "preventive_action": "   ",
                    "opa_repository_ref": "OPA/LL/2",
                },
                {
                    "lesson_id": "LL-OK",
                    "root_cause_documented": True,
                    "preventive_action": "acción",
                    "opa_repository_ref": "OPA/LL/3",
                },
            ]
        }
    )
    assert res["total_lessons"] == 3
    assert res["missing_root_cause_lesson_ids"] == ["LL-NO-RC"]
    assert res["missing_action_plan_lesson_ids"] == ["LL-NO-ACTION"]
    assert res["unlinked_opa_lesson_ids"] == []
    assert res["institutionalization_rate_pct"] == 33.33
    assert res["is_opa_ready"] is False


def test_audit_executive_report_lessons_learned_institutionalization_unlinked_opa_and_governance_fallback():
    """Cerradas/institucionalizadas sin ref OPA -> unlinked; secuencia anidada en governance."""
    from backend.services.project_export_service import (
        audit_executive_report_lessons_learned_institutionalization,
    )

    res_nested = audit_executive_report_lessons_learned_institutionalization(
        {
            "governance": {
                "lessons_learned": [
                    {
                        "lesson_id": "LL-CLOSED",
                        "root_cause_documented": True,
                        "preventive_action": "acción",
                        "status": "CLOSED",
                    },
                    {
                        "lesson_id": "LL-INST",
                        "root_cause_documented": True,
                        "preventive_action": "acción",
                        "status": "archived_to_opa",
                        "opa_repository_ref": "OPA/LL/9",
                    },
                ]
            }
        }
    )
    assert res_nested["total_lessons"] == 2
    assert res_nested["unlinked_opa_lesson_ids"] == ["LL-CLOSED"]
    assert res_nested["is_opa_ready"] is False

    # Root-level con secuencia válida: prioridad sobre governance.
    res_root = audit_executive_report_lessons_learned_institutionalization(
        {
            "lessons_learned": [
                {
                    "lesson_id": "LL-OK",
                    "root_cause_documented": True,
                    "preventive_action": "acción",
                    "opa_repository_ref": "OPA/LL/5",
                },
            ],
            "governance": {"lessons_learned": [{"lesson_id": "LL-IGNORED"}]},
        }
    )
    assert res_root["total_lessons"] == 1
    assert res_root["is_opa_ready"] is True


def test_audit_executive_report_lessons_learned_institutionalization_empty_or_none():
    """None, sin secuencia, entradas malformadas o sin lesson_id -> totales 0 y 0.0%."""
    from backend.services.project_export_service import (
        audit_executive_report_lessons_learned_institutionalization,
    )

    empty_result = {
        "total_lessons": 0,
        "missing_root_cause_lesson_ids": [],
        "missing_action_plan_lesson_ids": [],
        "unlinked_opa_lesson_ids": [],
        "institutionalization_rate_pct": 0.0,
        "is_opa_ready": False,
    }

    for payload in (None, {}, {"lessons_learned": None}, "not-a-mapping-arg-discarded"):
        assert audit_executive_report_lessons_learned_institutionalization(payload) == empty_result  # type: ignore[arg-type]

    malformed_seqs = (
        {"lessons_learned": "string-no-sequence"},
        {"lessons_learned": {"dict": "no"}},
        {"lessons_learned": [None, 42, "not-mapping", {"other": "x"}, {"lesson_id": "   "}]},
    )
    for payload in malformed_seqs:
        assert audit_executive_report_lessons_learned_institutionalization(payload) == empty_result


def test_audit_executive_report_risk_trigger_activation_governance_compliant():
    """Riesgos con condición definida, contingencia ejecutada al activarse y reserva autorizada pasan is_trigger_governance_compliant=True."""
    from backend.services.project_export_service import (
        ProjectExportService,
        audit_executive_report_risk_trigger_activation_governance,
    )

    report = {
        "risk_triggers": [
            {
                "risk_id": "RSK-10",
                "trigger_condition": "Latencia p99 > 500ms durante 15m",
                "trigger_activated": True,
                "contingency_plan_executed": True,
                "reserve_drawdown_authorized": True,
                "reserve_drawn_amount": 4500.0,
            },
            {
                "risk_id": "RSK-20",
                "trigger_condition": "Retraso de aduana > 5 días",
                "trigger_activated": False,
                "contingency_plan_executed": False,
                "reserve_drawdown_authorized": False,
                "reserve_drawn_amount": 0.0,
            },
        ]
    }
    res = audit_executive_report_risk_trigger_activation_governance(report)
    assert res == {
        "total_monitored_risks": 2,
        "activated_triggers_count": 1,
        "missing_trigger_condition_risk_ids": [],
        "unexecuted_contingency_risk_ids": [],
        "unauthorized_drawdown_risk_ids": [],
        "is_trigger_governance_compliant": True,
    }
    assert (
        ProjectExportService.audit_executive_report_risk_trigger_activation_governance(
            report
        )
        == res
    )


def test_audit_executive_report_risk_trigger_activation_governance_missing_cond_and_unexecuted():
    """Detecta riesgos sin trigger_condition y triggers activados sin plan de contingencia ejecutado."""
    from backend.services.project_export_service import (
        audit_executive_report_risk_trigger_activation_governance,
    )

    res = audit_executive_report_risk_trigger_activation_governance(
        {
            "governance": {
                "risk_triggers": [
                    {
                        "risk_id": "RSK-NO-COND",
                        "trigger_condition": "   ",
                        "trigger_activated": False,
                    },
                    {
                        "risk_id": "RSK-NO-EXEC",
                        "trigger_condition": "SPI < 0.85",
                        "trigger_activated": True,
                        "contingency_plan_executed": False,
                    },
                ]
            }
        }
    )
    assert res == {
        "total_monitored_risks": 2,
        "activated_triggers_count": 1,
        "missing_trigger_condition_risk_ids": ["RSK-NO-COND"],
        "unexecuted_contingency_risk_ids": ["RSK-NO-EXEC"],
        "unauthorized_drawdown_risk_ids": [],
        "is_trigger_governance_compliant": False,
    }


def test_audit_executive_report_risk_trigger_activation_governance_unauthorized_drawdown():
    """Detecta consumo de reserva sin trigger activado o sin autorización formal."""
    from backend.services.project_export_service import (
        audit_executive_report_risk_trigger_activation_governance,
    )

    res = audit_executive_report_risk_trigger_activation_governance(
        {
            "risk_triggers": [
                {
                    "risk_id": "RSK-DRAW-INACTIVE",
                    "trigger_condition": "Falla de enlace primario",
                    "trigger_activated": False,
                    "reserve_drawdown_authorized": True,
                    "reserve_drawn_amount": 1200.0,
                },
                {
                    "risk_id": "RSK-DRAW-UNAUTH",
                    "trigger_condition": "Incremento de tarifa > 12%",
                    "trigger_activated": True,
                    "contingency_plan_executed": True,
                    "reserve_drawdown_authorized": False,
                    "reserve_drawn_amount": 3000.0,
                },
            ]
        }
    )
    assert res == {
        "total_monitored_risks": 2,
        "activated_triggers_count": 1,
        "missing_trigger_condition_risk_ids": [],
        "unexecuted_contingency_risk_ids": [],
        "unauthorized_drawdown_risk_ids": [
            "RSK-DRAW-INACTIVE",
            "RSK-DRAW-UNAUTH",
        ],
        "is_trigger_governance_compliant": False,
    }


def test_audit_executive_report_risk_trigger_activation_governance_empty_or_invalid():
    """Reporte vacío, None o secuencia malformada devuelve total_monitored_risks=0 e is_trigger_governance_compliant=False."""
    from backend.services.project_export_service import (
        audit_executive_report_risk_trigger_activation_governance,
    )

    for payload in (
        None,
        {},
        {"risk_triggers": "not-seq"},
        {"risk_triggers": [{"risk_id": "  "}]},
    ):
        assert audit_executive_report_risk_trigger_activation_governance(payload) == {  # type: ignore[arg-type]
            "total_monitored_risks": 0,
            "activated_triggers_count": 0,
            "missing_trigger_condition_risk_ids": [],
            "unexecuted_contingency_risk_ids": [],
            "unauthorized_drawdown_risk_ids": [],
            "is_trigger_governance_compliant": False,
        }


def test_audit_executive_report_procurement_claims_settlement_clean():
    """Reclamos resueltos por negociación/mediación/arbitraje y documentados al cerrarse pasan is_claims_governance_clean=True."""
    from backend.services.project_export_service import (
        ProjectExportService,
        audit_executive_report_procurement_claims_settlement,
    )

    report = {
        "procurement_claims": [
            {
                "claim_id": "CLM-01",
                "disputed_amount": 8500.5,
                "resolution_method": "Negotiation",
                "status": "settled",
                "settlement_documented": True,
            },
            {
                "claim_id": "CLM-02",
                "disputed_amount": 3200.0,
                "resolution_method": "mediation",
                "status": "open",
                "settlement_documented": False,
            },
        ]
    }
    res = audit_executive_report_procurement_claims_settlement(report)
    assert res == {
        "total_claims": 2,
        "total_disputed_amount": 11700.5,
        "invalid_adr_method_claim_ids": [],
        "escalated_litigation_claim_ids": [],
        "undocumented_settlement_claim_ids": [],
        "is_claims_governance_clean": True,
    }
    assert (
        ProjectExportService.audit_executive_report_procurement_claims_settlement(
            report
        )
        == res
    )


def test_audit_executive_report_procurement_claims_settlement_invalid_and_litigation():
    """Detecta métodos fuera del catálogo ADR y reclamos escalados a litigio."""
    from backend.services.project_export_service import (
        audit_executive_report_procurement_claims_settlement,
    )

    res = audit_executive_report_procurement_claims_settlement(
        {
            "governance": {
                "procurement_claims": [
                    {
                        "claim_id": "CLM-BAD-ADR",
                        "disputed_amount": 1000.0,
                        "resolution_method": "verbal_handshake",
                        "status": "open",
                    },
                    {
                        "claim_id": "CLM-LIT",
                        "disputed_amount": 25000.0,
                        "resolution_method": "Litigation",
                        "status": "open",
                    },
                ]
            }
        }
    )
    assert res == {
        "total_claims": 2,
        "total_disputed_amount": 26000.0,
        "invalid_adr_method_claim_ids": ["CLM-BAD-ADR"],
        "escalated_litigation_claim_ids": ["CLM-LIT"],
        "undocumented_settlement_claim_ids": [],
        "is_claims_governance_clean": False,
    }


def test_audit_executive_report_procurement_claims_settlement_undocumented_closure():
    """Detecta reclamos en estado settled/closed sin settlement_documented=True."""
    from backend.services.project_export_service import (
        audit_executive_report_procurement_claims_settlement,
    )

    res = audit_executive_report_procurement_claims_settlement(
        {
            "procurement_claims": [
                {
                    "claim_id": "CLM-UNDOC-1",
                    "disputed_amount": 4000.0,
                    "resolution_method": "arbitration",
                    "status": "Closed",
                    "settlement_documented": False,
                }
            ]
        }
    )
    assert res == {
        "total_claims": 1,
        "total_disputed_amount": 4000.0,
        "invalid_adr_method_claim_ids": [],
        "escalated_litigation_claim_ids": [],
        "undocumented_settlement_claim_ids": ["CLM-UNDOC-1"],
        "is_claims_governance_clean": False,
    }


def test_audit_executive_report_procurement_claims_settlement_empty_or_invalid():
    """Reporte vacío, None o sin reclamos válidos devuelve total_claims=0 e is_claims_governance_clean=False."""
    from backend.services.project_export_service import (
        audit_executive_report_procurement_claims_settlement,
    )

    for payload in (
        None,
        {},
        {"procurement_claims": "invalid"},
        {"procurement_claims": [{"claim_id": "  "}]},
    ):
        assert audit_executive_report_procurement_claims_settlement(payload) == {  # type: ignore[arg-type]
            "total_claims": 0,
            "total_disputed_amount": 0.0,
            "invalid_adr_method_claim_ids": [],
            "escalated_litigation_claim_ids": [],
            "undocumented_settlement_claim_ids": [],
            "is_claims_governance_clean": False,
        }


def test_audit_executive_report_stakeholder_feedback_sla_healthy():
    """Feedback con action_owner_id, dentro de SLA y confirmado al cerrarse -> 100% e is_feedback_loop_healthy=True."""
    from backend.services.project_export_service import (
        ProjectExportService,
        audit_executive_report_stakeholder_feedback_sla,
    )

    report = {
        "stakeholder_feedback": [
            {
                "feedback_id": "FB-01",
                "response_days": 3.5,
                "action_owner_id": "USR-PM",
                "status": "resolved",
                "stakeholder_acknowledged": True,
            },
            {
                "feedback_id": "FB-02",
                "response_days": 7.0,
                "action_owner_id": "USR-COMMS",
                "status": "in_progress",
                "stakeholder_acknowledged": False,
            },
        ]
    }
    res = audit_executive_report_stakeholder_feedback_sla(report, max_sla_days=7.0)
    assert res == {
        "total_feedback_items": 2,
        "unassigned_feedback_ids": [],
        "sla_breached_feedback_ids": [],
        "unacknowledged_closure_feedback_ids": [],
        "sla_compliance_rate_pct": 100.0,
        "is_feedback_loop_healthy": True,
    }
    assert (
        ProjectExportService.audit_executive_report_stakeholder_feedback_sla(
            report, max_sla_days=7.0
        )
        == res
    )


def test_audit_executive_report_stakeholder_feedback_sla_unassigned_and_sla_breach():
    """Detecta feedback sin action_owner_id y demora mayor a max_sla_days (incluyendo fallback en governance)."""
    from backend.services.project_export_service import (
        audit_executive_report_stakeholder_feedback_sla,
    )

    res = audit_executive_report_stakeholder_feedback_sla(
        {
            "governance": {
                "stakeholder_feedback": [
                    {
                        "feedback_id": "FB-UNASSIGNED",
                        "response_days": 2.0,
                        "action_owner_id": "   ",
                        "status": "open",
                    },
                    {
                        "feedback_id": "FB-LATE",
                        "response_days": 10.5,
                        "action_owner_id": "USR-1",
                        "status": "open",
                    },
                ]
            }
        },
        max_sla_days=7.0,
    )
    assert res == {
        "total_feedback_items": 2,
        "unassigned_feedback_ids": ["FB-UNASSIGNED"],
        "sla_breached_feedback_ids": ["FB-LATE"],
        "unacknowledged_closure_feedback_ids": [],
        "sla_compliance_rate_pct": 50.0,
        "is_feedback_loop_healthy": False,
    }


def test_audit_executive_report_stakeholder_feedback_sla_unacknowledged_closure():
    """Feedback en estado closed/resolved sin stakeholder_acknowledged=True se reporta en unacknowledged_closure_feedback_ids."""
    from backend.services.project_export_service import (
        audit_executive_report_stakeholder_feedback_sla,
    )

    res = audit_executive_report_stakeholder_feedback_sla(
        {
            "stakeholder_feedback": [
                {
                    "feedback_id": "FB-CLOSED-NOACK",
                    "response_days": 4.0,
                    "action_owner_id": "USR-PM",
                    "status": "Closed",
                    "stakeholder_acknowledged": False,
                }
            ]
        }
    )
    assert res == {
        "total_feedback_items": 1,
        "unassigned_feedback_ids": [],
        "sla_breached_feedback_ids": [],
        "unacknowledged_closure_feedback_ids": ["FB-CLOSED-NOACK"],
        "sla_compliance_rate_pct": 100.0,
        "is_feedback_loop_healthy": False,
    }


def test_audit_executive_report_stakeholder_feedback_sla_empty_or_invalid():
    """Reporte vacío, None o sin items válidos devuelve total_feedback_items=0 e is_feedback_loop_healthy=False."""
    from backend.services.project_export_service import (
        audit_executive_report_stakeholder_feedback_sla,
    )

    for payload in (
        None,
        {},
        {"stakeholder_feedback": "invalid"},
        {"stakeholder_feedback": [{"feedback_id": "  "}]},
    ):
        assert audit_executive_report_stakeholder_feedback_sla(payload) == {  # type: ignore[arg-type]
            "total_feedback_items": 0,
            "unassigned_feedback_ids": [],
            "sla_breached_feedback_ids": [],
            "unacknowledged_closure_feedback_ids": [],
            "sla_compliance_rate_pct": 0.0,
            "is_feedback_loop_healthy": False,
        }


def test_audit_executive_report_benefits_handover_kpis_ready():
    """Beneficios cuantificados, con dueño, cadencia válida y custodio -> ready."""
    from backend.services.project_export_service import (
        ProjectExportService,
        audit_executive_report_benefits_handover_kpis,
    )

    res = audit_executive_report_benefits_handover_kpis(
        {
            "benefits_kpis": [
                {
                    "benefit_id": "HF-B1",
                    "baseline_value": 120,
                    "target_value": 200.5,
                    "benefit_owner_id": "u-1",
                    "measurement_cadence": "monthly",
                    "operational_custodian_accepted": True,
                },
                {
                    "benefit_id": "HF-B2",
                    "baseline_value": 5,
                    "target_value": 9,
                    "benefit_owner_id": "u-2",
                    "measurement_cadence": "ANNUAL",
                    "operational_custodian_accepted": True,
                },
            ]
        }
    )
    assert res["total_benefits"] == 2
    assert res["unquantified_benefit_ids"] == []
    assert res["ungoverned_cadence_benefit_ids"] == []
    assert res["unaccepted_handover_benefit_ids"] == []
    assert res["is_benefits_handover_ready"] is True

    static_res = ProjectExportService.audit_executive_report_benefits_handover_kpis(
        {
            "benefits_kpis": [
                {
                    "benefit_id": "HF-B1",
                    "baseline_value": 1,
                    "target_value": 2,
                    "benefit_owner_id": "u-1",
                    "measurement_cadence": "weekly",
                    "operational_custodian_accepted": True,
                },
            ]
        }
    )
    assert static_res["is_benefits_handover_ready"] is True


def test_audit_executive_report_benefits_handover_kpis_unquantified():
    """> Sin baseline/target numéricos; bool explícitamente rechazado."""
    from backend.services.project_export_service import (
        audit_executive_report_benefits_handover_kpis,
    )

    res = audit_executive_report_benefits_handover_kpis(
        {
            "benefits_kpis": [
                {
                    "benefit_id": "HF-NO-BASE",
                    "target_value": 30,
                    "benefit_owner_id": "u-1",
                    "measurement_cadence": "monthly",
                    "operational_custodian_accepted": True,
                },
                {
                    "benefit_id": "HF-BOOL",
                    "baseline_value": True,
                    "target_value": 30,
                    "benefit_owner_id": "u-1",
                    "measurement_cadence": "monthly",
                    "operational_custodian_accepted": True,
                },
                {
                    "benefit_id": "HF-STR",
                    "baseline_value": "alta",
                    "target_value": 30,
                    "benefit_owner_id": "u-1",
                    "measurement_cadence": "monthly",
                    "operational_custodian_accepted": True,
                },
            ]
        }
    )
    assert res["total_benefits"] == 3
    assert res["unquantified_benefit_ids"] == ["HF-NO-BASE", "HF-BOOL", "HF-STR"]
    assert res["ungoverned_cadence_benefit_ids"] == []
    assert res["unaccepted_handover_benefit_ids"] == []
    assert res["is_benefits_handover_ready"] is False


def test_audit_executive_report_benefits_handover_kpis_governance_and_fallback():
    """> Cadencia inválida o dueño ausente; custodio sin aceptar; fallback governance."""
    from backend.services.project_export_service import (
        audit_executive_report_benefits_handover_kpis,
    )

    res_nested = audit_executive_report_benefits_handover_kpis(
        {
            "governance": {
                "benefits_kpis": [
                    {
                        "benefit_id": "HF-NO-OWNER",
                        "baseline_value": 1,
                        "target_value": 2,
                        "measurement_cadence": "monthly",
                        "operational_custodian_accepted": True,
                    },
                    {
                        "benefit_id": "HF-BAD-CADENCE",
                        "baseline_value": 1,
                        "target_value": 2,
                        "benefit_owner_id": "u-2",
                        "measurement_cadence": "diaria",
                        "operational_custodian_accepted": False,
                    },
                ]
            }
        }
    )
    assert res_nested["total_benefits"] == 2
    assert res_nested["ungoverned_cadence_benefit_ids"] == ["HF-NO-OWNER", "HF-BAD-CADENCE"]
    assert res_nested["unaccepted_handover_benefit_ids"] == ["HF-BAD-CADENCE"]
    assert res_nested["is_benefits_handover_ready"] is False

    res_root_priority = audit_executive_report_benefits_handover_kpis(
        {
            "benefits_kpis": [
                {
                    "benefit_id": "HF-OK",
                    "baseline_value": 1,
                    "target_value": 2,
                    "benefit_owner_id": "u-1",
                    "measurement_cadence": "quarterly",
                    "operational_custodian_accepted": True,
                },
            ],
            "governance": {"benefits_kpis": [{"benefit_id": "HF-IGNORED"}]},
        }
    )
    assert res_root_priority["total_benefits"] == 1
    assert res_root_priority["is_benefits_handover_ready"] is True


def test_audit_executive_report_benefits_handover_kpis_empty_or_none():
    """None, vacío, secuencia malformada o sin benefit_id -> 0 beneficios."""
    from backend.services.project_export_service import (
        audit_executive_report_benefits_handover_kpis,
    )

    empty_result = {
        "total_benefits": 0,
        "unquantified_benefit_ids": [],
        "ungoverned_cadence_benefit_ids": [],
        "unaccepted_handover_benefit_ids": [],
        "is_benefits_handover_ready": False,
    }

    for payload in (
        None,
        {},
        {"benefits_kpis": None},
        {"benefits_kpis": "string-no-sequence"},
        {"benefits_kpis": {"dict": "no"}},
        42,
        [],
        ["no-dict", {"benefits_kpis": []}],
        [{"benefit_id": "   "}, {"other": "x"}],
    ):
        assert audit_executive_report_benefits_handover_kpis(payload) == empty_result  # type: ignore[arg-type]


def test_audit_executive_report_resource_spof_and_overallocation_healthy():
    """Recursos balanceados con respaldo asignado para habilidades críticas -> healthy."""
    from backend.services.project_export_service import (
        audit_executive_report_resource_spof_and_overallocation,
    )

    report = {
        "resource_allocations": [
            {
                "resource_id": "RES-ARCH-01",
                "allocation_pct": 90.0,
                "overtime_pct": 5.0,
                "is_critical_skill": True,
                "assigned_critical_tasks_count": 3,
                "backup_resource_id": "RES-ARCH-02",
            },
            {
                "id": "RES-DEV-02",
                "allocation_pct": 80.0,
                "overtime_pct": 0.0,
                "is_critical_skill": False,
                "assigned_critical_tasks_count": 0,
            },
        ]
    }
    res = audit_executive_report_resource_spof_and_overallocation(report)
    assert res == {
        "total_resources": 2,
        "overallocated_resource_ids": [],
        "burnout_risk_resource_ids": [],
        "spof_unbacked_resource_ids": [],
        "is_resource_governance_healthy": True,
        "status": "healthy",
        "recommendations": [],
    }


def test_audit_executive_report_resource_spof_and_overallocation_spof_and_overallocated_critical():
    """Detecta SPOF sin backup_resource_id y sobreasignación > 100% -> critical."""
    from backend.services.project_export_service import (
        audit_executive_report_resource_spof_and_overallocation,
    )

    res = audit_executive_report_resource_spof_and_overallocation(
        {
            "resource_allocations": [
                {
                    "resource_id": "RES-SPOF",
                    "allocation_pct": 125.0,
                    "overtime_pct": 10.0,
                    "is_critical_skill": True,
                    "backup_resource_id": "   ",
                },
                {
                    "resource_id": "RES-CP-TASK",
                    "allocation_pct": 95.0,
                    "overtime_pct": 0.0,
                    "is_critical_skill": False,
                    "assigned_critical_tasks_count": 2,
                    "backup_resource_id": "",
                },
            ]
        }
    )
    assert res["overallocated_resource_ids"] == ["RES-SPOF"]
    assert res["spof_unbacked_resource_ids"] == ["RES-SPOF", "RES-CP-TASK"]
    assert res["is_resource_governance_healthy"] is False
    assert res["status"] == "critical"
    assert len(res["recommendations"]) == 2


def test_audit_executive_report_resource_spof_and_overallocation_burnout_warning_and_fallback():
    """Detecta exceso de horas extra (overtime_pct > 15%) y fallback a report['governance']['resource_allocations'] -> warning."""
    from backend.services.project_export_service import (
        audit_executive_report_resource_spof_and_overallocation,
    )

    res = audit_executive_report_resource_spof_and_overallocation(
        {
            "governance": {
                "resource_allocations": [
                    {
                        "resource_id": "RES-OT",
                        "allocation_pct": 100.0,
                        "overtime_pct": 22.5,
                        "is_critical_skill": False,
                    }
                ]
            }
        },
        max_allocation_pct=100.0,
        max_overtime_pct=15.0,
    )
    assert res["total_resources"] == 1
    assert res["burnout_risk_resource_ids"] == ["RES-OT"]
    assert res["overallocated_resource_ids"] == []
    assert res["spof_unbacked_resource_ids"] == []
    assert res["is_resource_governance_healthy"] is False
    assert res["status"] == "warning"
    assert len(res["recommendations"]) == 1


def test_audit_executive_report_resource_spof_and_overallocation_empty_and_service_staticmethod():
    """Entradas vacías/None e invocación vía ProjectExportService.audit_executive_report_resource_spof_and_overallocation."""
    from backend.services.project_export_service import (
        ProjectExportService,
        audit_executive_report_resource_spof_and_overallocation,
    )

    for payload in (None, {}, {"resource_allocations": "invalid"}):
        res = audit_executive_report_resource_spof_and_overallocation(payload)  # type: ignore[arg-type]
        assert res["total_resources"] == 0
        assert res["is_resource_governance_healthy"] is True
        assert res["status"] == "healthy"

    sample = {
        "resource_allocations": [
            {"resource_id": "R-1", "allocation_pct": 85.0, "overtime_pct": 5.0}
        ]
    }
    assert (
        ProjectExportService.audit_executive_report_resource_spof_and_overallocation(
            sample
        )
        == audit_executive_report_resource_spof_and_overallocation(sample)
    )


def test_audit_executive_report_change_readiness_and_adoption_ready_units():
    """Unidades listas: formación y preparación sobre los mínimos, champion e hypercare ok."""
    from backend.services.project_export_service import (
        audit_executive_report_change_readiness_and_adoption,
    )

    report = {
        "change_readiness_units": [
            {
                "unit_id": "U-1",
                "training_completion_pct": 90.0,
                "readiness_score_pct": 80.0,
                "change_champion": "Ana", 
                "hypercare_support_ready": True,
            },
            {
                "id": "U-2",
                "training_completion_pct": 100,
                "readiness_score_pct": 85,
                "change_champion": "Luis",
                "hypercare_support_ready": True,
            },
        ]
    }
    res = audit_executive_report_change_readiness_and_adoption(report)
    assert res == {
        "total_units": 2,
        "insufficient_training_unit_ids": [],
        "low_readiness_unit_ids": [],
        "missing_champion_or_hypercare_unit_ids": [],
        "is_change_readiness_compliant": True,
    }

    # Bordes exactos de los mínimos (>=) siguen siendo compliant.
    edge = audit_executive_report_change_readiness_and_adoption(
        {
            "change_readiness_units": [
                {
                    "unit_id": "U-edge",
                    "training_completion_pct": 85.0,
                    "readiness_score_pct": 75.0,
                    "change_champion": "Champion",
                    "hypercare_support_ready": True,
                }
            ]
        }
    )
    assert edge["is_change_readiness_compliant"] is True


def test_audit_executive_report_change_readiness_and_adoption_low_scores():
    """Detecta capacitación insuficiente y puntaje de preparación bajo por unidad."""
    from backend.services.project_export_service import (
        audit_executive_report_change_readiness_and_adoption,
    )

    report = {
        "change_readiness_units": [
            {
                "unit_id": "U-1",
                "training_completion_pct": 50.0,
                "readiness_score_pct": 60.0,
                "change_champion": "Ana",
                "hypercare_support_ready": True,
            },
            {
                "unit_id": "U-2",
                "training_completion_pct": 84.99,
                "readiness_score_pct": 74.99,
                "change_champion": "Luis",
                "hypercare_support_ready": True,
            },
            # bool no es un pct válido -> cuenta como 0.0 en ambas bandas.
            {
                "unit_id": "U-3",
                "training_completion_pct": True,
                "readiness_score_pct": True,
                "change_champion": "Marta",
                "hypercare_support_ready": True,
            },
        ]
    }
    res = audit_executive_report_change_readiness_and_adoption(report)
    assert res["total_units"] == 3
    assert res["insufficient_training_unit_ids"] == ["U-1", "U-2", "U-3"]
    assert res["low_readiness_unit_ids"] == ["U-1", "U-2", "U-3"]
    assert res["missing_champion_or_hypercare_unit_ids"] == []
    assert res["is_change_readiness_compliant"] is False

    # Umbrales personalizados elevan la exigencia.
    strict = audit_executive_report_change_readiness_and_adoption(
        report,
        min_training_completion_pct=95.0,
        min_readiness_score_pct=90.0,
    )
    assert strict["insufficient_training_unit_ids"] == ["U-1", "U-2", "U-3"]
    assert strict["low_readiness_unit_ids"] == ["U-1", "U-2", "U-3"]


def test_audit_executive_report_change_readiness_and_adoption_missing_champion_and_fallback():
    """Champion ausente o hypercare no listo falla; soporta fallback governance."""
    from backend.services.project_export_service import (
        audit_executive_report_change_readiness_and_adoption,
    )

    report = {
        "governance": {
            "change_readiness_units": [
                {
                    "unit_id": "U-1",
                    "training_completion_pct": 90.0,
                    "readiness_score_pct": 80.0,
                    "hypercare_support_ready": True,
                },
                {
                    "unit_id": "U-2",
                    "training_completion_pct": 90.0,
                    "readiness_score_pct": 80.0,
                    "change_champion": "   ",
                    "hypercare_support_ready": True,
                },
                {
                    "unit_id": "U-3",
                    "training_completion_pct": 90.0,
                    "readiness_score_pct": 80.0,
                    "change_champion": "Marta",
                    "hypercare_support_ready": False,
                },
            ]
        }
    }
    res = audit_executive_report_change_readiness_and_adoption(report)
    assert res["total_units"] == 3
    assert res["insufficient_training_unit_ids"] == []
    assert res["low_readiness_unit_ids"] == []
    assert res["missing_champion_or_hypercare_unit_ids"] == ["U-1", "U-2", "U-3"]
    assert res["is_change_readiness_compliant"] is False


def test_audit_executive_report_change_readiness_and_adoption_empty_and_service_proxy():
    """Entradas vacías/None -> compliant False (total_units==0); proxy estático de la clase."""
    from backend.services.project_export_service import (
        ProjectExportService,
        audit_executive_report_change_readiness_and_adoption,
    )

    res_none = audit_executive_report_change_readiness_and_adoption(None)
    assert res_none == {
        "total_units": 0,
        "insufficient_training_unit_ids": [],
        "low_readiness_unit_ids": [],
        "missing_champion_or_hypercare_unit_ids": [],
        "is_change_readiness_compliant": False,
    }
    assert audit_executive_report_change_readiness_and_adoption({})["total_units"] == 0
    assert (
        audit_executive_report_change_readiness_and_adoption(
            {"change_readiness_units": "not-a-sequence"}
        )["total_units"]
        == 0
    )
    assert (
        audit_executive_report_change_readiness_and_adoption(
            {"change_readiness_units": [{"unit_id": "   ", "nested_id": "x"}]}
        )["total_units"]
        == 0
    )

    sample = {
        "change_readiness_units": [
            {
                "unit_id": "U-1",
                "training_completion_pct": 90.0,
                "readiness_score_pct": 80.0,
                "change_champion": "Ana",
                "hypercare_support_ready": True,
            }
        ]
    }
    assert (
        ProjectExportService.audit_executive_report_change_readiness_and_adoption(sample)
        == audit_executive_report_change_readiness_and_adoption(sample)
    )
    import backend.services.project_export_service as _m

    assert "audit_executive_report_change_readiness_and_adoption" in _m.__all__


def test_audit_executive_report_contract_closeout_and_claims_compliant():
    """Contratos cerrados con entregables aceptados, paz y salvo firmado, sin reclamos y garantía con SLA -> compliant True."""
    from backend.services.project_export_service import (
        ProjectExportService,
        audit_executive_report_contract_closeout_and_claims,
    )

    contracts = [
        {
            "contract_id": "CNT-101",
            "status": "closed",
            "open_claims_or_disputes_count": 0,
            "final_deliverables_accepted": True,
            "lien_waiver_or_release_signed": True,
            "warranty_period_months": 12,
            "warranty_sla_documented": True,
        },
        {
            "id": "CNT-102",
            "status": "active",
            "open_claims_or_disputes_count": 0,
            "final_deliverables_accepted": False,
            "lien_waiver_or_release_signed": False,
            "warranty_period_months": 0,
            "warranty_sla_documented": False,
        },
    ]
    res = audit_executive_report_contract_closeout_and_claims(contracts)
    assert res == {
        "total_evaluated": 2,
        "unresolved_claim_contract_ids": [],
        "premature_closeout_contract_ids": [],
        "missing_warranty_sla_contract_ids": [],
        "is_contract_closeout_compliant": True,
    }
    assert (
        ProjectExportService.audit_executive_report_contract_closeout_and_claims(
            contracts
        )
        == res
    )


def test_audit_executive_report_contract_closeout_and_claims_unresolved_and_premature():
    """Detecta reclamos abiertos y cierre prematuro sin aceptación de entregables o paz y salvo."""
    from backend.services.project_export_service import (
        audit_executive_report_contract_closeout_and_claims,
    )

    contracts = [
        {
            "contract_id": "CNT-CLAIM-CLOSED",
            "status": "completed",
            "open_claims_or_disputes_count": 2,
            "final_deliverables_accepted": True,
            "lien_waiver_or_release_signed": True,
        },
        {
            "contract_id": "CNT-NO-WAIVER",
            "status": "closed",
            "open_claims_or_disputes_count": 0,
            "final_deliverables_accepted": True,
            "lien_waiver_or_release_signed": False,
        },
        {
            "contract_id": "CNT-NO-DELIV",
            "status": "terminated",
            "open_claims_or_disputes_count": 0,
            "final_deliverables_accepted": False,
            "lien_waiver_or_release_signed": True,
        },
    ]
    res = audit_executive_report_contract_closeout_and_claims(contracts)
    assert res["total_evaluated"] == 3
    assert res["unresolved_claim_contract_ids"] == ["CNT-CLAIM-CLOSED"]
    assert res["premature_closeout_contract_ids"] == [
        "CNT-CLAIM-CLOSED",
        "CNT-NO-WAIVER",
        "CNT-NO-DELIV",
    ]
    assert res["missing_warranty_sla_contract_ids"] == []
    assert res["is_contract_closeout_compliant"] is False


def test_audit_executive_report_contract_closeout_and_claims_missing_warranty_sla():
    """Garantía > 0 meses sin SLA documentado agrega a missing_warranty_sla_contract_ids."""
    from backend.services.project_export_service import (
        audit_executive_report_contract_closeout_and_claims,
    )

    contracts = [
        {
            "contract_id": "CNT-WARR-NO-SLA",
            "status": "closed",
            "open_claims_or_disputes_count": 0,
            "final_deliverables_accepted": True,
            "lien_waiver_or_release_signed": True,
            "warranty_period_months": 24,
            "warranty_sla_documented": False,
        }
    ]
    res = audit_executive_report_contract_closeout_and_claims(contracts)
    assert res["total_evaluated"] == 1
    assert res["unresolved_claim_contract_ids"] == []
    assert res["premature_closeout_contract_ids"] == []
    assert res["missing_warranty_sla_contract_ids"] == ["CNT-WARR-NO-SLA"]
    assert res["is_contract_closeout_compliant"] is False


def test_audit_executive_report_contract_closeout_and_claims_invalid_inputs_and_export():
    """Ignora entradas no válidas (None, str, bytes, dict sin id) y verifica exportación en __all__."""
    import backend.services.project_export_service as _m
    from backend.services.project_export_service import (
        audit_executive_report_contract_closeout_and_claims,
    )

    assert "audit_executive_report_contract_closeout_and_claims" in _m.__all__
    for bad in (None, "not-a-seq", b"bytes", bytearray(b"abc"), [{"contract_id": "   "}, 123]):
        res = audit_executive_report_contract_closeout_and_claims(bad)
        assert res == {
            "total_evaluated": 0,
            "unresolved_claim_contract_ids": [],
            "premature_closeout_contract_ids": [],
            "missing_warranty_sla_contract_ids": [],
            "is_contract_closeout_compliant": True,
        }


def test_audit_executive_report_strategic_alignment_and_esg_compliant():
    """Iniciativas alineadas a OKR/pilar con score >= 70 e impacto ESG gestionado."""
    from backend.services.project_export_service import (
        audit_executive_report_strategic_alignment_and_esg,
    )

    initiatives = [
        {
            "initiative_id": "I-1",
            "okr_or_pillar_code": "OKR-1",
            "strategic_alignment_score": 85.0,
            "esg_impact_assessed": True,
        },
        {
            "id": "I-2",
            "okr_or_pillar_code": "PILLAR-2",
            "strategic_alignment_score": 70,
            "esg_impact_assessed": True,
            "has_negative_environmental_or_social_impact": True,
            "esg_mitigation_plan_approved": True,
        },
    ]
    res = audit_executive_report_strategic_alignment_and_esg(initiatives)
    assert res == {
        "total_evaluated": 2,
        "unaligned_strategic_initiative_ids": [],
        "unassessed_esg_initiative_ids": [],
        "unmitigated_esg_risk_initiative_ids": [],
        "is_strategic_and_esg_compliant": True,
    }


def test_audit_executive_report_strategic_alignment_and_esg_unaligned():
    """Detecta iniciativas sin OKR/pilar o con score bajo el minimo (comparacion estricta)."""
    from backend.services.project_export_service import (
        audit_executive_report_strategic_alignment_and_esg,
    )

    initiatives = [
        {"initiative_id": "N-1", "okr_or_pillar_code": "   ",
         "strategic_alignment_score": 90.0, "esg_impact_assessed": True},
        {"initiative_id": "N-2", "okr_or_pillar_code": "OKR-2",
         "strategic_alignment_score": 69.99, "esg_impact_assessed": True},
        {"initiative_id": "N-3", "okr_or_pillar_code": "OKR-3",
         "strategic_alignment_score": "oops", "esg_impact_assessed": True},
        {"initiative_id": "E-1", "okr_or_pillar_code": "OKR-4",
         "strategic_alignment_score": 70.0, "esg_impact_assessed": True},
    ]
    res = audit_executive_report_strategic_alignment_and_esg(initiatives)
    assert res["total_evaluated"] == 4
    assert res["unaligned_strategic_initiative_ids"] == ["N-1", "N-2", "N-3"]
    assert res["unassessed_esg_initiative_ids"] == []
    assert res["unmitigated_esg_risk_initiative_ids"] == []
    assert res["is_strategic_and_esg_compliant"] is False

    # Umbral personalizado eleva la exigencia.
    strict = audit_executive_report_strategic_alignment_and_esg(
        initiatives, min_alignment_score=95.0
    )
    assert strict["unaligned_strategic_initiative_ids"] == [
        "N-1", "N-2", "N-3", "E-1",
    ]


def test_audit_executive_report_strategic_alignment_and_esg_esg_gaps():
    """Detecta ESG sin evaluar e impacto negativo sin plan de mitigacion aprobado."""
    from backend.services.project_export_service import (
        audit_executive_report_strategic_alignment_and_esg,
    )

    initiatives = [
        {"initiative_id": "G-1", "okr_or_pillar_code": "OKR-1",
         "strategic_alignment_score": 80.0},  # esg_impact_assessed default False.
        {"initiative_id": "G-2", "okr_or_pillar_code": "OKR-2",
         "strategic_alignment_score": 80.0, "esg_impact_assessed": True,
         "has_negative_environmental_or_social_impact": True,
         "esg_mitigation_plan_approved": False},
        {"initiative_id": "G-3", "okr_or_pillar_code": "OKR-3",
         "strategic_alignment_score": 80.0, "esg_impact_assessed": True,
         "has_negative_environmental_or_social_impact": True,
         "esg_mitigation_plan_approved": True},
        {"initiative_id": "G-4", "okr_or_pillar_code": "OKR-4",
         "strategic_alignment_score": 80.0, "esg_impact_assessed": True,
         "has_negative_environmental_or_social_impact": False,  # sin impacto -> sin exigencia.
         "esg_mitigation_plan_approved": False},
    ]
    res = audit_executive_report_strategic_alignment_and_esg(initiatives)
    assert res["total_evaluated"] == 4
    assert res["unassessed_esg_initiative_ids"] == ["G-1"]
    assert res["unmitigated_esg_risk_initiative_ids"] == ["G-2"]
    assert res["is_strategic_and_esg_compliant"] is False


def test_audit_executive_report_strategic_alignment_and_esg_empty_and_service_proxy():
    """Entradas vacias/None/invalidas + llamada via ProjectExportService (staticmethod + __all__)."""
    from backend.services.project_export_service import (
        ProjectExportService,
        audit_executive_report_strategic_alignment_and_esg,
    )
    import backend.services.project_export_service as _m

    res_none = audit_executive_report_strategic_alignment_and_esg(None)
    assert res_none == {
        "total_evaluated": 0,
        "unaligned_strategic_initiative_ids": [],
        "unassessed_esg_initiative_ids": [],
        "unmitigated_esg_risk_initiative_ids": [],
        "is_strategic_and_esg_compliant": True,
    }
    assert audit_executive_report_strategic_alignment_and_esg("not-a-sequence")["total_evaluated"] == 0
    assert (
        audit_executive_report_strategic_alignment_and_esg(
            ["not-a-mapping", {"initiative_id": "   "}, {"other_id": "x"}]
        )["total_evaluated"]
        == 0
    )
    assert "audit_executive_report_strategic_alignment_and_esg" in _m.__all__

    sample = [
        {
            "initiative_id": "I-1",
            "okr_or_pillar_code": "OKR-1",
            "strategic_alignment_score": 90.0,
            "esg_impact_assessed": True,
        }
    ]
    assert (
        ProjectExportService.audit_executive_report_strategic_alignment_and_esg(sample)
        == audit_executive_report_strategic_alignment_and_esg(sample)
    )


def test_audit_executive_report_rag_status_and_narrative_consistency_transparent():
    """Valida KPIs con semáforo coherente (incluyendo yellow->amber) y narrativa correctiva suficiente."""
    from backend.services.project_export_service import (
        ProjectExportService,
        audit_executive_report_rag_status_and_narrative_consistency,
    )

    kpis = [
        {
            "kpi_id": "KPI-COST-01",
            "reported_rag": "green",
            "variance_pct": -2.0,
            "amber_threshold_pct": -5.0,
            "red_threshold_pct": -10.0,
            "corrective_action_narrative": "",
        },
        {
            "id": "KPI-SCHED-02",
            "reported_rag": "YELLOW",
            "variance_pct": -6.5,
            "amber_threshold_pct": -5.0,
            "red_threshold_pct": -10.0,
            "corrective_action_narrative": "Fast-tracking en paquetes críticos aprobado.",
        },
        {
            "kpi_id": "KPI-QUAL-03",
            "reported_rag": "red",
            "variance_pct": -12.0,
            "amber_threshold_pct": -5.0,
            "red_threshold_pct": -10.0,
            "corrective_action_narrative": "Se activó contingencia de pruebas automatizadas.",
        },
    ]
    res = audit_executive_report_rag_status_and_narrative_consistency(kpis)
    assert res == {
        "total_evaluated": 3,
        "invalid_rag_label_kpi_ids": [],
        "watermelon_masked_status_kpi_ids": [],
        "missing_corrective_narrative_kpi_ids": [],
        "is_rag_reporting_transparent": True,
    }
    assert (
        ProjectExportService.audit_executive_report_rag_status_and_narrative_consistency(
            kpis
        )
        == res
    )


def test_audit_executive_report_rag_watermelon_masking_and_invalid_labels():
    """Detecta proyectos sandía (watermelon masking: red->amber/green, amber->green) y etiquetas RAG inválidas."""
    from backend.services.project_export_service import (
        audit_executive_report_rag_status_and_narrative_consistency,
    )

    kpis = [
        {
            "kpi_id": "KPI-WM-RED-AS-GREEN",
            "reported_rag": "green",
            "variance_pct": -14.0,
            "corrective_action_narrative": "Plan de recuperación en curso con PMO.",
        },
        {
            "kpi_id": "KPI-WM-AMBER-AS-GREEN",
            "reported_rag": "green",
            "variance_pct": -7.0,
            "corrective_action_narrative": "Ajuste de turnos para recuperar atraso menor.",
        },
        {
            "kpi_id": "KPI-BAD-LABEL",
            "reported_rag": "blue",
            "variance_pct": 1.0,
        },
    ]
    res = audit_executive_report_rag_status_and_narrative_consistency(kpis)
    assert res["total_evaluated"] == 3
    assert res["invalid_rag_label_kpi_ids"] == ["KPI-BAD-LABEL"]
    assert res["watermelon_masked_status_kpi_ids"] == [
        "KPI-WM-RED-AS-GREEN",
        "KPI-WM-AMBER-AS-GREEN",
    ]
    assert res["missing_corrective_narrative_kpi_ids"] == []
    assert res["is_rag_reporting_transparent"] is False


def test_audit_executive_report_rag_missing_corrective_narrative():
    """Exige narrativa >= 15 caracteres cuando el estado objetivo o reportado es amber o red."""
    from backend.services.project_export_service import (
        audit_executive_report_rag_status_and_narrative_consistency,
    )

    kpis = [
        {
            "kpi_id": "KPI-SHORT-NARR",
            "reported_rag": "amber",
            "variance_pct": -6.0,
            "corrective_action_narrative": "En revisión",
        },
        {
            "kpi_id": "KPI-REPORTED-RED-NO-NARR",
            "reported_rag": "red",
            "variance_pct": 0.0,
            "corrective_action_narrative": "   ",
        },
    ]
    res = audit_executive_report_rag_status_and_narrative_consistency(kpis)
    assert res["total_evaluated"] == 2
    assert res["invalid_rag_label_kpi_ids"] == []
    assert res["watermelon_masked_status_kpi_ids"] == []
    assert res["missing_corrective_narrative_kpi_ids"] == [
        "KPI-SHORT-NARR",
        "KPI-REPORTED-RED-NO-NARR",
    ]
    assert res["is_rag_reporting_transparent"] is False


def test_audit_executive_report_rag_invalid_inputs_and_export():
    """Ignora entradas no secuencia o ítems sin kpi_id y verifica exportación en __all__."""
    import backend.services.project_export_service as _m
    from backend.services.project_export_service import (
        audit_executive_report_rag_status_and_narrative_consistency,
    )

    assert (
        "audit_executive_report_rag_status_and_narrative_consistency"
        in _m.__all__
    )
    for bad in (None, "not-a-seq", b"bytes", bytearray(b"xyz"), [{"kpi_id": "  "}, 99]):
        assert audit_executive_report_rag_status_and_narrative_consistency(
            bad
        ) == {
            "total_evaluated": 0,
            "invalid_rag_label_kpi_ids": [],
            "watermelon_masked_status_kpi_ids": [],
            "missing_corrective_narrative_kpi_ids": [],
            "is_rag_reporting_transparent": True,
        }


def test_audit_executive_report_reserve_drawdown_burn_rate_compliant():
    """Reservas de contingencia y gestión alineadas al avance, vinculadas y aprobadas."""
    from backend.services.project_export_service import (
        ProjectExportService,
        audit_executive_report_reserve_drawdown_burn_rate,
    )

    tranches = [
        {
            "tranche_id": "TR-CONT-01",
            "reserve_type": "contingency",
            "initial_amount": 50000.0,
            "consumed_amount": 20000.0,
            "linked_risk_or_change_ids": ["RSK-101"],
            "executive_sponsor_approved": False,
        },
        {
            "tranche_id": "TR-MGMT-02",
            "reserve_type": "MANAGEMENT",
            "initial_amount": 30000.0,
            "consumed_amount": 10000.0,
            "linked_risk_or_change_ids": ["CR-202"],
            "executive_sponsor_approved": True,
        },
    ]
    res = audit_executive_report_reserve_drawdown_burn_rate(
        tranches, project_percent_complete=50.0, max_burn_to_progress_ratio=1.25
    )
    assert res == {
        "total_tranches": 2,
        "total_initial_reserve": 80000.0,
        "total_consumed_reserve": 30000.0,
        "overall_drawdown_pct": 37.5,
        "invalid_reserve_type_tranche_ids": [],
        "overdrawn_or_negative_tranche_ids": [],
        "unlinked_drawdown_tranche_ids": [],
        "unapproved_management_reserve_tranche_ids": [],
        "accelerated_burn_tranche_ids": [],
        "is_reserve_drawdown_compliant": True,
    }
    assert (
        ProjectExportService.audit_executive_report_reserve_drawdown_burn_rate(
            tranches, project_percent_complete=50.0
        )
        == res
    )


def test_audit_executive_report_reserve_drawdown_overdrawn_and_unlinked():
    """Detecta sobregiro (consumed > initial), tipo inválido y consumo sin riesgo/cambio vinculado."""
    from backend.services.project_export_service import (
        audit_executive_report_reserve_drawdown_burn_rate,
    )

    tranches = [
        {
            "tranche_id": "TR-OVERDRAWN",
            "reserve_type": "contingency",
            "initial_amount": 10000.0,
            "consumed_amount": 12500.0,
            "linked_risk_or_change_ids": ["RSK-1"],
        },
        {
            "tranche_id": "TR-UNLINKED",
            "reserve_type": "slush_fund",
            "initial_amount": 20000.0,
            "consumed_amount": 5000.0,
            "linked_risk_or_change_ids": ["   "],
        },
    ]
    res = audit_executive_report_reserve_drawdown_burn_rate(
        tranches, project_percent_complete=80.0
    )
    assert res["total_tranches"] == 2
    assert res["invalid_reserve_type_tranche_ids"] == ["TR-UNLINKED"]
    assert res["overdrawn_or_negative_tranche_ids"] == ["TR-OVERDRAWN"]
    assert res["unlinked_drawdown_tranche_ids"] == ["TR-UNLINKED"]
    assert res["is_reserve_drawdown_compliant"] is False


def test_audit_executive_report_reserve_drawdown_unapproved_mgmt_and_accelerated_burn():
    """Detecta uso de reserva de gestión sin sponsor y quema acelerada frente al avance del proyecto."""
    from backend.services.project_export_service import (
        audit_executive_report_reserve_drawdown_burn_rate,
    )

    tranches = [
        {
            "tranche_id": "TR-MGMT-NO-SPONSOR",
            "reserve_type": "management",
            "initial_amount": 40000.0,
            "consumed_amount": 32000.0,
            "linked_risk_or_change_ids": ["CR-99"],
            "executive_sponsor_approved": False,
        }
    ]
    res = audit_executive_report_reserve_drawdown_burn_rate(
        tranches, project_percent_complete=20.0, max_burn_to_progress_ratio=1.25
    )
    assert res["unapproved_management_reserve_tranche_ids"] == [
        "TR-MGMT-NO-SPONSOR"
    ]
    assert res["accelerated_burn_tranche_ids"] == ["TR-MGMT-NO-SPONSOR"]
    assert res["is_reserve_drawdown_compliant"] is False


def test_audit_executive_report_reserve_drawdown_zero_progress_and_invalid_inputs():
    """Valida quema > 15% con avance 0%, entradas inválidas y exportación en __all__."""
    import backend.services.project_export_service as _m
    from backend.services.project_export_service import (
        audit_executive_report_reserve_drawdown_burn_rate,
    )

    assert "audit_executive_report_reserve_drawdown_burn_rate" in _m.__all__
    res_zero_pct = audit_executive_report_reserve_drawdown_burn_rate(
        [
            {
                "tranche_id": "TR-EARLY-BURN",
                "reserve_type": "contingency",
                "initial_amount": 10000.0,
                "consumed_amount": 2000.0,
                "linked_risk_or_change_ids": ["RSK-01"],
            }
        ],
        project_percent_complete=0.0,
    )
    assert res_zero_pct["accelerated_burn_tranche_ids"] == ["TR-EARLY-BURN"]
    assert res_zero_pct["is_reserve_drawdown_compliant"] is False

    for bad in (None, "not-a-seq", b"bytes", [{"tranche_id": "  "}]):
        assert audit_executive_report_reserve_drawdown_burn_rate(bad) == {
            "total_tranches": 0,
            "total_initial_reserve": 0.0,
            "total_consumed_reserve": 0.0,
            "overall_drawdown_pct": 0.0,
            "invalid_reserve_type_tranche_ids": [],
            "overdrawn_or_negative_tranche_ids": [],
            "unlinked_drawdown_tranche_ids": [],
            "unapproved_management_reserve_tranche_ids": [],
            "accelerated_burn_tranche_ids": [],
            "is_reserve_drawdown_compliant": True,
        }


def test_audit_executive_report_post_implementation_handover_sla_compliant():
    """Paquetes de traspaso firmados, con benefits owner, runbook completo, hypercare >= 14d y 0 defectos críticos cumplen §4.7."""
    from backend.services.project_export_service import (
        ProjectExportService,
        audit_executive_report_post_implementation_handover_sla,
    )

    packages = [
        {
            "package_id": "HND-CORE-01",
            "receiving_operations_team": "SRE & Plataforma CCF",
            "runbook_and_sop_complete": True,
            "hypercare_support_days": 30,
            "open_sev1_sev2_defects": 0,
            "operations_acceptance_signed": True,
            "benefits_owner_assigned": True,
        },
        {
            "package_id": "HND-FIN-02",
            "receiving_operations_team": "Mesa Operativa Financiera",
            "runbook_and_sop_complete": True,
            "hypercare_support_days": 14,
            "open_sev1_sev2_defects": 0,
            "operations_acceptance_signed": True,
            "benefits_owner_assigned": True,
        },
    ]
    res = audit_executive_report_post_implementation_handover_sla(packages)
    assert res == {
        "total_packages": 2,
        "unsigned_or_unowned_handover_ids": [],
        "insufficient_runbook_or_hypercare_ids": [],
        "blocking_critical_defect_handover_ids": [],
        "is_handover_sla_compliant": True,
    }
    assert (
        ProjectExportService.audit_executive_report_post_implementation_handover_sla(
            packages
        )
        == res
    )


def test_audit_executive_report_handover_sla_unsigned_or_unowned_packages():
    """Detecta paquetes sin equipo receptor, sin firma de aceptación operativa o sin dueño de beneficios."""
    from backend.services.project_export_service import (
        audit_executive_report_post_implementation_handover_sla,
    )

    packages = [
        {
            "package_id": "HND-NO-TEAM",
            "receiving_operations_team": "   ",
            "runbook_and_sop_complete": True,
            "hypercare_support_days": 21,
            "open_sev1_sev2_defects": 0,
            "operations_acceptance_signed": True,
            "benefits_owner_assigned": True,
        },
        {
            "package_id": "HND-NO-SIGN",
            "receiving_operations_team": "Ops NOC",
            "runbook_and_sop_complete": True,
            "hypercare_support_days": 21,
            "open_sev1_sev2_defects": 0,
            "operations_acceptance_signed": False,
            "benefits_owner_assigned": True,
        },
        {
            "package_id": "HND-NO-BENEFITS-OWNER",
            "receiving_operations_team": "Ops NOC",
            "runbook_and_sop_complete": True,
            "hypercare_support_days": 21,
            "open_sev1_sev2_defects": 0,
            "operations_acceptance_signed": True,
            "benefits_owner_assigned": False,
        },
    ]
    res = audit_executive_report_post_implementation_handover_sla(packages)
    assert res["total_packages"] == 3
    assert res["unsigned_or_unowned_handover_ids"] == [
        "HND-NO-TEAM",
        "HND-NO-SIGN",
        "HND-NO-BENEFITS-OWNER",
    ]
    assert res["insufficient_runbook_or_hypercare_ids"] == []
    assert res["blocking_critical_defect_handover_ids"] == []
    assert res["is_handover_sla_compliant"] is False


def test_audit_executive_report_handover_sla_insufficient_hypercare_and_defects():
    """Detecta runbook incompleto, ventana hypercare < min_hypercare_days y defectos Sev1/Sev2 abiertos."""
    from backend.services.project_export_service import (
        audit_executive_report_post_implementation_handover_sla,
    )

    packages = [
        {
            "package_id": "HND-SHORT-HYPERCARE",
            "receiving_operations_team": "Infraestructura",
            "runbook_and_sop_complete": True,
            "hypercare_support_days": 7,
            "open_sev1_sev2_defects": 0,
            "operations_acceptance_signed": True,
            "benefits_owner_assigned": True,
        },
        {
            "package_id": "HND-NO-RUNBOOK-AND-SEV1",
            "receiving_operations_team": "Soporte N2",
            "runbook_and_sop_complete": False,
            "hypercare_support_days": 20,
            "open_sev1_sev2_defects": 2,
            "operations_acceptance_signed": True,
            "benefits_owner_assigned": True,
        },
    ]
    res = audit_executive_report_post_implementation_handover_sla(
        packages, min_hypercare_days=14
    )
    assert res["total_packages"] == 2
    assert res["unsigned_or_unowned_handover_ids"] == []
    assert res["insufficient_runbook_or_hypercare_ids"] == [
        "HND-SHORT-HYPERCARE",
        "HND-NO-RUNBOOK-AND-SEV1",
    ]
    assert res["blocking_critical_defect_handover_ids"] == [
        "HND-NO-RUNBOOK-AND-SEV1"
    ]
    assert res["is_handover_sla_compliant"] is False


def test_audit_executive_report_handover_sla_invalid_inputs_and_export():
    """Maneja entradas vacías o no secuencia y verifica exportación en __all__."""
    import backend.services.project_export_service as _m
    from backend.services.project_export_service import (
        audit_executive_report_post_implementation_handover_sla,
    )

    assert "audit_executive_report_post_implementation_handover_sla" in _m.__all__
    for bad in (None, "not-a-seq", b"bytes", [{"package_id": "  "}]):
        assert audit_executive_report_post_implementation_handover_sla(bad) == {
            "total_packages": 0,
            "unsigned_or_unowned_handover_ids": [],
            "insufficient_runbook_or_hypercare_ids": [],
            "blocking_critical_defect_handover_ids": [],
            "is_handover_sla_compliant": True,
        }


def test_audit_executive_report_team_burnout_and_turnover_risk_compliant():
    """Equipos con utilización sostenible, baja rotación y cross-training para roles SPOF cumplen §9.4 y §9.5."""
    from backend.services.project_export_service import (
        ProjectExportService,
        audit_executive_report_team_burnout_and_turnover_risk,
    )

    snapshots = [
        {
            "team_id": "TEAM-BACKEND",
            "avg_utilization_pct": 85.0,
            "consecutive_overtime_sprints": 1,
            "annualized_attrition_rate_pct": 8.0,
            "single_point_of_failure_roles_count": 1,
            "cross_training_plan_active": True,
        },
        {
            "team_id": "TEAM-QA",
            "avg_utilization_pct": 92.0,
            "consecutive_overtime_sprints": 0,
            "annualized_attrition_rate_pct": 5.0,
            "single_point_of_failure_roles_count": 0,
            "cross_training_plan_active": False,
        },
    ]
    res = audit_executive_report_team_burnout_and_turnover_risk(snapshots)
    assert res == {
        "total_teams": 2,
        "invalid_health_metric_team_ids": [],
        "chronic_burnout_risk_team_ids": [],
        "high_turnover_attrition_team_ids": [],
        "unmitigated_key_person_spof_team_ids": [],
        "is_team_sustainability_compliant": True,
    }
    assert (
        ProjectExportService.audit_executive_report_team_burnout_and_turnover_risk(
            snapshots
        )
        == res
    )


def test_audit_executive_report_team_burnout_and_turnover_chronic_overtime():
    """Detecta riesgo de burnout por utilización > max_sustainable_utilization_pct o >= 3 sprints en sobretiempo."""
    from backend.services.project_export_service import (
        audit_executive_report_team_burnout_and_turnover_risk,
    )

    snapshots = [
        {
            "team_id": "TEAM-OVERUTIL",
            "avg_utilization_pct": 112.0,
            "consecutive_overtime_sprints": 1,
            "annualized_attrition_rate_pct": 10.0,
        },
        {
            "team_id": "TEAM-3-SPRINTS-OT",
            "avg_utilization_pct": 95.0,
            "consecutive_overtime_sprints": 3,
            "annualized_attrition_rate_pct": 10.0,
        },
    ]
    res = audit_executive_report_team_burnout_and_turnover_risk(snapshots)
    assert res["total_teams"] == 2
    assert res["chronic_burnout_risk_team_ids"] == [
        "TEAM-OVERUTIL",
        "TEAM-3-SPRINTS-OT",
    ]
    assert res["is_team_sustainability_compliant"] is False


def test_audit_executive_report_team_burnout_and_turnover_attrition_and_spof():
    """Detecta rotación anualizada > max_attrition_rate_pct y roles SPOF sin plan de cross-training."""
    from backend.services.project_export_service import (
        audit_executive_report_team_burnout_and_turnover_risk,
    )

    snapshots = [
        {
            "team_id": "TEAM-HIGH-ATTRITION",
            "avg_utilization_pct": 88.0,
            "consecutive_overtime_sprints": 0,
            "annualized_attrition_rate_pct": 22.5,
            "single_point_of_failure_roles_count": 0,
        },
        {
            "team_id": "TEAM-UNMITIGATED-SPOF",
            "avg_utilization_pct": 80.0,
            "consecutive_overtime_sprints": 0,
            "annualized_attrition_rate_pct": 5.0,
            "single_point_of_failure_roles_count": 2,
            "cross_training_plan_active": False,
        },
    ]
    res = audit_executive_report_team_burnout_and_turnover_risk(
        snapshots, max_attrition_rate_pct=15.0
    )
    assert res["high_turnover_attrition_team_ids"] == ["TEAM-HIGH-ATTRITION"]
    assert res["unmitigated_key_person_spof_team_ids"] == [
        "TEAM-UNMITIGATED-SPOF"
    ]
    assert res["is_team_sustainability_compliant"] is False


def test_audit_executive_report_team_burnout_and_turnover_invalid_and_export():
    """Detecta métricas negativas, ignora entradas no secuencia y verifica exportación en __all__."""
    import backend.services.project_export_service as _m
    from backend.services.project_export_service import (
        audit_executive_report_team_burnout_and_turnover_risk,
    )

    assert "audit_executive_report_team_burnout_and_turnover_risk" in _m.__all__
    res = audit_executive_report_team_burnout_and_turnover_risk(
        [{"team_id": "TEAM-NEG", "avg_utilization_pct": -10.0}]
    )
    assert res["invalid_health_metric_team_ids"] == ["TEAM-NEG"]
    assert res["is_team_sustainability_compliant"] is False

    for bad in (None, "not-a-seq", b"bytes", [{"team_id": "  "}]):
        assert audit_executive_report_team_burnout_and_turnover_risk(bad) == {
            "total_teams": 0,
            "invalid_health_metric_team_ids": [],
            "chronic_burnout_risk_team_ids": [],
            "high_turnover_attrition_team_ids": [],
            "unmitigated_key_person_spof_team_ids": [],
            "is_team_sustainability_compliant": True,
        }


def test_audit_executive_report_monte_carlo_p50_p80_confidence_compliant():
    """Simulación Monte Carlo con >= 1000 iteraciones, matriz de correlación, P50<=P80<=P90 y cobertura P80 cumple §11.4."""
    from backend.services.project_export_service import (
        ProjectExportService,
        audit_executive_report_monte_carlo_p50_p80_confidence,
    )

    sims = [
        {
            "simulation_id": "SIM-MC-01",
            "iterations_count": 5000,
            "deterministic_base_cost": 400000.0,
            "p50_cost": 420000.0,
            "p80_cost": 455000.0,
            "p90_cost": 480000.0,
            "allocated_contingency_reserve": 60000.0,  # 400k + 60k = 460k >= 455k
            "correlation_matrix_applied": True,
        }
    ]
    res = audit_executive_report_monte_carlo_p50_p80_confidence(sims)
    assert res == {
        "total_simulations": 1,
        "invalid_simulation_metric_ids": [],
        "under_sampled_or_uncorrelated_ids": [],
        "non_monotonic_percentile_ids": [],
        "underfunded_p80_contingency_ids": [],
        "is_monte_carlo_governance_compliant": True,
    }
    assert (
        ProjectExportService.audit_executive_report_monte_carlo_p50_p80_confidence(
            sims
        )
        == res
    )


def test_audit_executive_report_monte_carlo_under_sampled_and_underfunded_p80():
    """Detecta simulaciones con < min_iterations, sin correlación o con reserva insuficiente para P80."""
    from backend.services.project_export_service import (
        audit_executive_report_monte_carlo_p50_p80_confidence,
    )

    sims = [
        {
            "simulation_id": "SIM-LOW-ITER",
            "iterations_count": 500,
            "deterministic_base_cost": 200000.0,
            "p50_cost": 210000.0,
            "p80_cost": 230000.0,
            "p90_cost": 250000.0,
            "allocated_contingency_reserve": 35000.0,
            "correlation_matrix_applied": True,
        },
        {
            "simulation_id": "SIM-UNDERFUNDED-P80",
            "iterations_count": 2000,
            "deterministic_base_cost": 200000.0,
            "p50_cost": 215000.0,
            "p80_cost": 240000.0,
            "p90_cost": 260000.0,
            "allocated_contingency_reserve": 20000.0,  # 220k < 240k
            "correlation_matrix_applied": True,
        },
    ]
    res = audit_executive_report_monte_carlo_p50_p80_confidence(
        sims, min_iterations=1000
    )
    assert res["under_sampled_or_uncorrelated_ids"] == ["SIM-LOW-ITER"]
    assert res["underfunded_p80_contingency_ids"] == ["SIM-UNDERFUNDED-P80"]
    assert res["is_monte_carlo_governance_compliant"] is False


def test_audit_executive_report_monte_carlo_non_monotonic_percentiles():
    """Detecta inversión de cuantiles cuando P50 > P80 o P80 > P90."""
    from backend.services.project_export_service import (
        audit_executive_report_monte_carlo_p50_p80_confidence,
    )

    sims = [
        {
            "simulation_id": "SIM-INVERTED-QUANTILES",
            "iterations_count": 2500,
            "deterministic_base_cost": 100000.0,
            "p50_cost": 130000.0,
            "p80_cost": 120000.0,
            "p90_cost": 140000.0,
            "allocated_contingency_reserve": 30000.0,
            "correlation_matrix_applied": True,
        }
    ]
    res = audit_executive_report_monte_carlo_p50_p80_confidence(sims)
    assert res["non_monotonic_percentile_ids"] == ["SIM-INVERTED-QUANTILES"]
    assert res["is_monte_carlo_governance_compliant"] is False


def test_audit_executive_report_monte_carlo_invalid_metrics_and_export():
    """Detecta costos <= 0, ignora entradas no secuencia y verifica exportación en __all__."""
    import backend.services.project_export_service as _m
    from backend.services.project_export_service import (
        audit_executive_report_monte_carlo_p50_p80_confidence,
    )

    assert (
        "audit_executive_report_monte_carlo_p50_p80_confidence" in _m.__all__
    )
    res = audit_executive_report_monte_carlo_p50_p80_confidence(
        [
            {
                "simulation_id": "SIM-ZERO-BASE",
                "deterministic_base_cost": 0.0,
                "p50_cost": 100.0,
                "p80_cost": 120.0,
                "p90_cost": 140.0,
            }
        ]
    )
    assert res["invalid_simulation_metric_ids"] == ["SIM-ZERO-BASE"]
    assert res["is_monte_carlo_governance_compliant"] is False

    for bad in (None, "not-a-seq", b"bytes", [{"simulation_id": "  "}]):
        assert audit_executive_report_monte_carlo_p50_p80_confidence(bad) == {
            "total_simulations": 0,
            "invalid_simulation_metric_ids": [],
            "under_sampled_or_uncorrelated_ids": [],
            "non_monotonic_percentile_ids": [],
            "underfunded_p80_contingency_ids": [],
            "is_monte_carlo_governance_compliant": True,
        }


def test_audit_executive_report_vendor_sla_and_liquidated_damages_healthy():
    """Verifica estado HEALTHY cuando todos los contratos cumplen SLA, sin atrasos, sin disputas y lejos del tope LD."""
    from backend.services.project_export_service import (
        ProjectExportService,
        audit_executive_report_vendor_sla_and_liquidated_damages,
    )

    contracts = [
        {
            "contract_id": "VND-CLOUD-01",
            "contract_value": 100000.0,
            "sla_target_uptime_pct": 99.9,
            "actual_uptime_pct": 99.95,
            "late_deliverables_count": 0,
            "accrued_liquidated_damages": 1000.0,
            "ld_cap_pct": 10.0,
            "disputed_claims_amount": 0.0,
        },
        {
            "contract_id": "VND-DEV-02",
            "contract_value": 50000.0,
            "sla_target_uptime_pct": 99.5,
            "actual_uptime_pct": 99.8,
            "late_deliverables_count": 0,
            "accrued_liquidated_damages": 0.0,
            "ld_cap_pct": 10.0,
            "disputed_claims_amount": 0.0,
        },
    ]
    res = audit_executive_report_vendor_sla_and_liquidated_damages(
        contracts, max_ld_cap_utilization_pct=80.0
    )
    assert res == {
        "total_contracts": 2,
        "compliant_contracts_count": 2,
        "sla_breached_contracts_count": 0,
        "late_deliverables_contracts_count": 0,
        "near_or_at_ld_cap_count": 0,
        "total_accrued_liquidated_damages": 1000.0,
        "total_disputed_claims_amount": 0.0,
        "vendor_sla_governance_status": "HEALTHY",
        "findings": [],
    }
    assert (
        ProjectExportService.audit_executive_report_vendor_sla_and_liquidated_damages(
            contracts
        )
        == res
    )


def test_audit_executive_report_vendor_sla_and_liquidated_damages_at_risk():
    """Verifica estado AT_RISK cuando existe un único tipo de desviación (ej. SLA incumplido o reclamo en disputa) sin saturar LD."""
    from backend.services.project_export_service import (
        audit_executive_report_vendor_sla_and_liquidated_damages,
    )

    res = audit_executive_report_vendor_sla_and_liquidated_damages(
        [
            {
                "contract_id": "VND-SLA-MISS",
                "contract_value": 200000.0,
                "sla_target_uptime_pct": 99.9,
                "actual_uptime_pct": 99.2,
                "late_deliverables_count": 0,
                "accrued_liquidated_damages": 5000.0,
                "ld_cap_pct": 10.0,
                "disputed_claims_amount": 2500.0,
            }
        ],
        max_ld_cap_utilization_pct=80.0,
    )
    assert res["total_contracts"] == 1
    assert res["compliant_contracts_count"] == 0
    assert res["sla_breached_contracts_count"] == 1
    assert res["late_deliverables_contracts_count"] == 0
    assert res["near_or_at_ld_cap_count"] == 0
    assert res["total_accrued_liquidated_damages"] == 5000.0
    assert res["total_disputed_claims_amount"] == 2500.0
    assert res["vendor_sla_governance_status"] == "AT_RISK"
    assert len(res["findings"]) == 1
    assert res["findings"][0]["contract_id"] == "VND-SLA-MISS"
    assert res["findings"][0]["ld_cap_utilization_pct"] == 25.0


def test_audit_executive_report_vendor_sla_and_liquidated_damages_critical_ld_cap():
    """Verifica estado CRITICAL cuando el consumo del tope de daños liquidados alcanza o supera el umbral máximo."""
    from backend.services.project_export_service import (
        audit_executive_report_vendor_sla_and_liquidated_damages,
    )

    res = audit_executive_report_vendor_sla_and_liquidated_damages(
        [
            {
                "contract_id": "VND-LD-SATURATED",
                "contract_value": 100000.0,
                "sla_target_uptime_pct": 99.5,
                "actual_uptime_pct": 99.6,
                "late_deliverables_count": 2,
                "accrued_liquidated_damages": 8500.0,
                "ld_cap_pct": 10.0,
                "disputed_claims_amount": 0.0,
            }
        ],
        max_ld_cap_utilization_pct=80.0,
    )
    assert res["near_or_at_ld_cap_count"] == 1
    assert res["late_deliverables_contracts_count"] == 1
    assert res["vendor_sla_governance_status"] == "CRITICAL"
    assert res["findings"][0]["ld_cap_utilization_pct"] == 85.0


def test_audit_executive_report_vendor_sla_and_liquidated_damages_empty_and_export():
    """Verifica manejo de entradas vacías o no válidas y exportación en __all__."""
    import backend.services.project_export_service as _m
    from backend.services.project_export_service import (
        audit_executive_report_vendor_sla_and_liquidated_damages,
    )

    assert "audit_executive_report_vendor_sla_and_liquidated_damages" in _m.__all__
    for bad in ([], None, "invalid"):
        assert audit_executive_report_vendor_sla_and_liquidated_damages(bad) == {
            "total_contracts": 0,
            "compliant_contracts_count": 0,
            "sla_breached_contracts_count": 0,
            "late_deliverables_contracts_count": 0,
            "near_or_at_ld_cap_count": 0,
            "total_accrued_liquidated_damages": 0.0,
            "total_disputed_claims_amount": 0.0,
            "vendor_sla_governance_status": "HEALTHY",
            "findings": [],
        }


def test_audit_executive_report_stakeholder_escalation_and_briefing_cadence_healthy():
    """Verifica estado HEALTHY cuando escalamientos están en SLA con plan y notificación a sponsor y briefings al día."""
    from backend.services.project_export_service import (
        ProjectExportService,
        audit_executive_report_stakeholder_escalation_and_briefing_cadence,
    )

    records = [
        {
            "stakeholder_id": "STK-EXEC-01",
            "influence_level": "HIGH",
            "open_escalations_count": 1,
            "oldest_open_escalation_days": 3,
            "days_since_last_executive_briefing": 7,
            "action_plan_documented": True,
            "sponsor_notified": True,
        },
        {
            "stakeholder_id": "STK-OPS-02",
            "influence_level": "MEDIUM",
            "open_escalations_count": 0,
            "oldest_open_escalation_days": 0,
            "days_since_last_executive_briefing": 10,
            "action_plan_documented": False,
            "sponsor_notified": False,
        },
    ]
    res = audit_executive_report_stakeholder_escalation_and_briefing_cadence(
        records, max_open_escalation_days=7, max_briefing_gap_days=14
    )
    assert res == {
        "total_stakeholders_evaluated": 2,
        "compliant_stakeholders_count": 2,
        "overdue_escalations_stakeholders_count": 0,
        "unmitigated_escalations_count": 0,
        "stale_briefing_stakeholders_count": 0,
        "total_open_escalations": 1,
        "escalation_governance_status": "HEALTHY",
        "findings": [],
    }
    assert (
        ProjectExportService.audit_executive_report_stakeholder_escalation_and_briefing_cadence(
            records
        )
        == res
    )


def test_audit_executive_report_stakeholder_escalation_and_briefing_cadence_at_risk():
    """Verifica estado AT_RISK cuando no hay escalamientos vencidos ni sin plan pero sí atraso en briefing ejecutivo."""
    from backend.services.project_export_service import (
        audit_executive_report_stakeholder_escalation_and_briefing_cadence,
    )

    res = audit_executive_report_stakeholder_escalation_and_briefing_cadence(
        [
            {
                "stakeholder_id": "STK-LATE-BRIEF",
                "influence_level": "HIGH",
                "open_escalations_count": 0,
                "oldest_open_escalation_days": 0,
                "days_since_last_executive_briefing": 21,
                "action_plan_documented": False,
                "sponsor_notified": False,
            }
        ],
        max_open_escalation_days=7,
        max_briefing_gap_days=14,
    )
    assert res["stale_briefing_stakeholders_count"] == 1
    assert res["compliant_stakeholders_count"] == 0
    assert res["escalation_governance_status"] == "AT_RISK"
    assert len(res["findings"]) == 1
    assert res["findings"][0]["stakeholder_id"] == "STK-LATE-BRIEF"


def test_audit_executive_report_stakeholder_escalation_and_briefing_cadence_critical():
    """Verifica estado CRITICAL cuando existen escalamientos vencidos o interesados HIGH sin sponsor notificado."""
    from backend.services.project_export_service import (
        audit_executive_report_stakeholder_escalation_and_briefing_cadence,
    )

    res = audit_executive_report_stakeholder_escalation_and_briefing_cadence(
        [
            {
                "stakeholder_id": "STK-OVERDUE-UNMIT",
                "influence_level": "high",
                "open_escalations_count": 2,
                "oldest_open_escalation_days": 12,
                "days_since_last_executive_briefing": 5,
                "action_plan_documented": True,
                "sponsor_notified": False,
            }
        ],
        max_open_escalation_days=7,
        max_briefing_gap_days=14,
    )
    assert res["overdue_escalations_stakeholders_count"] == 1
    assert res["unmitigated_escalations_count"] == 1
    assert res["total_open_escalations"] == 2
    assert res["escalation_governance_status"] == "CRITICAL"


def test_audit_executive_report_stakeholder_escalation_and_briefing_cadence_empty_and_export():
    """Verifica manejo de entradas vacías o no válidas y exportación en __all__."""
    import backend.services.project_export_service as _m
    from backend.services.project_export_service import (
        audit_executive_report_stakeholder_escalation_and_briefing_cadence,
    )

    assert (
        "audit_executive_report_stakeholder_escalation_and_briefing_cadence"
        in _m.__all__
    )
    for bad in ([], None, "invalid"):
        assert (
            audit_executive_report_stakeholder_escalation_and_briefing_cadence(bad)
            == {
                "total_stakeholders_evaluated": 0,
                "compliant_stakeholders_count": 0,
                "overdue_escalations_stakeholders_count": 0,
                "unmitigated_escalations_count": 0,
                "stale_briefing_stakeholders_count": 0,
                "total_open_escalations": 0,
                "escalation_governance_status": "HEALTHY",
                "findings": [],
            }
        )




def test_audit_esg_compliance_healthy():
    """Controles sin breach y con permisos vigentes."""
    from backend.services.project_export_service import (
        audit_executive_report_esg_sustainability_and_regulatory_compliance,
    )

    res = audit_executive_report_esg_sustainability_and_regulatory_compliance(
        [
            {"control_id": "C-1", "status": "COMPLIANT", "days_until_permit_expiry": 200,
             "non_compliance_fine_exposure": 0.0, "corrective_action_assigned": False,
             "regulatory_authority_notified": False},
            {"control_id": "C-2", "status": "active", "days_until_permit_expiry": None,
             "non_compliance_fine_exposure": 0.0, "corrective_action_assigned": False,
             "regulatory_authority_notified": False},
        ]
    )
    assert res == {
        "total_controls": 2,
        "compliant_controls_count": 2,
        "breached_controls_count": 0,
        "expiring_permits_count": 0,
        "unmitigated_breaches_count": 0,
        "total_fine_exposure_amount": 0.0,
        "regulatory_governance_status": "HEALTHY",
        "findings": [],
    }


def test_audit_esg_compliance_breached_critical():
    """BREACHED/REVOKED (case-insensitive) sin accion correctiva ni notificacion -> CRITICAL."""
    from backend.services.project_export_service import (
        audit_executive_report_esg_sustainability_and_regulatory_compliance,
    )

    res = audit_executive_report_esg_sustainability_and_regulatory_compliance(
        [
            {"control_id": "C-3", "status": "breached", "days_until_permit_expiry": 500,
             "non_compliance_fine_exposure": 250000.0, "corrective_action_assigned": False,
             "regulatory_authority_notified": False},
            {"control_id": "C-4", "status": "REVOKED", "days_until_permit_expiry": None,
             "non_compliance_fine_exposure": 0.0, "corrective_action_assigned": False,
             "regulatory_authority_notified": False},
        ]
    )
    assert res["breached_controls_count"] == 2
    # Spec: falta de accion correctiva basta para unmitigated (independiente de la multa).
    assert res["unmitigated_breaches_count"] == 2
    assert res["total_fine_exposure_amount"] == 250000.0
    assert res["regulatory_governance_status"] == "CRITICAL"
    assert res["findings"][0]["issues"] == [
        "REGULATORY_BREACH (BREACHED)",
        "CORRECTIVE_ACTION_UNASSIGNED",
        "AUTHORITY_NOT_NOTIFIED",
    ]
    assert res["findings"][1]["issues"] == [
        "REGULATORY_BREACH (REVOKED)",
        "CORRECTIVE_ACTION_UNASSIGNED",
    ]

    # Breach mitigado (accion + notificado con multa) sigue siendo breached -> CRITICAL.
    mitigated = audit_executive_report_esg_sustainability_and_regulatory_compliance(
        [
            {"control_id": "C-5", "status": "non_compliant", "days_until_permit_expiry": 400,
             "non_compliance_fine_exposure": 5000.0, "corrective_action_assigned": True,
             "regulatory_authority_notified": True},
        ]
    )
    assert mitigated["breached_controls_count"] == 1
    assert mitigated["unmitigated_breaches_count"] == 0
    assert mitigated["regulatory_governance_status"] == "CRITICAL"
    assert mitigated["total_fine_exposure_amount"] == 5000.0

    # Multa 0.0 no exige notificacion cuando hay accion correctiva.
    zero = audit_executive_report_esg_sustainability_and_regulatory_compliance(
        [
            {"control_id": "C-6", "status": "BREACHED", "days_until_permit_expiry": 400,
             "non_compliance_fine_exposure": 0.0, "corrective_action_assigned": True,
             "regulatory_authority_notified": False},
        ]
    )
    assert zero["unmitigated_breaches_count"] == 0


def test_audit_esg_compliance_expiring_permits_at_risk():
    """Permiso proximo a vencer o vencido (<= SLA, borde 30 incluido, negativo tambien) -> AT_RISK."""
    from backend.services.project_export_service import (
        audit_executive_report_esg_sustainability_and_regulatory_compliance,
    )

    res = audit_executive_report_esg_sustainability_and_regulatory_compliance(
        [
            {"control_id": "C-7", "status": "COMPLIANT", "days_until_permit_expiry": 31,
             "non_compliance_fine_exposure": 0.0, "corrective_action_assigned": False,
             "regulatory_authority_notified": False},
            {"control_id": "C-8", "status": "COMPLIANT", "days_until_permit_expiry": 30,
             "non_compliance_fine_exposure": 0.0, "corrective_action_assigned": False,
             "regulatory_authority_notified": False},
            {"control_id": "C-9", "status": "COMPLIANT", "days_until_permit_expiry": -5,
             "non_compliance_fine_exposure": 0.0, "corrective_action_assigned": False,
             "regulatory_authority_notified": False},
        ]
    )
    assert res["expiring_permits_count"] == 2  # 30 y -5; 31 fuera del SLA
    assert res["compliant_controls_count"] == 1
    assert res["regulatory_governance_status"] == "AT_RISK"
    assert res["findings"][0]["issues"] == ["PERMIT_EXPIRY_WARNING (30<=30)"]

    # SLA custom: con max 15, 30 deja de contar.
    custom = audit_executive_report_esg_sustainability_and_regulatory_compliance(
        [
            {"control_id": "C-10", "status": "COMPLIANT", "days_until_permit_expiry": 16,
             "non_compliance_fine_exposure": 0.0, "corrective_action_assigned": False,
             "regulatory_authority_notified": False},
        ],
        max_permit_expiry_warning_days=15,
    )
    assert custom["expiring_permits_count"] == 0
    assert custom["regulatory_governance_status"] == "HEALTHY"


def test_audit_esg_compliance_fine_exposure_and_empty():
    """Suma de exposicion a multas con coerciones, entrada vacia/None y proxy + __all__."""
    from backend.services.project_export_service import (
        ProjectExportService,
        audit_executive_report_esg_sustainability_and_regulatory_compliance,
    )
    import backend.services.project_export_service as mod

    sums = audit_executive_report_esg_sustainability_and_regulatory_compliance(
        [
            {"control_id": "S1", "status": "COMPLIANT", "days_until_permit_expiry": None,
             "non_compliance_fine_exposure": 123.456, "corrective_action_assigned": False,
             "regulatory_authority_notified": False},
            {"control_id": "S2", "status": "COMPLIANT", "days_until_permit_expiry": None,
             "non_compliance_fine_exposure": None, "corrective_action_assigned": False,
             "regulatory_authority_notified": False},
            {"control_id": "S3", "status": "COMPLIANT", "days_until_permit_expiry": None,
             "non_compliance_fine_exposure": "oops", "corrective_action_assigned": False,
             "regulatory_authority_notified": False},
        ]
    )
    # None y no-numericos se tratan como 0.0 en la suma.
    assert sums["total_fine_exposure_amount"] == 123.46
    assert sums["regulatory_governance_status"] == "HEALTHY"

    for payload in ([], None, 42):
        empty = audit_executive_report_esg_sustainability_and_regulatory_compliance(payload)
        assert empty["total_controls"] == 0
        assert empty["total_fine_exposure_amount"] == 0.0
        assert empty["regulatory_governance_status"] == "HEALTHY"
        assert empty["findings"] == []

    sample = [{"control_id": "SM", "status": "COMPLIANT", "days_until_permit_expiry": None,
               "non_compliance_fine_exposure": 0.0, "corrective_action_assigned": False,
               "regulatory_authority_notified": False}]
    assert (
        ProjectExportService.audit_executive_report_esg_sustainability_and_regulatory_compliance(sample)
        == audit_executive_report_esg_sustainability_and_regulatory_compliance(sample)
    )
    assert "audit_executive_report_esg_sustainability_and_regulatory_compliance" in mod.__all__


def test_audit_executive_report_risk_burndown_and_residual_exposure_healthy():
    """Trayectoria de riesgo con reduccion neta positiva, cero acciones vencidas y reserva suficiente -> HEALTHY."""
    from backend.services.project_export_service import (
        ProjectExportService,
        audit_executive_report_risk_burndown_and_residual_exposure,
    )

    snapshots = [
        {
            "period_id": "P-01",
            "initial_emv_exposure": 40000.0,
            "closed_or_mitigated_emv": 15000.0,
            "newly_identified_emv": 5000.0,
            "overdue_mitigation_actions_count": 0,
        },
        {
            "period_id": "P-02",
            "initial_emv_exposure": 30000.0,
            "closed_or_mitigated_emv": 12000.0,
            "newly_identified_emv": 2000.0,
            "overdue_mitigation_actions_count": 0,
        },
    ]
    res = audit_executive_report_risk_burndown_and_residual_exposure(
        snapshots,
        current_contingency_reserve=25000.0,
        max_residual_to_reserve_ratio=1.0,
    )
    assert res == {
        "total_periods": 2,
        "compliant_periods_count": 2,
        "expanding_risk_periods_count": 0,
        "overdue_mitigation_periods_count": 0,
        "latest_residual_emv": 20000.0,
        "reserve_coverage_shortfall": 0.0,
        "is_reserve_underfunded": False,
        "risk_burndown_governance_status": "HEALTHY",
        "findings": [],
    }
    assert (
        ProjectExportService.audit_executive_report_risk_burndown_and_residual_exposure(
            snapshots, current_contingency_reserve=25000.0
        )
        == res
    )


def test_audit_executive_report_risk_burndown_and_residual_exposure_at_risk():
    """Detecta expansion neta de riesgo sin acciones vencidas y con reserva suficiente como AT_RISK."""
    from backend.services.project_export_service import (
        audit_executive_report_risk_burndown_and_residual_exposure,
    )

    res = audit_executive_report_risk_burndown_and_residual_exposure(
        [
            {
                "period_id": "P-EXPAND",
                "initial_emv_exposure": 20000.0,
                "closed_or_mitigated_emv": 3000.0,
                "newly_identified_emv": 8000.0,
                "overdue_mitigation_actions_count": 0,
            }
        ],
        current_contingency_reserve=30000.0,
        max_residual_to_reserve_ratio=1.0,
    )
    assert res["total_periods"] == 1
    assert res["compliant_periods_count"] == 0
    assert res["expanding_risk_periods_count"] == 1
    assert res["overdue_mitigation_periods_count"] == 0
    assert res["latest_residual_emv"] == 25000.0
    assert res["is_reserve_underfunded"] is False
    assert res["risk_burndown_governance_status"] == "AT_RISK"
    assert len(res["findings"]) == 1
    assert res["findings"][0]["period_id"] == "P-EXPAND"
    assert res["findings"][0]["ending_residual_emv"] == 25000.0


def test_audit_executive_report_risk_burndown_and_residual_exposure_critical():
    """Detecta reserva insuficiente frente a exposicion residual o combinacion de expansion + vencimiento como CRITICAL."""
    from backend.services.project_export_service import (
        audit_executive_report_risk_burndown_and_residual_exposure,
    )

    res = audit_executive_report_risk_burndown_and_residual_exposure(
        [
            {
                "period_id": "P-CRIT",
                "initial_emv_exposure": 50000.0,
                "closed_or_mitigated_emv": 5000.0,
                "newly_identified_emv": 10000.0,
                "overdue_mitigation_actions_count": 2,
            }
        ],
        current_contingency_reserve=40000.0,
        max_residual_to_reserve_ratio=1.0,
    )
    assert res["latest_residual_emv"] == 55000.0
    assert res["reserve_coverage_shortfall"] == 15000.0
    assert res["is_reserve_underfunded"] is True
    assert res["expanding_risk_periods_count"] == 1
    assert res["overdue_mitigation_periods_count"] == 1
    assert res["risk_burndown_governance_status"] == "CRITICAL"


def test_audit_executive_report_risk_burndown_and_residual_exposure_empty_and_export():
    """Maneja entradas vacias o invalidas devolviendo HEALTHY y verifica exportacion en __all__."""
    import backend.services.project_export_service as mod
    from backend.services.project_export_service import (
        audit_executive_report_risk_burndown_and_residual_exposure,
    )

    assert "audit_executive_report_risk_burndown_and_residual_exposure" in mod.__all__
    for payload in ([], None, "invalid"):
        empty = audit_executive_report_risk_burndown_and_residual_exposure(payload)  # type: ignore[arg-type]
        assert empty == {
            "total_periods": 0,
            "compliant_periods_count": 0,
            "expanding_risk_periods_count": 0,
            "overdue_mitigation_periods_count": 0,
            "latest_residual_emv": 0.0,
            "reserve_coverage_shortfall": 0.0,
            "is_reserve_underfunded": False,
            "risk_burndown_governance_status": "HEALTHY",
            "findings": [],
        }


def test_audit_executive_report_critical_path_float_and_convergence_healthy():
    """Red de caminos saludable con holgura positiva o negativa con plan de recuperación documentado."""
    from backend.services.project_export_service import (
        audit_executive_report_critical_path_float_and_convergence,
    )

    paths = [
        {
            "id": "CP-01",
            "baseline_float_days": 0.0,
            "remaining_float_days": 0.0,
            "merge_predecessors_count": 2,
            "recovery_plan_documented": True,
        },
        {
            "id": "PATH-02",
            "baseline_float_days": 20.0,
            "remaining_float_days": 12.0,
            "merge_predecessors_count": 2,
            "recovery_plan_documented": False,
        },
        {
            "id": "PATH-03",
            "baseline_float_days": 0.0,
            "remaining_float_days": -2.0,
            "merge_predecessors_count": 1,
            "recovery_plan_documented": True,
        },
    ]
    res = audit_executive_report_critical_path_float_and_convergence(paths)
    assert res["total_paths"] == 3
    assert res["compliant_paths"] == 3
    assert res["negative_float_without_recovery_ids"] == []
    assert res["near_critical_paths_ids"] == []
    assert res["excessive_float_burn_ids"] == []
    assert res["high_convergence_merge_bias_ids"] == []
    assert res["min_remaining_float_days"] == -2.0
    assert res["schedule_network_health"] == "healthy"
    assert res["is_compliant"] is True
    assert res["recommendations"] == []


def test_audit_executive_report_critical_path_float_and_convergence_critical_negative_float():
    """Detecta holgura negativa sin plan de recuperación documentado (schedule_network_health == 'critical')."""
    from backend.services.project_export_service import (
        audit_executive_report_critical_path_float_and_convergence,
    )

    paths = [
        {
            "path_id": "CP-NEG",
            "baseline_float_days": 0.0,
            "remaining_float_days": -4.5,
            "merge_predecessors_count": 2,
            "recovery_plan_documented": False,
        }
    ]
    res = audit_executive_report_critical_path_float_and_convergence(paths)
    assert res["total_paths"] == 1
    assert res["compliant_paths"] == 0
    assert res["negative_float_without_recovery_ids"] == ["CP-NEG"]
    assert res["min_remaining_float_days"] == -4.5
    assert res["schedule_network_health"] == "critical"
    assert res["is_compliant"] is False
    assert len(res["recommendations"]) >= 1


def test_audit_executive_report_critical_path_float_and_convergence_at_risk_burn_and_merge_bias():
    """Detecta consumo excesivo de holgura, caminos cuasi-críticos y sesgo de convergencia en hitos de unión (at_risk)."""
    from backend.services.project_export_service import (
        audit_executive_report_critical_path_float_and_convergence,
    )

    paths = [
        {
            "path_id": "PATH-NEAR-MERGE",
            "baseline_float_days": 20.0,
            "remaining_float_days": 2.0,
            "merge_predecessors_count": 5,
            "recovery_plan_documented": False,
        }
    ]
    res = audit_executive_report_critical_path_float_and_convergence(
        paths,
        near_critical_float_days=5.0,
        max_float_burn_rate_pct=80.0,
        max_merge_point_predecessors=3,
    )
    assert res["total_paths"] == 1
    assert res["compliant_paths"] == 0
    assert res["near_critical_paths_ids"] == ["PATH-NEAR-MERGE"]
    assert res["excessive_float_burn_ids"] == ["PATH-NEAR-MERGE"]
    assert res["high_convergence_merge_bias_ids"] == ["PATH-NEAR-MERGE"]
    assert res["negative_float_without_recovery_ids"] == []
    assert res["schedule_network_health"] == "at_risk"
    assert res["is_compliant"] is False
    assert len(res["recommendations"]) >= 3


def test_audit_executive_report_critical_path_float_and_convergence_empty_and_service_binding():
    """Manejo defensivo de entradas vacías/no-secuencia y exposición en ProjectExportService y __all__."""
    import backend.services.project_export_service as mod
    from backend.services.project_export_service import (
        ProjectExportService,
        audit_executive_report_critical_path_float_and_convergence,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = audit_executive_report_critical_path_float_and_convergence(payload)  # type: ignore[arg-type]
        assert empty["total_paths"] == 0
        assert empty["compliant_paths"] == 0
        assert empty["min_remaining_float_days"] == 0.0
        assert empty["schedule_network_health"] == "healthy"
        assert empty["is_compliant"] is True
        assert empty["recommendations"] == []

    sample = [
        {
            "id": "P-100",
            "baseline_float_days": 10.0,
            "remaining_float_days": 8.0,
            "merge_predecessors_count": 1,
        }
    ]
    assert (
        ProjectExportService.audit_executive_report_critical_path_float_and_convergence(
            sample
        )
        == audit_executive_report_critical_path_float_and_convergence(sample)
    )
    assert "audit_executive_report_critical_path_float_and_convergence" in mod.__all__


def test_audit_executive_report_contract_claims_and_change_orders_healthy():
    """Reclamos cerrados o en negociación dentro de SLA con cláusula contractual y exposición controlada."""
    from backend.services.project_export_service import (
        audit_executive_report_contract_claims_and_change_orders,
    )

    claims = [
        {
            "id": "CLM-01",
            "status": "settled",
            "contract_base_value": 100000.0,
            "disputed_amount": 5000.0,
            "days_unresolved": 60,
            "adr_attempted": True,
            "contract_clause_referenced": True,
        },
        {
            "id": "CLM-02",
            "status": "contested",
            "contract_base_value": 200000.0,
            "disputed_amount": 10000.0,
            "days_unresolved": 20,
            "adr_attempted": True,
            "contract_clause_referenced": True,
        },
    ]
    res = audit_executive_report_contract_claims_and_change_orders(claims)
    assert res["total_claims"] == 2
    assert res["compliant_claims"] == 2
    assert res["total_disputed_amount"] == 10000.0
    assert res["unsubstantiated_claim_ids"] == []
    assert res["overdue_unresolved_claim_ids"] == []
    assert res["excessive_disputed_exposure_ids"] == []
    assert res["premature_litigation_without_adr_ids"] == []
    assert res["claims_governance_health"] == "healthy"
    assert res["is_compliant"] is True
    assert res["recommendations"] == []


def test_audit_executive_report_contract_claims_and_change_orders_at_risk_unsubstantiated_and_overdue():
    """Detecta unsubstantiated_claim_ids y overdue_unresolved_claim_ids (claims_governance_health == 'at_risk')."""
    from backend.services.project_export_service import (
        audit_executive_report_contract_claims_and_change_orders,
    )

    claims = [
        {
            "claim_id": "CLM-10",
            "status": "open",
            "contract_base_value": 100000.0,
            "disputed_amount": 3000.0,
            "days_unresolved": 15,
            "adr_attempted": False,
            "contract_clause_referenced": False,
        },
        {
            "claim_id": "CLM-11",
            "status": "contested",
            "contract_base_value": 100000.0,
            "disputed_amount": 4000.0,
            "days_unresolved": 60,
            "adr_attempted": True,
            "contract_clause_referenced": True,
        },
    ]
    res = audit_executive_report_contract_claims_and_change_orders(
        claims, max_claim_resolution_days=45
    )
    assert res["total_claims"] == 2
    assert res["compliant_claims"] == 0
    assert res["total_disputed_amount"] == 7000.0
    assert res["unsubstantiated_claim_ids"] == ["CLM-10"]
    assert res["overdue_unresolved_claim_ids"] == ["CLM-11"]
    assert res["excessive_disputed_exposure_ids"] == []
    assert res["premature_litigation_without_adr_ids"] == []
    assert res["claims_governance_health"] == "at_risk"
    assert res["is_compliant"] is False
    assert len(res["recommendations"]) >= 2


def test_audit_executive_report_contract_claims_and_change_orders_critical_exposure_and_litigation():
    """Detecta excessive_disputed_exposure_ids y premature_litigation_without_adr_ids (critical)."""
    from backend.services.project_export_service import (
        audit_executive_report_contract_claims_and_change_orders,
    )

    claims = [
        {
            "claim_id": "CLM-20",
            "status": "contested",
            "contract_base_value": 100000.0,
            "disputed_amount": 25000.0,
            "days_unresolved": 10,
            "adr_attempted": True,
            "contract_clause_referenced": True,
        },
        {
            "claim_id": "CLM-21",
            "status": "litigation",
            "contract_base_value": 100000.0,
            "disputed_amount": 5000.0,
            "days_unresolved": 20,
            "adr_attempted": False,
            "contract_clause_referenced": True,
        },
    ]
    res = audit_executive_report_contract_claims_and_change_orders(
        claims, max_disputed_to_contract_value_pct=10.0
    )
    assert res["total_claims"] == 2
    assert res["compliant_claims"] == 0
    assert res["total_disputed_amount"] == 30000.0
    assert res["excessive_disputed_exposure_ids"] == ["CLM-20"]
    assert res["premature_litigation_without_adr_ids"] == ["CLM-21"]
    assert res["claims_governance_health"] == "critical"
    assert res["is_compliant"] is False
    assert len(res["recommendations"]) >= 2


def test_audit_executive_report_contract_claims_and_change_orders_empty_and_service_binding():
    """Manejo defensivo de entradas vacías/no-secuencia y exposición en ProjectExportService y __all__."""
    import backend.services.project_export_service as mod
    from backend.services.project_export_service import (
        ProjectExportService,
        audit_executive_report_contract_claims_and_change_orders,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = audit_executive_report_contract_claims_and_change_orders(payload)  # type: ignore[arg-type]
        assert empty["total_claims"] == 0
        assert empty["compliant_claims"] == 0
        assert empty["total_disputed_amount"] == 0.0
        assert empty["claims_governance_health"] == "healthy"
        assert empty["is_compliant"] is True
        assert empty["recommendations"] == []

    sample = [
        {
            "id": "CLM-99",
            "status": "open",
            "contract_base_value": 50000.0,
            "disputed_amount": 1000.0,
            "days_unresolved": 5,
            "contract_clause_referenced": True,
        }
    ]
    assert (
        ProjectExportService.audit_executive_report_contract_claims_and_change_orders(
            sample
        )
        == audit_executive_report_contract_claims_and_change_orders(sample)
    )
    assert "audit_executive_report_contract_claims_and_change_orders" in mod.__all__





def test_executive_report_cybersecurity_sla_healthy_and_critical():
    """OPEN sin brecha -> compliant; exploit en la naturaleza o CVSS crítico vencido -> CRITICAL."""
    from backend.services.project_export_service import (
        audit_executive_report_cybersecurity_vulnerability_and_patch_sla,
    )

    healthy = audit_executive_report_cybersecurity_vulnerability_and_patch_sla(
        [
            {
                "vuln_id": "V-1",
                "cvss_score": 5.5,
                "status": "OPEN",
                "days_open": 10,
            }
        ]
    )
    assert healthy["total_vulnerabilities"] == 1
    assert healthy["compliant_vulnerabilities_count"] == 1
    assert healthy["critical_sla_breach_or_active_exploit_count"] == 0
    assert healthy["high_severity_sla_breach_count"] == 0
    assert healthy["unmitigated_accepted_risk_count"] == 0
    assert healthy["security_posture_status"] == "HEALTHY"
    assert healthy["violations"] == []

    critical = audit_executive_report_cybersecurity_vulnerability_and_patch_sla(
        [
            {
                "vuln_id": "V-2",
                "cvss_score": 9.5,
                "status": "open",
                "days_open": 8,
            },
            {
                "vuln_id": "V-3",
                "cvss_score": 4.0,
                "status": "OPEN",
                "days_open": 200,
                "exploited_in_wild": True,
            },
        ]
    )
    assert critical["critical_sla_breach_or_active_exploit_count"] == 2
    assert critical["security_posture_status"] == "CRITICAL"
    assert [v["vuln_id"] for v in critical["violations"]] == ["V-2", "V-3"]

    # Vencido crítico permite ambos caminos de la regla 1: explotado con CVSS alto -> un solo reason.
    overlap = audit_executive_report_cybersecurity_vulnerability_and_patch_sla(
        [
            {
                "vuln_id": "V-4",
                "cvss_score": 10.0,
                "status": "OPEN",
                "days_open": 20,
                "exploited_in_wild": True,
            }
        ]
    )
    assert overlap["violations"][0]["reasons"] == ["critical_sla_breach_or_active_exploit"]


def test_executive_report_cybersecurity_sla_high_breach_and_thresholds():
    """High CVSS vencido -> AT_RISK; umbrales custom desplazan la clasificación."""
    from backend.services.project_export_service import (
        audit_executive_report_cybersecurity_vulnerability_and_patch_sla,
    )

    at_risk = audit_executive_report_cybersecurity_vulnerability_and_patch_sla(
        [{"vuln_id": "V-5", "cvss_score": 8.0, "status": "OPEN", "days_open": 31}]
    )
    assert at_risk["high_severity_sla_breach_count"] == 1
    assert at_risk["security_posture_status"] == "AT_RISK"
    assert at_risk["violations"][0]["reasons"] == ["high_severity_sla_breach"]

    # Cuando el CVSS llega al umbral crítico en vez de high -> regla 1.
    climbs = audit_executive_report_cybersecurity_vulnerability_and_patch_sla(
        [{"vuln_id": "V-6", "cvss_score": 9.0, "status": "OPEN", "days_open": 31}]
    )
    assert climbs["high_severity_sla_breach_count"] == 0
    assert climbs["critical_sla_breach_or_active_exploit_count"] == 1
    assert climbs["security_posture_status"] == "CRITICAL"

    # High pero dentro del SLA alto -> sin hallazgos.
    within = audit_executive_report_cybersecurity_vulnerability_and_patch_sla(
        [{"vuln_id": "V-7", "cvss_score": 7.0, "status": "OPEN", "days_open": 30}]
    )
    assert within["security_posture_status"] == "HEALTHY"
    assert within["compliant_vulnerabilities_count"] == 1

    # Umbrales custom: high=5 y critical=9 con CVSS 6 y 40 días -> AT_RISK.
    custom = audit_executive_report_cybersecurity_vulnerability_and_patch_sla(
        [{"vuln_id": "V-8", "cvss_score": 6.0, "status": "OPEN", "days_open": 40}],
        high_cvss_threshold=5.0,
        max_high_open_days=30,
    )
    assert custom["high_severity_sla_breach_count"] == 1
    assert custom["security_posture_status"] == "AT_RISK"


def test_executive_report_cybersecurity_sla_accepted_risk_and_settled():
    """accepted_risk sin control compensatorio o CVSS crítico -> CRITICAL; patched/mitigated no hallazgos."""
    from backend.services.project_export_service import (
        audit_executive_report_cybersecurity_vulnerability_and_patch_sla,
    )

    bad_accept = audit_executive_report_cybersecurity_vulnerability_and_patch_sla(
        [
            {"vuln_id": "V-9", "status": "ACCEPTED_RISK"},
            {
                "vuln_id": "V-10",
                "cvss_score": 9.9,
                "status": "accepted_risk",
                "compensating_control_documented": True,
            },
        ]
    )
    assert bad_accept["unmitigated_accepted_risk_count"] == 2
    assert bad_accept["security_posture_status"] == "CRITICAL"
    assert [v["vuln_id"] for v in bad_accept["violations"]] == ["V-9", "V-10"]

    ok_accept = audit_executive_report_cybersecurity_vulnerability_and_patch_sla(
        [
            {
                "vuln_id": "V-11",
                "cvss_score": 8.0,
                "status": "ACCEPTED_RISK",
                "compensating_control_documented": True,
            }
        ]
    )
    assert ok_accept["security_posture_status"] == "HEALTHY"
    assert ok_accept["compliant_vulnerabilities_count"] == 1

    settled = audit_executive_report_cybersecurity_vulnerability_and_patch_sla(
        [
            {"vuln_id": "V-12", "cvss_score": 9.9, "status": "PATCHED", "days_open": 999},
            {"vuln_id": "V-13", "status": "Mitigated", "exploited_in_wild": True},
        ]
    )
    assert settled["security_posture_status"] == "HEALTHY"
    assert settled["compliant_vulnerabilities_count"] == 2
    assert settled["violations"] == []


def test_executive_report_cybersecurity_sla_neutral_and_binding():
    """No-lista/None -> vacío; no-dict ignorados; proxy estático y __all__."""
    import backend.services.project_export_service as mod
    from backend.services.project_export_service import (
        ProjectExportService,
        audit_executive_report_cybersecurity_vulnerability_and_patch_sla,
    )

    for payload in (None, "not-a-list", 42):
        empty = audit_executive_report_cybersecurity_vulnerability_and_patch_sla(payload)
        assert empty["total_vulnerabilities"] == 0
        assert empty["compliant_vulnerabilities_count"] == 0
        assert empty["security_posture_status"] == "HEALTHY"
        assert empty["violations"] == []

    mixed = audit_executive_report_cybersecurity_vulnerability_and_patch_sla(
        ["no-dict", 42, {"vuln_id": "V-14", "cvss_score": 2.0, "status": "OPEN"}]
    )
    assert mixed["total_vulnerabilities"] == 1
    assert mixed["compliant_vulnerabilities_count"] == 1

    sample = [{"vuln_id": "V-15", "cvss_score": 9.0, "status": "OPEN", "days_open": 8}]
    assert (
        ProjectExportService.audit_executive_report_cybersecurity_vulnerability_and_patch_sla(sample)
        == audit_executive_report_cybersecurity_vulnerability_and_patch_sla(sample)
    )
    assert "audit_executive_report_cybersecurity_vulnerability_and_patch_sla" in mod.__all__


def test_audit_executive_report_capex_opex_capitalization_compliance_healthy():
    """Valida partidas CapEx elegibles (desarrollo/construcción, >=12m, asset ID, finanzas OK) y OpEx operativas."""
    from backend.services.project_export_service import (
        audit_executive_report_capex_opex_capitalization_compliance,
    )

    entries = [
        {
            "id": "CST-01",
            "classification": "capex",
            "project_stage": "application_development",
            "amount": 50000.0,
            "useful_life_months": 36,
            "asset_register_id": "FA-1001",
            "finance_approved": True,
        },
        {
            "id": "CST-02",
            "classification": "opex",
            "project_stage": "preliminary_discovery",
            "amount": 12000.0,
            "useful_life_months": 0,
            "asset_register_id": "",
            "finance_approved": True,
        },
        {
            "id": "CST-03",
            "classification": "opex",
            "project_stage": "training",
            "amount": 8000.0,
            "useful_life_months": 0,
            "asset_register_id": "",
            "finance_approved": True,
        },
    ]
    res = audit_executive_report_capex_opex_capitalization_compliance(entries)
    assert res["total_entries"] == 3
    assert res["compliant_entries"] == 3
    assert res["total_capex_amount"] == 50000.0
    assert res["total_opex_amount"] == 20000.0
    assert res["improper_capex_in_opex_stage_ids"] == []
    assert res["unqualified_capex_asset_ids"] == []
    assert res["missed_capitalization_opportunity_ids"] == []
    assert res["accounting_governance_health"] == "healthy"
    assert res["is_compliant"] is True
    assert res["recommendations"] == []


def test_audit_executive_report_capex_opex_capitalization_compliance_at_risk():
    """Detecta oportunidad de capitalización perdida en activo elegible registrado como OpEx ('at_risk')."""
    from backend.services.project_export_service import (
        audit_executive_report_capex_opex_capitalization_compliance,
    )

    entries = [
        {
            "entry_id": "CST-10",
            "classification": "opex",
            "project_stage": "hardware_acquisition",
            "amount": 35000.0,
            "useful_life_months": 48,
            "asset_register_id": "FA-2040",
            "finance_approved": True,
        }
    ]
    res = audit_executive_report_capex_opex_capitalization_compliance(entries)
    assert res["total_entries"] == 1
    assert res["compliant_entries"] == 0
    assert res["missed_capitalization_opportunity_ids"] == ["CST-10"]
    assert res["improper_capex_in_opex_stage_ids"] == []
    assert res["unqualified_capex_asset_ids"] == []
    assert res["accounting_governance_health"] == "at_risk"
    assert res["is_compliant"] is False
    assert len(res["recommendations"]) >= 1


def test_audit_executive_report_capex_opex_capitalization_compliance_critical():
    """Detecta CapEx impropio en etapa OpEx y CapEx sin vida útil mínima o aprobación financiera ('critical')."""
    from backend.services.project_export_service import (
        audit_executive_report_capex_opex_capitalization_compliance,
    )

    entries = [
        {
            "entry_id": "CST-20",
            "classification": "capex",
            "project_stage": "research",
            "amount": 18000.0,
            "useful_life_months": 24,
            "asset_register_id": "FA-3001",
            "finance_approved": True,
        },
        {
            "entry_id": "CST-21",
            "classification": "capex",
            "project_stage": "construction",
            "amount": 25000.0,
            "useful_life_months": 6,
            "asset_register_id": "",
            "finance_approved": False,
        },
    ]
    res = audit_executive_report_capex_opex_capitalization_compliance(entries)
    assert res["total_entries"] == 2
    assert res["compliant_entries"] == 0
    assert res["improper_capex_in_opex_stage_ids"] == ["CST-20"]
    assert res["unqualified_capex_asset_ids"] == ["CST-21"]
    assert res["accounting_governance_health"] == "critical"
    assert res["is_compliant"] is False
    assert len(res["recommendations"]) >= 2


def test_audit_executive_report_capex_opex_capitalization_compliance_empty_and_service_binding():
    """Manejo defensivo de entradas vacías/no-secuencia y exposición en ProjectExportService y __all__."""
    import backend.services.project_export_service as mod
    from backend.services.project_export_service import (
        ProjectExportService,
        audit_executive_report_capex_opex_capitalization_compliance,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = audit_executive_report_capex_opex_capitalization_compliance(payload)  # type: ignore[arg-type]
        assert empty["total_entries"] == 0
        assert empty["compliant_entries"] == 0
        assert empty["total_capex_amount"] == 0.0
        assert empty["total_opex_amount"] == 0.0
        assert empty["accounting_governance_health"] == "healthy"
        assert empty["is_compliant"] is True
        assert empty["recommendations"] == []

    sample = [
        {
            "id": "CST-99",
            "classification": "capex",
            "project_stage": "implementation",
            "amount": 10000.0,
            "useful_life_months": 24,
            "asset_register_id": "FA-999",
            "finance_approved": True,
        }
    ]
    assert (
        ProjectExportService.audit_executive_report_capex_opex_capitalization_compliance(
            sample
        )
        == audit_executive_report_capex_opex_capitalization_compliance(sample)
    )
    assert (
        "audit_executive_report_capex_opex_capitalization_compliance"
        in mod.__all__
    )


def test_audit_executive_report_key_personnel_bus_factor_and_succession_resilient():
    """Valida roles críticos con bus factor >= 2, sucesión documentada, cross-training >= 80% y rotación baja ('resilient')."""
    from backend.services.project_export_service import (
        audit_executive_report_key_personnel_bus_factor_and_succession,
    )

    roles = [
        {
            "role_id": "ROLE-01",
            "role_name": "Arquitecto Cloud Principal",
            "qualified_holders_count": 2,
            "has_documented_succession_plan": True,
            "cross_training_completion_pct": 90.0,
            "attrition_flight_risk": "low",
        },
        {
            "role_id": "ROLE-02",
            "role_name": "Líder DBA PostgreSQL",
            "qualified_holders_count": 3,
            "has_documented_succession_plan": True,
            "cross_training_completion_pct": 85.0,
            "attrition_flight_risk": "medium",
        },
    ]
    res = audit_executive_report_key_personnel_bus_factor_and_succession(
        roles,
        total_team_headcount=20,
        departures_last_12m=2,
    )
    assert res["total_critical_roles"] == 2
    assert res["spof_roles_count"] == 0
    assert res["spof_role_ids"] == []
    assert res["spof_without_succession_ids"] == []
    assert res["high_flight_risk_spof_ids"] == []
    assert res["under_trained_role_ids"] == []
    assert res["annualized_turnover_pct"] == 10.0
    assert res["turnover_breach"] is False
    assert res["continuity_status"] == "resilient"
    assert res["is_continuity_ready"] is True
    assert res["issues"] == []


def test_audit_executive_report_key_personnel_bus_factor_and_succession_critical():
    """Detecta SPOF sin sucesión o con riesgo de fuga alto y combinación de SPOF + brecha de rotación ('critical_bus_factor')."""
    from backend.services.project_export_service import (
        audit_executive_report_key_personnel_bus_factor_and_succession,
    )

    roles = [
        {
            "role_id": "ROLE-10",
            "role_name": "Especialista Seguridad Criptográfica",
            "qualified_holders_count": 1,
            "has_documented_succession_plan": False,
            "cross_training_completion_pct": 50.0,
            "attrition_flight_risk": "high",
        },
        {
            "role_id": "ROLE-11",
            "role_name": "Ingeniero DevOps Senior",
            "qualified_holders_count": 1,
            "has_documented_succession_plan": True,
            "cross_training_completion_pct": 90.0,
            "attrition_flight_risk": "low",
        },
    ]
    res = audit_executive_report_key_personnel_bus_factor_and_succession(
        roles,
        total_team_headcount=10,
        departures_last_12m=3,
    )
    assert res["total_critical_roles"] == 2
    assert res["spof_roles_count"] == 2
    assert res["spof_role_ids"] == ["ROLE-10", "ROLE-11"]
    assert res["spof_without_succession_ids"] == ["ROLE-10"]
    assert res["high_flight_risk_spof_ids"] == ["ROLE-10"]
    assert res["under_trained_role_ids"] == ["ROLE-10"]
    assert res["annualized_turnover_pct"] == 30.0
    assert res["turnover_breach"] is True
    assert res["continuity_status"] == "critical_bus_factor"
    assert res["is_continuity_ready"] is False
    assert len(res["issues"]) >= 4


def test_audit_executive_report_key_personnel_bus_factor_and_succession_at_risk():
    """Detecta roles con bajo cross-training o SPOF con plan de sucesión y bajo riesgo de fuga ('at_risk')."""
    from backend.services.project_export_service import (
        audit_executive_report_key_personnel_bus_factor_and_succession,
    )

    roles = [
        {
            "role_id": "ROLE-20",
            "role_name": "Analista Integración ERP",
            "qualified_holders_count": 1,
            "has_documented_succession_plan": True,
            "cross_training_completion_pct": 65.0,
            "attrition_flight_risk": "low",
        }
    ]
    res = audit_executive_report_key_personnel_bus_factor_and_succession(
        roles,
        max_single_point_of_failure_roles=0,
        total_team_headcount=10,
        departures_last_12m=1,
    )
    assert res["total_critical_roles"] == 1
    assert res["spof_roles_count"] == 1
    assert res["spof_role_ids"] == ["ROLE-20"]
    assert res["spof_without_succession_ids"] == []
    assert res["high_flight_risk_spof_ids"] == []
    assert res["under_trained_role_ids"] == ["ROLE-20"]
    assert res["turnover_breach"] is False
    assert res["continuity_status"] == "at_risk"
    assert res["is_continuity_ready"] is False
    assert len(res["issues"]) >= 2


def test_audit_executive_report_key_personnel_bus_factor_and_succession_empty_and_binding():
    """Verifica manejo de entradas vacías, brecha de rotación aislada y enlace en ProjectExportService y __all__."""
    import backend.services.project_export_service as mod
    from backend.services.project_export_service import (
        ProjectExportService,
        audit_executive_report_key_personnel_bus_factor_and_succession,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = audit_executive_report_key_personnel_bus_factor_and_succession(payload)  # type: ignore[arg-type]
        assert empty["total_critical_roles"] == 0
        assert empty["spof_roles_count"] == 0
        assert empty["continuity_status"] == "resilient"
        assert empty["is_continuity_ready"] is True
        assert empty["issues"] == []

    turnover_only = audit_executive_report_key_personnel_bus_factor_and_succession(
        [],
        total_team_headcount=10,
        departures_last_12m=4,
    )
    assert turnover_only["annualized_turnover_pct"] == 40.0
    assert turnover_only["turnover_breach"] is True
    assert turnover_only["continuity_status"] == "at_risk"
    assert turnover_only["is_continuity_ready"] is False

    sample = [
        {
            "role_id": "ROLE-99",
            "role_name": "Product Owner",
            "qualified_holders_count": 2,
            "has_documented_succession_plan": True,
            "cross_training_completion_pct": 95.0,
            "attrition_flight_risk": "low",
        }
    ]
    assert (
        ProjectExportService.audit_executive_report_key_personnel_bus_factor_and_succession(
            sample
        )
        == audit_executive_report_key_personnel_bus_factor_and_succession(sample)
    )
    assert (
        "audit_executive_report_key_personnel_bus_factor_and_succession"
        in mod.__all__
    )



def test_vendor_sla_credit_recovery_compliant_and_critical():
    """Vendor conforme -> COMPLIANT; breach crónico >= 3 meses -> CRITICAL_DEFAULT."""
    from backend.services.project_export_service import (
        audit_executive_report_vendor_sla_and_service_credit_recovery,
    )

    compliant = audit_executive_report_vendor_sla_and_service_credit_recovery(
        [
            {
                "vendor_id": "V-1",
                "measured_sla_pct": 99.5,
                "accrued_service_credits_usd": 100.0,
                "recovered_service_credits_usd": 95.0,
            }
        ]
    )
    assert compliant["total_vendor_contracts"] == 1
    assert compliant["sla_breach_vendor_ids"] == []
    assert compliant["chronic_breach_vendor_ids"] == []
    assert compliant["unrecovered_credit_vendor_ids"] == []
    assert compliant["total_unrecovered_credits_usd"] == 5.0
    assert compliant["vendor_governance_status"] == "COMPLIANT"
    assert compliant["is_vendor_sla_healthy"] is True

    chronic = audit_executive_report_vendor_sla_and_service_credit_recovery(
        [
            {
                "vendor_id": "V-2",
                "measured_sla_pct": 99.9,
                "chronic_consecutive_breach_months": 3,
            }
        ]
    )
    assert chronic["chronic_breach_vendor_ids"] == ["V-2"]
    assert chronic["vendor_governance_status"] == "CRITICAL_DEFAULT"
    assert chronic["is_vendor_sla_healthy"] is False

    # Límite exacto: 2 meses no es crónico.
    at_limit = audit_executive_report_vendor_sla_and_service_credit_recovery(
        [
            {
                "vendor_id": "V-3",
                "measured_sla_pct": 99.9,
                "chronic_consecutive_breach_months": 2,
            }
        ]
    )
    assert at_limit["chronic_breach_vendor_ids"] == []
    assert at_limit["vendor_governance_status"] == "COMPLIANT"


def test_vendor_sla_credit_recovery_breach_and_thresholds():
    """SLA bajo default/custom target -> breach; ratio de crédito > 10% -> unrecovered."""
    from backend.services.project_export_service import (
        audit_executive_report_vendor_sla_and_service_credit_recovery,
    )

    default_breach = audit_executive_report_vendor_sla_and_service_credit_recovery(
        [{"vendor_id": "V-4", "measured_sla_pct": 98.0}]
    )
    assert default_breach["sla_breach_vendor_ids"] == ["V-4"]
    assert default_breach["vendor_governance_status"] == "CREDITS_OR_SLA_AT_RISK"
    assert default_breach["is_vendor_sla_healthy"] is False

    custom_target = audit_executive_report_vendor_sla_and_service_credit_recovery(
        [{"vendor_id": "V-5", "measured_sla_pct": 99.5, "target_sla_pct": 99.9}]
    )
    assert custom_target["sla_breach_vendor_ids"] == ["V-5"]

    # Límite exacto: measured == target no es breach.
    at_limit = audit_executive_report_vendor_sla_and_service_credit_recovery(
        [{"vendor_id": "V-6", "measured_sla_pct": 99.0}]
    )
    assert at_limit["sla_breach_vendor_ids"] == []
    assert at_limit["vendor_governance_status"] == "COMPLIANT"

    credit = audit_executive_report_vendor_sla_and_service_credit_recovery(
        [
            {
                "vendor_id": "V-7",
                "measured_sla_pct": 99.9,
                "accrued_service_credits_usd": 1000.0,
                "recovered_service_credits_usd": 890.0,
            }
        ]
    )
    assert credit["unrecovered_credit_vendor_ids"] == ["V-7"]
    assert credit["total_unrecovered_credits_usd"] == 110.0
    assert credit["vendor_governance_status"] == "CREDITS_OR_SLA_AT_RISK"

    # Límite exacto: ratio 10% no excede.
    ratio_at_limit = audit_executive_report_vendor_sla_and_service_credit_recovery(
        [
            {
                "vendor_id": "V-8",
                "measured_sla_pct": 99.9,
                "accrued_service_credits_usd": 100.0,
                "recovered_service_credits_usd": 90.0,
            }
        ]
    )
    assert ratio_at_limit["unrecovered_credit_vendor_ids"] == []
    assert ratio_at_limit["vendor_governance_status"] == "COMPLIANT"

    # Umbral custom: ratio 10% con max 5% -> excede.
    strict = audit_executive_report_vendor_sla_and_service_credit_recovery(
        [
            {
                "vendor_id": "V-9",
                "measured_sla_pct": 99.9,
                "accrued_service_credits_usd": 100.0,
                "recovered_service_credits_usd": 90.0,
            }
        ],
        max_unrecovered_credit_ratio_pct=5.0,
    )
    assert strict["unrecovered_credit_vendor_ids"] == ["V-9"]
    assert strict["vendor_governance_status"] == "CREDITS_OR_SLA_AT_RISK"


def test_vendor_sla_credit_recovery_totals_and_neutral():
    """Suma max(0.0, accrued - recovered) con clamps; no-lista/None -> vacío COMPLIANT."""
    from backend.services.project_export_service import (
        audit_executive_report_vendor_sla_and_service_credit_recovery,
    )

    mixed = audit_executive_report_vendor_sla_and_service_credit_recovery(
        [
            {
                "vendor_id": "V-10",
                "measured_sla_pct": 99.9,
                "accrued_service_credits_usd": 50.0,
                "recovered_service_credits_usd": 80.0,
            },
            {
                "vendor_id": "V-11",
                "measured_sla_pct": 99.9,
                "accrued_service_credits_usd": 200.0,
                "recovered_service_credits_usd": 0.0,
            },
        ],
        max_unrecovered_credit_ratio_pct=100.0,
    )
    assert mixed["total_unrecovered_credits_usd"] == 200.0
    assert mixed["total_vendor_contracts"] == 2
    assert mixed["vendor_governance_status"] == "COMPLIANT"

    # Redondeo a 2 decimales.
    rounded = audit_executive_report_vendor_sla_and_service_credit_recovery(
        [
            {
                "vendor_id": "V-12",
                "measured_sla_pct": 99.9,
                "accrued_service_credits_usd": 100.0,
                "recovered_service_credits_usd": 33.333,
            }
        ],
        max_unrecovered_credit_ratio_pct=100.0,
    )
    assert rounded["total_unrecovered_credits_usd"] == 66.67

    for payload in (None, "not-a-list", 42):
        empty = audit_executive_report_vendor_sla_and_service_credit_recovery(payload)
        assert empty["total_vendor_contracts"] == 0
        assert empty["sla_breach_vendor_ids"] == []
        assert empty["chronic_breach_vendor_ids"] == []
        assert empty["unrecovered_credit_vendor_ids"] == []
        assert empty["total_unrecovered_credits_usd"] == 0.0
        assert empty["vendor_governance_status"] == "COMPLIANT"
        assert empty["is_vendor_sla_healthy"] is True

    mixed_entries = audit_executive_report_vendor_sla_and_service_credit_recovery(
        [
            "no-dict",
            42,
            {
                "vendor_id": "V-13",
                "measured_sla_pct": 99.9,
            },
        ]
    )
    assert mixed_entries["total_vendor_contracts"] == 1
    assert mixed_entries["vendor_governance_status"] == "COMPLIANT"


def test_vendor_sla_credit_recovery_precedence_and_binding():
    """CRITICAL_DEFAULT domina; proxy @staticmethod de ProjectExportService."""
    import backend.services.project_export_service as mod
    from backend.services.project_export_service import (
        ProjectExportService,
        audit_executive_report_vendor_sla_and_service_credit_recovery,
    )

    dominates = audit_executive_report_vendor_sla_and_service_credit_recovery(
        [
            {
                "vendor_id": "V-14",
                "measured_sla_pct": 90.0,
                "chronic_consecutive_breach_months": 5,
                "accrued_service_credits_usd": 500.0,
                "recovered_service_credits_usd": 0.0,
            }
        ]
    )
    assert dominates["sla_breach_vendor_ids"] == ["V-14"]
    assert dominates["chronic_breach_vendor_ids"] == ["V-14"]
    assert dominates["unrecovered_credit_vendor_ids"] == ["V-14"]
    assert dominates["vendor_governance_status"] == "CRITICAL_DEFAULT"

    sample = [{"vendor_id": "V-15", "measured_sla_pct": 90.0}]
    assert (
        ProjectExportService.audit_executive_report_vendor_sla_and_service_credit_recovery(sample)
        == audit_executive_report_vendor_sla_and_service_credit_recovery(sample)
    )
    assert "audit_executive_report_vendor_sla_and_service_credit_recovery" in mod.__all__


def test_audit_executive_report_supply_chain_lead_time_and_single_source_resilient():
    """Valida suministros en ruta crítica con >=2 proveedores calificados, lead-time dentro de tolerancia y buffer suficiente ('RESILIENT')."""
    from backend.services.project_export_service import (
        audit_executive_report_supply_chain_lead_time_and_single_source,
    )

    items = [
        {
            "item_id": "PRC-01",
            "baseline_lead_time_days": 30.0,
            "current_projected_lead_time_days": 33.0,
            "qualified_suppliers_count": 2,
            "is_on_critical_path": True,
            "buffer_days_available": 5.0,
        },
        {
            "item_id": "PRC-02",
            "baseline_lead_time_days": 15.0,
            "current_projected_lead_time_days": 15.0,
            "qualified_suppliers_count": 1,
            "is_on_critical_path": False,
            "buffer_days_available": 0.0,
        },
    ]
    res = audit_executive_report_supply_chain_lead_time_and_single_source(
        items
    )
    assert res["total_procurement_items"] == 2
    assert res["single_source_critical_ids"] == []
    assert res["lead_time_slip_ids"] == []
    assert res["buffer_exhausted_critical_ids"] == []
    assert res["supply_chain_status"] == "RESILIENT"
    assert res["is_supply_chain_resilient"] is True
    assert res["issues"] == []


def test_audit_executive_report_supply_chain_lead_time_and_single_source_critical():
    """Detecta proveedor único en ruta crítica y agotamiento de buffer por retraso de entrega ('CRITICAL_BOTTLENECK')."""
    from backend.services.project_export_service import (
        audit_executive_report_supply_chain_lead_time_and_single_source,
    )

    items = [
        {
            "item_id": "PRC-10",
            "baseline_lead_time_days": 20.0,
            "current_projected_lead_time_days": 28.0,
            "qualified_suppliers_count": 1,
            "is_on_critical_path": True,
            "buffer_days_available": 4.0,
        }
    ]
    res = audit_executive_report_supply_chain_lead_time_and_single_source(
        items
    )
    assert res["total_procurement_items"] == 1
    assert res["single_source_critical_ids"] == ["PRC-10"]
    assert res["lead_time_slip_ids"] == ["PRC-10"]
    assert res["buffer_exhausted_critical_ids"] == ["PRC-10"]
    assert res["supply_chain_status"] == "CRITICAL_BOTTLENECK"
    assert res["is_supply_chain_resilient"] is False
    assert len(res["issues"]) == 3


def test_audit_executive_report_supply_chain_lead_time_and_single_source_at_risk():
    """Detecta deslizamiento de lead-time (>20%) fuera de ruta crítica o con buffer suficiente y dual-source ('AT_RISK')."""
    from backend.services.project_export_service import (
        audit_executive_report_supply_chain_lead_time_and_single_source,
    )

    items = [
        {
            "item_id": "PRC-20",
            "baseline_lead_time_days": 20.0,
            "current_projected_lead_time_days": 26.0,
            "qualified_suppliers_count": 2,
            "is_on_critical_path": True,
            "buffer_days_available": 10.0,
        }
    ]
    res = audit_executive_report_supply_chain_lead_time_and_single_source(
        items
    )
    assert res["total_procurement_items"] == 1
    assert res["single_source_critical_ids"] == []
    assert res["buffer_exhausted_critical_ids"] == []
    assert res["lead_time_slip_ids"] == ["PRC-20"]
    assert res["supply_chain_status"] == "AT_RISK"
    assert res["is_supply_chain_resilient"] is False
    assert len(res["issues"]) == 1


def test_audit_executive_report_supply_chain_lead_time_and_single_source_empty_and_binding():
    """Verifica manejo defensivo de entradas vacías/no-secuencia y enlace en ProjectExportService y __all__."""
    import backend.services.project_export_service as mod
    from backend.services.project_export_service import (
        ProjectExportService,
        audit_executive_report_supply_chain_lead_time_and_single_source,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = audit_executive_report_supply_chain_lead_time_and_single_source(payload)  # type: ignore[arg-type]
        assert empty["total_procurement_items"] == 0
        assert empty["single_source_critical_ids"] == []
        assert empty["lead_time_slip_ids"] == []
        assert empty["buffer_exhausted_critical_ids"] == []
        assert empty["supply_chain_status"] == "RESILIENT"
        assert empty["is_supply_chain_resilient"] is True
        assert empty["issues"] == []

    sample = [
        {
            "item_id": "PRC-99",
            "baseline_lead_time_days": 10.0,
            "current_projected_lead_time_days": 10.0,
            "qualified_suppliers_count": 2,
            "is_on_critical_path": True,
            "buffer_days_available": 3.0,
        }
    ]
    assert (
        ProjectExportService.audit_executive_report_supply_chain_lead_time_and_single_source(
            sample
        )
        == audit_executive_report_supply_chain_lead_time_and_single_source(
            sample
        )
    )
    assert (
        "audit_executive_report_supply_chain_lead_time_and_single_source"
        in mod.__all__
    )


def test_audit_executive_report_stakeholder_sentiment_supportive():
    """Caso 1: NPS >= 10, sin detractores clave ni preocupaciones sin resolver -> SUPPORTIVE."""
    from backend.services.project_export_service import (
        audit_executive_report_stakeholder_sentiment_and_nps_drift,
    )

    surveys = [
        {
            "stakeholder_id": "STK-01",
            "nps_rating_0_to_10": 10.0,
            "is_high_influence_key_stakeholder": True,
            "previous_nps_rating_0_to_10": 9.0,
            "has_unresolved_concern": False,
        },
        {
            "stakeholder_id": "STK-02",
            "nps_rating_0_to_10": 9.0,
            "is_high_influence_key_stakeholder": False,
            "previous_nps_rating_0_to_10": 8.0,
            "has_unresolved_concern": False,
        },
        {
            "stakeholder_id": "STK-03",
            "nps_rating_0_to_10": 8.0,
            "is_high_influence_key_stakeholder": True,
            "previous_nps_rating_0_to_10": 8.0,
            "has_unresolved_concern": False,
        },
    ]
    res = audit_executive_report_stakeholder_sentiment_and_nps_drift(
        surveys, min_acceptable_nps_score=10.0, max_key_detractor_count=0
    )
    assert res["total_surveyed"] == 3
    assert res["net_promoter_score_nps"] == 66.67
    assert res["key_detractor_stakeholder_ids"] == []
    assert res["declining_sentiment_stakeholder_ids"] == []
    assert res["unaddressed_detractor_ids"] == []
    assert res["sentiment_health_status"] == "SUPPORTIVE"
    assert res["is_sentiment_healthy"] is True
    assert res["issues"] == []


def test_audit_executive_report_stakeholder_sentiment_erosion():
    """Caso 2: Caída >= 2 puntos en NPS o NPS global < mínimo sin detractor clave -> SENTIMENT_EROSION."""
    from backend.services.project_export_service import (
        audit_executive_report_stakeholder_sentiment_and_nps_drift,
    )

    surveys = [
        {
            "stakeholder_id": "STK-10",
            "nps_rating_0_to_10": 7.0,
            "is_high_influence_key_stakeholder": True,
            "previous_nps_rating_0_to_10": 9.5,  # caída 2.5 >= 2.0
            "has_unresolved_concern": False,
        },
        {
            "stakeholder_id": "STK-11",
            "nps_rating_0_to_10": 8.0,
            "is_high_influence_key_stakeholder": False,
            "previous_nps_rating_0_to_10": 8.0,
            "has_unresolved_concern": False,
        },
    ]
    res = audit_executive_report_stakeholder_sentiment_and_nps_drift(
        surveys, min_acceptable_nps_score=10.0, max_key_detractor_count=0
    )
    assert res["total_surveyed"] == 2
    assert res["net_promoter_score_nps"] == 0.0
    assert res["key_detractor_stakeholder_ids"] == []
    assert res["declining_sentiment_stakeholder_ids"] == ["STK-10"]
    assert res["unaddressed_detractor_ids"] == []
    assert res["sentiment_health_status"] == "SENTIMENT_EROSION"
    assert res["is_sentiment_healthy"] is False
    assert len(res["issues"]) >= 2


def test_audit_executive_report_stakeholder_sentiment_critical_resistance():
    """Caso 3: Detractor clave o detractor con preocupación sin resolver -> CRITICAL_RESISTANCE."""
    from backend.services.project_export_service import (
        audit_executive_report_stakeholder_sentiment_and_nps_drift,
    )

    surveys = [
        {
            "stakeholder_id": "STK-KEY-DET",
            "nps_rating_0_to_10": 5.0,
            "is_high_influence_key_stakeholder": True,
            "previous_nps_rating_0_to_10": 8.0,
            "has_unresolved_concern": True,
        },
        {
            "stakeholder_id": "STK-PROM",
            "nps_rating_0_to_10": 10.0,
            "is_high_influence_key_stakeholder": False,
            "previous_nps_rating_0_to_10": 10.0,
            "has_unresolved_concern": False,
        },
    ]
    res = audit_executive_report_stakeholder_sentiment_and_nps_drift(
        surveys, min_acceptable_nps_score=10.0, max_key_detractor_count=0
    )
    assert res["total_surveyed"] == 2
    assert res["net_promoter_score_nps"] == 0.0
    assert res["key_detractor_stakeholder_ids"] == ["STK-KEY-DET"]
    assert res["declining_sentiment_stakeholder_ids"] == ["STK-KEY-DET"]
    assert res["unaddressed_detractor_ids"] == ["STK-KEY-DET"]
    assert res["sentiment_health_status"] == "CRITICAL_RESISTANCE"
    assert res["is_sentiment_healthy"] is False
    assert len(res["issues"]) >= 2


def test_audit_executive_report_stakeholder_sentiment_empty_and_binding():
    """Caso 4: Entradas vacías/inválidas y binding en ProjectExportService + __all__."""
    import backend.services.project_export_service as mod
    from backend.services.project_export_service import (
        ProjectExportService,
        audit_executive_report_stakeholder_sentiment_and_nps_drift,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = audit_executive_report_stakeholder_sentiment_and_nps_drift(payload)  # type: ignore[arg-type]
        assert empty["total_surveyed"] == 0
        assert empty["net_promoter_score_nps"] == 0.0
        assert empty["key_detractor_stakeholder_ids"] == []
        assert empty["declining_sentiment_stakeholder_ids"] == []
        assert empty["unaddressed_detractor_ids"] == []
        assert empty["sentiment_health_status"] == "SUPPORTIVE"
        assert empty["is_sentiment_healthy"] is True
        assert empty["issues"] == []

    sample = [
        {
            "stakeholder_id": "STK-99",
            "nps_rating_0_to_10": 9.5,
            "is_high_influence_key_stakeholder": True,
            "previous_nps_rating_0_to_10": 9.0,
            "has_unresolved_concern": False,
        }
    ]
    assert (
        ProjectExportService.audit_executive_report_stakeholder_sentiment_and_nps_drift(
            sample
        )
        == audit_executive_report_stakeholder_sentiment_and_nps_drift(sample)
    )
    assert (
        "audit_executive_report_stakeholder_sentiment_and_nps_drift"
        in mod.__all__
    )


def test_audit_executive_report_regulatory_and_data_privacy_compliant():
    """Caso 1: Controles con DPIA firmado, estatutarios verificados y hallazgos en SLA -> COMPLIANT."""
    from backend.services.project_export_service import (
        audit_executive_report_regulatory_and_data_privacy_compliance,
    )

    controls = [
        {
            "control_id": "CTRL-PII-01",
            "processes_personal_data_pii": True,
            "dpia_completed_and_signed": True,
            "has_open_audit_finding": False,
            "finding_age_days": 0,
            "is_mandatory_statutory": True,
            "control_verified": True,
        },
        {
            "control_id": "CTRL-OPS-02",
            "processes_personal_data_pii": False,
            "dpia_completed_and_signed": False,
            "has_open_audit_finding": True,
            "finding_age_days": 15,
            "is_mandatory_statutory": False,
            "control_verified": True,
        },
    ]
    res = audit_executive_report_regulatory_and_data_privacy_compliance(
        controls, require_dpia_for_pii=True, max_finding_remediation_days=30
    )
    assert res["total_controls"] == 2
    assert res["missing_dpia_control_ids"] == []
    assert res["unverified_statutory_control_ids"] == []
    assert res["overdue_finding_control_ids"] == []
    assert res["regulatory_compliance_status"] == "COMPLIANT"
    assert res["is_regulatory_compliant"] is True
    assert res["issues"] == []


def test_audit_executive_report_regulatory_and_data_privacy_remediation_overdue():
    """Caso 2: DPIA y controles estatutarios cumplidos pero hallazgo de auditoría > 30d -> REMEDIATION_OVERDUE."""
    from backend.services.project_export_service import (
        audit_executive_report_regulatory_and_data_privacy_compliance,
    )

    controls = [
        {
            "control_id": "CTRL-FIND-01",
            "processes_personal_data_pii": False,
            "dpia_completed_and_signed": False,
            "has_open_audit_finding": True,
            "finding_age_days": 45,
            "is_mandatory_statutory": True,
            "control_verified": True,
        }
    ]
    res = audit_executive_report_regulatory_and_data_privacy_compliance(
        controls, require_dpia_for_pii=True, max_finding_remediation_days=30
    )
    assert res["total_controls"] == 1
    assert res["missing_dpia_control_ids"] == []
    assert res["unverified_statutory_control_ids"] == []
    assert res["overdue_finding_control_ids"] == ["CTRL-FIND-01"]
    assert res["regulatory_compliance_status"] == "REMEDIATION_OVERDUE"
    assert res["is_regulatory_compliant"] is False
    assert len(res["issues"]) >= 1


def test_audit_executive_report_regulatory_and_data_privacy_statutory_breach():
    """Caso 3: Falta DPIA en tratamiento PII o control estatutario no verificado -> STATUTORY_OR_PRIVACY_BREACH."""
    from backend.services.project_export_service import (
        audit_executive_report_regulatory_and_data_privacy_compliance,
    )

    controls = [
        {
            "control_id": "CTRL-NO-DPIA",
            "processes_personal_data_pii": True,
            "dpia_completed_and_signed": False,
            "has_open_audit_finding": False,
            "finding_age_days": 0,
            "is_mandatory_statutory": False,
            "control_verified": True,
        },
        {
            "control_id": "CTRL-UNVERIFIED-STAT",
            "processes_personal_data_pii": False,
            "dpia_completed_and_signed": False,
            "has_open_audit_finding": True,
            "finding_age_days": 60,
            "is_mandatory_statutory": True,
            "control_verified": False,
        },
    ]
    res = audit_executive_report_regulatory_and_data_privacy_compliance(
        controls, require_dpia_for_pii=True, max_finding_remediation_days=30
    )
    assert res["total_controls"] == 2
    assert res["missing_dpia_control_ids"] == ["CTRL-NO-DPIA"]
    assert res["unverified_statutory_control_ids"] == ["CTRL-UNVERIFIED-STAT"]
    assert res["overdue_finding_control_ids"] == ["CTRL-UNVERIFIED-STAT"]
    assert res["regulatory_compliance_status"] == "STATUTORY_OR_PRIVACY_BREACH"
    assert res["is_regulatory_compliant"] is False
    assert len(res["issues"]) >= 3


def test_audit_executive_report_regulatory_and_data_privacy_empty_and_binding():
    """Caso 4: Entradas vacías/inválidas y binding en ProjectExportService + __all__."""
    import backend.services.project_export_service as mod
    from backend.services.project_export_service import (
        ProjectExportService,
        audit_executive_report_regulatory_and_data_privacy_compliance,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = audit_executive_report_regulatory_and_data_privacy_compliance(payload)  # type: ignore[arg-type]
        assert empty["total_controls"] == 0
        assert empty["missing_dpia_control_ids"] == []
        assert empty["unverified_statutory_control_ids"] == []
        assert empty["overdue_finding_control_ids"] == []
        assert empty["regulatory_compliance_status"] == "COMPLIANT"
        assert empty["is_regulatory_compliant"] is True
        assert empty["issues"] == []

    sample = [
        {
            "control_id": "CTRL-99",
            "processes_personal_data_pii": True,
            "dpia_completed_and_signed": True,
            "has_open_audit_finding": False,
            "finding_age_days": 0,
            "is_mandatory_statutory": True,
            "control_verified": True,
        }
    ]
    assert (
        ProjectExportService.audit_executive_report_regulatory_and_data_privacy_compliance(
            sample
        )
        == audit_executive_report_regulatory_and_data_privacy_compliance(sample)
    )
    assert (
        "audit_executive_report_regulatory_and_data_privacy_compliance"
        in mod.__all__
    )


def test_audit_executive_report_finops_cloud_cost_optimal():
    """Caso 1: Workloads dentro de costo unitario, buena utilización (>= 40%), cobertura RI >= 60% y gasto sin etiqueta <= 5% -> OPTIMAL."""
    from backend.services.project_export_service import (
        audit_executive_report_finops_cloud_cost_and_idle_capacity,
    )

    workloads = [
        {
            "workload_id": "WKL-API",
            "monthly_baseline_cost": 5000.0,
            "monthly_actual_cost": 5200.0,
            "baseline_unit_cost": 0.10,
            "actual_unit_cost": 0.11,  # +10% <= 15%
            "avg_utilization_pct": 65.0,
            "commitment_coverage_pct": 75.0,
            "untagged_spend_amount": 100.0,
        },
        {
            "workload_id": "WKL-DB",
            "monthly_baseline_cost": 3000.0,
            "monthly_actual_cost": 2800.0,
            "baseline_unit_cost": 0.50,
            "actual_unit_cost": 0.48,
            "avg_utilization_pct": 55.0,
            "commitment_coverage_pct": 80.0,
            "untagged_spend_amount": 60.0,  # total untagged = 160 / 8000 = 2.0%
        },
    ]
    res = audit_executive_report_finops_cloud_cost_and_idle_capacity(workloads)
    assert res["total_workloads"] == 2
    assert res["total_baseline_cost"] == 8000.0
    assert res["total_actual_cost"] == 8000.0
    assert res["total_untagged_spend"] == 160.0
    assert res["untagged_spend_share_pct"] == 2.0
    assert res["estimated_monthly_waste"] == 160.0
    assert res["unit_cost_drift_workload_ids"] == []
    assert res["idle_capacity_workload_ids"] == []
    assert res["low_commitment_workload_ids"] == []
    assert res["finops_governance_status"] == "OPTIMAL"
    assert res["recommendations"] == []


def test_audit_executive_report_finops_cloud_cost_warning():
    """Caso 2: Capacidad ociosa (< 40%) o baja cobertura RI (< 60%) sin sobrepaso crítico -> WARNING."""
    from backend.services.project_export_service import (
        audit_executive_report_finops_cloud_cost_and_idle_capacity,
    )

    workloads = [
        {
            "workload_id": "WKL-DEV",
            "monthly_baseline_cost": 2000.0,
            "monthly_actual_cost": 2000.0,
            "baseline_unit_cost": 1.0,
            "actual_unit_cost": 1.05,
            "avg_utilization_pct": 15.0,  # < 40% -> waste = 2000 * (40-15)/100 = 500
            "commitment_coverage_pct": 30.0,  # < 60%
            "untagged_spend_amount": 50.0,
        }
    ]
    res = audit_executive_report_finops_cloud_cost_and_idle_capacity(workloads)
    assert res["total_workloads"] == 1
    assert res["idle_capacity_workload_ids"] == ["WKL-DEV"]
    assert res["low_commitment_workload_ids"] == ["WKL-DEV"]
    assert res["estimated_monthly_waste"] == 550.0
    assert res["finops_governance_status"] == "WARNING"
    assert len(res["recommendations"]) >= 2


def test_audit_executive_report_finops_cloud_cost_critical():
    """Caso 3: Costo total > 1.2x baseline, gasto sin etiqueta > 15% o >= 2 workloads con deriva de costo unitario -> CRITICAL."""
    from backend.services.project_export_service import (
        audit_executive_report_finops_cloud_cost_and_idle_capacity,
    )

    workloads = [
        {
            "workload_id": "WKL-ML-1",
            "monthly_baseline_cost": 4000.0,
            "monthly_actual_cost": 5500.0,
            "baseline_unit_cost": 1.0,
            "actual_unit_cost": 1.30,  # +30% > 15%
            "avg_utilization_pct": 50.0,
            "commitment_coverage_pct": 70.0,
            "untagged_spend_amount": 1200.0,
        },
        {
            "workload_id": "WKL-ML-2",
            "monthly_baseline_cost": 2000.0,
            "monthly_actual_cost": 2500.0,
            "baseline_unit_cost": 2.0,
            "actual_unit_cost": 2.60,  # +30% > 15%
            "avg_utilization_pct": 45.0,
            "commitment_coverage_pct": 65.0,
            "untagged_spend_amount": 400.0,  # 1600 / 8000 = 20% > 15%
        },
    ]
    res = audit_executive_report_finops_cloud_cost_and_idle_capacity(workloads)
    assert res["total_workloads"] == 2
    assert res["unit_cost_drift_workload_ids"] == ["WKL-ML-1", "WKL-ML-2"]
    assert res["untagged_spend_share_pct"] == 20.0
    assert res["finops_governance_status"] == "CRITICAL"
    assert len(res["recommendations"]) >= 2


def test_audit_executive_report_finops_cloud_cost_empty_and_binding():
    """Caso 4: Entradas vacías/inválidas y binding en ProjectExportService + __all__."""
    import backend.services.project_export_service as mod
    from backend.services.project_export_service import (
        ProjectExportService,
        audit_executive_report_finops_cloud_cost_and_idle_capacity,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = audit_executive_report_finops_cloud_cost_and_idle_capacity(payload)  # type: ignore[arg-type]
        assert empty["total_workloads"] == 0
        assert empty["total_baseline_cost"] == 0.0
        assert empty["total_actual_cost"] == 0.0
        assert empty["total_untagged_spend"] == 0.0
        assert empty["untagged_spend_share_pct"] == 0.0
        assert empty["estimated_monthly_waste"] == 0.0
        assert empty["unit_cost_drift_workload_ids"] == []
        assert empty["idle_capacity_workload_ids"] == []
        assert empty["low_commitment_workload_ids"] == []
        assert empty["finops_governance_status"] == "OPTIMAL"
        assert empty["recommendations"] == []

    sample = [
        {
            "workload_id": "WKL-99",
            "monthly_baseline_cost": 1000.0,
            "monthly_actual_cost": 1000.0,
            "baseline_unit_cost": 1.0,
            "actual_unit_cost": 1.0,
            "avg_utilization_pct": 80.0,
            "commitment_coverage_pct": 90.0,
            "untagged_spend_amount": 0.0,
        }
    ]
    assert (
        ProjectExportService.audit_executive_report_finops_cloud_cost_and_idle_capacity(
            sample
        )
        == audit_executive_report_finops_cloud_cost_and_idle_capacity(sample)
    )
    assert (
        "audit_executive_report_finops_cloud_cost_and_idle_capacity"
        in mod.__all__
    )


def test_audit_executive_report_sbom_cve_and_oss_license_compliance_compliant():
    """Caso 1: SBOM con licencias permisivas y sin CVEs fuera de SLA -> COMPLIANT."""
    from backend.services.project_export_service import (
        audit_executive_report_sbom_cve_and_oss_license_compliance,
    )

    deps = [
        {
            "package_id": "fastapi@0.115.0",
            "spdx_license": "MIT",
            "cvss_severity": "NONE",
            "days_open": 0,
            "has_patch_available": True,
            "is_direct_dependency": True,
        },
        {
            "package_id": "sqlalchemy@2.0.35",
            "spdx_license": "Apache-2.0",
            "cvss_severity": "CRITICAL",
            "days_open": 3,
            "has_patch_available": True,
            "is_direct_dependency": True,
        },
    ]
    res = audit_executive_report_sbom_cve_and_oss_license_compliance(
        deps, critical_cve_sla_days=7, high_cve_sla_days=30
    )
    assert res["total_dependencies"] == 2
    assert res["copyleft_violation_package_ids"] == []
    assert res["breached_critical_cve_package_ids"] == []
    assert res["breached_high_cve_package_ids"] == []
    assert res["unpatched_zero_day_package_ids"] == []
    assert res["sbom_governance_status"] == "COMPLIANT"
    assert res["is_sbom_compliant"] is True
    assert res["recommendations"] == []


def test_audit_executive_report_sbom_cve_and_oss_license_compliance_warning():
    """Caso 2: CVE HIGH fuera de SLA o zero-day sin parche pero sin copyleft ni CRITICAL vencido -> WARNING."""
    from backend.services.project_export_service import (
        audit_executive_report_sbom_cve_and_oss_license_compliance,
    )

    deps = [
        {
            "package_id": "urllib3@2.1.0",
            "spdx_license": "MIT",
            "cvss_severity": "HIGH",
            "days_open": 45,
            "has_patch_available": True,
            "is_direct_dependency": False,
        },
        {
            "package_id": "cryptography@42.0.0",
            "spdx_license": "BSD-3-Clause",
            "cvss_severity": "HIGH",
            "days_open": 5,
            "has_patch_available": False,
            "is_direct_dependency": True,
        },
    ]
    res = audit_executive_report_sbom_cve_and_oss_license_compliance(
        deps, critical_cve_sla_days=7, high_cve_sla_days=30
    )
    assert res["total_dependencies"] == 2
    assert res["copyleft_violation_package_ids"] == []
    assert res["breached_critical_cve_package_ids"] == []
    assert res["breached_high_cve_package_ids"] == ["urllib3@2.1.0"]
    assert res["unpatched_zero_day_package_ids"] == ["cryptography@42.0.0"]
    assert res["sbom_governance_status"] == "WARNING"
    assert res["is_sbom_compliant"] is False
    assert len(res["recommendations"]) >= 2


def test_audit_executive_report_sbom_cve_and_oss_license_compliance_critical():
    """Caso 3: Licencia copyleft prohibida (AGPL-3.0) y CVE CRITICAL fuera de SLA -> CRITICAL."""
    from backend.services.project_export_service import (
        audit_executive_report_sbom_cve_and_oss_license_compliance,
    )

    deps = [
        {
            "package_id": "copyleft-lib@1.0.0",
            "spdx_license": "AGPL-3.0",
            "cvss_severity": "NONE",
            "days_open": 0,
            "has_patch_available": True,
        },
        {
            "package_id": "xml-parser@0.9.1",
            "spdx_license": "UNKNOWN",
            "cvss_severity": "CRITICAL",
            "days_open": 14,
            "has_patch_available": False,
        },
    ]
    res = audit_executive_report_sbom_cve_and_oss_license_compliance(
        deps, critical_cve_sla_days=7, high_cve_sla_days=30
    )
    assert res["total_dependencies"] == 2
    assert res["copyleft_violation_package_ids"] == [
        "copyleft-lib@1.0.0",
        "xml-parser@0.9.1",
    ]
    assert res["breached_critical_cve_package_ids"] == ["xml-parser@0.9.1"]
    assert res["unpatched_zero_day_package_ids"] == ["xml-parser@0.9.1"]
    assert res["sbom_governance_status"] == "CRITICAL"
    assert res["is_sbom_compliant"] is False
    assert len(res["recommendations"]) >= 2


def test_audit_executive_report_sbom_cve_and_oss_license_empty_and_binding():
    """Caso 4: Entradas vacías/inválidas y binding en ProjectExportService + __all__."""
    import backend.services.project_export_service as mod
    from backend.services.project_export_service import (
        ProjectExportService,
        audit_executive_report_sbom_cve_and_oss_license_compliance,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = audit_executive_report_sbom_cve_and_oss_license_compliance(payload)  # type: ignore[arg-type]
        assert empty["total_dependencies"] == 0
        assert empty["copyleft_violation_package_ids"] == []
        assert empty["breached_critical_cve_package_ids"] == []
        assert empty["breached_high_cve_package_ids"] == []
        assert empty["unpatched_zero_day_package_ids"] == []
        assert empty["sbom_governance_status"] == "COMPLIANT"
        assert empty["is_sbom_compliant"] is True
        assert empty["recommendations"] == []

    sample = [
        {
            "package_id": "pydantic@2.9.0",
            "spdx_license": "MIT",
            "cvss_severity": "NONE",
            "days_open": 0,
            "has_patch_available": True,
        }
    ]
    assert (
        ProjectExportService.audit_executive_report_sbom_cve_and_oss_license_compliance(
            sample
        )
        == audit_executive_report_sbom_cve_and_oss_license_compliance(sample)
    )
    assert (
        "audit_executive_report_sbom_cve_and_oss_license_compliance" in mod.__all__
    )


def test_audit_executive_report_dr_rto_rpo_critical_paths():
    """Caso 1: TIER_0 con brecha RTO, backup sin verificar y 2+ brechas -> CRITICAL."""
    from backend.services.project_export_service import (
        audit_executive_report_disaster_recovery_rto_rpo_readiness,
    )

    res = audit_executive_report_disaster_recovery_rto_rpo_readiness(
        [
            {
                "system_id": "SYS-01",
                "criticality_tier": "TIER_0",
                "target_rto_minutes": 60.0,
                "actual_drill_rto_minutes": 95.0,
                "target_rpo_minutes": 15.0,
                "actual_drill_rpo_minutes": 15.0,
                "days_since_last_drill": 10,
                "backup_restore_verified": True,
            },
            {
                "system_id": "SYS-02",
                "criticality_tier": "TIER_2",
                "target_rto_minutes": 240.0,
                "actual_drill_rto_minutes": 240.0,
                "target_rpo_minutes": 60.0,
                "actual_drill_rpo_minutes": 75.0,
                "days_since_last_drill": 5,
                "backup_restore_verified": True,
            },
            {
                "system_id": "SYS-03",
                "criticality_tier": "TIER_1",
                "target_rto_minutes": 120.0,
                "actual_drill_rto_minutes": 120.0,
                "target_rpo_minutes": 30.0,
                "actual_drill_rpo_minutes": 30.0,
                "days_since_last_drill": 1,
                "backup_restore_verified": False,
            },
        ]
    )
    assert res["total_systems"] == 3
    assert res["rto_breached_system_ids"] == ["SYS-01"]
    assert res["rpo_breached_system_ids"] == ["SYS-02"]
    assert res["stale_drill_system_ids"] == []
    assert res["unverified_backup_system_ids"] == ["SYS-03"]
    # Brecha en TIER_0 + backup sin verificar -> CRITICAL.
    assert res["dr_governance_status"] == "CRITICAL"
    assert res["is_dr_compliant"] is False
    assert len(res["recommendations"]) == 3


def test_audit_executive_report_dr_rto_rpo_warning_paths():
    """Caso 2: brecha RTO en TIER_2 sola, o drill vencido -> WARNING."""
    from backend.services.project_export_service import (
        audit_executive_report_disaster_recovery_rto_rpo_readiness,
    )

    res_tier2 = audit_executive_report_disaster_recovery_rto_rpo_readiness(
        [
            {
                "system_id": "SYS-10",
                "criticality_tier": "TIER_2",
                "target_rto_minutes": 240.0,
                "actual_drill_rto_minutes": 300.0,
                "target_rpo_minutes": 60.0,
                "actual_drill_rpo_minutes": 60.0,
                "days_since_last_drill": 5,
                "backup_restore_verified": True,
            },
        ]
    )
    assert res_tier2["rto_breached_system_ids"] == ["SYS-10"]
    assert res_tier2["rpo_breached_system_ids"] == []
    assert res_tier2["dr_governance_status"] == "WARNING"
    assert res_tier2["is_dr_compliant"] is False

    res_stale = audit_executive_report_disaster_recovery_rto_rpo_readiness(
        [
            {
                "system_id": "SYS-11",
                "criticality_tier": "TIER_1",
                "target_rto_minutes": 60.0,
                "actual_drill_rto_minutes": 60.0,
                "target_rpo_minutes": 15.0,
                "actual_drill_rpo_minutes": 15.0,
                "days_since_last_drill": 91,
                "backup_restore_verified": True,
            },
        ]
    )
    assert res_stale["stale_drill_system_ids"] == ["SYS-11"]
    assert res_stale["rto_breached_system_ids"] == []
    assert res_stale["dr_governance_status"] == "WARNING"


def test_audit_executive_report_dr_rto_rpo_resilient_and_boundaries():
    """Caso 3: fronteras exactas (brecha solo si > target; drill vencido solo si > max) -> RESILIENT."""
    from backend.services.project_export_service import (
        audit_executive_report_disaster_recovery_rto_rpo_readiness,
    )

    res = audit_executive_report_disaster_recovery_rto_rpo_readiness(
        [
            {
                "system_id": "SYS-20",
                "criticality_tier": "TIER_0",
                "target_rto_minutes": 60.0,
                "actual_drill_rto_minutes": 60.0,
                "target_rpo_minutes": 15.0,
                "actual_drill_rpo_minutes": 15.0,
                "days_since_last_drill": 90,
                "backup_restore_verified": True,
            },
            {
                "system_id": "SYS-21",
                "criticality_tier": "TIER_1",
                "target_rto_minutes": 120.0,
                "actual_drill_rto_minutes": 118.0,
                "target_rpo_minutes": 30.0,
                "actual_drill_rpo_minutes": 29.0,
                "days_since_last_drill": 0,
                "backup_restore_verified": True,
            },
        ]
    )
    assert res["total_systems"] == 2
    assert res["rto_breached_system_ids"] == []
    assert res["rpo_breached_system_ids"] == []
    assert res["stale_drill_system_ids"] == []
    assert res["unverified_backup_system_ids"] == []
    assert res["dr_governance_status"] == "RESILIENT"
    assert res["is_dr_compliant"] is True
    assert res["recommendations"] == []


def test_audit_executive_report_dr_rto_rpo_invalid_and_binding():
    """Caso 4: entradas no-lista/no-dict y binding + __all__."""
    import backend.services.project_export_service as mod
    from backend.services.project_export_service import (
        ProjectExportService,
        audit_executive_report_disaster_recovery_rto_rpo_readiness,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = audit_executive_report_disaster_recovery_rto_rpo_readiness(payload)  # type: ignore[arg-type]
        assert empty["total_systems"] == 0
        assert empty["rto_breached_system_ids"] == []
        assert empty["rpo_breached_system_ids"] == []
        assert empty["stale_drill_system_ids"] == []
        assert empty["unverified_backup_system_ids"] == []
        assert empty["dr_governance_status"] == "RESILIENT"
        assert empty["is_dr_compliant"] is True
        assert empty["recommendations"] == []

    sample = [
        {
            "system_id": "SYS-30",
            "criticality_tier": "TIER_1",
            "target_rto_minutes": 60.0,
            "actual_drill_rto_minutes": 50.0,
            "target_rpo_minutes": 15.0,
            "actual_drill_rpo_minutes": 10.0,
            "days_since_last_drill": 3,
            "backup_restore_verified": True,
        },
    ]
    assert (
        ProjectExportService.audit_executive_report_disaster_recovery_rto_rpo_readiness(sample)
        == audit_executive_report_disaster_recovery_rto_rpo_readiness(sample)
    )
    assert "audit_executive_report_disaster_recovery_rto_rpo_readiness" in mod.__all__


def test_audit_executive_report_software_license_true_up_and_shelfware_optimized():
    """Caso 1: Suscripciones sin sobre-despliegue y shelfware <=20% -> OPTIMIZED."""
    from backend.services.project_export_service import (
        audit_executive_report_software_license_true_up_and_shelfware,
    )

    licenses = [
        {
            "subscription_id": "SUB-GITHUB-ENT",
            "purchased_seats": 100,
            "deployed_active_seats": 92,
            "annual_cost_per_seat": 250.0,
            "days_until_renewal": 120,
        },
        {
            "subscription_id": "SUB-JIRA-CLOUD",
            "purchased_seats": 50,
            "deployed_active_seats": 45,
            "annual_cost_per_seat": 150.0,
            "days_until_renewal": 60,
        },
    ]
    res = audit_executive_report_software_license_true_up_and_shelfware(
        licenses, max_shelfware_waste_pct=20.0, true_up_penalty_multiplier=1.25
    )
    assert res["total_subscriptions"] == 2
    assert res["total_true_up_exposure_cost"] == 0.0
    assert res["total_annual_shelfware_waste_cost"] == 2750.0
    assert res["overdeployed_subscription_ids"] == []
    assert res["shelfware_subscription_ids"] == []
    assert res["imminent_renewal_rightsizing_ids"] == []
    assert res["license_governance_status"] == "OPTIMIZED"
    assert res["is_license_compliant"] is True
    assert res["recommendations"] == []


def test_audit_executive_report_software_license_true_up_and_shelfware_warning():
    """Caso 2: Suscripción con shelfware >20% y renovación próxima (<=30d) sin sobre-despliegue -> WARNING."""
    from backend.services.project_export_service import (
        audit_executive_report_software_license_true_up_and_shelfware,
    )

    licenses = [
        {
            "subscription_id": "SUB-FIGMA-PRO",
            "purchased_seats": 100,
            "deployed_active_seats": 60,
            "annual_cost_per_seat": 500.0,
            "days_until_renewal": 20,
        }
    ]
    res = audit_executive_report_software_license_true_up_and_shelfware(
        licenses, max_shelfware_waste_pct=20.0, true_up_penalty_multiplier=1.25
    )
    assert res["total_subscriptions"] == 1
    assert res["total_true_up_exposure_cost"] == 0.0
    assert res["total_annual_shelfware_waste_cost"] == 20000.0
    assert res["overdeployed_subscription_ids"] == []
    assert res["shelfware_subscription_ids"] == ["SUB-FIGMA-PRO"]
    assert res["imminent_renewal_rightsizing_ids"] == ["SUB-FIGMA-PRO"]
    assert res["license_governance_status"] == "WARNING"
    assert res["is_license_compliant"] is False
    assert len(res["recommendations"]) >= 2


def test_audit_executive_report_software_license_true_up_and_shelfware_compliance_risk():
    """Caso 3: Asientos activos exceden los contratados (riesgo de penalización True-Up) -> COMPLIANCE_RISK."""
    from backend.services.project_export_service import (
        audit_executive_report_software_license_true_up_and_shelfware,
    )

    licenses = [
        {
            "subscription_id": "SUB-ORACLE-DB",
            "purchased_seats": 40,
            "deployed_active_seats": 50,
            "annual_cost_per_seat": 1000.0,
            "days_until_renewal": 15,
        }
    ]
    res = audit_executive_report_software_license_true_up_and_shelfware(
        licenses, max_shelfware_waste_pct=20.0, true_up_penalty_multiplier=1.25
    )
    assert res["total_subscriptions"] == 1
    assert res["total_true_up_exposure_cost"] == 12500.0
    assert res["overdeployed_subscription_ids"] == ["SUB-ORACLE-DB"]
    assert res["imminent_renewal_rightsizing_ids"] == ["SUB-ORACLE-DB"]
    assert res["license_governance_status"] == "COMPLIANCE_RISK"
    assert res["is_license_compliant"] is False
    assert len(res["recommendations"]) >= 2


def test_audit_executive_report_software_license_true_up_empty_and_binding():
    """Caso 4: Entradas vacías/inválidas y binding en ProjectExportService + __all__."""
    import backend.services.project_export_service as mod
    from backend.services.project_export_service import (
        ProjectExportService,
        audit_executive_report_software_license_true_up_and_shelfware,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = audit_executive_report_software_license_true_up_and_shelfware(payload)  # type: ignore[arg-type]
        assert empty["total_subscriptions"] == 0
        assert empty["total_true_up_exposure_cost"] == 0.0
        assert empty["total_annual_shelfware_waste_cost"] == 0.0
        assert empty["overdeployed_subscription_ids"] == []
        assert empty["shelfware_subscription_ids"] == []
        assert empty["imminent_renewal_rightsizing_ids"] == []
        assert empty["license_governance_status"] == "OPTIMIZED"
        assert empty["is_license_compliant"] is True
        assert empty["recommendations"] == []

    sample = [
        {
            "subscription_id": "SUB-99",
            "purchased_seats": 20,
            "deployed_active_seats": 19,
            "annual_cost_per_seat": 100.0,
            "days_until_renewal": 90,
        }
    ]
    assert (
        ProjectExportService.audit_executive_report_software_license_true_up_and_shelfware(
            sample
        )
        == audit_executive_report_software_license_true_up_and_shelfware(sample)
    )
    assert (
        "audit_executive_report_software_license_true_up_and_shelfware"
        in mod.__all__
    )


def test_audit_executive_report_pentest_remediation_sla_and_zero_trust_breach_exposure():
    from backend.services.project_export_service import (
        audit_executive_report_pentest_remediation_sla_and_zero_trust,
    )

    res = audit_executive_report_pentest_remediation_sla_and_zero_trust(
        [
            {
                "finding_id": "PT-001",
                "severity": "CRITICAL",
                "days_open": 12,
                "is_remediated_and_retested": False,
                "exploitable_externally": True,
                "compensating_waf_control_active": True,
            },
            {
                "finding_id": "PT-002",
                "severity": "HIGH",
                "days_open": 5,
                "is_remediated_and_retested": False,
                "exploitable_externally": True,
                "compensating_waf_control_active": False,
            },
            {
                "finding_id": "PT-003",
                "severity": "CRITICAL",
                "days_open": 45,
                "is_remediated_and_retested": True,
                "exploitable_externally": True,
                "compensating_waf_control_active": False,
            },
        ],
        critical_sla_days=7,
        high_sla_days=30,
        days_since_last_pentest=30,
        max_pentest_age_days=180,
    )
    assert res["total_findings"] == 3
    assert res["open_findings_count"] == 2
    assert res["stale_pentest_assessment"] is False
    assert res["breached_critical_finding_ids"] == ["PT-001"]
    assert res["breached_high_finding_ids"] == []
    assert res["unmitigated_external_exploit_ids"] == ["PT-002"]
    assert res["pentest_governance_status"] == "BREACH_EXPOSURE"
    assert res["is_security_posture_ready"] is False
    assert len(res["recommendations"]) >= 2


def test_audit_executive_report_pentest_remediation_sla_and_zero_trust_warning():
    from backend.services.project_export_service import (
        audit_executive_report_pentest_remediation_sla_and_zero_trust,
    )

    res = audit_executive_report_pentest_remediation_sla_and_zero_trust(
        [
            {
                "finding_id": "PT-010",
                "severity": "HIGH",
                "days_open": 40,
                "is_remediated_and_retested": False,
                "exploitable_externally": False,
                "compensating_waf_control_active": False,
            }
        ],
        critical_sla_days=7,
        high_sla_days=30,
        days_since_last_pentest=200,
        max_pentest_age_days=180,
    )
    assert res["open_findings_count"] == 1
    assert res["stale_pentest_assessment"] is True
    assert res["breached_critical_finding_ids"] == []
    assert res["breached_high_finding_ids"] == ["PT-010"]
    assert res["unmitigated_external_exploit_ids"] == []
    assert res["pentest_governance_status"] == "WARNING"
    assert res["is_security_posture_ready"] is False


def test_audit_executive_report_pentest_remediation_sla_and_zero_trust_hardened_and_empty():
    from backend.services.project_export_service import (
        audit_executive_report_pentest_remediation_sla_and_zero_trust,
    )

    empty = audit_executive_report_pentest_remediation_sla_and_zero_trust(
        [{"finding_id": "   "}, "invalid"]  # type: ignore[list-item]
    )
    assert empty["total_findings"] == 0
    assert empty["open_findings_count"] == 0
    assert empty["stale_pentest_assessment"] is False
    assert empty["pentest_governance_status"] == "HARDENED"
    assert empty["is_security_posture_ready"] is True
    assert empty["recommendations"] == []

    hardened = audit_executive_report_pentest_remediation_sla_and_zero_trust(
        [
            {
                "finding_id": "PT-020",
                "severity": "CRITICAL",
                "days_open": 3,
                "is_remediated_and_retested": False,
                "exploitable_externally": True,
                "compensating_waf_control_active": True,
            },
            {
                "finding_id": "PT-021",
                "severity": "LOW",
                "days_open": 60,
                "is_remediated_and_retested": False,
                "exploitable_externally": False,
                "compensating_waf_control_active": False,
            },
        ],
        critical_sla_days=7,
        high_sla_days=30,
        days_since_last_pentest=45,
        max_pentest_age_days=180,
    )
    assert hardened["total_findings"] == 2
    assert hardened["open_findings_count"] == 2
    assert hardened["pentest_governance_status"] == "HARDENED"
    assert hardened["is_security_posture_ready"] is True
    assert hardened["recommendations"] == []


def test_audit_executive_report_pentest_remediation_sla_and_zero_trust_staticmethod_and_dunder_all():
    import backend.services.project_export_service as mod
    from backend.services.project_export_service import (
        ProjectExportService,
        audit_executive_report_pentest_remediation_sla_and_zero_trust,
    )

    sample = [
        {
            "finding_id": "PT-99",
            "severity": "MEDIUM",
            "days_open": 10,
            "is_remediated_and_retested": True,
        }
    ]
    assert (
        ProjectExportService.audit_executive_report_pentest_remediation_sla_and_zero_trust(
            sample
        )
        == audit_executive_report_pentest_remediation_sla_and_zero_trust(sample)
    )
    assert (
        "audit_executive_report_pentest_remediation_sla_and_zero_trust"
        in mod.__all__
    )


def test_audit_executive_report_esg_carbon_footprint_green_sustainable():
    """Caso 1: Workloads con PUE eficiente (<=1.4), red limpia (<=350 g/kWh) y emisiones dentro del presupuesto -> GREEN_SUSTAINABLE."""
    from backend.services.project_export_service import (
        audit_executive_report_esg_carbon_footprint_and_green_cloud_pue,
    )

    workloads = [
        {
            "workload_id": "WKL-K8S-EU",
            "energy_consumed_kwh": 1000.0,
            "datacenter_pue": 1.15,
            "grid_carbon_intensity_g_per_kwh": 200.0,
            "renewable_energy_offset_pct": 50.0,  # gross=230 kg, net=115 kg
        },
        {
            "workload_id": "WKL-DB-US",
            "energy_consumed_kwh": 500.0,
            "datacenter_pue": 1.20,
            "grid_carbon_intensity_g_per_kwh": 300.0,
            "renewable_energy_offset_pct": 0.0,  # gross=180 kg, net=180 kg
        },
    ]
    res = audit_executive_report_esg_carbon_footprint_and_green_cloud_pue(
        workloads,
        max_pue_ratio=1.4,
        max_carbon_intensity_g_per_kwh=350.0,
        carbon_budget_kg_co2e=1000.0,
    )
    assert res["total_workloads_evaluated"] == 2
    assert res["total_net_co2e_kg"] == 295.0
    assert res["budget_utilization_pct"] == 29.5
    assert res["inefficient_pue_workload_ids"] == []
    assert res["high_carbon_grid_workload_ids"] == []
    assert res["esg_sustainability_status"] == "GREEN_SUSTAINABLE"
    assert res["is_esg_compliant"] is True


def test_audit_executive_report_esg_carbon_footprint_inefficient_infrastructure():
    """Caso 2: PUE > 1.4 o intensidad de red > 350 g/kWh sin exceder presupuesto de carbono -> INEFFICIENT_INFRASTRUCTURE."""
    from backend.services.project_export_service import (
        audit_executive_report_esg_carbon_footprint_and_green_cloud_pue,
    )

    workloads = [
        {
            "workload_id": "WKL-LEGACY-DC",
            "energy_consumed_kwh": 400.0,
            "datacenter_pue": 1.65,
            "grid_carbon_intensity_g_per_kwh": 450.0,
            "renewable_energy_offset_pct": 20.0,  # gross=297 kg, net=237.6 kg
        }
    ]
    res = audit_executive_report_esg_carbon_footprint_and_green_cloud_pue(
        workloads,
        max_pue_ratio=1.4,
        max_carbon_intensity_g_per_kwh=350.0,
        carbon_budget_kg_co2e=1000.0,
    )
    assert res["total_workloads_evaluated"] == 1
    assert res["total_net_co2e_kg"] == 237.6
    assert res["budget_utilization_pct"] == 23.76
    assert res["inefficient_pue_workload_ids"] == ["WKL-LEGACY-DC"]
    assert res["high_carbon_grid_workload_ids"] == ["WKL-LEGACY-DC"]
    assert res["esg_sustainability_status"] == "INEFFICIENT_INFRASTRUCTURE"
    assert res["is_esg_compliant"] is False


def test_audit_executive_report_esg_carbon_footprint_budget_breach():
    """Caso 3: Emisiones netas superan el presupuesto de carbono -> CARBON_BUDGET_BREACH."""
    from backend.services.project_export_service import (
        audit_executive_report_esg_carbon_footprint_and_green_cloud_pue,
    )

    workloads = [
        {
            "workload_id": "WKL-GPU-TRAIN",
            "energy_consumed_kwh": 5000.0,
            "datacenter_pue": 1.50,
            "grid_carbon_intensity_g_per_kwh": 400.0,
            "renewable_energy_offset_pct": 10.0,  # gross=3000 kg, net=2700 kg > 1000 kg
        }
    ]
    res = audit_executive_report_esg_carbon_footprint_and_green_cloud_pue(
        workloads,
        max_pue_ratio=1.4,
        max_carbon_intensity_g_per_kwh=350.0,
        carbon_budget_kg_co2e=1000.0,
    )
    assert res["total_workloads_evaluated"] == 1
    assert res["total_net_co2e_kg"] == 2700.0
    assert res["budget_utilization_pct"] == 270.0
    assert res["inefficient_pue_workload_ids"] == ["WKL-GPU-TRAIN"]
    assert res["high_carbon_grid_workload_ids"] == ["WKL-GPU-TRAIN"]
    assert res["esg_sustainability_status"] == "CARBON_BUDGET_BREACH"
    assert res["is_esg_compliant"] is False


def test_audit_executive_report_esg_carbon_footprint_empty_and_binding():
    """Caso 4: Entradas vacías/inválidas y binding en ProjectExportService + __all__."""
    import backend.services.project_export_service as mod
    from backend.services.project_export_service import (
        ProjectExportService,
        audit_executive_report_esg_carbon_footprint_and_green_cloud_pue,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = audit_executive_report_esg_carbon_footprint_and_green_cloud_pue(payload)  # type: ignore[arg-type]
        assert empty["total_workloads_evaluated"] == 0
        assert empty["total_net_co2e_kg"] == 0.0
        assert empty["budget_utilization_pct"] == 0.0
        assert empty["inefficient_pue_workload_ids"] == []
        assert empty["high_carbon_grid_workload_ids"] == []
        assert empty["esg_sustainability_status"] == "GREEN_SUSTAINABLE"
        assert empty["is_esg_compliant"] is True

    sample = [
        {
            "workload_id": "WKL-99",
            "energy_consumed_kwh": 200.0,
            "datacenter_pue": 1.1,
            "grid_carbon_intensity_g_per_kwh": 150.0,
            "renewable_energy_offset_pct": 100.0,
        }
    ]
    assert (
        ProjectExportService.audit_executive_report_esg_carbon_footprint_and_green_cloud_pue(
            sample
        )
        == audit_executive_report_esg_carbon_footprint_and_green_cloud_pue(sample)
    )
    assert (
        "audit_executive_report_esg_carbon_footprint_and_green_cloud_pue"
        in mod.__all__
    )


def test_audit_executive_report_dora_four_keys_and_delivery_stability_low_performing_at_risk():
    from backend.services.project_export_service import (
        audit_executive_report_dora_four_keys_and_delivery_stability,
    )

    res = audit_executive_report_dora_four_keys_and_delivery_stability(
        [
            {
                "service_id": "SVC-AUTH",
                "deployments_per_week": 1.0,
                "lead_time_for_changes_hours": 48.0,
                "change_failure_rate_pct": 25.0,
                "mean_time_to_restore_hours": 3.5,
            },
            {
                "service_id": "SVC-PAY",
                "deployments_per_week": 10.0,
                "lead_time_for_changes_hours": 4.0,
                "change_failure_rate_pct": 5.0,
                "mean_time_to_restore_hours": 0.5,
            },
        ],
        min_deploys_per_week=3.0,
        max_lead_time_hours=24.0,
        max_change_failure_rate_pct=15.0,
        max_mttr_hours=1.0,
    )
    assert res["total_services_evaluated"] == 2
    assert res["elite_performer_service_ids"] == ["SVC-PAY"]
    assert res["low_throughput_service_ids"] == ["SVC-AUTH"]
    assert res["instability_breach_service_ids"] == ["SVC-AUTH"]
    assert res["elite_performer_ratio_pct"] == 50.0
    assert res["dora_maturity_tier"] == "LOW_PERFORMING_AT_RISK"
    assert res["is_dora_compliant"] is False


def test_audit_executive_report_dora_four_keys_and_delivery_stability_unstable_and_low_velocity():
    from backend.services.project_export_service import (
        audit_executive_report_dora_four_keys_and_delivery_stability,
    )

    unstable = audit_executive_report_dora_four_keys_and_delivery_stability(
        [
            {
                "service_id": "SVC-FAST-BROKEN",
                "deployments_per_week": 15.0,
                "lead_time_for_changes_hours": 2.0,
                "change_failure_rate_pct": 30.0,
                "mean_time_to_restore_hours": 0.5,
            }
        ]
    )
    assert unstable["low_throughput_service_ids"] == []
    assert unstable["instability_breach_service_ids"] == ["SVC-FAST-BROKEN"]
    assert unstable["dora_maturity_tier"] == "HIGH_THROUGHPUT_UNSTABLE"
    assert unstable["is_dora_compliant"] is False

    slow = audit_executive_report_dora_four_keys_and_delivery_stability(
        [
            {
                "service_id": "SVC-SLOW-STABLE",
                "deployments_per_week": 0.5,
                "lead_time_for_changes_hours": 72.0,
                "change_failure_rate_pct": 2.0,
                "mean_time_to_restore_hours": 0.2,
            }
        ]
    )
    assert slow["low_throughput_service_ids"] == ["SVC-SLOW-STABLE"]
    assert slow["instability_breach_service_ids"] == []
    assert slow["dora_maturity_tier"] == "STABLE_LOW_VELOCITY"
    assert slow["is_dora_compliant"] is False


def test_audit_executive_report_dora_four_keys_and_delivery_stability_elite_and_empty():
    from backend.services.project_export_service import (
        audit_executive_report_dora_four_keys_and_delivery_stability,
    )

    empty = audit_executive_report_dora_four_keys_and_delivery_stability(
        [{"service_id": "   "}, "invalid"]  # type: ignore[list-item]
    )
    assert empty["total_services_evaluated"] == 0
    assert empty["elite_performer_ratio_pct"] == 100.0
    assert empty["dora_maturity_tier"] == "ELITE"
    assert empty["is_dora_compliant"] is True

    elite = audit_executive_report_dora_four_keys_and_delivery_stability(
        [
            {
                "service_id": "SVC-CORE",
                "deployments_per_week": 12.0,
                "lead_time_for_changes_hours": 6.0,
                "change_failure_rate_pct": 4.0,
                "mean_time_to_restore_hours": 0.4,
            }
        ]
    )
    assert elite["total_services_evaluated"] == 1
    assert elite["elite_performer_service_ids"] == ["SVC-CORE"]
    assert elite["elite_performer_ratio_pct"] == 100.0
    assert elite["dora_maturity_tier"] == "ELITE"
    assert elite["is_dora_compliant"] is True


def test_audit_executive_report_dora_four_keys_and_delivery_stability_staticmethod_and_dunder_all():
    import backend.services.project_export_service as mod
    from backend.services.project_export_service import (
        ProjectExportService,
        audit_executive_report_dora_four_keys_and_delivery_stability,
    )

    sample = [
        {
            "service_id": "SVC-99",
            "deployments_per_week": 5.0,
            "lead_time_for_changes_hours": 10.0,
            "change_failure_rate_pct": 5.0,
            "mean_time_to_restore_hours": 0.5,
        }
    ]
    assert (
        ProjectExportService.audit_executive_report_dora_four_keys_and_delivery_stability(
            sample
        )
        == audit_executive_report_dora_four_keys_and_delivery_stability(sample)
    )
    assert (
        "audit_executive_report_dora_four_keys_and_delivery_stability"
        in mod.__all__
    )


def test_audit_executive_report_data_privacy_pii_masking_and_residency_privacy_breach_blocked():
    from backend.services.project_export_service import (
        audit_executive_report_data_privacy_pii_masking_and_residency,
    )

    res = audit_executive_report_data_privacy_pii_masking_and_residency(
        [
            {
                "dataset_id": "DS-USERS",
                "contains_pii_or_phi": True,
                "is_encrypted_and_masked_at_rest": False,
                "retention_ttl_days": 180,
                "storage_region": "LATAM-BOG",
                "has_dpia_impact_assessment_signed": False,
            },
            {
                "dataset_id": "DS-TELEMETRY",
                "contains_pii_or_phi": False,
                "is_encrypted_and_masked_at_rest": True,
                "retention_ttl_days": 90,
                "storage_region": "AP-SOUTH",
                "has_dpia_impact_assessment_signed": True,
            },
        ],
        max_retention_days=365,
        allowed_regions=("EU-CENTRAL", "US-EAST", "LATAM-BOG"),
    )
    assert res["total_datasets_evaluated"] == 2
    assert res["pii_datasets_count"] == 1
    assert res["unmasked_pii_dataset_ids"] == ["DS-USERS"]
    assert res["missing_dpia_dataset_ids"] == ["DS-USERS"]
    assert res["unauthorized_region_dataset_ids"] == ["DS-TELEMETRY"]
    assert res["excessive_retention_dataset_ids"] == []
    assert res["privacy_governance_status"] == "PRIVACY_BREACH_BLOCKED"
    assert res["is_privacy_compliant"] is False


def test_audit_executive_report_data_privacy_pii_masking_and_residency_retention_warning():
    from backend.services.project_export_service import (
        audit_executive_report_data_privacy_pii_masking_and_residency,
    )

    res = audit_executive_report_data_privacy_pii_masking_and_residency(
        [
            {
                "dataset_id": "DS-ARCHIVE",
                "contains_pii_or_phi": True,
                "is_encrypted_and_masked_at_rest": True,
                "retention_ttl_days": 730,
                "storage_region": "EU-CENTRAL",
                "has_dpia_impact_assessment_signed": True,
            }
        ],
        max_retention_days=365,
    )
    assert res["unmasked_pii_dataset_ids"] == []
    assert res["missing_dpia_dataset_ids"] == []
    assert res["unauthorized_region_dataset_ids"] == []
    assert res["excessive_retention_dataset_ids"] == ["DS-ARCHIVE"]
    assert res["privacy_governance_status"] == "RETENTION_POLICY_WARNING"
    assert res["is_privacy_compliant"] is False


def test_audit_executive_report_data_privacy_pii_masking_and_residency_compliant_and_empty():
    from backend.services.project_export_service import (
        audit_executive_report_data_privacy_pii_masking_and_residency,
    )

    empty = audit_executive_report_data_privacy_pii_masking_and_residency(
        [{"dataset_id": "   "}, "invalid"]  # type: ignore[list-item]
    )
    assert empty["total_datasets_evaluated"] == 0
    assert empty["pii_datasets_count"] == 0
    assert empty["privacy_governance_status"] == "PRIVACY_COMPLIANT"
    assert empty["is_privacy_compliant"] is True

    compliant = audit_executive_report_data_privacy_pii_masking_and_residency(
        [
            {
                "dataset_id": "DS-CLEAN",
                "contains_pii_or_phi": True,
                "is_encrypted_and_masked_at_rest": True,
                "retention_ttl_days": 180,
                "storage_region": "us-east",
                "has_dpia_impact_assessment_signed": True,
            }
        ]
    )
    assert compliant["total_datasets_evaluated"] == 1
    assert compliant["pii_datasets_count"] == 1
    assert compliant["privacy_governance_status"] == "PRIVACY_COMPLIANT"
    assert compliant["is_privacy_compliant"] is True


def test_audit_executive_report_data_privacy_pii_masking_and_residency_staticmethod_and_dunder_all():
    import backend.services.project_export_service as mod
    from backend.services.project_export_service import (
        ProjectExportService,
        audit_executive_report_data_privacy_pii_masking_and_residency,
    )

    sample = [
        {
            "dataset_id": "DS-99",
            "contains_pii_or_phi": False,
            "retention_ttl_days": 30,
            "storage_region": "LATAM-BOG",
        }
    ]
    assert (
        ProjectExportService.audit_executive_report_data_privacy_pii_masking_and_residency(
            sample
        )
        == audit_executive_report_data_privacy_pii_masking_and_residency(sample)
    )
    assert (
        "audit_executive_report_data_privacy_pii_masking_and_residency"
        in mod.__all__
    )


def test_audit_executive_report_wcag_accessibility_and_aria_compliance_critical_barrier():
    from backend.services.project_export_service import (
        audit_executive_report_wcag_accessibility_and_aria_compliance,
    )

    res = audit_executive_report_wcag_accessibility_and_aria_compliance(
        [
            {
                "view_id": "VIEW-GANTT-CHART",
                "lowest_text_contrast_ratio": 3.1,
                "missing_aria_label_count": 4,
                "has_keyboard_focus_trap": False,
                "supports_prefers_reduced_motion": True,
            },
            {
                "view_id": "VIEW-TASK-DRAWER",
                "lowest_text_contrast_ratio": 5.2,
                "missing_aria_label_count": 0,
                "has_keyboard_focus_trap": True,
                "supports_prefers_reduced_motion": True,
            },
        ],
        min_contrast_ratio_aa=4.5,
        max_missing_aria_labels=0,
    )
    assert res["total_views_evaluated"] == 2
    assert res["contrast_failing_view_ids"] == ["VIEW-GANTT-CHART"]
    assert res["aria_incomplete_view_ids"] == ["VIEW-GANTT-CHART"]
    assert res["keyboard_trap_view_ids"] == ["VIEW-TASK-DRAWER"]
    assert res["motion_unsafe_view_ids"] == []
    assert res["accessibility_governance_status"] == "WCAG_CRITICAL_BARRIER"
    assert res["is_wcag_aa_compliant"] is False


def test_audit_executive_report_wcag_accessibility_and_aria_compliance_motion_warning():
    from backend.services.project_export_service import (
        audit_executive_report_wcag_accessibility_and_aria_compliance,
    )

    res = audit_executive_report_wcag_accessibility_and_aria_compliance(
        [
            {
                "view_id": "VIEW-HERO-BANNER",
                "lowest_text_contrast_ratio": 7.0,
                "missing_aria_label_count": 0,
                "has_keyboard_focus_trap": False,
                "supports_prefers_reduced_motion": False,
            }
        ]
    )
    assert res["contrast_failing_view_ids"] == []
    assert res["aria_incomplete_view_ids"] == []
    assert res["keyboard_trap_view_ids"] == []
    assert res["motion_unsafe_view_ids"] == ["VIEW-HERO-BANNER"]
    assert res["accessibility_governance_status"] == "MOTION_PREFERENCE_WARNING"
    assert res["is_wcag_aa_compliant"] is False


def test_audit_executive_report_wcag_accessibility_and_aria_compliance_compliant_and_empty():
    from backend.services.project_export_service import (
        audit_executive_report_wcag_accessibility_and_aria_compliance,
    )

    empty = audit_executive_report_wcag_accessibility_and_aria_compliance(
        [{"view_id": "   "}, "invalid"]  # type: ignore[list-item]
    )
    assert empty["total_views_evaluated"] == 0
    assert empty["accessibility_governance_status"] == "WCAG_AA_COMPLIANT"
    assert empty["is_wcag_aa_compliant"] is True

    compliant = audit_executive_report_wcag_accessibility_and_aria_compliance(
        [
            {
                "view_id": "VIEW-PORTFOLIO-SUMMARY",
                "lowest_text_contrast_ratio": 4.8,
                "missing_aria_label_count": 0,
                "has_keyboard_focus_trap": False,
                "supports_prefers_reduced_motion": True,
            }
        ]
    )
    assert compliant["total_views_evaluated"] == 1
    assert compliant["accessibility_governance_status"] == "WCAG_AA_COMPLIANT"
    assert compliant["is_wcag_aa_compliant"] is True


def test_audit_executive_report_wcag_accessibility_and_aria_compliance_staticmethod_and_dunder_all():
    import backend.services.project_export_service as mod
    from backend.services.project_export_service import (
        ProjectExportService,
        audit_executive_report_wcag_accessibility_and_aria_compliance,
    )

    sample = [
        {
            "view_id": "VIEW-99",
            "lowest_text_contrast_ratio": 5.5,
            "missing_aria_label_count": 0,
        }
    ]
    assert (
        ProjectExportService.audit_executive_report_wcag_accessibility_and_aria_compliance(
            sample
        )
        == audit_executive_report_wcag_accessibility_and_aria_compliance(sample)
    )
    assert (
        "audit_executive_report_wcag_accessibility_and_aria_compliance"
        in mod.__all__
    )


def test_audit_executive_report_watermelon_kpi_and_narrative_consistency_greenwash_detected():
    from backend.services.project_export_service import (
        audit_executive_report_watermelon_kpi_and_narrative_consistency,
    )

    res = audit_executive_report_watermelon_kpi_and_narrative_consistency(
        [
            {
                "section_id": "SEC-CORE-INFRA",
                "reported_rag_status": "green",
                "underlying_cpi": 0.84,
                "underlying_spi": 0.98,
                "open_critical_blockers": 0,
                "has_quantified_decision_request": True,
            },
            {
                "section_id": "SEC-DATA-MIGRATION",
                "reported_rag_status": "GREEN",
                "underlying_cpi": 1.02,
                "underlying_spi": 1.00,
                "open_critical_blockers": 2,
                "has_quantified_decision_request": True,
            },
        ],
        min_spi_cpi_for_green=0.95,
    )
    assert res["total_sections_evaluated"] == 2
    assert res["watermelon_greenwash_section_ids"] == [
        "SEC-CORE-INFRA",
        "SEC-DATA-MIGRATION",
    ]
    assert res["unactionable_red_amber_section_ids"] == []
    assert res["reporting_integrity_status"] == "WATERMELON_GREENWASH_DETECTED"
    assert res["is_reporting_transparent"] is False


def test_audit_executive_report_watermelon_kpi_and_narrative_consistency_missing_decision_warning():
    from backend.services.project_export_service import (
        audit_executive_report_watermelon_kpi_and_narrative_consistency,
    )

    res = audit_executive_report_watermelon_kpi_and_narrative_consistency(
        [
            {
                "section_id": "SEC-PROCUREMENT",
                "reported_rag_status": "RED",
                "underlying_cpi": 0.80,
                "underlying_spi": 0.85,
                "open_critical_blockers": 3,
                "has_quantified_decision_request": False,
            }
        ],
        min_spi_cpi_for_green=0.95,
    )
    assert res["watermelon_greenwash_section_ids"] == []
    assert res["unactionable_red_amber_section_ids"] == ["SEC-PROCUREMENT"]
    assert (
        res["reporting_integrity_status"]
        == "ESCALATION_DECISION_MISSING_WARNING"
    )
    assert res["is_reporting_transparent"] is False


def test_audit_executive_report_watermelon_kpi_and_narrative_consistency_transparent_and_empty():
    from backend.services.project_export_service import (
        audit_executive_report_watermelon_kpi_and_narrative_consistency,
    )

    empty = audit_executive_report_watermelon_kpi_and_narrative_consistency(
        [{"section_id": "   "}, "invalid"]  # type: ignore[list-item]
    )
    assert empty["total_sections_evaluated"] == 0
    assert (
        empty["reporting_integrity_status"]
        == "TRANSPARENT_EXECUTIVE_REPORTING"
    )
    assert empty["is_reporting_transparent"] is True

    transparent = (
        audit_executive_report_watermelon_kpi_and_narrative_consistency(
            [
                {
                    "section_id": "SEC-FINANCE",
                    "reported_rag_status": "GREEN",
                    "underlying_cpi": 0.99,
                    "underlying_spi": 0.97,
                    "open_critical_blockers": 0,
                },
                {
                    "section_id": "SEC-SECURITY",
                    "reported_rag_status": "AMBER",
                    "underlying_cpi": 0.91,
                    "underlying_spi": 0.92,
                    "open_critical_blockers": 1,
                    "has_quantified_decision_request": True,
                },
            ]
        )
    )
    assert transparent["total_sections_evaluated"] == 2
    assert (
        transparent["reporting_integrity_status"]
        == "TRANSPARENT_EXECUTIVE_REPORTING"
    )
    assert transparent["is_reporting_transparent"] is True


def test_audit_executive_report_watermelon_kpi_and_narrative_consistency_staticmethod_and_dunder_all():
    import backend.services.project_export_service as mod
    from backend.services.project_export_service import (
        ProjectExportService,
        audit_executive_report_watermelon_kpi_and_narrative_consistency,
    )

    sample = [
        {
            "section_id": "SEC-99",
            "reported_rag_status": "GREEN",
            "underlying_cpi": 1.0,
            "underlying_spi": 1.0,
            "open_critical_blockers": 0,
        }
    ]
    assert (
        ProjectExportService.audit_executive_report_watermelon_kpi_and_narrative_consistency(
            sample
        )
        == audit_executive_report_watermelon_kpi_and_narrative_consistency(
            sample
        )
    )
    assert (
        "audit_executive_report_watermelon_kpi_and_narrative_consistency"
        in mod.__all__
    )


def test_audit_executive_report_multi_region_failover_and_split_brain_fencing_failure():
    from backend.services.project_export_service import (
        audit_executive_report_multi_region_failover_and_split_brain_fencing,
    )

    res = audit_executive_report_multi_region_failover_and_split_brain_fencing(
        [
            {
                "region_id": "us-east-1",
                "dns_failover_ttl_seconds": 30,
                "replication_lag_ms": 120.0,
                "has_stonith_quorum_fencing": False,
                "passed_automated_regional_evacuation_drill": True,
            },
            {
                "region_id": "eu-west-1",
                "dns_failover_ttl_seconds": 30,
                "replication_lag_ms": 80.0,
                "has_stonith_quorum_fencing": True,
                "passed_automated_regional_evacuation_drill": False,
            },
        ],
        max_dns_failover_ttl_seconds=60,
        max_replication_lag_ms=500.0,
    )
    assert res["total_regions_evaluated"] == 2
    assert res["split_brain_vulnerable_region_ids"] == ["us-east-1"]
    assert res["failed_evacuation_drill_region_ids"] == ["eu-west-1"]
    assert res["high_replication_lag_region_ids"] == []
    assert res["slow_dns_ttl_region_ids"] == []
    assert (
        res["multi_region_resilience_status"]
        == "SPLIT_BRAIN_OR_EVACUATION_FAILURE"
    )
    assert res["is_multi_region_compliant"] is False


def test_audit_executive_report_multi_region_failover_and_split_brain_fencing_lag_and_dns_warning():
    from backend.services.project_export_service import (
        audit_executive_report_multi_region_failover_and_split_brain_fencing,
    )

    res = audit_executive_report_multi_region_failover_and_split_brain_fencing(
        [
            {
                "region_id": "sa-east-1",
                "dns_failover_ttl_seconds": 300,
                "replication_lag_ms": 850.0,
                "has_stonith_quorum_fencing": True,
                "passed_automated_regional_evacuation_drill": True,
            },
            {
                "region_id": "ap-southeast-1",
                "dns_failover_ttl_seconds": 0,
                "replication_lag_ms": 200.0,
                "has_stonith_quorum_fencing": True,
                "passed_automated_regional_evacuation_drill": True,
            },
        ],
        max_dns_failover_ttl_seconds=60,
        max_replication_lag_ms=500.0,
    )
    assert res["split_brain_vulnerable_region_ids"] == []
    assert res["failed_evacuation_drill_region_ids"] == []
    assert res["high_replication_lag_region_ids"] == ["sa-east-1"]
    assert res["slow_dns_ttl_region_ids"] == ["sa-east-1", "ap-southeast-1"]
    assert (
        res["multi_region_resilience_status"]
        == "REPLICATION_OR_DNS_LAG_WARNING"
    )
    assert res["is_multi_region_compliant"] is False


def test_audit_executive_report_multi_region_failover_and_split_brain_fencing_resilient_and_empty():
    from backend.services.project_export_service import (
        audit_executive_report_multi_region_failover_and_split_brain_fencing,
    )

    empty = (
        audit_executive_report_multi_region_failover_and_split_brain_fencing(
            [{"region_id": "   "}, "invalid"]  # type: ignore[list-item]
        )
    )
    assert empty["total_regions_evaluated"] == 0
    assert (
        empty["multi_region_resilience_status"] == "ACTIVE_ACTIVE_RESILIENT"
    )
    assert empty["is_multi_region_compliant"] is True

    resilient = (
        audit_executive_report_multi_region_failover_and_split_brain_fencing(
            [
                {
                    "region_id": "us-east-1",
                    "dns_failover_ttl_seconds": 30,
                    "replication_lag_ms": 45.0,
                    "has_stonith_quorum_fencing": True,
                    "passed_automated_regional_evacuation_drill": True,
                },
                {
                    "region_id": "us-west-2",
                    "dns_failover_ttl_seconds": 60,
                    "replication_lag_ms": 110.0,
                    "has_stonith_quorum_fencing": True,
                    "passed_automated_regional_evacuation_drill": True,
                },
            ],
            max_dns_failover_ttl_seconds=60,
            max_replication_lag_ms=500.0,
        )
    )
    assert resilient["total_regions_evaluated"] == 2
    assert (
        resilient["multi_region_resilience_status"]
        == "ACTIVE_ACTIVE_RESILIENT"
    )
    assert resilient["is_multi_region_compliant"] is True


def test_audit_executive_report_multi_region_failover_and_split_brain_fencing_staticmethod_and_dunder_all():
    import backend.services.project_export_service as mod
    from backend.services.project_export_service import (
        ProjectExportService,
        audit_executive_report_multi_region_failover_and_split_brain_fencing,
    )

    sample = [
        {
            "region_id": "eu-central-1",
            "dns_failover_ttl_seconds": 30,
            "replication_lag_ms": 50.0,
            "has_stonith_quorum_fencing": True,
            "passed_automated_regional_evacuation_drill": True,
        }
    ]
    assert (
        ProjectExportService.audit_executive_report_multi_region_failover_and_split_brain_fencing(
            sample
        )
        == audit_executive_report_multi_region_failover_and_split_brain_fencing(
            sample
        )
    )
    assert (
        "audit_executive_report_multi_region_failover_and_split_brain_fencing"
        in mod.__all__
    )


def test_audit_executive_report_backup_worm_immutability_and_restore_drills_ransomware_exposure():
    from backend.services.project_export_service import (
        audit_executive_report_backup_worm_immutability_and_restore_drills,
    )

    res = audit_executive_report_backup_worm_immutability_and_restore_drills(
        [
            {
                "vault_id": "VLT-PG-PRIMARY",
                "has_worm_object_lock_enabled": False,
                "is_air_gapped_isolated_account": True,
                "days_since_verified_restore_drill": 12,
                "last_restore_checksum_verified": True,
            },
            {
                "vault_id": "VLT-MINIO-BLOBS",
                "has_worm_object_lock_enabled": True,
                "is_air_gapped_isolated_account": True,
                "days_since_verified_restore_drill": 5,
                "last_restore_checksum_verified": False,
            },
        ],
        max_days_since_restore_drill=30,
    )
    assert res["total_vaults_evaluated"] == 2
    assert res["mutable_or_exposed_vault_ids"] == ["VLT-PG-PRIMARY"]
    assert res["corrupted_restore_vault_ids"] == ["VLT-MINIO-BLOBS"]
    assert res["stale_restore_drill_vault_ids"] == []
    assert res["ransomware_backup_status"] == "RANSOMWARE_DESTRUCTION_EXPOSURE"
    assert res["is_backup_resilience_compliant"] is False


def test_audit_executive_report_backup_worm_immutability_and_restore_drills_stale_drill_warning():
    from backend.services.project_export_service import (
        audit_executive_report_backup_worm_immutability_and_restore_drills,
    )

    res = audit_executive_report_backup_worm_immutability_and_restore_drills(
        [
            {
                "vault_id": "VLT-ARCHIVE-S3",
                "has_worm_object_lock_enabled": True,
                "is_air_gapped_isolated_account": True,
                "days_since_verified_restore_drill": 65,
                "last_restore_checksum_verified": True,
            }
        ],
        max_days_since_restore_drill=30,
    )
    assert res["mutable_or_exposed_vault_ids"] == []
    assert res["corrupted_restore_vault_ids"] == []
    assert res["stale_restore_drill_vault_ids"] == ["VLT-ARCHIVE-S3"]
    assert res["ransomware_backup_status"] == "RESTORE_DRILL_STALE_WARNING"
    assert res["is_backup_resilience_compliant"] is False


def test_audit_executive_report_backup_worm_immutability_and_restore_drills_verified_and_empty():
    from backend.services.project_export_service import (
        audit_executive_report_backup_worm_immutability_and_restore_drills,
    )

    empty = audit_executive_report_backup_worm_immutability_and_restore_drills(
        [{"vault_id": "   "}, "invalid"]  # type: ignore[list-item]
    )
    assert empty["total_vaults_evaluated"] == 0
    assert empty["ransomware_backup_status"] == "IMMUTABLE_BACKUP_VERIFIED"
    assert empty["is_backup_resilience_compliant"] is True

    verified = (
        audit_executive_report_backup_worm_immutability_and_restore_drills(
            [
                {
                    "vault_id": "VLT-GOLD-01",
                    "has_worm_object_lock_enabled": True,
                    "is_air_gapped_isolated_account": True,
                    "days_since_verified_restore_drill": 7,
                    "last_restore_checksum_verified": True,
                }
            ],
            max_days_since_restore_drill=30,
        )
    )
    assert verified["total_vaults_evaluated"] == 1
    assert verified["ransomware_backup_status"] == "IMMUTABLE_BACKUP_VERIFIED"
    assert verified["is_backup_resilience_compliant"] is True


def test_audit_executive_report_backup_worm_immutability_and_restore_drills_staticmethod_and_dunder_all():
    import backend.services.project_export_service as mod
    from backend.services.project_export_service import (
        ProjectExportService,
        audit_executive_report_backup_worm_immutability_and_restore_drills,
    )

    sample = [
        {
            "vault_id": "VLT-99",
            "has_worm_object_lock_enabled": True,
            "is_air_gapped_isolated_account": True,
            "days_since_verified_restore_drill": 10,
            "last_restore_checksum_verified": True,
        }
    ]
    assert (
        ProjectExportService.audit_executive_report_backup_worm_immutability_and_restore_drills(
            sample
        )
        == audit_executive_report_backup_worm_immutability_and_restore_drills(
            sample
        )
    )
    assert (
        "audit_executive_report_backup_worm_immutability_and_restore_drills"
        in mod.__all__
    )


def test_audit_executive_report_vendor_sla_uptime_and_rebate_capture_breach():
    from backend.services.project_export_service import (
        audit_executive_report_vendor_sla_uptime_and_rebate_capture,
    )

    result = audit_executive_report_vendor_sla_uptime_and_rebate_capture(
        [
            {
                "service_id": "SVC-UNCLAIMED",
                "observed_uptime_pct": 99.5,
                "contractual_sla_uptime_pct": 99.9,
                "eligible_for_penalty_rebate": True,
                "rebate_claim_submitted": False,
                "days_since_sla_breach": 40,
                "root_cause_attributed_and_documented": True,
            },
            {
                "service_id": "SVC-UNATTR",
                "observed_uptime_pct": 99.8,
                "contractual_sla_uptime_pct": 99.95,
                "eligible_for_penalty_rebate": False,
                "rebate_claim_submitted": True,
                "days_since_sla_breach": 5,
                "root_cause_attributed_and_documented": False,
            },
        ],
        min_contractual_uptime_pct=99.9,
        max_unclaimed_rebate_days=30,
    )
    assert result["evaluated_services_count"] == 2
    assert result["unclaimed_rebate_or_unattributed_service_ids"] == [
        "SVC-UNCLAIMED",
        "SVC-UNATTR",
    ]
    assert result["sla_uptime_deficit_service_ids"] == [
        "SVC-UNCLAIMED",
        "SVC-UNATTR",
    ]
    assert (
        result["vendor_sla_report_status"]
        == "VENDOR_SLA_REBATE_LEAKAGE_OR_ATTRIBUTION_BREACH"
    )
    assert result["is_vendor_sla_report_compliant"] is False


def test_audit_executive_report_vendor_sla_uptime_and_rebate_capture_warning():
    from backend.services.project_export_service import (
        audit_executive_report_vendor_sla_uptime_and_rebate_capture,
    )

    result = audit_executive_report_vendor_sla_uptime_and_rebate_capture(
        [
            {
                "service_id": "SVC-DEFICIT-1",
                "observed_uptime_pct": 99.7,
                "contractual_sla_uptime_pct": 99.9,
                "eligible_for_penalty_rebate": True,
                "rebate_claim_submitted": True,
                "days_since_sla_breach": 10,
                "root_cause_attributed_and_documented": True,
            }
        ],
        min_contractual_uptime_pct=99.9,
        max_unclaimed_rebate_days=30,
    )
    assert result["evaluated_services_count"] == 1
    assert result["unclaimed_rebate_or_unattributed_service_ids"] == []
    assert result["sla_uptime_deficit_service_ids"] == ["SVC-DEFICIT-1"]
    assert result["vendor_sla_report_status"] == "VENDOR_SLA_UPTIME_DEFICIT_WARNING"
    assert result["is_vendor_sla_report_compliant"] is False


def test_audit_executive_report_vendor_sla_uptime_and_rebate_capture_optimal_and_empty():
    from backend.services.project_export_service import (
        audit_executive_report_vendor_sla_uptime_and_rebate_capture,
    )

    empty = audit_executive_report_vendor_sla_uptime_and_rebate_capture(
        [{"service_id": "   "}, "invalid"]  # type: ignore[list-item]
    )
    assert empty["evaluated_services_count"] == 0
    assert empty["vendor_sla_report_status"] == "VENDOR_SLA_ATTAINMENT_OPTIMAL"
    assert empty["is_vendor_sla_report_compliant"] is True

    optimal = audit_executive_report_vendor_sla_uptime_and_rebate_capture(
        [
            {
                "service_id": "SVC-GOLD-1",
                "observed_uptime_pct": 99.99,
                "contractual_sla_uptime_pct": 99.95,
                "eligible_for_penalty_rebate": False,
                "rebate_claim_submitted": True,
                "days_since_sla_breach": 0,
                "root_cause_attributed_and_documented": True,
            }
        ],
        min_contractual_uptime_pct=99.9,
        max_unclaimed_rebate_days=30,
    )
    assert optimal["evaluated_services_count"] == 1
    assert optimal["vendor_sla_report_status"] == "VENDOR_SLA_ATTAINMENT_OPTIMAL"
    assert optimal["is_vendor_sla_report_compliant"] is True


def test_audit_executive_report_vendor_sla_uptime_and_rebate_capture_staticmethod_and_dunder_all():
    import backend.services.project_export_service as mod
    from backend.services.project_export_service import (
        ProjectExportService,
        audit_executive_report_vendor_sla_uptime_and_rebate_capture,
    )

    sample = [
        {
            "service_id": "SVC-99",
            "observed_uptime_pct": 99.98,
            "contractual_sla_uptime_pct": 99.9,
        }
    ]
    assert (
        ProjectExportService.audit_executive_report_vendor_sla_uptime_and_rebate_capture(
            sample
        )
        == audit_executive_report_vendor_sla_uptime_and_rebate_capture(sample)
    )
    assert (
        "audit_executive_report_vendor_sla_uptime_and_rebate_capture"
        in mod.__all__
    )


def test_audit_executive_report_finops_unit_economics_and_ri_coverage_breach():
    from backend.services.project_export_service import (
        audit_executive_report_finops_unit_economics_and_ri_coverage,
    )

    result = audit_executive_report_finops_unit_economics_and_ri_coverage(
        [
            {
                "account_id": "AWS-NO-ALERT",
                "monthly_cloud_spend": 10000.0,
                "idle_or_unattached_resource_waste_amount": 100.0,
                "ri_or_savings_plan_coverage_pct": 85.0,
                "unit_cost_per_active_tenant_drift_pct": 2.0,
                "anomaly_detection_budget_alerts_enabled": False,
            },
            {
                "account_id": "AWS-HIGH-WASTE",
                "monthly_cloud_spend": 20000.0,
                "idle_or_unattached_resource_waste_amount": 1500.0,
                "ri_or_savings_plan_coverage_pct": 85.0,
                "unit_cost_per_active_tenant_drift_pct": 2.0,
                "anomaly_detection_budget_alerts_enabled": True,
            },
        ],
        min_commitment_coverage_pct=75.0,
        max_idle_waste_pct_of_spend=5.0,
    )
    assert result["evaluated_accounts_count"] == 2
    assert result["excessive_waste_or_unmonitored_account_ids"] == [
        "AWS-NO-ALERT",
        "AWS-HIGH-WASTE",
    ]
    assert result["low_ri_coverage_or_unit_drift_account_ids"] == []
    assert (
        result["finops_report_status"]
        == "FINOPS_IDLE_WASTE_OR_ALERTING_BREACH"
    )
    assert result["is_finops_report_compliant"] is False


def test_audit_executive_report_finops_unit_economics_and_ri_coverage_warning():
    from backend.services.project_export_service import (
        audit_executive_report_finops_unit_economics_and_ri_coverage,
    )

    result = audit_executive_report_finops_unit_economics_and_ri_coverage(
        [
            {
                "account_id": "AWS-LOW-RI",
                "monthly_cloud_spend": 10000.0,
                "idle_or_unattached_resource_waste_amount": 200.0,
                "ri_or_savings_plan_coverage_pct": 60.0,
                "unit_cost_per_active_tenant_drift_pct": 5.0,
                "anomaly_detection_budget_alerts_enabled": True,
            },
            {
                "account_id": "AWS-UNIT-DRIFT",
                "monthly_cloud_spend": 10000.0,
                "idle_or_unattached_resource_waste_amount": 200.0,
                "ri_or_savings_plan_coverage_pct": 80.0,
                "unit_cost_per_active_tenant_drift_pct": 18.5,
                "anomaly_detection_budget_alerts_enabled": True,
            },
        ],
        min_commitment_coverage_pct=75.0,
        max_idle_waste_pct_of_spend=5.0,
    )
    assert result["evaluated_accounts_count"] == 2
    assert result["excessive_waste_or_unmonitored_account_ids"] == []
    assert result["low_ri_coverage_or_unit_drift_account_ids"] == [
        "AWS-LOW-RI",
        "AWS-UNIT-DRIFT",
    ]
    assert (
        result["finops_report_status"]
        == "FINOPS_RI_COVERAGE_OR_UNIT_DRIFT_WARNING"
    )
    assert result["is_finops_report_compliant"] is False


def test_audit_executive_report_finops_unit_economics_and_ri_coverage_optimal_and_empty():
    from backend.services.project_export_service import (
        audit_executive_report_finops_unit_economics_and_ri_coverage,
    )

    empty = audit_executive_report_finops_unit_economics_and_ri_coverage(
        [{"account_id": "   "}, "invalid"]  # type: ignore[list-item]
    )
    assert empty["evaluated_accounts_count"] == 0
    assert empty["finops_report_status"] == "FINOPS_UNIT_ECONOMICS_OPTIMAL"
    assert empty["is_finops_report_compliant"] is True

    optimal = audit_executive_report_finops_unit_economics_and_ri_coverage(
        [
            {
                "account_id": "AWS-GOLD-1",
                "monthly_cloud_spend": 15000.0,
                "idle_or_unattached_resource_waste_amount": 300.0,
                "ri_or_savings_plan_coverage_pct": 88.0,
                "unit_cost_per_active_tenant_drift_pct": 3.0,
                "anomaly_detection_budget_alerts_enabled": True,
            }
        ],
        min_commitment_coverage_pct=75.0,
        max_idle_waste_pct_of_spend=5.0,
    )
    assert optimal["evaluated_accounts_count"] == 1
    assert optimal["finops_report_status"] == "FINOPS_UNIT_ECONOMICS_OPTIMAL"
    assert optimal["is_finops_report_compliant"] is True


def test_audit_executive_report_finops_unit_economics_and_ri_coverage_staticmethod_and_dunder_all():
    import backend.services.project_export_service as mod
    from backend.services.project_export_service import (
        ProjectExportService,
        audit_executive_report_finops_unit_economics_and_ri_coverage,
    )

    sample = [
        {
            "account_id": "AWS-99",
            "monthly_cloud_spend": 10000.0,
            "idle_or_unattached_resource_waste_amount": 100.0,
            "ri_or_savings_plan_coverage_pct": 85.0,
        }
    ]
    assert (
        ProjectExportService.audit_executive_report_finops_unit_economics_and_ri_coverage(
            sample
        )
        == audit_executive_report_finops_unit_economics_and_ri_coverage(sample)
    )
    assert (
        "audit_executive_report_finops_unit_economics_and_ri_coverage"
        in mod.__all__
    )



def test_soc2_type2_exception_or_attestation_breach():
    from backend.services.project_export_service import (
        audit_executive_report_soc2_type2_continuous_evidence_and_exceptions,
    )

    res = audit_executive_report_soc2_type2_continuous_evidence_and_exceptions(
        [
            {
                "control_id": "CC6-EXCEPTION",
                "unremediated_control_exceptions_count": 1,
            },
            {
                "control_id": "CC6-UNSIGNED",
                "independent_auditor_sampled_and_signed": False,
            },
            {
                "control_id": "CC7-STALE-STALL",
                "bridge_letter_current": False,
            },
        ],
        max_evidence_staleness_days=30,
        min_automated_collection_pct=85.0,
    )
    assert res["evaluated_controls_count"] == 3
    assert res["exception_or_unattested_control_ids"] == [
        "CC6-EXCEPTION",
        "CC6-UNSIGNED",
        "CC7-STALE-STALL",
    ]
    assert res["stale_or_manual_evidence_control_ids"] == []
    assert (
        res["soc2_attestation_status"]
        == "SOC2_CONTROL_EXCEPTION_OR_ATTESTATION_BREACH"
    )
    assert res["is_soc2_report_compliant"] is False


def test_soc2_type2_evidence_freshness_or_automation_warning():
    from backend.services.project_export_service import (
        audit_executive_report_soc2_type2_continuous_evidence_and_exceptions,
    )

    res = audit_executive_report_soc2_type2_continuous_evidence_and_exceptions(
        [
            {
                "control_id": "CC6-OLD-EVIDENCE",
                "evidence_age_days": 45,
            },
            {
                "control_id": "CC7-MANUAL",
                "automated_evidence_collection_pct": 70.0,
            },
        ],
        max_evidence_staleness_days=30,
        min_automated_collection_pct=85.0,
    )
    assert res["evaluated_controls_count"] == 2
    assert res["exception_or_unattested_control_ids"] == []
    assert res["stale_or_manual_evidence_control_ids"] == [
        "CC6-OLD-EVIDENCE",
        "CC7-MANUAL",
    ]
    assert (
        res["soc2_attestation_status"]
        == "SOC2_EVIDENCE_FRESHNESS_OR_AUTOMATION_WARNING"
    )
    assert res["is_soc2_report_compliant"] is False


def test_soc2_type2_boundaries_optimal_and_defaults():
    from backend.services.project_export_service import (
        audit_executive_report_soc2_type2_continuous_evidence_and_exceptions,
    )

    res = audit_executive_report_soc2_type2_continuous_evidence_and_exceptions(
        [
            {
                "control_id": "CC8-BOUNDARY",
                "evidence_age_days": 30,
                "automated_evidence_collection_pct": 85.0,
            },
            {"control_id": "CC8-ALL-DEFAULTS"},
        ],
        max_evidence_staleness_days=30,
        min_automated_collection_pct=85.0,
    )
    assert res["evaluated_controls_count"] == 2
    assert res["exception_or_unattested_control_ids"] == []
    assert res["stale_or_manual_evidence_control_ids"] == []
    assert (
        res["soc2_attestation_status"]
        == "SOC2_CONTINUOUS_COMPLIANCE_OPTIMAL"
    )
    assert res["is_soc2_report_compliant"] is True


def test_soc2_type2_invalid_and_binding():
    import backend.services.project_export_service as mod
    from backend.services.project_export_service import (
        ProjectExportService,
        audit_executive_report_soc2_type2_continuous_evidence_and_exceptions,
    )

    empty = audit_executive_report_soc2_type2_continuous_evidence_and_exceptions(
        None
    )
    assert empty["evaluated_controls_count"] == 0
    assert empty["exception_or_unattested_control_ids"] == []
    assert empty["stale_or_manual_evidence_control_ids"] == []
    assert (
        empty["soc2_attestation_status"]
        == "SOC2_CONTINUOUS_COMPLIANCE_OPTIMAL"
    )
    assert empty["is_soc2_report_compliant"] is True

    invalid = audit_executive_report_soc2_type2_continuous_evidence_and_exceptions(
        [42, "not-a-dict", None, {"control_id": "   "}]  # type: ignore[list-item]
    )
    assert invalid["evaluated_controls_count"] == 0

    defaults = audit_executive_report_soc2_type2_continuous_evidence_and_exceptions(
        [
            {
                "control_id": "CC9-DEFAULTS",
                "unremediated_control_exceptions_count": None,
                "evidence_age_days": None,
                "automated_evidence_collection_pct": None,
                "independent_auditor_sampled_and_signed": None,
                "bridge_letter_current": None,
            }
        ]
    )
    assert defaults["evaluated_controls_count"] == 1
    assert (
        defaults["soc2_attestation_status"]
        == "SOC2_CONTINUOUS_COMPLIANCE_OPTIMAL"
    )
    assert defaults["is_soc2_report_compliant"] is True

    sample = [
        {
            "control_id": "CC1-1",
            "evidence_age_days": 5,
            "automated_evidence_collection_pct": 97.0,
        }
    ]
    assert (
        ProjectExportService.audit_executive_report_soc2_type2_continuous_evidence_and_exceptions(
            sample
        )
        == audit_executive_report_soc2_type2_continuous_evidence_and_exceptions(
            sample
        )
    )
    assert (
        "audit_executive_report_soc2_type2_continuous_evidence_and_exceptions"
        in mod.__all__
    )


def test_audit_executive_report_zero_trust_pam_and_mfa_attestation_breach():
    from backend.services.project_export_service import (
        audit_executive_report_zero_trust_pam_and_mfa_attestation,
    )

    result = audit_executive_report_zero_trust_pam_and_mfa_attestation(
        [
            {
                "domain_id": "DOM-ORPHAN",
                "standing_privileged_admin_accounts_count": 0,
                "phishing_resistant_mfa_enforced_pct": 100.0,
                "max_jit_elevation_minutes_observed": 30.0,
                "orphaned_terminated_employee_tokens_count": 2,
                "session_recording_audit_trail_enabled": True,
            },
            {
                "domain_id": "DOM-WEAK-MFA",
                "standing_privileged_admin_accounts_count": 0,
                "phishing_resistant_mfa_enforced_pct": 92.5,
                "max_jit_elevation_minutes_observed": 30.0,
                "orphaned_terminated_employee_tokens_count": 0,
                "session_recording_audit_trail_enabled": True,
            },
            {
                "domain_id": "DOM-NO-AUDIT",
                "standing_privileged_admin_accounts_count": 0,
                "phishing_resistant_mfa_enforced_pct": 100.0,
                "max_jit_elevation_minutes_observed": 30.0,
                "orphaned_terminated_employee_tokens_count": 0,
                "session_recording_audit_trail_enabled": False,
            },
        ],
        max_standing_admin_accounts_allowed=0,
        max_jit_session_duration_minutes=60.0,
    )
    assert result["evaluated_domains_count"] == 3
    assert result["zero_trust_breach_domain_ids"] == [
        "DOM-ORPHAN",
        "DOM-WEAK-MFA",
        "DOM-NO-AUDIT",
    ]
    assert result["standing_privilege_or_long_jit_domain_ids"] == []
    assert (
        result["zero_trust_pam_status"]
        == "ZERO_TRUST_MFA_OR_ORPHAN_TOKEN_BREACH"
    )
    assert result["is_zero_trust_pam_compliant"] is False


def test_audit_executive_report_zero_trust_pam_and_mfa_attestation_warning():
    from backend.services.project_export_service import (
        audit_executive_report_zero_trust_pam_and_mfa_attestation,
    )

    result = audit_executive_report_zero_trust_pam_and_mfa_attestation(
        [
            {
                "domain_id": "DOM-STANDING-ADMIN",
                "standing_privileged_admin_accounts_count": 1,
                "phishing_resistant_mfa_enforced_pct": 100.0,
                "max_jit_elevation_minutes_observed": 30.0,
                "orphaned_terminated_employee_tokens_count": 0,
                "session_recording_audit_trail_enabled": True,
            },
            {
                "domain_id": "DOM-LONG-JIT",
                "standing_privileged_admin_accounts_count": 0,
                "phishing_resistant_mfa_enforced_pct": 100.0,
                "max_jit_elevation_minutes_observed": 120.0,
                "orphaned_terminated_employee_tokens_count": 0,
                "session_recording_audit_trail_enabled": True,
            },
        ],
        max_standing_admin_accounts_allowed=0,
        max_jit_session_duration_minutes=60.0,
    )
    assert result["evaluated_domains_count"] == 2
    assert result["zero_trust_breach_domain_ids"] == []
    assert result["standing_privilege_or_long_jit_domain_ids"] == [
        "DOM-STANDING-ADMIN",
        "DOM-LONG-JIT",
    ]
    assert (
        result["zero_trust_pam_status"]
        == "PAM_STANDING_ADMIN_OR_JIT_DURATION_WARNING"
    )
    assert result["is_zero_trust_pam_compliant"] is False


def test_audit_executive_report_zero_trust_pam_and_mfa_attestation_optimal_and_empty():
    from backend.services.project_export_service import (
        audit_executive_report_zero_trust_pam_and_mfa_attestation,
    )

    empty = audit_executive_report_zero_trust_pam_and_mfa_attestation(
        [{"domain_id": "   "}, "invalid"]  # type: ignore[list-item]
    )
    assert empty["evaluated_domains_count"] == 0
    assert (
        empty["zero_trust_pam_status"] == "ZERO_TRUST_PAM_GOVERNANCE_OPTIMAL"
    )
    assert empty["is_zero_trust_pam_compliant"] is True

    optimal = audit_executive_report_zero_trust_pam_and_mfa_attestation(
        [
            {
                "domain_id": "DOM-PROD-IAM",
                "standing_privileged_admin_accounts_count": 0,
                "phishing_resistant_mfa_enforced_pct": 100.0,
                "max_jit_elevation_minutes_observed": 30.0,
                "orphaned_terminated_employee_tokens_count": 0,
                "session_recording_audit_trail_enabled": True,
            }
        ],
        max_standing_admin_accounts_allowed=0,
        max_jit_session_duration_minutes=60.0,
    )
    assert optimal["evaluated_domains_count"] == 1
    assert (
        optimal["zero_trust_pam_status"]
        == "ZERO_TRUST_PAM_GOVERNANCE_OPTIMAL"
    )
    assert optimal["is_zero_trust_pam_compliant"] is True


def test_audit_executive_report_zero_trust_pam_and_mfa_attestation_staticmethod_and_dunder_all():
    import backend.services.project_export_service as mod
    from backend.services.project_export_service import (
        ProjectExportService,
        audit_executive_report_zero_trust_pam_and_mfa_attestation,
    )

    sample = [
        {
            "domain_id": "DOM-99",
            "standing_privileged_admin_accounts_count": 0,
            "phishing_resistant_mfa_enforced_pct": 100.0,
        }
    ]
    assert (
        ProjectExportService.audit_executive_report_zero_trust_pam_and_mfa_attestation(
            sample
        )
        == audit_executive_report_zero_trust_pam_and_mfa_attestation(sample)
    )
    assert (
        "audit_executive_report_zero_trust_pam_and_mfa_attestation"
        in mod.__all__
    )



def test_api_quota_fairness_noisy_neighbor_breach():
    from backend.services.project_export_service import (
        audit_executive_report_api_quota_fairness_and_noisy_neighbor,
    )

    res = audit_executive_report_api_quota_fairness_and_noisy_neighbor(
        [
            {
                "tenant_id": "TENANT-LATENCY-KILLER",
                "caused_cross_tenant_latency_degradation": True,
            },
            {
                "tenant_id": "TENANT-NO-BUCKET",
                "per_tenant_token_bucket_enforced": False,
            },
        ],
        max_single_tenant_traffic_share_pct=35.0,
        max_unthrottled_burst_multiplier=3.0,
    )
    assert res["evaluated_tenants_count"] == 2
    assert res["noisy_neighbor_or_unisolated_tenant_ids"] == [
        "TENANT-LATENCY-KILLER",
        "TENANT-NO-BUCKET",
    ]
    assert res["quota_hog_or_burst_warning_tenant_ids"] == []
    assert (
        res["quota_fairness_status"]
        == "API_NOISY_NEIGHBOR_ISOLATION_BREACH"
    )
    assert res["is_quota_fairness_compliant"] is False


def test_api_quota_fairness_concentration_or_burst_warning():
    from backend.services.project_export_service import (
        audit_executive_report_api_quota_fairness_and_noisy_neighbor,
    )

    res = audit_executive_report_api_quota_fairness_and_noisy_neighbor(
        [
            {
                "tenant_id": "TENANT-HOG",
                "observed_traffic_share_pct": 48.0,
            },
            {
                "tenant_id": "TENANT-BURST",
                "burst_to_steady_rate_multiplier": 4.5,
            },
            {
                "tenant_id": "TENANT-NO-RETRY-HEADER",
                "retry_after_header_compliant": False,
            },
        ],
        max_single_tenant_traffic_share_pct=35.0,
        max_unthrottled_burst_multiplier=3.0,
    )
    assert res["evaluated_tenants_count"] == 3
    assert res["noisy_neighbor_or_unisolated_tenant_ids"] == []
    assert res["quota_hog_or_burst_warning_tenant_ids"] == [
        "TENANT-HOG",
        "TENANT-BURST",
        "TENANT-NO-RETRY-HEADER",
    ]
    assert (
        res["quota_fairness_status"]
        == "API_QUOTA_CONCENTRATION_OR_BURST_WARNING"
    )
    assert res["is_quota_fairness_compliant"] is False


def test_api_quota_fairness_boundaries_optimal_and_defaults():
    from backend.services.project_export_service import (
        audit_executive_report_api_quota_fairness_and_noisy_neighbor,
    )

    res = audit_executive_report_api_quota_fairness_and_noisy_neighbor(
        [
            {
                "tenant_id": "TENANT-BOUNDARY",
                "observed_traffic_share_pct": 35.0,
                "burst_to_steady_rate_multiplier": 3.0,
            },
            {"tenant_id": "TENANT-ALL-DEFAULTS"},
        ],
        max_single_tenant_traffic_share_pct=35.0,
        max_unthrottled_burst_multiplier=3.0,
    )
    assert res["evaluated_tenants_count"] == 2
    assert res["noisy_neighbor_or_unisolated_tenant_ids"] == []
    assert res["quota_hog_or_burst_warning_tenant_ids"] == []
    assert (
        res["quota_fairness_status"]
        == "API_MULTI_TENANT_FAIRNESS_OPTIMAL"
    )
    assert res["is_quota_fairness_compliant"] is True


def test_api_quota_fairness_invalid_and_binding():
    import backend.services.project_export_service as mod
    from backend.services.project_export_service import (
        ProjectExportService,
        audit_executive_report_api_quota_fairness_and_noisy_neighbor,
    )

    empty = audit_executive_report_api_quota_fairness_and_noisy_neighbor(None)
    assert empty["evaluated_tenants_count"] == 0
    assert empty["noisy_neighbor_or_unisolated_tenant_ids"] == []
    assert empty["quota_hog_or_burst_warning_tenant_ids"] == []
    assert (
        empty["quota_fairness_status"]
        == "API_MULTI_TENANT_FAIRNESS_OPTIMAL"
    )
    assert empty["is_quota_fairness_compliant"] is True

    invalid = audit_executive_report_api_quota_fairness_and_noisy_neighbor(
        [42, "not-a-dict", None, {"tenant_id": "   "}]  # type: ignore[list-item]
    )
    assert invalid["evaluated_tenants_count"] == 0

    defaults = audit_executive_report_api_quota_fairness_and_noisy_neighbor(
        [
            {
                "tenant_id": "TENANT-DEFAULTS",
                "observed_traffic_share_pct": None,
                "burst_to_steady_rate_multiplier": None,
                "per_tenant_token_bucket_enforced": None,
                "caused_cross_tenant_latency_degradation": None,
                "retry_after_header_compliant": None,
            }
        ]
    )
    assert defaults["evaluated_tenants_count"] == 1
    assert (
        defaults["quota_fairness_status"]
        == "API_MULTI_TENANT_FAIRNESS_OPTIMAL"
    )
    assert defaults["is_quota_fairness_compliant"] is True

    sample = [
        {
            "tenant_id": "TENANT-1",
            "observed_traffic_share_pct": 20.0,
            "burst_to_steady_rate_multiplier": 2.0,
        }
    ]
    assert (
        ProjectExportService.audit_executive_report_api_quota_fairness_and_noisy_neighbor(
            sample
        )
        == audit_executive_report_api_quota_fairness_and_noisy_neighbor(sample)
    )
    assert (
        "audit_executive_report_api_quota_fairness_and_noisy_neighbor"
        in mod.__all__
    )


def test_audit_executive_report_ai_llm_guardrails_and_grounding_breach():
    from backend.services.project_export_service import (
        audit_executive_report_ai_llm_guardrails_and_grounding,
    )

    result = audit_executive_report_ai_llm_guardrails_and_grounding(
        [
            {
                "workload_id": "AI-NO-GUARDRAIL",
                "prompt_injection_and_pii_redaction_active": False,
                "rag_grounding_faithfulness_pct": 95.0,
                "monthly_token_budget_utilization_pct": 50.0,
                "human_in_the_loop_for_high_risk_actions": True,
            },
            {
                "workload_id": "AI-NO-HITL",
                "prompt_injection_and_pii_redaction_active": True,
                "rag_grounding_faithfulness_pct": 95.0,
                "monthly_token_budget_utilization_pct": 50.0,
                "human_in_the_loop_for_high_risk_actions": False,
            },
            {
                "workload_id": "AI-HALLUCINATING",
                "prompt_injection_and_pii_redaction_active": True,
                "rag_grounding_faithfulness_pct": 84.0,
                "monthly_token_budget_utilization_pct": 50.0,
                "human_in_the_loop_for_high_risk_actions": True,
            },
        ],
        min_rag_grounding_faithfulness_pct=92.0,
        max_monthly_token_budget_utilization_pct=90.0,
    )
    assert result["evaluated_workloads_count"] == 3
    assert result["unguarded_or_unfaithful_workload_ids"] == [
        "AI-NO-GUARDRAIL",
        "AI-NO-HITL",
        "AI-HALLUCINATING",
    ]
    assert result["token_budget_pressure_workload_ids"] == []
    assert (
        result["ai_governance_status"]
        == "AI_GUARDRAIL_OR_HALLUCINATION_BREACH"
    )
    assert result["is_ai_governance_compliant"] is False


def test_audit_executive_report_ai_llm_guardrails_and_grounding_warning():
    from backend.services.project_export_service import (
        audit_executive_report_ai_llm_guardrails_and_grounding,
    )

    result = audit_executive_report_ai_llm_guardrails_and_grounding(
        [
            {
                "workload_id": "AI-TOKEN-SPIKE",
                "prompt_injection_and_pii_redaction_active": True,
                "rag_grounding_faithfulness_pct": 95.5,
                "monthly_token_budget_utilization_pct": 96.0,
                "human_in_the_loop_for_high_risk_actions": True,
            }
        ],
        min_rag_grounding_faithfulness_pct=92.0,
        max_monthly_token_budget_utilization_pct=90.0,
    )
    assert result["evaluated_workloads_count"] == 1
    assert result["unguarded_or_unfaithful_workload_ids"] == []
    assert result["token_budget_pressure_workload_ids"] == ["AI-TOKEN-SPIKE"]
    assert (
        result["ai_governance_status"]
        == "AI_TOKEN_BUDGET_EXHAUSTION_WARNING"
    )
    assert result["is_ai_governance_compliant"] is False


def test_audit_executive_report_ai_llm_guardrails_and_grounding_optimal_and_empty():
    from backend.services.project_export_service import (
        audit_executive_report_ai_llm_guardrails_and_grounding,
    )

    empty = audit_executive_report_ai_llm_guardrails_and_grounding(
        [{"workload_id": "   "}, "invalid"]  # type: ignore[list-item]
    )
    assert empty["evaluated_workloads_count"] == 0
    assert empty["ai_governance_status"] == "AI_GOVERNANCE_GROUNDED_OPTIMAL"
    assert empty["is_ai_governance_compliant"] is True

    optimal = audit_executive_report_ai_llm_guardrails_and_grounding(
        [
            {
                "workload_id": "AI-RAG-COPILOT-1",
                "prompt_injection_and_pii_redaction_active": True,
                "rag_grounding_faithfulness_pct": 97.2,
                "monthly_token_budget_utilization_pct": 62.0,
                "human_in_the_loop_for_high_risk_actions": True,
            }
        ],
        min_rag_grounding_faithfulness_pct=92.0,
        max_monthly_token_budget_utilization_pct=90.0,
    )
    assert optimal["evaluated_workloads_count"] == 1
    assert optimal["unguarded_or_unfaithful_workload_ids"] == []
    assert optimal["token_budget_pressure_workload_ids"] == []
    assert optimal["ai_governance_status"] == "AI_GOVERNANCE_GROUNDED_OPTIMAL"
    assert optimal["is_ai_governance_compliant"] is True


def test_audit_executive_report_ai_llm_guardrails_and_grounding_staticmethod_and_dunder_all():
    import backend.services.project_export_service as mod
    from backend.services.project_export_service import (
        ProjectExportService,
        audit_executive_report_ai_llm_guardrails_and_grounding,
    )

    sample = [
        {
            "workload_id": "AI-99",
            "rag_grounding_faithfulness_pct": 95.0,
            "monthly_token_budget_utilization_pct": 55.0,
        }
    ]
    assert (
        ProjectExportService.audit_executive_report_ai_llm_guardrails_and_grounding(
            sample
        )
        == audit_executive_report_ai_llm_guardrails_and_grounding(sample)
    )
    assert (
        "audit_executive_report_ai_llm_guardrails_and_grounding"
        in mod.__all__
    )


def test_audit_executive_report_webhook_dlq_replay_and_hmac_signing_breach():
    from backend.services.project_export_service import (
        audit_executive_report_webhook_dlq_replay_and_hmac_signing,
    )

    result = audit_executive_report_webhook_dlq_replay_and_hmac_signing(
        [
            {
                "endpoint_id": "WH-NO-HMAC",
                "delivery_success_rate_pct": 99.8,
                "dlq_oldest_unreplayed_age_hours": 0.2,
                "hmac_sha256_signature_enforced": False,
                "replay_timestamp_tolerance_enforced": True,
                "exponential_backoff_with_jitter_enabled": True,
            },
            {
                "endpoint_id": "WH-NO-REPLAY-GUARD",
                "delivery_success_rate_pct": 99.8,
                "dlq_oldest_unreplayed_age_hours": 0.2,
                "hmac_sha256_signature_enforced": True,
                "replay_timestamp_tolerance_enforced": False,
                "exponential_backoff_with_jitter_enabled": True,
            },
            {
                "endpoint_id": "WH-STALLED-DLQ",
                "delivery_success_rate_pct": 99.8,
                "dlq_oldest_unreplayed_age_hours": 8.5,
                "hmac_sha256_signature_enforced": True,
                "replay_timestamp_tolerance_enforced": True,
                "exponential_backoff_with_jitter_enabled": True,
            },
        ],
        min_delivery_success_pct=99.5,
        max_dlq_oldest_message_age_hours=4.0,
    )
    assert result["evaluated_endpoints_count"] == 3
    assert result["unsigned_or_dlq_stalled_endpoint_ids"] == [
        "WH-NO-HMAC",
        "WH-NO-REPLAY-GUARD",
        "WH-STALLED-DLQ",
    ]
    assert result["low_delivery_or_missing_jitter_endpoint_ids"] == []
    assert (
        result["webhook_reliability_status"]
        == "WEBHOOK_HMAC_OR_DLQ_STALL_BREACH"
    )
    assert result["is_webhook_reliability_compliant"] is False


def test_audit_executive_report_webhook_dlq_replay_and_hmac_signing_warning():
    from backend.services.project_export_service import (
        audit_executive_report_webhook_dlq_replay_and_hmac_signing,
    )

    result = audit_executive_report_webhook_dlq_replay_and_hmac_signing(
        [
            {
                "endpoint_id": "WH-LOW-SUCCESS",
                "delivery_success_rate_pct": 97.2,
                "dlq_oldest_unreplayed_age_hours": 1.0,
                "hmac_sha256_signature_enforced": True,
                "replay_timestamp_tolerance_enforced": True,
                "exponential_backoff_with_jitter_enabled": True,
            },
            {
                "endpoint_id": "WH-NO-JITTER",
                "delivery_success_rate_pct": 99.9,
                "dlq_oldest_unreplayed_age_hours": 0.5,
                "hmac_sha256_signature_enforced": True,
                "replay_timestamp_tolerance_enforced": True,
                "exponential_backoff_with_jitter_enabled": False,
            },
        ],
        min_delivery_success_pct=99.5,
        max_dlq_oldest_message_age_hours=4.0,
    )
    assert result["evaluated_endpoints_count"] == 2
    assert result["unsigned_or_dlq_stalled_endpoint_ids"] == []
    assert result["low_delivery_or_missing_jitter_endpoint_ids"] == [
        "WH-LOW-SUCCESS",
        "WH-NO-JITTER",
    ]
    assert (
        result["webhook_reliability_status"]
        == "WEBHOOK_DELIVERY_OR_BACKOFF_WARNING"
    )
    assert result["is_webhook_reliability_compliant"] is False


def test_audit_executive_report_webhook_dlq_replay_and_hmac_signing_optimal_and_empty():
    from backend.services.project_export_service import (
        audit_executive_report_webhook_dlq_replay_and_hmac_signing,
    )

    empty = audit_executive_report_webhook_dlq_replay_and_hmac_signing(
        [{"endpoint_id": "   "}, "invalid"]  # type: ignore[list-item]
    )
    assert empty["evaluated_endpoints_count"] == 0
    assert (
        empty["webhook_reliability_status"]
        == "WEBHOOK_DELIVERY_RELIABILITY_OPTIMAL"
    )
    assert empty["is_webhook_reliability_compliant"] is True

    optimal = audit_executive_report_webhook_dlq_replay_and_hmac_signing(
        [
            {
                "endpoint_id": "WH-BILLING-EVENTS-1",
                "delivery_success_rate_pct": 99.95,
                "dlq_oldest_unreplayed_age_hours": 0.25,
                "hmac_sha256_signature_enforced": True,
                "replay_timestamp_tolerance_enforced": True,
                "exponential_backoff_with_jitter_enabled": True,
            }
        ],
        min_delivery_success_pct=99.5,
        max_dlq_oldest_message_age_hours=4.0,
    )
    assert optimal["evaluated_endpoints_count"] == 1
    assert optimal["unsigned_or_dlq_stalled_endpoint_ids"] == []
    assert optimal["low_delivery_or_missing_jitter_endpoint_ids"] == []
    assert (
        optimal["webhook_reliability_status"]
        == "WEBHOOK_DELIVERY_RELIABILITY_OPTIMAL"
    )
    assert optimal["is_webhook_reliability_compliant"] is True


def test_audit_executive_report_webhook_dlq_replay_and_hmac_signing_staticmethod_and_dunder_all():
    import backend.services.project_export_service as mod
    from backend.services.project_export_service import (
        ProjectExportService,
        audit_executive_report_webhook_dlq_replay_and_hmac_signing,
    )

    sample = [
        {
            "endpoint_id": "WH-99",
            "delivery_success_rate_pct": 99.8,
            "dlq_oldest_unreplayed_age_hours": 0.4,
        }
    ]
    assert (
        ProjectExportService.audit_executive_report_webhook_dlq_replay_and_hmac_signing(
            sample
        )
        == audit_executive_report_webhook_dlq_replay_and_hmac_signing(sample)
    )
    assert (
        "audit_executive_report_webhook_dlq_replay_and_hmac_signing"
        in mod.__all__
    )


def test_data_residency_sovereignty_or_scc_breach():
    from backend.services.project_export_service import (
        audit_executive_report_data_residency_and_scc_transfer,
    )

    res = audit_executive_report_data_residency_and_scc_transfer(
        [
            {
                "transfer_id": "XF-NO-SCC-STALE",
                "is_cross_border_transfer": True,
                "scc_and_tia_signed": False,
                "tia_review_age_days": 370,
            },
            {
                "transfer_id": "XF-NO-BYOK",
                "sovereign_encryption_byok_active": False,
            },
        ],
        require_scc_and_tia_for_cross_border=True,
        max_tia_review_age_days=180,
    )
    assert res["evaluated_transfers_count"] == 2
    assert res["unlawful_transfer_or_unencrypted_sovereignty_transfer_ids"] == [
        "XF-NO-SCC-STALE",
        "XF-NO-BYOK",
    ]
    assert res["stale_tia_or_unnotified_subprocessor_transfer_ids"] == [
        "XF-NO-SCC-STALE"
    ]
    assert (
        res["data_residency_status"]
        == "DATA_RESIDENCY_SOVEREIGNTY_OR_SCC_BREACH"
    )
    assert res["is_data_residency_compliant"] is False

    unenforced = audit_executive_report_data_residency_and_scc_transfer(
        [
            {
                "transfer_id": "XF-SCC-FLAG-OFF",
                "is_cross_border_transfer": True,
                "scc_and_tia_signed": False,
            }
        ],
        require_scc_and_tia_for_cross_border=False,
        max_tia_review_age_days=180,
    )
    assert (
        unenforced["unlawful_transfer_or_unencrypted_sovereignty_transfer_ids"]
        == []
    )


def test_data_residency_tia_aging_or_subprocessor_warning():
    from backend.services.project_export_service import (
        audit_executive_report_data_residency_and_scc_transfer,
    )

    res = audit_executive_report_data_residency_and_scc_transfer(
        [
            {
                "transfer_id": "XF-STALE-TIA",
                "is_cross_border_transfer": True,
                "tia_review_age_days": 200,
            },
            {
                "transfer_id": "XF-UNNOTIFIED-PROC",
                "is_cross_border_transfer": False,
                "subprocessor_notified": False,
            },
        ],
        require_scc_and_tia_for_cross_border=True,
        max_tia_review_age_days=180,
    )
    assert res["evaluated_transfers_count"] == 2
    assert res["unlawful_transfer_or_unencrypted_sovereignty_transfer_ids"] == []
    assert res["stale_tia_or_unnotified_subprocessor_transfer_ids"] == [
        "XF-STALE-TIA",
        "XF-UNNOTIFIED-PROC",
    ]
    assert (
        res["data_residency_status"]
        == "DATA_RESIDENCY_TIA_AGING_OR_SUBPROCESSOR_WARNING"
    )
    assert res["is_data_residency_compliant"] is False


def test_data_residency_boundaries_and_defaults_optimal():
    from backend.services.project_export_service import (
        audit_executive_report_data_residency_and_scc_transfer,
    )

    res = audit_executive_report_data_residency_and_scc_transfer(
        [
            {
                "transfer_id": "XF-BOUNDARY",
                "is_cross_border_transfer": True,
                "tia_review_age_days": 180,
            },
            {"transfer_id": "XF-ALL-DEFAULTS"},
        ],
        require_scc_and_tia_for_cross_border=True,
        max_tia_review_age_days=180,
    )
    assert res["evaluated_transfers_count"] == 2
    assert res["unlawful_transfer_or_unencrypted_sovereignty_transfer_ids"] == []
    assert res["stale_tia_or_unnotified_subprocessor_transfer_ids"] == []
    assert (
        res["data_residency_status"] == "DATA_RESIDENCY_SOVEREIGNTY_OPTIMAL"
    )
    assert res["is_data_residency_compliant"] is True


def test_data_residency_invalid_and_binding():
    import backend.services.project_export_service as mod
    from backend.services.project_export_service import (
        ProjectExportService,
        audit_executive_report_data_residency_and_scc_transfer,
    )

    empty = audit_executive_report_data_residency_and_scc_transfer(None)
    assert empty["evaluated_transfers_count"] == 0
    assert empty["unlawful_transfer_or_unencrypted_sovereignty_transfer_ids"] == []
    assert empty["stale_tia_or_unnotified_subprocessor_transfer_ids"] == []
    assert (
        empty["data_residency_status"]
        == "DATA_RESIDENCY_SOVEREIGNTY_OPTIMAL"
    )
    assert empty["is_data_residency_compliant"] is True

    invalid = audit_executive_report_data_residency_and_scc_transfer(
        [42, "not-a-dict", None, {"transfer_id": "   "}]  # type: ignore[list-item]
    )
    assert invalid["evaluated_transfers_count"] == 0

    defaults = audit_executive_report_data_residency_and_scc_transfer(
        [
            {
                "transfer_id": "XF-DEFAULTS",
                "is_cross_border_transfer": None,
                "scc_and_tia_signed": None,
                "sovereign_encryption_byok_active": None,
                "tia_review_age_days": None,
                "subprocessor_notified": None,
            }
        ]
    )
    assert defaults["evaluated_transfers_count"] == 1
    assert (
        defaults["data_residency_status"]
        == "DATA_RESIDENCY_SOVEREIGNTY_OPTIMAL"
    )
    assert defaults["is_data_residency_compliant"] is True

    sample = [
        {
            "transfer_id": "XF-1",
            "tia_review_age_days": 30,
        }
    ]
    assert (
        ProjectExportService.audit_executive_report_data_residency_and_scc_transfer(
            sample
        )
        == audit_executive_report_data_residency_and_scc_transfer(sample)
    )
    assert (
        "audit_executive_report_data_residency_and_scc_transfer"
        in mod.__all__
    )


def test_audit_executive_report_accessibility_wcag_aa_contrast_and_screen_reader_parity_breach():
    from backend.services.project_export_service import (
        audit_executive_report_accessibility_wcag_aa_contrast_and_screen_reader_parity,
    )

    res = audit_executive_report_accessibility_wcag_aa_contrast_and_screen_reader_parity(
        [
            {
                "artifact_id": "  PDF-BOARD-Q1  ",
                "pdf_ua_tagged_structure_valid": False,
                "all_charts_have_alt_text": True,
                "min_observed_contrast_ratio": 7.5,
                "colorblind_safe_palette_used": True,
            },
            {
                "artifact_id": "DECK-EXEC-Q2",
                "pdf_ua_tagged_structure_valid": True,
                "all_charts_have_alt_text": False,
                "min_observed_contrast_ratio": 3.2,
                "colorblind_safe_palette_used": False,
            },
            {
                "artifact_id": "PDF-CLEAN",
                "pdf_ua_tagged_structure_valid": True,
                "all_charts_have_alt_text": True,
                "min_observed_contrast_ratio": 4.5,
                "colorblind_safe_palette_used": True,
            },
        ]
    )
    assert res["evaluated_artifacts_count"] == 3
    assert res["untagged_or_missing_alt_text_artifact_ids"] == [
        "PDF-BOARD-Q1",
        "DECK-EXEC-Q2",
    ]
    assert res["low_contrast_or_non_colorblind_artifact_ids"] == [
        "DECK-EXEC-Q2"
    ]
    assert (
        res["accessibility_wcag_status"]
        == "ACCESSIBILITY_PDFUA_OR_ALT_TEXT_BREACH"
    )
    assert res["is_accessibility_wcag_compliant"] is False


def test_audit_executive_report_accessibility_wcag_aa_contrast_and_screen_reader_parity_warning():
    from backend.services.project_export_service import (
        audit_executive_report_accessibility_wcag_aa_contrast_and_screen_reader_parity,
    )

    res = audit_executive_report_accessibility_wcag_aa_contrast_and_screen_reader_parity(
        [
            {
                "artifact_id": "PDF-LOW-CONTRAST",
                "pdf_ua_tagged_structure_valid": True,
                "all_charts_have_alt_text": True,
                "min_observed_contrast_ratio": 4.4,
                "colorblind_safe_palette_used": True,
            },
            {
                "artifact_id": "PDF-BAD-PALETTE",
                "pdf_ua_tagged_structure_valid": False,
                "all_charts_have_alt_text": False,
                "min_observed_contrast_ratio": 4.5,
                "colorblind_safe_palette_used": False,
            },
        ],
        min_contrast_ratio=4.5,
        require_tagged_pdf_and_alt_text=False,
    )
    assert res["evaluated_artifacts_count"] == 2
    assert res["untagged_or_missing_alt_text_artifact_ids"] == []
    assert res["low_contrast_or_non_colorblind_artifact_ids"] == [
        "PDF-LOW-CONTRAST",
        "PDF-BAD-PALETTE",
    ]
    assert (
        res["accessibility_wcag_status"]
        == "ACCESSIBILITY_CONTRAST_OR_PALETTE_WARNING"
    )
    assert res["is_accessibility_wcag_compliant"] is False


def test_audit_executive_report_accessibility_wcag_aa_contrast_and_screen_reader_parity_optimal_and_defensive():
    from backend.services.project_export_service import (
        audit_executive_report_accessibility_wcag_aa_contrast_and_screen_reader_parity,
    )

    empty = audit_executive_report_accessibility_wcag_aa_contrast_and_screen_reader_parity(
        None
    )
    assert empty["evaluated_artifacts_count"] == 0
    assert empty["untagged_or_missing_alt_text_artifact_ids"] == []
    assert empty["low_contrast_or_non_colorblind_artifact_ids"] == []
    assert empty["accessibility_wcag_status"] == "ACCESSIBILITY_WCAG_AA_OPTIMAL"
    assert empty["is_accessibility_wcag_compliant"] is True

    optimal = audit_executive_report_accessibility_wcag_aa_contrast_and_screen_reader_parity(
        [
            "not-a-dict",  # type: ignore[list-item]
            {"artifact_id": "   "},
            {
                "artifact_id": "PDF-DEFAULTS",
                "pdf_ua_tagged_structure_valid": None,
                "all_charts_have_alt_text": None,
                "min_observed_contrast_ratio": None,
                "colorblind_safe_palette_used": None,
            },
        ]
    )
    assert optimal["evaluated_artifacts_count"] == 1
    assert optimal["untagged_or_missing_alt_text_artifact_ids"] == []
    assert optimal["low_contrast_or_non_colorblind_artifact_ids"] == []
    assert (
        optimal["accessibility_wcag_status"] == "ACCESSIBILITY_WCAG_AA_OPTIMAL"
    )
    assert optimal["is_accessibility_wcag_compliant"] is True


def test_audit_executive_report_accessibility_wcag_aa_contrast_and_screen_reader_parity_staticmethod_and_dunder_all():
    import backend.services.project_export_service as mod
    from backend.services.project_export_service import (
        ProjectExportService,
        audit_executive_report_accessibility_wcag_aa_contrast_and_screen_reader_parity,
    )

    sample = [
        {
            "artifact_id": "PDF-99",
            "min_observed_contrast_ratio": 7.1,
        }
    ]
    assert (
        ProjectExportService.audit_executive_report_accessibility_wcag_aa_contrast_and_screen_reader_parity(
            sample
        )
        == audit_executive_report_accessibility_wcag_aa_contrast_and_screen_reader_parity(
            sample
        )
    )
    assert (
        "audit_executive_report_accessibility_wcag_aa_contrast_and_screen_reader_parity"
        in mod.__all__
    )


def test_audit_executive_report_idempotency_key_and_replay_window_breach():
    from backend.services.project_export_service import (
        audit_executive_report_idempotency_key_and_replay_window,
    )

    result = audit_executive_report_idempotency_key_and_replay_window(
        [
            {
                "endpoint_id": "EP-NO-KEY",
                "idempotency_key_enforced": False,
                "payload_fingerprint_mismatch_rejected": True,
                "idempotency_ttl_hours": 48,
                "concurrent_in_flight_lock_active": True,
            },
            {
                "endpoint_id": "EP-NO-HASH-CHECK",
                "idempotency_key_enforced": True,
                "payload_fingerprint_mismatch_rejected": False,
                "idempotency_ttl_hours": 48,
                "concurrent_in_flight_lock_active": True,
            },
        ],
        min_idempotency_ttl_hours=24,
        require_payload_hash_validation=True,
    )
    assert result["evaluated_endpoints_count"] == 2
    assert result["duplicate_mutation_or_unhashed_endpoint_ids"] == [
        "EP-NO-KEY",
        "EP-NO-HASH-CHECK",
    ]
    assert result["short_ttl_or_missing_inflight_lock_endpoint_ids"] == []
    assert (
        result["idempotency_gate_status"]
        == "IDEMPOTENCY_DEDUPLICATION_OR_HASH_BREACH"
    )
    assert result["is_idempotency_gate_compliant"] is False


def test_audit_executive_report_idempotency_key_and_replay_window_warning():
    from backend.services.project_export_service import (
        audit_executive_report_idempotency_key_and_replay_window,
    )

    result = audit_executive_report_idempotency_key_and_replay_window(
        [
            {
                "endpoint_id": "EP-SHORT-TTL",
                "idempotency_key_enforced": True,
                "payload_fingerprint_mismatch_rejected": True,
                "idempotency_ttl_hours": 6,
                "concurrent_in_flight_lock_active": True,
            },
            {
                "endpoint_id": "EP-NO-INFLIGHT-LOCK",
                "idempotency_key_enforced": True,
                "payload_fingerprint_mismatch_rejected": False,
                "idempotency_ttl_hours": 48,
                "concurrent_in_flight_lock_active": False,
            },
        ],
        min_idempotency_ttl_hours=24,
        require_payload_hash_validation=False,
    )
    assert result["evaluated_endpoints_count"] == 2
    assert result["duplicate_mutation_or_unhashed_endpoint_ids"] == []
    assert result["short_ttl_or_missing_inflight_lock_endpoint_ids"] == [
        "EP-SHORT-TTL",
        "EP-NO-INFLIGHT-LOCK",
    ]
    assert (
        result["idempotency_gate_status"]
        == "IDEMPOTENCY_TTL_OR_INFLIGHT_LOCK_WARNING"
    )
    assert result["is_idempotency_gate_compliant"] is False


def test_audit_executive_report_idempotency_key_and_replay_window_optimal_and_empty():
    from backend.services.project_export_service import (
        audit_executive_report_idempotency_key_and_replay_window,
    )

    empty = audit_executive_report_idempotency_key_and_replay_window(
        [{"endpoint_id": "   "}, "invalid"]  # type: ignore[list-item]
    )
    assert empty["evaluated_endpoints_count"] == 0
    assert (
        empty["idempotency_gate_status"]
        == "IDEMPOTENCY_REPLAY_PROTECTION_OPTIMAL"
    )
    assert empty["is_idempotency_gate_compliant"] is True

    optimal = audit_executive_report_idempotency_key_and_replay_window(
        [
            {
                "endpoint_id": "EP-PAYMENTS-POST",
                "idempotency_key_enforced": True,
                "payload_fingerprint_mismatch_rejected": True,
                "idempotency_ttl_hours": 48,
                "concurrent_in_flight_lock_active": True,
            }
        ],
        min_idempotency_ttl_hours=24,
        require_payload_hash_validation=True,
    )
    assert optimal["evaluated_endpoints_count"] == 1
    assert optimal["duplicate_mutation_or_unhashed_endpoint_ids"] == []
    assert optimal["short_ttl_or_missing_inflight_lock_endpoint_ids"] == []
    assert (
        optimal["idempotency_gate_status"]
        == "IDEMPOTENCY_REPLAY_PROTECTION_OPTIMAL"
    )
    assert optimal["is_idempotency_gate_compliant"] is True


def test_audit_executive_report_idempotency_key_and_replay_window_staticmethod_and_dunder_all():
    import backend.services.project_export_service as mod
    from backend.services.project_export_service import (
        ProjectExportService,
        audit_executive_report_idempotency_key_and_replay_window,
    )

    sample = [
        {
            "endpoint_id": "EP-99",
            "idempotency_ttl_hours": 72,
        }
    ]
    assert (
        ProjectExportService.audit_executive_report_idempotency_key_and_replay_window(
            sample
        )
        == audit_executive_report_idempotency_key_and_replay_window(sample)
    )
    assert (
        "audit_executive_report_idempotency_key_and_replay_window"
        in mod.__all__
    )


def test_rfc3161_tsa_or_hash_chain_breach():
    from backend.services.project_export_service import (
        audit_executive_report_rfc3161_timestamping_and_non_repudiation,
    )

    res = audit_executive_report_rfc3161_timestamping_and_non_repudiation(
        [
            {
                "package_id": "PKG-NO-TSA",
                "rfc3161_tsa_token_verified": False,
            },
            {
                "package_id": "PKG-BROKEN-CHAIN",
                "merkle_hash_chain_intact": False,
            },
        ],
        max_tsa_clock_skew_ms=500,
        require_ocsp_stapling_and_ltv=True,
    )
    assert res["evaluated_packages_count"] == 2
    assert res["broken_hash_or_missing_tsa_package_ids"] == [
        "PKG-NO-TSA",
        "PKG-BROKEN-CHAIN",
    ]
    assert res["missing_ltv_or_clock_skew_package_ids"] == []
    assert (
        res["non_repudiation_status"]
        == "NON_REPUDIATION_TSA_OR_HASH_CHAIN_BREACH"
    )
    assert res["is_non_repudiation_compliant"] is False

    ltv_optional = audit_executive_report_rfc3161_timestamping_and_non_repudiation(
        [
            {
                "package_id": "PKG-LTV-OFF",
                "ocsp_ltv_embedded": False,
            }
        ],
        max_tsa_clock_skew_ms=500,
        require_ocsp_stapling_and_ltv=False,
    )
    assert ltv_optional["missing_ltv_or_clock_skew_package_ids"] == []


def test_rfc3161_ltv_or_clock_skew_warning():
    from backend.services.project_export_service import (
        audit_executive_report_rfc3161_timestamping_and_non_repudiation,
    )

    res = audit_executive_report_rfc3161_timestamping_and_non_repudiation(
        [
            {
                "package_id": "PKG-NO-LTV",
                "ocsp_ltv_embedded": False,
            },
            {
                "package_id": "PKG-SKEW-DRIFT",
                "tsa_clock_skew_ms": 900,
            },
        ],
        max_tsa_clock_skew_ms=500,
        require_ocsp_stapling_and_ltv=True,
    )
    assert res["evaluated_packages_count"] == 2
    assert res["broken_hash_or_missing_tsa_package_ids"] == []
    assert res["missing_ltv_or_clock_skew_package_ids"] == [
        "PKG-NO-LTV",
        "PKG-SKEW-DRIFT",
    ]
    assert (
        res["non_repudiation_status"]
        == "NON_REPUDIATION_LTV_OR_CLOCK_SKEW_WARNING"
    )
    assert res["is_non_repudiation_compliant"] is False


def test_rfc3161_boundaries_optimal_and_defaults():
    from backend.services.project_export_service import (
        audit_executive_report_rfc3161_timestamping_and_non_repudiation,
    )

    res = audit_executive_report_rfc3161_timestamping_and_non_repudiation(
        [
            {
                "package_id": "PKG-BOUNDARY",
                "tsa_clock_skew_ms": 500,
            },
            {"package_id": "PKG-ALL-DEFAULTS"},
        ],
        max_tsa_clock_skew_ms=500,
        require_ocsp_stapling_and_ltv=True,
    )
    assert res["evaluated_packages_count"] == 2
    assert res["broken_hash_or_missing_tsa_package_ids"] == []
    assert res["missing_ltv_or_clock_skew_package_ids"] == []
    assert (
        res["non_repudiation_status"]
        == "NON_REPUDIATION_RFC3161_SEAL_OPTIMAL"
    )
    assert res["is_non_repudiation_compliant"] is True


def test_rfc3161_invalid_and_binding():
    import backend.services.project_export_service as mod
    from backend.services.project_export_service import (
        ProjectExportService,
        audit_executive_report_rfc3161_timestamping_and_non_repudiation,
    )

    empty = audit_executive_report_rfc3161_timestamping_and_non_repudiation(
        None
    )
    assert empty["evaluated_packages_count"] == 0
    assert empty["broken_hash_or_missing_tsa_package_ids"] == []
    assert empty["missing_ltv_or_clock_skew_package_ids"] == []
    assert (
        empty["non_repudiation_status"]
        == "NON_REPUDIATION_RFC3161_SEAL_OPTIMAL"
    )
    assert empty["is_non_repudiation_compliant"] is True

    invalid = audit_executive_report_rfc3161_timestamping_and_non_repudiation(
        [42, "not-a-dict", None, {"package_id": "   "}]  # type: ignore[list-item]
    )
    assert invalid["evaluated_packages_count"] == 0

    defaults = audit_executive_report_rfc3161_timestamping_and_non_repudiation(
        [
            {
                "package_id": "PKG-DEFAULTS",
                "rfc3161_tsa_token_verified": None,
                "merkle_hash_chain_intact": None,
                "ocsp_ltv_embedded": None,
                "tsa_clock_skew_ms": None,
            }
        ]
    )
    assert defaults["evaluated_packages_count"] == 1
    assert (
        defaults["non_repudiation_status"]
        == "NON_REPUDIATION_RFC3161_SEAL_OPTIMAL"
    )
    assert defaults["is_non_repudiation_compliant"] is True

    sample = [
        {
            "package_id": "PKG-1",
            "tsa_clock_skew_ms": 60,
        }
    ]
    assert (
        ProjectExportService.audit_executive_report_rfc3161_timestamping_and_non_repudiation(
            sample
        )
        == audit_executive_report_rfc3161_timestamping_and_non_repudiation(
            sample
        )
    )
    assert (
        "audit_executive_report_rfc3161_timestamping_and_non_repudiation"
        in mod.__all__
    )


def test_audit_executive_report_siem_log_forwarding_and_retention_breach():
    from backend.services.project_export_service import (
        audit_executive_report_siem_log_forwarding_and_retention,
    )

    res = audit_executive_report_siem_log_forwarding_and_retention(
        [
            {
                "stream_id": "  SIEM-NO-HMAC  ",
                "tamper_evident_hmac_chaining_enabled": False,
                "pii_tokenization_before_ingest": True,
                "siem_ingestion_lag_seconds": 8,
                "hot_retention_days": 180,
            },
            {
                "stream_id": "SIEM-PII-LEAK",
                "tamper_evident_hmac_chaining_enabled": True,
                "pii_tokenization_before_ingest": False,
                "siem_ingestion_lag_seconds": 45,
                "hot_retention_days": 30,
            },
            {
                "stream_id": "SIEM-CLEAN",
                "tamper_evident_hmac_chaining_enabled": True,
                "pii_tokenization_before_ingest": True,
                "siem_ingestion_lag_seconds": 30,
                "hot_retention_days": 90,
            },
        ]
    )
    assert res["evaluated_streams_count"] == 3
    assert res["unhashed_or_unmasked_pii_stream_ids"] == [
        "SIEM-NO-HMAC",
        "SIEM-PII-LEAK",
    ]
    assert res["high_lag_or_short_retention_stream_ids"] == ["SIEM-PII-LEAK"]
    assert (
        res["siem_audit_status"] == "SIEM_TAMPER_CHAIN_OR_PII_MASKING_BREACH"
    )
    assert res["is_siem_audit_compliant"] is False


def test_audit_executive_report_siem_log_forwarding_and_retention_warning():
    from backend.services.project_export_service import (
        audit_executive_report_siem_log_forwarding_and_retention,
    )

    res = audit_executive_report_siem_log_forwarding_and_retention(
        [
            {
                "stream_id": "SIEM-HIGH-LAG",
                "tamper_evident_hmac_chaining_enabled": True,
                "pii_tokenization_before_ingest": True,
                "siem_ingestion_lag_seconds": 31,
                "hot_retention_days": 90,
            },
            {
                "stream_id": "SIEM-SHORT-RET",
                "tamper_evident_hmac_chaining_enabled": True,
                "pii_tokenization_before_ingest": True,
                "siem_ingestion_lag_seconds": 30,
                "hot_retention_days": 89,
            },
        ],
        max_siem_ingestion_lag_seconds=30,
        min_hot_retention_days=90,
    )
    assert res["evaluated_streams_count"] == 2
    assert res["unhashed_or_unmasked_pii_stream_ids"] == []
    assert res["high_lag_or_short_retention_stream_ids"] == [
        "SIEM-HIGH-LAG",
        "SIEM-SHORT-RET",
    ]
    assert (
        res["siem_audit_status"]
        == "SIEM_INGESTION_LAG_OR_RETENTION_WARNING"
    )
    assert res["is_siem_audit_compliant"] is False


def test_audit_executive_report_siem_log_forwarding_and_retention_optimal_and_defensive():
    from backend.services.project_export_service import (
        audit_executive_report_siem_log_forwarding_and_retention,
    )

    empty = audit_executive_report_siem_log_forwarding_and_retention(None)
    assert empty["evaluated_streams_count"] == 0
    assert empty["siem_audit_status"] == "SIEM_TELEMETRY_PIPELINE_OPTIMAL"
    assert empty["is_siem_audit_compliant"] is True

    defaults = audit_executive_report_siem_log_forwarding_and_retention(
        [
            "not-a-dict",  # type: ignore[list-item]
            {"stream_id": "   "},
            {
                "stream_id": "SIEM-DEFAULTS",
                "tamper_evident_hmac_chaining_enabled": None,
                "pii_tokenization_before_ingest": None,
                "siem_ingestion_lag_seconds": None,
                "hot_retention_days": None,
            },
        ]
    )
    assert defaults["evaluated_streams_count"] == 1
    assert defaults["siem_audit_status"] == "SIEM_TELEMETRY_PIPELINE_OPTIMAL"
    assert defaults["is_siem_audit_compliant"] is True


def test_audit_executive_report_siem_log_forwarding_and_retention_staticmethod_and_dunder_all():
    import backend.services.project_export_service as mod
    from backend.services.project_export_service import (
        ProjectExportService,
        audit_executive_report_siem_log_forwarding_and_retention,
    )

    sample = [{"stream_id": "SIEM-99", "siem_ingestion_lag_seconds": 5}]
    assert (
        ProjectExportService.audit_executive_report_siem_log_forwarding_and_retention(
            sample
        )
        == audit_executive_report_siem_log_forwarding_and_retention(sample)
    )
    assert (
        "audit_executive_report_siem_log_forwarding_and_retention"
        in mod.__all__
    )

