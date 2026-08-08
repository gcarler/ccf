"""Messaging send endpoint — using dependency override approach."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend import models
from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin


def _ok(status):
    return status in (200, 201, 204)


@pytest.fixture
def full(client, db_session):
    admin, _, _ = _seed_admin(db_session, email="pas6@test.com")
    headers = _auth_headers(client, email="pas6@test.com", password="testpass123")
    sede = db_session.query(models.Sede).first()
    return {"c": client, "h": headers, "s": sede}


class TestMessagingSend:
    def test_missing_channel_422(self, full):
        """Schema validation rejects missing channel/content with 422."""
        resp = full["c"].post("/api/crm/messaging/send",
            json={"template_id": str(uuid.uuid4())}, headers=full["h"])
        assert resp.status_code == 422

    def _call_with_payload_override(self, full, client, db_session, **payload_kw):
        """Send a messaging payload with the gateway mocked. Sends the real
        JSON body (channel/content are required by the schema) and only
        overrides the MessagingGateway dependency."""
        c, h, s = full["c"], full["h"], full["s"]

        from backend.services.messaging import get_messaging_gateway
        gw = MagicMock()
        gw.send_sms = AsyncMock(return_value=type("L", (), {"id": 1})())
        gw.send_whatsapp = AsyncMock(return_value=type("L", (), {"id": 1})())
        gw.send_email = AsyncMock(return_value=type("L", (), {"id": 1})())
        client.app.dependency_overrides[get_messaging_gateway] = lambda: gw

        body = {
            "channel": payload_kw.get("channel", "sms"),
            "content": payload_kw.get("content", "Test SMS"),
        }
        if payload_kw.get("persona_id"):
            body["persona_id"] = str(payload_kw["persona_id"])
        if payload_kw.get("target_segments"):
            body["target_segments"] = payload_kw["target_segments"]

        return c.post("/api/crm/messaging/send", json=body, headers=h)

    def test_send_sms(self, full, client, db_session):
        """SMS channel."""
        s = full["s"]
        p = models.Persona(id=uuid.uuid4(), first_name="S", last_name="T",
                          sede_id=s.id, phone="+573001234561")
        db_session.add(p)
        db_session.commit()

        try:
            resp = self._call_with_payload_override(full, client, db_session,
                channel="sms", content="Test SMS", persona_id=p.id)
            assert _ok(resp.status_code), f"sms: {resp.status_code} {resp.text[:200]}"
        finally:
            client.app.dependency_overrides.clear()
