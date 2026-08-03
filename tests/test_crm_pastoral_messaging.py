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
    def test_missing_channel_400(self, full):
        """Schema validation rejects missing channel/content."""
        resp = full["c"].post("/api/crm/messaging/send",
            json={"template_id": str(uuid.uuid4())}, headers=full["h"])
        assert resp.status_code == 400

    def _call_with_payload_override(self, full, client, db_session, **payload_kw):
        """Override the route's body dependency to bypass schema validation."""
        c, h, s = full["c"], full["h"], full["s"]
        from backend.schemas.crm.base import MessagingSend

        # Create a mock payload object with all attributes the endpoint reads
        mock = MagicMock(spec=MessagingSend)
        mock.template_id = payload_kw.get("template_id", uuid.uuid4())
        mock.channel = payload_kw.get("channel", "sms")
        mock.content = payload_kw.get("content", "test")
        mock.persona_id = payload_kw.get("persona_id", None)
        mock.campaign_name = payload_kw.get("campaign_name", None)
        mock.name = payload_kw.get("name", None)
        mock.target_segments = payload_kw.get("target_segments", None)
        mock.recipient_ids = payload_kw.get("recipient_ids", [])
        mock.recipient_role = payload_kw.get("recipient_role", None)
        mock.variables = payload_kw.get("variables", {})

        # Patch the schema's init to always return our mock
        # This works because FastAPI calls MessagingSend(**body_data) internally
        original_init = MessagingSend.__init__
        original_new = MessagingSend.__new__

        def mock_init(self, **kwargs):
            # Copy our mock's attributes onto self
            self.__dict__.update(mock.__dict__)

        # MessagingSend(**data) creates instance then validates
        # We intercept by making __new__ return our mock instance
        @staticmethod
        def mock_new(cls, **kwargs):
            return mock

        MessagingSend.__new__ = mock_new
        MessagingSend.__init__ = lambda self, **kwargs: None

        try:
            resp = c.post("/api/crm/messaging/send",
                json={"template_id": str(uuid.uuid4()), **payload_kw.get("extra_json", {})},
                headers=h)
            return resp
        finally:
            MessagingSend.__init__ = original_init
            MessagingSend.__new__ = original_new

    def test_send_sms(self, full, client, db_session):
        """SMS channel."""
        s = full["s"]
        p = models.Persona(id=uuid.uuid4(), first_name="S", last_name="T",
                          sede_id=s.id, phone="+573001234561")
        db_session.add(p)
        db_session.commit()

        from backend.services.messaging import get_messaging_gateway
        gw = MagicMock()
        gw.send_sms = AsyncMock(return_value=type("L", (), {"id": 1})())
        client.app.dependency_overrides[get_messaging_gateway] = lambda: gw

        try:
            resp = self._call_with_payload_override(full, client, db_session,
                channel="sms", content="Test SMS", persona_id=p.id)
            assert _ok(resp.status_code), f"sms: {resp.status_code} {resp.text[:200]}"
        finally:
            client.app.dependency_overrides.clear()
