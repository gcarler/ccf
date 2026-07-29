"""Tests exhaustivos y estructurales para backend/services/messaging.py (100% Cobertura)."""

import pytest
import uuid
from unittest.mock import patch, MagicMock
from backend import models
from backend.services.messaging import (
    MessagingGateway,
    StubMessagingGateway,
    get_messaging_gateway,
    reset_gateway_singleton,
    _create_log,
    CommunicationOutcome,
)


class TestMessaging100Pct:

    def test_create_log_leader_id_variations(self, db_session):
        p = models.Persona(first_name="Leader", last_name="Test")
        db_session.add(p)
        db_session.commit()

        # 1. UUID object leader_id
        uid_leader = uuid.uuid4()
        log1 = _create_log(
            db_session,
            persona_id=str(p.id),
            channel="Email",
            content="Content 1",
            leader_id=uid_leader,
        )
        assert log1.leader_id == uid_leader

        # 2. String UUID leader_id
        str_leader = str(uuid.uuid4())
        log2 = _create_log(
            db_session,
            persona_id=str(p.id),
            channel="SMS",
            content="Content 2",
            leader_id=str_leader,
        )
        assert str(log2.leader_id) == str_leader

        # 3. Invalid format leader_id string
        log3 = _create_log(
            db_session,
            persona_id=str(p.id),
            channel="WhatsApp",
            content="Content 3",
            leader_id="not-a-uuid",
        )
        assert log3.leader_id is None

    def test_messaging_gateway_validation_errors(self, db_session):
        gw = MessagingGateway()

        # 1. Invalid persona UUID string
        with pytest.raises(ValueError, match="persona_id con formato UUID"):
            gw._resolve_to_uuid("invalid-uuid")

        # 2. Persona not found
        with pytest.raises(ValueError, match="Persona no encontrada"):
            gw._persona_or_raise(db_session, str(uuid.uuid4()))

        # 3. Persona missing email
        p_no_email = models.Persona(first_name="NoEmail", last_name="", phone="3000000000")
        db_session.add(p_no_email)
        db_session.commit()

        with pytest.raises(ValueError, match="Persona sin correo"):
            gw._persona_or_raise(db_session, str(p_no_email.id), require_email=True)

    def test_messaging_gateway_send_whatsapp_and_sms(self, db_session):
        import asyncio
        gw = MessagingGateway()

        p_no_phone = models.Persona(first_name="NoPhone", last_name="", email="nophone@test.com")
        p_valid = models.Persona(first_name="Valid", last_name="", email="valid@test.com", phone="3001112233")
        db_session.add_all([p_no_phone, p_valid])
        db_session.commit()

        # Missing phone raises
        with pytest.raises(ValueError, match="telefono"):
            asyncio.run(gw.send_whatsapp(db_session, str(p_no_phone.id), "Hola", leader_id=None))

        with pytest.raises(ValueError, match="celular"):
            asyncio.run(gw.send_sms(db_session, str(p_no_phone.id), "Hola", leader_id=None))

        # Success paths
        log_wa = asyncio.run(gw.send_whatsapp(db_session, str(p_valid.id), "Hola WA", leader_id=None, campaign_name="WA Camp"))
        assert log_wa.channel == "WhatsApp"
        assert log_wa.campaign_name == "WA Camp"

        log_sms = asyncio.run(gw.send_sms(db_session, str(p_valid.id), "Hola SMS", leader_id=None, campaign_name="SMS Camp"))
        assert log_sms.channel == "SMS"
        assert log_sms.campaign_name == "SMS Camp"

    def test_messaging_gateway_send_email_smtp_modes(self, db_session):
        import asyncio
        p = models.Persona(first_name="EmailUser", last_name="", email="user@test.com")
        db_session.add(p)
        db_session.commit()

        # 1. No SMTP credentials -> PENDING_SMTP_CONFIG
        settings_no_smtp = MagicMock(smtp_host=None, smtp_user=None, smtp_password=None)
        gw1 = MessagingGateway(settings=settings_no_smtp)
        log1 = asyncio.run(gw1.send_email(db_session, str(p.id), "Text body", leader_id=None))
        assert log1.outcome == CommunicationOutcome.PENDING_SMTP_CONFIG.value

        # 2. SMTP credentials with success
        settings_smtp = MagicMock(
            smtp_host="smtp.test.com",
            smtp_port=587,
            smtp_user="smtp@test.com",
            smtp_password="password",
        )
        gw2 = MessagingGateway(settings=settings_smtp)
        with patch("smtplib.SMTP") as mock_smtp_cls:
            mock_server = MagicMock()
            mock_smtp_cls.return_value.__enter__.return_value = mock_server
            log2 = asyncio.run(gw2.send_email(db_session, str(p.id), "Text body", leader_id=None, html="<h1>HTML</h1>"))
            assert log2.outcome == CommunicationOutcome.SENT_REAL.value

        # 3. SMTP credentials with exception -> SMTP_FAILED
        with patch("smtplib.SMTP", side_effect=RuntimeError("Connection refused")):
            log3 = asyncio.run(gw2.send_email(db_session, str(p.id), "Text body", leader_id=None))
            assert log3.outcome == CommunicationOutcome.SMTP_FAILED.value

    def test_stub_messaging_gateway_and_override(self, db_session):
        import asyncio
        p_normal = models.Persona(first_name="Normal", last_name="", email="normal@test.com", phone="300123")
        p_override = models.Persona(first_name="Override", last_name="", email="override@test.com", phone="300999")
        db_session.add_all([p_normal, p_override])
        db_session.commit()

        settings_stub = MagicMock(
            stub_comms=True,
            test_email_override="override@test.com",
            smtp_host=None,
        )
        stub_gw = StubMessagingGateway(settings=settings_stub)

        # Stub WA and SMS
        log_wa = asyncio.run(stub_gw.send_whatsapp(db_session, str(p_normal.id), "Stub WA", leader_id=None))
        assert log_wa.outcome == StubMessagingGateway.OUTCOME

        log_sms = asyncio.run(stub_gw.send_sms(db_session, str(p_normal.id), "Stub SMS", leader_id=None))
        assert log_sms.outcome == StubMessagingGateway.OUTCOME

        # Stub Email without override
        log_em_stub = asyncio.run(stub_gw.send_email(db_session, str(p_normal.id), "Stub Email", leader_id=None))
        assert log_em_stub.outcome == StubMessagingGateway.OUTCOME

        # Stub Email with override matching email
        log_em_override = asyncio.run(stub_gw.send_email(db_session, str(p_override.id), "Override Email", leader_id=None))
        assert log_em_override.outcome == CommunicationOutcome.PENDING_SMTP_CONFIG.value

    def test_get_messaging_gateway_factory(self):
        reset_gateway_singleton()
        with patch("backend.services.messaging.get_settings") as mock_set:
            mock_set.return_value = MagicMock(stub_comms=True)
            gw1 = get_messaging_gateway()
            assert isinstance(gw1, StubMessagingGateway)

            reset_gateway_singleton()
            mock_set.return_value = MagicMock(stub_comms=False)
            gw2 = get_messaging_gateway()
            assert isinstance(gw2, MessagingGateway)
            assert not isinstance(gw2, StubMessagingGateway)

            reset_gateway_singleton()
