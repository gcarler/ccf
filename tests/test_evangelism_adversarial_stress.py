"""
Empirical Adversarial Stress Test Suite for CCF Evangelismo.

Validates the security, isolation, and contract integrity remediations:
1. /strategies/public-config: 100% isolated per tenant (cross-sede blind).
2. PATCH /strategies/{id}/toggle-public: IDOR protection (uniform 404 on cross-sede/missing).
3. POST /events/: Cross-sede creation attempt rejects with 403 before any DB write.
4. POST /attendance/bulk: Cross-sede Persona UUIDs are silently ignored and not registered in DB.
5. GET /reports/group/{id}/attendance-pdf & attendance-excel: Uniform 404 on non-existent vs cross-sede (0 BOLA oracle).
6. Zero db.delete() and zero datetime.utcnow across evangelism backend.
"""

from __future__ import annotations

import datetime
import os
import uuid

from backend import models
from backend.models_evangelism import (
    CategoriaEstrategia,
    EstrategiaEvangelismo,
    GrupoEvangelismo,
)
from tests.conftest import auth_headers, seed_admin, seed_user_with_role


def _create_strategy(
    db_session,
    sede_id,
    categoria_id,
    nombre="Estrategia Test",
    dia="Lunes",
    hora="19:00",
    is_public=False,
    activa=True,
    deleted=False,
):
    est = EstrategiaEvangelismo(
        id=uuid.uuid4(),
        nombre=nombre,
        sede_id=sede_id,
        categoria_id=categoria_id,
        typology="relacional",
        strategy_type="geografica",
        frecuencia="SEMANAL",
        dia_reunion=dia,
        hora_reunion=hora,
        fecha_inicio=datetime.datetime(2026, 6, 1, tzinfo=datetime.timezone.utc),
        fecha_fin=datetime.datetime(2026, 6, 22, tzinfo=datetime.timezone.utc),
        activa=activa,
        is_public=is_public,
        status="active",
        deleted_at=datetime.datetime.now(datetime.timezone.utc) if deleted else None,
    )
    db_session.add(est)
    db_session.commit()
    db_session.refresh(est)
    return est


def _create_group(
    db_session,
    sede_id,
    estrategia_id,
    nombre="Grupo Test",
    lider_persona_id=None,
    activo=True,
    deleted=False,
):
    grp = GrupoEvangelismo(
        id=uuid.uuid4(),
        nombre=nombre,
        codigo=f"GRP-{uuid.uuid4().hex[:6]}",
        sede_id=sede_id,
        estrategia_id=estrategia_id,
        ubicacion="Sector Central",
        direccion="Calle 10 # 20-30",
        capacidad=25,
        dia_reunion="Martes",
        hora_reunion="19:30",
        lider_persona_id=lider_persona_id,
        activo=activo,
        deleted_at=datetime.datetime.now(datetime.timezone.utc) if deleted else None,
    )
    db_session.add(grp)
    db_session.commit()
    db_session.refresh(grp)
    return grp


def _create_persona(
    db_session,
    sede_id,
    first_name="Juan",
    last_name="Perez",
    email=None,
):
    if email is None:
        email = f"persona_{uuid.uuid4().hex[:6]}@ccf.test"
    persona = models.Persona(
        id=uuid.uuid4(),
        first_name=first_name,
        last_name=last_name,
        email=email,
        phone="+573101234567",
        sede_id=sede_id,
        church_role="Miembro",
    )
    db_session.add(persona)
    db_session.commit()
    db_session.refresh(persona)
    return persona


class TestEvangelismAdversarialEmpirical:
    """Rigorous empirical adversarial suite stress-testing CCF Evangelismo security boundaries."""

    def test_adv_01_public_config_tenant_isolation_and_tampering(self, client, db_session):
        """1. /strategies/public-config must strictly isolate strategies per tenant and ignore tampering."""
        # Setup Sede A and Sede B
        user_a, persona_a, sede_a = seed_admin(db_session, email="admin_adv_a@test.com")
        headers_a = auth_headers(client, email="admin_adv_a@test.com")

        sede_b = models.Sede(
            id=uuid.uuid4(),
            nombre=f"Sede B {uuid.uuid4().hex[:4]}",
            ciudad="Medellin",
            es_activa=True,
        )
        db_session.add(sede_b)
        db_session.commit()

        user_b, persona_b, _ = seed_user_with_role(
            db_session,
            role_name="admin",
            email="admin_adv_b@test.com",
            sede_id=sede_b.id,
        )
        headers_b = auth_headers(client, email="admin_adv_b@test.com")

        cat = CategoriaEstrategia(nombre=f"Cat Adv 1 {uuid.uuid4().hex[:6]}")
        db_session.add(cat)
        db_session.commit()

        # Seed strategies for Sede A
        est_a1 = _create_strategy(db_session, sede_a.id, cat.id, nombre="Estrategia A1 Publica", is_public=True)
        est_a2 = _create_strategy(db_session, sede_a.id, cat.id, nombre="Estrategia A2 Privada", is_public=False)
        est_a_del = _create_strategy(db_session, sede_a.id, cat.id, nombre="Estrategia A3 Borrada", is_public=True, deleted=True)

        # Seed strategies for Sede B
        est_b1 = _create_strategy(db_session, sede_b.id, cat.id, nombre="Estrategia B1 Publica", is_public=True)
        est_b2 = _create_strategy(db_session, sede_b.id, cat.id, nombre="Estrategia B2 Privada", is_public=False)

        # 1. User A queries public config
        resp_a = client.get("/api/evangelism/strategies/public-config", headers=headers_a)
        assert resp_a.status_code == 200
        data_a = resp_a.json()
        ids_a = {item["id"] for item in data_a}

        # Assert Sede A strategies present
        assert str(est_a1.id) in ids_a
        assert str(est_a2.id) in ids_a
        # Assert Sede A soft-deleted excluded
        assert str(est_a_del.id) not in ids_a
        # Assert Sede B strategies strictly excluded (ZERO cross-tenant leakage)
        assert str(est_b1.id) not in ids_a
        assert str(est_b2.id) not in ids_a

        # 2. Tampering attack: User A attempts query param override (?sede_id=... or headers)
        tamper_resp = client.get(
            f"/api/evangelism/strategies/public-config?sede_id={sede_b.id}",
            headers={**headers_a, "X-Sede-Id": str(sede_b.id)},
        )
        assert tamper_resp.status_code == 200
        tamper_ids = {item["id"] for item in tamper_resp.json()}
        # Sede B must STILL NOT be leaked
        assert str(est_b1.id) not in tamper_ids
        assert str(est_b2.id) not in tamper_ids
        assert str(est_a1.id) in tamper_ids

        # 3. User B queries public config
        resp_b = client.get("/api/evangelism/strategies/public-config", headers=headers_b)
        assert resp_b.status_code == 200
        data_b = resp_b.json()
        ids_b = {item["id"] for item in data_b}

        assert str(est_b1.id) in ids_b
        assert str(est_b2.id) in ids_b
        assert str(est_a1.id) not in ids_b
        assert str(est_a2.id) not in ids_b

    def test_adv_02_toggle_public_idor_prevention_uniform_404(self, client, db_session):
        """2. PATCH /strategies/{id}/toggle-public against cross-sede strategy must return uniform 404 (no IDOR)."""
        user_a, persona_a, sede_a = seed_admin(db_session, email="admin_adv_02_a@test.com")
        headers_a = auth_headers(client, email="admin_adv_02_a@test.com")

        sede_b = models.Sede(
            id=uuid.uuid4(),
            nombre=f"Sede B IDOR {uuid.uuid4().hex[:4]}",
            ciudad="Cali",
            es_activa=True,
        )
        db_session.add(sede_b)
        db_session.commit()

        cat = CategoriaEstrategia(nombre=f"Cat Adv 2 {uuid.uuid4().hex[:6]}")
        db_session.add(cat)
        db_session.commit()

        # Strategy B in Sede B (attacker target)
        est_b = _create_strategy(db_session, sede_b.id, cat.id, nombre="Strategy B Secret", is_public=False)
        # Deleted Strategy in Sede A
        est_a_del = _create_strategy(db_session, sede_a.id, cat.id, nombre="Strategy A Deleted", is_public=False, deleted=True)
        # Active Strategy in Sede A
        est_a = _create_strategy(db_session, sede_a.id, cat.id, nombre="Strategy A Active", is_public=False)

        # Attack 1: User A targets Sede B strategy -> must return 404
        resp_idor = client.patch(
            f"/api/evangelism/strategies/{est_b.id}/toggle-public",
            json={"is_public": True},
            headers=headers_a,
        )
        assert resp_idor.status_code == 404, f"Expected 404 IDOR protection, got {resp_idor.status_code}"
        assert resp_idor.json()["detail"] == "Estrategia no encontrada"

        # Verify DB untouched
        db_session.refresh(est_b)
        assert est_b.is_public is False, "DB was mutated by cross-sede unauthorized toggle!"

        # Attack 2: Non-existent UUID -> must return identical 404
        fake_uuid = uuid.uuid4()
        resp_fake = client.patch(
            f"/api/evangelism/strategies/{fake_uuid}/toggle-public",
            json={"is_public": True},
            headers=headers_a,
        )
        assert resp_fake.status_code == 404
        assert resp_fake.json()["detail"] == "Estrategia no encontrada"
        assert resp_fake.json() == resp_idor.json(), "Error response oracle discrepancy between cross-sede and non-existent!"

        # Attack 3: Deleted strategy in Sede A -> must return identical 404
        resp_del = client.patch(
            f"/api/evangelism/strategies/{est_a_del.id}/toggle-public",
            json={"is_public": True},
            headers=headers_a,
        )
        assert resp_del.status_code == 404
        assert resp_del.json()["detail"] == "Estrategia no encontrada"

        # Legitimate mutation: User A toggles Sede A strategy -> 200 OK
        resp_ok = client.patch(
            f"/api/evangelism/strategies/{est_a.id}/toggle-public",
            json={"is_public": True},
            headers=headers_a,
        )
        assert resp_ok.status_code == 200
        assert resp_ok.json() == {"id": str(est_a.id), "is_public": True}
        db_session.refresh(est_a)
        assert est_a.is_public is True

    def test_adv_03_create_event_with_cross_sede_rejected_403(self, client, db_session):
        """3. Creating an event with payload.sede_id of another sede must reject with 403 before creating in DB."""
        user_a, persona_a, sede_a = seed_admin(db_session, email="admin_adv_03_a@test.com")
        headers_a = auth_headers(client, email="admin_adv_03_a@test.com")

        sede_b = models.Sede(
            id=uuid.uuid4(),
            nombre=f"Sede B Event {uuid.uuid4().hex[:4]}",
            ciudad="Cartagena",
            es_activa=True,
        )
        db_session.add(sede_b)
        db_session.commit()

        initial_events_b_count = db_session.query(models.CrmEvent).filter(models.CrmEvent.sede_id == sede_b.id).count()

        # Attack 1: User A sends POST /events/ with payload.sede_id = sede_b.id
        event_name_malicious = f"Malicious Cross-Sede Event {uuid.uuid4().hex[:6]}"
        payload_malicious = {
            "name": event_name_malicious,
            "sede_id": str(sede_b.id),
            "event_type": "PERMANENT",
            "target_audience": "ALL",
            "status": "SCHEDULED",
        }

        resp_create = client.post(
            "/api/evangelism/events/",
            json=payload_malicious,
            headers=headers_a,
        )

        assert resp_create.status_code == 403, f"Expected 403 Forbidden, got {resp_create.status_code}: {resp_create.text}"
        assert "No puedes crear eventos para una sede distinta a la tuya" in resp_create.json()["detail"]

        # Empirical DB check: No event was created in Sede B
        current_events_b_count = db_session.query(models.CrmEvent).filter(models.CrmEvent.sede_id == sede_b.id).count()
        assert current_events_b_count == initial_events_b_count, "DB pollution! Event was created in Sede B despite 403"

        created_in_db = db_session.query(models.CrmEvent).filter(models.CrmEvent.name == event_name_malicious).first()
        assert created_in_db is None, "Malicious event was written to the database!"

        # Attack 2: User A sends POST /events/ with random unassigned UUID
        random_sede_uuid = uuid.uuid4()
        payload_random_sede = {
            "name": f"Event Random Sede {uuid.uuid4().hex[:6]}",
            "sede_id": str(random_sede_uuid),
            "event_type": "PERMANENT",
            "target_audience": "ALL",
        }
        resp_random = client.post(
            "/api/evangelism/events/",
            json=payload_random_sede,
            headers=headers_a,
        )
        assert resp_random.status_code == 403

        # Legitimate check: Creating event with same sede or None succeeds
        legit_name = f"Legit Sede A Event {uuid.uuid4().hex[:6]}"
        payload_legit = {
            "name": legit_name,
            "sede_id": str(sede_a.id),
            "event_type": "PERMANENT",
            "target_audience": "ALL",
        }
        resp_legit = client.post(
            "/api/evangelism/events/",
            json=payload_legit,
            headers=headers_a,
        )
        assert resp_legit.status_code in (200, 201), f"Legit event creation failed: {resp_legit.status_code} {resp_legit.text}"
        event_data = resp_legit.json()
        assert str(event_data["sede_id"]) == str(sede_a.id)

    def test_adv_04_bulk_attendance_cross_tenant_persona_ignored(self, client, db_session):
        """4. Bulk attendance registration with cross-tenant Persona UUID must be ignored and not recorded."""
        user_a, persona_a, sede_a = seed_admin(db_session, email="admin_adv_04_a@test.com")
        headers_a = auth_headers(client, email="admin_adv_04_a@test.com")

        sede_b = models.Sede(
            id=uuid.uuid4(),
            nombre=f"Sede B Attend {uuid.uuid4().hex[:4]}",
            ciudad="Bucaramanga",
            es_activa=True,
        )
        db_session.add(sede_b)
        db_session.commit()

        # Create Event in Sede A
        event_a = models.CrmEvent(
            id=uuid.uuid4(),
            name=f"Event Attendance Test {uuid.uuid4().hex[:4]}",
            sede_id=sede_a.id,
            event_type="PERMANENT",
            target_audience="ALL",
            status="SCHEDULED",
        )
        db_session.add(event_a)
        db_session.commit()

        # Personas in Sede A (legitimate)
        p_a1 = _create_persona(db_session, sede_a.id, first_name="Ana", last_name="SedeA")
        p_a2 = _create_persona(db_session, sede_a.id, first_name="Carlos", last_name="SedeA")

        # Personas in Sede B (adversarial cross-tenant injection target)
        p_b1 = _create_persona(db_session, sede_b.id, first_name="David", last_name="SedeB")
        p_b2 = _create_persona(db_session, sede_b.id, first_name="Elena", last_name="SedeB")
        fake_uuid = uuid.uuid4()

        # Attack: User A calls /attendance/bulk mixing Sede A and Sede B personas + fake UUID
        bulk_payload = {
            "event_id": str(event_a.id),
            "session_date": "2026-09-15",
            "persona_ids": [
                str(p_a1.id),
                str(p_b1.id),
                str(p_b2.id),
                str(fake_uuid),
            ],
            "source": "manual",
        }

        resp = client.post(
            "/api/evangelism/attendance/bulk",
            json=bulk_payload,
            headers=headers_a,
        )
        assert resp.status_code == 200, f"Bulk attendance request failed: {resp.status_code} {resp.text}"
        data = resp.json()

        # Verification of response payload
        assert data["status"] == "success"
        # Only p_a1 must be recorded
        assert data["recorded"] == 1
        assert data["created"] == 1

        invalid_ids = [str(x) for x in data["invalid_persona_ids"]]
        assert str(p_b1.id) in invalid_ids, "Cross-tenant persona B1 was not flagged in invalid_persona_ids"
        assert str(p_b2.id) in invalid_ids, "Cross-tenant persona B2 was not flagged in invalid_persona_ids"
        assert str(fake_uuid) in invalid_ids, "Non-existent persona was not flagged in invalid_persona_ids"
        assert str(p_a1.id) not in invalid_ids

        # Direct Empirical Database Verification:
        # 1. Persona A1 record MUST exist in EventAttendance
        att_a1 = (
            db_session.query(models.EventAttendance)
            .filter(
                models.EventAttendance.event_id == event_a.id,
                models.EventAttendance.persona_id == p_a1.id,
            )
            .first()
        )
        assert att_a1 is not None, "Legitimate Sede A persona attendance was not created!"
        assert att_a1.attended is True

        # 2. Persona B1 and B2 records MUST NOT exist in EventAttendance
        att_b1 = (
            db_session.query(models.EventAttendance)
            .filter(
                models.EventAttendance.event_id == event_a.id,
                models.EventAttendance.persona_id == p_b1.id,
            )
            .first()
        )
        assert att_b1 is None, "SECURITY FAILURE: Cross-tenant persona B1 was registered in Sede A event attendance!"

        att_b2 = (
            db_session.query(models.EventAttendance)
            .filter(
                models.EventAttendance.event_id == event_a.id,
                models.EventAttendance.persona_id == p_b2.id,
            )
            .first()
        )
        assert att_b2 is None, "SECURITY FAILURE: Cross-tenant persona B2 was registered in Sede A event attendance!"

        att_fake = (
            db_session.query(models.EventAttendance)
            .filter(
                models.EventAttendance.event_id == event_a.id,
                models.EventAttendance.persona_id == fake_uuid,
            )
            .first()
        )
        assert att_fake is None, "SECURITY FAILURE: Fake UUID persona was registered in event attendance!"

    def test_adv_05_attendance_pdf_and_excel_uniform_404_anti_bola(self, client, db_session):
        """5. attendance_pdf and attendance_excel must return uniform 404 for non-existent vs cross-sede (0 BOLA oracle)."""
        user_a, persona_a, sede_a = seed_admin(db_session, email="admin_adv_05_a@test.com")
        headers_a = auth_headers(client, email="admin_adv_05_a@test.com")

        sede_b = models.Sede(
            id=uuid.uuid4(),
            nombre=f"Sede B Export {uuid.uuid4().hex[:4]}",
            ciudad="Pereira",
            es_activa=True,
        )
        db_session.add(sede_b)
        db_session.commit()

        cat = CategoriaEstrategia(nombre=f"Cat Adv 5 {uuid.uuid4().hex[:6]}")
        db_session.add(cat)
        db_session.commit()

        est_a = _create_strategy(db_session, sede_a.id, cat.id, nombre="Strategy A Export")
        est_b = _create_strategy(db_session, sede_b.id, cat.id, nombre="Strategy B Export")

        # Group in Sede A (legitimate)
        leader_a = _create_persona(db_session, sede_a.id, first_name="Lider", last_name="A")
        group_a = _create_group(db_session, sede_a.id, est_a.id, nombre="Grupo Sede A", lider_persona_id=leader_a.id)

        # Group in Sede B (attacker target)
        leader_b = _create_persona(db_session, sede_b.id, first_name="Lider", last_name="B")
        group_b = _create_group(db_session, sede_b.id, est_b.id, nombre="Grupo Sede B", lider_persona_id=leader_b.id)

        # Soft-deleted Group in Sede A
        group_a_del = _create_group(db_session, sede_a.id, est_a.id, nombre="Grupo A Deleted", deleted=True)

        fake_group_id = uuid.uuid4()

        # ── Test PDF Endpoint ──
        # Target 1: Non-existent group
        resp_pdf_fake = client.get(
            f"/api/evangelism/reports/group/{fake_group_id}/attendance-pdf",
            headers=headers_a,
        )
        assert resp_pdf_fake.status_code == 404
        assert resp_pdf_fake.json() == {"detail": "Grupo no encontrado"}

        # Target 2: Cross-sede group (Sede B)
        resp_pdf_cross = client.get(
            f"/api/evangelism/reports/group/{group_b.id}/attendance-pdf",
            headers=headers_a,
        )
        assert resp_pdf_cross.status_code == 404
        assert resp_pdf_cross.json() == {"detail": "Grupo no encontrado"}

        # Target 3: Soft-deleted group in Sede A
        resp_pdf_del = client.get(
            f"/api/evangelism/reports/group/{group_a_del.id}/attendance-pdf",
            headers=headers_a,
        )
        assert resp_pdf_del.status_code == 404
        assert resp_pdf_del.json() == {"detail": "Grupo no encontrado"}

        # Anti-BOLA verification: status code AND response body are identical across all 3
        assert resp_pdf_fake.status_code == resp_pdf_cross.status_code == resp_pdf_del.status_code == 404
        assert resp_pdf_fake.json() == resp_pdf_cross.json() == resp_pdf_del.json(), (
            "BOLA oracle leak! Responses differ between non-existent and cross-sede PDF requests"
        )

        # Legitimate Sede A PDF export
        resp_pdf_ok = client.get(
            f"/api/evangelism/reports/group/{group_a.id}/attendance-pdf",
            headers=headers_a,
        )
        assert resp_pdf_ok.status_code == 200
        assert resp_pdf_ok.headers.get("content-type") == "application/pdf"
        assert len(resp_pdf_ok.content) > 100

        # ── Test Excel Endpoint ──
        # Target 1: Non-existent group
        resp_excel_fake = client.get(
            f"/api/evangelism/reports/group/{fake_group_id}/attendance-excel",
            headers=headers_a,
        )
        assert resp_excel_fake.status_code == 404
        assert resp_excel_fake.json() == {"detail": "Grupo no encontrado"}

        # Target 2: Cross-sede group (Sede B)
        resp_excel_cross = client.get(
            f"/api/evangelism/reports/group/{group_b.id}/attendance-excel",
            headers=headers_a,
        )
        assert resp_excel_cross.status_code == 404
        assert resp_excel_cross.json() == {"detail": "Grupo no encontrado"}

        # Target 3: Soft-deleted group in Sede A
        resp_excel_del = client.get(
            f"/api/evangelism/reports/group/{group_a_del.id}/attendance-excel",
            headers=headers_a,
        )
        assert resp_excel_del.status_code == 404
        assert resp_excel_del.json() == {"detail": "Grupo no encontrado"}

        # Anti-BOLA verification: status code AND response body are identical
        assert resp_excel_fake.status_code == resp_excel_cross.status_code == resp_excel_del.status_code == 404
        assert resp_excel_fake.json() == resp_excel_cross.json() == resp_excel_del.json(), (
            "BOLA oracle leak! Responses differ between non-existent and cross-sede Excel requests"
        )

        # Legitimate Sede A Excel export
        resp_excel_ok = client.get(
            f"/api/evangelism/reports/group/{group_a.id}/attendance-excel",
            headers=headers_a,
        )
        assert resp_excel_ok.status_code == 200
        assert "spreadsheetml" in resp_excel_ok.headers.get("content-type", "")
        assert len(resp_excel_ok.content) > 100

    def test_adv_06_code_audit_zero_db_delete_and_zero_datetime_utcnow(self):
        """6. Rigorous static audit: zero db.delete() in evangelismo and zero datetime.utcnow across backend."""
        backend_dir = "/root/ccf/backend"

        # 1. Zero datetime.utcnow across the ENTIRE backend
        utcnow_matches = []
        for root, _, files in os.walk(backend_dir):
            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        for line_num, line in enumerate(f, 1):
                            if "datetime.utcnow" in line and not line.strip().startswith("#"):
                                utcnow_matches.append(f"{file_path}:{line_num}: {line.strip()}")

        assert len(utcnow_matches) == 0, "Found forbidden datetime.utcnow calls:\n" + "\n".join(utcnow_matches)

        # 2. Zero db.delete() in the Evangelismo subsystem
        evangelism_delete_matches = []
        for root, _, files in os.walk(backend_dir):
            for file in files:
                if file.endswith(".py") and ("evangelis" in file or "evangelis" in root):
                    file_path = os.path.join(root, file)
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        for line_num, line in enumerate(f, 1):
                            if "db.delete(" in line and not line.strip().startswith("#"):
                                evangelism_delete_matches.append(f"{file_path}:{line_num}: {line.strip()}")

        assert len(evangelism_delete_matches) == 0, "Found forbidden db.delete() in evangelismo:\n" + "\n".join(evangelism_delete_matches)
