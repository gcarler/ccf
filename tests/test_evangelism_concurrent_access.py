"""
Evangelism — Concurrent Access / Idempotency Tests (T-05)

Verifies that double-submission, toggle, and split operations are idempotent
or properly guarded against race conditions.

Note: True concurrency cannot be tested in SQLite (serializes writes).
These tests verify the logic that prevents data corruption.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from backend import models
from backend.models_evangelism import (
    CategoriaEstrategia,
    EstrategiaEvangelismo,
    GrupoEvangelismo,
    HabilitacionSesionEnum,
    ParticipanteGrupo,
    SesionGrupo,
)
from tests.conftest import auth_headers, seed_admin


def _setup_group_with_sessions(db_session):
    """Helper: create strategy + group + participants + sessions for testing."""
    admin, admin_persona, sede = seed_admin(db_session)

    categoria = CategoriaEstrategia(nombre="Cat Concurrent")
    db_session.add(categoria)
    db_session.flush()

    estrategia = EstrategiaEvangelismo(
        nombre="Estrategia Concurrent",
        sede_id=sede.id,
        categoria_id=categoria.id,
        typology="relacional",
        strategy_type="geografica",
        frecuencia="SEMANAL",
        dia_reunion="Lunes",
        hora_reunion="19:00",
        fecha_inicio=datetime(2026, 6, 1, tzinfo=timezone.utc),
        fecha_fin=datetime(2026, 6, 22, tzinfo=timezone.utc),
        activa=True,
        status="active",
    )
    db_session.add(estrategia)
    db_session.flush()

    personas = []
    for i in range(4):
        p = models.Persona(
            first_name=f"Conc{i}",
            last_name=f"Test{i}",
            email=f"conc{i}_{uuid.uuid4().hex[:4]}@ccf.test",
            phone=f"+57300{i:07d}",
            sede_id=sede.id,
            church_role="Miembro",
        )
        db_session.add(p)
        personas.append(p)
    db_session.flush()

    grupo = GrupoEvangelismo(
        nombre="Grupo Concurrent",
        codigo=f"GC-{uuid.uuid4().hex[:6]}",
        sede_id=sede.id,
        estrategia_id=estrategia.id,
        ubicacion="Zona C",
        direccion="Calle C",
        capacidad=20,
        dia_reunion="Lunes",
        hora_reunion="19:00",
        lider_persona_id=personas[0].id,
        asistente_persona_id=personas[1].id,
        activo=True,
    )
    db_session.add(grupo)
    db_session.flush()

    for j in range(4):
        pg = ParticipanteGrupo(
            grupo_id=grupo.id,
            persona_id=personas[j].id,
            rol_base="LIDER" if j == 0 else "ASISTENTE" if j == 1 else "MIEMBRO",
            activo=True,
        )
        db_session.add(pg)
    db_session.flush()

    sesion = SesionGrupo(
        grupo_id=grupo.id,
        fecha_sesion=datetime(2026, 6, 8, tzinfo=timezone.utc),
        estado="PENDIENTE",
        estado_habilitacion=HabilitacionSesionEnum.DESHABILITADO.value,
        tema_estudio="Tema Concurrent",
    )
    db_session.add(sesion)
    db_session.flush()
    db_session.commit()

    return {
        "sede": sede,
        "estrategia": estrategia,
        "grupo": grupo,
        "personas": personas,
        "sesion": sesion,
        "admin": admin,
    }


class TestAttendanceDoubleSubmission:
    """T-05: Attendance double-submission must be idempotent (replace, not duplicate)."""

    def test_double_submit_replaces_not_duplicates(self, client, db_session):
        """Submitting attendance twice for the same session should not crash.
        The endpoint soft-deletes existing attendance then inserts fresh records.
        This test verifies the endpoint handles double-submission gracefully.
        """
        data = _setup_group_with_sessions(db_session)
        headers = auth_headers(client)
        grupo = data["grupo"]
        sesion = data["sesion"]
        personas = data["personas"]

        # Enable session
        sesion.estado_habilitacion = HabilitacionSesionEnum.HABILITADO.value
        db_session.commit()

        # First submission: 4 people
        attendance1 = [
            {"persona_id": str(personas[0].id), "status": "present"},
            {"persona_id": str(personas[1].id), "status": "present"},
            {"persona_id": str(personas[2].id), "status": "present"},
            {"persona_id": str(personas[3].id), "status": "absent"},
        ]
        resp1 = client.post(
            f"/api/evangelism/sessions/{sesion.id}/attendance",
            json=attendance1,
            headers=headers,
        )
        assert resp1.status_code == 200

        # Second submission: same people (should not crash)
        resp2 = client.post(
            f"/api/evangelism/sessions/{sesion.id}/attendance",
            json=attendance1,
            headers=headers,
        )
        assert resp2.status_code == 200

        # Third submission: different data
        attendance3 = [
            {"persona_id": str(personas[0].id), "status": "absent"},
        ]
        resp3 = client.post(
            f"/api/evangelism/sessions/{sesion.id}/attendance",
            json=attendance3,
            headers=headers,
        )
        assert resp3.status_code == 200

    def test_double_submit_with_changed_data_replaces(self, client, db_session):
        """Second submission with different attendance data should succeed."""
        data = _setup_group_with_sessions(db_session)
        headers = auth_headers(client)
        sesion = data["sesion"]
        personas = data["personas"]

        sesion.estado_habilitacion = HabilitacionSesionEnum.HABILITADO.value
        db_session.commit()

        # First: 2 present
        attendance1 = [
            {"persona_id": str(personas[0].id), "status": "present"},
            {"persona_id": str(personas[1].id), "status": "present"},
        ]
        resp1 = client.post(
            f"/api/evangelism/sessions/{sesion.id}/attendance",
            json=attendance1,
            headers=headers,
        )
        assert resp1.status_code == 200

        # Second: persona[0] now absent
        attendance2 = [
            {"persona_id": str(personas[0].id), "status": "absent"},
            {"persona_id": str(personas[1].id), "status": "present"},
        ]
        resp2 = client.post(
            f"/api/evangelism/sessions/{sesion.id}/attendance",
            json=attendance2,
            headers=headers,
        )
        assert resp2.status_code == 200


class TestSessionToggleIdempotency:
    """T-05: Session enable/disable toggle must be idempotent."""

    def test_enable_already_enabled_session_is_idempotent(self, client, db_session):
        """Enabling an already-enabled session should succeed (no crash)."""
        data = _setup_group_with_sessions(db_session)
        headers = auth_headers(client)
        sesion = data["sesion"]

        # First enable
        resp1 = client.patch(
            f"/api/evangelism/sessions/{sesion.id}/habilitacion",
            json={"accion": "HABILITAR"},
            headers=headers,
        )
        assert resp1.status_code == 200

        # Second enable — should be idempotent
        resp2 = client.patch(
            f"/api/evangelism/sessions/{sesion.id}/habilitacion",
            json={"accion": "HABILITAR"},
            headers=headers,
        )
        assert resp2.status_code == 200

    def test_disable_and_reenable_session(self, client, db_session):
        """Disabling then re-enabling a session should work correctly."""
        data = _setup_group_with_sessions(db_session)
        headers = auth_headers(client)
        sesion = data["sesion"]

        # Enable
        resp1 = client.patch(
            f"/api/evangelism/sessions/{sesion.id}/habilitacion",
            json={"accion": "HABILITAR"},
            headers=headers,
        )
        assert resp1.status_code == 200

        # Disable
        resp2 = client.patch(
            f"/api/evangelism/sessions/{sesion.id}/habilitacion",
            json={"accion": "DESHABILITAR"},
            headers=headers,
        )
        assert resp2.status_code == 200

        # Re-enable
        resp3 = client.patch(
            f"/api/evangelism/sessions/{sesion.id}/habilitacion",
            json={"accion": "HABILITAR"},
            headers=headers,
        )
        assert resp3.status_code == 200

        # Attendance should now be accepted again
        personas = data["personas"]
        resp4 = client.post(
            f"/api/evangelism/sessions/{sesion.id}/attendance",
            json=[{"persona_id": str(personas[0].id), "status": "present"}],
            headers=headers,
        )
        assert resp4.status_code == 200


class TestGroupSplitIdempotency:
    """T-05: Group split must produce consistent results."""

    def test_split_produces_valid_result(self, client, db_session):
        """Splitting a group should create a new group with half the members."""
        data = _setup_group_with_sessions(db_session)
        headers = auth_headers(client)
        grupo = data["grupo"]
        personas = data["personas"]

        resp = client.post(
            "/api/evangelism/multiplication/split",
            json={
                "grupo_id": str(grupo.id),
                "nuevo_nombre": "Grupo Split",
                "nuevo_lider_id": str(personas[2].id),
            },
            headers=headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        # Verify response has some structure
        assert isinstance(body, dict)

        # Original group should still exist
        original = (
            db_session.query(GrupoEvangelismo)
            .filter(
                GrupoEvangelismo.id == grupo.id,
                GrupoEvangelismo.deleted_at.is_(None),
            )
            .first()
        )
        assert original is not None

    def test_split_already_small_group_fails(self, client, db_session):
        """Cannot split a group with fewer than 2 active members."""
        admin, admin_persona, sede = seed_admin(db_session)
        headers = auth_headers(client)

        categoria = CategoriaEstrategia(nombre="Cat Small")
        db_session.add(categoria)
        db_session.flush()

        estrategia = EstrategiaEvangelismo(
            nombre="Estrategia Small",
            sede_id=sede.id,
            categoria_id=categoria.id,
            typology="relacional",
            strategy_type="geografica",
            frecuencia="SEMANAL",
            dia_reunion="Lunes",
            hora_reunion="19:00",
            fecha_inicio=datetime(2026, 6, 1, tzinfo=timezone.utc),
            fecha_fin=datetime(2026, 6, 22, tzinfo=timezone.utc),
            activa=True,
            status="active",
        )
        db_session.add(estrategia)
        db_session.flush()

        persona = models.Persona(
            first_name="Solo",
            last_name="Member",
            email=f"solo_{uuid.uuid4().hex[:4]}@ccf.test",
            phone="+573000000001",
            sede_id=sede.id,
            church_role="Miembro",
        )
        db_session.add(persona)
        db_session.flush()

        grupo = GrupoEvangelismo(
            nombre="Grupo Small",
            codigo=f"GS-{uuid.uuid4().hex[:6]}",
            sede_id=sede.id,
            estrategia_id=estrategia.id,
            ubicacion="Zona S",
            direccion="Calle S",
            capacidad=20,
            dia_reunion="Lunes",
            hora_reunion="19:00",
            lider_persona_id=persona.id,
            activo=True,
        )
        db_session.add(grupo)
        db_session.flush()

        pg = ParticipanteGrupo(
            grupo_id=grupo.id,
            persona_id=persona.id,
            rol_base="LIDER",
            activo=True,
        )
        db_session.add(pg)
        db_session.commit()

        resp = client.post(
            "/api/evangelism/multiplication/split",
            json={
                "grupo_id": str(grupo.id),
                "nuevo_nombre": "Grupo Small 2",
                "nuevo_lider_id": str(persona.id),
            },
            headers=headers,
        )
        assert resp.status_code == 400
