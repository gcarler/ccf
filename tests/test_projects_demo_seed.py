from __future__ import annotations

import pytest

from scripts.seeding.seed_projects_demo import (
    DEMO_PROJECTS,
    seed_projects_demo,
    validate_seed_target,
)
from tests.conftest import auth_headers, seed_admin


@pytest.mark.parametrize("database_name", ["ccf_test", "projects_e2e_20261004", "ccf_quality_run_42"])
def test_projects_demo_reset_requires_exact_confirmation_on_isolated_database(database_name):
    database_url = f"postgresql://tester:secret@127.0.0.1:5432/{database_name}"

    assert validate_seed_target(database_url, database_name, reset=True) == database_name


def test_projects_demo_seed_rejects_missing_or_mismatched_database_confirmation():
    database_url = "postgresql://tester:secret@127.0.0.1:5432/ccf_projects_e2e"

    with pytest.raises(RuntimeError, match="PROJECTS_DEMO_TARGET_DATABASE"):
        validate_seed_target(database_url, None, reset=True)
    with pytest.raises(RuntimeError, match="PROJECTS_DEMO_TARGET_DATABASE"):
        validate_seed_target(database_url, "another_database", reset=True)


def test_projects_demo_reset_rejects_confirmed_non_test_database():
    database_url = "postgresql://tester:secret@127.0.0.1:5432/ccf_recovery_20260823"

    with pytest.raises(RuntimeError, match="_e2e, _test o _quality"):
        validate_seed_target(database_url, "ccf_recovery_20260823", reset=True)


def test_projects_demo_non_reset_seed_allows_explicitly_confirmed_local_database():
    database_url = "postgresql://tester:secret@127.0.0.1:5432/ccf_dev"

    assert validate_seed_target(database_url, "ccf_dev", reset=False) == "ccf_dev"


def test_projects_demo_seed_roundtrip(client, db_session):
    user, persona, sede = seed_admin(db_session)
    created = seed_projects_demo(db_session, actor_email=user.email, reset=True)

    assert len(created) == 3

    headers = auth_headers(client)

    projects_resp = client.get("/api/projects", headers=headers)
    assert projects_resp.status_code == 200
    projects = projects_resp.json()
    assert len(projects) == 3

    projects_by_title = {row["title"]: row for row in projects}
    assert set(projects_by_title) == {item["title"] for item in DEMO_PROJECTS}

    tasks_resp = client.get("/api/projects/tasks", headers=headers)
    assert tasks_resp.status_code == 200
    assert len(tasks_resp.json()) == 15

    activities_resp = client.get("/api/projects/activities?limit=50", headers=headers)
    assert activities_resp.status_code == 200
    assert len(activities_resp.json()) == 15

    for project_def in DEMO_PROJECTS:
        project = projects_by_title[project_def["title"]]
        detail_resp = client.get(f"/api/projects/{project['id']}", headers=headers)
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert detail["title"] == project_def["title"]
        assert len(detail["tasks"]) == 5

        project_activities_resp = client.get(
            f"/api/projects/activities?project_id={project['id']}&limit=10",
            headers=headers,
        )
        assert project_activities_resp.status_code == 200
        project_activities = project_activities_resp.json()
        assert len(project_activities) == 5
        assert {row["project_id"] for row in project_activities} == {project["id"]}

    summary_resp = client.get("/api/projects/summary", headers=headers)
    assert summary_resp.status_code == 200
    summary_rows = summary_resp.json()
    assert sum(row["total_projects"] for row in summary_rows) == 3
    assert sum(row["total_tasks"] for row in summary_rows) == 15
