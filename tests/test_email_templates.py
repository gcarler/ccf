"""Tests para email_templates.py — renderers HTML responsive."""
from __future__ import annotations

from backend.services.email import _FALLBACK_BRAND
from backend.services.email_templates import (
    _RENDERERS,
    render_birthday,
    render_counseling_reminder,
    render_email,
    render_event_invitation,
    render_pastoral_close,
    render_pastoral_followup,
    render_welcome,
    render_welcome_guide,
)


class TestDispatcher:
    def test_valid_type(self):
        assert len(render_email("welcome", {"nombre": "T", "sede": "S"})) > 100
    def test_invalid_type(self):
        assert render_email("nonexistent", {}) == ""
    def test_all_keys_valid(self):
        assert set(_RENDERERS.keys()) == {"welcome", "birthday", "pastoral_followup", "pastoral_close", "event_invitation", "welcome_guide", "counseling_reminder"}

class TestWelcome:
    def test_contains_nombre(self):
        assert "Carlos" in render_welcome({"nombre": "Carlos", "sede": "CCF"})
    def test_is_html(self):
        r = render_welcome({"nombre": "T", "sede": "S"})
        assert r.startswith("<!DOCTYPE html>") and "</html>" in r

class TestBirthday:
    def test_contains_nombre(self):
        assert "Maria" in render_birthday({"nombre": "Maria"})
    def test_verse(self):
        assert "Jerem" in render_birthday({"nombre": "T"})

class TestPastoralFollowup:
    def test_pastor(self):
        assert "Pastor Juan" in render_pastoral_followup({"nombre": "L", "pastor": "Pastor Juan", "sede": "S"})

class TestPastoralClose:
    def test_sede(self):
        assert "Iglesia" in render_pastoral_close({"nombre": "T", "sede": "Iglesia"})

class TestEventInvitation:
    def test_evento(self):
        assert "Conferencia" in render_event_invitation({"nombre": "P", "evento": "Conferencia", "fecha": "15 Ago", "hora": "18:00", "lugar": "Aud", "link": "#"})

class TestWelcomeGuide:
    def test_link(self):
        assert "https://x.com" in render_welcome_guide({"nombre": "A", "link_guia": "https://x.com", "sede": "S"})

class TestCounselingReminder:
    def test_fecha(self):
        assert "2026-07-15" in render_counseling_reminder({"nombre": "L", "fecha": "2026-07-15", "hora": "14:00", "pastoral_name": "P"})

class TestBranding:
    def test_fallback(self):
        r = render_welcome({"nombre": "T", "sede": "S"})
        assert _FALLBACK_BRAND["dark"] in r and _FALLBACK_BRAND["primary"] in r
    def test_custom(self):
        custom = {"primary": "#FF0000", "dark": "#333", "medium": "#666", "pale": "#EEE", "church_name": "Iglesia", "logo_url": ""}
        assert "#FF0000" in render_welcome({"nombre": "T", "sede": "S"}, custom)
