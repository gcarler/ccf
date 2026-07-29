import uuid
import pytest
from unittest.mock import MagicMock, patch
import smtplib

from backend import models
from backend.services.messaging import (
    MessagingGateway,
    StubMessagingGateway,
    _create_log,
    get_messaging_gateway,
    reset_gateway_singleton,
    CommunicationOutcome,
)

class DummyPersona:
    def __init__(self, id_val, email=None, phone=None):
        self.id = id_val
        self.email = email
        self.phone = phone

class DummySettings:
    def __init__(self, stub_comms=False, smtp_host=None, smtp_port=587, smtp_user=None, smtp_password=None, test_email_override=""):
        self.stub_comms = stub_comms
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.test_email_override = test_email_override

def test_create_log_leader_id_variations():
    db = MagicMock()
    persona_id = str(uuid.uuid4())
    leader_uuid = uuid.uuid4()
    
    # 1. leader_id as UUID
    log1 = _create_log(
        db,
        persona_id=persona_id,
        channel="WhatsApp",
        content="Test 1",
        leader_id=leader_uuid
    )
    assert log1.leader_id == leader_uuid
    
    # 2. leader_id as valid UUID string
    log2 = _create_log(
        db,
        persona_id=persona_id,
        channel="WhatsApp",
        content="Test 2",
        leader_id=str(leader_uuid)
    )
    assert log2.leader_id == leader_uuid
    
    # 3. leader_id as invalid UUID string
    log3 = _create_log(
        db,
        persona_id=persona_id,
        channel="WhatsApp",
        content="Test 3",
        leader_id="invalid-uuid"
    )
    assert log3.leader_id is None

def test_messaging_gateway_resolve_to_uuid():
    gw = MessagingGateway()
    valid_uuid = uuid.uuid4()
    
    # Passing UUID directly
    res1 = gw._resolve_to_uuid(valid_uuid)
    assert res1 == valid_uuid
    
    # Passing valid UUID string
    res2 = gw._resolve_to_uuid(str(valid_uuid))
    assert res2 == valid_uuid
    
    # Passing invalid UUID string
    with pytest.raises(ValueError, match="persona_id con formato UUID inválido"):
        gw._resolve_to_uuid("invalid-uuid")

def test_messaging_gateway_persona_or_raise():
    gw = MessagingGateway()
    db = MagicMock()
    valid_uuid = uuid.uuid4()
    
    # Persona not found
    db.query.return_value.filter.return_value.first.return_value = None
    with pytest.raises(ValueError, match="Persona no encontrada"):
        gw._persona_or_raise(db, str(valid_uuid))
        
    # Persona found, require_email=True but email is missing
    persona_no_email = DummyPersona(valid_uuid, email=None)
    db.query.return_value.filter.return_value.first.return_value = persona_no_email
    with pytest.raises(ValueError, match="Persona sin correo electronico"):
        gw._persona_or_raise(db, str(valid_uuid), require_email=True)
        
    # Persona found with email
    persona_with_email = DummyPersona(valid_uuid, email="test@example.com")
    db.query.return_value.filter.return_value.first.return_value = persona_with_email
    res = gw._persona_or_raise(db, str(valid_uuid), require_email=True)
    assert res == persona_with_email

@pytest.mark.asyncio
async def test_messaging_gateway_send_whatsapp():
    gw = MessagingGateway()
    db = MagicMock()
    valid_uuid = uuid.uuid4()
    
    # Persona without phone
    persona_no_phone = DummyPersona(valid_uuid, phone=None)
    db.query.return_value.filter.return_value.first.return_value = persona_no_phone
    with pytest.raises(ValueError, match="Persona sin numero de telefono"):
        await gw.send_whatsapp(db, str(valid_uuid), "Hello", None)
        
    # Persona with phone
    persona_with_phone = DummyPersona(valid_uuid, phone="123456789")
    db.query.return_value.filter.return_value.first.return_value = persona_with_phone
    log = await gw.send_whatsapp(db, str(valid_uuid), "Hello", None, campaign_name="Campaign", external_id="EXT-123")
    assert log.channel == "WhatsApp"
    assert log.recipient_phone == "123456789"
    assert log.external_id == "EXT-123"

@pytest.mark.asyncio
async def test_messaging_gateway_send_sms():
    gw = MessagingGateway()
    db = MagicMock()
    valid_uuid = uuid.uuid4()
    
    # Persona without phone
    persona_no_phone = DummyPersona(valid_uuid, phone=None)
    db.query.return_value.filter.return_value.first.return_value = persona_no_phone
    with pytest.raises(ValueError, match="Persona sin numero celular"):
        await gw.send_sms(db, str(valid_uuid), "Hello", None)
        
    # Persona with phone
    persona_with_phone = DummyPersona(valid_uuid, phone="123456789")
    db.query.return_value.filter.return_value.first.return_value = persona_with_phone
    log = await gw.send_sms(db, str(valid_uuid), "Hello", None, campaign_name="Campaign", external_id="EXT-456")
    assert log.channel == "SMS"
    assert log.recipient_phone == "123456789"
    assert log.external_id == "EXT-456"

@pytest.mark.asyncio
async def test_messaging_gateway_send_email_outcomes():
    db = MagicMock()
    valid_uuid = uuid.uuid4()
    persona = DummyPersona(valid_uuid, email="user@example.com")
    db.query.return_value.filter.return_value.first.return_value = persona

    # 1. SMTP NOT configured
    settings_no_smtp = DummySettings(smtp_host=None)
    gw_no_smtp = MessagingGateway(settings=settings_no_smtp)
    log1 = await gw_no_smtp.send_email(db, str(valid_uuid), "Text content", None)
    assert log1.outcome == CommunicationOutcome.PENDING_SMTP_CONFIG.value

    # 2. SMTP configured, send_message succeeds (with html)
    settings_smtp = DummySettings(smtp_host="smtp.example.com", smtp_user="sender@example.com", smtp_password="secret")
    gw_smtp = MessagingGateway(settings=settings_smtp)
    
    mock_smtp_class = MagicMock()
    mock_smtp_instance = MagicMock()
    mock_smtp_class.return_value.__enter__.return_value = mock_smtp_instance
    
    with patch("smtplib.SMTP", mock_smtp_class):
        log2 = await gw_smtp.send_email(
            db, str(valid_uuid), "Text content", None, campaign_name="Email Camp", html="<p>HTML</p>"
        )
        assert log2.outcome == CommunicationOutcome.SENT_REAL.value
        mock_smtp_instance.starttls.assert_called_once()
        mock_smtp_instance.login.assert_called_once_with("sender@example.com", "secret")
        mock_smtp_instance.send_message.assert_called_once()

    # 3. SMTP configured, raises Exception (SMTP failure)
    with patch("smtplib.SMTP", side_effect=Exception("Connection error")):
        log3 = await gw_smtp.send_email(db, str(valid_uuid), "Text content", None)
        assert log3.outcome == CommunicationOutcome.SMTP_FAILED.value

@pytest.mark.asyncio
async def test_stub_messaging_gateway():
    settings = DummySettings(stub_comms=True)
    stub_gw = StubMessagingGateway(settings=settings)
    db = MagicMock()
    valid_uuid = uuid.uuid4()
    
    # 1. send_whatsapp (persona found with phone)
    persona = DummyPersona(valid_uuid, phone="987654321", email="stub@example.com")
    db.query.return_value.filter.return_value.first.return_value = persona
    log_wa = await stub_gw.send_whatsapp(db, str(valid_uuid), "WA test", None)
    assert log_wa.outcome == CommunicationOutcome.STUB.value
    assert log_wa.recipient_phone == "987654321"

    # 2. send_sms (persona not found -> phone is None)
    db.query.return_value.filter.return_value.first.return_value = None
    log_sms = await stub_gw.send_sms(db, str(valid_uuid), "SMS test", None)
    assert log_sms.outcome == CommunicationOutcome.STUB.value
    assert log_sms.recipient_phone is None

    # 3. send_email (no override match)
    db.query.return_value.filter.return_value.first.return_value = persona
    log_em = await stub_gw.send_email(db, str(valid_uuid), "Email test", None)
    assert log_em.outcome == CommunicationOutcome.STUB.value

    # 4. send_email WITH TEST_EMAIL_OVERRIDE matching email
    settings_override = DummySettings(stub_comms=True, test_email_override="stub@example.com")
    stub_gw_override = StubMessagingGateway(settings=settings_override)
    with patch.object(MessagingGateway, "send_email") as mock_super_email:
        mock_super_email.return_value = "super_result"
        res = await stub_gw_override.send_email(db, str(valid_uuid), "Override email", None)
        assert res == "super_result"
        mock_super_email.assert_called_once()

def test_get_messaging_gateway_and_reset():
    reset_gateway_singleton()
    
    settings_stub = DummySettings(stub_comms=True)
    settings_real = DummySettings(stub_comms=False)

    with patch("backend.services.messaging.get_settings", return_value=settings_stub):
        gw1 = get_messaging_gateway()
        assert isinstance(gw1, StubMessagingGateway)
        # Calling second time returns cached instance
        gw1_cached = get_messaging_gateway()
        assert gw1_cached is gw1

    # Transition from Stub to Real without reset (tests line 377 in messaging.py)
    with patch("backend.services.messaging.get_settings", return_value=settings_real):
        gw2 = get_messaging_gateway()
        assert type(gw2) is MessagingGateway
        assert not isinstance(gw2, StubMessagingGateway)

    # Test reset_gateway_singleton
    reset_gateway_singleton()
    from backend.services.messaging import _gateway_instance
    assert _gateway_instance is None
