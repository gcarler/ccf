"""Unit tests for evangelism_main/main_utils.py — pure functions."""
from __future__ import annotations

import uuid

from backend.api.evangelism_main import main_utils as utils
from backend import models


class TestChannelLabel:
    def test_whatsapp(self):
        assert utils._channel_label("whatsApp") == "WhatsApp"
        assert utils._channel_label("WHATSAPP") == "WhatsApp"
    def test_email(self):
        assert utils._channel_label("email") == "Email"
    def test_sms(self):
        assert utils._channel_label("sms") == "SMS"
        assert utils._channel_label(None) == "SMS"


class TestPersonaMatchesSegment:
    def test_active_match(self, db_session):
        p = models.Persona(id=uuid.uuid4(), first_name="A", last_name="B", church_role_effective="miembro")
        db_session.add(p)
        db_session.commit()
        assert utils._persona_matches_segment(p, "active", set()) is True
    def test_active_no_match(self, db_session):
        p = models.Persona(id=uuid.uuid4(), first_name="A", last_name="B", church_role_effective="visitante")
        db_session.add(p)
        db_session.commit()
        assert utils._persona_matches_segment(p, "active", set()) is False
    def test_new_match(self, db_session):
        p = models.Persona(id=uuid.uuid4(), first_name="A", last_name="B", estado_vital="nuevo")
        db_session.add(p)
        db_session.commit()
        assert utils._persona_matches_segment(p, "new", set()) is True
    def test_staff_match(self, db_session):
        p = models.Persona(id=uuid.uuid4(), first_name="A", last_name="B", church_role_effective="pastor")
        db_session.add(p)
        db_session.commit()
        assert utils._persona_matches_segment(p, "staff", set()) is True
    def test_empty(self, db_session):
        p = models.Persona(id=uuid.uuid4(), first_name="A", last_name="B")
        db_session.add(p)
        db_session.commit()
        assert utils._persona_matches_segment(p, "", set()) is False
