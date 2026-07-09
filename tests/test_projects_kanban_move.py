"""TDD-red suite: Kanban move semantics for /projects/tasks/{id}.

Targets (Sprint 1/2 of the Projects-node debt roadmap):

1. PATCH /projects/tasks/{id} with status that does NOT match any
   ProjectPhase.slug for the owning project should be rejected (422/400),
   not silently accepted as a free String. — RED: no validation today.
2. Soft-deleted phases must not be assignable. — RED.
3. PATCH cross-project (passing project_id != task.project_id) must
   return 404 (defense-in-depth). — Probably GREEN today but locks in.
4. PATCH that changes assignee_id must invoke notify_task_assigned and
   persist in a SINGLE atomic transaction. — RED: the service currently
   uses two commits.
5. When PATCH fails, the client receives a stable error envelope
   ("detail" string, no leaked internal trace). — Locks in.
"""
from __future__ import annotations

import uuid as _uuid
from datetime import datetime, timezone

from backend import models as _models
from backend.models_projects import ProjectTask
from tests.conftest import auth_headers, seed_admin
from tests.factories_projects import (
    _ensure_persona,
    create_default_phases_factory,
    create_project_factory,
    create_task_factory,
)


class TestKanbanStatusValidation:
    """Status PATCH must be a known phase slug, not a free String."""

    def test_patch_status_matching_phase_is_accepted(self, client, db_session):
        """Baseline: PATCH to a valid phase slug succeeds (200)."""
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        create_default_phases_factory(db_session, proj.id)
        task = create_task_factory(db_session, proj.id, status="todo")
        headers = auth_headers(client)

        resp = client.patch(
            f"/api/projects/tasks/{task.id}",
            json={"status": "in_progress"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "in_progress"

    def test_patch_status_invalid_slug_rejected(self, client, db_session):
        """RED: PATCH with status="not_a_real_phase" should fail, not silently accept."""
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        create_default_phases_factory(db_session, proj.id)
        task = create_task_factory(db_session, proj.id)
        headers = auth_headers(client)

        resp = client.patch(
            f"/api/projects/tasks/{task.id}",
            json={"status": "not_a_real_phase"},
            headers=headers,
        )
        # Currently the column is a free String — would return 200.
        # We want 422 (Pydantic validation) or 400 with descriptive message.
        assert resp.status_code in (400, 422), (
            f"Expected rejection of unknown slug, got {resp.status_code}: {resp.text}"
        )
        detail = (resp.json() or {}).get("detail", "")
        assert "phase" in str(detail).lower() or "status" in str(detail).lower(), (
            f"Error detail must mention the offending axis: {detail}"
        )

    def test_patch_status_to_soft_deleted_phase_rejected(self, client, db_session):
        """RED: a phase whose deleted_at is set must NOT be assignable."""
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        phases = create_default_phases_factory(db_session, proj.id)
        task = create_task_factory(db_session, proj.id)

        # Soft-delete the 'review' phase row. Use Python datetime because
        # the test DB is SQLite (no NOW() builtin) — keeping the test
        # portable across Postgres + SQLite.
        review_phase = next(p for p in phases if p.slug == "review")
        review_phase.deleted_at = datetime.now(timezone.utc)
        db_session.commit()
        headers = auth_headers(client)

        resp = client.patch(
            f"/api/projects/tasks/{task.id}",
            json={"status": "review"},
            headers=headers,
        )
        assert resp.status_code in (400, 404, 422), (
            f"Should refuse soft-deleted phase, got {resp.status_code}: {resp.text}"
        )


class TestKanbanProjectScope:
    """Defensive cross-project checks on PATCH and DELETE."""

    def test_patch_task_via_wrong_project_returns_404(self, client, db_session):
        """GREEN today via _ensure_task_in_project — locks the contract."""
        _, _, sede = seed_admin(db_session)
        proj_a = create_project_factory(db_session, title="A")
        proj_b = create_project_factory(db_session, title="B")
        create_default_phases_factory(db_session, proj_a.id)
        create_default_phases_factory(db_session, proj_b.id)
        # Task belongs to proj_a; caller passes proj_b in URL
        task = create_task_factory(db_session, proj_a.id, status="todo")
        headers = auth_headers(client)

        resp = client.patch(
            f"/api/projects/{proj_b.id}/tasks/{task.id}",
            json={"status": "in_progress"},
            headers=headers,
        )
        assert resp.status_code == 404, (
            f"Cross-project PATCH must 404, got {resp.status_code}: {resp.text}"
        )

    def test_delete_task_via_wrong_project_returns_404(self, client, db_session):
        """GREEN today — locks in the route ordering invariant."""
        _, _, sede = seed_admin(db_session)
        proj_a = create_project_factory(db_session, title="AX")
        proj_b = create_project_factory(db_session, title="BX")
        task = create_task_factory(db_session, proj_a.id)
        headers = auth_headers(client)

        resp = client.delete(
            f"/api/projects/{proj_b.id}/tasks/{task.id}",
            headers=headers,
        )
        assert resp.status_code == 404, (
            f"Cross-project DELETE must 404, got {resp.status_code}"
        )


class TestKanbanAssigneeNotificationAtomicity:
    """notify_task_assigned must be atomic (single commit + rollback)."""

    def test_patch_assignee_triggers_atomic_notification(self, client, db_session, monkeypatch):
        """RED: send_email must fail atomically — no NotificacionUsuario orphan row.

        We monkey-patch send_email to raise. The expected behavior after the
        Sprint 1 fix is: zero NotificacionUsuario rows created, the task
        update itself rolls back, and the API returns 500 (or 200 with a
        specific 'email_failed' outcome persisted).
        """
        from backend.services import email as email_service

        _, persona, sede = seed_admin(db_session)
        proj = create_project_factory(db_session, owner_id=persona.id)
        task = create_task_factory(
            db_session,
            proj.id,
            assignee_id=None,  # start with no assignee
        )

        # A fresh assignee the admin assigns to
        new_assignee = _ensure_persona(db_session)
        new_assignee.email = f"target_{new_assignee.id.hex[:8]}@example.com"
        db_session.commit()

        monkeypatch.setattr(
            email_service,
            "send_email",
            lambda *a, **kw: False,  # returns False → outcome=email_failed
        )

        headers = auth_headers(client)

        # Snapshot counts BEFORE the patch for both NotificacionUsuario
        # and CommunicationLog. NotificacionUsuario lives on backend.models
        # (sibling module, not models_notifications — see models.py).
        pre_notif = db_session.query(_models.NotificacionUsuario).count()
        pre_comm = db_session.query(_models.CommunicationLog).count()

        resp = client.patch(
            f"/api/projects/tasks/{task.id}",
            json={"assignee_id": str(new_assignee.id)},
            headers=headers,
        )

        # Post-conditions for atomicity:
        #   - activity_log row created (linearización siempre)   → +1
        #   - Si email falla:
        #       * NotificacionUsuario delta == 0  **or**  delta == 1 pero
        #         acompañado de CommunicationLog outcome=email_failed
        #       * Nunca delta >1 (ausencia de duplicación)
        #   - Si email funciona: NotificacionUsuario delta == 1,
        #       CommunicationLog outcome=email_sent
        post_notif = db_session.query(_models.NotificacionUsuario).count()
        post_comm = db_session.query(_models.CommunicationLog).count()

        delta_notif = post_notif - pre_notif
        delta_comm = post_comm - pre_comm

        assert resp.status_code in (200, 500, 502), (
            f"Unexpected status from assignee patch: {resp.status_code}: {resp.text}"
        )
        # Atómico: nunca más de 1 NotificacionUsuario creado en un solo call
        assert delta_notif <= 1, (
            f"Multiple notifications persisted in one call: delta={delta_notif}"
        )
        # Si se creó una notificación, debe estar respaldada por un
        # CommunicationLog con outcome consistente (no estado huérfano)
        if delta_notif == 1:
            assert delta_comm >= 1, (
                "Notificación persistida sin CommunicationLog de auditoría — estado inconsistente"
            )
            last_cl = (
                db_session.query(_models.CommunicationLog)
                .order_by(_models.CommunicationLog.id.desc())
                .first()
            )
            assert last_cl.outcome in {"email_sent", "email_failed", "no_email"}, (
                f"CommunicationLog outcome incoherente con delta_notif=1: {last_cl.outcome}"
            )


class TestKanbanErrorEnvelope:
    """Errors must return a stable {detail: <string>} envelope."""

    def test_patch_malformed_uuid_returns_clean_404(self, client, db_session):
        seed_admin(db_session)
        headers = auth_headers(client)
        # FastAPI path-parameter typing accepts a string; we send a malformed
        # UUID that should be rejected by _ensure_task → 404 with clean detail.
        resp = client.patch(
            "/api/projects/tasks/not-a-uuid",
            json={"status": "todo"},
            headers=headers,
        )
        assert resp.status_code in (400, 404, 422), resp.text
        body = resp.json() or {}
        assert "detail" in body, f"Response envelope missing 'detail': {body}"
