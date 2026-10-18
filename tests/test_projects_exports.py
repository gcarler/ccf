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


