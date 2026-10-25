"""Numerical regression oracles for project indicator consolidation (H02/H04/H05)."""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from backend import models
from backend.services import project_evm_service as evm

NOW = datetime(2026, 10, 24, tzinfo=timezone.utc)


def make_project(db):
    row = models.Project(id=uuid4(), title="Indicator core integrity", budget_allocated=1000,
                         budget_spent=0, progress_mode="auto_tasks", start_date=NOW-timedelta(days=10),
                         target_date=NOW+timedelta(days=10))
    db.add(row)
    db.flush()
    return row


@pytest.mark.parametrize("empty_budget", [900, 0])
def test_empty_components_remain_in_budget_denominator(db_session, empty_budget):
    project = make_project(db_session)
    completed = models.ProjectComponent(id=uuid4(), project_id=project.id, code="1", name="Complete", budget_allocated=100)
    empty = models.ProjectComponent(id=uuid4(), project_id=project.id, code="2", name="Empty", budget_allocated=empty_budget)
    db_session.add_all([completed, empty])
    db_session.flush()
    db_session.add(models.ProjectTask(id=uuid4(), project_id=project.id, component_id=completed.id,
                                     title="Completed work", status="completed", estimated_hours=10,
                                     physical_progress_pct=100, due_date=NOW))
    db_session.commit()
    result = evm.calculate_project_evm(db_session, project, now=NOW)
    expected_pct = 10 if empty_budget == 900 else 100
    assert result["progress_percentage"] == expected_pct
    assert result["ev"] == 1000 * expected_pct / 100
    if empty_budget == 900:
        assert sum(evm.calculate_component_evm(db_session, component, now=NOW)["ev"]
                   for component in (completed, empty)) == result["ev"]


@pytest.mark.parametrize("component_budgets", [(900, 100), (100, 900)])
def test_earned_hours_do_not_follow_component_money_weights(db_session, component_budgets):
    project = make_project(db_session)
    components = [models.ProjectComponent(id=uuid4(), project_id=project.id, code=str(i), name=str(i), budget_allocated=budget)
                  for i, budget in enumerate(component_budgets)]
    db_session.add_all(components)
    db_session.flush()
    for component, hours, pct in zip(components, [10, 90], [100, 0]):
        db_session.add(models.ProjectTask(id=uuid4(), project_id=project.id, component_id=component.id,
                                         title="Leaf", estimated_hours=hours, physical_progress_pct=pct,
                                         status="completed" if pct == 100 else "todo"))
    db_session.commit()
    result = evm.build_project_execution_matrix(db_session, project, now=NOW)
    assert result["frente_tiempo"]["total_estimated_hours"] == 100
    assert result["frente_tiempo"]["earned_hours"] == 10
    assert result["frente_tiempo"]["time_progress_pct"] == component_budgets[0] / 10


def test_effort_counts_leaf_scope_once_and_includes_parent_actual_hours(db_session):
    from tests.conftest import seed_admin
    _, person, _ = seed_admin(db_session, email="leaf-effort-integrity@example.com")
    project = make_project(db_session)
    component = models.ProjectComponent(id=uuid4(), project_id=project.id, code="1", name="Scope", budget_allocated=1000)
    db_session.add(component)
    db_session.flush()
    parent = models.ProjectTask(id=uuid4(), project_id=project.id, component_id=component.id,
                                title="Container", estimated_hours=100, physical_progress_pct=90, status="in_progress")
    db_session.add(parent)
    db_session.flush()
    db_session.add_all([
        models.ProjectTask(id=uuid4(), project_id=project.id, component_id=component.id, parent_id=parent.id,
                           title="Completed 10h", estimated_hours=10, physical_progress_pct=100, status="completed"),
        models.ProjectTask(id=uuid4(), project_id=project.id, component_id=component.id, parent_id=parent.id,
                           title="Pending 90h", estimated_hours=90, physical_progress_pct=0, status="todo"),
        models.ProjectTimeLog(project_id=project.id, task_id=parent.id, persona_id=person.id, hours=20, date=NOW),
    ])
    db_session.commit()
    matrix = evm.build_project_execution_matrix(db_session, project, now=NOW)
    effort = matrix["frente_tiempo"]
    assert effort["total_estimated_hours"] == 100
    assert effort["earned_hours"] == 10
    assert effort["actual_hours"] == 20
    assert effort["hours_efficiency_pct"] == 50
    component_effort = matrix["rollup_hierarchy"]["components"][0]
    assert component_effort["estimated_hours"] == 100
    assert component_effort["actual_hours"] == 20
    assert component_effort["hours_efficiency_pct"] == 50


@pytest.mark.parametrize("planned_hours,physical_pct,status", [(100, 20, "todo"), (0, 30, "in_progress"), (100, 100, "completed")])
def test_time_log_lifecycle_preserves_physical_measurement(db_session, planned_hours, physical_pct, status):
    from backend import schemas
    from backend.crud import projects as crud
    from tests.conftest import seed_admin
    _, person, _ = seed_admin(db_session, email="time-progress-integrity@example.com")
    project = make_project(db_session)
    task = models.ProjectTask(id=uuid4(), project_id=project.id, title="Measured work", estimated_hours=planned_hours,
                              physical_progress_pct=physical_pct, status=status)
    db_session.add(task)
    db_session.commit()
    log_ids = []
    for day in range(4):
        log = crud.create_project_time_log(db_session, project.id,
                                          schemas.ProjectTimeLogCreate(task_id=task.id, hours=20, date=NOW-timedelta(days=day)),
                                          persona_id=person.id, created_by=person.id)
        log_ids.append(log.id)
    db_session.expire_all()
    assert task.actual_hours == 80
    assert task.physical_progress_pct == physical_pct
    assert task.status == ("in_progress" if status == "todo" else status)
    if planned_hours == 100 and physical_pct == 20:
        effort = evm.build_project_execution_matrix(db_session, project, now=NOW)["frente_tiempo"]
        assert effort["earned_hours"] == 20
        assert effort["actual_hours"] == 80
        assert effort["hours_efficiency_pct"] == 25
    for log_id in log_ids:
        assert crud.delete_project_time_log(db_session, project.id, log_id)
    db_session.expire_all()
    assert task.actual_hours == 0
    assert task.physical_progress_pct == physical_pct
