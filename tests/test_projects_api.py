"""Comprehensive API tests for the Projects module.

Covers all 34 API endpoints in /api/projects/* using factories and
the conftest.py fixtures (db_session, client, seed_admin, auth_headers).

Organised in 12 labelled sections (A-L) with 83 individual tests.
"""

from __future__ import annotations

import uuid as _uuid

import pytest
from sqlalchemy import event

from backend.models_crm import (
    ChatMessage,  # noqa: F401 — register for import side effects
    Persona,
)
from backend.models_projects import (
    Project,
    ProjectAttachment,
    ProjectComment,
    ProjectExpense,
    ProjectFile,
    ProjectIndicator,
    ProjectIndicatorRecord,
    ProjectPhase,
    ProjectTask,
    ProjectTaskDependency,
)
from tests.conftest import auth_headers, seed_admin, seed_user_with_role
from tests.factories_projects import (
    create_attachment_factory,
    create_comment_factory,
    create_default_phases_factory,
    create_message_factory,
    create_milestone_factory,
    create_project_factory,
    create_subtask_factory,
    create_supply_factory,
    create_task_factory,
    create_whiteboard_factory,
    create_wiki_factory,
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
    def test_assignee_candidates_use_projects_permission_and_search_only_same_sede(self, client, db_session):
        from backend.models_crm import Persona

        _, _, sede_a = seed_admin(db_session, email="assignee-admin-a@test.com")
        _, _, sede_b = seed_admin(db_session, email="assignee-admin-b@test.com")
        same_sede = Persona(first_name="Lucía", last_name="Ramírez", sede_id=sede_a.id)
        other_sede = Persona(first_name="Lucía", last_name="Ramírez", sede_id=sede_b.id)
        db_session.add_all([same_sede, other_sede])
        db_session.flush()
        reader, _, _ = seed_user_with_role(
            db_session,
            role_name="ProjectsOnlyReader",
            email="projects-only-reader@test.com",
            sede_id=sede_a.id,
            permisos={"projects:read": "allow"},
        )

        response = client.get(
            "/api/projects/assignee-candidates?search=Luc%C3%ADa&limit=50",
            headers=auth_headers(client, email=reader.email),
        )

        assert response.status_code == 200, response.text
        payload = response.json()
        candidate_ids = {item["id"] for item in payload}
        assert str(same_sede.id) in candidate_ids
        assert str(other_sede.id) not in candidate_ids
        assert all(set(item) == {"id", "nombre_completo"} for item in payload)

    def test_assignee_candidate_detail_is_scoped_to_actor_sede(self, client, db_session):
        from backend.models_crm import Persona

        _, _, sede_a = seed_admin(db_session, email="assignee-detail-a@test.com")
        _, _, sede_b = seed_admin(db_session, email="assignee-detail-b@test.com")
        own_person = Persona(first_name="Persona", last_name="Local", sede_id=sede_a.id)
        foreign_person = Persona(first_name="Persona", last_name="Externa", sede_id=sede_b.id)
        db_session.add_all([own_person, foreign_person])
        db_session.flush()
        reader, _, _ = seed_user_with_role(
            db_session,
            role_name="ProjectsOnlyDetailReader",
            email="projects-only-detail-reader@test.com",
            sede_id=sede_a.id,
            permisos={"projects:read": "allow"},
        )
        headers = auth_headers(client, email=reader.email)

        own_response = client.get(
            f"/api/projects/assignee-candidates/{own_person.id}",
            headers=headers,
        )
        assert own_response.status_code == 200, own_response.text
        assert own_response.json() == {
            "id": str(own_person.id),
            "nombre_completo": "Persona Local",
        }

        response = client.get(
            f"/api/projects/assignee-candidates/{foreign_person.id}",
            headers=headers,
        )

        assert response.status_code == 404, response.text

    def test_list_projects_empty(self, client, db_session):
        """GET /api/projects without data returns empty list."""
        seed_admin(db_session)
        headers = auth_headers(client)
        resp = client.get("/api/projects", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_projects_page_paginates_and_filters(self, client, db_session):
        seed_admin(db_session)
        headers = auth_headers(client)
        create_project_factory(db_session, title="Alpha Uno", status="active")
        create_project_factory(db_session, title="Alpha Dos", status="planning")
        create_project_factory(db_session, title="Beta", status="active")

        first = client.get("/api/projects/page?offset=0&limit=2", headers=headers)
        second = client.get("/api/projects/page?offset=2&limit=2", headers=headers)
        assert first.status_code == second.status_code == 200
        first_page = first.json()
        second_page = second.json()
        assert first_page["total"] == second_page["total"] == 3
        assert len(first_page["items"]) == 2
        assert len(second_page["items"]) == 1
        assert first_page["skip"] == 0 and first_page["limit"] == 2
        assert set(item["id"] for item in first_page["items"]).isdisjoint(
            item["id"] for item in second_page["items"]
        )

        filtered = client.get(
            "/api/projects/page?status=active&search=Alpha",
            headers=headers,
        )
        assert filtered.status_code == 200
        assert filtered.json()["total"] == 1
        assert filtered.json()["items"][0]["title"] == "Alpha Uno"

    def test_list_projects_page_rejects_unbounded_limit(self, client, db_session):
        seed_admin(db_session)
        response = client.get("/api/projects/page?limit=101", headers=auth_headers(client))
        assert response.status_code == 422

    def test_project_summary_page_returns_aggregates_without_child_graphs(self, client, db_session):
        seed_admin(db_session)
        headers = auth_headers(client)
        project = create_project_factory(db_session, title="Proyecto resumido", progress_mode="auto_tasks")
        create_task_factory(db_session, project.id, title="Pendiente", status="todo")
        create_task_factory(db_session, project.id, title="En curso", status="in_progress")
        create_task_factory(db_session, project.id, title="Completada", status="completed")

        response = client.get("/api/projects/summary-page", headers=headers)

        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["total"] == 1
        item = payload["items"][0]
        assert item["id"] == str(project.id)
        assert item["task_count"] == 3
        assert item["completed_task_count"] == 1
        assert item["in_progress_task_count"] == 1
        assert item["progress_percent"] == 33
        assert item["health_status"] == "on_track"
        assert "tasks" not in item
        assert "milestones" not in item
        assert "attachments" not in item

    def test_project_summary_page_respects_manual_and_milestone_progress_modes(self, client, db_session):
        seed_admin(db_session)
        headers = auth_headers(client)
        manual = create_project_factory(
            db_session,
            title="Progreso manual",
            progress_mode="manual",
            manual_progress=62.5,
        )
        milestone_project = create_project_factory(
            db_session,
            title="Progreso por hitos",
            progress_mode="milestones",
        )
        create_milestone_factory(db_session, milestone_project.id, title="Hito logrado", is_completed=True)
        create_milestone_factory(db_session, milestone_project.id, title="Hito pendiente", is_completed=False)

        response = client.get("/api/projects/summary-page?limit=10", headers=headers)

        assert response.status_code == 200, response.text
        by_id = {item["id"]: item for item in response.json()["items"]}
        assert by_id[str(manual.id)]["progress_percent"] == 62
        assert by_id[str(milestone_project.id)]["progress_percent"] == 50

    def test_project_summary_page_query_count_does_not_grow_per_project(self, client, db_session):
        seed_admin(db_session)
        headers = auth_headers(client)
        engine = db_session.get_bind()

        def count_reads(search_term: str) -> int:
            statements: list[str] = []

            def record_statement(_conn, _cursor, statement, _parameters, _context, _executemany):
                if statement.lstrip().upper().startswith("SELECT"):
                    statements.append(statement)

            event.listen(engine, "before_cursor_execute", record_statement)
            try:
                response = client.get(
                    f"/api/projects/summary-page?search={search_term}&limit=100",
                    headers=headers,
                )
            finally:
                event.remove(engine, "before_cursor_execute", record_statement)
            assert response.status_code == 200, response.text
            return len(statements)

        single = create_project_factory(db_session, title="Query Budget Single")
        create_task_factory(db_session, single.id, title="Single task")
        single_query_count = count_reads("Query Budget Single")

        for index in range(8):
            project = create_project_factory(db_session, title=f"Query Budget Batch {index}")
            create_task_factory(db_session, project.id, title=f"Batch task {index}")
        batch_query_count = count_reads("Query Budget Batch")

        assert batch_query_count == single_query_count

    def test_project_summary_page_reduces_payload_with_tasks_and_attachments(self, client, db_session):
        seed_admin(db_session)
        headers = auth_headers(client)
        project = create_project_factory(db_session, title="Payload benchmark")
        for task_index in range(24):
            task = ProjectTask(
                project_id=project.id,
                title=f"Tarea representativa {task_index}",
                description="Detalle de tarea con contexto operativo y criterios de aceptación. " * 4,
                status="todo",
                priority="medium",
                assignee_id=project.owner_id,
                labels=["operaciones", "planificación"],
            )
            db_session.add(task)
            db_session.flush()
            db_session.add_all([
                ProjectAttachment(
                    task_id=task.id,
                    filename=f"evidencia_{task_index}_{attachment_index}_documento_de_trabajo.pdf",
                    file_url=f"/api/static/projects/{project.id}/tasks/{task.id}/evidencia_{attachment_index}.pdf",
                    file_type="application/pdf",
                    file_size=32_768,
                    uploader_id=project.owner_id,
                )
                for attachment_index in range(2)
            ])
        db_session.commit()

        summary_response = client.get(
            "/api/projects/summary-page?search=Payload benchmark",
            headers=headers,
        )
        full_response = client.get(
            "/api/projects/page?search=Payload benchmark",
            headers=headers,
        )

        assert summary_response.status_code == full_response.status_code == 200
        summary_bytes = len(summary_response.content)
        full_bytes = len(full_response.content)
        assert summary_bytes * 5 < full_bytes, (
            f"Expected at least 80% payload reduction; summary={summary_bytes}B, full={full_bytes}B"
        )

    def test_legacy_project_list_ignores_pagination_parameters(self, client, db_session):
        seed_admin(db_session)
        headers = auth_headers(client)
        create_project_factory(db_session, title="Legacy Uno")
        create_project_factory(db_session, title="Legacy Dos")
        create_project_factory(db_session, title="Legacy Tres")

        first = client.get("/api/projects?offset=0&limit=2", headers=headers)
        second = client.get("/api/projects?offset=2&limit=2", headers=headers)
        assert first.status_code == second.status_code == 200
        assert len(first.json()) == len(second.json()) == 3
        assert {item["id"] for item in first.json()} == {item["id"] for item in second.json()}

    def test_legacy_project_list_returns_all_projects(self, client, db_session):
        seed_admin(db_session)
        headers = auth_headers(client)
        for index in range(51):
            create_project_factory(db_session, title=f"Bounded legacy {index:02d}")

        response = client.get("/api/projects", headers=headers)

        assert response.status_code == 200
        assert len(response.json()) == 51

    def test_create_project(self, client, db_session):
        """POST /api/projects creates a project and returns 201."""
        _, _, sede = seed_admin(db_session)
        headers = auth_headers(client)
        payload = dict(title="Proyecto de prueba", description="Test", status="planning", color="#3b82f6")
        resp = client.post("/api/projects", json=payload, headers=headers)
        assert resp.status_code == 201, f"Body: {resp.text}"
        data = resp.json()
        assert data["title"] == "Proyecto de prueba"
        assert data["status"] == "planning"
        _assert_uuid(data["id"])
        _assert_datetime(data["created_at"])

    def test_create_project_without_owner_or_actor_persona_returns_409(self, client, db_session, monkeypatch):
        import backend.api.projects as projects_api

        seed_admin(db_session, email="project-ownerless-create@test.com")
        monkeypatch.setattr(projects_api, "get_user_persona_id", lambda _db, _user_id: None)
        projects_before = db_session.query(Project).count()

        response = client.post(
            "/api/projects",
            json={"title": "Proyecto sin responsable"},
            headers=auth_headers(client, email="project-ownerless-create@test.com"),
        )

        assert response.status_code == 409, response.text
        assert "responsable" in response.json()["detail"].lower()
        assert db_session.query(Project).count() == projects_before

    def test_create_project_rolls_back_when_default_phases_cannot_be_created(
        self, client, db_session, monkeypatch
    ):
        from fastapi import HTTPException

        import backend.api.projects as projects_api

        seed_admin(db_session, email="project-phase-failure@test.com")
        projects_before = db_session.query(Project).count()
        phases_before = db_session.query(ProjectPhase).count()
        create_default_phases = projects_api.crud.create_default_phases

        def fail_default_phases(_db, _project_id, *, commit=True):
            create_default_phases(_db, _project_id, commit=commit)
            raise HTTPException(status_code=503, detail="Fallo simulado al crear fases")

        monkeypatch.setattr(projects_api.crud, "create_default_phases", fail_default_phases)
        response = client.post(
            "/api/projects",
            json={"title": "No debe persistir sin fases"},
            headers=auth_headers(client, email="project-phase-failure@test.com"),
        )

        assert response.status_code == 503, response.text
        assert db_session.query(Project).count() == projects_before
        assert db_session.query(ProjectPhase).count() == phases_before

    # PEND-QUALITY-PROJECT-TITLE-NORM-001 (anotación diferida del code
    # review del 2026-07-16, aplicada el mismo día): ``ProjectBase.title``
    # rechaza título vacío / whitespace-only en POST y PATCH con 422.
    def test_create_project_with_empty_title_returns_422(self, client, db_session):
        _, _, sede = seed_admin(db_session)
        headers = auth_headers(client)
        resp = client.post("/api/projects", json={"title": "", "status": "planning"}, headers=headers)
        assert resp.status_code == 422

    def test_create_project_with_whitespace_title_returns_422(self, client, db_session):
        _, _, sede = seed_admin(db_session)
        headers = auth_headers(client)
        resp = client.post("/api/projects", json={"title": "   ", "status": "planning"}, headers=headers)
        assert resp.status_code == 422

    def test_create_project_title_matches_database_limit(self, client, db_session):
        """A 200-char title persists; the first unsupported character is a 422."""
        seed_admin(db_session)
        headers = auth_headers(client)
        accepted = client.post(
            "/api/projects", json={"title": "P" * 200, "status": "planning"}, headers=headers,
        )
        assert accepted.status_code == 201, accepted.text
        assert len(accepted.json()["title"]) == 200

        rejected = client.post(
            "/api/projects", json={"title": "P" * 201, "status": "planning"}, headers=headers,
        )
        assert rejected.status_code == 422

    def test_update_project_title_matches_database_limit(self, client, db_session):
        seed_admin(db_session)
        project = create_project_factory(db_session)
        headers = auth_headers(client)
        accepted = client.patch(
            f"/api/projects/{project.id}", json={"title": "P" * 200}, headers=headers,
        )
        assert accepted.status_code == 200, accepted.text
        assert len(accepted.json()["title"]) == 200

        rejected = client.patch(
            f"/api/projects/{project.id}", json={"title": "P" * 201}, headers=headers,
        )
        assert rejected.status_code == 422

    def test_update_project_with_empty_title_returns_422(self, client, db_session):
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        headers = auth_headers(client)
        resp = client.patch(f"/api/projects/{proj.id}", json={"title": ""}, headers=headers)
        assert resp.status_code == 422

    def test_create_project_creates_default_phases(self, client, db_session):
        """Creating a project also creates 4 default Kanban phases."""
        _, _, sede = seed_admin(db_session)
        headers = auth_headers(client)
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
        _, _, sede = seed_admin(db_session)
        headers = auth_headers(client)
        client.post("/api/projects", json={"title": "List Test"}, headers=headers)
        resp = client.get("/api/projects", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_get_project_by_id(self, client, db_session):
        """GET /api/projects/{id} returns the project with tasks and milestones."""
        from datetime import datetime, timezone

        _, _, sede = seed_admin(db_session)
        data = setup_project_with_all_relations(db_session)
        attachment = create_attachment_factory(db_session, data["tasks"][0].id, filename="detalle.pdf")
        deleted_attachment = create_attachment_factory(db_session, data["tasks"][0].id, filename="archivado.pdf")
        deleted_attachment.deleted_at = datetime.now(timezone.utc)
        db_session.commit()
        headers = auth_headers(client)
        project_id = str(data["project"].id)

        resp = client.get(f"/api/projects/{project_id}", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == project_id
        assert len(body["tasks"]) >= 1
        assert len(body["milestones"]) >= 1
        first_task = next(task for task in body["tasks"] if task["id"] == str(data["tasks"][0].id))
        assert any(
            item["id"] == str(attachment.id) and item["filename"] == "detalle.pdf" for item in first_task["attachments"]
        )
        assert all(item["filename"] != "archivado.pdf" for item in first_task["attachments"])

    def test_get_project_not_found(self, client, db_session):
        """GET /api/projects/{nonexistent} returns 404."""
        seed_admin(db_session)
        headers = auth_headers(client)
        fake_id = str(_uuid.uuid4())
        resp = client.get(f"/api/projects/{fake_id}", headers=headers)
        assert resp.status_code == 404

    def test_update_project(self, client, db_session):
        """PATCH /api/projects/{id} updates fields."""
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        headers = auth_headers(client)
        resp = client.patch(
            f"/api/projects/{proj.id}", json={"title": "Actualizado", "status": "active"}, headers=headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["title"] == "Actualizado"
        assert body["status"] == "active"

    def test_delete_project(self, client, db_session):
        """DELETE /api/projects/{id} soft-deletes the project."""

        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        headers = auth_headers(client)
        resp = client.delete(f"/api/projects/{proj.id}", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["deleted"] == str(proj.id)
        # Verify soft delete in DB
        db_session.refresh(proj)
        assert proj.deleted_at is not None

    def test_delete_project_removes_from_list(self, client, db_session):
        """Deleted project no longer appears in listing."""
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        headers = auth_headers(client)
        client.delete(f"/api/projects/{proj.id}", headers=headers)
        resp = client.get("/api/projects", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 0

    def test_list_projects_filtered_by_owner(self, client, db_session):
        """GET /api/projects?owner_id={id} filters by owner."""
        from backend.models_crm import Persona

        _, _, sede = seed_admin(db_session)
        owner_a = Persona(id=_uuid.uuid4(), first_name="Alice", last_name="Owner", email="alice@test.com")
        owner_b = Persona(id=_uuid.uuid4(), first_name="Bob", last_name="Owner", email="bob@test.com")
        db_session.add_all([owner_a, owner_b])
        db_session.flush()

        proj_a = create_project_factory(db_session, owner_id=owner_a.id, title="Proyecto Alice")
        proj_b = create_project_factory(db_session, owner_id=owner_b.id, title="Proyecto Bob")

        headers = auth_headers(client)

        # Filter by owner_a → only proj_a
        resp = client.get(f"/api/projects?owner_id={owner_a.id}", headers=headers)
        assert resp.status_code == 200
        projects = resp.json()
        assert len(projects) == 1, f"Expected 1, got {len(projects)}"
        assert projects[0]["title"] == "Proyecto Alice"

        # Filter by owner_b → only proj_b
        resp = client.get(f"/api/projects?owner_id={owner_b.id}", headers=headers)
        assert resp.status_code == 200
        projects = resp.json()
        assert len(projects) == 1, f"Expected 1, got {len(projects)}"
        assert projects[0]["title"] == "Proyecto Bob"

        # Filter by non-existent owner → empty
        resp = client.get(f"/api/projects?owner_id={_uuid.uuid4()}", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []

        # Without filter → both
        resp = client.get("/api/projects", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 2


# ── B: Phases ────────────────────────────────────────────────────────────
# Routes: GET /projects/{id}/phases, PUT /projects/{id}/phases


class TestPhases:
    def test_list_default_phases(self, client, db_session):
        """GET /projects/{id}/phases returns the 4 default phases."""
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        create_default_phases_factory(db_session, proj.id)
        headers = auth_headers(client)
        resp = client.get(f"/api/projects/{proj.id}/phases", headers=headers)
        assert resp.status_code == 200
        phases = resp.json()
        assert len(phases) == 4
        slugs = {p["slug"] for p in phases}
        assert slugs == {"todo", "in_progress", "review", "completed"}

    def test_set_phases_reorder(self, client, db_session):
        """PUT /projects/{id}/phases replaces phases with new order."""
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        create_default_phases_factory(db_session, proj.id)
        headers = auth_headers(client)
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
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        create_default_phases_factory(db_session, proj.id)
        create_task_factory(db_session, proj.id, status="todo")
        headers = auth_headers(client)
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
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        headers = auth_headers(client)
        resp = client.post(
            f"/api/projects/{proj.id}/tasks",
            json={"title": "Mi tarea", "status": "todo", "priority": "high"},
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        _assert_uuid(data["id"])
        assert data["title"] == "Mi tarea"

    def test_create_task_rejects_parent_from_another_project(self, client, db_session):
        _, _, sede = seed_admin(db_session, email="project-task-parent-cross@test.com")
        project = create_project_factory(db_session, sede_id=sede.id)
        other_project = create_project_factory(db_session, sede_id=sede.id)
        foreign_parent = create_task_factory(db_session, other_project.id)

        response = client.post(
            f"/api/projects/{project.id}/tasks",
            json={"title": "No debe vincular", "parent_id": str(foreign_parent.id)},
            headers=auth_headers(client, email="project-task-parent-cross@test.com"),
        )

        assert response.status_code == 404, response.text
        assert db_session.query(ProjectTask).filter_by(project_id=project.id).count() == 0

    def test_create_task_accepts_parent_from_same_project(self, client, db_session):
        _, _, sede = seed_admin(db_session, email="project-task-parent-local@test.com")
        project = create_project_factory(db_session, sede_id=sede.id)
        parent = create_task_factory(db_session, project.id)

        response = client.post(
            f"/api/projects/{project.id}/tasks",
            json={"title": "Subtarea", "parent_id": str(parent.id)},
            headers=auth_headers(client, email="project-task-parent-local@test.com"),
        )

        assert response.status_code == 201, response.text
        assert response.json()["parent_id"] == str(parent.id)

    def test_crud_rejects_parent_from_another_project_without_persisting(self, db_session):
        from backend.crud.projects import create_project_task
        from backend.schemas.projects import ProjectTaskCreate

        project = create_project_factory(db_session)
        other_project = create_project_factory(db_session)
        foreign_parent = create_task_factory(db_session, other_project.id)
        task = ProjectTaskCreate(
            title="No debe vincular",
            project_id=project.id,
            parent_id=foreign_parent.id,
        )

        with pytest.raises(ValueError, match="same project"):
            create_project_task(db_session, task)

        assert db_session.query(ProjectTask).filter_by(project_id=project.id).count() == 0

    # ── PEND-QUALITY-TASK-CREATE-001 (cierre 2026-07-16) ──
    # Cobertura de validación de título no vacío en POST y PATCH.
    def test_create_task_with_empty_title_returns_422(self, client, db_session):
        """PEND-QUALITY-TASK-CREATE-001: la vista list enviaba ``title: ''``
        literal; el backend debe rechazar con 422 vía ``min_length=1``."""
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        headers = auth_headers(client)
        resp = client.post(
            f"/api/projects/{proj.id}/tasks",
            json={"title": "", "status": "todo"},
            headers=headers,
        )
        assert resp.status_code == 422

    def test_create_task_with_whitespace_title_returns_422(self, client, db_session):
        """El field_validator ``mode='before'`` hace ``strip()`` antes de
        validar, por lo que '   ' queda como '' y falla ``min_length=1``."""
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        headers = auth_headers(client)
        resp = client.post(
            f"/api/projects/{proj.id}/tasks",
            json={"title": "   ", "status": "todo"},
            headers=headers,
        )
        assert resp.status_code == 422

    def test_create_task_title_matches_database_limit(self, client, db_session):
        """A 200-char title persists; the first unsupported character is a 422."""
        seed_admin(db_session)
        proj = create_project_factory(db_session)
        headers = auth_headers(client)
        accepted = client.post(
            f"/api/projects/{proj.id}/tasks",
            json={"title": "T" * 200, "status": "todo"},
            headers=headers,
        )
        assert accepted.status_code == 201, accepted.text
        assert len(accepted.json()["title"]) == 200

        rejected = client.post(
            f"/api/projects/{proj.id}/tasks",
            json={"title": "T" * 201, "status": "todo"},
            headers=headers,
        )
        assert rejected.status_code == 422

    def test_update_task_title_matches_database_limit(self, client, db_session):
        seed_admin(db_session)
        project = create_project_factory(db_session)
        task = create_task_factory(db_session, project.id, title="Original")
        headers = auth_headers(client)
        accepted = client.patch(
            f"/api/projects/tasks/{task.id}", json={"title": "T" * 200}, headers=headers,
        )
        assert accepted.status_code == 200, accepted.text
        assert len(accepted.json()["title"]) == 200

        rejected = client.patch(
            f"/api/projects/tasks/{task.id}", json={"title": "T" * 201}, headers=headers,
        )
        assert rejected.status_code == 422

    def test_update_task_with_empty_title_returns_422(self, client, db_session):
        """PATCH con title='' también debe ser rechazado para no permitir
        ``clear title`` accidental."""
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        task = create_task_factory(db_session, proj.id, title="Original")
        headers = auth_headers(client)
        resp = client.patch(
            f"/api/projects/tasks/{task.id}",
            json={"title": ""},
            headers=headers,
        )
        assert resp.status_code == 422

    def test_list_tasks_empty(self, client, db_session):
        """GET /projects/{id}/tasks returns [] when no tasks."""
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        headers = auth_headers(client)
        resp = client.get(f"/api/projects/{proj.id}/tasks", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_tasks_with_data(self, client, db_session):
        """GET /projects/{id}/tasks returns created tasks."""
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        create_task_factory(db_session, proj.id, title="Task A")
        create_task_factory(db_session, proj.id, title="Task B")
        headers = auth_headers(client)
        resp = client.get(f"/api/projects/{proj.id}/tasks", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_list_tasks_with_status_filter(self, client, db_session):
        """GET /projects/{id}/tasks?status=completed filters tasks."""
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        # Ensure created_at ordering is deterministic
        create_task_factory(db_session, proj.id, status="completed", title="Done!")
        create_task_factory(db_session, proj.id, status="todo", title="Todo")
        headers = auth_headers(client)
        resp = client.get(f"/api/projects/{proj.id}/tasks?status=completed", headers=headers)
        assert resp.status_code == 200
        tasks = resp.json()
        assert len(tasks) == 1
        assert tasks[0]["status"] == "completed"

    def test_get_task(self, client, db_session):
        """GET /projects/tasks/{task_id} returns the task."""
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        task = create_task_factory(db_session, proj.id)
        headers = auth_headers(client)
        resp = client.get(f"/api/projects/tasks/{task.id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == str(task.id)

    def test_update_task_flat(self, client, db_session):
        """PATCH /projects/tasks/{task_id} updates a task."""
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        task = create_task_factory(db_session, proj.id, title="Old")
        headers = auth_headers(client)
        resp = client.patch(f"/api/projects/tasks/{task.id}", json={"title": "New Title"}, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["title"] == "New Title"

    def test_update_task_flat_records_project_activity(self, client, db_session):
        """Flat task edits, used by quick-edit views, appear in the activity feed."""
        from backend.models_projects import ProjectActivityLog

        _, persona, sede = seed_admin(db_session, email="flat-task-activity@test.com")
        project = create_project_factory(db_session, sede_id=sede.id)
        task = create_task_factory(db_session, project.id, title="Antes de editar")

        response = client.patch(
            f"/api/projects/tasks/{task.id}",
            json={"title": "Después de editar"},
            headers=auth_headers(client, email="flat-task-activity@test.com"),
        )

        assert response.status_code == 200, response.text
        activities = (
            db_session.query(ProjectActivityLog)
            .filter_by(project_id=project.id, action_type="task_updated")
            .all()
        )
        assert len(activities) == 1
        assert activities[0].persona_id == persona.id
        assert "title" in activities[0].description
        assert "Después de editar" in activities[0].description

        feed_response = client.get(
            f"/api/projects/activities?project_id={project.id}",
            headers=auth_headers(client, email="flat-task-activity@test.com"),
        )
        assert feed_response.status_code == 200, feed_response.text
        feed_items = feed_response.json()
        assert len(feed_items) == 1
        assert feed_items[0]["kind"] == "task_updated"
        assert feed_items[0]["project_id"] == str(project.id)
        assert "Después de editar" in feed_items[0]["description"]

        no_op_response = client.patch(
            f"/api/projects/tasks/{task.id}",
            json={"title": "Después de editar"},
            headers=auth_headers(client, email="flat-task-activity@test.com"),
        )
        assert no_op_response.status_code == 200, no_op_response.text
        assert (
            db_session.query(ProjectActivityLog)
            .filter_by(project_id=project.id, action_type="task_updated")
            .count()
            == 1
        ), "Un PATCH sin cambios no debe duplicar eventos de actividad"

    def test_update_task_scoped(self, client, db_session):
        """PATCH /projects/{id}/tasks/{task_id} also works."""
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        task = create_task_factory(db_session, proj.id, priority="low")
        headers = auth_headers(client)
        resp = client.patch(f"/api/projects/{proj.id}/tasks/{task.id}", json={"priority": "urgent"}, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["priority"] == "urgent"

    def test_create_task_normalizes_old_priority(self, client, db_session):
        """Old priority 'normal' is normalized to 'medium' on create."""
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        headers = auth_headers(client)
        resp = client.post(
            f"/api/projects/{proj.id}/tasks",
            json={"title": "Old priority", "status": "todo", "priority": "normal"},
            headers=headers,
        )
        assert resp.status_code == 201
        assert resp.json()["priority"] == "medium"

    def test_update_task_normalizes_old_status(self, client, db_session):
        """Old status values 'done' and 'blocked' are normalized on update."""
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        task = create_task_factory(db_session, proj.id, status="todo")
        headers = auth_headers(client)

        resp = client.patch(
            f"/api/projects/{proj.id}/tasks/{task.id}",
            json={"status": "done"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"

        resp = client.patch(
            f"/api/projects/{proj.id}/tasks/{task.id}",
            json={"status": "blocked"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "todo"

    def test_delete_task(self, client, db_session):
        """DELETE /projects/{id}/tasks/{task_id} soft-deletes."""
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        task = create_task_factory(db_session, proj.id)
        headers = auth_headers(client)
        resp = client.delete(f"/api/projects/{proj.id}/tasks/{task.id}", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["deleted"] == str(task.id)
        # Verify soft delete in DB
        db_session.refresh(task)
        assert task.deleted_at is not None

    def test_get_task_not_found(self, client, db_session):
        """GET /projects/tasks/{fake_uuid} returns 404."""
        _, _, sede = seed_admin(db_session)
        headers = auth_headers(client)
        resp = client.get(f"/api/projects/tasks/{_uuid.uuid4()}", headers=headers)
        assert resp.status_code == 404

    def test_create_task_with_uuid_assignee(self, client, db_session):
        """POST task with UUID assignee_id — no Number() coercion."""
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        persona_id = str(_uuid.uuid4())
        # Create the persona so the FK resolves
        db_session.add(
            Persona(
                id=_uuid.UUID(persona_id),
                first_name="Assign",
                last_name="Test",
                email="assignee@test.com",
                sede_id=sede.id,
            )
        )
        db_session.flush()
        headers = auth_headers(client)
        resp = client.post(
            f"/api/projects/{proj.id}/tasks",
            json={"title": "UUID assignee", "assignee_id": persona_id},
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["assignee_id"] == persona_id

    def test_create_task_with_node(self, client, db_session):
        """POST task with a node persists it (F2: nodos operativos reales)."""
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        headers = auth_headers(client)
        resp = client.post(
            f"/api/projects/{proj.id}/tasks",
            json={"title": "Tarea nodo", "node": "nutrition"},
            headers=headers,
        )
        assert resp.status_code == 201
        assert resp.json()["node"] == "nutrition"

    def test_update_task_node(self, client, db_session):
        """PATCH task node updates it (F2)."""
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        task = create_task_factory(db_session, proj.id, node="digital")
        headers = auth_headers(client)
        resp = client.patch(
            f"/api/projects/{proj.id}/tasks/{task.id}",
            json={"node": "nutrition"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["node"] == "nutrition"

    def test_create_task_node_blank_becomes_null(self, client, db_session):
        """POST task with node='' or whitespace stores null (F2)."""
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        headers = auth_headers(client)
        resp = client.post(
            f"/api/projects/{proj.id}/tasks",
            json={"title": "Tarea sin nodo", "node": "   "},
            headers=headers,
        )
        assert resp.status_code == 201
        assert resp.json()["node"] is None


# ── D: Subtasks ──────────────────────────────────────────────────────────
# Routes (3): POST/PATCH/DELETE /projects/{id}/tasks/{tid}/subtasks[/{sid}]


class TestSubtasks:
    def test_create_subtask(self, client, db_session):
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        parent = create_task_factory(db_session, proj.id)
        headers = auth_headers(client)
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
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        parent = create_task_factory(db_session, proj.id)
        sub = create_subtask_factory(db_session, parent.id, proj.id, title="Old Sub")
        headers = auth_headers(client)
        resp = client.patch(
            f"/api/projects/{proj.id}/tasks/{parent.id}/subtasks/{sub.id}",
            json={"title": "Updated Sub"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated Sub"

    def test_delete_subtask(self, client, db_session):
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        parent = create_task_factory(db_session, proj.id)
        sub = create_subtask_factory(db_session, parent.id, proj.id)
        headers = auth_headers(client)
        resp = client.delete(
            f"/api/projects/{proj.id}/tasks/{parent.id}/subtasks/{sub.id}",
            headers=headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["deleted"] == str(sub.id)
        # Verify soft delete in DB
        db_session.refresh(sub)
        assert sub.deleted_at is not None

    def test_subtask_mismatched_parent(self, client, db_session):
        """PATCH subtask with wrong parent returns 404."""
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        t1 = create_task_factory(db_session, proj.id)
        t2 = create_task_factory(db_session, proj.id)
        sub = create_subtask_factory(db_session, t1.id, proj.id)
        headers = auth_headers(client)
        resp = client.patch(
            f"/api/projects/{proj.id}/tasks/{t2.id}/subtasks/{sub.id}",
            json={"title": "Nope"},
            headers=headers,
        )
        assert resp.status_code == 404


class TestSoftDeletedProjectChildren:
    def test_project_responses_exclude_deleted_children_and_use_active_metrics(self, client, db_session):
        from datetime import datetime, timedelta, timezone

        _, _, sede = seed_admin(db_session)
        project = create_project_factory(db_session, sede_id=sede.id, title="Proyecto hijos activos")
        active_task = create_task_factory(
            db_session,
            project.id,
            title="Tarea activa",
            status="todo",
            due_date=datetime.now(timezone.utc) + timedelta(days=3),
        )
        deleted_completed_task = create_task_factory(
            db_session,
            project.id,
            title="Tarea completada eliminada",
            status="completed",
        )
        deleted_overdue_tasks = [
            create_task_factory(
                db_session,
                project.id,
                title=f"Tarea vencida eliminada {index}",
                status="todo",
                due_date=datetime.now(timezone.utc) - timedelta(days=3),
            )
            for index in range(2)
        ]
        active_milestone = create_milestone_factory(
            db_session,
            project.id,
            title="Hito activo",
            is_completed=False,
        )
        deleted_milestone = create_milestone_factory(
            db_session,
            project.id,
            title="Hito completado eliminado",
            is_completed=True,
        )
        deleted_at = datetime.now(timezone.utc)
        deleted_completed_task.deleted_at = deleted_at
        deleted_milestone.deleted_at = deleted_at
        for task in deleted_overdue_tasks:
            task.deleted_at = deleted_at
        project.progress_mode = "auto_tasks"
        db_session.commit()

        headers = auth_headers(client)
        detail_response = client.get(f"/api/projects/{project.id}", headers=headers)
        assert detail_response.status_code == 200, detail_response.text
        detail = detail_response.json()
        assert [task["id"] for task in detail["tasks"]] == [str(active_task.id)]
        assert [milestone["id"] for milestone in detail["milestones"]] == [str(active_milestone.id)]
        assert detail["progress_percent"] == 0
        assert detail["health_status"] == "on_track"

        milestones_project = create_project_factory(
            db_session,
            sede_id=sede.id,
            title="Proyecto progreso por hitos",
            progress_mode="milestones",
        )
        active_progress_milestone = create_milestone_factory(
            db_session,
            milestones_project.id,
            title="Hito de progreso activo",
            is_completed=False,
        )
        deleted_progress_milestone = create_milestone_factory(
            db_session,
            milestones_project.id,
            title="Hito de progreso eliminado",
            is_completed=True,
        )
        deleted_progress_milestone.deleted_at = datetime.now(timezone.utc)
        db_session.commit()

        page_response = client.get(
            f"/api/projects/page?search={milestones_project.title}",
            headers=headers,
        )
        assert page_response.status_code == 200, page_response.text
        item = next(
            project_item
            for project_item in page_response.json()["items"]
            if project_item["id"] == str(milestones_project.id)
        )
        assert [milestone["id"] for milestone in item["milestones"]] == [str(active_progress_milestone.id)]
        assert item["progress_percent"] == 0


# ── E: Milestones ─────────────────────────────────────────────────────────
# Routes (5): GET/POST /projects/{id}/milestones,
#             PATCH /projects/{id}/milestones/{mid},
#             DELETE /projects/{id}/milestones/{mid}


class TestMilestones:
    def test_list_milestones(self, client, db_session):
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        create_milestone_factory(db_session, proj.id, title="M1")
        create_milestone_factory(db_session, proj.id, title="M2")
        headers = auth_headers(client)
        resp = client.get(f"/api/projects/{proj.id}/milestones", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_create_milestone(self, client, db_session):
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        headers = auth_headers(client)
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
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        ms = create_milestone_factory(db_session, proj.id)
        headers = auth_headers(client)
        resp = client.patch(
            f"/api/projects/{proj.id}/milestones/{ms.id}",
            json={"is_completed": True},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["is_completed"] is True

    def test_update_milestone_reopen(self, client, db_session):
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        ms = create_milestone_factory(db_session, proj.id, is_completed=True)
        headers = auth_headers(client)
        resp = client.patch(
            f"/api/projects/{proj.id}/milestones/{ms.id}",
            json={"is_completed": False},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["is_completed"] is False

    def test_delete_milestone(self, client, db_session):
        """DELETE /projects/{id}/milestones/{mid} soft-deletes the milestone."""
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        ms = create_milestone_factory(db_session, proj.id)
        headers = auth_headers(client)
        resp = client.delete(f"/api/projects/{proj.id}/milestones/{ms.id}", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["deleted"] == str(ms.id)
        # Verify it no longer appears in the listing
        list_resp = client.get(f"/api/projects/{proj.id}/milestones", headers=headers)
        assert list_resp.status_code == 200
        assert all(m["id"] != str(ms.id) for m in list_resp.json())


# ── F: Comments ──────────────────────────────────────────────────────────
# Routes (6): GET /projects/comments, POST /projects/comments,
#             POST /projects/{id}/comments, PATCH /projects/comments/{cid},
#             DELETE /projects/comments/{cid}


class TestComments:
    def test_notification_target_url_rejects_external_destinations(self):
        from backend.services.comment_notifications import _safe_target_url

        assert _safe_target_url("/plataforma/projects/project-1?task=task-1") == (
            "/plataforma/projects/project-1?task=task-1"
        )
        assert _safe_target_url("https://evil.example/phishing") is None
        assert _safe_target_url("//evil.example/phishing") is None
        assert _safe_target_url("/\u005c\u005cevil.example") is None

    def test_list_comments_empty(self, client, db_session):
        _, _, sede = seed_admin(db_session)
        headers = auth_headers(client)
        resp = client.get("/api/projects/comments", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_comments_pagination(self, client, db_session):
        """GET /api/projects/comments?limit=N&offset=M paginates correctly."""
        user, persona, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)

        # Create 5 comments with staggered timestamps so ordering is deterministic
        for i in range(5):
            create_comment_factory(
                db_session,
                proj.id,
                persona.id,
                content=f"Comentario paginado {i}",
            )

        headers = auth_headers(client)

        # Page 1: limit=2 → first 2 items (newest first: 4, 3)
        resp = client.get("/api/projects/comments?limit=2&offset=0", headers=headers)
        assert resp.status_code == 200
        page1 = resp.json()
        assert len(page1) == 2, f"Expected 2, got {len(page1)}"
        assert page1[0]["content"] == "Comentario paginado 4"
        assert page1[1]["content"] == "Comentario paginado 3"

        # Page 2: offset=2, limit=2 → next 2 items (2, 1)
        resp = client.get("/api/projects/comments?limit=2&offset=2", headers=headers)
        assert resp.status_code == 200
        page2 = resp.json()
        assert len(page2) == 2, f"Expected 2, got {len(page2)}"
        assert page2[0]["content"] == "Comentario paginado 2"
        assert page2[1]["content"] == "Comentario paginado 1"

        # Page 3: offset=4, limit=2 → last item (0)
        resp = client.get("/api/projects/comments?limit=2&offset=4", headers=headers)
        assert resp.status_code == 200
        page3 = resp.json()
        assert len(page3) == 1, f"Expected 1, got {len(page3)}"
        assert page3[0]["content"] == "Comentario paginado 0"

        # Offset beyond total → empty list
        resp = client.get("/api/projects/comments?limit=2&offset=99", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_comments_with_data(self, client, db_session):
        _, _, sede = seed_admin(db_session)
        data = setup_project_with_all_relations(db_session)
        headers = auth_headers(client)
        resp = client.get("/api/projects/comments", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_list_comments_filtered_by_project(self, client, db_session):
        _, _, sede = seed_admin(db_session)
        d1 = setup_project_with_all_relations(db_session)
        headers = auth_headers(client)
        resp = client.get(f"/api/projects/comments?project_id={d1['project'].id}", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_create_comment_with_project_id_body(self, client, db_session):
        """POST /projects/comments with project_id in the body."""
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        headers = auth_headers(client)
        resp = client.post(
            "/api/projects/comments",
            json={"project_id": str(proj.id), "content": "Project comment"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["content"] == "Project comment"

    def test_create_comment_by_project(self, client, db_session):
        """POST /projects/{id}/comments."""
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        headers = auth_headers(client)
        resp = client.post(
            f"/api/projects/{proj.id}/comments",
            json={"content": "Scoped comment"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["content"] == "Scoped comment"

    def test_comment_mention_persists_same_origin_project_deep_link(self, client, db_session):
        from backend.models_auth import NotificacionUsuario
        from backend.models_crm import Persona

        _, _, author_sede = seed_admin(db_session, email="mention-author@test.com")
        recipient, recipient_persona, _ = seed_admin(db_session, email="mention-recipient@test.com")
        recipient.sede_id = author_sede.id
        recipient_persona.sede_id = author_sede.id
        non_login_persona = Persona(
            first_name="No",
            last_name="Login",
            email="mention-no-login@test.com",
            sede_id=author_sede.id,
        )
        db_session.add(non_login_persona)
        project = create_project_factory(db_session, sede_id=author_sede.id)
        task = create_task_factory(db_session, project.id, title="Tarea mencionada")
        db_session.commit()

        response = client.post(
            f"/api/projects/{project.id}/comments",
            json={
                "content": "Revisemos esto",
                "task_id": str(task.id),
                "mentions": [str(recipient_persona.id), str(non_login_persona.id)],
            },
            headers=auth_headers(client, email="mention-author@test.com"),
        )

        assert response.status_code == 200, response.text
        notification = (
            db_session.query(NotificacionUsuario)
            .filter(NotificacionUsuario.user_id == recipient.id)
            .one()
        )
        expected_url = f"/plataforma/projects/{project.id}?task={task.id}"
        assert notification.target_url == expected_url
        assert (
            db_session.query(NotificacionUsuario)
            .filter(NotificacionUsuario.user_id == non_login_persona.id)
            .count()
            == 0
        )

        inbox = client.get(
            "/api/messaging/notifications",
            headers=auth_headers(client, email="mention-recipient@test.com"),
        )
        assert inbox.status_code == 200, inbox.text
        assert inbox.json()[0]["target_url"] == expected_url

    def test_update_comment_content(self, client, db_session):
        """Update comment content via PATCH."""
        user, persona, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        comment = create_comment_factory(db_session, proj.id, persona.id)
        headers = auth_headers(client)
        resp = client.patch(f"/api/projects/comments/{comment.id}", json={"content": "Updated"}, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["content"] == "Updated"

    def test_resolve_comment(self, client, db_session):
        """Resolve a comment via PATCH is_resolved=True."""
        user, persona, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        comment = create_comment_factory(db_session, proj.id, persona.id)
        headers = auth_headers(client)
        resp = client.patch(f"/api/projects/comments/{comment.id}", json={"is_resolved": True}, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["is_resolved"] is True

    def test_delete_comment(self, client, db_session):
        """Delete a comment via DELETE."""
        user, persona, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        comment = create_comment_factory(db_session, proj.id, persona.id)
        headers = auth_headers(client)
        resp = client.delete(f"/api/projects/comments/{comment.id}", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["deleted"] == str(comment.id)
        # Verify soft delete in DB
        db_session.refresh(comment)
        assert comment.deleted_at is not None

    def test_comment_not_found(self, client, db_session):
        _, _, sede = seed_admin(db_session)
        headers = auth_headers(client)
        resp = client.patch("/api/projects/comments/999999", json={"content": "Nope"}, headers=headers)
        assert resp.status_code == 404

    def test_create_comment_missing_fields(self, client, db_session):
        _, _, sede = seed_admin(db_session)
        headers = auth_headers(client)
        resp = client.post("/api/projects/comments", json={}, headers=headers)
        # Pydantic validation returns 422 for missing required fields.
        assert resp.status_code == 422


# ── G: Inbox ─────────────────────────────────────────────────────────────
# Routes (2): GET /projects/inbox, POST /projects/inbox/{id}/read


class TestInbox:
    def test_list_inbox_empty(self, client, db_session):
        _, _, sede = seed_admin(db_session)
        headers = auth_headers(client)
        resp = client.get("/api/projects/inbox", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_mark_inbox_read(self, client, db_session):
        """Baseline con un item real del feed del actor (cierre PEND-QUALITY-INBOX-SCOPE-001)."""
        from backend.models_projects import ProjectInboxState

        user, persona, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        other_persona_id = _uuid.uuid4()
        db_session.add(Persona(id=other_persona_id, first_name="Otro", last_name="Autor", email="other_mark@test.com"))
        db_session.flush()
        c = create_comment_factory(db_session, proj.id, author_id=other_persona_id, content="visible en mi inbox")
        headers = auth_headers(client)
        item_id = f"comment-{c.id}"
        resp = client.post(f"/api/projects/inbox/{item_id}/read", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
        db_session.query(ProjectInboxState).filter(ProjectInboxState.item_id == item_id).delete()
        db_session.commit()

    # ── PEND-QUALITY-INBOX-SCOPE-001 (cierre 2026-07-16) ──
    # Cobertura de los huecos de soft delete y validación de item_id.
    def test_inbox_excludes_comments_from_soft_deleted_project(self, client, db_session):
        """Comentarios de proyectos soft-deleted NO deben llegar al feed."""
        from datetime import datetime, timezone

        user, persona, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        # Crear comentario de OTRO autor (no auto-comentario del actor)
        other_persona_id = _uuid.uuid4()
        db_session.add(Persona(id=other_persona_id, first_name="Otro", last_name="Autor", email="other@test.com"))
        db_session.flush()
        create_comment_factory(db_session, proj.id, author_id=other_persona_id, content="En proyecto vivo")
        # Soft-delete del proyecto
        proj.deleted_at = datetime.now(timezone.utc)
        db_session.flush()
        db_session.commit()
        headers = auth_headers(client)
        resp = client.get("/api/projects/inbox", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_inbox_excludes_tasks_from_soft_deleted_project(self, client, db_session):
        """Tareas de proyectos soft-deleted NO deben llegar al feed del inbox."""
        from datetime import datetime, timezone

        user, persona, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        # Crear tarea asignada al actor en el proyecto
        create_task_factory(db_session, proj.id, assignee_id=persona.id, status="todo")
        proj.deleted_at = datetime.now(timezone.utc)
        db_session.flush()
        db_session.commit()
        headers = auth_headers(client)
        resp = client.get("/api/projects/inbox", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_mark_inbox_read_with_invalid_id_returns_404(self, client, db_session):
        """``item_id`` arbitrario NO debe persistirse; respondemos 404."""
        _, _, sede = seed_admin(db_session)
        headers = auth_headers(client)
        resp = client.post("/api/projects/inbox/not-a-real-item/read", headers=headers)
        assert resp.status_code == 404
        # Confirmamos que no se persiste el estado de \u00edtem inventado
        from backend.models_projects import ProjectInboxState

        rows = db_session.query(ProjectInboxState).filter(ProjectInboxState.item_id == "not-a-real-item").all()
        assert rows == []

    def test_mark_inbox_read_with_other_actor_item_returns_404(self, client, db_session):
        """Un item real pero de un proyecto soft-deleted NO debe ser marcado
        como leído por un actor externo."""
        from datetime import datetime, timezone

        user, persona, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        other_persona_id = _uuid.uuid4()
        db_session.add(Persona(id=other_persona_id, first_name="Otro", last_name="X", email="ox@test.com"))
        db_session.flush()
        c = create_comment_factory(db_session, proj.id, author_id=other_persona_id, content="privado")
        # Soft-delete del proyecto (el item deja de estar en el inbox)
        proj.deleted_at = datetime.now(timezone.utc)
        db_session.flush()
        db_session.commit()
        headers = auth_headers(client)
        item_id = f"comment-{c.id}"
        resp = client.post(f"/api/projects/inbox/{item_id}/read", headers=headers)
        assert resp.status_code == 404


# ── H: Portfolio / Workload / Activities / My Tasks ──────────────────────
# Routes (4): GET /projects/summary, GET /projects/workload,
#             GET /projects/activities, GET /projects/tasks


class TestPortfolioWorkload:
    def test_portfolio_summary(self, client, db_session):
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        create_task_factory(db_session, proj.id, status="todo")
        create_task_factory(db_session, proj.id, status="completed")
        headers = auth_headers(client)
        resp = client.get("/api/projects/summary", headers=headers)
        assert resp.status_code == 200
        rows = resp.json()
        assert len(rows) >= 1

    def test_workload_summary(self, client, db_session):
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        create_task_factory(db_session, proj.id, status="in_progress")
        headers = auth_headers(client)
        resp = client.get("/api/projects/workload", headers=headers)
        assert resp.status_code == 200
        # Might be empty if no assignee_id matches, but should not crash
        assert isinstance(resp.json(), list)

    def test_list_activities(self, client, db_session):
        _, _, sede = seed_admin(db_session)
        data = setup_project_with_all_relations(db_session)
        headers = auth_headers(client)
        resp = client.get("/api/projects/activities", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_list_activities_default_limit(self, client, db_session):
        """GET /api/projects/activities without explicit limit defaults to 20."""
        user, persona, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)

        # Create 25 activity logs — more than the default limit of 20
        from tests.factories_projects import create_activity_log_factory

        for i in range(25):
            create_activity_log_factory(
                db_session,
                proj.id,
                "task_created",
                persona_id=persona.id,
                description=f"Default limit test {i}",
            )

        headers = auth_headers(client)
        # No limit param → uses default 20
        resp = client.get("/api/projects/activities", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 20, f"Expected default limit 20, got {len(data)}"

        # Explicit limit=5 overrides default
        resp = client.get("/api/projects/activities?limit=5", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 5, f"Expected 5, got {len(resp.json())}"

    def test_list_activities_pagination(self, client, db_session):
        """GET /api/projects/activities?limit=N&offset=M paginates correctly."""
        user, persona, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)

        # Create 5 activity logs
        from tests.factories_projects import create_activity_log_factory

        for i in range(5):
            create_activity_log_factory(
                db_session,
                proj.id,
                "task_created",
                persona_id=persona.id,
                description=f"Actividad paginada {i}",
            )

        headers = auth_headers(client)

        # Page 1: limit=2 → first 2 (newest first: 4, 3)
        resp = client.get("/api/projects/activities?limit=2&offset=0", headers=headers)
        assert resp.status_code == 200
        page1 = resp.json()
        assert len(page1) == 2, f"Expected 2, got {len(page1)}"
        assert "Actividad paginada 4" in page1[0]["description"]
        assert "Actividad paginada 3" in page1[1]["description"]

        # Page 2: offset=2, limit=2 → next 2 (2, 1)
        resp = client.get("/api/projects/activities?limit=2&offset=2", headers=headers)
        assert resp.status_code == 200
        page2 = resp.json()
        assert len(page2) == 2, f"Expected 2, got {len(page2)}"
        assert "Actividad paginada 2" in page2[0]["description"]
        assert "Actividad paginada 1" in page2[1]["description"]

        # Offset beyond total → empty
        resp = client.get("/api/projects/activities?limit=2&offset=99", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_activities_filtered(self, client, db_session):
        _, _, sede = seed_admin(db_session)
        data = setup_project_with_all_relations(db_session)
        headers = auth_headers(client)
        resp = client.get(f"/api/projects/activities?project_id={data['project'].id}", headers=headers)
        assert resp.status_code == 200
        assert all(a["project_id"] == str(data["project"].id) for a in resp.json())

    def test_list_all_my_tasks(self, client, db_session):
        """GET /projects/tasks returns tasks assigned to current user's persona."""
        user, persona, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        create_task_factory(db_session, proj.id, assignee_id=persona.id)
        headers = auth_headers(client)
        resp = client.get("/api/projects/tasks", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_legacy_my_tasks_returns_all_assigned_tasks(self, client, db_session):
        _, persona, _ = seed_admin(db_session)
        project = create_project_factory(db_session)
        for index in range(101):
            create_task_factory(
                db_session,
                project.id,
                assignee_id=persona.id,
                title=f"Lote legacy {index}",
            )
        response = client.get("/api/projects/tasks", headers=auth_headers(client))

        assert response.status_code == 200
        assert len(response.json()) == 101

    def test_list_my_tasks_hides_tasks_from_soft_deleted_projects(self, client, db_session):
        from datetime import datetime, timezone

        _, persona, _ = seed_admin(db_session)
        active_project = create_project_factory(db_session, title="Proyecto activo")
        deleted_project = create_project_factory(db_session, title="Proyecto archivado")
        active_task = create_task_factory(db_session, active_project.id, assignee_id=persona.id)
        deleted_task = create_task_factory(db_session, deleted_project.id, assignee_id=persona.id)
        deleted_project.deleted_at = datetime.now(timezone.utc)
        db_session.commit()
        headers = auth_headers(client)

        legacy_response = client.get("/api/projects/tasks", headers=headers)
        paged_response = client.get("/api/projects/tasks/page", headers=headers)

        assert legacy_response.status_code == paged_response.status_code == 200
        legacy_ids = {item["id"] for item in legacy_response.json()}
        paged_ids = {item["id"] for item in paged_response.json()["items"]}
        assert str(active_task.id) in legacy_ids
        assert str(active_task.id) in paged_ids
        assert str(deleted_task.id) not in legacy_ids
        assert str(deleted_task.id) not in paged_ids

    def test_list_my_tasks_page_is_stable_and_bounded(self, client, db_session):
        _, persona, _ = seed_admin(db_session)
        project = create_project_factory(db_session)
        for index in range(3):
            create_task_factory(db_session, project.id, assignee_id=persona.id, title=f"Paginada {index}")
        headers = auth_headers(client)

        first = client.get("/api/projects/tasks/page?offset=0&limit=2", headers=headers)
        second = client.get("/api/projects/tasks/page?offset=2&limit=2", headers=headers)
        assert first.status_code == second.status_code == 200
        first_page = first.json()
        second_page = second.json()
        assert first_page["total"] == second_page["total"] == 3
        assert len(first_page["items"]) == 2
        assert len(second_page["items"]) == 1
        assert first_page["skip"] == 0 and first_page["limit"] == 2
        assert {item["id"] for item in first_page["items"]}.isdisjoint(
            item["id"] for item in second_page["items"]
        )
        assert all(item["project_title"] == project.title for item in first_page["items"])

    def test_list_my_tasks_page_rejects_limit_above_cap(self, client, db_session):
        seed_admin(db_session)
        response = client.get("/api/projects/tasks/page?limit=101", headers=auth_headers(client))
        assert response.status_code == 422


class TestAnalytics:
    """GET /projects/{id}/analytics — F1: métricas reales del proyecto."""

    def _get(self, client, project_id):
        headers = auth_headers(client)
        return client.get(f"/api/projects/{project_id}/analytics", headers=headers)

    def test_analytics_empty_project(self, client, db_session):
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        resp = self._get(client, proj.id)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_tasks"] == 0
        assert data["completed_tasks"] == 0
        assert data["open_tasks"] == 0
        assert data["overdue_tasks"] == 0
        assert data["unassigned_tasks"] == 0
        assert data["risk_level"] == "bajo"
        assert data["risk_reason"] == "Sin bloqueos"
        assert data["health_label"] == "crítica" or data["health_label"] == "en riesgo"

    def test_analytics_healthy_project(self, client, db_session):
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        create_task_factory(db_session, proj.id, status="completed")
        create_task_factory(db_session, proj.id, status="completed")
        resp = self._get(client, proj.id)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_tasks"] == 2
        assert data["completed_tasks"] == 2
        assert data["open_tasks"] == 0
        assert data["overdue_tasks"] == 0
        assert data["unassigned_tasks"] == 0
        assert data["risk_level"] == "bajo"
        assert data["health_label"] == "óptima"

    def test_analytics_overdue_raises_risk(self, client, db_session):
        from datetime import datetime, timedelta, timezone

        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        overdue = datetime.now(timezone.utc) - timedelta(days=3)
        create_task_factory(db_session, proj.id, status="in_progress", due_date=overdue)
        create_task_factory(db_session, proj.id, status="completed", due_date=overdue)
        resp = self._get(client, proj.id)
        assert resp.status_code == 200
        data = resp.json()
        assert data["overdue_tasks"] == 1
        assert data["overdue_days"] == 3
        assert data["risk_level"] == "alto"
        assert "vencida" in data["risk_reason"]

    def test_analytics_unassigned_raises_risk(self, client, db_session):
        from backend.models_projects import ProjectTask

        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        db_session.add(
            ProjectTask(
                id=_uuid.uuid4(),
                project_id=proj.id,
                title="Tarea sin responsable",
                status="todo",
                priority="medium",
                order_index=0,
                labels=[],
            )
        )
        db_session.commit()
        resp = self._get(client, proj.id)
        assert resp.status_code == 200
        data = resp.json()
        assert data["unassigned_tasks"] == 1
        assert data["risk_level"] == "medio"
        assert "responsable" in data["risk_reason"]

    def test_analytics_velocity(self, client, db_session):
        from datetime import datetime, timedelta, timezone

        _, _, sede = seed_admin(db_session)
        created = datetime.now(timezone.utc) - timedelta(days=10)
        proj = create_project_factory(db_session, created_at=created)
        for _ in range(5):
            create_task_factory(db_session, proj.id, status="completed")
        resp = self._get(client, proj.id)
        assert resp.status_code == 200
        data = resp.json()
        assert data["completed_tasks"] == 5
        assert data["velocity"] == 0.5

    def test_analytics_cross_sede_returns_404(self, client, db_session):
        """Axioma 3: analytics de un proyecto de otra sede → 404."""
        from tests.conftest import seed_user_with_role

        _, _, sede_a = seed_admin(db_session)
        proj = create_project_factory(db_session, sede_id=sede_a.id)
        seed_user_with_role(
            db_session,
            role_name="pastor",
            email="useranalytics@test.com",
            sede_id=_uuid.uuid4(),
        )
        headers = auth_headers(client, email="useranalytics@test.com")
        resp = client.get(f"/api/projects/{proj.id}/analytics", headers=headers)
        assert resp.status_code == 404


# ── H.1: Equipo / Membresía (F4) ─────────────────────────────────────────
# Routes (3): GET/POST /projects/{id}/team, DELETE /projects/{id}/team/{persona_id}


class TestProjectTeam:
    def test_team_empty(self, client, db_session):
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session, sede_id=sede.id)
        headers = auth_headers(client)
        resp = client.get(f"/api/projects/{proj.id}/team", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_invite_member(self, client, db_session):
        from tests.factories_projects import _ensure_persona

        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session, sede_id=sede.id)
        persona = _ensure_persona(db_session)
        persona.sede_id = sede.id
        db_session.commit()
        headers = auth_headers(client)
        resp = client.post(
            f"/api/projects/{proj.id}/team",
            json={"persona_id": str(persona.id)},
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["persona_id"] == str(persona.id)
        assert data["project_id"] == str(proj.id)
        assert data["role"] == "member"

    def test_invite_member_then_list(self, client, db_session):
        from tests.factories_projects import _ensure_persona

        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session, sede_id=sede.id)
        persona = _ensure_persona(db_session)
        persona.sede_id = sede.id
        db_session.commit()
        headers = auth_headers(client)
        client.post(f"/api/projects/{proj.id}/team", json={"persona_id": str(persona.id)}, headers=headers)
        resp = client.get(f"/api/projects/{proj.id}/team", headers=headers)
        assert resp.status_code == 200
        rows = resp.json()
        assert len(rows) == 1
        assert rows[0]["persona_id"] == str(persona.id)
        assert rows[0]["persona_name"] == persona.nombre_completo

    def test_invite_duplicate_returns_409(self, client, db_session):
        from tests.factories_projects import _ensure_persona

        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session, sede_id=sede.id)
        persona = _ensure_persona(db_session)
        persona.sede_id = sede.id
        db_session.commit()
        headers = auth_headers(client)
        payload = {"persona_id": str(persona.id)}
        assert client.post(f"/api/projects/{proj.id}/team", json=payload, headers=headers).status_code == 201
        resp = client.post(f"/api/projects/{proj.id}/team", json=payload, headers=headers)
        assert resp.status_code == 409

    def test_invite_unknown_persona_returns_404(self, client, db_session):
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        headers = auth_headers(client)
        resp = client.post(
            f"/api/projects/{proj.id}/team",
            json={"persona_id": str(_uuid.uuid4())},
            headers=headers,
        )
        assert resp.status_code == 404

    def test_remove_member(self, client, db_session):
        from tests.factories_projects import _ensure_persona

        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session, sede_id=sede.id)
        persona = _ensure_persona(db_session)
        persona.sede_id = sede.id
        db_session.commit()
        headers = auth_headers(client)
        client.post(f"/api/projects/{proj.id}/team", json={"persona_id": str(persona.id)}, headers=headers)
        resp = client.delete(f"/api/projects/{proj.id}/team/{persona.id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["removed"] == str(persona.id)
        assert client.get(f"/api/projects/{proj.id}/team", headers=headers).json() == []

    def test_remove_unknown_member_returns_404(self, client, db_session):
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        headers = auth_headers(client)
        resp = client.delete(f"/api/projects/{proj.id}/team/{_uuid.uuid4()}", headers=headers)
        assert resp.status_code == 404

    def test_team_cross_sede_returns_404(self, client, db_session):
        """Axioma 3: invitar/listar en proyecto de otra sede → 404."""
        from tests.conftest import seed_user_with_role
        from tests.factories_projects import _ensure_persona

        _, _, sede_a = seed_admin(db_session)
        proj = create_project_factory(db_session, sede_id=sede_a.id)
        persona = _ensure_persona(db_session)
        persona.sede_id = sede_a.id
        db_session.commit()
        seed_user_with_role(
            db_session,
            role_name="pastor",
            email="userteam@test.com",
            sede_id=_uuid.uuid4(),
        )
        headers = auth_headers(client, email="userteam@test.com")
        resp = client.post(
            f"/api/projects/{proj.id}/team",
            json={"persona_id": str(persona.id)},
            headers=headers,
        )
        assert resp.status_code == 404


# ── I: Wiki / Whiteboard ────────────────────────────────────────────────
# Routes (4): GET/POST /projects/{id}/wiki, GET/POST /projects/{id}/whiteboard


class TestWikiWhiteboard:
    def test_get_wiki_nonexistent(self, client, db_session):
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        headers = auth_headers(client)
        resp = client.get(f"/api/projects/{proj.id}/wiki", headers=headers)
        assert resp.status_code == 200
        assert resp.json() is None

    def test_create_wiki(self, client, db_session):
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        headers = auth_headers(client)
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
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        create_wiki_factory(db_session, proj.id)
        headers = auth_headers(client)
        resp = client.post(
            f"/api/projects/{proj.id}/wiki",
            json={"content": "# Updated", "title": "Updated Wiki"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated Wiki"

    def test_get_whiteboard_nonexistent(self, client, db_session):
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        headers = auth_headers(client)
        resp = client.get(f"/api/projects/{proj.id}/whiteboard", headers=headers)
        assert resp.status_code == 200
        assert resp.json() is None

    def test_create_whiteboard(self, client, db_session):
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        headers = auth_headers(client)
        resp = client.post(
            f"/api/projects/{proj.id}/whiteboard",
            json={"title": "Pizarra", "elements_json": '[{"type":"rectangle"}]'},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "Pizarra"

    def test_update_whiteboard(self, client, db_session):
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        create_whiteboard_factory(db_session, proj.id)
        headers = auth_headers(client)
        resp = client.post(
            f"/api/projects/{proj.id}/whiteboard",
            json={"elements_json": '[{"type":"circle"}]'},
            headers=headers,
        )
        assert resp.status_code == 200
        assert "circle" in resp.json()["elements_json"]

    def test_whiteboard_optimistic_version_accepts_current_version_and_refreshes_it(self, client, db_session):
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        create_whiteboard_factory(db_session, proj.id)
        headers = auth_headers(client)
        route = f"/api/projects/{proj.id}/whiteboard"
        current = client.get(route, headers=headers)
        assert current.status_code == 200, current.text

        first_save = client.post(
            route,
            json={"elements_json": '[{"type":"rectangle"}]', "base_updated_at": current.json()["updated_at"]},
            headers=headers,
        )
        assert first_save.status_code == 200, first_save.text
        assert "rectangle" in first_save.json()["elements_json"]

        second_save = client.post(
            route,
            json={"elements_json": '[{"type":"circle"}]', "base_updated_at": first_save.json()["updated_at"]},
            headers=headers,
        )
        assert second_save.status_code == 200, second_save.text
        assert "circle" in second_save.json()["elements_json"]

    def test_stale_whiteboard_version_returns_409_without_overwriting(self, client, db_session):
        from datetime import timedelta

        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        board = create_whiteboard_factory(db_session, proj.id, elements_json='[{"type":"rectangle"}]')
        headers = auth_headers(client)
        route = f"/api/projects/{proj.id}/whiteboard"
        stale_version = client.get(route, headers=headers).json()["updated_at"]

        board.updated_at = board.updated_at + timedelta(seconds=1)
        board.elements_json = '[{"type":"circle"}]'
        db_session.commit()

        response = client.post(
            route,
            json={"elements_json": '[{"type":"triangle"}]', "base_updated_at": stale_version},
            headers=headers,
        )

        assert response.status_code == 409, response.text
        assert response.json()["detail"]["code"] == "whiteboard_conflict"
        assert response.json()["detail"]["current_updated_at"]
        db_session.refresh(board)
        assert "circle" in board.elements_json
        assert "triangle" not in board.elements_json

    def test_stale_whiteboard_save_cannot_restore_a_deleted_board(self, client, db_session):
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        create_whiteboard_factory(db_session, proj.id)
        headers = auth_headers(client)
        route = f"/api/projects/{proj.id}/whiteboard"
        stale_version = client.get(route, headers=headers).json()["updated_at"]

        deleted = client.delete(route, headers=headers)
        assert deleted.status_code == 204, deleted.text
        stale_save = client.post(
            route,
            json={"elements_json": '[{"type":"circle"}]', "base_updated_at": stale_version},
            headers=headers,
        )

        assert stale_save.status_code == 409, stale_save.text
        assert client.get(route, headers=headers).json() is None


# ── J: Supplies ──────────────────────────────────────────────────────────
# Routes (4): GET/POST /projects/{pid}/tasks/{tid}/supplies,
#             PATCH/DELETE /projects/{pid}/tasks/{tid}/supplies/{sid}


class TestSupplies:
    def test_list_supplies_empty(self, client, db_session):
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        task = create_task_factory(db_session, proj.id)
        headers = auth_headers(client)
        resp = client.get(f"/api/projects/{proj.id}/tasks/{task.id}/supplies", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_create_supply(self, client, db_session):
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        task = create_task_factory(db_session, proj.id)
        headers = auth_headers(client)
        resp = client.post(
            f"/api/projects/{proj.id}/tasks/{task.id}/supplies",
            json={"item_name": "Cable HDMI", "quantity": 2, "status": "pending"},
            headers=headers,
        )
        assert resp.status_code == 201
        assert resp.json()["item_name"] == "Cable HDMI"

    def test_update_supply(self, client, db_session):
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        task = create_task_factory(db_session, proj.id)
        supply = create_supply_factory(db_session, task.id)
        headers = auth_headers(client)
        resp = client.patch(
            f"/api/projects/{proj.id}/tasks/{task.id}/supplies/{supply.id}",
            json={"status": "ready"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ready"

    def test_delete_supply(self, client, db_session):
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        task = create_task_factory(db_session, proj.id)
        supply = create_supply_factory(db_session, task.id)
        headers = auth_headers(client)
        resp = client.delete(
            f"/api/projects/{proj.id}/tasks/{task.id}/supplies/{supply.id}",
            headers=headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["deleted"] == str(supply.id)
        # Verify soft delete in DB
        db_session.refresh(supply)
        assert supply.deleted_at is not None


# ── J.1: Attachments ───────────────────────────────────────────────────────
# Routes (2): POST /projects/{pid}/tasks/{tid}/attachments,
#             DELETE /projects/{pid}/tasks/{tid}/attachments/{aid}


class TestAttachments:
    def test_upload_attachment_exceeds_max_size(self, client, db_session):
        """POST with file > 10 MB returns 400."""
        from backend.core.uploads import MAX_UPLOAD_SIZE

        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        task = create_task_factory(db_session, proj.id)
        headers = auth_headers(client)
        # 1 byte over the limit
        oversized = b"x" * (MAX_UPLOAD_SIZE + 1)
        files = {"file": ("huge.pdf", oversized, "application/pdf")}
        resp = client.post(
            f"/api/projects/{proj.id}/tasks/{task.id}/attachments",
            files=files,
            headers=headers,
        )
        assert resp.status_code == 400, f"Expected 400, got {resp.status_code}: {resp.text}"
        assert "File exceeds maximum size" in resp.text

    def test_upload_attachment(self, client, db_session):
        """POST /projects/{pid}/tasks/{tid}/attachments uploads a file."""
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        task = create_task_factory(db_session, proj.id)
        headers = auth_headers(client)
        files = {"file": ("reporte.pdf", b"%PDF-1.4 test", "application/pdf")}
        resp = client.post(
            f"/api/projects/{proj.id}/tasks/{task.id}/attachments",
            files=files,
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == task.title
        attachments = data["attachments"]
        assert any(a["filename"] == "reporte.pdf" for a in attachments)
        assert any(a["file_url"] for a in attachments)
        assert any(a["file_size"] > 0 for a in attachments)
        # Verify persistence in DB
        db_attachment = (
            db_session.query(ProjectAttachment)
            .filter(
                ProjectAttachment.task_id == task.id,
                ProjectAttachment.filename == "reporte.pdf",
            )
            .first()
        )
        assert db_attachment is not None

    def test_delete_attachment(self, client, db_session):
        """DELETE /projects/{pid}/tasks/{tid}/attachments/{aid} soft-deletes."""
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        task = create_task_factory(db_session, proj.id)
        attachment = create_attachment_factory(db_session, task.id)
        headers = auth_headers(client)
        resp = client.delete(
            f"/api/projects/{proj.id}/tasks/{task.id}/attachments/{attachment.id}",
            headers=headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["deleted"] == str(attachment.id)
        # Verify soft delete in DB
        db_session.refresh(attachment)
        assert attachment.deleted_at is not None


# ── K: Chat Messages ─────────────────────────────────────────────────────
# Routes (3): GET/POST /projects/{id}/messages,
#             DELETE /projects/{id}/messages/{mid}


class TestMessages:
    def test_list_messages_empty(self, client, db_session):
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        headers = auth_headers(client)
        resp = client.get(f"/api/projects/{proj.id}/messages", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_send_message(self, client, db_session):
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        headers = auth_headers(client)
        resp = client.post(
            f"/api/projects/{proj.id}/messages",
            json={"content": "Hola equipo"},
            headers=headers,
        )
        assert resp.status_code == 201
        assert resp.json()["content"] == "Hola equipo"

    def test_delete_own_message(self, client, db_session):
        user, persona, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        msg = create_message_factory(db_session, proj.id, persona.id)
        headers = auth_headers(client)
        resp = client.delete(f"/api/projects/{proj.id}/messages/{msg.id}", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        # Verify soft delete in DB
        db_session.refresh(msg)
        assert msg.deleted_at is not None


# ── L.1: Cross-sede / Multi-tenant Security ───────────────────────────────


class TestCrossSedeSecurity:
    """Verify Axioma 3: users cannot access projects from another sede."""

    def test_cross_sede_update_task_returns_404(self, client, db_session):
        """PATCH task in another sede returns 404 (not 403)."""
        from tests.conftest import seed_user_with_role

        _, _, sede_a = seed_admin(db_session)
        proj = create_project_factory(db_session, sede_id=sede_a.id)
        task = create_task_factory(db_session, proj.id)
        # Create user in a different sede
        seed_user_with_role(
            db_session,
            role_name="pastor",
            email="userb@test.com",
            sede_id=_uuid.uuid4(),
        )
        headers_b = auth_headers(client, email="userb@test.com")
        resp = client.patch(
            f"/api/projects/{proj.id}/tasks/{task.id}",
            json={"title": "Hacked"},
            headers=headers_b,
        )
        assert resp.status_code == 404
        # Verify task was not modified
        db_session.refresh(task)
        assert task.title != "Hacked"

    def test_cross_sede_upload_attachment_returns_404(self, client, db_session):
        """POST attachment in another sede returns 404 and does not create it."""
        from tests.conftest import seed_user_with_role

        _, _, sede_a = seed_admin(db_session)
        proj = create_project_factory(db_session, sede_id=sede_a.id)
        task = create_task_factory(db_session, proj.id)
        seed_user_with_role(
            db_session,
            role_name="pastor",
            email="userb2@test.com",
            sede_id=_uuid.uuid4(),
        )
        headers_b = auth_headers(client, email="userb2@test.com")
        files = {"file": ("reporte.pdf", b"%PDF-1.4 test", "application/pdf")}
        resp = client.post(
            f"/api/projects/{proj.id}/tasks/{task.id}/attachments",
            files=files,
            headers=headers_b,
        )
        assert resp.status_code == 404
        # Verify no attachment was created
        db_attachment = (
            db_session.query(ProjectAttachment)
            .filter(
                ProjectAttachment.task_id == task.id,
            )
            .first()
        )
        assert db_attachment is None

    def test_cross_sede_delete_attachment_returns_404(self, client, db_session):
        """DELETE attachment in another sede returns 404 and does not delete it."""
        from tests.conftest import seed_user_with_role

        _, _, sede_a = seed_admin(db_session)
        proj = create_project_factory(db_session, sede_id=sede_a.id)
        task = create_task_factory(db_session, proj.id)
        attachment = create_attachment_factory(db_session, task.id)
        seed_user_with_role(
            db_session,
            role_name="pastor",
            email="userb4@test.com",
            sede_id=_uuid.uuid4(),
        )
        headers_b = auth_headers(client, email="userb4@test.com")
        resp = client.delete(
            f"/api/projects/{proj.id}/tasks/{task.id}/attachments/{attachment.id}",
            headers=headers_b,
        )
        assert resp.status_code == 404
        # Verify attachment was not deleted
        db_session.refresh(attachment)
        assert attachment.deleted_at is None

    def test_delete_attachment_from_another_task_in_same_project_returns_404(self, client, db_session):
        """An attachment ID cannot escape its task, even within one project/sede."""
        _, _, sede = seed_admin(db_session)
        project = create_project_factory(db_session, sede_id=sede.id)
        task_in_path = create_task_factory(db_session, project.id, title="Tarea de la ruta")
        other_task = create_task_factory(db_session, project.id, title="Otra tarea")
        attachment = create_attachment_factory(db_session, other_task.id)

        response = client.delete(
            f"/api/projects/{project.id}/tasks/{task_in_path.id}/attachments/{attachment.id}",
            headers=auth_headers(client),
        )

        assert response.status_code == 404, response.text
        db_session.refresh(attachment)
        assert attachment.deleted_at is None

    def test_delete_attachment_from_another_project_returns_404(self, client, db_session):
        """A valid same-sede task in another project is not a valid path parent."""
        _, _, sede = seed_admin(db_session)
        project_in_path = create_project_factory(db_session, sede_id=sede.id)
        other_project = create_project_factory(db_session, sede_id=sede.id)
        task_in_other_project = create_task_factory(db_session, other_project.id)
        attachment = create_attachment_factory(db_session, task_in_other_project.id)

        response = client.delete(
            f"/api/projects/{project_in_path.id}/tasks/{task_in_other_project.id}/attachments/{attachment.id}",
            headers=auth_headers(client),
        )

        assert response.status_code == 404, response.text
        db_session.refresh(attachment)
        assert attachment.deleted_at is None

    def test_cross_sede_delete_milestone_returns_404(self, client, db_session):
        """DELETE milestone in another sede returns 404 and does not delete it."""
        from tests.conftest import seed_user_with_role

        _, _, sede_a = seed_admin(db_session)
        proj = create_project_factory(db_session, sede_id=sede_a.id)
        ms = create_milestone_factory(db_session, proj.id)
        seed_user_with_role(
            db_session,
            role_name="pastor",
            email="userb5@test.com",
            sede_id=_uuid.uuid4(),
        )
        headers_b = auth_headers(client, email="userb5@test.com")
        resp = client.delete(
            f"/api/projects/{proj.id}/milestones/{ms.id}",
            headers=headers_b,
        )
        assert resp.status_code == 404
        # Verify milestone was not deleted
        db_session.refresh(ms)
        assert ms.deleted_at is None

    @pytest.mark.parametrize(
        "method,expected_status",
        [
            ("get", 404),
            ("post", 404),
            ("patch", 404),
            ("delete", 404),
        ],
    )
    def test_cross_sede_supply_operations_return_404(self, client, db_session, method, expected_status):
        """GET/POST/PATCH/DELETE supplies in another sede return 404."""
        from tests.conftest import seed_user_with_role

        _, _, sede_a = seed_admin(db_session)
        proj = create_project_factory(db_session, sede_id=sede_a.id)
        task = create_task_factory(db_session, proj.id)
        supply = create_supply_factory(db_session, task.id)
        seed_user_with_role(
            db_session,
            role_name="pastor",
            email=f"userb3_{method}@test.com",
            sede_id=_uuid.uuid4(),
        )
        headers_b = auth_headers(client, email=f"userb3_{method}@test.com")

        url = f"/api/projects/{proj.id}/tasks/{task.id}/supplies"
        if method in ("patch", "delete"):
            url = f"{url}/{supply.id}"

        if method == "get":
            resp = client.get(url, headers=headers_b)
        elif method == "post":
            resp = client.post(
                url,
                json={"item_name": "Cable", "quantity": 1, "status": "pending"},
                headers=headers_b,
            )
        elif method == "patch":
            resp = client.patch(url, json={"status": "ready"}, headers=headers_b)
        else:  # delete
            resp = client.delete(url, headers=headers_b)

        assert resp.status_code == expected_status

        # Verify no mutation occurred
        if method == "post":
            from backend.models_projects import TaskSupply

            count = (
                db_session.query(TaskSupply)
                .filter(
                    TaskSupply.task_id == task.id,
                    TaskSupply.item_name == "Cable",
                )
                .count()
            )
            assert count == 0
        elif method == "patch":
            db_session.refresh(supply)
            assert supply.status != "ready"
        elif method == "delete":
            db_session.refresh(supply)
            assert supply.deleted_at is None


# ── L: UUID & Edge Cases ─────────────────────────────────────────────────
# Transversal validations across the module


class TestUUIDEdgeCases:
    def test_get_project_by_nonexistent_uuid(self, client, db_session):
        """UUID format is respected; nonexistent returns 404."""
        _, _, sede = seed_admin(db_session)
        headers = auth_headers(client)
        resp = client.get(f"/api/projects/{_uuid.uuid4()}", headers=headers)
        assert resp.status_code == 404

    def test_uuid_format_in_response(self, client, db_session):
        """All UUID fields in responses are valid UUID strings, not integers."""
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        create_task_factory(db_session, proj.id)
        headers = auth_headers(client)
        resp = client.get(f"/api/projects/{proj.id}", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        _assert_uuid(data["id"])
        for task in data.get("tasks", []):
            _assert_uuid(task["id"])
            _assert_uuid(task["project_id"])

    def test_uuid_not_coerced_to_number(self, client, db_session):
        """Verifies Number() coercion bug is not present on any UUID field."""
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session, owner_id=_uuid.uuid4())
        headers = auth_headers(client)
        resp = client.get(f"/api/projects/{proj.id}", headers=headers)
        assert resp.status_code == 200
        owner_id = resp.json()["owner_id"]
        _assert_uuid(owner_id)
        # Ensure it's not NaN (what Number() yields for UUID)
        import math

        assert not (isinstance(owner_id, float) and math.isnan(owner_id))

    def test_staff_only_endpoints(self, client, db_session):
        """DELETE project requires staff/admin."""
        from tests.conftest import seed_user_with_role

        user, _, _ = seed_user_with_role(db_session, role_name="persona", email="user@test.com")
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)

        # Non-staff user
        headers = auth_headers(client, email="user@test.com")
        resp = client.delete(f"/api/projects/{proj.id}", headers=headers)
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"

    def test_pipeline_creates_project(self, client, db_session):
        """Full creation -> list -> get -> update -> delete lifecycle works."""
        _, _, sede = seed_admin(db_session)
        headers = auth_headers(client)

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


class TestProjectAutomationIsolation:
    def test_evaluate_rejects_task_from_another_project(self, client, db_session):
        """An editor cannot trigger an automation against a foreign project task."""
        seed_admin(db_session)
        project_a = create_project_factory(db_session, title="Proyecto A")
        project_b = create_project_factory(db_session, title="Proyecto B")
        foreign_task = create_task_factory(db_session, project_b.id, title="Tarea ajena")
        headers = auth_headers(client)

        response = client.post(
            f"/api/projects/{project_a.id}/automations/evaluate",
            json={"trigger_event": "task_completed", "task_id": str(foreign_task.id)},
            headers=headers,
        )

        assert response.status_code == 404

    def test_evaluate_rejects_foreign_task_id_inside_context_data(self, client, db_session):
        """Task scoping must be identical whether the ID is formal or contextual."""
        seed_admin(db_session)
        project_a = create_project_factory(db_session, title="Proyecto A")
        project_b = create_project_factory(db_session, title="Proyecto B")
        foreign_task = create_task_factory(db_session, project_b.id, title="Tarea ajena")

        response = client.post(
            f"/api/projects/{project_a.id}/automations/evaluate",
            json={
                "trigger_event": "task_completed",
                "context_data": {"task_id": str(foreign_task.id)},
            },
            headers=auth_headers(client),
        )

        assert response.status_code == 404, response.text

    def test_task_scoped_automation_without_task_is_failed_without_counting_execution(self, client, db_session):
        """Task actions must not report success or increment metrics without a task."""
        from backend.models_projects import ProjectAutomationRule

        _, _, sede = seed_admin(db_session)
        project = create_project_factory(db_session, sede_id=sede.id)
        rule = ProjectAutomationRule(
            project_id=project.id,
            sede_id=sede.id,
            name="Escalar prioridad",
            trigger_event="task_completed",
            condition_data={},
            action_type="set_priority",
            action_data={"priority": "urgent"},
            is_active=True,
        )
        db_session.add(rule)
        db_session.commit()

        response = client.post(
            f"/api/projects/{project.id}/automations/evaluate",
            json={"trigger_event": "task_completed", "dry_run": False},
            headers=auth_headers(client),
        )

        assert response.status_code == 200, response.text
        assert response.json()[0]["status"] == "failed"
        assert "requiere una tarea activa" in response.json()[0]["details"]
        db_session.refresh(rule)
        assert rule.execution_count == 0
        assert rule.last_triggered_at is None

    def test_automation_evaluation_defaults_to_preview_without_persisting_changes(self, client, db_session):
        """Omitting dry_run must preview effects without mutating task or rule state."""
        from backend.models_projects import ProjectActivityLog, ProjectAutomationRule, ProjectTask

        _, _, sede = seed_admin(db_session)
        project = create_project_factory(db_session, sede_id=sede.id)
        task = create_task_factory(
            db_session,
            project.id,
            title="Cerrar registro",
            status="completed",
            priority="high",
            node="Planificación",
        )
        rules = [
            ProjectAutomationRule(
                project_id=project.id,
                sede_id=sede.id,
                name="Registrar aviso",
                trigger_event="task_completed",
                condition_data={},
                action_type="notify_assignee",
                action_data={},
                is_active=True,
            ),
            ProjectAutomationRule(
                project_id=project.id,
                sede_id=sede.id,
                name="Mover a revisión",
                trigger_event="task_completed",
                condition_data={},
                action_type="change_phase",
                action_data={"phase_name": "Revisión"},
                is_active=True,
            ),
            ProjectAutomationRule(
                project_id=project.id,
                sede_id=sede.id,
                name="Crear seguimiento",
                trigger_event="task_completed",
                condition_data={},
                action_type="create_followup_task",
                action_data={"title": "Validar acta", "duration_days": 4},
                is_active=True,
            ),
            ProjectAutomationRule(
                project_id=project.id,
                sede_id=sede.id,
                name="Escalar prioridad",
                trigger_event="task_completed",
                condition_data={},
                action_type="set_priority",
                action_data={"priority": "urgent"},
                is_active=True,
            ),
        ]
        db_session.add_all(rules)
        db_session.commit()
        headers = auth_headers(client)
        task_count_before = db_session.query(ProjectTask).filter(
            ProjectTask.project_id == project.id,
            ProjectTask.deleted_at.is_(None),
        ).count()
        activity_count_before = db_session.query(ProjectActivityLog).filter(
            ProjectActivityLog.project_id == project.id,
        ).count()

        response = client.post(
            f"/api/projects/{project.id}/automations/evaluate",
            json={"trigger_event": "task_completed", "task_id": str(task.id)},
            headers=headers,
        )

        assert response.status_code == 200, response.text
        results = response.json()
        assert len(results) == 4
        assert {result["status"] for result in results} == {"would_execute"}
        assert any("Se crearía la tarea de seguimiento 'Validar acta'" in result["details"] for result in results)

        db_session.expire_all()
        persisted_task = db_session.query(ProjectTask).filter(ProjectTask.id == task.id).one()
        persisted_rules = db_session.query(ProjectAutomationRule).filter(
            ProjectAutomationRule.project_id == project.id,
        ).all()
        task_count_after = db_session.query(ProjectTask).filter(
            ProjectTask.project_id == project.id,
            ProjectTask.deleted_at.is_(None),
        ).count()
        activity_count_after = db_session.query(ProjectActivityLog).filter(
            ProjectActivityLog.project_id == project.id,
        ).count()
        assert persisted_task.priority == "high"
        assert persisted_task.node == "Planificación"
        assert task_count_after == task_count_before
        assert activity_count_after == activity_count_before
        assert all(rule.execution_count == 0 and rule.last_triggered_at is None for rule in persisted_rules)

    def test_automation_evaluate_mutates_only_when_dry_run_is_explicitly_false(self, client, db_session):
        """Actual execution must be opt-in, never the endpoint's implicit behavior."""
        from backend.models_projects import ProjectAutomationRule, ProjectTask

        _, _, sede = seed_admin(db_session)
        project = create_project_factory(db_session, sede_id=sede.id)
        rule = ProjectAutomationRule(
            project_id=project.id,
            sede_id=sede.id,
            name="Seguimiento automático",
            trigger_event="task_completed",
            condition_data={},
            action_type="create_followup_task",
            action_data={"title": "Seguimiento generado", "duration_days": 3},
            is_active=True,
        )
        db_session.add(rule)
        db_session.commit()
        task_count_before = db_session.query(ProjectTask).filter(
            ProjectTask.project_id == project.id,
            ProjectTask.deleted_at.is_(None),
        ).count()

        response = client.post(
            f"/api/projects/{project.id}/automations/evaluate",
            json={"trigger_event": "task_completed", "dry_run": False},
            headers=auth_headers(client),
        )

        assert response.status_code == 200, response.text
        assert response.json()[0]["status"] == "executed"
        db_session.expire_all()
        assert db_session.query(ProjectTask).filter(
            ProjectTask.project_id == project.id,
            ProjectTask.deleted_at.is_(None),
        ).count() == task_count_before + 1
        persisted_rule = db_session.query(ProjectAutomationRule).filter(ProjectAutomationRule.id == rule.id).one()
        assert persisted_rule.execution_count == 1

    def test_followup_automation_rejects_titles_over_database_limit(self, client, db_session):
        """Invalid action JSON must not turn a valid automation request into a DB 500."""
        from backend.models_projects import ProjectAutomationRule, ProjectTask

        _, _, sede = seed_admin(db_session)
        project = create_project_factory(db_session, sede_id=sede.id)
        rule = ProjectAutomationRule(
            project_id=project.id,
            sede_id=sede.id,
            name="Tarea de seguimiento inválida",
            trigger_event="task_completed",
            condition_data={},
            action_type="create_followup_task",
            action_data={"title": "T" * 201},
            is_active=True,
        )
        db_session.add(rule)
        db_session.commit()
        task_count_before = db_session.query(ProjectTask).filter(
            ProjectTask.project_id == project.id,
            ProjectTask.deleted_at.is_(None),
        ).count()

        response = client.post(
            f"/api/projects/{project.id}/automations/evaluate",
            json={"trigger_event": "task_completed"},
            headers=auth_headers(client),
        )

        assert response.status_code == 200, response.text
        assert response.json()[0]["status"] == "failed"
        assert "no puede superar 200 caracteres" in response.json()[0]["details"]
        assert db_session.query(ProjectTask).filter(
            ProjectTask.project_id == project.id,
            ProjectTask.deleted_at.is_(None),
        ).count() == task_count_before


class TestProjectTimeTracking:
    def test_create_time_log_defaults_to_authenticated_persona(self, client, db_session):
        _, actor_persona, sede = seed_admin(db_session, email="time-log-actor@test.com")
        project = create_project_factory(db_session, sede_id=sede.id)

        response = client.post(
            f"/api/projects/{project.id}/time-logs",
            json={"hours": 1.5, "description": "Trabajo de prueba"},
            headers=auth_headers(client, email="time-log-actor@test.com"),
        )

        assert response.status_code == 201, response.text
        assert response.json()["persona_id"] == str(actor_persona.id)
        assert response.json()["hours"] == 1.5

    def test_create_time_log_allows_same_sede_persona_attribution(self, client, db_session):
        _, _, sede = seed_admin(db_session, email="time-log-manager@test.com")
        project = create_project_factory(db_session, sede_id=sede.id)
        teammate = Persona(
            id=_uuid.uuid4(),
            first_name="Equipo",
            last_name="Proyectos",
            email="time-log-teammate@test.com",
            sede_id=sede.id,
        )
        db_session.add(teammate)
        db_session.commit()

        response = client.post(
            f"/api/projects/{project.id}/time-logs",
            json={"hours": 2, "persona_id": str(teammate.id)},
            headers=auth_headers(client, email="time-log-manager@test.com"),
        )

        assert response.status_code == 201, response.text
        assert response.json()["persona_id"] == str(teammate.id)


class TestProjectOwnerContract:
    def test_create_project_honors_requested_same_sede_owner(self, client, db_session):
        _, _, sede = seed_admin(db_session, email="project-owner-creator@test.com")
        owner = Persona(
            id=_uuid.uuid4(),
            first_name="Responsable",
            last_name="Proyecto",
            email="project-owner-same-sede@test.com",
            sede_id=sede.id,
        )
        db_session.add(owner)
        db_session.commit()

        response = client.post(
            "/api/projects",
            json={"title": "Proyecto con responsable elegido", "owner_id": str(owner.id)},
            headers=auth_headers(client, email="project-owner-creator@test.com"),
        )

        assert response.status_code == 201, response.text
        assert response.json()["owner_id"] == str(owner.id)


class TestProjectBudgetLifecycle:
    def test_budget_summary_get_does_not_persist_derived_spend(self, client, db_session):
        _, _, sede = seed_admin(db_session, email="project-budget-summary-read-only@test.com")
        project = create_project_factory(db_session, sede_id=sede.id)
        project.budget_allocated = 1000
        project.budget_spent = 75
        db_session.commit()

        response = client.get(
            f"/api/projects/{project.id}/budget-summary",
            headers=auth_headers(client, email="project-budget-summary-read-only@test.com"),
        )

        assert response.status_code == 200, response.text
        assert response.json()["budget_spent"] == 0
        db_session.refresh(project)
        assert project.budget_spent == 75

    def test_expense_lifecycle_recalculates_paid_budget_and_soft_delete(self, client, db_session):
        _, _, sede = seed_admin(db_session, email="project-budget-lifecycle@test.com")
        project = create_project_factory(db_session, sede_id=sede.id)
        project.budget_allocated = 1000
        db_session.commit()
        headers = auth_headers(client, email="project-budget-lifecycle@test.com")
        route = f"/api/projects/{project.id}/expenses"

        created = client.post(
            route,
            json={"category": "materials", "description": "Compra de prueba", "amount": 50},
            headers=headers,
        )
        assert created.status_code == 201, created.text
        expense_id = _uuid.UUID(created.json()["id"])
        db_session.refresh(project)
        assert project.budget_spent == 0

        marked_paid = client.patch(
            f"{route}/{expense_id}",
            json={"status": "paid"},
            headers=headers,
        )
        assert marked_paid.status_code == 200, marked_paid.text
        db_session.refresh(project)
        assert project.budget_spent == 50

        marked_committed = client.patch(
            f"{route}/{expense_id}",
            json={"status": "committed"},
            headers=headers,
        )
        assert marked_committed.status_code == 200, marked_committed.text
        db_session.refresh(project)
        assert project.budget_spent == 0

        summary = client.get(f"/api/projects/{project.id}/budget-summary", headers=headers)
        assert summary.status_code == 200, summary.text
        assert summary.json()["paid_amount"] == 0
        assert summary.json()["committed_amount"] == 50
        assert summary.json()["planned_amount"] == 0
        assert summary.json()["remaining_budget"] == 1000
        assert summary.json()["burn_rate_percent"] == 0

        marked_paid_again = client.patch(
            f"{route}/{expense_id}",
            json={"status": "paid"},
            headers=headers,
        )
        assert marked_paid_again.status_code == 200, marked_paid_again.text
        db_session.refresh(project)
        assert project.budget_spent == 50

        deleted = client.delete(f"{route}/{expense_id}", headers=headers)
        assert deleted.status_code == 200, deleted.text
        expense = db_session.query(ProjectExpense).filter_by(id=expense_id).one()
        db_session.refresh(project)
        assert expense.deleted_at is not None
        assert project.budget_spent == 0

        final_summary = client.get(f"/api/projects/{project.id}/budget-summary", headers=headers)
        assert final_summary.status_code == 200, final_summary.text
        assert final_summary.json()["total_expenses_count"] == 0
        assert final_summary.json()["paid_amount"] == 0


class TestProjectExternalLinkValidation:
    def test_expense_patch_can_clear_nullable_receipt_and_description(self, client, db_session):
        _, _, sede = seed_admin(db_session, email="project-expense-clear-null@test.com")
        project = create_project_factory(db_session, sede_id=sede.id)
        headers = auth_headers(client, email="project-expense-clear-null@test.com")
        created = client.post(
            f"/api/projects/{project.id}/expenses",
            json={
                "amount": 24.5,
                "description": "Factura de materiales",
                "receipt_url": "https://example.org/receipt/24",
            },
            headers=headers,
        )

        assert created.status_code == 201, created.text
        expense_id = created.json()["id"]
        assert created.json()["receipt_url"] == "https://example.org/receipt/24"

        updated = client.patch(
            f"/api/projects/{project.id}/expenses/{expense_id}",
            json={"receipt_url": None, "description": None},
            headers=headers,
        )

        assert updated.status_code == 200, updated.text
        assert updated.json()["receipt_url"] is None
        assert updated.json()["description"] is None
        db_session.expire_all()
        stored = db_session.query(ProjectExpense).filter_by(id=_uuid.UUID(expense_id)).one()
        assert stored.receipt_url is None
        assert stored.description is None

    def test_expense_rejects_scriptable_receipt_url_without_persisting(self, client, db_session):
        _, _, sede = seed_admin(db_session, email="project-receipt-url@test.com")
        project = create_project_factory(db_session, sede_id=sede.id)

        response = client.post(
            f"/api/projects/{project.id}/expenses",
            json={"amount": 1, "receipt_url": "javascript:alert(document.domain)"},
            headers=auth_headers(client, email="project-receipt-url@test.com"),
        )

        assert response.status_code == 422, response.text
        assert db_session.query(ProjectExpense).filter_by(project_id=project.id).count() == 0

    def test_indicator_record_rejects_scriptable_evidence_url_without_persisting(
        self, client, db_session
    ):
        _, actor, sede = seed_admin(db_session, email="project-evidence-url@test.com")
        project = create_project_factory(db_session, sede_id=sede.id)
        indicator = ProjectIndicator(
            project_id=project.id,
            name="Indicador con evidencia",
            target_value=10,
            sede_id=sede.id,
            created_by=actor.id,
        )
        db_session.add(indicator)
        db_session.commit()

        response = client.post(
            f"/api/projects/{project.id}/indicators/{indicator.id}/records",
            json={"period": "2026-Q4", "evidence_url": "data:text/html,<script>alert(1)</script>"},
            headers=auth_headers(client, email="project-evidence-url@test.com"),
        )

        assert response.status_code == 422, response.text
        assert db_session.query(ProjectIndicatorRecord).filter_by(indicator_id=indicator.id).count() == 0


class TestProjectIndicatorRouteScoping:
    def test_indicator_spi_is_calculated_by_backend_not_client(self, client, db_session):
        _, actor, sede = seed_admin(db_session, email="indicator-spi-authority@test.com")
        project = create_project_factory(db_session, sede_id=sede.id)
        indicator = ProjectIndicator(
            project_id=project.id,
            name="Indicador de ejecución",
            target_value=100,
            current_value=0,
            sede_id=sede.id,
            created_by=actor.id,
        )
        db_session.add(indicator)
        db_session.commit()

        response = client.post(
            f"/api/projects/{project.id}/indicators/{indicator.id}/records",
            json={
                "period": "2026-10",
                "target_value": 100,
                "actual_value": 25,
                "spi": 9.99,
            },
            headers=auth_headers(client, email="indicator-spi-authority@test.com"),
        )

        assert response.status_code == 201, response.text
        assert response.json()["spi"] == 0.25
        db_session.expire_all()
        persisted = db_session.query(ProjectIndicatorRecord).filter_by(id=response.json()["id"]).one()
        assert persisted.spi == 0.25

    def test_indicator_mutations_and_records_are_scoped_to_route_project(self, client, db_session):
        _, actor, sede = seed_admin(db_session, email="indicator-scope@test.com")
        route_project = create_project_factory(db_session, sede_id=sede.id)
        owning_project = create_project_factory(db_session, sede_id=sede.id)
        indicator = ProjectIndicator(
            project_id=owning_project.id,
            name="Indicador privado",
            current_value=4,
            target_value=10,
            sede_id=sede.id,
            created_by=actor.id,
        )
        db_session.add(indicator)
        db_session.flush()
        record = ProjectIndicatorRecord(
            indicator_id=indicator.id,
            period="2026-10",
            target_value=10,
            actual_value=4,
            reported_by=actor.id,
        )
        db_session.add(record)
        db_session.commit()
        headers = auth_headers(client, email="indicator-scope@test.com")

        update = client.patch(
            f"/api/projects/{route_project.id}/advanced-indicators/{indicator.id}",
            json={"name": "No debe cambiarse"}, headers=headers,
        )
        delete = client.delete(
            f"/api/projects/{route_project.id}/advanced-indicators/{indicator.id}", headers=headers,
        )
        add_record = client.post(
            f"/api/projects/{route_project.id}/indicators/{indicator.id}/records",
            json={"period": "2026-11", "target_value": 10, "actual_value": 9}, headers=headers,
        )
        list_records = client.get(
            f"/api/projects/{route_project.id}/indicators/{indicator.id}/records", headers=headers,
        )

        assert [update.status_code, delete.status_code, add_record.status_code, list_records.status_code] == [404] * 4
        db_session.refresh(indicator)
        assert indicator.name == "Indicador privado"
        assert indicator.deleted_at is None
        assert db_session.query(ProjectIndicatorRecord).filter_by(indicator_id=indicator.id).count() == 1


class TestProjectFileAssociationScoping:
    def test_drive_link_accepts_google_docs_host_and_normalizes_embed(self, client, db_session):
        _, _, sede = seed_admin(db_session, email="project-drive-docs@test.com")
        project = create_project_factory(db_session, sede_id=sede.id)

        response = client.post(
            f"/api/projects/{project.id}/files/link-drive",
            json={
                "drive_url": "https://docs.google.com/document/d/document-file-id-123/edit",
                "name": "Documento de Google",
            },
            headers=auth_headers(client, email="project-drive-docs@test.com"),
        )

        assert response.status_code == 200, response.text
        assert response.json()["embed_url"] == "https://docs.google.com/document/d/document-file-id-123/preview"

    @pytest.mark.parametrize(
        "drive_url",
        [
            "https://evil.example/file/d/attacker-file-id/view",
            "https://drive.google.com.evil.example/file/d/attacker-file-id/view",
            "http://drive.google.com/file/d/attacker-file-id/view",
        ],
    )
    def test_drive_link_rejects_non_google_or_insecure_hosts(
        self, client, db_session, drive_url
    ):
        _, _, sede = seed_admin(db_session, email="project-drive-host@test.com")
        project = create_project_factory(db_session, sede_id=sede.id)

        response = client.post(
            f"/api/projects/{project.id}/files/link-drive",
            json={"drive_url": drive_url, "name": "Enlace externo"},
            headers=auth_headers(client, email="project-drive-host@test.com"),
        )

        assert response.status_code == 400, response.text
        assert db_session.query(ProjectFile).filter_by(project_id=project.id).count() == 0

    @pytest.mark.parametrize("association", ["task_id", "phase_id"])
    def test_drive_file_cannot_reference_another_projects_task_or_phase(
        self, client, db_session, association
    ):
        _, _, sede = seed_admin(db_session, email=f"project-file-{association}@test.com")
        target_project = create_project_factory(db_session, sede_id=sede.id)
        other_project = create_project_factory(db_session, sede_id=sede.id)
        target_task = create_task_factory(db_session, target_project.id)
        task = create_task_factory(db_session, other_project.id)
        target_phase = ProjectPhase(
            id=_uuid.uuid4(),
            project_id=target_project.id,
            name="Fase destino",
            slug="fase-destino",
            order_index=1,
        )
        phase = ProjectPhase(
            id=_uuid.uuid4(),
            project_id=other_project.id,
            name="Fase privada",
            slug="fase-privada",
            order_index=1,
        )
        db_session.add_all([target_phase, phase])
        db_session.commit()
        linked_id = task.id if association == "task_id" else phase.id
        target_linked_id = target_task.id if association == "task_id" else target_phase.id

        response = client.post(
            f"/api/projects/{target_project.id}/files/link-drive",
            json={
                "drive_url": "https://drive.google.com/file/d/drive-file-id-123/view",
                "name": "Documento vinculado",
                association: str(linked_id),
            },
            headers=auth_headers(client, email=f"project-file-{association}@test.com"),
        )

        assert response.status_code == 404, response.text
        assert db_session.query(ProjectFile).filter_by(project_id=target_project.id).count() == 0

        valid_response = client.post(
            f"/api/projects/{target_project.id}/files/link-drive",
            json={
                "drive_url": "https://drive.google.com/file/d/drive-file-valid-123/view",
                "name": "Documento válido",
                association: str(target_linked_id),
            },
            headers=auth_headers(client, email=f"project-file-{association}@test.com"),
        )
        assert valid_response.status_code == 200, valid_response.text
        assert valid_response.json()[association] == str(target_linked_id)

        invalid_filter = client.get(
            f"/api/projects/{target_project.id}/files",
            params={association: str(linked_id)},
            headers=auth_headers(client, email=f"project-file-{association}@test.com"),
        )
        assert invalid_filter.status_code == 404, invalid_filter.text


class TestProjectCommentAssociationScoping:
    @pytest.mark.parametrize("route_kind", ["flat", "nested"])
    def test_comment_cannot_reference_task_from_another_project(self, client, db_session, route_kind):
        _, _, sede = seed_admin(db_session, email=f"project-comment-{route_kind}@test.com")
        target_project = create_project_factory(db_session, sede_id=sede.id)
        other_project = create_project_factory(db_session, sede_id=sede.id)
        target_task = create_task_factory(db_session, target_project.id)
        other_task = create_task_factory(db_session, other_project.id)
        if route_kind == "flat":
            route = "/api/projects/comments"
            payload = {
                "project_id": str(target_project.id),
                "task_id": str(other_task.id),
                "content": "No debe vincularse",
            }
        else:
            route = f"/api/projects/{target_project.id}/comments"
            payload = {"task_id": str(other_task.id), "content": "No debe vincularse"}

        response = client.post(
            route,
            json=payload,
            headers=auth_headers(client, email=f"project-comment-{route_kind}@test.com"),
        )

        assert response.status_code == 404, response.text
        assert db_session.query(ProjectComment).filter_by(project_id=target_project.id).count() == 0

        if route_kind == "flat":
            payload.update(project_id=str(target_project.id), task_id=str(target_task.id))
        else:
            payload["task_id"] = str(target_task.id)
        valid_response = client.post(
            route,
            json=payload,
            headers=auth_headers(client, email=f"project-comment-{route_kind}@test.com"),
        )
        assert valid_response.status_code == 200, valid_response.text
        assert valid_response.json()["task_id"] == str(target_task.id)


class TestProjectTaskDependencyScoping:
    @pytest.mark.parametrize("foreign_endpoint", ["predecessor_id", "successor_id"])
    def test_dependency_rejects_task_from_another_project(self, client, db_session, foreign_endpoint):
        _, _, sede = seed_admin(db_session, email=f"project-dependency-{foreign_endpoint}@test.com")
        project = create_project_factory(db_session, sede_id=sede.id)
        other_project = create_project_factory(db_session, sede_id=sede.id)
        local_tasks = [create_task_factory(db_session, project.id) for _ in range(2)]
        foreign_task = create_task_factory(db_session, other_project.id)
        task_ids = {
            "predecessor_id": str(local_tasks[0].id),
            "successor_id": str(local_tasks[1].id),
        }
        task_ids[foreign_endpoint] = str(foreign_task.id)

        response = client.post(
            f"/api/projects/{project.id}/dependencies",
            json=task_ids,
            headers=auth_headers(client, email=f"project-dependency-{foreign_endpoint}@test.com"),
        )

        assert response.status_code == 404, response.text
        assert db_session.query(ProjectTaskDependency).filter_by(project_id=project.id).count() == 0

    def test_dependency_accepts_two_active_tasks_from_same_project(self, client, db_session):
        _, _, sede = seed_admin(db_session, email="project-dependency-local@test.com")
        project = create_project_factory(db_session, sede_id=sede.id)
        predecessor = create_task_factory(db_session, project.id)
        successor = create_task_factory(db_session, project.id)

        response = client.post(
            f"/api/projects/{project.id}/dependencies",
            json={"predecessor_id": str(predecessor.id), "successor_id": str(successor.id)},
            headers=auth_headers(client, email="project-dependency-local@test.com"),
        )

        assert response.status_code == 201, response.text
        assert response.json()["project_id"] == str(project.id)

    def test_deleted_dependency_pair_can_be_recreated(self, client, db_session):
        """Soft-delete must not permanently reserve a unique task pair."""
        _, _, sede = seed_admin(db_session, email="project-dependency-restore@test.com")
        project = create_project_factory(db_session, sede_id=sede.id)
        predecessor = create_task_factory(db_session, project.id)
        successor = create_task_factory(db_session, project.id)
        headers = auth_headers(client, email="project-dependency-restore@test.com")
        route = f"/api/projects/{project.id}/dependencies"
        payload = {"predecessor_id": str(predecessor.id), "successor_id": str(successor.id)}

        created = client.post(route, json=payload, headers=headers)
        assert created.status_code == 201, created.text
        dependency_id = created.json()["id"]

        deleted = client.delete(f"{route}/{dependency_id}", headers=headers)
        assert deleted.status_code == 200, deleted.text

        recreated = client.post(
            route,
            json={**payload, "dependency_type": "SS", "lag_days": 2},
            headers=headers,
        )

        assert recreated.status_code == 201, recreated.text
        assert recreated.json()["id"] == dependency_id
        assert recreated.json()["dependency_type"] == "SS"
        assert recreated.json()["lag_days"] == 2
        row = db_session.query(ProjectTaskDependency).filter_by(id=_uuid.UUID(dependency_id)).one()
        assert row.deleted_at is None

    def test_crud_rejects_cross_project_dependency_without_persisting(self, db_session):
        from backend.crud.projects import create_task_dependency
        from backend.schemas.projects import ProjectTaskDependencyCreate

        project = create_project_factory(db_session)
        other_project = create_project_factory(db_session)
        predecessor = create_task_factory(db_session, project.id)
        successor = create_task_factory(db_session, other_project.id)
        payload = ProjectTaskDependencyCreate(
            predecessor_id=predecessor.id,
            successor_id=successor.id,
        )

        with pytest.raises(ValueError, match="Both dependency tasks"):
            create_task_dependency(db_session, project.id, payload)

        assert db_session.query(ProjectTaskDependency).count() == 0
