"""Calidad del pre-registro contextual — expiración de cancel y rutas públicas.

Reconstruido desde su bytecode (restauración de trabajo perdido): valida que
el token de cancelación expire a las 72h (anclado al QR), que el QR del
ticket esté hash-bound (el token plano nunca se persiste) y que el QR expire
a los 365 días (plan §4.3) tanto en ``/ticket`` como en el check-in
``ccf-evt-checkin`` (410), más la existencia de las rutas públicas
``/ticket`` y ``/cancel``.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from backend import models
from backend.api.public import router
from backend.core.security import get_password_hash
from backend.models_auth import RolPlataforma, Usuario
from backend.models_crm import Persona
from backend.models_evangelism import Sede
from backend.services.event_registration_service import (
    _issue_cancel_token,
    _issue_qr,
    _utcnow,
    generate_qr_token,
    is_cancel_token_expired,
    is_qr_token_expired,
)
from tests.conftest import auth_headers


def test_cancel_token_expires_and_qr_ticket_is_hash_bound():
    """El token de cancelación vence a las 72h; el QR se resuelve por hash."""

    class _FakeDB:
        """Suficiente para _issue_*: solo necesitan flush()."""

        def flush(self):
            return None

    reg = models.EventRegistration(
        id=uuid.uuid4(),
        event_id=uuid.uuid4(),
        persona_id=uuid.uuid4(),
    )
    _issue_qr(_FakeDB(), reg)
    _issue_cancel_token(_FakeDB(), reg)

    # Recién emitido: el token de cancelación NO está expirado.
    assert is_cancel_token_expired(reg) is False

    # QR hash-bound: el token plano nunca se persiste en la columna; el hash sí.
    assert reg.qr_token is None
    assert reg.qr_token_hash
    assert (reg.extras or {}).get("_cancel_token_hash")

    # 73h después de la emisión (anclada a qr_generated_at): expirado.
    reg.qr_generated_at = _utcnow() - timedelta(hours=73)
    assert is_cancel_token_expired(reg) is True


def test_public_ticket_and_cancel_routes_exist():
    """Las rutas públicas /ticket (GET) y /cancel (POST) están registradas."""
    paths = {getattr(route, "path", "") for route in router.routes}
    assert "/events/{event_id}/ticket" in paths
    assert "/events/{event_id}/cancel" in paths


def test_qr_token_expires_after_365_days():
    """El QR expira a los 365 días (plan §4.3); recién emitido no expira."""

    class _FakeDB:
        def flush(self):
            return None

    reg = models.EventRegistration(
        id=uuid.uuid4(),
        event_id=uuid.uuid4(),
        persona_id=uuid.uuid4(),
    )
    _issue_qr(_FakeDB(), reg)

    # Recién emitido: vigente.
    assert is_qr_token_expired(reg) is False

    # Sin qr_generated_at → expirado (no se puede validar antigüedad).
    reg.qr_generated_at = None
    assert is_qr_token_expired(reg) is True

    # 366 días después de la emisión: expirado.
    reg.qr_generated_at = _utcnow() - timedelta(days=366)
    assert is_qr_token_expired(reg) is True


@pytest.fixture
def _evan_user(db_session):
    """Usuario evangelista con permisos de edit (mismo patrón que checkin full)."""
    sede = db_session.query(Sede).first()
    if not sede:
        sede = Sede(id=uuid.uuid4(), nombre="Test", ciudad="Test", es_activa=True)
        db_session.add(sede)
        db_session.flush()

    role = RolPlataforma(
        id=uuid.uuid4(),
        nombre="EVANGELISTA",
        permisos={"evangelism:edit": "allow", "evangelism:read": "allow"},
    )
    db_session.add(role)
    db_session.flush()

    p = Persona(id=uuid.uuid4(), first_name="QR", last_name="Expiry", sede_id=sede.id)
    db_session.add(p)
    db_session.flush()

    user = Usuario(
        id=p.id,
        sede_id=sede.id,
        username="qr_expiry",
        email="qr_expiry@test.com",
        password_hash=get_password_hash("test123"),
        rol_plataforma_id=role.id,
        is_active=True,
        is_email_verified=True,
    )
    db_session.add(user)
    db_session.commit()
    return {"user": user, "sede": sede}


@pytest.fixture
def _evan_client(client, _evan_user):
    """Cliente autenticado con el usuario evangelista."""
    headers = auth_headers(client, email="qr_expiry@test.com", password="test123")
    return {"c": client, "h": headers, "s": _evan_user["sede"]}


def _expired_qr_registration(db_session, sede, *, days_ago: int = 366) -> dict:
    """Crea evento + persona + inscripción CONFIRMED con QR vencido.

    Returns el token plano (para la request) y el event_id.
    """
    evt = models.CrmEvent(
        id=uuid.uuid4(),
        name="QR Expiry Event",
        event_date=datetime(2026, 8, 15, 10, 0, 0, tzinfo=timezone.utc),
        sede_id=sede.id,
    )
    db_session.add(evt)
    db_session.flush()

    p = Persona(id=uuid.uuid4(), first_name="Expired", last_name="QR", sede_id=sede.id)
    db_session.add(p)
    db_session.flush()

    token, token_hash = generate_qr_token(evt.id, p.id)
    reg = models.EventRegistration(
        id=uuid.uuid4(),
        event_id=evt.id,
        persona_id=p.id,
        registration_status="CONFIRMED",
        qr_token_hash=token_hash,
        qr_generated_at=_utcnow() - timedelta(days=days_ago),
        participant_role_code="MIEMBRO",
    )
    db_session.add(reg)
    db_session.commit()
    return {"token": token, "event_id": evt.id, "persona_id": p.id}


def test_public_ticket_rejects_expired_qr(client, db_session, _evan_user):
    """GET /ticket con QR vencido (366d) → 410."""
    data = _expired_qr_registration(db_session, _evan_user["sede"])
    resp = client.get(
        f"/api/public/events/{data['event_id']}/ticket?token={data['token']}"
    )
    assert resp.status_code == 410, resp.text[:200]


def test_ccf_evt_checkin_rejects_expired_qr(_evan_client, db_session):
    """POST ccf-evt-checkin con QR vencido (366d) → 410."""
    c, h, s = _evan_client["c"], _evan_client["h"], _evan_client["s"]
    data = _expired_qr_registration(db_session, s)
    resp = c.post(
        f"/api/evangelism/events/{data['event_id']}/sessions/2026-08-15/ccf-evt-checkin",
        json={"qr_token": data["token"]},
        headers=h,
    )
    assert resp.status_code == 410, resp.text[:200]


def test_public_ticket_accepts_fresh_qr(client, db_session, _evan_user):
    """GET /ticket con QR recién emitido → 200 (regresión de la expiración)."""
    data = _expired_qr_registration(db_session, _evan_user["sede"], days_ago=1)
    resp = client.get(
        f"/api/public/events/{data['event_id']}/ticket?token={data['token']}"
    )
    assert resp.status_code == 200, resp.text[:200]
    body = resp.json()
    assert body["participant_role_code"] == "MIEMBRO"
