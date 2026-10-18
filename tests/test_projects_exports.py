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

