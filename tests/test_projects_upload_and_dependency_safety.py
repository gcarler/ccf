"""HTTP regressions for project upload safety and cyclic dependencies."""
from uuid import UUID

import pytest

from backend import models
from tests.conftest import auth_headers, seed_admin
from tests.factories_projects import create_project_factory, create_task_factory


@pytest.fixture
def project_context(db_session, client):
    user, _, sede = seed_admin(db_session, email="projects-safety@example.com")
    project = create_project_factory(db_session, sede_id=sede.id, owner_id=user.id)
    tasks = [create_task_factory(db_session, project.id) for _ in range(3)]
    db_session.commit()
    return project, tasks, auth_headers(client, email=user.email)


@pytest.mark.parametrize("chain_length", [2, 3])
def test_cycle_returns_422_without_persisting_rejected_edge(client, db_session, project_context, chain_length):
    project, tasks, headers = project_context
    route = f"/api/projects/{project.id}/dependencies"
    for predecessor, successor in zip(tasks[:chain_length], tasks[1:chain_length]):
        response = client.post(route, headers=headers, json={"predecessor_id": str(predecessor.id), "successor_id": str(successor.id)})
        assert response.status_code == 201, response.text
    before = db_session.query(models.ProjectTaskDependency).filter_by(project_id=project.id).count()
    response = client.post(route, headers=headers, json={"predecessor_id": str(tasks[chain_length-1].id), "successor_id": str(tasks[0].id)})
    assert response.status_code == 422, response.text
    assert "circular" in response.json()["detail"].lower()
    db_session.expire_all()
    assert db_session.query(models.ProjectTaskDependency).filter_by(project_id=project.id).count() == before
    # Rejection must not poison the next valid request/session.
    valid = client.post(route, headers=headers, json={"predecessor_id": str(tasks[0].id), "successor_id": str(tasks[2].id)})
    assert valid.status_code == 201, valid.text
    assert UUID(valid.json()["predecessor_id"]) == tasks[0].id
