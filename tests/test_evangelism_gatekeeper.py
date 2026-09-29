"""Fase 2 Super-PRO de Control de Acceso y Puerta (TKT-EVT-GATEKEEPER-02).

Pruebas canónicas de Gatekeeper:
1. Validación de QRs CCF-EVT- e inscripciones confirmadas.
2. Bloqueo de reingreso fraudulento (duplicate_access / HTTP 409) con detalle
   de primer ingreso (first_checkin_at, checked_by_name, registration_code).
3. Registro exitoso con fecha UTC, operador, PII y código correlativo.
4. Monitor de aforo en vivo: contador en tiempo real y porcentaje de capacidad.
"""

from __future__ import annotations

import datetime
from datetime import timezone
import uuid

import pytest

from backend import models
from backend.core.security import get_password_hash
from backend.models_auth import RolPlataforma, Usuario
from backend.models_crm import Persona
from backend.models_evangelism import Sede
from backend.services.event_registration_service import generate_qr_token
from tests.conftest import auth_headers


@pytest.fixture
def _gatekeeper_env(db_session, client):
    """Crea un operador de puerta autenticado y una sede activa."""
    sede = db_session.query(Sede).first()
    if not sede:
        sede = Sede(id=uuid.uuid4(), nombre="Sede Central Faro", ciudad="Santiago", es_activa=True)
        db_session.add(sede)
        db_session.flush()

    role = db_session.query(RolPlataforma).filter(RolPlataforma.nombre == "GATEKEEPER_OPERATOR").first()
    if not role:
        role = RolPlataforma(
            id=uuid.uuid4(),
            nombre="GATEKEEPER_OPERATOR",
            permisos={"evangelism:edit": "allow", "evangelism:read": "allow"},
        )
        db_session.add(role)
        db_session.flush()

    user_id = uuid.uuid4()
    p_op = Persona(
        id=user_id,
        first_name="Carlos",
        last_name="Puerta",
        sede_id=sede.id,
    )
    db_session.add(p_op)
    db_session.flush()

    user = Usuario(
        id=user_id,
        sede_id=sede.id,
        username="operador_gatekeeper",
        email="gatekeeper@faro.cl",
        password_hash=get_password_hash("puerta123"),
        rol_plataforma_id=role.id,
        is_active=True,
        is_email_verified=True,
    )
    db_session.add(user)
    db_session.commit()

    headers = auth_headers(client, email="gatekeeper@faro.cl", password="puerta123")
    return {"client": client, "headers": headers, "sede": sede, "operator": user, "operator_persona": p_op}


def test_gatekeeper_valid_checkin_success(db_session, _gatekeeper_env):
    """Acceso válido: valida QR CCF-EVT-, persiste UTC, operador, PII y occupancy."""
    client = _gatekeeper_env["client"]
    headers = _gatekeeper_env["headers"]
    sede = _gatekeeper_env["sede"]
    operator = _gatekeeper_env["operator"]

    # Crear evento con aforo máximo 50
    now = datetime.datetime.now(timezone.utc)
    today_str = now.strftime("%Y-%m-%d")

    event = models.CrmEvent(
        id=uuid.uuid4(),
        name="Gran Noche de Milagros",
        event_date=now,
        sede_id=sede.id,
        capacity_max=50,
        status="ACTIVE",
    )
    db_session.add(event)

    # Crear participante con PII completa
    persona = Persona(
        id=uuid.uuid4(),
        first_name="Daniel",
        last_name="Mendoza",
        email="daniel.mendoza@test.com",
        phone="+56998765432",
        sede_id=sede.id,
    )
    db_session.add(persona)
    db_session.flush()

    # Inscripción confirmada con correlativo #CCF-EVT-0007
    token, token_hash = generate_qr_token(event.id, persona.id)
    reg = models.EventRegistration(
        id=uuid.uuid4(),
        event_id=event.id,
        persona_id=persona.id,
        registration_status="CONFIRMED",
        registration_number=7,
        qr_token_hash=token_hash,
        qr_generated_at=now,
        participant_role_code="INVITADO",
    )
    db_session.add(reg)
    db_session.commit()

    # 1er Check-in
    resp = client.post(
        f"/api/evangelism/events/{event.id}/sessions/{today_str}/ccf-evt-checkin",
        json={"qr_token": token},
        headers=headers,
    )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "success"
    assert data["is_duplicate"] is False
    assert data["persona_id"] == str(persona.id)
    assert data["persona_name"] == "Daniel Mendoza"
    assert data["first_name"] == "Daniel"
    assert data["last_name"] == "Mendoza"
    assert data["email"] == "daniel.mendoza@test.com"
    assert data["phone"] == "+56998765432"
    assert data["registration_code"] == "#CCF-EVT-0007"
    assert data["participant_role_code"] == "INVITADO"
    assert data["checked_in_by"] == str(operator.id)
    assert data["checked_by_name"] == "Carlos Puerta"
    assert data["check_in_at"] is not None
    assert data["occupancy"]["count"] == 1
    assert data["occupancy"]["capacity_max"] == 50
    assert data["occupancy"]["percentage"] == 2.0

    # Verificar en DB que la inscripción y asistencia quedaron CHECKED_IN y UTC
    db_session.refresh(reg)
    assert reg.registration_status == "CHECKED_IN"
    assert reg.check_in_at is not None
    assert reg.checked_in_by == operator.id

    attendance = (
        db_session.query(models.EventAttendance)
        .filter(
            models.EventAttendance.event_id == event.id,
            models.EventAttendance.persona_id == persona.id,
        )
        .first()
    )
    assert attendance is not None
    assert attendance.attended is True
    assert attendance.check_in_at is not None


def test_gatekeeper_blocks_duplicate_reentry(db_session, _gatekeeper_env):
    """Anti-fraude: bloquea reingreso duplicado con HTTP 409 y status duplicate_access."""
    client = _gatekeeper_env["client"]
    headers = _gatekeeper_env["headers"]
    sede = _gatekeeper_env["sede"]

    now = datetime.datetime.now(timezone.utc)
    today_str = now.strftime("%Y-%m-%d")

    event = models.CrmEvent(
        id=uuid.uuid4(),
        name="Conferencia Faro PRO",
        event_date=now,
        sede_id=sede.id,
        capacity_max=200,
        status="ACTIVE",
    )
    db_session.add(event)

    persona = Persona(
        id=uuid.uuid4(),
        first_name="Marcela",
        last_name="Rios",
        email="marcela@faro.cl",
        sede_id=sede.id,
    )
    db_session.add(persona)
    db_session.flush()

    token, token_hash = generate_qr_token(event.id, persona.id)
    reg = models.EventRegistration(
        id=uuid.uuid4(),
        event_id=event.id,
        persona_id=persona.id,
        registration_status="CONFIRMED",
        registration_number=15,
        qr_token_hash=token_hash,
        qr_generated_at=now,
        participant_role_code="MIEMBRO",
    )
    db_session.add(reg)
    db_session.commit()

    # 1er Escaneo: éxito
    resp1 = client.post(
        f"/api/evangelism/events/{event.id}/sessions/{today_str}/ccf-evt-checkin",
        json={"qr_token": token},
        headers=headers,
    )
    assert resp1.status_code == 200

    # 2do Escaneo con el mismo QR (intento de pase clonado / reingreso): Bloqueo 409
    resp2 = client.post(
        f"/api/evangelism/events/{event.id}/sessions/{today_str}/ccf-evt-checkin",
        json={"qr_token": token},
        headers=headers,
    )
    assert resp2.status_code == 409, resp2.text
    dup_data = resp2.json()

    # Soporte tanto en top-level como en detail
    status_val = dup_data.get("status") or (dup_data.get("detail", {}) if isinstance(dup_data.get("detail"), dict) else {}).get("status")
    assert status_val == "duplicate_access"

    first_checkin = dup_data.get("first_checkin_at") or (dup_data.get("detail", {}) if isinstance(dup_data.get("detail"), dict) else {}).get("first_checkin_at")
    assert first_checkin is not None

    checked_by = dup_data.get("checked_by_name") or (dup_data.get("detail", {}) if isinstance(dup_data.get("detail"), dict) else {}).get("checked_by_name")
    assert checked_by == "Carlos Puerta"

    reg_code = dup_data.get("registration_code") or (dup_data.get("detail", {}) if isinstance(dup_data.get("detail"), dict) else {}).get("registration_code")
    assert reg_code == "#CCF-EVT-0015"


def test_gatekeeper_rejects_unconfirmed_and_tampered_qr(db_session, _gatekeeper_env):
    """Valida rechazo de QRs no confirmados, malformados o con hash alterado."""
    client = _gatekeeper_env["client"]
    headers = _gatekeeper_env["headers"]
    sede = _gatekeeper_env["sede"]

    now = datetime.datetime.now(timezone.utc)
    today_str = now.strftime("%Y-%m-%d")

    event = models.CrmEvent(
        id=uuid.uuid4(),
        name="Evento Auditoria",
        event_date=now,
        sede_id=sede.id,
    )
    db_session.add(event)

    persona = Persona(
        id=uuid.uuid4(),
        first_name="Auditor",
        last_name="Forense",
        sede_id=sede.id,
    )
    db_session.add(persona)
    db_session.flush()

    token, token_hash = generate_qr_token(event.id, persona.id)

    # Caso 1: Inscripción PENDING (no confirmada)
    reg_pending = models.EventRegistration(
        id=uuid.uuid4(),
        event_id=event.id,
        persona_id=persona.id,
        registration_status="PENDING",
        qr_token_hash=token_hash,
        qr_generated_at=now,
    )
    db_session.add(reg_pending)
    db_session.commit()

    resp = client.post(
        f"/api/evangelism/events/{event.id}/sessions/{today_str}/ccf-evt-checkin",
        json={"qr_token": token},
        headers=headers,
    )
    assert resp.status_code == 409
    assert "no confirmada" in resp.text

    # Caso 2: QR alterado / secret modificado
    reg_pending.registration_status = "CONFIRMED"
    db_session.commit()

    tampered_token = token[:-4] + "ffff"
    resp_tampered = client.post(
        f"/api/evangelism/events/{event.id}/sessions/{today_str}/ccf-evt-checkin",
        json={"qr_token": tampered_token},
        headers=headers,
    )
    assert resp_tampered.status_code == 403


def test_gatekeeper_live_occupancy_monitor(db_session, _gatekeeper_env):
    """Valida los endpoints de monitor de aforo en vivo."""
    client = _gatekeeper_env["client"]
    headers = _gatekeeper_env["headers"]
    sede = _gatekeeper_env["sede"]

    now = datetime.datetime.now(timezone.utc)
    today_str = now.strftime("%Y-%m-%d")

    event = models.CrmEvent(
        id=uuid.uuid4(),
        name="Cumbre de Liderazgo",
        event_date=now,
        sede_id=sede.id,
        capacity_max=100,
        status="ACTIVE",
    )
    db_session.add(event)

    # 3 asistencias registradas
    for i in range(3):
        p = Persona(id=uuid.uuid4(), first_name=f"Asistente{i}", last_name="Test", sede_id=sede.id)
        db_session.add(p)
        db_session.flush()
        att = models.EventAttendance(
            event_id=event.id,
            session_date=now.date(),
            persona_id=p.id,
            attended=True,
            status="present",
            check_in_at=now,
        )
        db_session.add(att)
    db_session.commit()

    # GET sesión específica
    resp1 = client.get(
        f"/api/evangelism/events/{event.id}/sessions/{today_str}/occupancy",
        headers=headers,
    )
    assert resp1.status_code == 200
    occ1 = resp1.json()
    assert occ1["checked_in_count"] == 3
    assert occ1["capacity_max"] == 100
    assert occ1["percentage"] == 3.0
    assert occ1["is_full"] is False

    # GET endpoint general de evento
    resp2 = client.get(
        f"/api/evangelism/events/{event.id}/occupancy",
        headers=headers,
    )
    assert resp2.status_code == 200
    occ2 = resp2.json()
    assert occ2["checked_in_count"] == 3
    assert occ2["percentage"] == 3.0
