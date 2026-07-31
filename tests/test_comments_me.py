"""Tests for the comment admin center endpoints (projects, tasks, agenda)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from backend.models_agenda import AgendaEventComment, EventoAgenda
from backend.models_projects import Project, ProjectComment, ProjectTask
from tests.conftest import auth_headers, seed_admin, seed_user_with_role


@pytest.fixture
def comments_env(client, db_session):
    """Seed users, a project, a task, an agenda event and several comments."""
    main_user, main_persona, sede = seed_admin(db_session, email="main@test.com")
    headers = auth_headers(client, email="main@test.com", password="testpass123")

    other_user, other_persona, _ = seed_user_with_role(
        db_session, role_name="persona", email="other@test.com", sede_id=sede.id
    )

    project = Project(title="Test Project", sede_id=sede.id, owner_id=main_persona.id)
    db_session.add(project)
    db_session.flush()

    task = ProjectTask(title="Test Task", project_id=project.id)
    db_session.add(task)
    db_session.flush()

    agenda = EventoAgenda(
        titulo="Test Event",
        sede_id=sede.id,
        organizador_persona_id=main_persona.id,
        fecha_inicio=datetime.now(timezone.utc),
        fecha_fin=datetime.now(timezone.utc),
    )
    db_session.add(agenda)
    db_session.flush()

    main_id = str(main_persona.id)
    other_id = str(other_persona.id)

    # Main user authored comments
    c_project = ProjectComment(project_id=project.id, author_id=main_id, content="Proj comment")
    c_activity = ProjectComment(project_id=project.id, task_id=task.id, author_id=main_id, content="Task comment")
    c_agenda = AgendaEventComment(event_id=agenda.id, author_id=main_id, content="Agenda comment")

    # Other user authored comments mentioning the main user
    c_mention_project = ProjectComment(
        project_id=project.id, author_id=other_id, content="Mention project", mentions=[main_id]
    )
    c_mention_agenda = AgendaEventComment(
        event_id=agenda.id, author_id=other_id, content="Mention agenda", mentions=[main_id]
    )

    # Self-mention: should be excluded from /me/mentions
    c_self_mention = AgendaEventComment(
        event_id=agenda.id, author_id=main_id, content="Self mention", mentions=[main_id]
    )

    db_session.add_all(
        [
            c_project,
            c_activity,
            c_agenda,
            c_mention_project,
            c_mention_agenda,
            c_self_mention,
        ]
    )
    db_session.commit()

    return {
        "client": client,
        "headers": headers,
        "main_id": main_id,
        "other_id": other_id,
        "project_id": str(project.id),
        "task_id": str(task.id),
        "agenda_id": str(agenda.id),
    }


class TestCommentsMeCreated:
    def test_returns_all_modules(self, comments_env):
        c, h = comments_env["client"], comments_env["headers"]
        resp = c.get("/api/comments/me/created", headers=h)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3
        assert {item["module_type"] for item in data} == {"project", "activity", "agenda"}

    def test_filter_by_project(self, comments_env):
        c, h = comments_env["client"], comments_env["headers"]
        resp = c.get("/api/comments/me/created?type=project", headers=h)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["module_type"] == "project"
        assert data[0]["context_title"] == "Test Project"

    def test_filter_by_activity(self, comments_env):
        c, h = comments_env["client"], comments_env["headers"]
        resp = c.get("/api/comments/me/created?type=activity", headers=h)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["module_type"] == "activity"
        assert data[0]["task_id"] == comments_env["task_id"]

    def test_filter_by_agenda(self, comments_env):
        c, h = comments_env["client"], comments_env["headers"]
        resp = c.get("/api/comments/me/created?type=agenda", headers=h)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["module_type"] == "agenda"
        assert data[0]["context_title"] == "Test Event"

    def test_invalid_type_filter(self, comments_env):
        c, h = comments_env["client"], comments_env["headers"]
        resp = c.get("/api/comments/me/created?type=invalid", headers=h)
        assert resp.status_code == 422

    def test_offset_pagination(self, comments_env):
        c, h = comments_env["client"], comments_env["headers"]
        first = c.get("/api/comments/me/created?limit=1&offset=0", headers=h).json()
        second = c.get("/api/comments/me/created?limit=1&offset=1", headers=h).json()
        assert len(first) == 1
        assert len(second) == 1
        assert first[0]["id"] != second[0]["id"]


class TestCommentsMeMentions:
    def test_excludes_self_mentions(self, comments_env):
        c, h = comments_env["client"], comments_env["headers"]
        resp = c.get("/api/comments/me/mentions", headers=h)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert {item["module_type"] for item in data} == {"project", "agenda"}
        for item in data:
            assert item["author_id"] != comments_env["main_id"]

    def test_filter_mentions_by_type(self, comments_env):
        c, h = comments_env["client"], comments_env["headers"]
        resp = c.get("/api/comments/me/mentions?type=project", headers=h)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["module_type"] == "project"

    def test_pagination(self, comments_env):
        c, h = comments_env["client"], comments_env["headers"]
        resp = c.get("/api/comments/me/mentions?limit=1&offset=0", headers=h)
        assert resp.status_code == 200
        assert len(resp.json()) == 1
