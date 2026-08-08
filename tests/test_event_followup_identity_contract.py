from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy.orm import sessionmaker

from backend import models
from backend.schemas.crm.base import PublicEventIdentityVerify
from backend.services.event_followup_service import (
    consume_verified_identity_token,
    identifier_hash,
    normalize_identifier,
    request_identity_challenge,
    resolve_verified_identity_token,
    verify_identity_challenge,
)

ROOT = Path(__file__).resolve().parents[1]


def test_identity_normalization_is_canonical():
    assert normalize_identifier("  Person@Example.COM ", identifier_type="email") == "person@example.com"
    assert normalize_identifier(" cc - 123 456 ", identifier_type="CC") == "CC-123456"


def test_followup_models_and_migration_declare_persistent_contract():
    models = (ROOT / "backend/models_crm.py").read_text()
    migration = (ROOT / "alembic/canonical_versions/20260807_0001_event_followup_identity.py").read_text()
    assert "class EventCommunicationDelivery" in models
    assert "uq_event_communication_delivery_key" in models
    assert "class EventIdentityChallenge" in models
    assert "communication_consent" in models
    assert "event_communication_deliveries" in migration
    assert "event_identity_challenges" in migration
    assert "20260806_0001_event_contextual_roles" in migration


def test_public_contract_contains_identity_endpoints_and_single_use_token():
    public_api = (ROOT / "backend/api/public.py").read_text()
    service = (ROOT / "backend/services/event_followup_service.py").read_text()
    assert '"/events/{event_id}/identify"' in public_api
    assert '"/events/{event_id}/identify/verify"' in public_api
    assert "challenge_id=payload.challenge_id" in public_api
    assert "identifier_type == identifier_type" in service
    assert "consumed_at" in service
    assert "with_for_update" in service


def test_identity_verification_can_bind_code_to_a_specific_challenge():
    challenge_id = uuid4()
    payload = PublicEventIdentityVerify(
        identifier={"email": "person@example.com"},
        challenge_id=challenge_id,
        code="123456",
    )

    assert payload.challenge_id == challenge_id
    assert payload.code == "123456"


def test_identity_verification_requires_challenge_id():
    with pytest.raises(ValueError):
        PublicEventIdentityVerify(
            identifier={"email": "person@example.com"},
            code="123456",
        )


def test_public_identity_verify_requires_challenge_id_http(client, db_session):
    _, _, event, _ = _identity_context(db_session)
    db_session.commit()
    response = client.post(
        f"/api/public/events/{event.id}/identify/verify",
        json={"identifier": {"email": "person@example.com"}, "code": "123456"},
    )
    assert response.status_code == 422


def test_public_identity_verify_rejects_challenge_from_other_event(client, db_session):
    _, persona, event, other_event = _identity_context(db_session)
    challenge = _challenge(db_session, event, persona)
    db_session.commit()
    response = client.post(
        f"/api/public/events/{other_event.id}/identify/verify",
        json={
            "identifier": {"email": "person@example.com"},
            "challenge_id": str(challenge.id),
            "code": "123456",
        },
    )
    assert response.status_code == 403


def test_public_identity_to_registration_is_single_use(client, db_session, monkeypatch):
    """Cubre el flujo HTTP completo, no solo los helpers de servicio."""
    _, persona, event, other_event = _identity_context(db_session)
    db_session.commit()
    sent_messages = []

    def capture_email(*, to, subject, html, **kwargs):
        sent_messages.append({"to": to, "subject": subject, "html": html})
        return True

    monkeypatch.setattr("backend.services.email.send_email", capture_email)

    identify_response = client.post(
        f"/api/public/events/{event.id}/identify",
        json={"email": persona.email},
    )
    assert identify_response.status_code == 200, identify_response.text
    identify_payload = identify_response.json()
    assert identify_payload["result"] == "VERIFICATION_REQUIRED"
    challenge_id = identify_payload["challenge_id"]
    assert sent_messages and sent_messages[-1]["to"] == persona.email
    code_match = re.search(r"<strong>\s*(\d{6})\s*</strong>", sent_messages[-1]["html"])
    assert code_match is not None
    code = code_match.group(1)

    verify_response = client.post(
        f"/api/public/events/{event.id}/identify/verify",
        json={
            "identifier": {"email": persona.email},
            "challenge_id": challenge_id,
            "code": code,
        },
    )
    assert verify_response.status_code == 200, verify_response.text
    verify_payload = verify_response.json()
    verified_token = verify_payload["verified_identity_token"]
    assert verify_payload["fields"] == {
        "first_name": persona.first_name,
        "last_name": persona.last_name,
        "email": persona.email,
        "phone": persona.phone,
        "id_type": persona.id_type,
        "id_number": persona.id_number,
    }

    register_response = client.post(
        f"/api/public/events/{event.id}/register",
        json={
            "verified_identity_token": verified_token,
            "accept_contact": True,
        },
    )
    assert register_response.status_code == 200, register_response.text
    registration = register_response.json()
    assert registration["persona_id"] == str(persona.id)
    assert registration["registration_status"] == "CONFIRMED"
    assert db_session.query(models.Persona).filter(models.Persona.email == persona.email).count() == 1
    assert db_session.query(models.EventRegistration).filter_by(
        event_id=event.id,
        persona_id=persona.id,
    ).count() == 1

    challenge = db_session.query(models.EventIdentityChallenge).filter_by(
        id=challenge_id,
        event_id=event.id,
        persona_id=persona.id,
    ).one()
    assert db_session.query(models.EventIdentityChallenge).filter_by(event_id=event.id).count() == 1
    assert challenge.verified_at is not None
    assert challenge.consumed_at is not None

    cross_event_register = client.post(
        f"/api/public/events/{other_event.id}/register",
        json={"verified_identity_token": verified_token, "accept_contact": True},
    )
    assert cross_event_register.status_code == 403
    assert db_session.query(models.EventRegistration).filter_by(
        event_id=other_event.id,
        persona_id=persona.id,
    ).count() == 0

    replay_register = client.post(
        f"/api/public/events/{event.id}/register",
        json={"verified_identity_token": verified_token, "accept_contact": True},
    )
    assert replay_register.status_code == 403
    assert db_session.query(models.EventRegistration).filter_by(
        event_id=event.id,
        persona_id=persona.id,
    ).count() == 1
    persisted_registration = db_session.query(models.EventRegistration).filter_by(
        event_id=event.id,
        persona_id=persona.id,
    ).one()
    assert persisted_registration.registration_status == "CONFIRMED"

    replay_verify = client.post(
        f"/api/public/events/{event.id}/identify/verify",
        json={
            "identifier": {"email": persona.email},
            "challenge_id": challenge_id,
            "code": code,
        },
    )
    assert replay_verify.status_code == 403


def _identity_context(db_session):
    sede = models.Sede(id=uuid4(), nombre="Identity Sede", ciudad="Bogotá", es_activa=True)
    # Flush explícito de la sede antes que las entidades que la referencian:
    # CrmEvent no declara relationship a Sede, por lo que el UOW de SQLAlchemy
    # no garantiza el orden de INSERT en PostgreSQL (FK crm_events_sede_id_fkey).
    db_session.add(sede)
    db_session.flush()
    persona = models.Persona(
        id=uuid4(),
        sede_id=sede.id,
        first_name="Persona",
        last_name="Verificada",
        email="person@example.com",
    )
    event = models.CrmEvent(
        id=uuid4(),
        sede_id=sede.id,
        name="Evento Identity",
        status="SCHEDULED",
        requires_registration=True,
    )
    other_event = models.CrmEvent(
        id=uuid4(),
        sede_id=sede.id,
        name="Otro Evento",
        status="SCHEDULED",
        requires_registration=True,
    )
    db_session.add_all([persona, event, other_event])
    db_session.flush()
    return sede, persona, event, other_event


def _challenge(db_session, event, persona, *, identifier_type="email", code="123456", identifier_value=None):
    identifier_value = identifier_value or ("person@example.com" if identifier_type.lower() == "email" else persona.id_number)
    challenge = models.EventIdentityChallenge(
        id=uuid4(),
        event_id=event.id,
        identifier_type=identifier_type.upper() if identifier_type.lower() != "email" else "email",
        identifier_hash=identifier_hash(normalize_identifier(identifier_value, identifier_type=identifier_type)),
        challenge_hash=identifier_hash(code),
        persona_id=persona.id,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
        max_attempts=5,
    )
    db_session.add(challenge)
    db_session.flush()
    return challenge


def test_identity_challenge_isolated_by_event_and_identifier_type(db_session):
    _, persona, event, other_event = _identity_context(db_session)
    challenge = _challenge(db_session, event, persona)
    db_session.commit()

    with pytest.raises(ValueError, match="IDENTITY_VERIFICATION_FAILED"):
        verify_identity_challenge(
            db_session,
            other_event,
            identifier_type="email",
            identifier_value="person@example.com",
            code="123456",
            challenge_id=challenge.id,
        )
    with pytest.raises(ValueError, match="IDENTITY_VERIFICATION_FAILED"):
        verify_identity_challenge(
            db_session,
            event,
            identifier_type="CC",
            identifier_value="person@example.com",
            code="123456",
            challenge_id=challenge.id,
        )


def test_identity_ambiguity_is_rejected_instead_of_selecting_first_match(db_session):
    _, persona, event, _ = _identity_context(db_session)
    duplicate = models.Persona(
        id=uuid4(),
        sede_id=persona.sede_id,
        first_name="Otra",
        last_name="Coincidencia",
        email=persona.email,
    )
    db_session.add(duplicate)
    db_session.flush()

    from backend.services.event_followup_service import request_identity_challenge

    with pytest.raises(ValueError, match="IDENTITY_AMBIGUOUS"):
        request_identity_challenge(
            db_session,
            event,
            identifier_type="email",
            identifier_value=persona.email,
        )


def test_identity_type_is_canonical_between_challenge_and_verification(db_session, monkeypatch):
    _, persona, event, _ = _identity_context(db_session)
    persona.id_type = "CC"
    persona.id_number = "123456"
    db_session.flush()
    monkeypatch.setattr("backend.services.event_followup_service.secrets.randbelow", lambda _: 654321)

    requested = request_identity_challenge(
        db_session,
        event,
        identifier_type="cc",
        identifier_value="123 456",
    )
    challenge = db_session.query(models.EventIdentityChallenge).filter_by(
        event_id=event.id,
        identifier_type="CC",
    ).one()
    assert requested["challenge_id"] == str(challenge.id)

    result = verify_identity_challenge(
        db_session,
        event,
        identifier_type="cc",
        identifier_value="123 456",
        code="654321",
        challenge_id=challenge.id,
    )
    assert result["persona"].id == persona.id


def test_identity_challenge_replay_and_token_consumption_are_rejected(db_session):
    _, persona, event, _ = _identity_context(db_session)
    challenge = _challenge(db_session, event, persona)
    db_session.commit()

    result = verify_identity_challenge(
        db_session,
        event,
        identifier_type="email",
        identifier_value="person@example.com",
        code="123456",
        challenge_id=challenge.id,
    )
    db_session.commit()
    token = result["verified_identity_token"]

    with pytest.raises(ValueError, match="IDENTITY_VERIFICATION_FAILED"):
        verify_identity_challenge(
            db_session,
            event,
            identifier_type="email",
            identifier_value="person@example.com",
            code="123456",
            challenge_id=challenge.id,
        )

    consume_verified_identity_token(db_session, event, token)
    db_session.commit()
    with pytest.raises(ValueError, match="IDENTITY_TOKEN_INVALID"):
        resolve_verified_identity_token(db_session, event, token)


@pytest.mark.postgres

def test_identity_challenge_postgres_concurrent_verification_is_single_use(db_session):
    """Two independent PostgreSQL sessions may verify a challenge only once."""
    if db_session.get_bind().dialect.name != "postgresql":
        pytest.skip("SQLite no representa concurrencia de locks; requiere PostgreSQL")

    _, persona, event, _ = _identity_context(db_session)
    challenge = _challenge(db_session, event, persona)
    db_session.commit()

    session_factory = sessionmaker(bind=db_session.get_bind(), expire_on_commit=False)
    barrier = Barrier(2)

    event_id = event.id
    challenge_id = challenge.id

    def verify_in_independent_session():
        session = session_factory()
        try:
            barrier.wait(timeout=10)
            event_for_session = session.query(models.CrmEvent).filter_by(id=event_id).one()
            result = verify_identity_challenge(
                session,
                event_for_session,
                identifier_type="email",
                identifier_value="person@example.com",
                code="123456",
                challenge_id=challenge_id,
            )
            session.commit()
            return ("success", result["verified_identity_token"])
        except ValueError as exc:
            session.rollback()
            return ("rejected", str(exc))
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: verify_in_independent_session(), range(2)))

    successes = [value for kind, value in results if kind == "success"]
    rejected = [value for kind, value in results if kind == "rejected"]
    assert len(successes) == 1
    assert len(rejected) == 1
    assert len(successes[0]) >= 32
    assert rejected[0] == "IDENTITY_VERIFICATION_FAILED"

    verification = db_session.query(models.EventIdentityChallenge).filter_by(id=challenge_id).one()
    # La sesión original mantiene el challenge en su identity map desde antes de
    # los hilos; refresh() lee el estado persistido por el thread ganador.
    db_session.refresh(verification)
    assert verification.verified_at is not None
    assert verification.consumed_at is None
