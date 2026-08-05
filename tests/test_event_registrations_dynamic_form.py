"""Tests del pre-registro con formulario dinámico vinculado (plan_de_form_builder).

Cuando ``CrmEvent.form_id`` está seteado, ``POST /public/events/{id}/register``
valida ``form_data`` + ``captcha_token`` contra el ``CmsForm`` vinculado
(``backend.api.public._validate_event_form_data``) y persiste los datos limpios
en ``extras["_form_data"]``.

Cubre:
  - Sin form_id → regresión del formulario fijo (funciona como antes).
  - Con form_id + form_data válido → CONFIRMED + extras._form_data persistido.
  - form_data inválido (required, tipo) → 422.
  - captcha habilitado: requerido (400) / válido (éxito) con mock.
  - honeypot rellenado → 200 silencioso sin crear inscripción.
  - formulario inactivo/eliminado → 404.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from backend import models

BASE = "/api/public/events"


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
        requires_registration=True,
    )
    fields.update(overrides)
    evt = models.CrmEvent(**fields)
    db_session.add(evt)
    db_session.flush()
    return evt


def _make_form(db_session, sede, **overrides):
    fields = dict(
        id=uuid.uuid4(),
        site_id=uuid.uuid4(),  # el render público no valida sitio en este flujo
        name="Preguntas del evento",
        fields=[
            {"id": "iglesia", "type": "select", "label": "¿Iglesia?", "options": ["Central", "Norte", "Otra"]},
            {"id": "asistio", "type": "checkbox", "label": "¿Asistió antes?"},
            {"id": "edad", "type": "number", "label": "Edad", "min_value": 0, "max_value": 120},
        ],
        captcha_enabled=False,
        honeypot_enabled=True,
        is_active=True,
    )
    fields.update(overrides)
    form = models.CmsForm(**fields)
    db_session.add(form)
    db_session.flush()
    return form


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


class TestEventWithDynamicForm:
    def test_register_with_form_data_valid(self, client, db_session, sede):
        form = _make_form(db_session, sede)
        evt = _make_event(db_session, sede, form_id=form.id)
        db_session.commit()

        resp = _register(
            client,
            evt.id,
            form_data={"iglesia": "Central", "asistio": True, "edad": 30},
        )
        assert resp.status_code in (200, 201), resp.text
        body = resp.json()
        assert body["registration_status"] == "CONFIRMED"

        reg = db_session.query(models.EventRegistration).filter(
            models.EventRegistration.id == uuid.UUID(body["id"])
        ).first()
        assert reg is not None
        assert reg.extras["_form_data"] == {"iglesia": "Central", "asistio": True, "edad": 30}

    def test_register_form_data_missing_required_422(self, client, db_session, sede):
        form = _make_form(
            db_session,
            sede,
            fields=[
                {"id": "nombre_extra", "type": "text", "label": "Extra", "required": True},
            ],
        )
        evt = _make_event(db_session, sede, form_id=form.id)
        db_session.commit()

        resp = _register(client, evt.id, form_data={})
        assert resp.status_code == 422, resp.text
        assert resp.json()["detail"]["code"] == "REQUIRED_FIELD"

    def test_register_form_data_invalid_type_422(self, client, db_session, sede):
        form = _make_form(db_session, sede)
        evt = _make_event(db_session, sede, form_id=form.id)
        db_session.commit()

        resp = _register(client, evt.id, form_data={"iglesia": "Central", "edad": "treinta"})
        assert resp.status_code == 422, resp.text
        assert resp.json()["detail"]["code"] == "INVALID_NUMBER"

    def test_register_form_data_invalid_option_422(self, client, db_session, sede):
        form = _make_form(db_session, sede)
        evt = _make_event(db_session, sede, form_id=form.id)
        db_session.commit()

        resp = _register(client, evt.id, form_data={"iglesia": "No existe"})
        assert resp.status_code == 422, resp.text
        assert resp.json()["detail"]["code"] == "INVALID_OPTION"

    def test_register_no_form_id_regression(self, client, db_session, sede):
        evt = _make_event(db_session, sede, form_id=None)
        db_session.commit()

        resp = _register(client, evt.id)
        assert resp.status_code in (200, 201), resp.text
        assert resp.json()["registration_status"] == "CONFIRMED"

    def test_register_form_inactive_404(self, client, db_session, sede):
        form = _make_form(db_session, sede, is_active=False)
        evt = _make_event(db_session, sede, form_id=form.id)
        db_session.commit()

        resp = _register(client, evt.id, form_data={"iglesia": "Central"})
        assert resp.status_code == 404

    def test_register_with_honeypot_enabled_form(self, client, db_session, sede):
        """El preregistro NO aplica honeypot (diseño §5.4: captcha + rate-limit).

        El renderer nunca envía ``_hp`` para humanos, así que un formulario con
        ``honeypot_enabled=True`` no bloquea el preregistro legítimo.
        """
        form = _make_form(db_session, sede, honeypot_enabled=True)
        evt = _make_event(db_session, sede, form_id=form.id)
        db_session.commit()

        resp = _register(client, evt.id, form_data={"iglesia": "Central"})
        assert resp.status_code in (200, 201), resp.text
        assert resp.json()["registration_status"] == "CONFIRMED"

    def test_register_captcha_required_400(self, client, db_session, sede):
        form = _make_form(db_session, sede, captcha_enabled=True)
        evt = _make_event(db_session, sede, form_id=form.id)
        db_session.commit()

        resp = _register(client, evt.id, form_data={"iglesia": "Central"})
        assert resp.status_code == 400, resp.text
        assert resp.json()["detail"]["code"] == "CAPTCHA_REQUIRED"

    @pytest.mark.parametrize("token,expected", [("bad-token", 400), ("good-token", 200)])
    def test_register_captcha_verified(self, client, db_session, sede, monkeypatch, token, expected):
        from backend.api import public as public_module

        async def _fake_verify(captcha_token, *, remote_ip=None):
            return captcha_token == "good-token"

        monkeypatch.setattr(public_module, "verify_hcaptcha", _fake_verify)
        form = _make_form(db_session, sede, captcha_enabled=True)
        evt = _make_event(db_session, sede, form_id=form.id)
        db_session.commit()

        resp = _register(
            client,
            evt.id,
            form_data={"iglesia": "Central"},
            captcha_token=token,
        )
        assert resp.status_code == expected, resp.text
        if expected == 400:
            assert resp.json()["detail"]["code"] == "CAPTCHA_FAILED"

    def test_register_persists_form_data_in_extras(self, client, db_session, sede):
        """Los extras con prefijo ``_`` no se exponen en la respuesta pública."""
        form = _make_form(db_session, sede)
        evt = _make_event(db_session, sede, form_id=form.id)
        db_session.commit()

        resp = _register(client, evt.id, form_data={"iglesia": "Norte"})
        assert resp.status_code in (200, 201), resp.text
        body = resp.json()
        assert "_form_data" not in body["extras"]
        assert body["registration_status"] == "CONFIRMED"


class TestEventFormIdInMetadata:
    def test_public_metadata_exposes_form_id(self, client, db_session, sede):
        form = _make_form(db_session, sede)
        evt = _make_event(db_session, sede, form_id=form.id)
        db_session.commit()

        resp = client.get(f"{BASE}/{evt.id}")
        assert resp.status_code == 200, resp.text
        assert resp.json()["form_id"] == str(form.id)

    def test_public_metadata_form_id_null_without_form(self, client, db_session, sede):
        evt = _make_event(db_session, sede, form_id=None)
        db_session.commit()

        resp = client.get(f"{BASE}/{evt.id}")
        assert resp.status_code == 200, resp.text
        assert resp.json()["form_id"] is None
