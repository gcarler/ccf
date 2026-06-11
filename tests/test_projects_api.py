"""Comprehensive API tests for the Projects module.

Covers all 34 API endpoints in /api/projects/* using factories and
the conftest.py fixtures (db_session, client, seed_admin_v2, auth_headers_v2).

Organised in 12 labelled sections (A-L) with ~66 individual tests.
"""

from __future__ import annotations

import uuid as _uuid

import pytest

from backend.models_personas import Persona
from backend.models_crm import ChatMessage  # noqa: F401 — register for import side effects
from tests.conftest import seed_admin_v2, auth_headers_v2
from tests.factories_projects import (
    create_project_factory,
    create_task_factory,
    create_subtask_factory,
    create_milestone_factory,
    create_comment_factory,
    create_supply_factory,
    create_default_phases_factory,
    create_activity_log_factory,
    create_wiki_factory,
    create_whiteboard_factory,
    create_message_factory,
    create_attachment_factory,
    create_inbox_state_factory,
    setup_project_with_all_relations,
)

# ── Helpers ───────────────────────────────────────────────────────────────


def _assert_uuid(value: str) -> _uuid.UUID:
    """Assert *value* is a valid UUID string and return it."""
    assert isinstance(value, str), f"Expected string, got {type(value)}: {value}"
    parsed = _uuid.UUID(value)
    assert str(parsed) == value, f"UUID string mismatch: {parsed} != {value}"
    return parsed


def _assert_datetime(value: str):
    """Assert *value* looks like an ISO-8601 datetime string."""
    from datetime import datetime
    assert isinstance(value, str), f"Expected string datetime, got {type(value)}"
    datetime.fromisoformat(value.replace("Z", "+00:00"))


# ── A: CRUD Proyectos ────────────────────────────────────────────────────
# Routes: GET /projects, POST /projects, GET /projects/{id},
#         PATCH /projects/{id}, DELETE /projects/{id}


class TestProjectsCRUD:

    def test_list_projects_empty(self, client, db_session):
        """GET /api/projects without data returns empty list."""
        seed_admin_v2(db_session)
        headers = auth_headers_v2(client)
        resp = client.get("/api/projects", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_create_project(self, client, db_session):
        """POST /api/projects creates a project and returns 201."""
        _, _, sede = seed_admin_v2(db_session)
        headers = auth_headers_v2(client)
        payload = dict(title="Proyecto de prueba", description="Test", status="planning", color="#3b82f6")
        resp = client.post("/api/projects", json=payload, headers=headers)
        assert resp.status_code == 201, f"Body: {resp.text}"
        data = resp.json()
        assert data["title"] == "Proyecto de prueba"
        assert data["status"] == "planning"
        _assert_uuid(data["id"])
        _assert_datetime(data["created_at"])

    def test_create_project_creates_default_phases(self, client, db_session):
        """Creating a project also creates 4 default Kanban phases."""
        _, _, sede = seed_admin_v2(db_session)
        headers = auth_headers_v2(client)
        resp = client.post("/api/projects", json={"title": "Con fases", "status": "planning"}, headers=headers)
        assert resp.status_code == 201
        project_id = resp.json()["id"]

        # Verify phases exist
        phases_resp = client.get(f"/api/projects/{project_id}/phases", headers=headers)
        assert phases_resp.status_code == 200
        phases = phases_resp.json()
        assert len(phases) == 4, f"Expected 4 phases, got {len(phases)}"

    def test_create_then_list(self, client, db_session):
        """Project appears in list after creation."""
        _, _, sede = seed_admin_v2(db_session)
        headers = auth_headers_v2(client)
        client.post("/api/projects", json={"title": "List Test"}, headers=headers)
        resp = client.get("/api/projects", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_get_project_by_id(self, client, db_session):
        """GET /api/projects/{id} returns the project with tasks and milestones."""
        _, _, sede = seed_admin_v2(db_session)
        data = setup_project_with_all_relations(db_session)
        headers = auth_headers_v2(client)
        project_id = str(data["project"].id)

        resp = client.get(f"/api/projects/{project_id}", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == project_id
        assert len(body["tasks"]) >= 1
        assert len(body["milestones"]) >= 1

    def test_get_project_not_found(self, client, db_session):
        """GET /api/projects/{nonexistent} returns 404."""
        seed_admin_v2(db_session)
        headers = auth_headers_v2(client)
        fake_id = str(_uuid.uuid4())
        resp = client.get(f"/api/projects/{fake_id}", headers=headers)
        assert resp.status_code == 404

    def test_update_project(self, client, db_session):
        """PATCH /api/projects/{id} updates fields."""
        _, _, sede = seed_admin_v2(db_session)
        proj = create_project_factory(db_session)
        headers = auth_headers_v2(client)
        resp = client.patch(f"/api/projects/{proj.id}", json={"title": "Actualizado", "status": "active"}, headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["title"] == "Actualizado"
        assert body["status"] == "active"

    def test_delete_project(self, client, db_session):
        """DELETE /api/projects/{id} soft-deletes the project."""
        _, _, sede = seed_admin_v2(db_session)
        proj = create_project_factory(db_session)
        headers = auth_headers_v2(client)
        resp = client.delete(f"/api/projects/{proj.id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_delete_project_removes_from_list(self, client, db_session):
        """Deleted project no longer appears in listing."""
        _, _, sede = seed_admin_v2(db_session)
        proj = create_project_factory(db_session)
        headers = auth_headers_v2(client)
        client.delete(f"/api/projects/{proj.id}", headers=headers)
        resp = client.get("/api/projects", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 0


# ── B: Phases ────────────────────────────────────────────────────────────
# Routes: GET /projects/{id}/phases, PUT /projects/{id}/phases


class TestPhases:

    def test_list_default_phases(self, client, db_session):
        """GET /projects/{id}/phases returns the 4 default phases."""
        _, _, sede = seed_admin_v2(db_session)
        proj = create_project_factory(db_session)
        create_default_phases_factory(db_session, proj.id)
        headers = auth_headers_v2(client)
        resp = client.get(f"/api/projects/{proj.id}/phases", headers=headers)
        assert resp.status_code == 200
        phases = resp.json()
        assert len(phases) == 4
        slugs = {p["slug"] for p in phases}
        assert slugs == {"todo", "in_progress", "review", "completed"}

    def test_set_phases_reorder(self, client, db_session):
        """PUT /projects/{id}/phases replaces phases with new order."""
        _, _, sede = seed_admin_v2(db_session)
        proj = create_project_factory(db_session)
        create_default_phases_factory(db_session, proj.id)
        headers = auth_headers_v2(client)
        new_phases = [
            {"name": "Backlog", "slug": "backlog", "color": "#64748b"},
            {"name": "In Progress", "slug": "in_progress", "color": "#3b82f6"},
            {"name": "Done", "slug": "done", "color": "#22c55e"},
        ]
        resp = client.put(f"/api/projects/{proj.id}/phases", json=new_phases, headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 3

    def test_set_phases_blocks_delete_with_tasks(self, client, db_session):
        """PUT that removes a phase with tasks returns 409."""
        _, _, sede = seed_admin_v2(db_session)
        proj = create_project_factory(db_session)
        create_default_phases_factory(db_session, proj.id)
        create_task_factory(db_session, proj.id, status="todo")
        headers = auth_headers_v2(client)
        resp = client.put(
            f"/api/projects/{proj.id}/phases",
            json=[{"name": "Done", "slug": "completed", "color": "green"}],
            headers=headers,
        )
        assert resp.status_code == 409


# ── C: Tasks ─────────────────────────────────────────────────────────────
# Routes: POST /projects/{id}/tasks, GET /projects/{id}/tasks,
#         GET /projects/tasks/{id}, PATCH /projects/tasks/{id},
#         PATCH /projects/{id}/tasks/{id}, DELETE /projects/{id}/tasks/{id}


class TestTasks:

    def test_create_task(self, client, db_session):
        """POST /projects/{id}/tasks creates a task."""
        _, _, sede = seed_admin_v2(db_session)
        proj = create_project_factory(db_session)
        headers = auth_headers_v2(client)
        resp = client.post(
            f"/api/projects/{proj.id}/tasks",
            json={"title": "Mi tarea", "status": "todo", "priority": "high"},
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        _assert_uuid(data["id"])
        assert data["title"] == "Mi tarea"

    def test_list_tasks_empty(self, client, db_session):
        """GET /projects/{id}/tasks returns [] when no tasks."""
        _, _, sede = seed_admin_v2(db_session)
        proj = create_project_factory(db_session)
        headers = auth_headers_v2(client)
        resp = client.get(f"/api/projects/{proj.id}/tasks", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_tasks_with_data(self, client, db_session):
        """GET /projects/{id}/tasks returns created tasks."""
        _, _, sede = seed_admin_v2(db_session)
        proj = create_project_factory(db_session)
        create_task_factory(db_session, proj.id, title="Task A")
        create_task_factory(db_session, proj.id, title="Task B")
        headers = auth_headers_v2(client)
        resp = client.get(f"/api/projects/{proj.id}/tasks", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_list_tasks_with_status_filter(self, client, db_session):
        """GET /projects/{id}/tasks?status=completed filters tasks."""
        from sqlalchemy import func
        _, _, sede = seed_admin_v2(db_session)
        proj = create_project_factory(db_session)
        # Ensure created_at ordering is deterministic
        create_task_factory(db_session, proj.id, status="completed", title="Done!")
        create_task_factory(db_session, proj.id, status="todo", title="Todo")
        headers = auth_headers_v2(client)
        resp = client.get(f"/api/projects/{proj.id}/tasks?status=completed", headers=headers)
        assert resp.status_code == 200
        tasks = resp.json()
        assert len(tasks) == 1
        assert tasks[0]["status"] == "completed"

    def test_get_task(self, client, db_session):
        """GET /projects/tasks/{task_id} returns the task."""
        _, _, sede = seed_admin_v2(db_session)
        proj = create_project_factory(db_session)
        task = create_task_factory(db_session, proj.id)
        headers = auth_headers_v2(client)
        resp = client.get(f"/api/projects/tasks/{task.id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == str(task.id)

    def test_update_task_flat(self, client, db_session):
        """PATCH /projects/tasks/{task_id} updates a task."""
        _, _, sede = seed_admin_v2(db_session)
        proj = create_project_factory(db_session)
        task = create_task_factory(db_session, proj.id, title="Old")
        headers = auth_headers_v2(client)
        resp = client.patch(f"/api/projects/tasks/{task.id}", json={"title": "New Title"}, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["title"] == "New Title"

    def test_update_task_scoped(self, client, db_session):
        """PATCH /projects/{id}/tasks/{task_id} also works."""
        _, _, sede = seed_admin_v2(db_session)
        proj = create_project_factory(db_session)
        task = create_task_factory(db_session, proj.id, priority="low")
        headers = auth_headers_v2(client)
        resp = client.patch(f"/api/projects/{proj.id}/tasks/{task.id}", json={"priority": "urgent"}, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["priority"] == "urgent"

    def test_delete_task(self, client, db_session):
        """DELETE /projects/{id}/tasks/{task_id} soft-deletes."""
        _, _, sede = seed_admin_v2(db_session)
        proj = create_project_factory(db_session)
        task = create_task_factory(db_session, proj.id)
        headers = auth_headers_v2(client)
        resp = client.delete(f"/api/projects/{proj.id}/tasks/{task.id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_get_task_not_found(self, client, db_session):
        """GET /projects/tasks/{fake_uuid} returns 404."""
        _, _, sede = seed_admin_v2(db_session)
        headers = auth_headers_v2(client)
        resp = client.get(f"/api/projects/tasks/{_uuid.uuid4()}", headers=headers)
        assert resp.status_code == 404

    def test_create_task_with_uuid_assignee(self, client, db_session):
        """POST task with UUID assignee_id — no Number() coercion."""
        _, _, sede = seed_admin_v2(db_session)
        proj = create_project_factory(db_session)
        persona_id = str(_uuid.uuid4())
        # Create the persona so the FK resolves
        db_session.add(Persona(id=_uuid.UUID(persona_id), first_name="Assign", last_name="Test", email="assignee@test.com"))
        db_session.flush()
        headers = auth_headers_v2(client)
        resp = client.post(
            f"/api/projects/{proj.id}/tasks",
            json={"title": "UUID assignee", "assignee_id": persona_id},
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["assignee_id"] == persona_id


# ── D: Subtasks ──────────────────────────────────────────────────────────
# Routes (3): POST/PATCH/DELETE /projects/{id}/tasks/{tid}/subtasks[/{sid}]


class TestSubtasks:

    def test_create_subtask(self, client, db_session):
        _, _, sede = seed_admin_v2(db_session)
        proj = create_project_factory(db_session)
        parent = create_task_factory(db_session, proj.id)
        headers = auth_headers_v2(client)
        resp = client.post(
            f"/api/projects/{proj.id}/tasks/{parent.id}/subtasks",
            json={"title": "Subtask A"},
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["parent_id"] == str(parent.id)
        assert data["project_id"] == str(proj.id)

    def test_update_subtask(self, client, db_session):
        _, _, sede = seed_admin_v2(db_session)
        proj = create_project_factory(db_session)
        parent = create_task_factory(db_session, proj.id)
        sub = create_subtask_factory(db_session, parent.id, proj.id, title="Old Sub")
        headers = auth_headers_v2(client)
        resp = client.patch(
            f"/api/projects/{proj.id}/tasks/{parent.id}/subtasks/{sub.id}",
            json={"title": "Updated Sub"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated Sub"

    def test_delete_subtask(self, client, db_session):
        _, _, sede = seed_admin_v2(db_session)
        proj = create_project_factory(db_session)
        parent = create_task_factory(db_session, proj.id)
        sub = create_subtask_factory(db_session, parent.id, proj.id)
        headers = auth_headers_v2(client)
        resp = client.delete(
            f"/api/projects/{proj.id}/tasks/{parent.id}/subtasks/{sub.id}",
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_subtask_mismatched_parent(self, client, db_session):
        """PATCH subtask with wrong parent returns 404."""
        _, _, sede = seed_admin_v2(db_session)
        proj = create_project_factory(db_session)
        t1 = create_task_factory(db_session, proj.id)
        t2 = create_task_factory(db_session, proj.id)
        sub = create_subtask_factory(db_session, t1.id, proj.id)
        headers = auth_headers_v2(client)
        resp = client.patch(
            f"/api/projects/{proj.id}/tasks/{t2.id}/subtasks/{sub.id}",
            json={"title": "Nope"},
            headers=headers,
        )
        assert resp.status_code == 404


# ── E: Milestones ─────────────────────────────────────────────────────────
# Routes (4): GET/POST /projects/{id}/milestones,
#             PATCH /projects/{id}/milestones/{mid}


class TestMilestones:

    def test_list_milestones(self, client, db_session):
        _, _, sede = seed_admin_v2(db_session)
        proj = create_project_factory(db_session)
        create_milestone_factory(db_session, proj.id, title="M1")
        create_milestone_factory(db_session, proj.id, title="M2")
        headers = auth_headers_v2(client)
        resp = client.get(f"/api/projects/{proj.id}/milestones", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_create_milestone(self, client, db_session):
        _, _, sede = seed_admin_v2(db_session)
        proj = create_project_factory(db_session)
        headers = auth_headers_v2(client)
        resp = client.post(
            f"/api/projects/{proj.id}/milestones",
            json={"title": "Nuevo hito", "description": "Desc"},
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        _assert_uuid(data["id"])
        assert data["title"] == "Nuevo hito"

    def test_update_milestone_complete(self, client, db_session):
        _, _, sede = seed_admin_v2(db_session)
        proj = create_project_factory(db_session)
        ms = create_milestone_factory(db_session, proj.id)
        headers = auth_headers_v2(client)
        resp = client.patch(
            f"/api/projects/{proj.id}/milestones/{ms.id}",
            json={"is_completed": True},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["is_completed"] is True

    def test_update_milestone_reopen(self, client, db_session):
        _, _, sede = seed_admin_v2(db_session)
        proj = create_project_factory(db_session)
        ms = create_milestone_factory(db_session, proj.id, is_completed=True)
        headers = auth_headers_v2(client)
        resp = client.patch(
            f"/api/projects/{proj.id}/milestones/{ms.id}",
            json={"is_completed": False},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["is_completed"] is False


# ── F: Comments ──────────────────────────────────────────────────────────
# Routes (6): GET /projects/comments, POST /projects/comments,
#             POST /projects/{id}/comments, PATCH /projects/comments/{cid},
#             DELETE /projects/comments/{cid}


class TestComments:

    def test_list_comments_empty(self, client, db_session):
        _, _, sede = seed_admin_v2(db_session)
        headers = auth_headers_v2(client)
        resp = client.get("/api/projects/comments", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_comments_with_data(self, client, db_session):
        _, _, sede = seed_admin_v2(db_session)
        data = setup_project_with_all_relations(db_session)
        headers = auth_headers_v2(client)
        resp = client.get("/api/projects/comments", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_list_comments_filtered_by_project(self, client, db_session):
        _, _, sede = seed_admin_v2(db_session)
        d1 = setup_project_with_all_relations(db_session)
        headers = auth_headers_v2(client)
        resp = client.get(f"/api/projects/comments?project_id={d1['project'].id}", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_create_comment_legacy(self, client, db_session):
        """POST /projects/comments (body with project_id, content) — legacy route."""
        _, _, sede = seed_admin_v2(db_session)
        proj = create_project_factory(db_session)
        headers = auth_headers_v2(client)
        resp = client.post(
            "/api/projects/comments",
            json={"project_id": str(proj.id), "content": "Legacy comment"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["content"] == "Legacy comment"

    def test_create_comment_by_project(self, client, db_session):
        """POST /projects/{id}/comments."""
        _, _, sede = seed_admin_v2(db_session)
        proj = create_project_factory(db_session)
        headers = auth_headers_v2(client)
        resp = client.post(
            f"/api/projects/{proj.id}/comments",
            json={"content": "Scoped comment"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["content"] == "Scoped comment"

    def test_update_comment_content(self, client, db_session):
        """Update comment content via PATCH."""
        user, persona, sede = seed_admin_v2(db_session)
        proj = create_project_factory(db_session)
        comment = create_comment_factory(db_session, proj.id, persona.id)
        headers = auth_headers_v2(client)
        resp = client.patch(f"/api/projects/comments/{comment.id}", json={"content": "Updated"}, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["content"] == "Updated"

    def test_resolve_comment(self, client, db_session):
        """Resolve a comment via PATCH is_resolved=True."""
        user, persona, sede = seed_admin_v2(db_session)
        proj = create_project_factory(db_session)
        comment = create_comment_factory(db_session, proj.id, persona.id)
        headers = auth_headers_v2(client)
        resp = client.patch(f"/api/projects/comments/{comment.id}", json={"is_resolved": True}, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["is_resolved"] is True

    def test_delete_comment(self, client, db_session):
        """Delete a comment via DELETE."""
        user, persona, sede = seed_admin_v2(db_session)
        proj = create_project_factory(db_session)
        comment = create_comment_factory(db_session, proj.id, persona.id)
        headers = auth_headers_v2(client)
        resp = client.delete(f"/api/projects/comments/{comment.id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_comment_not_found(self, client, db_session):
        _, _, sede = seed_admin_v2(db_session)
        headers = auth_headers_v2(client)
        resp = client.patch("/api/projects/comments/999999", json={"content": "Nope"}, headers=headers)
        assert resp.status_code == 404

    def test_create_comment_missing_fields(self, client, db_session):
        _, _, sede = seed_admin_v2(db_session)
        headers = auth_headers_v2(client)
        resp = client.post("/api/projects/comments", json={}, headers=headers)
        assert resp.status_code == 400


# ── G: Inbox ─────────────────────────────────────────────────────────────
# Routes (2): GET /projects/inbox, POST /projects/inbox/{id}/read


class TestInbox:

    def test_list_inbox_empty(self, client, db_session):
        _, _, sede = seed_admin_v2(db_session)
        headers = auth_headers_v2(client)
        resp = client.get("/api/projects/inbox", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_mark_inbox_read(self, client, db_session):
        _, _, sede = seed_admin_v2(db_session)
        headers = auth_headers_v2(client)
        resp = client.post("/api/projects/inbox/comment-1/read", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["ok"] is True


# ── H: Portfolio / Workload / Activities / My Tasks ──────────────────────
# Routes (4): GET /projects/summary, GET /projects/workload,
#             GET /projects/activities, GET /projects/tasks


class TestPortfolioWorkload:

    def test_portfolio_summary(self, client, db_session):
        _, _, sede = seed_admin_v2(db_session)
        proj = create_project_factory(db_session)
        create_task_factory(db_session, proj.id, status="todo")
        create_task_factory(db_session, proj.id, status="completed")
        headers = auth_headers_v2(client)
        resp = client.get("/api/projects/summary", headers=headers)
        assert resp.status_code == 200
        rows = resp.json()
        assert len(rows) >= 1

    def test_workload_summary(self, client, db_session):
        _, _, sede = seed_admin_v2(db_session)
        proj = create_project_factory(db_session)
        create_task_factory(db_session, proj.id, status="in_progress")
        headers = auth_headers_v2(client)
        resp = client.get("/api/projects/workload", headers=headers)
        assert resp.status_code == 200
        # Might be empty if no assignee_id matches, but should not crash
        assert isinstance(resp.json(), list)

    def test_list_activities(self, client, db_session):
        _, _, sede = seed_admin_v2(db_session)
        data = setup_project_with_all_relations(db_session)
        headers = auth_headers_v2(client)
        resp = client.get("/api/projects/activities", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_list_activities_filtered(self, client, db_session):
        _, _, sede = seed_admin_v2(db_session)
        data = setup_project_with_all_relations(db_session)
        headers = auth_headers_v2(client)
        resp = client.get(f"/api/projects/activities?project_id={data['project'].id}", headers=headers)
        assert resp.status_code == 200
        assert all(a["project_id"] == str(data["project"].id) for a in resp.json())

    def test_list_all_my_tasks(self, client, db_session):
        """GET /projects/tasks returns tasks assigned to current user's persona."""
        user, persona, sede = seed_admin_v2(db_session)
        proj = create_project_factory(db_session)
        create_task_factory(db_session, proj.id, assignee_id=persona.id)
        headers = auth_headers_v2(client)
        resp = client.get("/api/projects/tasks", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1


# ── I: Wiki / Whiteboard ────────────────────────────────────────────────
# Routes (4): GET/POST /projects/{id}/wiki, GET/POST /projects/{id}/whiteboard


class TestWikiWhiteboard:

    def test_get_wiki_nonexistent(self, client, db_session):
        _, _, sede = seed_admin_v2(db_session)
        proj = create_project_factory(db_session)
        headers = auth_headers_v2(client)
        resp = client.get(f"/api/projects/{proj.id}/wiki", headers=headers)
        assert resp.status_code == 200
        assert resp.json() is None

    def test_create_wiki(self, client, db_session):
        _, _, sede = seed_admin_v2(db_session)
        proj = create_project_factory(db_session)
        headers = auth_headers_v2(client)
        resp = client.post(
            f"/api/projects/{proj.id}/wiki",
            json={"content": "# New Wiki", "title": "Wiki Title"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Wiki Title"
        assert "# New Wiki" in data["content"]

    def test_update_wiki(self, client, db_session):
        _, _, sede = seed_admin_v2(db_session)
        proj = create_project_factory(db_session)
        create_wiki_factory(db_session, proj.id)
        headers = auth_headers_v2(client)
        resp = client.post(
            f"/api/projects/{proj.id}/wiki",
            json={"content": "# Updated", "title": "Updated Wiki"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated Wiki"

    def test_get_whiteboard_nonexistent(self, client, db_session):
        _, _, sede = seed_admin_v2(db_session)
        proj = create_project_factory(db_session)
        headers = auth_headers_v2(client)
        resp = client.get(f"/api/projects/{proj.id}/whiteboard", headers=headers)
        assert resp.status_code == 200
        assert resp.json() is None

    def test_create_whiteboard(self, client, db_session):
        _, _, sede = seed_admin_v2(db_session)
        proj = create_project_factory(db_session)
        headers = auth_headers_v2(client)
        resp = client.post(
            f"/api/projects/{proj.id}/whiteboard",
            json={"title": "Pizarra", "elements_json": '[{"type":"rectangle"}]'},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "Pizarra"

    def test_update_whiteboard(self, client, db_session):
        _, _, sede = seed_admin_v2(db_session)
        proj = create_project_factory(db_session)
        create_whiteboard_factory(db_session, proj.id)
        headers = auth_headers_v2(client)
        resp = client.post(
            f"/api/projects/{proj.id}/whiteboard",
            json={"elements_json": '[{"type":"circle"}]'},
            headers=headers,
        )
        assert resp.status_code == 200
        assert "circle" in resp.json()["elements_json"]


# ── J: Supplies ──────────────────────────────────────────────────────────
# Routes (4): GET/POST /projects/{pid}/tasks/{tid}/supplies,
#             PATCH/DELETE /projects/{pid}/tasks/{tid}/supplies/{sid}


class TestSupplies:

    def test_list_supplies_empty(self, client, db_session):
        _, _, sede = seed_admin_v2(db_session)
        proj = create_project_factory(db_session)
        task = create_task_factory(db_session, proj.id)
        headers = auth_headers_v2(client)
        resp = client.get(f"/api/projects/{proj.id}/tasks/{task.id}/supplies", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_create_supply(self, client, db_session):
        _, _, sede = seed_admin_v2(db_session)
        proj = create_project_factory(db_session)
        task = create_task_factory(db_session, proj.id)
        headers = auth_headers_v2(client)
        resp = client.post(
            f"/api/projects/{proj.id}/tasks/{task.id}/supplies",
            json={"item_name": "Cable HDMI", "quantity": 2, "status": "pending"},
            headers=headers,
        )
        assert resp.status_code == 201
        assert resp.json()["item_name"] == "Cable HDMI"

    def test_update_supply(self, client, db_session):
        _, _, sede = seed_admin_v2(db_session)
        proj = create_project_factory(db_session)
        task = create_task_factory(db_session, proj.id)
        supply = create_supply_factory(db_session, task.id)
        headers = auth_headers_v2(client)
        resp = client.patch(
            f"/api/projects/{proj.id}/tasks/{task.id}/supplies/{supply.id}",
            json={"status": "purchased"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "purchased"

    def test_delete_supply(self, client, db_session):
        _, _, sede = seed_admin_v2(db_session)
        proj = create_project_factory(db_session)
        task = create_task_factory(db_session, proj.id)
        supply = create_supply_factory(db_session, task.id)
        headers = auth_headers_v2(client)
        resp = client.delete(
            f"/api/projects/{proj.id}/tasks/{task.id}/supplies/{supply.id}",
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True


# ── K: Chat Messages ─────────────────────────────────────────────────────
# Routes (3): GET/POST /projects/{id}/messages,
#             DELETE /projects/{id}/messages/{mid}


class TestMessages:

    def test_list_messages_empty(self, client, db_session):
        _, _, sede = seed_admin_v2(db_session)
        proj = create_project_factory(db_session)
        headers = auth_headers_v2(client)
        resp = client.get(f"/api/projects/{proj.id}/messages", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_send_message(self, client, db_session):
        _, _, sede = seed_admin_v2(db_session)
        proj = create_project_factory(db_session)
        headers = auth_headers_v2(client)
        resp = client.post(
            f"/api/projects/{proj.id}/messages",
            json={"content": "Hola equipo"},
            headers=headers,
        )
        assert resp.status_code == 201
        assert resp.json()["content"] == "Hola equipo"

    def test_delete_own_message(self, client, db_session):
        user, persona, sede = seed_admin_v2(db_session)
        proj = create_project_factory(db_session)
        msg = create_message_factory(db_session, proj.id, persona.id)
        headers = auth_headers_v2(client)
        resp = client.delete(f"/api/projects/{proj.id}/messages/{msg.id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["ok"] is True


# ── L: UUID & Edge Cases ─────────────────────────────────────────────────
# Transversal validations across the module


class TestUUIDEdgeCases:

    def test_get_project_by_nonexistent_uuid(self, client, db_session):
        """UUID format is respected; nonexistent returns 404."""
        _, _, sede = seed_admin_v2(db_session)
        headers = auth_headers_v2(client)
        resp = client.get(f"/api/projects/{_uuid.uuid4()}", headers=headers)
        assert resp.status_code == 404

    def test_uuid_format_in_response(self, client, db_session):
        """All UUID fields in responses are valid UUID strings, not integers."""
        _, _, sede = seed_admin_v2(db_session)
        proj = create_project_factory(db_session)
        create_task_factory(db_session, proj.id)
        headers = auth_headers_v2(client)
        resp = client.get(f"/api/projects/{proj.id}", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        _assert_uuid(data["id"])
        for task in data.get("tasks", []):
            _assert_uuid(task["id"])
            _assert_uuid(task["project_id"])

    def test_uuid_not_coerced_to_number(self, client, db_session):
        """Verifies Number() coercion bug is not present on any UUID field."""
        _, _, sede = seed_admin_v2(db_session)
        proj = create_project_factory(db_session, owner_id=_uuid.uuid4())
        headers = auth_headers_v2(client)
        resp = client.get(f"/api/projects/{proj.id}", headers=headers)
        assert resp.status_code == 200
        owner_id = resp.json()["owner_id"]
        _assert_uuid(owner_id)
        # Ensure it's not NaN (what Number() yields for UUID)
        import math
        assert not (isinstance(owner_id, float) and math.isnan(owner_id))

    def test_staff_only_endpoints(self, client, db_session):
        """DELETE project requires staff/admin."""
        from tests.conftest import seed_user_with_role_v2
        user, _, _ = seed_user_with_role_v2(db_session, role_name="member", email="user@test.com")
        _, _, sede = seed_admin_v2(db_session)
        proj = create_project_factory(db_session)

        # Non-staff user
        headers = auth_headers_v2(client, email="user@test.com")
        resp = client.delete(f"/api/projects/{proj.id}", headers=headers)
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"

    def test_pipeline_creates_project(self, client, db_session):
        """Full creation -> list -> get -> update -> delete lifecycle works."""
        _, _, sede = seed_admin_v2(db_session)
        headers = auth_headers_v2(client)

        # Create
        resp = client.post("/api/projects", json={"title": "Lifecycle", "status": "planning"}, headers=headers)
        assert resp.status_code == 201
        pid = resp.json()["id"]

        # List
        resp = client.get("/api/projects", headers=headers)
        assert len(resp.json()) == 1

        # Get
        resp = client.get(f"/api/projects/{pid}", headers=headers)
        assert resp.status_code == 200

        # Update
        resp = client.patch(f"/api/projects/{pid}", json={"status": "active"}, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "active"

        # Delete
        resp = client.delete(f"/api/projects/{pid}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

        # Verify gone
        resp = client.get("/api/projects", headers=headers)
        assert resp.json() == []


