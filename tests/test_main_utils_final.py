"""Final coverage for main_utils.py — remaining branches."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from backend import models
from backend.api.evangelism_main.main_utils import (
    _channel_label,
    _persona_matches_segment,
    _resolve_campaign_personas,
    _serialize_message_group,
    _serialize_crm_task,
)


# ── _channel_label ─────────────────────────────────────────────────────────────

class TestChannelLabel:
    def test_whatsapp(self):
        assert _channel_label("whatsapp") == "WhatsApp"
        assert _channel_label("WHATSAPP") == "WhatsApp"
    def test_email(self):
        assert _channel_label("email") == "Email"
        assert _channel_label("EMAIL") == "Email"
    def test_sms(self):
        assert _channel_label("sms") == "SMS"
        assert _channel_label("") == "SMS"
        assert _channel_label(None) == "SMS"
    def test_unknown(self):
        assert _channel_label("telegram") == "SMS"


# ── _persona_matches_segment ───────────────────────────────────────────────────

class TestPersonaMatchesSegment:
    def test_vip_match(self):
        """Line 63: persona.id in donation_persona_ids."""
        p = type("P", (), {"id": uuid.uuid4(), "church_role_effective": None, "estado_vital": None, "family_id": None})()
        result = _persona_matches_segment(p, "vip", {str(p.id)})
        assert result is True

    def test_vip_no_match(self):
        p = type("P", (), {"id": uuid.uuid4(), "church_role_effective": None, "estado_vital": None, "family_id": None})()
        result = _persona_matches_segment(p, "vip", set())
        assert result is False


# ── _resolve_campaign_personas ─────────────────────────────────────────────────

class TestResolveCampaignPersonas:
    def test_empty_segments(self):
        """Returns empty list."""
        db = MagicMock()
        assert _resolve_campaign_personas(db, []) == []


# ── _serialize_message_group ───────────────────────────────────────────────────

class TestSerializeMessageGroup:
    def test_single_log(self):
        """Basic serialization with one log."""
        log = type("L", (), {
            "id": 1, "created_at": datetime(2026, 7, 1, tzinfo=timezone.utc),
            "campaign_name": None, "channel": "sms", "content": "Hello",
            "outcome": "sent_real", "recipient_phone": "+123", "external_id": None,
            "persona": type("P", (), {"nombre_completo": "John Doe"})(),
        })()
        result = _serialize_message_group([log])
        assert result["channel"] == "sms"
        assert result["delivered_count"] >= 0
        assert result["persona_name"] == "John Doe"

    def test_no_persona(self):
        """Line 115: no persona returns 'Desconocido'."""
        log = type("L", (), {
            "id": 1, "created_at": datetime(2026, 7, 1, tzinfo=timezone.utc),
            "campaign_name": None, "channel": "sms", "content": "Hi",
            "outcome": "failed", "recipient_phone": None, "external_id": None,
            "persona": None,
        })()
        result = _serialize_message_group([log])
        assert result["persona_name"] == "Desconocido"
        # failed_count > 0 and delivered_count == 0 -> status "failed" (line 125)
        assert result["status"] == "failed"

    def test_partial_status(self):
        """Line 127: both failed and delivered -> status 'partial'."""
        logs = []
        for i, outcome in enumerate(["sent_real", "failed"]):
            log = type("L", (), {
                "id": i, "created_at": datetime(2026, 7, 1, tzinfo=timezone.utc),
                "campaign_name": None, "channel": "sms", "content": "Hi",
                "outcome": outcome, "recipient_phone": None, "external_id": None,
                "persona": type("P", (), {"nombre_completo": "John Doe"})(),
            })()
            logs.append(log)
        result = _serialize_message_group(logs)
        assert result["status"] == "partial"

    def test_has_campaign_name(self):
        """Line 117: campaign_name found."""
        log = type("L", (), {
            "id": 1, "created_at": datetime(2026, 7, 1, tzinfo=timezone.utc),
            "campaign_name": "Summer2026", "channel": "email", "content": "Promo",
            "outcome": "sent_real", "recipient_phone": None, "external_id": None,
            "persona": type("P", (), {"nombre_completo": "Jane Doe"})(),
        })()
        result = _serialize_message_group([log])
        assert result["campaign_name"] == "Summer2026"
        assert result["name"] == "Summer2026"

    def test_multi_contact_campaign(self):
        """Line 133: multiple logs -> campaign display."""
        logs = []
        for i in range(3):
            log = type("L", (), {
                "id": i, "created_at": datetime(2026, 7, 1, tzinfo=timezone.utc),
                "campaign_name": None, "channel": "sms", "content": "Hi",
                "outcome": "sent_real", "recipient_phone": None, "external_id": None,
                "persona": type("P", (), {"nombre_completo": f"Person {i}"})(),
            })()
            logs.append(log)
        result = _serialize_message_group(logs)
        assert "contactos" in result["name"]

    def test_status_fallback(self):
        """Line 129: default status from outcome."""
        log = type("L", (), {
            "id": 1, "created_at": datetime(2026, 7, 1, tzinfo=timezone.utc),
            "campaign_name": None, "channel": "sms", "content": "Hi",
            "outcome": "sent", "recipient_phone": None, "external_id": None,
            "persona": type("P", (), {"nombre_completo": "Bob"})(),
        })()
        result = _serialize_message_group([log])
        assert result["status"] == "sent"


# ── _serialize_crm_task ───────────────────────────────────────────────────────

class TestSerializeCrmTask:
    def test_basic_serialization(self):
        """Lines 158-162: persona and assignee fallbacks."""
        task = type("T", (), {
            "id": 1, "title": "Task 1", "description": "Desc", "status": "open",
            "priority": "high", "category": "call", "due_date": None,
            "persona_id": uuid.uuid4(), "created_at": None,
            "persona": type("P", (), {"nombre_completo": "Contact"})(),
            "assignee": type("P", (), {"nombre_completo": "Assignee"})(),
        })()
        result = _serialize_crm_task(task)
        assert result["title"] == "Task 1"
        assert result["persona_name"] == "Contact"
        assert result["assigned_to"] == "Assignee"

    def test_no_persona_no_assignee(self):
        """Fallback when persona/assignee attributes are missing."""
        task = type("T", (), {
            "id": 2, "title": "Task 2", "description": None, "status": "done",
            "priority": "low", "category": None, "due_date": None,
            "persona_id": uuid.uuid4(), "created_at": None,
            "persona": None, "assignee": None,
        })()
        result = _serialize_crm_task(task)
        assert result["persona_name"] is None
        assert result["assigned_to"] is None
