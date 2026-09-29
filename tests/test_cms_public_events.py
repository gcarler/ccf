"""Tests TKT-CMS-BACKEND-EVENTS-02 — Backend de Eventos Públicos y Pre-registro.

Cubre:
- GET  /api/evangelism/public/upcoming-events: campos enriquecidos
  (sede_nombre, direccion, imagen_url, next_datetime UTC aware,
  hora_formateada, permite_registro), filtrado public/activa/no-borrada y
  orden por próxima ocurrencia.
- POST /api/evangelism/public/strategies/{id}/register: Axioma 1 (busca o
  crea la Persona canónica, nunca tablas paralelas), hereda sede de la
  estrategia (Axioma 3), confirmación idempotente de asistencia y errores
  nominales (404 estrategia inexistente/privada, 422 sin contacto).
"""

from __future__ import annotations

import datetime
import uuid

import pytest

from backend import models
from backend.api.evangelism_public import _hora_formateada, get_next_occurrence
from backend.models_evangelism import CategoriaEstrategia, EstrategiaEvangelismo, Sede
from tests.conftest import seed_admin

REGISTER_PATH = "/api/evangelism/public/strategies/{id}/register"


# ─────────────────────────────────────────────────────────────────────────────
# Helpers de seed
# ─────────────────────────────────────────────────────────────────────────────


def _seed_sede(db_session, nombre: str = "Sede Central", ciudad: str = "Bogotá") -> Sede:
    sede = Sede(id=uuid.uuid4(), nombre=nombre, ciudad=ciudad, es_activa=True)
    db_session.add(sede)
    db_session.commit()
    db_session.refresh(sede)
    return sede


def _seed_categoria(db_session) -> CategoriaEstrategia:
    cat = CategoriaEstrategia(nombre=f"Cat Public Events {uuid.uuid4().hex[:8]}")
    db_session.add(cat)
    db_session.commit()
    db_session.refresh(cat)
    return cat


def _seed_estrategia(
    db_session,
    sede,
    categoria,
    nombre: str = "Noche de Esperanza",
    dia: str = "Miércoles",
    hora: str = "19:30",
    is_public: bool = True,
    activa: bool = True,
    deleted: bool = False,
    descripcion: str | None = "Campaña de evangelismo masivo",
    direccion: str | None = None,
):
    est = EstrategiaEvangelismo(
        id=uuid.uuid4(),
        nombre=nombre,
        descripcion=descripcion,
        sede_id=sede.id,
        categoria_id=categoria.id,
        typology="evento_masivo",
        strategy_type="geografica",
        frecuencia="SEMANAL",
        dia_reunion=dia,
        hora_reunion=hora,
        activa=activa,
        is_public=is_public,
        status="active",
        deleted_at=datetime.datetime.now(datetime.timezone.utc) if deleted else None,
    )
    db_session.add(est)
    if direccion:
        db_session.add(
            models.GrupoEvangelismo(
                estrategia_id=est.id,
                sede_id=sede.id,
                nombre=f"Grupo base {nombre}",
                direccion=direccion,
                activo=True,
            )
        )
    db_session.commit()
    db_session.refresh(est)
    return est


def _seed_sesion(db_session, est, sede, fecha_sesion):
    grupo = models.GrupoEvangelismo(
        estrategia_id=est.id,
        sede_id=sede.id,
        nombre=f"Grupo sesión {uuid.uuid4().hex[:6]}",
        activo=True,
    )
    db_session.add(grupo)
    db_session.flush()
    sesion = models.SesionGrupo(grupo_id=grupo.id, fecha_sesion=fecha_sesion)
    db_session.add(sesion)
    db_session.commit()
    db_session.refresh(sesion)
    return sesion


def _register(client, est_id: str, payload: dict):
    return client.post(REGISTER_PATH.format(id=est_id), json=payload)


# ─────────────────────────────────────────────────────────────────────────────
# GET /public/upcoming-events
# ─────────────────────────────────────────────────────────────────────────────


class TestUpcomingPublicEvents:
    def test_upcoming_events_enriched_payload(self, client, db_session):
        """El feed expone sede_nombre, direccion, imagen_url, next_datetime
        UTC aware, hora_formateada y permite_registro."""
        sede = _seed_sede(db_session)
        cat = _seed_categoria(db_session)
        est = _seed_estrategia(
            db_session,
            sede,
            cat,
            nombre="Noche de Esperanza",
            dia="Miércoles",
            hora="19:30",
            descripcion="Campaña masiva",
            direccion="Calle 45 #12-30",
        )

        resp = client.get("/api/evangelism/public/upcoming-events")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

        item = next(e for e in data if e["id"] == str(est.id))
        assert item["nombre"] == "Noche de Esperanza"
        assert item["sede_nombre"] == "Sede Central"
        assert item["sede"] == {"id": str(sede.id), "nombre": "Sede Central", "ciudad": "Bogotá"}
        assert item["direccion"] == "Calle 45 #12-30"
        assert item["lugar"] == "Calle 45 #12-30, Sede Central"
        assert item["imagen_url"] is None
        assert item["permite_registro"] is True
        assert item["hora_formateada"] == "19:30"
        assert item["descripcion"] == "Campaña masiva"

        # next_datetime UTC aware (offset +00:00) y next_date YYYY-MM-DD
        next_dt = datetime.datetime.fromisoformat(item["next_datetime"])
        assert next_dt.tzinfo is not None
        assert next_dt.utcoffset() == datetime.timedelta(0)
        assert item["next_date"] == next_dt.strftime("%Y-%m-%d")
        # Miércoles 19:30 UTC → miércoles y 19:30
        assert next_dt.weekday() == 2
        assert (next_dt.hour, next_dt.minute) == (19, 30)

    def test_upcoming_events_filters_and_orders(self, client, db_session):
        """Solo public + activa + no borrada; orden ascendente por fecha."""
        seed_admin(db_session)
        sede = _seed_sede(db_session)
        cat = _seed_categoria(db_session)
        est_public = _seed_estrategia(db_session, sede, cat, nombre="Public Martes", dia="Martes", hora="18:00")
        _seed_estrategia(db_session, sede, cat, nombre="Privada", dia="Martes", hora="18:00", is_public=False)
        _seed_estrategia(db_session, sede, cat, nombre="Inactiva", dia="Martes", hora="18:00", activa=False)
        _seed_estrategia(db_session, sede, cat, nombre="Borrada", dia="Martes", hora="18:00", deleted=True)
        _seed_estrategia(db_session, sede, cat, nombre="Sin horario", dia=None, hora=None)

        resp = client.get("/api/evangelism/public/upcoming-events")
        assert resp.status_code == 200
        data = resp.json()
        ids = [e["id"] for e in data]

        assert str(est_public.id) in ids
        nombres = [e["nombre"] for e in data if e["id"] == str(est_public.id)]
        assert nombres == ["Public Martes"]

        # next_datetime orden ascendente
        dts = [datetime.datetime.fromisoformat(e["next_datetime"]) for e in data]
        assert dts == sorted(dts)

    def test_upcoming_events_excludes_other_sedes(self, client, db_session):
        """El feed público no filtra por sede del actor (es anónimo), pero
        cada item reporta la sede correcta de su estrategia."""
        sede_a = _seed_sede(db_session, nombre="Sede A", ciudad="Cali")
        sede_b = _seed_sede(db_session, nombre="Sede B", ciudad="Medellín")
        cat = _seed_categoria(db_session)
        est_a = _seed_estrategia(db_session, sede_a, cat, nombre="Estrategia A", dia="Jueves", hora="10:00")
        est_b = _seed_estrategia(db_session, sede_b, cat, nombre="Estrategia B", dia="Viernes", hora="20:00")

        resp = client.get("/api/evangelism/public/upcoming-events")
        assert resp.status_code == 200
        data = {e["id"]: e for e in resp.json()}
        assert data[str(est_a.id)]["sede_nombre"] == "Sede A"
        assert data[str(est_b.id)]["sede_nombre"] == "Sede B"

    def test_get_next_occurrence_is_utc_aware(self):
        dt = get_next_occurrence("Lunes", "18:30")
        assert dt is not None
        assert dt.tzinfo is datetime.timezone.utc
        assert dt.weekday() == 0

        assert get_next_occurrence(None, "18:00") is None
        assert get_next_occurrence("Lunes", None) is None
        assert get_next_occurrence("DíaInválido", "18:00") is None
        assert get_next_occurrence("Lunes", "hora_mala") is None

    def test_hora_formateada_normalization(self):
        assert _hora_formateada("9:05") == "09:05"
        assert _hora_formateada("19:30:00") == "19:30"
        assert _hora_formateada(None) is None
        assert _hora_formateada("no-es-hora") is None


# ─────────────────────────────────────────────────────────────────────────────
# POST /public/strategies/{id}/register
# ─────────────────────────────────────────────────────────────────────────────


class TestPublicStrategyRegister:
    def test_register_creates_visitor_persona_axioma1(self, client, db_session):
        """Crea la Persona canónica (Axioma 1) con rol Visitante y hereda la
        sede de la estrategia (Axioma 3: nunca del cliente)."""
        sede = _seed_sede(db_session)
        cat = _seed_categoria(db_session)
        est = _seed_estrategia(db_session, sede, cat, dia="Sábado", hora="16:00")

        resp = _register(
            client,
            str(est.id),
            {"nombre": "Maria Fernanda Gomez", "email": "maria@example.com", "telefono": "+573001234567"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["ok"] is True
        assert body["persona_created"] is True

        persona = db_session.query(models.Persona).filter(models.Persona.id == uuid.UUID(body["persona_id"])).first()
        assert persona is not None
        # Axioma 1: persona canónica en la tabla kernel
        assert persona.nombre_completo == "Maria Fernanda Gomez"
        assert persona.email == "maria@example.com"
        assert persona.phone == "+573001234567"
        assert persona.church_role == "Visitante"
        assert persona.spiritual_status == "Nuevo"
        # Axioma 3: sede heredada del servidor, no del cliente
        assert persona.sede_id == est.sede_id

    def test_register_reuses_existing_persona_by_email(self, client, db_session):
        """No duplica personas: reutiliza la Persona canónica existente."""
        seed_admin(db_session)
        sede = _seed_sede(db_session)
        cat = _seed_categoria(db_session)
        est = _seed_estrategia(db_session, sede, cat, dia="Domingo", hora="09:00")

        existente = models.Persona(
            first_name="Carlos", last_name="Ruiz", email="carlos@example.com", sede_id=sede.id
        )
        db_session.add(existente)
        db_session.commit()
        db_session.refresh(existente)

        resp = _register(client, str(est.id), {"nombre": "Otro Nombre", "email": "carlos@example.com"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["persona_created"] is False
        assert body["persona_id"] == str(existente.id)

        total = db_session.query(models.Persona).filter(models.Persona.email == "carlos@example.com").count()
        assert total == 1

    def test_register_reuses_existing_persona_by_phone(self, client, db_session):
        """Sin email, resuelve la persona canónica por teléfono."""
        sede = _seed_sede(db_session)
        cat = _seed_categoria(db_session)
        est = _seed_estrategia(db_session, sede, cat, dia="Lunes", hora="10:00")

        existente = models.Persona(first_name="Ana", last_name="Diaz", phone="+573117654321", sede_id=sede.id)
        db_session.add(existente)
        db_session.commit()
        db_session.refresh(existente)

        resp = _register(client, str(est.id), {"nombre": "Ana Diaz", "telefono": "+573117654321"})
        assert resp.status_code == 200
        assert resp.json()["persona_id"] == str(existente.id)

    def test_register_requires_contact_info(self, client, db_session):
        """Sin email ni teléfono responde 422 nominal."""
        sede = _seed_sede(db_session)
        cat = _seed_categoria(db_session)
        est = _seed_estrategia(db_session, sede, cat)

        resp = _register(client, str(est.id), {"nombre": "Sin Contacto"})
        assert resp.status_code == 422

    def test_register_404_for_unknown_or_private_strategy(self, client, db_session):
        """404 nominal para estrategia inexistente, privada, inactiva o borrada."""
        sede = _seed_sede(db_session)
        cat = _seed_categoria(db_session)
        est_priv = _seed_estrategia(db_session, sede, cat, nombre="Privada Reg", is_public=False)
        est_ina = _seed_estrategia(db_session, sede, cat, nombre="Inactiva Reg", activa=False)
        est_del = _seed_estrategia(db_session, sede, cat, nombre="Borrada Reg", deleted=True)

        payload = {"nombre": "Test User", "email": "t@example.com"}
        for est in (est_priv, est_ina, est_del):
            resp = _register(client, str(est.id), payload)
            assert resp.status_code == 404

        resp = _register(client, str(uuid.uuid4()), payload)
        assert resp.status_code == 404

    def test_register_requires_nombre(self, client, db_session):
        """El payload nominal exige nombre (validación Pydantic)."""
        sede = _seed_sede(db_session)
        cat = _seed_categoria(db_session)
        est = _seed_estrategia(db_session, sede, cat)

        resp = _register(client, str(est.id), {"nombre": "   ", "email": "x@example.com"})
        assert resp.status_code == 422

    def test_register_confirms_attendance_idempotent(self, client, db_session):
        """La confirmación de asistencia es idempotente por (sesión, persona)."""
        sede = _seed_sede(db_session)
        cat = _seed_categoria(db_session)
        est = _seed_estrategia(db_session, sede, cat, dia="Martes", hora="18:00")
        next_dt = get_next_occurrence(est.dia_reunion, est.hora_reunion)
        sesion = _seed_sesion(db_session, est, sede, next_dt)

        payload = {"nombre": "Laura Perez", "email": "laura@example.com"}
        resp1 = _register(client, str(est.id), payload)
        assert resp1.status_code == 200

        asistencias = (
            db_session.query(models.Asistencia).filter(models.Asistencia.persona_id == uuid.UUID(resp1.json()["persona_id"])).all()
        )
        assert len(asistencias) == 1
        assert asistencias[0].sesion_id == sesion.id

        # Segundo registro: idempotente, no duplica asistencia
        resp2 = _register(client, str(est.id), payload)
        assert resp2.status_code == 200
        asistencias_after = (
            db_session.query(models.Asistencia).filter(models.Asistencia.persona_id == uuid.UUID(resp2.json()["persona_id"])).all()
        )
        assert len(asistencias_after) == 1

    def test_register_without_computable_session_still_saves_persona(self, client, db_session):
        """Sin sesión creada, el registro igual resuelve la persona (pre-registro)."""
        sede = _seed_sede(db_session)
        cat = _seed_categoria(db_session)
        est = _seed_estrategia(db_session, sede, cat, dia="Jueves", hora="21:00")

        resp = _register(client, str(est.id), {"nombre": "Pedro Cano", "email": "pedro@example.com"})
        assert resp.status_code == 200
        body = resp.json()
        persona = db_session.query(models.Persona).filter(models.Persona.id == uuid.UUID(body["persona_id"])).first()
        assert persona is not None
        assert persona.church_role == "Visitante"

    def test_register_rejects_invalid_nombre_type(self, client, db_session):
        """El endpoint rechaza payloads mal tipados (422 de validación)."""
        sede = _seed_sede(db_session)
        cat = _seed_categoria(db_session)
        est = _seed_estrategia(db_session, sede, cat)
        resp = _register(client, str(est.id), {"nombre": 12345, "email": "x@example.com"})
        assert resp.status_code == 422
