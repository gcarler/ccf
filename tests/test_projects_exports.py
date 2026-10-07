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
