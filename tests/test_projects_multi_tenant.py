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

from sqlalchemy import text as _sql_text

import pytest

from backend import models as _models
from backend.models_crm import Persona
from backend.models_projects import Project
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
        assert resp.status_code == 404, (
            f"Cross-sede GET must be 404 (leak-proof), got {resp.status_code}: {resp.text}"
        )

    def test_patch_project_cross_sede_returns_404(self, client, db_session):
        s_a, _ = _seed_paired_sedes(db_session)
        proj_in_a = create_project_factory(db_session, sede_id=s_a.id)
        hdr_b = auth_headers(client, email="adminB@test.com")
        resp = client.patch(
            f"/api/projects/{proj_in_a.id}",
            json={"title": "Hacked from B"},
            headers=hdr_b,
        )
        assert resp.status_code == 404, (
            f"Cross-sede PATCH must be 404, got {resp.status_code}: {resp.text}"
        )

    def test_delete_project_cross_sede_returns_404(self, client, db_session):
        s_a, _ = _seed_paired_sedes(db_session)
        proj_in_a = create_project_factory(db_session, sede_id=s_a.id)
        hdr_b = auth_headers(client, email="adminB@test.com")
        resp = client.delete(f"/api/projects/{proj_in_a.id}", headers=hdr_b)
        assert resp.status_code == 404

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
        assert found is None, (
            f"Crud layer leaked cross-sede project: {found!r}"
        )


# ── C: notify_task_assigned atomicity ────────────────────────────────────


class TestNotifyTaskAssignedAtomicity:
    """The notification side-effect must be one transaction."""

    def test_send_email_failure_does_not_persist_notification(
        self, client, db_session, monkeypatch
    ):
        """RED: when send_email returns False, NO NotificacionUsuario row."""
        from backend.services import email as email_service
        from backend.services.task_notifications import notify_task_assigned

        _, persona, sede = seed_admin(db_session)
        proj = create_project_factory(db_session, owner_id=persona.id)
        task = create_task_factory(db_session, proj.id, assignee_id=None)

        # Assign a target persona with an email
        target = db_session.query(_models.Persona).filter(
            _models.Persona.id == _uuid.uuid4()
        ).first()
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
        from backend.models import NotificacionUsuario as _Notif
        from backend.models import CommunicationLog as _CL

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
        assert delta_notif in (0, 1), (
            f"More than one NotificacionUsuario in a single assign call: delta={delta_notif}"
        )
        # Audit row must reflect the email failure
        assert delta_comm >= 1, (
            f"send_email failed but no CommunicationLog audit row was written"
        )
        newest_cl = (
            db_session.query(_CL)
            .filter(_CL.campaign_name == "Asignación de tarea")
            .order_by(_CL.id.desc())
            .first()
        )
        assert newest_cl is not None, (
            "CommunicationLog with campaign='Asignación de tarea' not found"
        )
        assert newest_cl.outcome == "email_failed", (
            f"Audit outcome must be 'email_failed' (send_email was forced to fail), "
            f"got {newest_cl.outcome!r}"
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
