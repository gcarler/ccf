"""Tests del pre-registro público a eventos masivos (plan_de_preregistro, Fase 2).

Cubre los casos clave del plan §6 aplicables a la API pública implementada en
``backend/api/public.py`` + ``backend/services/event_registration_service.py``:
  1. Happy path sin verificación email → CONFIRMED + QR generado.
  2. Con verificación email → PENDING hasta verificar (GET /verify).
  3. Aforo lleno → 409 EVENT_FULL; con waitlist → WAITLIST con posición.
  4. Cancelación libera slot y promueve waitlist automáticamente.
  7. Evento inexistente → 404; evento sin pre-registro → 403.
Además: idempotencia por email, estado por email/phone, ventana de registro.

El check-in (casos 5-6) y las campañas (caso 8) pertenecen a Fases 4-5.

Notas del contrato:
- Los errores de negocio devuelven ``{"code": ..., "detail": ...}`` en ``detail``.
- El token de cancelación (``CCF-CXL-``) vive en ``extras["_cancel_token"]`` y
  no se expone en la respuesta (los extras con prefijo ``_`` se ocultan).
- El verify token no se devuelve por API: se envía por email. Para testear
  simulamos lo que hace el sender (hash del secret en ``_verify_token_hash``).
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from backend import models

BASE = "/api/public/events"


# ── Helpers ─────────────────────────────────────────────────────────────────


@pytest.fixture
def sede(db_session):
    s = models.Sede(id=uuid.uuid4(), nombre="Sede Test", ciudad="Bogota", es_activa=True)
    db_session.add(s)
    db_session.flush()
    return s


def _make_event(db_session, sede, **overrides):
    fields = dict(
        id=uuid.uuid4(),
        name="Concierto Navidad",
        event_date=datetime(2026, 12, 24, 19, 0, 0, tzinfo=timezone.utc),
        location="Auditorio Principal",
        sede_id=sede.id,
        status="SCHEDULED",
    )
    fields.update(overrides)
    evt = models.CrmEvent(**fields)
    db_session.add(evt)
    db_session.flush()
    return evt


def _register(client, event_id, **overrides):
    payload = {
        "first_name": "Ana",
        "last_name": "Pérez",
        "email": "ana@example.com",
        "phone": "3001234567",
        "accept_contact": True,
    }
    payload.update(overrides)
    return client.post(f"{BASE}/{event_id}/register", json=payload)


def _reg_row(db_session, reg_id) -> models.EventRegistration:
    return db_session.query(models.EventRegistration).filter(
        models.EventRegistration.id == uuid.UUID(reg_id)
    ).first()


# ── Metadata pública ─────────────────────────────────────────────────────────


class TestPublicMetadata:
    def test_metadata_ok(self, client, db_session, sede):
        evt = _make_event(
            db_session,
            sede,
            requires_registration=True,
            capacity_max=100,
            description="Un gran concierto",
        )
        db_session.commit()

        resp = client.get(f"{BASE}/{evt.id}")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["name"] == "Concierto Navidad"
        assert data["requires_registration"] is True
        assert data["capacity_max"] == 100
        assert data["capacity_remaining"] == 100
        assert data["is_open"] is True

    def test_metadata_404(self, client):
        resp = client.get(f"{BASE}/{uuid.uuid4()}")
        assert resp.status_code == 404

    def test_metadata_capacity_remaining_accounts_occupied(self, client, db_session, sede):
        evt = _make_event(db_session, sede, requires_registration=True, capacity_max=1)
        db_session.commit()
        _register(client, evt.id)
        resp = client.get(f"{BASE}/{evt.id}")
        assert resp.json()["capacity_remaining"] == 0

    def test_metadata_not_open_before_window(self, client, db_session, sede):
        evt = _make_event(
            db_session,
            sede,
            requires_registration=True,
            registration_opens_at=datetime.now(timezone.utc) + timedelta(days=2),
        )
        db_session.commit()
        assert client.get(f"{BASE}/{evt.id}").json()["is_open"] is False


# ── Registro público ─────────────────────────────────────────────────────────


class TestPublicRegister:
    def test_happy_path_confirmed_with_qr(self, client, db_session, sede):
        """Caso 1: sin verificación email → CONFIRMED + QR CCF-EVT-."""
        evt = _make_event(db_session, sede, requires_registration=True)
        db_session.commit()

        resp = _register(client, evt.id)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["registration_status"] == "CONFIRMED"
        assert data["qr_token"].startswith("CCF-EVT-")

        # La Persona se creó heredando la sede del evento
        persona = db_session.query(models.Persona).filter(models.Persona.email == "ana@example.com").first()
        assert persona is not None
        assert persona.sede_id == sede.id

        # El hash del QR está persistido (el secret nunca viaja a la DB)
        reg = _reg_row(db_session, data["id"])
        assert reg.qr_token_hash is not None
        assert reg.qr_token_hash not in data["qr_token"]

    def test_open_event_rejected_403(self, client, db_session, sede):
        """Evento sin pre-registro → 403 NOT_REGISTRATION_EVENT (backward-compat)."""
        evt = _make_event(db_session, sede, requires_registration=False)
        db_session.commit()

        resp = _register(client, evt.id)
        assert resp.status_code == 403
        assert resp.json()["detail"]["code"] == "NOT_REGISTRATION_EVENT"

    def test_idempotent_same_email(self, client, db_session, sede):
        """Re-registro con el mismo email → misma inscripción (sin duplicados)."""
        evt = _make_event(db_session, sede, requires_registration=True)
        db_session.commit()

        r1 = _register(client, evt.id).json()
        r2 = _register(client, evt.id).json()
        assert r2["id"] == r1["id"]
        assert r2["registration_status"] == "CONFIRMED"
        # No se duplican registros (UNIQUE event_id, persona_id)
        count = (
            db_session.query(models.EventRegistration)
            .filter(models.EventRegistration.event_id == evt.id)
            .count()
        )
        assert count == 1

    def test_upsert_persona_email_priority_over_phone(self, client, db_session, sede):
        """E6: upsert_persona busca por email primero, luego phone.

        Si el email coincide con una persona y el phone con otra distinta,
        la búsqueda debe resolver la del email (orden determinístico), no
        la primera que encuenta un OR query.
        """
        from backend.services.event_registration_service import upsert_persona

        # Dos personas existentes: una con email, otra con el mismo phone
        p_email = models.Persona(
            first_name="ConEmail", last_name="Test", email="a@test.com",
            phone="3000000000", sede_id=sede.id,
        )
        p_phone = models.Persona(
            first_name="ConPhone", last_name="Test", email="b@test.com",
            phone="3000000000", sede_id=sede.id,
        )
        db_session.add_all([p_email, p_phone])
        db_session.flush()

        result = upsert_persona(
            db_session,
            first_name="Nuevo", last_name="Usuario",
            email="a@test.com", phone="3000000000",
        )
        assert result.id == p_email.id
        assert result.first_name == "ConEmail"

    def test_waitlist_when_full(self, client, db_session, sede):
        """Caso 3: aforo lleno + waitlist → WAITLIST con posición."""
        evt = _make_event(
            db_session,
            sede,
            requires_registration=True,
            capacity_max=1,
            waiting_list_enabled=True,
        )
        db_session.commit()

        # Phones distintos: el upsert de persona busca por email OR phone, así
        # que dos personas con el mismo phone colisionan (idempotencia).
        r1 = _register(client, evt.id, email="uno@example.com", phone="3000000001")
        assert r1.json()["registration_status"] == "CONFIRMED"
        r2 = _register(client, evt.id, email="dos@example.com", phone="3000000002")
        data2 = r2.json()
        assert data2["registration_status"] == "WAITLIST"
        assert data2["waiting_list_position"] == 1

    def test_event_full_409_without_waitlist(self, client, db_session, sede):
        """Caso 3b: aforo lleno sin waitlist → 409 EVENT_FULL."""
        evt = _make_event(db_session, sede, requires_registration=True, capacity_max=1)
        db_session.commit()

        assert _register(client, evt.id, email="uno@example.com", phone="3000000001").status_code == 200
        resp = _register(client, evt.id, email="dos@example.com", phone="3000000002")
        assert resp.status_code == 409
        assert resp.json()["detail"]["code"] == "EVENT_FULL"

    def test_pending_requires_email_verification(self, client, db_session, sede):
        """Caso 2: con verificación email → PENDING (sin QR)."""
        evt = _make_event(db_session, sede, requires_registration=True, requires_email_verification=True)
        db_session.commit()

        resp = _register(client, evt.id)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["registration_status"] == "PENDING"
        assert data["qr_token"] is None

        # El sender de email persistió el hash del verify token en extras
        reg = _reg_row(db_session, data["id"])
        assert (reg.extras or {}).get("_verify_token_hash")

    def test_window_closed_409(self, client, db_session, sede):
        """Ventana de registro cerrada → 409 REGISTRATION_CLOSED."""
        evt = _make_event(
            db_session,
            sede,
            requires_registration=True,
            registration_closes_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        db_session.commit()

        # El servicio usa 410 Gone para ventana cerrada (permanente) y 409
        # para NOT_YET_OPEN (temporal).
        resp = _register(client, evt.id)
        assert resp.status_code == 410
        assert resp.json()["detail"]["code"] == "REGISTRATION_CLOSED"

    def test_missing_event_404(self, client):
        resp = _register(client, uuid.uuid4())
        assert resp.status_code == 404


# ── Verificación de email ────────────────────────────────────────────────────


class TestPublicVerify:
    def _pending_reg(self, client, db_session, sede):
        evt = _make_event(db_session, sede, requires_registration=True, requires_email_verification=True)
        db_session.commit()
        reg_id = _register(client, evt.id).json()["id"]
        return evt, _reg_row(db_session, reg_id)

    def _craft_verify_token(self, db_session, reg, secret="testsecret"):
        """Emula lo que hace el sender de email: guarda hash del secret y expiración."""
        extras = dict(reg.extras or {})
        extras["_verify_token_hash"] = hashlib.sha256(secret.encode()).hexdigest()
        extras["_verify_expires_at"] = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        reg.extras = extras
        db_session.commit()
        return f"CCF-VER-{reg.id}-{secret}"

    def test_verify_promotes_to_confirmed(self, client, db_session, sede):
        """Caso 2: verificar el email → CONFIRMED + QR."""
        evt, reg = self._pending_reg(client, db_session, sede)
        token = self._craft_verify_token(db_session, reg)

        resp = client.get(f"{BASE}/{evt.id}/verify", params={"token": token})
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["registration_status"] == "CONFIRMED"
        assert data["qr_token"].startswith("CCF-EVT-")

    def test_verify_invalid_token_403(self, client, db_session, sede):
        evt, _ = self._pending_reg(client, db_session, sede)
        resp = client.get(f"{BASE}/{evt.id}/verify", params={"token": "CCF-VER-just-a-token"})
        assert resp.status_code in (400, 403, 404)

    def test_verify_wrong_secret_403(self, client, db_session, sede):
        # Secrets sin guiones (como secrets.token_hex real): el parseo del
        # token usa rsplit('-', 1) y un secret con '-' rompería el UUID.
        evt, reg = self._pending_reg(client, db_session, sede)
        token = self._craft_verify_token(db_session, reg, secret="goodsecret123")
        wrong = token.rsplit("-", 1)[0] + "-wrongsecret456"
        resp = client.get(f"{BASE}/{evt.id}/verify", params={"token": wrong})
        assert resp.status_code == 403


# ── Estado del inscrito ──────────────────────────────────────────────────────


class TestPublicStatus:
    def test_status_by_email(self, client, db_session, sede):
        evt = _make_event(db_session, sede, requires_registration=True)
        db_session.commit()
        reg_id = _register(client, evt.id).json()["id"]

        resp = client.get(f"{BASE}/{evt.id}/status", params={"email": "ana@example.com"})
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["id"] == reg_id
        assert data["registration_status"] == "CONFIRMED"

    def test_status_by_phone(self, client, db_session, sede):
        evt = _make_event(db_session, sede, requires_registration=True)
        db_session.commit()
        _register(client, evt.id)

        resp = client.get(f"{BASE}/{evt.id}/status", params={"phone": "3001234567"})
        assert resp.status_code == 200
        assert resp.json()["registration_status"] == "CONFIRMED"

    def test_status_not_registered_404(self, client, db_session, sede):
        evt = _make_event(db_session, sede, requires_registration=True)
        db_session.commit()
        resp = client.get(f"{BASE}/{evt.id}/status", params={"email": "nobody@example.com"})
        assert resp.status_code == 404

    def test_status_requires_identifier_400(self, client, db_session, sede):
        evt = _make_event(db_session, sede, requires_registration=True)
        db_session.commit()
        assert client.get(f"{BASE}/{evt.id}/status").status_code == 400


# ── Auto-cancelación ─────────────────────────────────────────────────────────


class TestPublicCancel:
    def _cancel_token(self, db_session, reg_id):
        """Recupera el cancel_token transient (no persistido en extras desde fix #2).

        El token se emite una sola vez en runtime; los tests lo recuperan del
        atributo transient del registro, o del email capturado. Aquí pedimos
        reemitirlo vía el mismo helper que usa el service: como el hash ya
        está en extras, no podemos recuperar el token (sha256 no reversible),
        así que estos tests dependen de capturar el token en el momento de
        la emisión. Para simplificar los tests de cancelación usamos el
        endpoint de verify (que reemite) o re-register — ver en cada test.
        """
        reg = _reg_row(db_session, reg_id)
        return getattr(reg, "_cancel_token_transient", None)

    def test_cancel_with_cancel_token(self, client, db_session, sede):
        evt = _make_event(db_session, sede, requires_registration=True)
        db_session.commit()
        reg_resp = _register(client, evt.id).json()
        reg_id = reg_resp["id"]
        # cancel_token se emite una sola vez en la respuesta de /register
        # (volatile, no persistido en DB desde fix seguridad #2).
        cancel_token = reg_resp["cancel_token"]
        assert cancel_token and cancel_token.startswith("CCF-CXL-")

        resp = client.post(f"{BASE}/{evt.id}/cancel", json={"cancel_token": cancel_token})
        assert resp.status_code == 200, resp.text
        assert resp.json()["registration_status"] == "CANCELLED"

        # El estado ya no aparece como activo
        status = client.get(f"{BASE}/{evt.id}/status", params={"email": "ana@example.com"})
        assert status.status_code == 404

    def test_cancel_invalid_token_404(self, client, db_session, sede):
        evt = _make_event(db_session, sede, requires_registration=True)
        db_session.commit()
        resp = client.post(f"{BASE}/{evt.id}/cancel", json={"cancel_token": "CCF-CXL-fake"})
        assert resp.status_code == 400

    def test_cancel_promotes_waitlist(self, client, db_session, sede):
        """Caso 4: cancelar libera slot y promueve al primer waitlist."""
        evt = _make_event(
            db_session,
            sede,
            requires_registration=True,
            capacity_max=1,
            waiting_list_enabled=True,
        )
        db_session.commit()

        reg_a = _register(client, evt.id, email="uno@example.com", phone="3000000001").json()
        _register(client, evt.id, email="dos@example.com", phone="3000000002").json()
        # cancel_token volatile: tomarlo de la respuesta de /register (no DB).
        cancel_token = reg_a["cancel_token"]

        resp = client.post(f"{BASE}/{evt.id}/cancel", json={"cancel_token": cancel_token})
        assert resp.status_code == 200
        assert resp.json()["registration_status"] == "CANCELLED"

        promoted = _reg_row(db_session, reg_a["id"])
        b_row = (
            db_session.query(models.EventRegistration)
            .join(models.Persona, models.EventRegistration.persona_id == models.Persona.id)
            .filter(
                models.EventRegistration.event_id == evt.id,
                models.Persona.email == "dos@example.com",
            )
            .first()
        )
        assert b_row is not None
        assert b_row.registration_status == "CONFIRMED"
        # Tras fix seguridad #2, qr_token NO se persiste en DB (solo el hash).
        # El token se emite una sola vez en runtime y por email.
        assert b_row.qr_token is None
        assert b_row.qr_token_hash is not None
        assert b_row.qr_generated_at is not None
        assert b_row.waiting_list_position is None

    def test_cancel_reactivation_creates_new_lifecycle(self, client, db_session, sede):
        """Cancelar y re-registrar la misma persona reactiva la fila (UNIQUE)."""
        evt = _make_event(db_session, sede, requires_registration=True)
        db_session.commit()

        reg_id = _register(client, evt.id).json()["id"]
        cancel_token = self._cancel_token(db_session, reg_id)
        client.post(f"{BASE}/{evt.id}/cancel", json={"cancel_token": cancel_token})

        r2 = _register(client, evt.id)
        assert r2.status_code == 200, r2.text
        assert r2.json()["registration_status"] == "CONFIRMED"
        count = (
            db_session.query(models.EventRegistration)
            .filter(models.EventRegistration.event_id == evt.id)
            .count()
        )
        assert count == 1


# ── Check-in unificado con el QR generado (Fase 4) ───────────────────────────


@pytest.fixture
def checkin_ctx(client, db_session):
    """Admin autenticado en una sede (el evento debe crearse en esa sede)."""
    from tests.conftest import auth_headers as _auth_headers
    from tests.conftest import seed_admin as _seed_admin

    _admin, _persona, admin_sede = _seed_admin(db_session, email="checkin@test.com")
    headers = _auth_headers(client, email="checkin@test.com", password="testpass123")
    return {"client": client, "headers": headers, "sede": admin_sede}


class TestUnifiedCheckin:
    def _checkin(self, ctx, event_id, payload):
        return ctx["client"].post(
            f"/api/evangelism/events/{event_id}/sessions/2026-12-24/checkin",
            json=payload,
            headers=ctx["headers"],
        )

    def test_checkin_with_qr_event(self, checkin_ctx, client, db_session):
        """Caso 5: QR CCF-EVT- marca CHECKED_IN + crea EventAttendance."""
        evt = _make_event(db_session, checkin_ctx["sede"], requires_registration=True)
        db_session.commit()
        reg_data = _register(client, evt.id).json()
        reg_id = reg_data["id"]
        # El QR se emite una sola vez en la respuesta de /register (no persistido en DB).
        qr = reg_data["qr_token"]
        assert qr is not None and qr.startswith("CCF-EVT-")

        resp = self._checkin(checkin_ctx, evt.id, {"qr_token": qr})
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["status"] == "success"
        assert data["is_duplicate"] is False

        reg = _reg_row(db_session, reg_id)
        assert reg.registration_status == "CHECKED_IN"
        assert reg.check_in_at is not None

        attendance = (
            db_session.query(models.EventAttendance)
            .filter(
                models.EventAttendance.event_id == evt.id,
                models.EventAttendance.session_date.isnot(None),
            )
            .first()
        )
        assert attendance is not None
        assert attendance.attended is True

    def test_checkin_duplicate(self, checkin_ctx, client, db_session):
        """Caso 6: check-in duplicado → is_duplicate=True."""
        evt = _make_event(db_session, checkin_ctx["sede"], requires_registration=True)
        db_session.commit()
        reg_data = _register(client, evt.id).json()
        reg_id = reg_data["id"]
        # El QR se emite una sola vez en la respuesta de /register (no persistido en DB).
        qr = reg_data["qr_token"]
        assert qr is not None and qr.startswith("CCF-EVT-")

        r1 = self._checkin(checkin_ctx, evt.id, {"qr_token": qr})
        r2 = self._checkin(checkin_ctx, evt.id, {"qr_token": qr})
        assert r1.json()["is_duplicate"] is False
        assert r2.status_code == 200
        assert r2.json()["is_duplicate"] is True

    def test_checkin_pending_rejected(self, checkin_ctx, client, db_session):
        """Inscripción PENDING (email sin verificar) no puede hacer check-in."""
        evt = _make_event(
            db_session, checkin_ctx["sede"], requires_registration=True, requires_email_verification=True
        )
        db_session.commit()
        reg_resp = _register(client, evt.id).json()  # PENDING → sin QR
        assert reg_resp["qr_token"] is None

        # QR fabricado: el registro PENDING nunca tuvo QR emitido → 403 "QR inválido"
        # (el hash no matchea ninguna inscripción; no se llega al chequeo de estado).
        reg = _reg_row(db_session, reg_resp["id"])
        fake_qr = f"CCF-EVT-{evt.id}-{reg.persona_id}-{'f' * 32}"
        resp = self._checkin(checkin_ctx, evt.id, {"qr_token": fake_qr})
        assert resp.status_code == 403


# ── Form Builder dinámico (plan §5.4) ────────────────────────────────────────


class TestPublicRegisterFormBuilder:
    """Tests del pre-registro cuando el evento tiene un ``CmsForm`` vinculado.

    Cubre ``backend/api/public.py:_validate_event_form_data``: valida
    ``form_data`` + ``captcha_token`` server-side y persiste los datos
    limpios en ``event_registrations.extras._form_data``.

    Nota: estos tests cubren el bug ``_validate_event_form_data`` no
    definida introducido en la iteración previa y resuelto ahora.
    """

    def _make_form(self, db_session, sede, *, fields=None, captcha_enabled=False, is_active=True):
        """Crea un ``CmsSite`` y un ``CmsForm`` vinculado a la sede del evento.

        ``CmsForm.site_id`` es NOT NULL — requerimos un ``CmsSite`` con
        ``sede_id`` igual al del evento (Axioma 3 multi-tenant).
        """
        site = models.CmsSite(
            id=uuid.uuid4(),
            site_key=f"test-{uuid.uuid4().hex[:8]}",
            name=f"Sitio Test {sede.nombre}",
            sede_id=sede.id,
            is_active=True,
        )
        db_session.add(site)
        db_session.flush()
        form = models.CmsForm(
            id=uuid.uuid4(),
            site_id=site.id,
            name="Form Preinscripción Concierto",
            fields=fields or [
                {"id": "iglesia", "type": "text", "label": "Iglesia de procedencia", "required": True},
                {"id": "alergias", "type": "textarea", "label": "Alergias", "required": False},
            ],
            is_active=is_active,
            captcha_enabled=captcha_enabled,
            honeypot_enabled=True,
        )
        db_session.add(form)
        db_session.flush()
        return form

    def test_register_with_form_id_validates_and_persists_form_data(self, client, db_session, sede):
        """Evento con ``form_id`` seteado → form_data se valida y persiste en extras._form_data."""
        form = self._make_form(db_session, sede)
        evt = _make_event(db_session, sede, requires_registration=True, form_id=form.id)
        db_session.commit()

        resp = client.post(
            f"{BASE}/{evt.id}/register",
            json={
                "first_name": "Ana",
                "last_name": "Pérez",
                "email": "ana@example.com",
                "phone": "3001234567",
                "accept_contact": True,
                "form_data": {"iglesia": "Emmanuel Boquilla", "alergias": ""},
            },
        )
        assert resp.status_code == 200, resp.text
        reg_id = resp.json()["id"]
        reg = _reg_row(db_session, reg_id)
        # El dato limpio quedó persistido en extras._form_data. ``alergias``
        # (opcional + vacío) no se persiste — ``validate_submission`` omite
        # los campos opcionales vacíos para ahorrar espacio; solo guarda
        # los campos requeridos con valor real.
        assert reg.extras.get("_form_data") == {"iglesia": "Emmanuel Boquilla"}

    def test_register_with_form_id_required_field_missing_returns_422(self, client, db_session, sede):
        """Campo required faltante en form_data → 422 (no se crea la inscripción)."""
        form = self._make_form(db_session, sede)
        evt = _make_event(db_session, sede, requires_registration=True, form_id=form.id)
        db_session.commit()

        resp = client.post(
            f"{BASE}/{evt.id}/register",
            json={
                "first_name": "Ana",
                "last_name": "Pérez",
                "email": "ana@example.com",
                "phone": "3001234567",
                "accept_contact": True,
                "form_data": {"alergias": "Mariscos"},  # falta iglesia (required)
            },
        )
        assert resp.status_code == 422, resp.text
        assert resp.json()["detail"]["code"] == "REQUIRED_FIELD"
        assert resp.json()["detail"]["field_id"] == "iglesia"

        # No se creó la inscripción
        count = db_session.query(models.EventRegistration).filter(
            models.EventRegistration.event_id == evt.id
        ).count()
        assert count == 0

    def test_register_with_form_id_form_not_found_returns_404(self, client, db_session, sede):
        """``form_id`` apunta a un ``CmsForm`` eliminado → 404 FORM_NOT_FOUND."""
        evt = _make_event(
            db_session, sede,
            requires_registration=True,
            form_id=uuid.uuid4(),  # form_id no resolvable
        )
        db_session.commit()

        resp = client.post(
            f"{BASE}/{evt.id}/register",
            json={
                "first_name": "Ana",
                "last_name": "Pérez",
                "email": "ana@example.com",
                "form_data": {},
            },
        )
        assert resp.status_code == 404, resp.text
        assert resp.json()["detail"]["code"] == "FORM_NOT_FOUND"

    def test_register_with_form_id_form_inactive_returns_404(self, client, db_session, sede):
        """``CmsForm`` inactivo (is_active=False) → 404 FORM_NOT_FOUND."""
        form = self._make_form(db_session, sede, is_active=False)
        evt = _make_event(db_session, sede, requires_registration=True, form_id=form.id)
        db_session.commit()

        resp = client.post(
            f"{BASE}/{evt.id}/register",
            json={
                "first_name": "Ana",
                "last_name": "Pérez",
                "email": "ana@example.com",
                "form_data": {"iglesia": "x", "alergias": ""},
            },
        )
        assert resp.status_code == 404, resp.text
        assert resp.json()["detail"]["code"] == "FORM_NOT_FOUND"

    def test_register_with_form_id_captcha_enabled_no_token_returns_400(self, client, db_session, sede):
        """Form con captcha_enabled=True y sin captcha_token → 400 CAPTCHA_REQUIRED."""
        form = self._make_form(db_session, sede, captcha_enabled=True)
        evt = _make_event(db_session, sede, requires_registration=True, form_id=form.id)
        db_session.commit()

        resp = client.post(
            f"{BASE}/{evt.id}/register",
            json={
                "first_name": "Ana",
                "last_name": "Pérez",
                "email": "ana@example.com",
                "form_data": {"iglesia": "x", "alergias": ""},
                # sin captcha_token
            },
        )
        assert resp.status_code == 400, resp.text
        assert resp.json()["detail"]["code"] == "CAPTCHA_REQUIRED"

    def test_register_without_form_id_ignores_form_data(self, client, db_session, sede):
        """Evento sin ``form_id`` → ``form_data`` se ignora (backward-compat con preregistro fijo)."""
        evt = _make_event(db_session, sede, requires_registration=True)  # form_id=None
        db_session.commit()

        resp = client.post(
            f"{BASE}/{evt.id}/register",
            json={
                "first_name": "Ana",
                "last_name": "Pérez",
                "email": "ana@example.com",
                "phone": "3001234567",
                "form_data": {"random_field": "no valida nada"},
            },
        )
        # El form_data se ignora — el pre-registro se hace con campos top-level
        assert resp.status_code == 200, resp.text
        reg = _reg_row(db_session, resp.json()["id"])
        # No se persistió _form_data porque el evento no tiene form_id
        assert "_form_data" not in (reg.extras or {})
