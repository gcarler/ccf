from __future__ import annotations

from scripts.seeding.seed_projects_demo import DEMO_PROJECTS, seed_projects_demo
from tests.conftest import auth_headers, seed_admin


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
