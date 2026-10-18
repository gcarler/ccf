"""Regression tests for honest automation execution results."""

import pytest

from backend.models_projects import ProjectAutomationRule
from backend.services.project_lifecycle_pmi_service import (
    ProjectLifecyclePMIService,
    evaluate_automation_governance_readiness,
)
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


def test_automation_governance_readiness_optimal_active_rules():
    rules = [
        {
            "action_type": "reassign_task",
            "action_data": {"assignee_id": "11111111-2222-3333-4444-555555555555"},
            "is_active": True,
            "execution_count": 4,
        },
        {
            "action_type": "change_phase",
            "action_data": {"phase_name": "Ejecución"},
            "is_active": True,
            "execution_count": 7,
        },
        {
            "action_type": "set_priority",
            "action_data": {"priority": "urgent"},
            "is_active": True,
            "execution_count": 2,
        },
        {
            "action_type": "create_followup_task",
            "action_data": {"title": "QA Review", "priority": "high"},
            "is_active": True,
            "execution_count": 5,
        },
    ]
    res = evaluate_automation_governance_readiness(rules)
    assert res == {
        "total_rules": 4,
        "active_rules": 4,
        "valid_active_rules": 4,
        "misconfigured_active_rules": 0,
        "total_executions": 18,
        "readiness_pct": 100.0,
        "governance_status": "optimal",
    }


def test_automation_governance_readiness_warning_and_critical_mixed_rules():
    warning_rules = [
        {
            "action_type": "set_priority",
            "action_data": {"priority": "high"},
            "is_active": True,
            "execution_count": 3,
        },
        {
            "action_type": "notify_channel",
            "action_data": {"channel": "pmo"},
            "is_active": True,
            "execution_count": 1,
        },
        {
            "action_type": "reassign_task",
            "action_data": {"assignee_id": "   "},
            "is_active": True,
            "execution_count": 0,
        },
    ]
    warn_res = evaluate_automation_governance_readiness(warning_rules)
    assert warn_res["total_rules"] == 3
    assert warn_res["active_rules"] == 3
    assert warn_res["valid_active_rules"] == 2
    assert warn_res["misconfigured_active_rules"] == 1
    assert warn_res["readiness_pct"] == 66.67
    assert warn_res["governance_status"] == "warning"

    critical_rules = [
        {
            "action_type": "unknown_action",
            "action_data": {},
            "is_active": True,
            "execution_count": 0,
        },
        {
            "action_type": "change_phase",
            "action_data": {},
            "is_active": True,
            "execution_count": 0,
        },
        {
            "action_type": "create_followup_task",
            "action_data": {"priority": "impossible"},
            "is_active": True,
            "execution_count": 0,
        },
        {
            "action_type": "notify_assignee",
            "action_data": {},
            "is_active": True,
            "execution_count": 2,
        },
    ]
    crit_res = ProjectLifecyclePMIService.evaluate_automation_governance_readiness(critical_rules)
    assert crit_res["active_rules"] == 4
    assert crit_res["valid_active_rules"] == 1
    assert crit_res["misconfigured_active_rules"] == 3
    assert crit_res["readiness_pct"] == 25.0
    assert crit_res["governance_status"] == "critical"


def test_automation_governance_readiness_inactive_misconfigured_rules_ignored():
    rules = [
        {
            "action_type": "set_priority",
            "action_data": {"priority": "medium"},
            "is_active": True,
            "execution_count": 6,
        },
        {
            "action_type": "reassign_task",
            "action_data": {},
            "is_active": False,
            "execution_count": 10,
        },
        {
            "action_type": "unsupported_action",
            "action_data": None,
            "is_active": False,
            "execution_count": 0,
        },
    ]
    res = evaluate_automation_governance_readiness(rules)
    assert res["total_rules"] == 3
    assert res["active_rules"] == 1
    assert res["valid_active_rules"] == 1
    assert res["misconfigured_active_rules"] == 0
    assert res["total_executions"] == 16
    assert res["readiness_pct"] == 100.0
    assert res["governance_status"] == "optimal"


def test_automation_governance_readiness_empty_or_none_idle():
    empty_res = evaluate_automation_governance_readiness([])
    assert empty_res == {
        "total_rules": 0,
        "active_rules": 0,
        "valid_active_rules": 0,
        "misconfigured_active_rules": 0,
        "total_executions": 0,
        "readiness_pct": 100.0,
        "governance_status": "idle",
    }

    none_res = evaluate_automation_governance_readiness(None)
    assert none_res["governance_status"] == "idle"
    assert none_res["readiness_pct"] == 100.0

