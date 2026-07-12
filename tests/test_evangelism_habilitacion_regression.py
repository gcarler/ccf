"""
Evangelism — Regression tests for session enablement (habilitación) and attendance flow.

Coverage:
1. End-to-end: strategy → group → session (DESHABILITADO) → attendance blocked (403)
   → enable session → attendance succeeds → reported_at/offering_amount persisted.
2. Toggle individual: HABILITAR / DESHABILITAR / CERRAR.
3. Disabling a previously-enabled session blocks further attendance.
4. CERRADO session blocks attendance.
5. habilitar-todas / deshabilitar-todas bulk operations.
6. Cross-sede isolation: another sede's user cannot enable or report attendance.
7. First-time visitor triggers CRM bridge on enabled session.
8. reported_at is set when attendance is submitted.
9. offering_amount is persisted when included in attendance payload.

These tests are intentionally separate from the general coverage suite so that
any regression in the enablement gate is caught immediately and in isolation.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from backend import models
from backend.models_evangelism import (
    Asistencia,
    CategoriaEstrategia,
    EstrategiaEvangelismo,
    GrupoEvangelismo,
    HabilitacionSesionEnum,
    ParticipanteGrupo,
    RolPersonalizadoEstrategia,
    SesionGrupo,
)
from backend.models_crm_pipeline import CasoCRM, EtapaPipeline, PipelineCRM, TipoPipelineEnum
from backend.models_crm_pipeline import CanalOrigenEnum
from tests.conftest import TestingSessionLocal, auth_headers, seed_admin, seed_user_with_role


def _create_strategy_and_group(client, db_session, with_sessions=True):
    """Helper: creates a minimal strategy + group + participants + sessions."""
    admin, admin_persona, sede = seed_admin(db_session)

    categoria = CategoriaEstrategia(nombre="Cat Habilitacion")
    db_session.add(categoria)
    db_session.flush()

    estrategia = EstrategiaEvangelismo(
        nombre="Estrategia Habilitacion",
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
    for i in range(5):
        p = models.Persona(
            first_name=f"Hab{i}",
            last_name=f"Test{i}",
            email=f"hab{i}_{uuid.uuid4().hex[:4]}@ccf.test",
            phone=f"+57300{i:07d}",
            sede_id=sede.id,
            church_role="Miembro",
        )
        db_session.add(p)
        personas.append(p)
    db_session.flush()

    grupo = GrupoEvangelismo(
        nombre="Grupo Habilitacion",
        codigo=f"GH-{uuid.uuid4().hex[:6]}",
        sede_id=sede.id,
        estrategia_id=estrategia.id,
        ubicacion="Zona H",
        direccion="Calle H",
        capacidad=20,
        dia_reunion="Lunes",
        hora_reunion="19:00",
        lider_persona_id=personas[0].id,
        asistente_persona_id=personas[1].id,
        activo=True,
    )
    db_session.add(grupo)
    db_session.flush()

    for j in range(3):
        pg = ParticipanteGrupo(
            grupo_id=grupo.id,
            persona_id=personas[j].id,
            rol_base="LIDER" if j == 0 else "ASISTENTE",
            activo=True,
        )
        db_session.add(pg)
    db_session.flush()

    sesiones = []
    if with_sessions:
        for j in range(3):
            s = SesionGrupo(
                grupo_id=grupo.id,
                fecha_sesion=datetime(2026, 6, 8 + j * 7, tzinfo=timezone.utc),
                estado="PENDIENTE",
                estado_habilitacion=HabilitacionSesionEnum.DESHABILITADO.value,
                tema_estudio=f"Tema H{j}",
            )
            db_session.add(s)
            sesiones.append(s)
        db_session.flush()

    db_session.commit()
    for s in sesiones:
        db_session.refresh(s)

    return {
        "sede": sede,
        "estrategia": estrategia,
        "grupo": grupo,
        "personas": personas,
        "sesiones": sesiones,
        "categoria": categoria,
    }


class TestHabilitacionFlujoCompleto:
    """End-to-end regression for the enablement → attendance gate."""

    def test_sesion_nace_deshabilitada_y_bloquea_asistencia(self, client, db_session):
        seed_admin(db_session)
        headers = auth_headers(client)
        data = _create_strategy_and_group(client, db_session)
        sesion = data["sesiones"][0]
        persona = data["personas"][2]

        # 1. Verify session starts DESHABILITADO
        assert sesion.estado_habilitacion == "DESHABILITADO"

        # 2. Attendance must be blocked
        resp = client.post(
            f"/api/evangelism/sessions/{sesion.id}/attendance",
            json=[{"persona_id": str(persona.id), "status": "present"}],
            headers=headers,
        )
        assert resp.status_code == 403, resp.text
        assert "deshabilitado" in resp.json()["detail"].lower()

    def test_habilitar_individual_y_luego_asistencia_exitosa(self, client, db_session):
        seed_admin(db_session)
        headers = auth_headers(client)
        data = _create_strategy_and_group(client, db_session)
        sesion = data["sesiones"][0]
        persona = data["personas"][2]

        # Habilitar
        hab = client.patch(
            f"/api/evangelism/sessions/{sesion.id}/habilitacion",
            json={"accion": "HABILITAR"},
            headers=headers,
        )
        assert hab.status_code == 200, hab.text
        assert hab.json()["estado_habilitacion"] == "HABILITADO"

        # Asistencia ahora debe funcionar
        resp = client.post(
            f"/api/evangelism/sessions/{sesion.id}/attendance",
            json=[{"persona_id": str(persona.id), "status": "present"}],
            headers=headers,
        )
        assert resp.status_code == 200, resp.text

        # Verificar en DB con sesión fresca (el endpoint usa otra transacción)
        fresh = TestingSessionLocal()
        sesion_reloaded = fresh.query(SesionGrupo).filter(SesionGrupo.id == sesion.id).first()
        assert sesion_reloaded.reported_at is not None, (
            "Regression: reported_at quedó NULL tras asistencia exitosa."
        )
        asistencia = (
            fresh.query(Asistencia)
            .filter(Asistencia.sesion_id == sesion.id, Asistencia.persona_id == persona.id)
            .first()
        )
        fresh.close()
        assert asistencia is not None
        assert asistencia.estado == "presente"

    def test_registro_de_visitante_en_grupo_crea_caso_crm(self, client, db_session):
        admin, admin_persona, sede = seed_admin(db_session)
        headers = auth_headers(client, email=admin.email, password="testpass123")

        categoria = CategoriaEstrategia(nombre="Cat Visitante")
        db_session.add(categoria)
        db_session.flush()

        estrategia = EstrategiaEvangelismo(
            nombre="Estrategia Visitante",
            sede_id=sede.id,
            categoria_id=categoria.id,
            typology="relacional",
            strategy_type="geografica",
            frecuencia="SEMANAL",
            fecha_inicio=datetime(2026, 6, 1, tzinfo=timezone.utc),
            fecha_fin=datetime(2026, 7, 1, tzinfo=timezone.utc),
            activa=True,
        )
        db_session.add(estrategia)
        db_session.flush()

        grupo = GrupoEvangelismo(
            nombre="Grupo Visitantes",
            codigo=f"GV-{uuid.uuid4().hex[:6]}",
            sede_id=sede.id,
            estrategia_id=estrategia.id,
            lider_persona_id=admin_persona.id,
            activo=True,
        )
        db_session.add(grupo)
        db_session.commit()
        db_session.refresh(grupo)

        resp = client.post(
            "/api/evangelism/groups/visitors",
            json={
                "first_name": "Nuevo",
                "last_name": "Visitante",
                "phone": "+573001234567",
                "grupo_id": str(grupo.id),
            },
            headers=headers,
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["status"] == "created"
        assert body["first_name"] == "Nuevo"
        assert body["last_name"] == "Visitante"

        fresh = TestingSessionLocal()
        try:
            persona = (
                fresh.query(models.Persona)
                .filter(models.Persona.phone == "+573001234567")
                .first()
            )
            assert persona is not None
            assert str(persona.id) == body["persona_id"]
            assert persona.church_role == "Visitante"
            assert persona.origen_grupo_id == grupo.id
            case = (
                fresh.query(CasoCRM)
                .filter(CasoCRM.persona_id == persona.id)
                .filter(CasoCRM.origen_grupo_id == grupo.id)
                .first()
            )
            assert case is not None
            assert case.origen_canal == CanalOrigenEnum.EVANGELISMO
            assert case.titulo_caso.startswith("Seguimiento:")
            pipeline = (
                fresh.query(PipelineCRM)
                .filter(PipelineCRM.sede_id == sede.id)
                .filter(PipelineCRM.tipo == TipoPipelineEnum.NUEVOS_VISITANTES)
                .first()
            )
            assert pipeline is not None
            stage = (
                fresh.query(EtapaPipeline)
                .filter(EtapaPipeline.pipeline_id == pipeline.id)
                .filter(EtapaPipeline.deleted_at.is_(None))
                .first()
            )
            assert stage is not None
        finally:
            fresh.close()

    def test_deshabilitar_despues_de_habilitar_bloquea_asistencia(self, client, db_session):
        seed_admin(db_session)
        headers = auth_headers(client)
        data = _create_strategy_and_group(client, db_session)
        sesion = data["sesiones"][0]
        persona = data["personas"][2]

        # Habilitar → asistencia OK
        client.patch(
            f"/api/evangelism/sessions/{sesion.id}/habilitacion",
            json={"accion": "HABILITAR"},
            headers=headers,
        )
        r1 = client.post(
            f"/api/evangelism/sessions/{sesion.id}/attendance",
            json=[{"persona_id": str(persona.id), "status": "present"}],
            headers=headers,
        )
        assert r1.status_code == 200

        # Deshabilitar
        client.patch(
            f"/api/evangelism/sessions/{sesion.id}/habilitacion",
            json={"accion": "DESHABILITAR"},
            headers=headers,
        )

        # Nueva asistencia debe bloquearse
        persona2 = data["personas"][3]
        r2 = client.post(
            f"/api/evangelism/sessions/{sesion.id}/attendance",
            json=[{"persona_id": str(persona2.id), "status": "present"}],
            headers=headers,
        )
        assert r2.status_code == 403

    def test_cerrar_sesion_bloquea_asistencia(self, client, db_session):
        seed_admin(db_session)
        headers = auth_headers(client)
        data = _create_strategy_and_group(client, db_session)
        sesion = data["sesiones"][0]
        persona = data["personas"][2]

        # Habilitar primero
        client.patch(
            f"/api/evangelism/sessions/{sesion.id}/habilitacion",
            json={"accion": "HABILITAR"},
            headers=headers,
        )
        # Cerrar
        client.patch(
            f"/api/evangelism/sessions/{sesion.id}/habilitacion",
            json={"accion": "CERRAR"},
            headers=headers,
        )

        r = client.post(
            f"/api/evangelism/sessions/{sesion.id}/attendance",
            json=[{"persona_id": str(persona.id), "status": "present"}],
            headers=headers,
        )
        assert r.status_code == 403
        assert "cerrado" in r.json()["detail"].lower()

    def test_habilitar_todas_y_asistencia_por_lotes(self, client, db_session):
        seed_admin(db_session)
        headers = auth_headers(client)
        data = _create_strategy_and_group(client, db_session)
        estrategia = data["estrategia"]
        sesiones = data["sesiones"]
        personas = data["personas"]

        # Todas deshabilitadas inicialmente
        for s in sesiones:
            assert s.estado_habilitacion == "DESHABILITADO"

        # Habilitar todas
        resp = client.post(
            f"/api/evangelism/strategies/{estrategia.id}/habilitar-todas",
            headers=headers,
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["sesiones_habilitadas"] == len(sesiones)

        # Reportar asistencia en todas
        for sesion in sesiones:
            payload = [
                {"persona_id": str(personas[j].id), "status": "present"}
                for j in range(3)
            ]
            r = client.post(
                f"/api/evangelism/sessions/{sesion.id}/attendance",
                json=payload,
                headers=headers,
            )
            assert r.status_code == 200, r.text

            # Verificar reported_at con sesión fresca
            fresh = TestingSessionLocal()
            sesion_reloaded = fresh.query(SesionGrupo).filter(SesionGrupo.id == sesion.id).first()
            assert sesion_reloaded.reported_at is not None
            fresh.close()

    def test_deshabilitar_todas_bloquea_asistencia_en_todas(self, client, db_session):
        seed_admin(db_session)
        headers = auth_headers(client)
        data = _create_strategy_and_group(client, db_session)
        estrategia = data["estrategia"]
        sesiones = data["sesiones"]
        personas = data["personas"]

        # Habilitar todas primero
        client.post(
            f"/api/evangelism/strategies/{estrategia.id}/habilitar-todas",
            headers=headers,
        )
        # Deshabilitar todas
        client.post(
            f"/api/evangelism/strategies/{estrategia.id}/deshabilitar-todas",
            headers=headers,
        )

        for sesion in sesiones:
            r = client.post(
                f"/api/evangelism/sessions/{sesion.id}/attendance",
                json=[{"persona_id": str(personas[0].id), "status": "present"}],
                headers=headers,
            )
            assert r.status_code == 403, f"Sesión {sesion.id} no bloqueó asistencia"

    def test_primera_vez_en_sesion_habilitada_dispara_crm_bridge(self, client, db_session):
        seed_admin(db_session)
        headers = auth_headers(client)
        data = _create_strategy_and_group(client, db_session)
        sesion = data["sesiones"][0]
        persona = data["personas"][2]

        # Habilitar
        client.patch(
            f"/api/evangelism/sessions/{sesion.id}/habilitacion",
            json={"accion": "HABILITAR"},
            headers=headers,
        )

        # Primera vez
        resp = client.post(
            f"/api/evangelism/sessions/{sesion.id}/attendance",
            json=[{"persona_id": str(persona.id), "status": "first_time"}],
            headers=headers,
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert "metadata" in body
        # CRM bridge se dispara
        assert body.get("evento_integracion") is not None

    def test_offering_amount_persistido_en_asistencia_faro(self, client, db_session):
        seed_admin(db_session)
        headers = auth_headers(client)
        data = _create_strategy_and_group(client, db_session)
        sesion = data["sesiones"][0]
        persona = data["personas"][2]

        # Habilitar
        client.patch(
            f"/api/evangelism/sessions/{sesion.id}/habilitacion",
            json={"accion": "HABILITAR"},
            headers=headers,
        )

        # Asistencia vía FARO endpoint con offering_amount
        resp = client.post(
            f"/api/evangelism/grupos/sessions/{sesion.id}/attendance",
            json={
                "persona_ids": [str(persona.id)],
                "offering_amount": 125.50,
            },
            headers=headers,
        )
        assert resp.status_code == 200, resp.text

        # Verificar en DB con sesión fresca
        fresh = TestingSessionLocal()
        sesion_reloaded = fresh.query(SesionGrupo).filter(SesionGrupo.id == sesion.id).first()
        assert sesion_reloaded.offering_amount is not None
        assert float(sesion_reloaded.offering_amount) == pytest.approx(125.50, abs=0.01)
        fresh.close()

    def test_reported_at_se_setea_al_reportar_asistencia(self, client, db_session):
        seed_admin(db_session)
        headers = auth_headers(client)
        data = _create_strategy_and_group(client, db_session)
        sesion = data["sesiones"][0]
        persona = data["personas"][2]

        # Antes debe ser None
        assert sesion.reported_at is None

        client.patch(
            f"/api/evangelism/sessions/{sesion.id}/habilitacion",
            json={"accion": "HABILITAR"},
            headers=headers,
        )
        client.post(
            f"/api/evangelism/sessions/{sesion.id}/attendance",
            json=[{"persona_id": str(persona.id), "status": "present"}],
            headers=headers,
        )

        # Re-query con sesión fresca
        fresh = TestingSessionLocal()
        sesion_reloaded = fresh.query(SesionGrupo).filter(SesionGrupo.id == sesion.id).first()
        assert sesion_reloaded.reported_at is not None
        # SQLite puede devolver naive; lo importante es que no sea None
        assert isinstance(sesion_reloaded.reported_at, datetime)
        fresh.close()

    # Nota: los tests básicos de toggle (acción inválida, 404, habilitar sin grupos)
    # ya existen en test_evangelism_module_coverage.py; no se duplican aquí.


class TestHabilitacionSedeIsolation:
    """Cross-sede regression: enablement and attendance are sede-scoped."""

    def test_usuario_otra_sede_no_puede_habilitar(self, client, db_session):
        admin, _, sede_a = seed_admin(db_session, email="admin_a@ccf.test")

        # Crear estrategia en sede A
        categoria = CategoriaEstrategia(nombre="Cat Iso")
        db_session.add(categoria)
        db_session.flush()

        est = EstrategiaEvangelismo(
            nombre="Estrategia A",
            sede_id=sede_a.id,
            categoria_id=categoria.id,
            frecuencia="SEMANAL",
            fecha_inicio=datetime(2026, 6, 1, tzinfo=timezone.utc),
            fecha_fin=datetime(2026, 6, 22, tzinfo=timezone.utc),
            activa=True,
        )
        db_session.add(est)
        db_session.flush()

        grupo = GrupoEvangelismo(
            nombre="Grupo A", sede_id=sede_a.id, estrategia_id=est.id,
            ubicacion="u", capacidad=10, activo=True,
        )
        db_session.add(grupo)
        db_session.flush()

        sesion = SesionGrupo(
            grupo_id=grupo.id,
            fecha_sesion=datetime(2026, 6, 8, tzinfo=timezone.utc),
            estado="PENDIENTE",
            estado_habilitacion="DESHABILITADO",
        )
        db_session.add(sesion)
        db_session.commit()

        # Usuario de sede B intenta habilitar
        _, _, sede_b = seed_user_with_role(
            db_session, role_name="ADMIN", email="admin_b@ccf.test",
        )
        headers_b = auth_headers(client, email="admin_b@ccf.test")

        resp = client.patch(
            f"/api/evangelism/sessions/{sesion.id}/habilitacion",
            json={"accion": "HABILITAR"},
            headers=headers_b,
        )
        # Debe retornar 404 porque la sesión no pertenece a su sede
        assert resp.status_code == 404

    def test_usuario_otra_sede_no_puede_reportar_asistencia(self, client, db_session):
        admin, _, sede_a = seed_admin(db_session, email="admin_a2@ccf.test")

        categoria = CategoriaEstrategia(nombre="Cat Iso2")
        db_session.add(categoria)
        db_session.flush()

        est = EstrategiaEvangelismo(
            nombre="Estrategia A2",
            sede_id=sede_a.id,
            categoria_id=categoria.id,
            frecuencia="SEMANAL",
            fecha_inicio=datetime(2026, 6, 1, tzinfo=timezone.utc),
            fecha_fin=datetime(2026, 6, 22, tzinfo=timezone.utc),
            activa=True,
        )
        db_session.add(est)
        db_session.flush()

        p = models.Persona(
            first_name="P", last_name="A", sede_id=sede_a.id,
            email="pa@ccf.test", phone="3000000001",
        )
        db_session.add(p)
        db_session.flush()

        grupo = GrupoEvangelismo(
            nombre="Grupo A2", sede_id=sede_a.id, estrategia_id=est.id,
            ubicacion="u", capacidad=10, activo=True,
        )
        db_session.add(grupo)
        db_session.flush()

        pg = ParticipanteGrupo(
            grupo_id=grupo.id, persona_id=p.id, rol_base="Miembro", activo=True,
        )
        db_session.add(pg)

        sesion = SesionGrupo(
            grupo_id=grupo.id,
            fecha_sesion=datetime(2026, 6, 8, tzinfo=timezone.utc),
            estado="PENDIENTE",
            estado_habilitacion="HABILITADO",
        )
        db_session.add(sesion)
        db_session.commit()

        # Usuario sede B intenta reportar asistencia
        seed_user_with_role(db_session, role_name="ADMIN", email="admin_b2@ccf.test")
        headers_b = auth_headers(client, email="admin_b2@ccf.test")

        resp = client.post(
            f"/api/evangelism/sessions/{sesion.id}/attendance",
            json=[{"persona_id": str(p.id), "status": "present"}],
            headers=headers_b,
        )
        # Debe fallar con 404 (sesión no en su sede)
        assert resp.status_code == 404


class TestHabilitacionSoftDeletedSession:
    """Regression: soft-deleted sessions cannot be enabled or receive attendance."""

    def test_sesion_soft_deleted_no_acepta_habilitacion(self, client, db_session):
        seed_admin(db_session)
        headers = auth_headers(client)
        data = _create_strategy_and_group(client, db_session)
        sesion = data["sesiones"][0]

        # Soft-delete la sesión
        sesion.deleted_at = datetime.now(timezone.utc)
        db_session.commit()

        resp = client.patch(
            f"/api/evangelism/sessions/{sesion.id}/habilitacion",
            json={"accion": "HABILITAR"},
            headers=headers,
        )
        assert resp.status_code == 404

    def test_sesion_soft_deleted_no_acepta_asistencia(self, client, db_session):
        seed_admin(db_session)
        headers = auth_headers(client)
        data = _create_strategy_and_group(client, db_session)
        sesion = data["sesiones"][0]
        persona = data["personas"][2]

        # Habilitar primero
        client.patch(
            f"/api/evangelism/sessions/{sesion.id}/habilitacion",
            json={"accion": "HABILITAR"},
            headers=headers,
        )
        # Soft-delete
        sesion.deleted_at = datetime.now(timezone.utc)
        db_session.commit()

        resp = client.post(
            f"/api/evangelism/sessions/{sesion.id}/attendance",
            json=[{"persona_id": str(persona.id), "status": "present"}],
            headers=headers,
        )
        assert resp.status_code == 404
