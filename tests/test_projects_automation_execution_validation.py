"""Regression tests for honest automation execution results."""

import pytest

from backend.models_projects import ProjectAutomationRule
from tests.conftest import auth_headers, seed_admin
from tests.factories_projects import create_project_factory, create_task_factory


@pytest.mark.parametrize(
    ("action_type", "action_data", "expected_detail"),
    [
        ("unknown_action", {}, "Acción no soportada"),
        ("reassign_task", {}, "requiere assignee_id"),
        ("change_phase", {}, "requiere phase_name o node"),
        ("set_priority", {"priority": ["urgent"]}, "prioridad de destino no es válida"),
        (
            "create_followup_task",
            {"priority": "impossible"},
            "prioridad de la tarea de seguimiento no es válida",
        ),
    ],
)
def test_invalid_automation_configuration_fails_without_counting_execution(
    client, db_session, action_type, action_data, expected_detail
):
    _, _, sede = seed_admin(db_session)
    project = create_project_factory(db_session, sede_id=sede.id)
    task = create_task_factory(db_session, project.id, status="completed", priority="medium")
    rule = ProjectAutomationRule(
        project_id=project.id,
        sede_id=sede.id,
        name="Configuración no ejecutable",
        trigger_event="task_completed",
        condition_data={},
        action_type=action_type,
        action_data=action_data,
        is_active=True,
    )
    db_session.add(rule)
    db_session.commit()

    response = client.post(
        f"/api/projects/{project.id}/automations/evaluate",
        json={"trigger_event": "task_completed", "task_id": str(task.id), "dry_run": False},
        headers=auth_headers(client),
    )

    assert response.status_code == 200, response.text
    result = response.json()[0]
    assert result["status"] == "failed"
    assert expected_detail in result["details"]
    db_session.refresh(rule)
    db_session.refresh(task)
    assert rule.execution_count == 0
    assert rule.last_triggered_at is None
    assert task.priority == "medium"
