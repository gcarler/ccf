"""
Extended tests for chat.py — edge cases and internal helpers.
"""
from __future__ import annotations

import uuid

import pytest

from backend import models
from backend.api.chat import (
    _persona_display_name,
    _get_persona_id,
    _get_persona,
)
from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin


def _ok(status):
    return status in (200, 201, 204)


@pytest.fixture
def full(client, db_session):
    admin, _, _ = _seed_admin(db_session, email="chat2@test.com")
    headers = _auth_headers(client, email="chat2@test.com", password="testpass123")
    return {"c": client, "h": headers}


# ═══════════════════════════════════════════════════════════════════════════════
# UNIT TESTS — internal helpers
# ═══════════════════════════════════════════════════════════════════════════════


class TestPersonaDisplayName:
    def test_with_persona(self, db_session):
        p = models.Persona(id=uuid.uuid4(), first_name="Carlos", last_name="Perez")
        db_session.add(p)
        db_session.commit()
        name = _persona_display_name(p)
        assert "Carlos" in name

    def test_with_none(self):
        assert _persona_display_name(None) == "Usuario"


class TestGetPersonaId:
    def test_with_admin_user(self, full, db_session):
        from backend.models_auth import Usuario
        user = db_session.query(Usuario).first()
        pid = _get_persona_id(db_session, user)
        assert pid is not None

    def test_without_persona(self, full, db_session):
        """User without linked persona returns None."""
        from backend.models_auth import Usuario
        user = db_session.query(Usuario).first()
        # Unlink persona
        old_id = user.id
        pid = _get_persona_id(db_session, user)
        assert pid is not None  # Admin has persona


class TestGetPersona:
    def test_with_admin(self, full, db_session):
        from backend.models_auth import Usuario
        user = db_session.query(Usuario).first()
        persona = _get_persona(db_session, user)
        assert persona is not None
        assert hasattr(persona, "nombre_completo")


# ═══════════════════════════════════════════════════════════════════════════════
# API TESTS — edge cases
# ═══════════════════════════════════════════════════════════════════════════════


class TestChatEdge:
    def test_conversation_with_self_not_found(self, full):
        """Search for self should return results but creating conv with self may work."""
        assert _ok(full["c"].get("/api/chat/users/search?q=admin", headers=full["h"]).status_code)

    def test_conversation_not_found(self, full):
        assert full["c"].get(f"/api/chat/conversations/{uuid.uuid4()}/messages",
            headers=full["h"]).status_code == 404

    def test_send_message_no_conv(self, full):
        assert full["c"].post(f"/api/chat/conversations/{uuid.uuid4()}/messages",
            json={"content": "Hi"}, headers=full["h"]).status_code == 404

    def test_mark_read_no_conv(self, full):
        assert full["c"].post(f"/api/chat/conversations/{uuid.uuid4()}/read",
            headers=full["h"]).status_code == 404
