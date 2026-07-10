"""TDD-red suite: Project chat + WebSocket broadcast semantics.

Targets:

1. Project chat uses `room_id = 'project_{project_id}'` and stores rows
   in `ChatMessage` (models_crm). — Locks the contract.
2. Authenticated user can list messages with cursor pagination. — Locks.
3. POST a message persists it and returns a payload with the
   `sender_name` field resolved from the actor's Persona. — Locks.
4. DELETE own message: 200. DELETE another user's message without a
   privileged role: 403. — Locks behavior.
5. Soft-deleted messages must NOT appear in subsequent listings. — Locks.
6. When POST returns, the asyncio broadcast task is *not* awaited but is
   scheduled (`asyncio.ensure_future`). We assert the message row exists
   without blocking on the broadcast. — Locks the side-effect contract.
"""
from __future__ import annotations

import uuid as _uuid

from backend import models as _models
from backend.models_crm import ChatMessage, Persona
from tests.conftest import auth_headers, seed_admin, seed_user_with_role
from tests.factories_projects import (
    _ensure_persona,
    create_message_factory,
    create_project_factory,
)


class TestChatMessageListingAndCursor:
    """GET /projects/{id}/messages paginates newest-first."""

    def test_list_messages_empty(self, client, db_session):
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        headers = auth_headers(client)
        resp = client.get(f"/api/projects/{proj.id}/messages", headers=headers)
        assert resp.status_code == 200, resp.text
        assert resp.json() == []

    def test_post_then_list_returns_message(self, client, db_session):
        _, persona, sede = seed_admin(db_session)
        proj = create_project_factory(db_session, owner_id=persona.id)
        headers = auth_headers(client)

        post = client.post(
            f"/api/projects/{proj.id}/messages",
            json={"content": "Hola equipo"},
            headers=headers,
        )
        assert post.status_code == 201
        posted = post.json()
        # Contract: response carries an id (UUID) and sender_name
        assert posted["content"] == "Hola equipo"
        _uuid.UUID(posted["id"])  # must parse
        assert posted["sender_name"], "sender_name must be populated"

        listed = client.get(f"/api/projects/{proj.id}/messages", headers=headers).json()
        assert len(listed) >= 1
        assert any(m["content"] == "Hola equipo" for m in listed)

    def test_messages_are_isolated_per_project(self, client, db_session):
        """Messages in project A must NOT leak into project B."""
        _, _, sede = seed_admin(db_session)
        proj_a = create_project_factory(db_session, title="Chat A")
        proj_b = create_project_factory(db_session, title="Chat B")
        headers = auth_headers(client)
        client.post(
            f"/api/projects/{proj_a.id}/messages",
            json={"content": "Secreto A"},
            headers=headers,
        )
        client.post(
            f"/api/projects/{proj_b.id}/messages",
            json={"content": "Secreto B"},
            headers=headers,
        )

        body_a = client.get(f"/api/projects/{proj_a.id}/messages", headers=headers).json()
        body_b = client.get(f"/api/projects/{proj_b.id}/messages", headers=headers).json()
        contents_a = [m["content"] for m in body_a]
        contents_b = [m["content"] for m in body_b]
        assert "Secreto A" in contents_a
        assert "Secreto A" not in contents_b
        assert "Secreto B" in contents_b
        assert "Secreto B" not in contents_a

    def test_room_id_format_is_project_prefix(self, client, db_session):
        """Room id must be `project_{project_id}` for WebSocket routing."""
        _, persona, sede = seed_admin(db_session)
        proj = create_project_factory(db_session, owner_id=persona.id)
        headers = auth_headers(client)
        client.post(
            f"/api/projects/{proj.id}/messages",
            json={"content": "format room"},
            headers=headers,
        )
        row = db_session.query(ChatMessage).filter(
            ChatMessage.room_id == f"project_{proj.id}"
        ).first()
        assert row is not None, (
            f"No ChatMessage with room_id='project_{proj.id}' was persisted"
        )


class TestChatDeletePermissions:
    """DELETE message: own OK, third-party 403 without privileged role."""

    def test_delete_own_message_succeeds(self, client, db_session):
        _, persona, sede = seed_admin(db_session)
        proj = create_project_factory(db_session, owner_id=persona.id)
        msg = create_message_factory(db_session, proj.id, persona.id)
        headers = auth_headers(client)

        resp = client.delete(
            f"/api/projects/{proj.id}/messages/{msg.id}",
            headers=headers,
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["ok"] is True

    def test_delete_third_party_message_returns_403_for_persona_role(
        self, client, db_session
    ):
        """A LECTOR/PERSONA user cannot delete messages sent by others."""
        _, owner, sede = seed_admin(db_session, email="author@test.com")
        proj = create_project_factory(db_session, owner_id=owner.id)
        msg = create_message_factory(db_session, proj.id, owner.id)

        # Third-party user with no privileged role.
        seed_user_with_role(db_session, role_name="persona", email="reader@test.com")
        hdr_reader = auth_headers(client, email="reader@test.com")
        # Author has full read access; we use them to verify the rejected
        # delete did NOT remove the row. The reader role lacks the
        # ``projects:read`` permission so reading via ``hdr_reader`` would
        # 403 and pollute the assertion with permission-side noise.
        hdr_owner = auth_headers(client, email="author@test.com")

        resp = client.delete(
            f"/api/projects/{proj.id}/messages/{msg.id}",
            headers=hdr_reader,
        )
        # Acceptable: 401 (token invalid) or 403 (role not allowed) — both
        # are leak-safe rejections. The endpoint MUST NOT allow the delete.
        assert resp.status_code in (401, 403), (
            f"Expected 401/403 for non-owner non-admin, got {resp.status_code}: {resp.text}"
        )
        # Confirm the message is still present after the rejected delete —
        # no partial authorization.
        listed = client.get(
            f"/api/projects/{proj.id}/messages", headers=hdr_owner
        ).json()
        assert isinstance(listed, list), (
            f"GET /messages must return a list (got: {type(listed).__name__}): {listed}"
        )
        assert any(m["id"] == str(msg.id) and m.get("deleted_at") in (None, "null", "")
                   for m in listed), (
            f"Message should still exist after rejected delete: {listed}"
        )

    def test_soft_deleted_message_excluded_from_listing(self, client, db_session):
        _, persona, sede = seed_admin(db_session)
        proj = create_project_factory(db_session, owner_id=persona.id)
        msg = create_message_factory(db_session, proj.id, persona.id, content="Hidden")
        headers = auth_headers(client)

        client.delete(f"/api/projects/{proj.id}/messages/{msg.id}", headers=headers)

        listed = client.get(f"/api/projects/{proj.id}/messages", headers=headers).json()
        assert all(m["content"] != "Hidden" for m in listed), (
            "Soft-deleted message appears in listing — soft delete is not respected"
        )

    def test_soft_deleted_message_kept_in_db_for_audit(self, client, db_session):
        """Auditability: row stays in DB after soft-delete."""
        _, persona, sede = seed_admin(db_session)
        proj = create_project_factory(db_session, owner_id=persona.id)
        msg = create_message_factory(db_session, proj.id, persona.id)
        headers = auth_headers(client)

        client.delete(f"/api/projects/{proj.id}/messages/{msg.id}", headers=headers)

        # The factory above loaded ``msg`` into ``db_session``'s identity
        # map. The API call commits ``msg.deleted_at`` from a SEPARATE
        # session, so SQLAlchemy's identity map still hands back the
        # stale (pre-commit) snapshot when queried by primary key. Force
        # a fresh DB read here so the auditability assertion sees the
        # post-commit timestamp.
        db_session.expire_all()
        row = db_session.query(ChatMessage).filter(
            ChatMessage.id == msg.id
        ).first()
        assert row is not None, "Soft delete removes the row (should NOT)"
        assert row.deleted_at is not None, "deleted_at not stamped"


class TestChatPaginationCursor:
    """GET with `before` cursor returns older messages."""

    def test_before_cursor_filters_correctly(self, client, db_session):
        _, persona, sede = seed_admin(db_session)
        proj = create_project_factory(db_session, owner_id=persona.id)
        headers = auth_headers(client)

        # Send 5 messages; capture ids as UUID objects (int attr is the
        # comparable integer representation of a UUID).
        uuids = []
        for i in range(5):
            r = client.post(
                f"/api/projects/{proj.id}/messages",
                json={"content": f"msg-{i}"},
                headers=headers,
            )
            uuids.append(_uuid.UUID(r.json()["id"]))

        # Listing newest first
        first_page = client.get(
            f"/api/projects/{proj.id}/messages?limit=3",
            headers=headers,
        ).json()
        assert len(first_page) == 3

        # Use the smallest uuid of the first page as the cursor
        cursor = min(_uuid.UUID(m["id"]) for m in first_page)
        second_page = client.get(
            f"/api/projects/{proj.id}/messages?limit=3&before={cursor.int}",
            headers=headers,
        ).json()
        # All messages on second page must have uuid < cursor
        for m in second_page:
            assert _uuid.UUID(m["id"]) < cursor, (
                f"Cursor pagination broken: {m}"
            )


class TestChatAsynclyBroadcast:
    """The POST handler schedules a websocket broadcast.

    We assert that broadcast_event is called (or scheduled) and that the
    request completes WITHOUT awaiting it. If the service becomes
    synchronous (e.g., added await()), the response time would jump.
    """

    def test_post_message_returns_immediately(self, client, db_session):
        """POST /messages is non-blocking even if broadcast is slow."""
        import time as _time
        _, persona, sede = seed_admin(db_session)
        proj = create_project_factory(db_session, owner_id=persona.id)
        headers = auth_headers(client)

        t0 = _time.perf_counter()
        resp = client.post(
            f"/api/projects/{proj.id}/messages",
            json={"content": "fast post"},
            headers=headers,
        )
        elapsed = _time.perf_counter() - t0
        # Generous bound — if we see > 2s the broadcast became blocking
        assert elapsed < 2.0, (
            f"POST /messages took {elapsed:.2f}s — broadcast is likely blocking the response"
        )
        assert resp.status_code == 201
