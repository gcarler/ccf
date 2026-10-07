"""TDD-red suite: Projects multi-tenant (Axioma 3) defense-in-depth.

Validates that the Projects module is leak-proof at three layers:

1. API-layer scope: the route helpers (`_ensure_project`, list filters)
   must return 404 (not 403, never revealing existence) when the actor's
   `sede_id` does not match the project's `sede_id`. — Likely GREEN today.
2. CRUD-layer defense-in-depth: the CRUD functions should accept and
   enforce an `actor_user_id` argument that re-validates the scope — RED.
3. notify_task_assigned atomicity: when `send_email` raises, the
   NotificacionUsuario + CommunicationLog + activity_log inserts must
   roll back as a single transaction. — RED.

All cross-sede assertions must use 404 (existence-leak safe). 403 is FORBIDDEN.
"""

from __future__ import annotations

import uuid as _uuid
from datetime import datetime, timezone

import pytest

from backend import models as _models
from tests.conftest import auth_headers, seed_admin
from tests.factories_projects import (
    create_project_factory,
    create_subtask_factory,
    create_task_factory,
)

# ── Helper: seed TWO admins in DIFFERENT sedes ───────────────────────────


def _seed_paired_sedes(db):
    """Return (sede_A, sede_B). User objects aren't needed by any current
    caller — pair of admin sedA + sedB is enough."""
    _, _, s_a = seed_admin(db, email="adminA@test.com")
    _, _, s_b = seed_admin(db, email="adminB@test.com")
    return s_a, s_b


def _seed_paired_sedes_with_personas(db):
    """Return (sede_A, persona_A, sede_B, persona_B) for tests that need
    the persona records of the paired admins users."""
    _, p_a, s_a = seed_admin(db, email="adminA@test.com")
    _, p_b, s_b = seed_admin(db, email="adminB@test.com")
    return s_a, p_a, s_b, p_b


# ── A: API-layer cross-sede → 404 (existence-leak safe) ──────────────────


class TestMultiTenantAPIScope:
    """Every Projects read/mutation must reject foreign-sede access with 404."""

    def test_get_project_cross_sede_returns_404(self, client, db_session):
        s_a, _ = _seed_paired_sedes(db_session)
        proj_in_a = create_project_factory(db_session, sede_id=s_a.id)
        hdr_b = auth_headers(client, email="adminB@test.com")
        resp = client.get(f"/api/projects/{proj_in_a.id}", headers=hdr_b)
        assert resp.status_code == 404, f"Cross-sede GET must be 404 (leak-proof), got {resp.status_code}: {resp.text}"

    def test_patch_project_cross_sede_returns_404(self, client, db_session):
        s_a, _ = _seed_paired_sedes(db_session)
        proj_in_a = create_project_factory(db_session, sede_id=s_a.id)
        hdr_b = auth_headers(client, email="adminB@test.com")
        resp = client.patch(
            f"/api/projects/{proj_in_a.id}",
            json={"title": "Hacked from B"},
            headers=hdr_b,
        )
        assert resp.status_code == 404, f"Cross-sede PATCH must be 404, got {resp.status_code}: {resp.text}"

    def test_delete_project_cross_sede_returns_404(self, client, db_session):
        s_a, _ = _seed_paired_sedes(db_session)
        proj_in_a = create_project_factory(db_session, sede_id=s_a.id)
        hdr_b = auth_headers(client, email="adminB@test.com")
        resp = client.delete(f"/api/projects/{proj_in_a.id}", headers=hdr_b)
        assert resp.status_code == 404

    def test_delete_task_cross_sede_returns_404_without_soft_delete(self, client, db_session):
        sede_a, _ = _seed_paired_sedes(db_session)
        project_a = create_project_factory(db_session, sede_id=sede_a.id)
        task_a = create_task_factory(db_session, project_a.id, title="Tarea protegida A")

        response = client.delete(
            f"/api/projects/{project_a.id}/tasks/{task_a.id}",
            headers=auth_headers(client, email="adminB@test.com"),
        )

        assert response.status_code == 404, response.text
        db_session.refresh(task_a)
        assert task_a.deleted_at is None

    def test_list_projects_excludes_foreign_sede(self, client, db_session):
        s_a, s_b = _seed_paired_sedes(db_session)
        create_project_factory(db_session, sede_id=s_a.id, title="Solo A")
        create_project_factory(db_session, sede_id=s_b.id, title="Solo B")
        hdr_a = auth_headers(client, email="adminA@test.com")
        hdr_b = auth_headers(client, email="adminB@test.com")
        titles_a = [p["title"] for p in client.get("/api/projects", headers=hdr_a).json()]
        titles_b = [p["title"] for p in client.get("/api/projects", headers=hdr_b).json()]
        assert "Solo A" in titles_a
        assert "Solo A" not in titles_b, "Cross-sede listing leaks A's project to B"
        assert "Solo B" in titles_b
        assert "Solo B" not in titles_a, "Cross-sede listing leaks B's project to A"

    def test_list_projects_page_keeps_tenant_scope_and_total(self, client, db_session):
        s_a, s_b = _seed_paired_sedes(db_session)
        create_project_factory(db_session, sede_id=s_a.id, title="Proyecto visible A")
        create_project_factory(db_session, sede_id=s_b.id, title="Proyecto privado B")
        response = client.get(
            "/api/projects/page?offset=0&limit=1",
            headers=auth_headers(client, email="adminA@test.com"),
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["total"] == 1
        assert len(payload["items"]) == 1
        assert payload["items"][0]["title"] == "Proyecto visible A"

    def test_project_summary_page_keeps_tenant_scope_and_total(self, client, db_session):
        s_a, s_b = _seed_paired_sedes(db_session)
        create_project_factory(db_session, sede_id=s_a.id, title="Resumen visible A")
        create_project_factory(db_session, sede_id=s_b.id, title="Resumen privado B")
        response = client.get(
            "/api/projects/summary-page",
            headers=auth_headers(client, email="adminA@test.com"),
        )

        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["total"] == 1
        assert len(payload["items"]) == 1
        assert payload["items"][0]["title"] == "Resumen visible A"

    def test_list_my_tasks_page_keeps_tenant_scope(self, client, db_session):
        sede_a, persona_a, sede_b, _ = _seed_paired_sedes_with_personas(db_session)
        project_a = create_project_factory(db_session, sede_id=sede_a.id)
        project_b = create_project_factory(db_session, sede_id=sede_b.id)
        create_task_factory(db_session, project_a.id, assignee_id=persona_a.id, title="Tarea A")
        create_task_factory(db_session, project_b.id, assignee_id=persona_a.id, title="Tarea B")

        actor_headers = auth_headers(client, email="adminA@test.com")
        response = client.get(
            "/api/projects/tasks/page",
            headers=actor_headers,
        )
        legacy = client.get("/api/projects/tasks", headers=actor_headers)
        assert response.status_code == 200
        payload = response.json()
        assert payload["total"] == 1
        assert [item["title"] for item in payload["items"]] == ["Tarea A"]
        assert [item["title"] for item in legacy.json()] == ["Tarea A"]

    def test_public_project_template_is_listed_cross_sede_but_read_only(self, client, db_session):
        from backend.models_projects import ProjectTemplate

        _, persona_a, sede_a = seed_admin(db_session, email="templateA@test.com")
        _, _, sede_b = seed_admin(db_session, email="templateB@test.com")
        template = ProjectTemplate(
            id=_uuid.uuid4(),
            name="Plantilla pública de A",
            category="general",
            default_budget=0,
            structure={"phases": [], "tasks": []},
            created_by=persona_a.id,
            is_public=True,
            sede_id=sede_a.id,
        )
        db_session.add(template)
        db_session.commit()

        headers_b = auth_headers(client, email="templateB@test.com")
        listed = client.get("/api/projects/templates", headers=headers_b)
        assert listed.status_code == 200
        assert template.id.hex in {item["id"].replace("-", "") for item in listed.json()}
        assert client.get(f"/api/projects/templates/{template.id}", headers=headers_b).status_code == 200
        instantiated = client.post(
            f"/api/projects/from-template/{template.id}",
            json={"title": "Instanciado en sede B"},
            headers=headers_b,
        )
        assert instantiated.status_code == 201, instantiated.text
        assert instantiated.json()["title"] == "Instanciado en sede B"
        created_project = db_session.query(_models.Project).filter(
            _models.Project.title == "Instanciado en sede B"
        ).one()
        assert created_project.sede_id == sede_b.id
        assert client.patch(
            f"/api/projects/templates/{template.id}",
            json={"name": "Modificada desde B"},
            headers=headers_b,
        ).status_code == 404
        assert client.delete(
            f"/api/projects/templates/{template.id}", headers=headers_b
        ).status_code == 404

        db_session.refresh(template)
        assert template.name == "Plantilla pública de A"
        assert template.deleted_at is None

    def test_create_time_log_rejects_persona_from_another_sede(self, client, db_session):
        from backend.models_projects import ProjectTimeLog

        sede_a, _, sede_b, persona_b = _seed_paired_sedes_with_personas(db_session)
        project_a = create_project_factory(db_session, sede_id=sede_a.id)

        response = client.post(
            f"/api/projects/{project_a.id}/time-logs",
            json={"hours": 1, "persona_id": str(persona_b.id)},
            headers=auth_headers(client, email="adminA@test.com"),
        )

        assert response.status_code == 404, response.text
        assert db_session.query(ProjectTimeLog).filter(ProjectTimeLog.project_id == project_a.id).count() == 0

    def test_create_project_rejects_owner_from_another_sede(self, client, db_session):
        sede_a, _, _, persona_b = _seed_paired_sedes_with_personas(db_session)

        response = client.post(
            "/api/projects",
            json={"title": "Proyecto con owner ajeno", "owner_id": str(persona_b.id)},
            headers=auth_headers(client, email="adminA@test.com"),
        )

        assert response.status_code == 404, response.text
        assert db_session.query(_models.Project).filter(
            _models.Project.title == "Proyecto con owner ajeno",
            _models.Project.sede_id == sede_a.id,
        ).count() == 0

    def test_update_project_rejects_owner_from_another_sede(self, client, db_session):
        sede_a, _, _, persona_b = _seed_paired_sedes_with_personas(db_session)
        project_a = create_project_factory(db_session, sede_id=sede_a.id)
        original_owner_id = project_a.owner_id

        response = client.patch(
            f"/api/projects/{project_a.id}",
            json={"owner_id": str(persona_b.id)},
            headers=auth_headers(client, email="adminA@test.com"),
        )

        assert response.status_code == 404, response.text
        db_session.refresh(project_a)
        assert project_a.owner_id == original_owner_id

    def test_instantiate_template_rejects_owner_from_another_sede(self, client, db_session):
        from backend.models_projects import ProjectTemplate

        sede_a, persona_a, sede_b, _ = _seed_paired_sedes_with_personas(db_session)
        template = ProjectTemplate(
            id=_uuid.uuid4(),
            name="Plantilla pública con asignación segura",
            category="general",
            default_budget=0,
            structure={"phases": [], "tasks": []},
            created_by=persona_a.id,
            is_public=True,
            sede_id=sede_a.id,
        )
        db_session.add(template)
        db_session.commit()

        response = client.post(
            f"/api/projects/from-template/{template.id}",
            json={"title": "Proyecto plantilla owner cross-sede", "owner_id": str(persona_a.id)},
            headers=auth_headers(client, email="adminB@test.com"),
        )

        assert response.status_code == 404, response.text
        assert db_session.query(_models.Project).filter(
            _models.Project.title == "Proyecto plantilla owner cross-sede",
            _models.Project.sede_id == sede_b.id,
        ).count() == 0

    def test_create_project_template_ignores_client_sede_id(self, client, db_session):
        _, _, sede_a = seed_admin(db_session, email="templateCreateA@test.com")
        _, _, sede_b = seed_admin(db_session, email="templateCreateB@test.com")
        headers_a = auth_headers(client, email="templateCreateA@test.com")

        response = client.post(
            "/api/projects/templates",
            headers=headers_a,
            json={
                "name": "Plantilla sede A",
                "category": "general",
                "structure": {"phases": [], "tasks": []},
                "is_public": True,
                "sede_id": str(sede_b.id),
            },
        )

        assert response.status_code == 201, response.text
        assert response.json()["sede_id"] == str(sede_a.id)

    def test_only_projects_manager_can_mutate_global_templates(self, client, db_session):
        from backend.models_projects import ProjectTemplate
        from tests.test_projects_rbac import _seed_role_user

        _, _, sede = seed_admin(db_session, email="globalTemplateAdmin@test.com")
        global_template = ProjectTemplate(
            id=_uuid.uuid4(),
            name="Plantilla ministerial",
            category="general",
            default_budget=0,
            structure={"phases": [], "tasks": []},
            is_public=True,
            sede_id=None,
        )
        db_session.add(global_template)
        db_session.commit()
        editor, _, _ = _seed_role_user(db_session, "Editor", "globalTemplateEditor@test.com")
        editor.sede_id = sede.id
        db_session.commit()
        headers = auth_headers(client, email=editor.email)

        patch_response = client.patch(
            f"/api/projects/templates/{global_template.id}",
            json={"name": "Alteración no autorizada"},
            headers=headers,
        )
        delete_response = client.delete(
            f"/api/projects/templates/{global_template.id}", headers=headers
        )
        assert patch_response.status_code == 404
        assert delete_response.status_code == 404
        db_session.refresh(global_template)
        assert global_template.name == "Plantilla ministerial"
        assert global_template.deleted_at is None

    def test_create_task_cross_sede_returns_404(self, client, db_session):
        s_a, _ = _seed_paired_sedes(db_session)
        proj_in_a = create_project_factory(db_session, sede_id=s_a.id)
        hdr_b = auth_headers(client, email="adminB@test.com")
        resp = client.post(
            f"/api/projects/{proj_in_a.id}/tasks",
            json={"title": "Injected from B", "status": "todo"},
            headers=hdr_b,
        )
        assert resp.status_code == 404

    def test_create_comment_cross_sede_returns_404(self, client, db_session):
        s_a, _ = _seed_paired_sedes(db_session)
        proj_in_a = create_project_factory(db_session, sede_id=s_a.id)
        hdr_b = auth_headers(client, email="adminB@test.com")
        resp = client.post(
            f"/api/projects/{proj_in_a.id}/comments",
            json={"content": "Leaking into A's project"},
            headers=hdr_b,
        )
        assert resp.status_code == 404


# ── A.1: Assignee scope must be existence-leak safe ─────────────────────


class TestAssigneeSedeScope:
    """_assert_assignee_in_sede must return the same 404 for missing and cross-sede personas."""

    def test_create_task_with_nonexistent_assignee_returns_404(self, client, db_session):
        s_a, _, _, _ = _seed_paired_sedes_with_personas(db_session)
        proj_in_a = create_project_factory(db_session, sede_id=s_a.id)
        hdr_a = auth_headers(client, email="adminA@test.com")
        resp = client.post(
            f"/api/projects/{proj_in_a.id}/tasks",
            json={"title": "Task with missing assignee", "assignee_id": str(_uuid.uuid4())},
            headers=hdr_a,
        )
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Assignee not found"

    def test_create_task_with_cross_sede_assignee_returns_404(self, client, db_session):
        s_a, _, _, persona_b = _seed_paired_sedes_with_personas(db_session)
        proj_in_a = create_project_factory(db_session, sede_id=s_a.id)
        hdr_a = auth_headers(client, email="adminA@test.com")
        resp = client.post(
            f"/api/projects/{proj_in_a.id}/tasks",
            json={"title": "Task with cross-sede assignee", "assignee_id": str(persona_b.id)},
            headers=hdr_a,
        )
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Assignee not found"

    def test_create_task_with_unscoped_assignee_returns_404(self, client, db_session):
        s_a, _, _, _ = _seed_paired_sedes_with_personas(db_session)
        unscoped = _models.Persona(
            id=_uuid.uuid4(),
            first_name="Unscoped",
            last_name="Persona",
            email=f"unscoped-{_uuid.uuid4().hex[:8]}@example.com",
            sede_id=None,
        )
        db_session.add(unscoped)
        db_session.commit()
        proj_in_a = create_project_factory(db_session, sede_id=s_a.id)
        hdr_a = auth_headers(client, email="adminA@test.com")
        resp = client.post(
            f"/api/projects/{proj_in_a.id}/tasks",
            json={"title": "Task with unscoped assignee", "assignee_id": str(unscoped.id)},
            headers=hdr_a,
        )
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Assignee not found"

    def test_update_task_with_cross_sede_assignee_returns_404(self, client, db_session):
        s_a, persona_a, _, persona_b = _seed_paired_sedes_with_personas(db_session)
        proj_in_a = create_project_factory(db_session, sede_id=s_a.id)
        task = create_task_factory(db_session, proj_in_a.id, assignee_id=persona_a.id)
        hdr_a = auth_headers(client, email="adminA@test.com")
        resp = client.patch(
            f"/api/projects/{proj_in_a.id}/tasks/{task.id}",
            json={"assignee_id": str(persona_b.id)},
            headers=hdr_a,
        )
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Assignee not found"

    def test_create_subtask_with_cross_sede_assignee_returns_404(self, client, db_session):
        s_a, persona_a, _, persona_b = _seed_paired_sedes_with_personas(db_session)
        proj_in_a = create_project_factory(db_session, sede_id=s_a.id)
        task = create_task_factory(db_session, proj_in_a.id, assignee_id=persona_a.id)
        hdr_a = auth_headers(client, email="adminA@test.com")
        resp = client.post(
            f"/api/projects/{proj_in_a.id}/tasks/{task.id}/subtasks",
            json={"title": "Subtask with cross-sede assignee", "assignee_id": str(persona_b.id)},
            headers=hdr_a,
        )
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Assignee not found"

    def test_update_subtask_with_cross_sede_assignee_returns_404(self, client, db_session):
        s_a, persona_a, _, persona_b = _seed_paired_sedes_with_personas(db_session)
        proj_in_a = create_project_factory(db_session, sede_id=s_a.id)
        task = create_task_factory(db_session, proj_in_a.id, assignee_id=persona_a.id)
        subtask = create_subtask_factory(db_session, task.id, proj_in_a.id, assignee_id=persona_a.id)
        hdr_a = auth_headers(client, email="adminA@test.com")
        resp = client.patch(
            f"/api/projects/{proj_in_a.id}/tasks/{task.id}/subtasks/{subtask.id}",
            json={"assignee_id": str(persona_b.id)},
            headers=hdr_a,
        )
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Assignee not found"

    def test_create_subtask_with_unscoped_assignee_returns_404(self, client, db_session):
        s_a, persona_a, _, _ = _seed_paired_sedes_with_personas(db_session)
        unscoped = _models.Persona(
            id=_uuid.uuid4(),
            first_name="Unscoped",
            last_name="Subtask",
            email=f"unscoped-subtask-{_uuid.uuid4().hex[:8]}@example.com",
            sede_id=None,
        )
        db_session.add(unscoped)
        db_session.commit()
        project = create_project_factory(db_session, sede_id=s_a.id)
        parent = create_task_factory(db_session, project.id, assignee_id=persona_a.id)
        headers = auth_headers(client, email="adminA@test.com")
        response = client.post(
            f"/api/projects/{project.id}/tasks/{parent.id}/subtasks",
            json={"title": "Subtask with unscoped assignee", "assignee_id": str(unscoped.id)},
            headers=headers,
        )
        assert response.status_code == 404


    def test_update_task_flat_with_cross_sede_assignee_returns_404(self, client, db_session):
        s_a, persona_a, _, persona_b = _seed_paired_sedes_with_personas(db_session)
        proj_in_a = create_project_factory(db_session, sede_id=s_a.id)
        task = create_task_factory(db_session, proj_in_a.id, assignee_id=persona_a.id)
        hdr_a = auth_headers(client, email="adminA@test.com")
        resp = client.patch(
            f"/api/projects/tasks/{task.id}",
            json={"assignee_id": str(persona_b.id)},
            headers=hdr_a,
        )
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Assignee not found"

    def test_update_task_with_unscoped_assignee_returns_404(self, client, db_session):
        s_a, persona_a, _, _ = _seed_paired_sedes_with_personas(db_session)
        unscoped = _models.Persona(
            id=_uuid.uuid4(),
            first_name="Unscoped",
            last_name="Persona",
            email=f"unscoped-update-{_uuid.uuid4().hex[:8]}@example.com",
            sede_id=None,
        )
        db_session.add(unscoped)
        db_session.commit()
        proj_in_a = create_project_factory(db_session, sede_id=s_a.id)
        task = create_task_factory(db_session, proj_in_a.id, assignee_id=persona_a.id)
        hdr_a = auth_headers(client, email="adminA@test.com")
        resp = client.patch(
            f"/api/projects/{proj_in_a.id}/tasks/{task.id}",
            json={"assignee_id": str(unscoped.id)},
            headers=hdr_a,
        )
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Assignee not found"


    def test_create_subtask_cross_sede_project_returns_404(self, client, db_session):
        s_a, _ = _seed_paired_sedes(db_session)
        project = create_project_factory(db_session, sede_id=s_a.id)
        parent = create_task_factory(db_session, project.id)
        headers_b = auth_headers(client, email="adminB@test.com")
        response = client.post(
            f"/api/projects/{project.id}/tasks/{parent.id}/subtasks",
            json={"title": "Subtask injected from B"},
            headers=headers_b,
        )
        assert response.status_code == 404


class TestAutomationManagementAndSedeScope:
    """Automation access is tenant-safe and global rules are manager-only."""

    def test_create_automation_uses_project_sede_not_client_sede(self, client, db_session):
        from backend.models_projects import ProjectAutomationRule

        sede_a, _, sede_b, _ = _seed_paired_sedes_with_personas(db_session)
        project = create_project_factory(db_session, sede_id=sede_a.id)
        response = client.post(
            f"/api/projects/{project.id}/automations",
            json={"name": "Regla con sede manipulada", "sede_id": str(sede_b.id)},
            headers=auth_headers(client, email="adminA@test.com"),
        )

        assert response.status_code == 201, response.text
        assert response.json()["sede_id"] == str(sede_a.id)
        rule = db_session.query(ProjectAutomationRule).filter(
            ProjectAutomationRule.id == response.json()["id"]
        ).one()
        assert rule.sede_id == sede_a.id

    def test_notify_automation_rejects_cross_sede_context_recipient(self, client, db_session):
        from backend.models_projects import ProjectActivityLog, ProjectAutomationRule

        sede_a, _, _, persona_b = _seed_paired_sedes_with_personas(db_session)
        project = create_project_factory(db_session, sede_id=sede_a.id)
        rule = ProjectAutomationRule(
            project_id=project.id,
            sede_id=sede_a.id,
            name="Notificar responsable",
            trigger_event="task_completed",
            condition_data={},
            action_type="notify_assignee",
            action_data={},
            is_active=True,
        )
        db_session.add(rule)
        db_session.commit()
        activity_count_before = db_session.query(ProjectActivityLog).filter(
            ProjectActivityLog.project_id == project.id,
        ).count()

        response = client.post(
            f"/api/projects/{project.id}/automations/evaluate",
            json={
                "trigger_event": "task_completed",
                "context_data": {"assignee_id": str(persona_b.id)},
                "dry_run": False,
            },
            headers=auth_headers(client, email="adminA@test.com"),
        )

        assert response.status_code == 200, response.text
        assert response.json()[0]["status"] == "failed"
        assert "not found in actor sede" in response.json()[0]["details"]
        assert db_session.query(ProjectActivityLog).filter(
            ProjectActivityLog.project_id == project.id,
        ).count() == activity_count_before
        db_session.refresh(rule)
        assert rule.execution_count == 0
        assert rule.last_triggered_at is None

    def test_notify_automation_allows_same_sede_context_recipient(self, client, db_session):
        from backend.models_projects import ProjectActivityLog, ProjectAutomationRule

        sede_a, persona_a, _, _ = _seed_paired_sedes_with_personas(db_session)
        project = create_project_factory(db_session, sede_id=sede_a.id)
        rule = ProjectAutomationRule(
            project_id=project.id,
            sede_id=sede_a.id,
            name="Notificar responsable local",
            trigger_event="task_completed",
            condition_data={},
            action_type="notify_assignee",
            action_data={},
            is_active=True,
        )
        db_session.add(rule)
        db_session.commit()

        response = client.post(
            f"/api/projects/{project.id}/automations/evaluate",
            json={
                "trigger_event": "task_completed",
                "context_data": {"assignee_id": str(persona_a.id)},
                "dry_run": False,
            },
            headers=auth_headers(client, email="adminA@test.com"),
        )

        assert response.status_code == 200, response.text
        assert response.json()[0]["status"] == "executed"
        activity = db_session.query(ProjectActivityLog).filter(
            ProjectActivityLog.project_id == project.id,
        ).one()
        assert activity.persona_id == persona_a.id

    def test_editor_can_preview_but_only_manager_can_execute_sede_wide_rules(self, client, db_session):
        from backend.models_projects import ProjectActivityLog, ProjectAutomationRule, ProjectTask
        from tests.test_projects_rbac import _seed_role_user

        _, _, sede = seed_admin(db_session, email="automationExecutionOwner@test.com")
        project = create_project_factory(db_session, sede_id=sede.id)
        rule = ProjectAutomationRule(
            project_id=None,
            sede_id=sede.id,
            name="Seguimiento compartido",
            trigger_event="task_completed",
            condition_data={},
            action_type="create_followup_task",
            action_data={"title": "Seguimiento desde regla global"},
            is_active=True,
        )
        editor, _, _ = _seed_role_user(db_session, "Editor", "automationExecutionEditor@test.com")
        manager, _, _ = _seed_role_user(db_session, "Gestor", "automationExecutionManager@test.com")
        editor.sede_id = sede.id
        manager.sede_id = sede.id
        db_session.add(rule)
        db_session.commit()
        project_path = f"/api/projects/{project.id}/automations/evaluate"
        task_count_before = db_session.query(ProjectTask).filter(
            ProjectTask.project_id == project.id,
            ProjectTask.deleted_at.is_(None),
        ).count()
        activity_count_before = db_session.query(ProjectActivityLog).filter(
            ProjectActivityLog.project_id == project.id,
        ).count()

        preview = client.post(
            project_path,
            json={"trigger_event": "task_completed", "dry_run": True},
            headers=auth_headers(client, email=editor.email),
        )
        execution = client.post(
            project_path,
            json={"trigger_event": "task_completed", "dry_run": False},
            headers=auth_headers(client, email=editor.email),
        )

        assert preview.status_code == 200, preview.text
        assert preview.json()[0]["status"] == "would_execute"
        assert execution.status_code == 403, execution.text
        db_session.expire_all()
        assert db_session.query(ProjectTask).filter(
            ProjectTask.project_id == project.id,
            ProjectTask.deleted_at.is_(None),
        ).count() == task_count_before
        assert db_session.query(ProjectActivityLog).filter(
            ProjectActivityLog.project_id == project.id,
        ).count() == activity_count_before
        db_session.refresh(rule)
        assert rule.execution_count == 0
        assert rule.last_triggered_at is None

        manager_execution = client.post(
            project_path,
            json={"trigger_event": "task_completed", "dry_run": False},
            headers=auth_headers(client, email=manager.email),
        )

        assert manager_execution.status_code == 200, manager_execution.text
        assert manager_execution.json()[0]["status"] == "executed"
        db_session.expire_all()
        assert db_session.query(ProjectTask).filter(
            ProjectTask.project_id == project.id,
            ProjectTask.deleted_at.is_(None),
        ).count() == task_count_before + 1
        db_session.refresh(rule)
        assert rule.execution_count == 1

    def test_reassign_automation_rejects_cross_sede_assignee(self, client, db_session):
        from backend.models_projects import ProjectActivityLog, ProjectAutomationRule, ProjectTask

        sede_a, persona_a, _, persona_b = _seed_paired_sedes_with_personas(db_session)
        project = create_project_factory(db_session, sede_id=sede_a.id)
        task = create_task_factory(db_session, project.id, assignee_id=persona_a.id, status="completed")
        rule = ProjectAutomationRule(
            project_id=project.id,
            sede_id=sede_a.id,
            name="Reasignación fuera de sede",
            trigger_event="task_completed",
            condition_data={},
            action_type="reassign_task",
            action_data={"assignee_id": str(persona_b.id)},
            is_active=True,
        )
        db_session.add(rule)
        db_session.commit()
        activity_count_before = db_session.query(ProjectActivityLog).filter(
            ProjectActivityLog.project_id == project.id,
        ).count()

        response = client.post(
            f"/api/projects/{project.id}/automations/evaluate",
            json={"trigger_event": "task_completed", "task_id": str(task.id)},
            headers=auth_headers(client, email="adminA@test.com"),
        )

        assert response.status_code == 200, response.text
        assert response.json()[0]["status"] == "failed"
        assert "not found in actor sede" in response.json()[0]["details"]
        db_session.expire_all()
        assert db_session.query(ProjectTask).filter(ProjectTask.id == task.id).one().assignee_id == persona_a.id
        persisted_rule = db_session.query(ProjectAutomationRule).filter(ProjectAutomationRule.id == rule.id).one()
        assert persisted_rule.execution_count == 0
        assert db_session.query(ProjectActivityLog).filter(
            ProjectActivityLog.project_id == project.id,
        ).count() == activity_count_before


    def test_project_editor_can_manage_local_rule_but_not_sede_wide_rule(self, client, db_session):
        from backend.crud.projects import delete_project_automation_rule, update_project_automation_rule
        from backend.models_projects import ProjectAutomationRule
        from backend.schemas.projects import ProjectAutomationRuleUpdate
        from tests.test_projects_rbac import _seed_role_user

        _, _, sede = seed_admin(db_session, email="automationGlobalOwner@test.com")
        project = create_project_factory(db_session, sede_id=sede.id)
        rule = ProjectAutomationRule(
            project_id=None,
            sede_id=sede.id,
            name="Regla compartida de sede",
            trigger_event="task_completed",
            condition_data={},
            action_type="notify_assignee",
            action_data={},
            is_active=True,
        )
        local_rule = ProjectAutomationRule(
            project_id=project.id,
            sede_id=sede.id,
            name="Regla local del proyecto",
            trigger_event="task_completed",
            condition_data={},
            action_type="notify_assignee",
            action_data={},
            is_active=True,
        )
        db_session.add_all([rule, local_rule])
        editor, _, _ = _seed_role_user(db_session, "Editor", "automationGlobalEditor@test.com")
        editor.sede_id = sede.id
        db_session.commit()
        headers = auth_headers(client, email=editor.email)

        list_response = client.get(f"/api/projects/{project.id}/automations", headers=headers)
        assert list_response.status_code == 200, list_response.text
        assert {item["id"] for item in list_response.json()} == {str(rule.id), str(local_rule.id)}

        patch_response = client.patch(
            f"/api/projects/{project.id}/automations/{rule.id}",
            json={"name": "Regla alterada por editor"},
            headers=headers,
        )
        delete_response = client.delete(
            f"/api/projects/{project.id}/automations/{rule.id}",
            headers=headers,
        )
        local_patch_response = client.patch(
            f"/api/projects/{project.id}/automations/{local_rule.id}",
            json={"name": "Regla local actualizada"},
            headers=headers,
        )
        local_delete_response = client.delete(
            f"/api/projects/{project.id}/automations/{local_rule.id}",
            headers=headers,
        )

        assert patch_response.status_code == 404, patch_response.text
        assert delete_response.status_code == 404, delete_response.text
        assert local_patch_response.status_code == 200, local_patch_response.text
        assert local_delete_response.status_code == 200, local_delete_response.text
        assert update_project_automation_rule(
            db_session,
            rule.id,
            ProjectAutomationRuleUpdate(name="CRUD sin manage"),
            user_sede_id=sede.id,
        ) is None
        assert not delete_project_automation_rule(db_session, rule.id, user_sede_id=sede.id)
        db_session.refresh(rule)
        assert rule.name == "Regla compartida de sede"
        assert rule.deleted_at is None
        db_session.refresh(local_rule)
        assert local_rule.name == "Regla local actualizada"
        assert local_rule.deleted_at is not None

    def test_projects_manager_can_manage_sede_wide_automation(self, client, db_session):
        from backend.models_projects import ProjectAutomationRule

        _, _, sede = seed_admin(db_session, email="automationGlobalManager@test.com")
        project = create_project_factory(db_session, sede_id=sede.id)
        rule = ProjectAutomationRule(
            project_id=None,
            sede_id=sede.id,
            name="Regla compartida de sede",
            trigger_event="task_completed",
            condition_data={},
            action_type="notify_assignee",
            action_data={},
            is_active=True,
        )
        db_session.add(rule)
        db_session.commit()
        headers = auth_headers(client, email="automationGlobalManager@test.com")

        patch_response = client.patch(
            f"/api/projects/{project.id}/automations/{rule.id}",
            json={"name": "Regla actualizada por manager"},
            headers=headers,
        )
        delete_response = client.delete(
            f"/api/projects/{project.id}/automations/{rule.id}",
            headers=headers,
        )

        assert patch_response.status_code == 200, patch_response.text
        assert delete_response.status_code == 200, delete_response.text
        db_session.refresh(rule)
        assert rule.name == "Regla actualizada por manager"
        assert rule.deleted_at is not None

    def test_followup_automation_rejects_cross_sede_assignee_without_inserting_task(self, client, db_session):
        from backend.models_projects import ProjectActivityLog, ProjectAutomationRule, ProjectTask

        sede_a, _, _, persona_b = _seed_paired_sedes_with_personas(db_session)
        project = create_project_factory(db_session, sede_id=sede_a.id)
        rule = ProjectAutomationRule(
            project_id=project.id,
            sede_id=sede_a.id,
            name="Seguimiento fuera de sede",
            trigger_event="task_completed",
            condition_data={},
            action_type="create_followup_task",
            action_data={"title": "Seguimiento inválido", "assignee_id": str(persona_b.id)},
            is_active=True,
        )
        db_session.add(rule)
        db_session.commit()
        task_count_before = db_session.query(ProjectTask).filter(
            ProjectTask.project_id == project.id,
            ProjectTask.deleted_at.is_(None),
        ).count()
        activity_count_before = db_session.query(ProjectActivityLog).filter(
            ProjectActivityLog.project_id == project.id,
        ).count()

        response = client.post(
            f"/api/projects/{project.id}/automations/evaluate",
            json={"trigger_event": "task_completed"},
            headers=auth_headers(client, email="adminA@test.com"),
        )

        assert response.status_code == 200, response.text
        assert response.json()[0]["status"] == "failed"
        assert "not found in actor sede" in response.json()[0]["details"]
        db_session.expire_all()
        assert db_session.query(ProjectTask).filter(
            ProjectTask.project_id == project.id,
            ProjectTask.deleted_at.is_(None),
        ).count() == task_count_before
        persisted_rule = db_session.query(ProjectAutomationRule).filter(ProjectAutomationRule.id == rule.id).one()
        assert persisted_rule.execution_count == 0
        assert persisted_rule.last_triggered_at is None
        assert db_session.query(ProjectActivityLog).filter(
            ProjectActivityLog.project_id == project.id,
        ).count() == activity_count_before


class TestProjectExportsSedeScope:
    @pytest.mark.parametrize(
        "export_path",
        [
            "export/executive-data",
            "export/summary-pdf",
            "export/tasks-csv",
            "export/expenses-csv",
        ],
    )
    def test_project_exports_reject_foreign_sede(self, client, db_session, export_path):
        _seed_paired_sedes_with_personas(db_session)
        from backend import models as _models

        sede_b = _models.Sede(nombre="Sede B exports", ciudad="Bogota", es_activa=True)
        db_session.add(sede_b)
        db_session.flush()
        foreign_project = create_project_factory(
            db_session,
            title="Finanzas privadas",
            sede_id=sede_b.id,
        )

        response = client.get(
            f"/api/projects/{foreign_project.id}/{export_path}",
            headers=auth_headers(client, email="adminA@test.com"),
        )

        assert response.status_code == 404, response.text


class TestProjectTeamSedeScope:
    def test_invite_unscoped_persona_returns_404(self, client, db_session):
        s_a, _ = _seed_paired_sedes(db_session)
        unscoped = _models.Persona(
            id=_uuid.uuid4(),
            first_name="Unscoped",
            last_name="Team member",
            email=f"unscoped-team-{_uuid.uuid4().hex[:8]}@example.com",
            sede_id=None,
        )
        db_session.add(unscoped)
        db_session.commit()
        project = create_project_factory(db_session, sede_id=s_a.id)
        headers_a = auth_headers(client, email="adminA@test.com")
        response = client.post(
            f"/api/projects/{project.id}/team",
            json={"persona_id": str(unscoped.id)},
            headers=headers_a,
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Persona no encontrada en esta sede"
        assert (
            db_session.query(_models.ProjectMember)
            .filter(
                _models.ProjectMember.project_id == project.id,
                _models.ProjectMember.persona_id == unscoped.id,
            )
            .first()
            is None
        )


# ── B: CRUD-layer defense-in-depth (the gap!) ────────────────────────────


class TestMultiTenantCRUDDefenseInDepth:
    """The CRUD functions should re-validate scope with actor_user_id."""

    def test_create_project_crud_rejects_none_sede_id(self, db_session):
        """Backend contract: crud.create_project() must reject sede_id=None.

        In current code the function accepts sede_id=None silently, weakening
        Axioma 3 (multi-tenant defense-in-depth). The expected post-fix
        behavior is that the function raises (TypeError, ValueError, or a
        custom exception) so the route layer cannot accidentally create
        cross-tenant UGC.
        """
        import pytest

        from backend import crud
        from backend.schemas.projects import ProjectCreate

        u_a, _, _ = seed_admin(db_session)
        payload = ProjectCreate(title="Backend test")

        with pytest.raises((TypeError, ValueError, AttributeError, RuntimeError)):
            crud.create_project(
                db_session,
                payload,
                owner_persona_id=u_a.id,
                sede_id=None,  # explicit None = no tenant
            )

    def test_get_project_via_crud_applies_sede_scope(self, db_session):
        """Crud layer must return None when querying a project foreign-sede."""
        from backend import crud

        s_a, s_b = _seed_paired_sedes(db_session)
        proj_in_a = create_project_factory(db_session, sede_id=s_a.id)
        found = crud.get_project(db_session, proj_in_a.id, sede_id=s_b.id)
        assert found is None, f"Crud layer leaked cross-sede project: {found!r}"


class TestProjectRiskOwnerSedeScope:
    def test_create_risk_rejects_owner_from_another_sede(self, client, db_session):
        sede_a, _, _, persona_b = _seed_paired_sedes_with_personas(db_session)
        project = create_project_factory(db_session, sede_id=sede_a.id)

        response = client.post(
            f"/api/projects/{project.id}/risks",
            json={"title": "Riesgo con owner cruzado", "owner_id": str(persona_b.id)},
            headers=auth_headers(client, email="adminA@test.com"),
        )

        assert response.status_code == 404, response.text
        assert db_session.query(_models.ProjectRisk).filter_by(project_id=project.id).count() == 0

    def test_update_risk_rejects_owner_from_another_sede_without_mutation(self, client, db_session):
        sede_a, persona_a, _, persona_b = _seed_paired_sedes_with_personas(db_session)
        project = create_project_factory(db_session, sede_id=sede_a.id)
        risk = _models.ProjectRisk(
            project_id=project.id,
            title="Riesgo local",
            owner_id=persona_a.id,
            probability=3,
            impact=3,
            severity_score=9,
            status="active",
        )
        db_session.add(risk)
        db_session.commit()

        response = client.patch(
            f"/api/projects/{project.id}/risks/{risk.id}",
            json={"owner_id": str(persona_b.id)},
            headers=auth_headers(client, email="adminA@test.com"),
        )

        assert response.status_code == 404, response.text
        db_session.refresh(risk)
        assert risk.owner_id == persona_a.id

    def test_risk_owner_can_be_assigned_within_project_sede(self, client, db_session):
        sede_a, persona_a, _, _ = _seed_paired_sedes_with_personas(db_session)
        project = create_project_factory(db_session, sede_id=sede_a.id)

        response = client.post(
            f"/api/projects/{project.id}/risks",
            json={"title": "Riesgo con owner local", "owner_id": str(persona_a.id)},
            headers=auth_headers(client, email="adminA@test.com"),
        )

        assert response.status_code == 201, response.text
        assert response.json()["owner_id"] == str(persona_a.id)

    def test_update_risk_can_clear_optional_owner(self, client, db_session):
        sede_a, persona_a, _, _ = _seed_paired_sedes_with_personas(db_session)
        project = create_project_factory(db_session, sede_id=sede_a.id)
        risk = _models.ProjectRisk(
            project_id=project.id,
            title="Riesgo reasignable",
            owner_id=persona_a.id,
            probability=3,
            impact=3,
            severity_score=9,
            status="active",
        )
        db_session.add(risk)
        db_session.commit()

        response = client.patch(
            f"/api/projects/{project.id}/risks/{risk.id}",
            json={"owner_id": None},
            headers=auth_headers(client, email="adminA@test.com"),
        )

        assert response.status_code == 200, response.text
        assert response.json()["owner_id"] is None
        db_session.refresh(risk)
        assert risk.owner_id is None



    def test_crud_rejects_risk_owner_from_another_sede(self, db_session):
        from backend.crud.projects import create_project_risk
        from backend.schemas.projects import ProjectRiskCreate

        sede_a, _, _, persona_b = _seed_paired_sedes_with_personas(db_session)
        project = create_project_factory(db_session, sede_id=sede_a.id)

        with pytest.raises(ValueError, match="Risk owner not found in project sede"):
            create_project_risk(
                db_session,
                project.id,
                ProjectRiskCreate(title="Riesgo CRUD cruzado", owner_id=persona_b.id),
            )

        assert db_session.query(_models.ProjectRisk).filter_by(project_id=project.id).count() == 0

    def test_crud_update_rejects_risk_owner_from_another_sede(self, db_session):
        from backend.crud.projects import update_project_risk
        from backend.schemas.projects import ProjectRiskUpdate

        sede_a, _, _, persona_b = _seed_paired_sedes_with_personas(db_session)
        project = create_project_factory(db_session, sede_id=sede_a.id)
        risk = _models.ProjectRisk(
            project_id=project.id,
            title="Riesgo sin owner",
            probability=3,
            impact=3,
            severity_score=9,
            status="active",
        )
        db_session.add(risk)
        db_session.commit()

        with pytest.raises(ValueError, match="Risk owner not found in project sede"):
            update_project_risk(
                db_session,
                project.id,
                risk.id,
                ProjectRiskUpdate(owner_id=persona_b.id),
            )

        db_session.refresh(risk)
        assert risk.owner_id is None


# ── C: notify_task_assigned atomicity ────────────────────────────────────


class TestNotifyTaskAssignedAtomicity:
    """The notification side-effect must be one transaction."""

    def test_send_email_failure_does_not_persist_notification(self, client, db_session, monkeypatch):
        """RED: when send_email returns False, NO NotificacionUsuario row."""
        from backend.services import email as email_service
        from backend.services.task_notifications import notify_task_assigned

        _, persona, sede = seed_admin(db_session)
        proj = create_project_factory(db_session, owner_id=persona.id)
        task = create_task_factory(db_session, proj.id, assignee_id=None)

        # Assign a target persona with an email
        target = db_session.query(_models.Persona).filter(_models.Persona.id == _uuid.uuid4()).first()
        if target is None:
            target = _models.Persona(
                id=_uuid.uuid4(),
                first_name="Target",
                last_name="Test",
                email=f"target_{_uuid.uuid4().hex[:8]}@example.com",
            )
            db_session.add(target)
            db_session.flush()
        else:
            target.email = f"target_{_uuid.uuid4().hex[:8]}@example.com"
            db_session.flush()
        target.email = "target@example.com"  # ensure email present
        db_session.flush()

        def _always_fail(*a, **kw):
            return False

        monkeypatch.setattr(email_service, "send_email", _always_fail)

        # Snapshot counts BEFORE the call. Both models live on backend.models
        # (single source of truth; CommunicationLog is not on
        # models_operational — that import would silently fail and mask the
        # assertion).
        from backend.models import CommunicationLog as _CL
        from backend.models import NotificacionUsuario as _Notif

        pre_notif = db_session.query(_Notif).count()
        pre_comm = db_session.query(_CL).count()

        # Trigger notify directly
        notify_task_assigned(
            db_session,
            task=task,
            project=proj,
            assigned_by_user_id=persona.id,
        )

        # Atomic invariant: send_email returned False → outcome MUST be
        # 'email_failed'. Pre-fix: NotificacionUsuario is committed first
        # (orphans), then email fails, leaving inconsistent state.
        # Post-fix: either zero notifications (rollback) OR a single
        # notification paired with a CommunicationLog(outcome=email_failed).
        post_notif = db_session.query(_Notif).count()
        post_comm = db_session.query(_CL).count()
        delta_notif = post_notif - pre_notif
        delta_comm = post_comm - pre_comm

        # At most one notification per call
        assert delta_notif in (0, 1), f"More than one NotificacionUsuario in a single assign call: delta={delta_notif}"
        # Audit row must reflect the email failure
        assert delta_comm >= 1, "send_email failed but no CommunicationLog audit row was written"
        newest_cl = (
            db_session.query(_CL).filter(_CL.campaign_name == "Asignación de tarea").order_by(_CL.id.desc()).first()
        )
        assert newest_cl is not None, "CommunicationLog with campaign='Asignación de tarea' not found"
        assert newest_cl.outcome == "email_failed", (
            f"Audit outcome must be 'email_failed' (send_email was forced to fail), got {newest_cl.outcome!r}"
        )
        # The pivotal contract: if send_email failed, NO NotificacionUsuario
        # row should remain. Any notification row in the email_failed path
        # signals the broken 2-commit pattern.
        if delta_notif == 1 and newest_cl.outcome == "email_failed":
            pytest.fail(
                "Atomicity violated: send_email failed but a NotificacionUsuario "
                "row was already committed. The service must rollback the entire "
                "transaction on email failure rather than persisting half-state."
            )


# ── D: Axm 3 Basic mutations respect deletion boundary ────────────────────


class TestSoftDeleteRespectsTenantScope:
    """A soft-deleted project must NOT be visible cross-sede either."""

    def test_soft_deleted_project_hidden_from_listing(self, client, db_session):
        s_a, _ = _seed_paired_sedes(db_session)
        proj = create_project_factory(db_session, sede_id=s_a.id)
        create_task_factory(db_session, proj.id, title="Dead task")

        # Soft delete directly (the route layer does this on DELETE).
        # Use Python datetime instead of SQL NOW() so the test is portable
        # between Postgres test DBs and SQLite dev DBs (which has no NOW() builtin).
        proj.deleted_at = datetime.now(timezone.utc)
        db_session.commit()

        # Use the API of the admin whose sede matches sede_A
        # (adminA@test.com was seeded with their own sede; we trust
        # that the env was created in the same seed_admin batch above).
        hdr_a = auth_headers(client, email="adminA@test.com")
        listed = client.get("/api/projects", headers=hdr_a).json()
        ids = [p["id"] for p in listed]
        assert str(proj.id) not in ids, "Listing includes soft-deleted project"


class TestProjectCreationRequiresActorSede:
    """Project UGC must never be assigned to an inferred/first tenant."""

    def test_create_project_without_actor_sede_returns_409_without_persisting(
        self, client, db_session, monkeypatch
    ):
        import backend.api.projects as projects_api

        seed_admin(db_session, email="project-no-sede-create@test.com")
        monkeypatch.setattr(projects_api, "get_user_sede_id", lambda _db, _user: None)
        before = db_session.query(_models.Project).count()

        response = client.post(
            "/api/projects",
            json={"title": "No debe quedar sin sede"},
            headers=auth_headers(client, email="project-no-sede-create@test.com"),
        )

        assert response.status_code == 409, response.text
        assert db_session.query(_models.Project).count() == before


    @pytest.mark.parametrize(
        "path_template",
        [
            "/api/projects/from-template/{template_id}",
            "/api/projects/templates/{template_id}/instantiate",
        ],
    )
    def test_instantiate_template_without_actor_sede_returns_409_without_persisting(
        self, client, db_session, monkeypatch, path_template
    ):
        import backend.api.projects as projects_api
        from backend.models_projects import ProjectTemplate

        _, persona, sede = seed_admin(db_session, email="project-no-sede-template@test.com")
        db_session.add(
            _models.ChurchLocation(
                id=sede.id,
                name="Ubicación de referencia no confiable",
                is_active=True,
            )
        )
        template = ProjectTemplate(
            name="Plantilla pública",
            category="general",
            default_budget=0,
            structure={"phases": [], "tasks": []},
            created_by=persona.id,
            is_public=True,
            sede_id=sede.id,
        )
        db_session.add(template)
        db_session.commit()
        monkeypatch.setattr(projects_api, "get_user_sede_id", lambda _db, _user: None)
        before = db_session.query(_models.Project).count()

        response = client.post(
            path_template.format(template_id=template.id),
            json={"title": "No heredar una sede arbitraria"},
            headers=auth_headers(client, email="project-no-sede-template@test.com"),
        )

        assert response.status_code == 409, response.text
        assert db_session.query(_models.Project).count() == before


class TestProjectSedeDeletePolicy:
    @pytest.mark.parametrize(
        "model_name",
        ["Project", "ProjectTemplate", "ProjectAutomationRule", "ProjectIndicator", "ProjectFile"],
    )
    def test_tenant_scope_sede_foreign_key_restricts_hard_delete(self, model_name):
        model = getattr(_models, model_name)
        sede_foreign_keys = [
            foreign_key
            for foreign_key in model.__table__.foreign_keys
            if foreign_key.parent.name == "sede_id"
            and foreign_key.column.table.name == "sedes"
        ]

        assert len(sede_foreign_keys) == 1
        assert sede_foreign_keys[0].ondelete == "RESTRICT"

    def test_hard_delete_sede_is_rejected_when_private_project_records_exist(self, db_session):
        from sqlalchemy import delete, text
        from sqlalchemy.exc import IntegrityError

        db_session.commit()
        connection = db_session.connection()
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        assert connection.execute(text("PRAGMA foreign_keys")).scalar_one() == 1

        _, persona, sede = seed_admin(db_session, email="project-sede-fk-restrict@test.com")
        _, _, other_sede = seed_admin(db_session, email="project-sede-fk-other@test.com")
        project = _models.Project(title="Proyecto protegido", owner_id=persona.id, sede_id=sede.id)
        db_session.add_all(
            [
                project,
                _models.ProjectTemplate(
                    name="Plantilla privada",
                    structure={},
                    is_public=False,
                    sede_id=sede.id,
                ),
                _models.ProjectAutomationRule(
                    name="Regla privada",
                    trigger_event="manual",
                    action_type="notify_assignee",
                    sede_id=sede.id,
                ),
            ]
        )
        db_session.flush()
        db_session.add_all(
            [
                _models.ProjectIndicator(
                    project_id=project.id,
                    name="Indicador protegido",
                    sede_id=sede.id,
                ),
                _models.ProjectFile(
                    project_id=project.id,
                    name="Archivo protegido",
                    file_url="https://example.test/protected.pdf",
                    sede_id=sede.id,
                ),
            ]
        )
        db_session.commit()

        from backend.crud.projects import get_project_templates

        visible_to_other_sede = get_project_templates(db_session, user_sede_id=other_sede.id)
        assert all(template.name != "Plantilla privada" for template in visible_to_other_sede)

        with pytest.raises(IntegrityError):
            db_session.execute(delete(_models.Sede).where(_models.Sede.id == sede.id))
            db_session.commit()

        db_session.rollback()
        assert db_session.query(_models.ProjectTemplate).filter_by(name="Plantilla privada").one().sede_id == sede.id
        db_session.connection().exec_driver_sql("PRAGMA foreign_keys=OFF")


class TestProjectTimeLogPersonaDeletePolicy:
    def test_time_log_persona_fk_is_required_and_restrictive(self):
        time_log = _models.ProjectTimeLog.__table__
        persona_column = time_log.c.persona_id
        persona_fk = next(
            foreign_key
            for foreign_key in time_log.foreign_keys
            if foreign_key.parent.name == "persona_id"
            and foreign_key.column.table.name == "personas"
        )

        assert persona_column.nullable is False
        assert persona_fk.ondelete == "RESTRICT"

    def test_hard_delete_persona_is_rejected_when_project_time_logs_exist(self, db_session):
        from sqlalchemy import delete, text
        from sqlalchemy.exc import IntegrityError

        db_session.commit()
        connection = db_session.connection()
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        assert connection.execute(text("PRAGMA foreign_keys")).scalar_one() == 1

        _, _, sede = seed_admin(db_session, email="project-log-persona-delete@test.com")
        persona = _models.Persona(first_name="Persona", last_name="ConHoras", sede_id=sede.id)
        project = _models.Project(title="Proyecto con horas", sede_id=sede.id)
        db_session.add_all([persona, project])
        db_session.flush()
        time_log = _models.ProjectTimeLog(
            project_id=project.id,
            persona_id=persona.id,
            hours=2,
        )
        db_session.add(time_log)
        db_session.commit()

        with pytest.raises(IntegrityError):
            db_session.execute(delete(_models.Persona).where(_models.Persona.id == persona.id))
            db_session.commit()

        db_session.rollback()
        saved_log = db_session.query(_models.ProjectTimeLog).filter_by(id=time_log.id).one()
        assert saved_log.persona_id == persona.id
        db_session.connection().exec_driver_sql("PRAGMA foreign_keys=OFF")
