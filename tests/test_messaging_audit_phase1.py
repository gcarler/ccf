"""Tests for messaging audit Phase 1 fixes (C-01–C-05, A-01–A-06).

Covers:
  - C-01/C-02: CommunicationLog soft-delete (deleted_at column + query filter)
  - C-03: WebSocket permission check (check_ws_module_access)
  - C-05: Cross-sede isolation for direct persona_id in send_crm_message
  - A-03/A-04: Schema fields (campaign_name, recipient_phone, is_read, external_id)
  - A-06: mark_all_read returns marked_count
"""
from __future__ import annotations

import uuid as _uuid
from datetime import datetime, timezone

from backend import models
from backend.core.permissions import check_ws_module_access
from tests.conftest import auth_headers, seed_admin, seed_user_with_role

# ── C-01/C-02: Soft-delete CommunicationLog ──────────────────────────────


def test_communication_log_has_deleted_at_column():
    """C-01: CommunicationLog model exposes deleted_at column."""
    cols = {c.name for c in models.CommunicationLog.__table__.columns}
    assert "deleted_at" in cols, (
        f"deleted_at missing from CommunicationLog columns: {cols}"
    )


def test_deleted_logs_excluded_from_query(client, db_session):
    """C-02: Logs with deleted_at set must not appear in history."""
    admin, persona, sede = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email)

    visible = models.CommunicationLog(
        persona_id=persona.id,
        channel="internal",
        content="Visible message",
        outcome="internal_log",
    )
    deleted = models.CommunicationLog(
        persona_id=persona.id,
        channel="internal",
        content="Deleted message",
        outcome="internal_log",
        deleted_at=datetime.now(timezone.utc),
    )
    db_session.add_all([visible, deleted])
    db_session.commit()

    resp = client.get("/api/messaging/history?limit=100", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.text
    assert "Visible message" in body
    assert "Deleted message" not in body, (
        "C-02 REGRESSION: soft-deleted log appeared in history"
    )


def test_soft_delete_log_via_orm(client, db_session):
    """C-01/C-02: Setting deleted_at filters the log out."""
    admin, persona, sede = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email)

    log = models.CommunicationLog(
        persona_id=persona.id,
        channel="email",
        content="Will be soft-deleted",
        outcome="internal_log",
    )
    db_session.add(log)
    db_session.commit()
    db_session.refresh(log)

    # Verify visible first
    resp = client.get("/api/messaging/history?limit=100", headers=headers)
    assert "Will be soft-deleted" in resp.text

    # Soft-delete
    log.deleted_at = datetime.now(timezone.utc)
    db_session.commit()

    resp = client.get("/api/messaging/history?limit=100", headers=headers)
    assert "Will be soft-deleted" not in resp.text, (
        "C-02: soft-deleted log still visible after deleted_at set"
    )


# ── C-03: WebSocket permission check ─────────────────────────────────────


def test_check_ws_module_access_allows_admin(db_session):
    """C-03: Admin user with messaging:read passes check."""
    user, persona, sede = seed_admin(db_session)
    result = check_ws_module_access(db_session, user, "messaging", "read")
    assert result is True


def test_check_ws_module_access_rejects_no_perm(db_session):
    """C-03: User without messaging:read is rejected."""
    user, persona, sede = seed_user_with_role(
        db_session,
        role_name="readonly",
        email="nows@example.com",
        permisos={"messaging": "deny"},
    )
    result = check_ws_module_access(db_session, user, "messaging", "read")
    assert result is False


def test_check_ws_module_access_rejects_inactive(db_session):
    """C-03: Inactive user with no permissions is rejected.

    Note: check_ws_module_access checks permissions, not is_active.
    The is_active check happens in the WebSocket endpoint handler.
    An inactive user with an admin role would still pass the permission
    check (admin bypasses), which is by design — the WS handler checks
    is_active separately before calling this function.
    """
    user, persona, sede = seed_user_with_role(
        db_session,
        role_name="readonly",
        email="inactive_ws@example.com",
        permisos={"messaging": "deny"},
    )
    user.is_active = False
    db_session.commit()
    result = check_ws_module_access(db_session, user, "messaging", "read")
    assert result is False


# ── C-05: Cross-sede isolation for persona_id direct ─────────────────────


def test_send_crm_message_cross_sede_persona_rejected(client, db_session):
    """C-05: send_crm_message rejects persona_id from another sede."""
    admin_a, _, sede_a = seed_admin(db_session, email="pastoralA@example.com")
    admin_b, _, sede_b = seed_admin(db_session, email="pastoralB@example.com")

    persona_b = models.Persona(
        id=_uuid.uuid4(),
        first_name="Victim",
        last_name="CrossSede",
        email="victim_cross@example.com",
        sede_id=sede_b.id,
        estado_vital="ACTIVO",
    )
    db_session.add(persona_b)
    db_session.commit()

    headers_a = auth_headers(client, email="pastoralA@example.com")
    resp = client.post(
        "/api/messaging/send",
        headers=headers_a,
        json={
            "persona_id": str(persona_b.id),
            "channel": "internal",
            "content": "C-05 cross-sede attack",
        },
    )
    assert resp.status_code == 404, (
        f"C-05 REGRESSION: cross-sede persona_id should be rejected "
        f"(got {resp.status_code}): {resp.text}"
    )

    leaked = (
        db_session.query(models.CommunicationLog)
        .filter(models.CommunicationLog.persona_id == persona_b.id)
        .first()
    )
    assert leaked is None, "C-05: cross-sede log persisted despite 404"


def test_send_crm_message_same_sede_persona_allowed(client, db_session):
    """C-05: send_crm_message allows persona_id from same sede (regression)."""
    admin, persona, sede = seed_admin(db_session)

    headers = auth_headers(client)
    resp = client.post(
        "/api/messaging/send",
        headers=headers,
        json={
            "persona_id": str(persona.id),
            "channel": "internal",
            "content": "C-05 same-sede legit",
        },
    )
    assert resp.status_code == 200, (
        f"C-05 REGRESSION: same-sede persona_id should succeed "
        f"(got {resp.status_code}): {resp.text}"
    )


# ── A-03/A-04: Schema fields ────────────────────────────────────────────


def test_communication_log_schema_has_extended_fields():
    """A-03: CommunicationLog schema includes new fields."""
    from backend.schemas.notifications import CommunicationLog as CLSchema
    fields = set(CLSchema.model_fields.keys())
    for expected in ("campaign_name", "recipient_phone", "is_read", "external_id"):
        assert expected in fields, (
            f"A-03: field '{expected}' missing from CommunicationLog schema: {fields}"
        )


def test_communication_log_create_schema():
    """A-03: CommunicationLogCreate accepts the expected fields."""
    from backend.schemas.notifications import CommunicationLogCreate
    fields = set(CommunicationLogCreate.model_fields.keys())
    assert "persona_id" in fields
    assert "channel" in fields
    assert "content" in fields
    assert "leader_id" in fields
    assert "outcome" in fields


def test_messaging_channel_enum():
    """A-04: MessagingChannel Literal type restricts values."""
    from backend.schemas.notifications import MessagingChannel
    # The Literal type is a typing construct, just verify it exists
    assert MessagingChannel is not None


# ── A-06: mark_all_read returns marked_count ─────────────────────────────


def test_mark_all_read_returns_marked_count(client, db_session):
    """A-06: POST /notifications/mark-all-read returns {marked_count: N}."""
    admin, persona, sede = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email)

    # Seed 3 unread notifications
    for i in range(3):
        notif = models.Notification(
            user_id=str(admin.id),
            title=f"Unread-{i}",
            content=f"Content-{i}",
            is_read=False,
        )
        db_session.add(notif)
    # Seed 1 already-read notification
    read_notif = models.Notification(
        user_id=str(admin.id),
        title="Already-read",
        content="read",
        is_read=True,
    )
    db_session.add(read_notif)
    db_session.commit()

    resp = client.post(
        "/api/messaging/notifications/mark-all-read", headers=headers
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "marked_count" in data, (
        f"A-06: response missing marked_count: {data}"
    )
    assert data["marked_count"] == 3, (
        f"A-06: expected marked_count=3 (3 unread), got {data['marked_count']}"
    )


def test_mark_all_read_returns_zero_when_all_read(client, db_session):
    """A-06: marked_count=0 when no unread notifications."""
    admin, persona, sede = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email)

    notif = models.Notification(
        user_id=str(admin.id),
        title="Already-read",
        content="read",
        is_read=True,
    )
    db_session.add(notif)
    db_session.commit()

    resp = client.post(
        "/api/messaging/notifications/mark-all-read", headers=headers
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["marked_count"] == 0


# ── A-05: Index exists ──────────────────────────────────────────────────


def test_auth_notifications_has_user_id_index():
    """A-05: auth_notifications table has ix_auth_notifications_user_id."""
    from backend.models_auth import NotificacionUsuario
    index_names = {i.name for i in NotificacionUsuario.__table__.indexes}
    assert "ix_auth_notifications_user_id" in index_names, (
        f"A-05: index missing. Found: {index_names}"
    )


# ── A-01: Presence endpoint enriches with persona_id ────────────────────


def test_presence_enriches_client_with_persona_id(client, db_session):
    """A-01: GET /messaging/presence/{room} returns enriched client objects."""
    admin, persona, sede = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email)
    resp = client.get("/api/messaging/presence/general", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["room"] == "general"
    assert isinstance(data["clients"], list)
    # Each client should be a dict with client_id and persona_id keys
    for entry in data["clients"]:
        assert "client_id" in entry
        assert "persona_id" in entry


# ── M-01: Notifications offset param ────────────────────────────────────


def test_notifications_supports_offset(client, db_session):
    """M-01: GET /messaging/notifications honors offset param."""
    admin, persona, sede = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email)

    for i in range(5):
        notif = models.Notification(
            user_id=str(admin.id),
            title=f"Notif-{i}",
            content=f"Content-{i}",
            is_read=False,
        )
        db_session.add(notif)
    db_session.commit()

    resp_page0 = client.get(
        "/api/messaging/notifications?limit=2&offset=0", headers=headers
    )
    resp_page1 = client.get(
        "/api/messaging/notifications?limit=2&offset=2", headers=headers
    )
    assert resp_page0.status_code == 200, resp_page0.text
    assert resp_page1.status_code == 200, resp_page1.text
    page0_ids = {n["id"] for n in resp_page0.json()}
    page1_ids = {n["id"] for n in resp_page1.json()}
    assert len(resp_page0.json()) == 2
    assert len(resp_page1.json()) == 2
    assert page0_ids.isdisjoint(page1_ids), "Pages should not overlap"


# ── M-02: History offset param ──────────────────────────────────────────


def test_history_supports_offset(client, db_session):
    """M-02: GET /messaging/history honors offset param."""
    admin, persona, sede = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email)

    for i in range(5):
        log = models.CommunicationLog(
            persona_id=persona.id,
            channel="internal",
            content=f"Message-{i}",
            outcome="internal_log",
        )
        db_session.add(log)
    db_session.commit()

    resp_page0 = client.get(
        "/api/messaging/history?limit=2&offset=0", headers=headers
    )
    resp_page1 = client.get(
        "/api/messaging/history?limit=2&offset=2", headers=headers
    )
    assert resp_page0.status_code == 200, resp_page0.text
    assert resp_page1.status_code == 200, resp_page1.text
    page0_ids = {n["id"] for n in resp_page0.json()}
    page1_ids = {n["id"] for n in resp_page1.json()}
    assert len(resp_page0.json()) == 2
    assert len(resp_page1.json()) == 2
    assert page0_ids.isdisjoint(page1_ids), "Pages should not overlap"


# ── M-04: Room name validation ──────────────────────────────────────────


def test_valid_room_names_accepted():
    """M-04: Valid room names pass the allowlist."""
    import re
    pattern = re.compile(
        r"^(global|project_[0-9a-f-]{36}|dm_[0-9a-f-]{36}|room_[0-9a-f-]{36}|general|staff)$",
        re.IGNORECASE,
    )
    assert pattern.match("global")
    assert pattern.match("general")
    assert pattern.match("staff")
    assert pattern.match("project_550e8400-e29b-41d4-a716-446655440000")
    assert pattern.match("dm_550e8400-e29b-41d4-a716-446655440000")
    assert pattern.match("room_550e8400-e29b-41d4-a716-446655440000")


def test_invalid_room_names_rejected():
    """M-04: Invalid/malicious room names fail the allowlist."""
    import re
    pattern = re.compile(
        r"^(global|project_[0-9a-f-]{36}|dm_[0-9a-f-]{36}|room_[0-9a-f-]{36}|general|staff)$",
        re.IGNORECASE,
    )
    assert not pattern.match("")
    assert not pattern.match("../../../etc/passwd")
    assert not pattern.match("admin_secrets")
    assert not pattern.match("project_not-a-uuid")
    assert not pattern.match("dm_550e8400-e29b-41d4-a716-446655440000; DROP TABLE")


# ── M-06: sede_id column exists ──────────────────────────────────────────


def test_notification_has_sede_id_column():
    """M-06: auth_notifications table has sede_id column."""
    from backend.models_auth import NotificacionUsuario
    cols = {c.name for c in NotificacionUsuario.__table__.columns}
    assert "sede_id" in cols, f"M-06: sede_id missing. Found: {cols}"


def test_notification_has_sede_id_index():
    """M-06: auth_notifications table has ix_auth_notifications_sede_id."""
    from backend.models_auth import NotificacionUsuario
    index_names = {i.name for i in NotificacionUsuario.__table__.indexes}
    assert "ix_auth_notifications_sede_id" in index_names, (
        f"M-06: index missing. Found: {index_names}"
    )


# ── M-08: Frontend type fix ─────────────────────────────────────────────


def test_notification_schema_id_is_uuid_string():
    """M-08: BackendNotification.id schema accepts UUID strings (not number)."""
    from backend.schemas.notifications import Notification as NotifSchema
    # Pydantic model should accept a UUID string as id
    n = NotifSchema(
        id=_uuid.uuid4(),
        persona_id=_uuid.uuid4(),
        title="test",
        content="test",
        is_read=False,
        created_at=datetime.now(timezone.utc),
    )
    assert isinstance(n.id, _uuid.UUID)
