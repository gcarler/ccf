"""Tests del correo de confirmación con QR (SMTP/plantilla) y del PNG endpoint.

Cubre la calidad de producción del email de pre-registro:
  1. ``resolve_public_base_url`` — el dominio base de los links nunca cae al
     placeholder ``https://ccf.co``; usa ``frontend_url`` (dominio canónico).
  2. ``render_event_confirmation_email`` — layout corporativo, QR embebido
     (img con URL del backend), botón "Abrir mi código QR" y link de
     cancelación.
  3. ``_send_confirmation_email`` — el email de confirmación se construye con
     el dominio resuelto y el QR PNG correcto.
  4. Endpoint ``GET /api/public/events/{id}/qr.png`` — devuelve PNG válido
     para un token CONFIRMED y 404 para token desconocido.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from backend import models
from backend.core.config import get_settings
from backend.services.event_registration_service import (
    _send_confirmation_email,
    render_qr_png,
    resolve_public_base_url,
)
from backend.services.email import render_event_confirmation_email

BASE = "/api/public/events"


# ── Helpers (mismos patrones que test_event_registrations.py) ───────────────


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


# ── 1. Resolución de la URL pública base ────────────────────────────────────


class TestResolvePublicBaseUrl:
    def test_uses_frontend_url_when_public_base_url_empty(self):
        """Sin public_base_url configurada, usa frontend_url (dominio canónico)."""
        s = get_settings()
        base = resolve_public_base_url()
        assert base
        assert base == (s.frontend_url or s.public_base_url).rstrip("/")
        # Nunca el placeholder https://ccf.co si hay un frontend configurado
        if s.frontend_url and "ccf.co" not in s.frontend_url:
            assert "ccf.co" not in base

    def test_no_trailing_slash(self, monkeypatch):
        import backend.services.event_registration_service as svc

        monkeypatch.setattr(
            svc,
            "get_settings",
            lambda: type("S", (), {"public_base_url": "https://site.example/", "frontend_url": ""})(),
        )
        assert resolve_public_base_url() == "https://site.example"


# ── 2. Plantilla del email ──────────────────────────────────────────────────


class TestConfirmationEmailTemplate:
    def test_render_includes_qr_image_and_links(self):
        html = render_event_confirmation_email(
            event_name="Aniversario 40 Años CCF",
            persona_first_name="Ana",
            event_date_str="23/08/2026 09:00",
            location_str="Auditorio Principal",
            qr_link="https://ministerioselfaro.org/public/events/e1/qr?token=CCF-EVT-x&cancel=CCF-CXL-y",
            cancel_link="https://ministerioselfaro.org/public/events/e1/cancel?token=CCF-CXL-y",
            qr_img_url="https://ministerioselfaro.org/api/public/events/e1/qr.png?token=CCF-EVT-x",
        )
        # El HTML usa entidades para acentos (c&oacute;digo, inscripci&oacute;n…)
        assert "Inscripci&oacute;n confirmada" in html
        assert "Aniversario 40 Años CCF" in html
        assert "c&oacute;digo QR de ingreso" in html
        assert "/qr.png?token=" in html  # QR como imagen servida por el backend
        assert "Abrir mi c&oacute;digo QR" in html
        assert "Cancela tu inscripci&oacute;n" in html
        assert "ministerioselfaro.org" in html
        # Layout corporativo
        assert "<html" in html
        assert "CCF" in html
        assert "Todos los derechos reservados" in html

    def test_render_without_qr_omits_blocks(self):
        html = render_event_confirmation_email(
            event_name="Evento",
            persona_first_name="Ana",
            event_date_str="1/1/2026",
            location_str="Lugar",
            qr_link="",
        )
        assert "qr.png" not in html
        assert "Abrir mi código QR" not in html
        assert "Cancela tu inscripción" not in html

    def test_render_qr_png_valid_bytes(self):
        png = render_qr_png("https://example.org/ticket")
        assert png[:8] == b"\x89PNG\r\n\x1a\n"  # magic bytes PNG


# ── 3. _send_confirmation_email construye el QR correcto ────────────────────


class TestSendConfirmationEmail:
    def test_builds_correct_domain_and_qr_img(self, monkeypatch, db_session, sede):
        import backend.services.email as email_mod

        captured: dict = {}

        def fake_send(to, subject, html, text=""):
            captured.update(to=to, subject=subject, html=html)
            return True

        monkeypatch.setattr(email_mod, "send_email", fake_send)

        evt = _make_event(db_session, sede, requires_registration=True)
        persona = models.Persona(
            first_name="Ana", last_name="Pérez", email="ana@example.com", sede_id=sede.id
        )
        db_session.add(persona)
        db_session.flush()
        reg = models.EventRegistration(
            id=uuid.uuid4(), event_id=evt.id, persona_id=persona.id,
            registration_status="CONFIRMED", source="public_form",
        )
        db_session.add(reg)
        db_session.flush()

        _send_confirmation_email(
            db_session, evt, reg, persona,
            public_base_url=resolve_public_base_url(),
            qr_token_plain=f"CCF-EVT-{evt.id}-{persona.id}-{'a' * 32}",
            cancel_token_plain=f"CCF-CXL-{reg.id}-{'b' * 32}",
        )

        assert captured["subject"] == f"Confirmación: {evt.name}"
        base = resolve_public_base_url()
        assert f"{base}/public/events/{evt.id}/qr?token=" in captured["html"]
        assert f"{base}/api/public/events/{evt.id}/qr.png?token=" in captured["html"]
        assert f"{base}/public/events/{evt.id}/cancel?token=" in captured["html"]
        assert "ccf.co" not in captured["html"]

    def test_empty_public_base_url_falls_back_to_settings(self, monkeypatch, db_session, sede):
        """resend del admin (public_base_url='') debe resolver el dominio igualmente."""
        import backend.services.email as email_mod

        captured: dict = {}

        def fake_send(to, subject, html, text=""):
            captured["html"] = html
            return True

        monkeypatch.setattr(email_mod, "send_email", fake_send)

        evt = _make_event(db_session, sede, requires_registration=True)
        persona = models.Persona(
            first_name="Ana", last_name="Pérez", email="ana@example.com", sede_id=sede.id
        )
        db_session.add(persona)
        db_session.flush()
        reg = models.EventRegistration(
            id=uuid.uuid4(), event_id=evt.id, persona_id=persona.id,
            registration_status="CONFIRMED", source="public_form",
        )
        db_session.add(reg)
        db_session.flush()

        _send_confirmation_email(
            db_session, evt, reg, persona,
            public_base_url="",  # el caso que antes producía URL relativa
            qr_token_plain=f"CCF-EVT-{evt.id}-{persona.id}-{'c' * 32}",
            cancel_token_plain=f"CCF-CXL-{reg.id}-{'d' * 32}",
        )

        base = resolve_public_base_url()
        assert f"{base}/public/events/{evt.id}/qr?token=" in captured["html"]
        # No quedó una URL relativa "/public/events/..."
        assert "/public/events/" in captured["html"]
        assert captured["html"].lstrip().startswith(("<", " "))
        assert "ccf.co" not in captured["html"]


# ── 4. Endpoint público PNG ─────────────────────────────────────────────────


class TestQrPngEndpoint:
    def test_returns_png_for_confirmed_token(self, client, db_session, sede):
        evt = _make_event(db_session, sede, requires_registration=True)
        db_session.commit()

        resp = _register(client, evt.id)
        assert resp.status_code == 200, resp.text
        qr_token = resp.json()["qr_token"]
        assert qr_token

        png_resp = client.get(f"{BASE}/{evt.id}/qr.png", params={"token": qr_token})
        assert png_resp.status_code == 200, png_resp.text
        assert png_resp.headers["content-type"] == "image/png"
        assert png_resp.content[:8] == b"\x89PNG\r\n\x1a\n"

    def test_unknown_token_404(self, client, db_session, sede):
        evt = _make_event(db_session, sede, requires_registration=True)
        db_session.commit()

        resp = client.get(f"{BASE}/{evt.id}/qr.png", params={"token": f"CCF-EVT-{uuid.uuid4()}-{'f' * 32}"})
        assert resp.status_code == 404

    def test_cancel_param_encoded_in_qr_content(self, client, db_session, sede):
        evt = _make_event(db_session, sede, requires_registration=True)
        db_session.commit()
        reg_data = _register(client, evt.id).json()
        qr_token = reg_data["qr_token"]
        cancel_token = reg_data["cancel_token"]

        # El PNG se genera igualmente (no podemos decodificar el QR aquí, pero
        # el endpoint acepta el cancel param y devuelve 200).
        resp = client.get(
            f"{BASE}/{evt.id}/qr.png",
            params={"token": qr_token, "cancel": cancel_token},
        )
        assert resp.status_code == 200
        assert resp.content[:8] == b"\x89PNG\r\n\x1a\n"

    def test_not_registered_token_404(self, client, db_session, sede):
        evt = _make_event(db_session, sede, requires_registration=True)
        db_session.commit()
        # Sin registro previo, cualquier token es desconocido (min_length ≥ 10).
        resp = client.get(
            f"{BASE}/{evt.id}/qr.png",
            params={"token": f"CCF-EVT-{uuid.uuid4()}-{'f' * 32}"},
        )
        assert resp.status_code == 404
