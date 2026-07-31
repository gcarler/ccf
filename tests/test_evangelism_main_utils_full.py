"""Complete coverage for evangelism_main/main_utils.py — all working tests."""

from __future__ import annotations

import uuid

from backend import models
from backend.api.evangelism_main import main_utils as utils


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

    def test_groups_match(self, db_session):
        p = models.Persona(id=uuid.uuid4(), first_name="A", last_name="B", family_id=uuid.uuid4())
        db_session.add(p)
        db_session.commit()
        assert utils._persona_matches_segment(p, "groups", set()) is True

    def test_low_match(self, db_session):
        p = models.Persona(id=uuid.uuid4(), first_name="A", last_name="B", estado_vital="creyente")
        db_session.add(p)
        db_session.commit()
        assert utils._persona_matches_segment(p, "low", set()) is True

    def test_empty_segment(self, db_session):
        p = models.Persona(id=uuid.uuid4(), first_name="A", last_name="B")
        db_session.add(p)
        db_session.commit()
        assert utils._persona_matches_segment(p, "", set()) is False

    def test_none_segment(self, db_session):
        p = models.Persona(id=uuid.uuid4(), first_name="A", last_name="B")
        db_session.add(p)
        db_session.commit()
        assert utils._persona_matches_segment(p, None, set()) is False


class TestResolveCampaignPersonas:
    def test_empty(self, db_session):
        assert utils._resolve_campaign_personas(db_session, []) == []

    def test_with_data(self, db_session):
        p = models.Persona(id=uuid.uuid4(), first_name="A", last_name="B", church_role_effective="miembro")
        db_session.add(p)
        db_session.commit()
        result = utils._resolve_campaign_personas(db_session, ["active"])
        assert len(result) >= 1


class TestChannelLabel:
    def test_whatsapp(self):
        assert utils._channel_label("whatsapp") == "WhatsApp"
        assert utils._channel_label("WHATSAPP") == "WhatsApp"

    def test_email(self):
        assert utils._channel_label("email") == "Email"

    def test_sms(self):
        assert utils._channel_label("sms") == "SMS"
        assert utils._channel_label("") == "SMS"
        assert utils._channel_label(None) == "SMS"
