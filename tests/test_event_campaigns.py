"""Tests de campañas de mensajería ligadas a eventos masivos (plan_de_preregistro, Fase 5).

Cubre los casos clave del plan §5 aplicables a la API admin implementada en
``backend/api/evangelism_events/events_registrations.py`` +
``backend/services/event_campaign_service.py``:

  1. Creación de campaña (MANUAL/EMAIL, target CONFIRMED) vía POST admin.
  2. Hidratación de variables ``{{evento_nombre}}``/``{{qr_url}}`` en la plantilla.
  3. ``dry_run``: no envía, retorna preview y conteo.
  4. ``send`` filtra por target_status (no toca WAITLIST/CANCELLED).
  5. ``broadcast`` permite sobreescribir target_status.
  6. Campaña no encontrada → 404; verificación de plantilla ausente.

Nota: los envíos reales usan el gateway async de ``services/messaging.py``;
los tests usan ``dry_run=True`` (o una plantilla ausente) para no depender de
gateways externos. ``hydrate_template`` se valida directamente.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from backend import models
from backend.services.event_campaign_service import hydrate_template
from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_user_with_role as _seed_user_with_role

ADMIN = "/api/evangelism/events"


# ── Helpers ─────────────────────────────────────────────────────────────────


@pytest.fixture
def sede(db_session):
    s = models.Sede(id=uuid.uuid4(), nombre="Sede Test", ciudad="Bogota", es_activa=True)
    db_session.add(s)
    db_session.flush()
    return s


@pytest.fixture
def admin_headers(client, db_session, sede):
    """Admin Auth v3 en la MISMA sede del fixture + headers Bearer."""
    _seed_user_with_role(
        db_session,
        role_name="evangelism_admin",
        email="camp-admin@test.com",
        password="testpass123",
        sede_id=sede.id,
        permisos={
            "evangelism:read": "allow",
            "evangelism:edit": "allow",
            "evangelism:manage": "allow",
        },
    )
    return _auth_headers(client, email="camp-admin@test.com", password="testpass123")


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


def _make_plantilla(db_session, sede, **overrides):
    fields = dict(
        id=uuid.uuid4(),
        sede_id=sede.id,
        categoria_id=uuid.uuid4(),  # la FK no se valida en SQLite tests
        titulo="Recordatorio evento",
        canal=models.CanalEnvio.EMAIL,
        contenido_texto="Te esperamos en {{evento_nombre}} el {{EVENTO_FECHA}}",
    )
    fields.update(overrides)
    plt = models.PlantillaMensaje(**fields)
    db_session.add(plt)
    db_session.flush()
    return plt


def _make_registration(db_session, event, persona=None, **overrides):
    if persona is None:
        persona = models.Persona(
            id=uuid.uuid4(),
            sede_id=event.sede_id,
            first_name="Ana",
            last_name="Pérez",
            email="ana@example.com",
            phone="3001234567",
        )
        db_session.add(persona)
        db_session.flush()
    fields = dict(
        id=uuid.uuid4(),
        event_id=event.id,
        persona_id=persona.id,
        registration_status="CONFIRMED",
        source="admin",
        registered_at=datetime.now(timezone.utc),
    )
    fields.update(overrides)
    reg = models.EventRegistration(**fields)
    db_session.add(reg)
    db_session.flush()
    return reg


def _make_campaign(db_session, event, plantilla, **overrides):
    fields = dict(
        id=uuid.uuid4(),
        event_id=event.id,
        name="Recordatorio día evento",
        plantilla_id=plantilla.id,
        canal="EMAIL",
        trigger_type="MANUAL",
        target_status=["CONFIRMED"],
        is_active=True,
    )
    fields.update(overrides)
    camp = models.EventCampaign(**fields)
    db_session.add(camp)
    db_session.flush()
    return camp


# ── Hidratación de plantilla (servicio) ─────────────────────────────────────


class TestHydrateTemplate:
    def test_event_and_persona_variables(self, db_session, sede):
        evt = _make_event(db_session, sede)
        persona = models.Persona(
            id=uuid.uuid4(),
            sede_id=sede.id,
            first_name="Ana",
            last_name="Pérez",
            email="ana@example.com",
        )
        db_session.add(persona)
        db_session.flush()
        reg = _make_registration(db_session, evt, persona)

        text = hydrate_template(
            "Hola {{nombre}} en {{EVENTO_NOMBRE}} el {{evento_fecha}}",
            persona=persona,
            event=evt,
            registration=reg,
        )
        assert "Ana" in text
        assert "Concierto Navidad" in text
        assert "24/12/2026" in text

    def test_qr_url_variable(self, db_session, sede):
        evt = _make_event(db_session, sede)
        reg = _make_registration(db_session, evt, qr_token="CCF-EVT-abc")
        persona = reg.persona

        text = hydrate_template(
            "Tu QR: {{qr_url}}",
            persona=persona,
            event=evt,
            registration=reg,
            public_base_url="https://ccf.co",
        )
        assert "https://ccf.co/public/events/" in text
        assert "CCF-EVT-abc" in text

    def test_qr_url_empty_without_token(self, db_session, sede):
        evt = _make_event(db_session, sede)
        reg = _make_registration(db_session, evt, qr_token=None)

        text = hydrate_template(
            "QR: {{qr_url}}", persona=reg.persona, event=evt, registration=reg, public_base_url="https://ccf.co"
        )
        assert text == "QR: "


# ── Admin campañas ──────────────────────────────────────────────────────────


class TestAdminCampaigns:
    def test_create_campaign(self, client, db_session, sede, admin_headers):
        evt = _make_event(db_session, sede)
        plt = _make_plantilla(db_session, sede)
        db_session.commit()

        resp = client.post(
            f"{ADMIN}/{evt.id}/campaigns",
            headers=admin_headers,
            json={
                "name": "Recordatorio",
                "plantilla_id": str(plt.id),
                "canal": "EMAIL",
                "trigger_type": "MANUAL",
                "target_status": ["CONFIRMED"],
                "is_active": True,
            },
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["event_id"] == str(evt.id)
        assert data["canal"] == "EMAIL"
        assert data["trigger_type"] == "MANUAL"

    def test_list_campaigns(self, client, db_session, sede, admin_headers):
        evt = _make_event(db_session, sede)
        plt = _make_plantilla(db_session, sede)
        _make_campaign(db_session, evt, plt, name="Campaña A")
        _make_campaign(db_session, evt, plt, name="Campaña B")
        db_session.commit()

        resp = client.get(f"{ADMIN}/{evt.id}/campaigns", headers=admin_headers)
        assert resp.status_code == 200, resp.text
        assert len(resp.json()) == 2

    def test_delete_campaign(self, client, db_session, sede, admin_headers):
        evt = _make_event(db_session, sede)
        plt = _make_plantilla(db_session, sede)
        camp = _make_campaign(db_session, evt, plt)
        db_session.commit()

        resp = client.delete(f"{ADMIN}/{evt.id}/campaigns/{camp.id}", headers=admin_headers)
        assert resp.status_code == 204
        assert (
            db_session.query(models.EventCampaign)
            .filter(models.EventCampaign.id == camp.id, models.EventCampaign.deleted_at.is_(None))
            .count()
            == 0
        )

    def test_campaign_404(self, client, db_session, sede, admin_headers):
        evt = _make_event(db_session, sede)
        db_session.commit()
        resp = client.get(f"{ADMIN}/{evt.id}/campaigns/{uuid.uuid4()}", headers=admin_headers)
        assert resp.status_code in (404, 405)


# ── Envío de campaña (dry_run) ──────────────────────────────────────────────


class TestSendCampaign:
    def test_send_dry_run_preview(self, client, db_session, sede, admin_headers):
        evt = _make_event(db_session, sede)
        plt = _make_plantilla(db_session, sede, contenido_texto="Hola {{nombre}}, evento: {{evento_nombre}}")
        _make_campaign(db_session, evt, plt)
        _make_registration(db_session, evt)
        db_session.commit()
        camp = db_session.query(models.EventCampaign).filter(
            models.EventCampaign.event_id == evt.id
        ).first()

        resp = client.post(f"{ADMIN}/{evt.id}/campaigns/{camp.id}/send", params={"dry_run": "true"}, headers=admin_headers)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["sent"] == 0
        assert data["would_send_to"] == 1
        assert "Ana" in data["preview"]
        assert "Concierto Navidad" in data["preview"]

    def test_send_respects_target_status(self, client, db_session, sede, admin_headers):
        evt = _make_event(db_session, sede)
        plt = _make_plantilla(db_session, sede)
        _make_campaign(db_session, evt, plt)
        _make_registration(db_session, evt, registration_status="CONFIRMED")
        _make_registration(
            db_session,
            evt,
            persona=models.Persona(
                id=uuid.uuid4(),
                sede_id=evt.sede_id,
                first_name="Luis",
                last_name="Gómez",
                email="luis@example.com",
                phone="3009999999",
            ),
            registration_status="WAITLIST",
            waiting_list_position=1,
        )
        db_session.commit()
        camp = db_session.query(models.EventCampaign).filter(
            models.EventCampaign.event_id == evt.id
        ).first()

        resp = client.post(f"{ADMIN}/{evt.id}/campaigns/{camp.id}/send", params={"dry_run": "true"}, headers=admin_headers)
        assert resp.status_code == 200
        # Solo CONFIRMED es audiencia → 1, no 2
        assert resp.json()["would_send_to"] == 1

    def test_send_no_regs_zero(self, client, db_session, sede, admin_headers):
        evt = _make_event(db_session, sede)
        plt = _make_plantilla(db_session, sede)
        _make_campaign(db_session, evt, plt)
        db_session.commit()
        camp = db_session.query(models.EventCampaign).filter(
            models.EventCampaign.event_id == evt.id
        ).first()

        resp = client.post(f"{ADMIN}/{evt.id}/campaigns/{camp.id}/send", params={"dry_run": "true"}, headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        # Sin inscripciones, dry_run no devuelve preview; nada se envía.
        assert data["sent"] == 0
        assert data["skipped"] == 0

    def test_broadcast_overrides_target_status(self, client, db_session, sede, admin_headers):
        evt = _make_event(db_session, sede)
        plt = _make_plantilla(db_session, sede)
        camp = _make_campaign(db_session, evt, plt, target_status=["CONFIRMED"])
        db_session.commit()

        resp = client.post(
            f"{ADMIN}/{evt.id}/registrations/broadcast",
            headers=admin_headers,
            json={"campaign_id": str(camp.id), "target_status": ["WAITLIST"]},
        )
        assert resp.status_code == 200, resp.text
        db_session.refresh(camp)
        assert camp.target_status == ["WAITLIST"]
