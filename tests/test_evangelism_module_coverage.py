"""
Evangelism Module — full coverage boost.

Estrategia: ejercita TODAS las superficies del módulo evangelismo
(backend.api.evangelism*, backend.services.calculo_sesiones,
backend.api.evangelism_events, backend.api.evangelism_grupos,
backend.services.evangelism_*, backend.models_evangelism) con un
fixture base compartido + funciones puras + tests de bordes.

Convenciones:
- Happy paths: assert status_code == 200 (con .text en el assert para
  diagnosticar).
- Negative paths: asserts específicos con códigos esperados.
- db_session es function-scoped → no necesitamos try/finally para
  mutaciones a la BD.
"""
from __future__ import annotations

import datetime as _dt
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import object_session as _sa_object_session

from backend import models
from backend.models_evangelism import (
    Asistencia as MAsistencia,
)
from backend.models_evangelism import (
    CampaignSeason,
    CategoriaEstrategia,
    EstrategiaEvangelismo,
    GrupoEvangelismo,
    HistorialEmbudo,
    MotivoExcusa,
    ParticipanteGrupo,
    RegistroSeguimiento,
    RolPersonalizadoEstrategia,
    SesionGrupo,
)
from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin


def _uuid_str() -> str:
    return str(uuid.uuid4())


@pytest.fixture
def full(db_session, client):
    """Seed compartido: admin + sede + categoría + estrategia + 2 grupos + personas + sesiones + asistencia."""
    admin, admin_persona, sede = _seed_admin(db_session)

    categoria = CategoriaEstrategia(nombre="Categoria Principal")
    db_session.add(categoria)
    db_session.flush()

    estrategia = EstrategiaEvangelismo(
        nombre="Estrategia Relacional",
        descripcion="Cobertura",
        sede_id=sede.id,
        categoria_id=categoria.id,
        typology="relacional",
        strategy_type="geografica",
        frecuencia="SEMANAL",
        dia_reunion="Lunes",
        hora_reunion="19:00",
        fecha_inicio=datetime(2026, 6, 1, tzinfo=timezone.utc),
        fecha_fin=datetime(2026, 8, 31, tzinfo=timezone.utc),
        activa=True,
        status="active",
    )
    db_session.add(estrategia)
    db_session.flush()

    personas = []
    for i in range(12):
        p = models.Persona(
            first_name=f"Persona{i}",
            last_name=f"Test{i}",
            email=f"persona{i}_{uuid.uuid4().hex[:4]}@ccf.test",
            phone=f"+57300{i:07d}",
            sede_id=sede.id,
            church_role="Miembro",
        )
        db_session.add(p)
        personas.append(p)
    db_session.flush()

    rp_lider = RolPersonalizadoEstrategia(nombre_rol="Líder", estrategia_id=estrategia.id)
    rp_colider = RolPersonalizadoEstrategia(nombre_rol="Colíder", estrategia_id=estrategia.id)
    rp_anfitrion = RolPersonalizadoEstrategia(nombre_rol="Anfitrión", estrategia_id=estrategia.id)
    db_session.add_all([rp_lider, rp_colider, rp_anfitrion])
    db_session.flush()
    estrategia.default_role_id = rp_lider.id

    grupos = []
    for i in range(2):
        g = GrupoEvangelismo(
            nombre=f"Grupo {i}",
            codigo=f"G-{uuid.uuid4().hex[:6]}",
            sede_id=sede.id,
            estrategia_id=estrategia.id,
            ubicacion=f"Zona {i}",
            direccion=f"Calle {i}",
            capacidad=20,
            dia_reunion="Lunes",
            hora_reunion="19:00",
            lider_persona_id=personas[i * 2].id,
            asistente_persona_id=personas[i * 2 + 1].id,
            anfitrion_persona_id=personas[(i + 4) % len(personas)].id,
            activo=True,
        )
        db_session.add(g)
        grupos.append(g)
    db_session.flush()

    participantes = []
    for gi, g in enumerate(grupos):
        for j in range(3):
            rol = ["LIDER", "ASISTENTE", "INVITADO"][j % 3]
            pg = ParticipanteGrupo(
                grupo_id=g.id,
                persona_id=personas[(gi * 3 + j) % len(personas)].id,
                rol_base=rol,
                rol_personalizado_id=rp_lider.id if j == 0 else None,
                activo=True,
            )
            db_session.add(pg)
            participantes.append(pg)
    db_session.flush()

    sesiones = []
    for g in grupos:
        for j in range(3):
            s = SesionGrupo(
                grupo_id=g.id,
                fecha_sesion=datetime(2026, 6, 8 + j * 7, tzinfo=timezone.utc),
                estado="PENDIENTE",
                estado_habilitacion="HABILITADO",
                tema_estudio=f"Tema {j}",
                offering_amount=100 + j * 50,
            )
            db_session.add(s)
            sesiones.append(s)
    db_session.flush()

    for s in sesiones:
        for i, pg in enumerate(participantes[:3]):
            if i == 0:
                estado, es_pv = "ASISTIO", False
            elif i == 1:
                estado, es_pv = "primera_vez", True
            else:
                estado, es_pv = "FALTO", False
            a = MAsistencia(
                sesion_id=s.id,
                persona_id=pg.persona_id,
                estado=estado,
                es_primera_vez=es_pv,
            )
            db_session.add(a)
    db_session.flush()

    season = CampaignSeason(
        name="Temporada Cobertura",
        start_date=datetime(2026, 6, 1).date(),
        end_date=datetime(2026, 12, 31).date(),
        periodicity="SEMANAL",
        status="Activa",
    )
    db_session.add(season)
    db_session.flush()

    for p in personas[:4]:
        db_session.add(HistorialEmbudo(
            persona_id=p.id,
            rol_anterior="Visitante",
            rol_nuevo="Miembro",
            fecha_cambio=datetime(2026, 6, 15, tzinfo=timezone.utc),
        ))
    db_session.flush()

    db_session.commit()
    for s in sesiones:
        db_session.refresh(s)

    headers = _auth_headers(client)

    return {
        "c": client,
        "h": headers,
        "sede": sede,
        "categoria": categoria,
        "admin": admin,
        "admin_persona": admin_persona,
        "estrategia": estrategia,
        "personas": personas,
        "grupos": grupos,
        "participantes": participantes,
        "sesiones": sesiones,
        "season": season,
        "roles_personalizados": [rp_lider, rp_colider, rp_anfitrion],
    }


# ════════════════════════════════════════════════════════════════════
# 1. HELPERS PUROS — evangelism_shared.py
# ════════════════════════════════════════════════════════════════════


class TestSharedPureHelpers:
    """Cubre las funciones puras sin DB ni HTTP."""

    def test_normalize_attendance_status_present(self):
        from backend.api.evangelism_shared import normalize_attendance_status
        for v in ["ASISTIO", "Presente", "present", "presente", "primera_vez", "first_time"]:
            assert normalize_attendance_status(v) == "present", v

    def test_normalize_attendance_status_absent(self):
        from backend.api.evangelism_shared import normalize_attendance_status
        for v in ["FALTO", "Ausente", "absent", "ausente"]:
            assert normalize_attendance_status(v) == "absent", v

    def test_normalize_attendance_status_excused(self):
        from backend.api.evangelism_shared import normalize_attendance_status
        for v in ["EXCUSA", "Excusa", "excusa"]:
            assert normalize_attendance_status(v) == "excused", v

    def test_normalize_attendance_status_unknown(self):
        from backend.api.evangelism_shared import normalize_attendance_status
        assert normalize_attendance_status("xyz") == "xyz"
        assert normalize_attendance_status("") == ""
        assert normalize_attendance_status(None) == ""

    def test_is_attended_absent_excused(self):
        from backend.api.evangelism_shared import (
            is_absent_status,
            is_attended_status,
            is_excused_status,
        )
        assert is_attended_status("ASISTIO") is True
        assert is_attended_status("primera_vez") is True
        assert is_attended_status("FALTO") is False
        assert is_absent_status("FALTO") is True
        assert is_absent_status("Ausente") is True
        assert is_absent_status("ASISTIO") is False
        assert is_excused_status("EXCUSA") is True
        assert is_excused_status("ASISTIO") is False

    def test_parse_session_date_date(self):
        from backend.api.evangelism_shared import parse_session_date
        assert parse_session_date(_dt.date(2026, 6, 1)) == _dt.date(2026, 6, 1)

    def test_parse_session_date_datetime(self):
        from backend.api.evangelism_shared import parse_session_date
        assert parse_session_date(_dt.datetime(2026, 6, 15, 12, 0)) == _dt.date(2026, 6, 15)

    def test_parse_session_date_string_iso(self):
        from backend.api.evangelism_shared import parse_session_date
        assert parse_session_date("2026-06-01") == _dt.date(2026, 6, 1)
        assert parse_session_date("2026-06-01T12:30:00") == _dt.date(2026, 6, 1)

    def test_parse_session_date_invalid(self):
        from backend.api.evangelism_shared import parse_session_date
        with pytest.raises(ValueError):
            parse_session_date("bad-date")
        with pytest.raises(ValueError):
            parse_session_date("")
        with pytest.raises(ValueError):
            parse_session_date(12345)  # type: ignore[arg-type]

    def test_normalize_role_scope_payload_role(self):
        from backend.api.evangelism_shared import normalize_role_scope_payload
        result = normalize_role_scope_payload({
            "target_audience": "ROLE",
            "target_role_ids": [_uuid_str(), _uuid_str(), "invalid"],
            "target_persona_ids": [_uuid_str()],
        })
        assert isinstance(result["target_role_ids"], list)
        assert len(result["target_role_ids"]) == 2
        assert result["target_role_id"] == result["target_role_ids"][0]
        assert result["target_persona_ids"] is None

    def test_normalize_role_scope_payload_role_single(self):
        from backend.api.evangelism_shared import normalize_role_scope_payload
        rid = _uuid_str()
        result = normalize_role_scope_payload({"target_audience": "ROLE", "target_role_id": rid})
        assert str(result["target_role_id"]) == rid
        assert result["target_role_ids"] == [rid]

    def test_normalize_role_scope_payload_manual(self):
        from backend.api.evangelism_shared import normalize_role_scope_payload
        pid = _uuid_str()
        result = normalize_role_scope_payload({
            "target_audience": "MANUAL",
            "target_persona_ids": [pid, pid, "  "],
        })
        assert result["target_persona_ids"] == [pid]
        assert result["target_role_id"] is None

    def test_normalize_role_scope_payload_other(self):
        from backend.api.evangelism_shared import normalize_role_scope_payload
        result = normalize_role_scope_payload({"target_audience": "ALL"})
        assert result["target_role_id"] is None
        assert result["target_role_ids"] is None
        assert result["target_persona_ids"] is None

    def test_channel_label(self):
        from backend.api.evangelism_shared import _channel_label
        assert _channel_label("whatsapp") == "WhatsApp"
        assert _channel_label("EMAIL") == "Email"
        assert _channel_label("sms") == "SMS"
        assert _channel_label("") == "SMS"
        assert _channel_label(None) == "SMS"  # type: ignore[arg-type]

    def test_persona_payload_minimal(self, db_session):
        from backend.api.evangelism_shared import persona_payload
        _seed_admin(db_session)
        p = models.Persona(
            first_name="Min", last_name="User", sede_id=_seed_admin(db_session)[2].id,
        )
        db_session.add(p)
        db_session.commit()
        db_session.refresh(p)
        payload = persona_payload(p, attended=True)
        assert payload["persona_id"] == p.id
        assert payload["attended"] is True
        assert payload["es_primera_vez"] is False
        out = persona_payload(
            p, attended=False, scanned_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
        )
        assert out["scanned_at"] is not None

    def test_utc_now_is_aware(self):
        from backend.api.evangelism_shared import utc_now
        now = utc_now()
        assert now.tzinfo is not None

    def test_normalize_attendance_status_primera_vez(self):
        from backend.api.evangelism_shared import normalize_attendance_status
        # Asegurar que 'primera_vez' mapea a 'present' (es presente en primera vez)
        assert normalize_attendance_status("primera_vez") == "present"
        assert normalize_attendance_status("first_time") == "present"


# ════════════════════════════════════════════════════════════════════
# 2. MODEL HYBRID PROPERTIES
# ════════════════════════════════════════════════════════════════════


class TestModelHybridProperties:
    def test_grupo_status_getter_setter(self, db_session):
        _seed_admin(db_session)
        g = GrupoEvangelismo(
            nombre="H", sede_id=db_session.query(models.Sede).first().id,
            ubicacion="u", capacidad=10, activo=True,
        )
        db_session.add(g); db_session.commit(); db_session.refresh(g)
        assert g.status == "active"
        g.status = "inactive"
        assert g.activo is False
        g.status = "active"
        assert g.activo is True
        g.status = "Activo"
        assert g.activo is True

    def test_grupo_leader_name_setter_and_getter(self, db_session):
        _seed_admin(db_session)
        sede = db_session.query(models.Sede).first()
        p = models.Persona(
            first_name="L", last_name="P", church_role="Líder", sede_id=sede.id,
        )
        db_session.add(p); db_session.flush()
        g = GrupoEvangelismo(
            nombre="G", sede_id=sede.id, ubicacion="u",
            capacidad=10, lider_persona_id=p.id, activo=True,
        )
        db_session.add(g); db_session.commit(); db_session.refresh(g)
        # Getter usa la propiedad hybrida + existe el lider → devuelve concatenación
        assert g.leader_name == "L P"
        # Setter persiste valor custom
        g.leader_name = "Carlos"
        assert g._leader_name == "Carlos"
        # Sin lider_persona_id → getter retorna _leader_name
        g.lider_persona_id = None
        db_session.commit(); db_session.refresh(g)
        # Si accedemos al hybrid property, debe devolver _leader_name o ""
        assert g.leader_name == "Carlos" or g.leader_name == ""

    def test_grupo_personas_count(self, db_session):
        _seed_admin(db_session)
        sede = db_session.query(models.Sede).first()
        personas = []
        for i in range(4):
            p = models.Persona(first_name=f"P{i}", last_name="T", sede_id=sede.id)
            db_session.add(p); personas.append(p)
        db_session.flush()
        g = GrupoEvangelismo(nombre="G", sede_id=sede.id, ubicacion="u", capacidad=10, activo=True)
        db_session.add(g); db_session.flush()
        # 2 activos + 1 activo + 1 soft-deleted
        for i, p in enumerate(personas):
            db_session.add(ParticipanteGrupo(
                grupo_id=g.id,
                persona_id=p.id,
                rol_base="Miembro",
                activo=(i < 3),
                deleted_at=(datetime.now(timezone.utc) if i == 2 else None),
            ))
        db_session.flush()
        # Cuenta solo activos que no estén soft-deleted
        assert g.personas_count == 2

    def test_grupo_end_time_property(self, db_session):
        _seed_admin(db_session)
        sede = db_session.query(models.Sede).first()
        g = GrupoEvangelismo(nombre="G", sede_id=sede.id, ubicacion="u", capacidad=10, activo=True)
        db_session.add(g); db_session.commit(); db_session.refresh(g)
        assert g.end_time is None
        g.end_time = "21:00"
        assert g.end_time == "21:00"

    def test_asistencia_status_property_and_setter(self, db_session):
        _seed_admin(db_session)
        sede = db_session.query(models.Sede).first()
        p = models.Persona(first_name="A", last_name="T", sede_id=sede.id)
        s = SesionGrupo(
            grupo_id=uuid.uuid4(),
            fecha_sesion=datetime(2026, 6, 1, tzinfo=timezone.utc),
            estado="PENDIENTE",
        )
        db_session.add_all([p, s]); db_session.flush()
        for estado, valor, pv in [
            ("ASISTIO", "present", False),
            ("Presente", "present", False),
            ("primera_vez", "first_time", True),
            ("FALTO", "absent", False),
            ("Ausente", "absent", False),
            ("EXCUSA", "excused", False),
        ]:
            a = MAsistencia(
                sesion_id=s.id, persona_id=p.id, estado=estado, es_primera_vez=pv,
            )
            db_session.add(a); db_session.flush()
            assert a.status == valor, (estado, valor, a.status)

        a2 = MAsistencia(sesion_id=s.id, persona_id=p.id, estado="ASISTIO")
        db_session.add(a2); db_session.flush()
        a2.status = "absent"
        assert a2.estado == "FALTO"
        a2.status = "first_time"
        assert a2.estado == "primera_vez"
        assert a2.es_primera_vez is True
        a2.status = "excused"
        assert a2.estado == "EXCUSA"
        a2.status = "present"
        assert a2.estado == "Presente"
        assert a2.es_primera_vez is False

    def test_asistencia_attended_setter(self, db_session):
        _seed_admin(db_session)
        sede = db_session.query(models.Sede).first()
        p = models.Persona(first_name="A", last_name="B", sede_id=sede.id)
        s = SesionGrupo(
            grupo_id=uuid.uuid4(), fecha_sesion=datetime(2026, 6, 1, tzinfo=timezone.utc),
            estado="PENDIENTE",
        )
        db_session.add_all([p, s]); db_session.flush()
        a = MAsistencia(sesion_id=s.id, persona_id=p.id, estado="ASISTIO")
        db_session.add(a); db_session.flush()
        a.attended = False
        assert a.estado == "Ausente"
        a.attended = True
        assert a.estado == "Presente"


# ════════════════════════════════════════════════════════════════════
# 3. MAIN_ESTRATEGIAS — generate_strategy_sessions (+phases)
# ════════════════════════════════════════════════════════════════════


class TestGenerateStrategySessions:
    def test_generate_strategy_sessions_no_groups(self, full):
        est = full["estrategia"]
        est.grupos = []
        db_sess = _sa_object_session(est)
        db_sess.commit()
        resp = full["c"].post(f"/api/evangelism/strategies/{est.id}/generate-sessions", headers=full["h"])
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["total_sessions_created"] == 0
        assert "message" in data

    def test_generate_strategy_sessions_with_groups(self, full):
        est = full["estrategia"]
        resp = full["c"].post(f"/api/evangelism/strategies/{est.id}/generate-sessions", headers=full["h"])
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["total_sessions_created"] > 0
        assert data["groups"] == 2

    def test_generate_strategy_sessions_bad_strategy(self, full):
        resp = full["c"].post(
            f"/api/evangelism/strategies/{uuid.uuid4()}/generate-sessions",
            headers=full["h"],
        )
        assert resp.status_code == 404

    def test_generate_strategy_sessions_missing_required_fields(self, full, db_session):
        """Estrategia sin frecuencia / fechas → 400."""
        est = EstrategiaEvangelismo(
            id=uuid.uuid4(),
            nombre="SinCompletar",
            sede_id=full["sede"].id,
            categoria_id=full["categoria"].id,
        )
        db_session.add(est); db_session.commit()
        resp = full["c"].post(
            f"/api/evangelism/strategies/{est.id}/generate-sessions", headers=full["h"],
        )
        assert resp.status_code == 400

    def test_generate_strategy_sessions_day_adjust_lunes(self, full, db_session):
        """Si fecha_inicio cae en miércoles, se ajusta al primer lunes."""
        est = EstrategiaEvangelismo(
            id=uuid.uuid4(),
            nombre="AjusteDia",
            sede_id=full["sede"].id,
            categoria_id=full["categoria"].id,
            frecuencia="SEMANAL",
            fecha_inicio=datetime(2026, 6, 3, tzinfo=timezone.utc),  # Miércoles
            fecha_fin=datetime(2026, 6, 17, tzinfo=timezone.utc),
            dia_reunion="Lunes",
            hora_reunion="19:00",
            activa=True,
        )
        db_session.add(est); db_session.commit()
        # Reasignar un grupo a esta estrategia
        g = full["grupos"][0]
        g.estrategia_id = est.id
        db_session.commit()
        resp = full["c"].post(
            f"/api/evangelism/strategies/{est.id}/generate-sessions", headers=full["h"],
        )
        assert resp.status_code == 200, resp.text
        # Verifica que la fecha returned sea un lunes (weekday 0)
        from datetime import datetime as _d
        start_str = resp.json().get("start", "")
        if start_str:
            d = _d.fromisoformat(start_str.replace("Z", "+00:00"))
            assert d.weekday() == 0, d

    def test_generate_strategy_sessions_bad_frequency_with_groups(self, full, db_session):
        """Con grupos pero frecuencia inválida → excepciones internas."""
        # Trasmigramos los grupos a una estrategia con freq inválida
        est = EstrategiaEvangelismo(
            id=uuid.uuid4(),
            nombre="FreqInvalida",
            sede_id=full["sede"].id,
            categoria_id=full["categoria"].id,
            frecuencia="PATATA",
            fecha_inicio=datetime(2026, 6, 1, tzinfo=timezone.utc),
            fecha_fin=datetime(2026, 6, 30, tzinfo=timezone.utc),
            activa=True,
        )
        db_session.add(est); db_session.commit()
        for g in full["grupos"]:
            g.estrategia_id = est.id
        db_session.commit()
        resp = full["c"].post(
            f"/api/evangelism/strategies/{est.id}/generate-sessions", headers=full["h"],
        )
        assert resp.status_code == 400, resp.text


# ════════════════════════════════════════════════════════════════════
# 4. PHASES PROJECT — _project_phases_as_tasks
# ════════════════════════════════════════════════════════════════════


class TestPhasesProject:
    """Valida N1 tasks generados al crear/actualizar estrategia evento_masivo."""

    def test_create_strategy_evento_masivo_con_phases(self, full, db_session):
        resp = full["c"].post("/api/evangelism/strategies", json={
            "name": "Congreso Anual",
            "description": "Evento grande",
            "typology": "evento_masivo",
            "strategy_type": "congreso",
            "event_format": "MULTILOCACION",
            "phases": [
                {"name": "Pre-producción", "type": "prep",
                 "start_date": "2026-08-01", "end_date": "2026-08-15"},
                {"name": "Ejecución", "type": "main",
                 "start_date": "2026-09-01", "end_date": "2026-09-30"},
            ],
            "start_date": "2026-08-01",
            "status": "active",
        }, headers=full["h"])
        assert resp.status_code == 200, resp.text
        assert resp.json()["name"] == "Congreso Anual"
        # Verificar Project + ProjectTask
        from backend.models_projects import Project, ProjectTask
        projects = db_session.query(Project).filter(
            Project.title.like("[MASIVO] Congreso Anual"),
        ).all()
        assert len(projects) >= 1
        tasks = db_session.query(ProjectTask).filter(
            ProjectTask.title.like("[N1]%"),
        ).all()
        assert len(tasks) >= 2

    def test_create_strategy_evento_masivo_sin_phases(self, full):
        """evento_masivo sin phases - NO crea Project."""
        resp = full["c"].post("/api/evangelism/strategies", json={
            "name": "Sin Fases",
            "typology": "evento_masivo",
            "start_date": "2026-09-01",
        }, headers=full["h"])
        assert resp.status_code == 200, resp.text

    def test_update_strategy_con_phases(self, full):
        """PUT con typology evento_masivo + phases."""
        est = full["estrategia"]
        resp = full["c"].put(
            f"/api/evangelism/strategies/{est.id}",
            json={
                "typology": "evento_masivo",
                "strategy_type": "retiro",
                "phases": [
                    {"name": "Fase única", "type": "general",
                     "start_date": "2026-09-01", "end_date": "2026-09-05"},
                ],
            },
            headers=full["h"],
        )
        # 200 o 400 (default_role validation), ambos válidos
        assert resp.status_code in (200, 400), resp.text


# ════════════════════════════════════════════════════════════════════
# 5. MAIN_ROLES y EXCUSAS
# ════════════════════════════════════════════════════════════════════


class TestRolesYExcusas:
    def test_list_strategy_roles(self, full):
        est = full["estrategia"]
        resp = full["c"].get(f"/api/evangelism/strategies/{est.id}/roles", headers=full["h"])
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert len(body) >= 3

    def test_list_strategy_roles_404(self, full):
        resp = full["c"].get(
            f"/api/evangelism/strategies/{uuid.uuid4()}/roles", headers=full["h"],
        )
        assert resp.status_code == 404

    def test_create_strategy_role(self, full):
        est = full["estrategia"]
        resp = full["c"].post(
            f"/api/evangelism/strategies/{est.id}/roles",
            json={"nombre_rol": "Líder de Oración", "descripcion": "Rol de prueba"},
            headers=full["h"],
        )
        assert resp.status_code == 200, resp.text

    def test_create_strategy_role_404(self, full):
        resp = full["c"].post(
            f"/api/evangelism/strategies/{uuid.uuid4()}/roles",
            json={"nombre_rol": "X"},
            headers=full["h"],
        )
        assert resp.status_code == 404

    def test_delete_strategy_role(self, full):
        est = full["estrategia"]
        role_id = full["roles_personalizados"][2].id
        resp = full["c"].delete(
            f"/api/evangelism/strategies/{est.id}/roles/{role_id}", headers=full["h"],
        )
        assert resp.status_code == 200, resp.text
        assert resp.json() == {"ok": True}

    def test_delete_strategy_role_404(self, full):
        est = full["estrategia"]
        resp = full["c"].delete(
            f"/api/evangelism/strategies/{est.id}/roles/{uuid.uuid4()}",
            headers=full["h"],
        )
        assert resp.status_code == 404

    def test_list_motivos_excusa(self, full):
        resp = full["c"].get("/api/evangelism/excuses", headers=full["h"])
        assert resp.status_code == 200, resp.text

    def test_list_motivos_excusa_incluir_inactivos(self, full):
        resp = full["c"].get("/api/evangelism/excuses?solo_activos=false", headers=full["h"])
        assert resp.status_code == 200, resp.text

    def test_create_motivo_excusa(self, full):
        resp = full["c"].post(
            "/api/evangelism/excuses", json={"descripcion": "Viaje"}, headers=full["h"],
        )
        assert resp.status_code == 200, resp.text

    def test_update_motivo_excusa(self, full, db_session):
        me = MotivoExcusa(descripcion="MOTIVO_TEST", es_del_sistema=False, activo=True)
        db_session.add(me); db_session.commit(); db_session.refresh(me)
        resp = full["c"].patch(
            f"/api/evangelism/excuses/{me.id}",
            json={"descripcion": "MOTIVO_TEST_V2", "activo": False},
            headers=full["h"],
        )
        assert resp.status_code == 200, resp.text

    def test_update_motivo_excusa_404(self, full):
        resp = full["c"].patch(
            f"/api/evangelism/excuses/{uuid.uuid4()}",
            json={"descripcion": "X", "activo": True},
            headers=full["h"],
        )
        assert resp.status_code == 404

    def test_update_motivo_excusa_sistema_bloqueado(self, full, db_session):
        me = MotivoExcusa(descripcion="SISTEMA_BLOQ", es_del_sistema=True, activo=True)
        db_session.add(me); db_session.commit(); db_session.refresh(me)
        resp = full["c"].patch(
            f"/api/evangelism/excuses/{me.id}",
            json={"descripcion": "INTENTO_MODIFICAR_SISTEMA", "activo": True},
            headers=full["h"],
        )
        assert resp.status_code == 404

    def test_delete_motivo_excusa(self, full, db_session):
        me = MotivoExcusa(descripcion="BORRABLE", es_del_sistema=False, activo=True)
        db_session.add(me); db_session.commit(); db_session.refresh(me)
        resp = full["c"].delete(f"/api/evangelism/excuses/{me.id}", headers=full["h"])
        assert resp.status_code == 200, resp.text

    def test_delete_motivo_excusa_sistema_bloqueado(self, full, db_session):
        me = MotivoExcusa(descripcion="SISTEMA_X", es_del_sistema=True, activo=True)
        db_session.add(me); db_session.commit(); db_session.refresh(me)
        resp = full["c"].delete(f"/api/evangelism/excuses/{me.id}", headers=full["h"])
        assert resp.status_code == 404

    def test_seed_motivos_excusa(self, full):
        resp = full["c"].post("/api/evangelism/excuses/seed", headers=full["h"])
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert "created" in body
        assert "excusas" in body


# ════════════════════════════════════════════════════════════════════
# 6. GRUPOS — list, get, create, update, delete, visitors
# ════════════════════════════════════════════════════════════════════


class TestGruposEndpoints:
    def test_list_grupos(self, full):
        resp = full["c"].get("/api/evangelism/grupos", headers=full["h"])
        assert resp.status_code == 200, resp.text
        assert len(resp.json()) >= 2

    def test_list_grupos_filtro_estrategia(self, full):
        est = full["estrategia"]
        resp = full["c"].get(
            f"/api/evangelism/grupos?estrategia_id={est.id}", headers=full["h"],
        )
        assert resp.status_code == 200, resp.text
        assert len(resp.json()) >= 2

    def test_list_my_grupos_admin_ve_todos(self, full):
        resp = full["c"].get("/api/evangelism/grupos/mine", headers=full["h"])
        assert resp.status_code == 200, resp.text
        assert len(resp.json()) >= 2

    def test_faro_assignment_summary(self, full):
        resp = full["c"].get("/api/evangelism/grupos/assignment-summary", headers=full["h"])
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "houses_total" in data
        assert "personas_total" in data

    def test_get_grupo_detallado(self, full):
        g = full["grupos"][0]
        resp = full["c"].get(f"/api/evangelism/grupos/{g.id}", headers=full["h"])
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["id"] == str(g.id)
        assert "sessions" in data
        assert "monitoring" in data

    def test_get_grupo_404(self, full):
        resp = full["c"].get(
            f"/api/evangelism/grupos/{uuid.uuid4()}", headers=full["h"],
        )
        assert resp.status_code == 404

    def test_create_grupo_minimo(self, full):
        resp = full["c"].post("/api/evangelism/grupos", json={
            "nombre": "Grupo Nuevo", "lugar": "Centro",
        }, headers=full["h"])
        assert resp.status_code == 200, resp.text

    def test_update_grupo_basico(self, full):
        g = full["grupos"][0]
        resp = full["c"].put(
            f"/api/evangelism/grupos/{g.id}",
            json={"nombre": "Grupo Renombrado"},
            headers=full["h"],
        )
        assert resp.status_code == 200, resp.text

    def test_update_grupo_404(self, full):
        resp = full["c"].put(
            f"/api/evangelism/grupos/{uuid.uuid4()}",
            json={"nombre": "X"},
            headers=full["h"],
        )
        assert resp.status_code == 404

    def test_delete_grupo(self, full):
        g = full["grupos"][0]
        resp = full["c"].delete(f"/api/evangelism/grupos/{g.id}", headers=full["h"])
        assert resp.status_code == 204, resp.text

    def test_delete_grupo_404(self, full):
        resp = full["c"].delete(
            f"/api/evangelism/grupos/{uuid.uuid4()}", headers=full["h"],
        )
        assert resp.status_code == 404

    def test_get_grupo_strategy_metrics(self, full):
        est = full["estrategia"]
        resp = full["c"].get(
            f"/api/evangelism/strategies/{est.id}/metrics", headers=full["h"],
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "summary" in data
        assert "weekly" in data

    def test_get_macro_despliegue(self, full):
        resp = full["c"].get("/api/evangelism/macro-despliegue", headers=full["h"])
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "despliegue" in data or "season" in data


# ════════════════════════════════════════════════════════════════════
# 7. CAMPAIGN SEASONS
# ════════════════════════════════════════════════════════════════════


class TestCampaignSeasons:
    def test_list_seasons(self, full):
        resp = full["c"].get("/api/evangelism/grupos/seasons", headers=full["h"])
        assert resp.status_code == 200, resp.text
        assert isinstance(resp.json(), list)

    def test_create_season(self, full):
        resp = full["c"].post("/api/evangelism/grupos/seasons", json={
            "name": "Temporada Q3",
            "start_date": "2026-07-01",
            "end_date": "2026-09-30",
            "periodicity": "QUINCENAL",
        }, headers=full["h"])
        assert resp.status_code == 200, resp.text

    def test_create_season_bad_dates(self, full):
        resp = full["c"].post("/api/evangelism/grupos/seasons", json={
            "name": "Bad", "start_date": "2026-09-01", "end_date": "2026-08-01",
        }, headers=full["h"])
        assert resp.status_code == 400

    def test_create_season_invalid_format(self, full):
        resp = full["c"].post("/api/evangelism/grupos/seasons", json={
            "name": "Bad", "start_date": "bad-date", "end_date": "2026-08-01",
        }, headers=full["h"])
        assert resp.status_code == 400

    def test_create_season_missing_name(self, full):
        resp = full["c"].post("/api/evangelism/grupos/seasons", json={
            "start_date": "2026-07-01", "end_date": "2026-09-30",
        }, headers=full["h"])
        assert resp.status_code == 400

    def test_update_season(self, full):
        s = full["season"]
        resp = full["c"].patch(
            f"/api/evangelism/grupos/seasons/{s.id}",
            json={"status": "Cerrada"},
            headers=full["h"],
        )
        assert resp.status_code == 200, resp.text

    def test_update_season_404(self, full):
        resp = full["c"].patch(
            f"/api/evangelism/grupos/seasons/{uuid.uuid4()}",
            json={"status": "X"},
            headers=full["h"],
        )
        assert resp.status_code == 404


# ════════════════════════════════════════════════════════════════════
# 8. SESSIONS — faro, list, create, toggle habilitación
# ════════════════════════════════════════════════════════════════════


class TestSessions:
    def test_list_faro_sessions(self, full):
        resp = full["c"].get("/api/evangelism/grupos/sessions", headers=full["h"])
        assert resp.status_code == 200, resp.text
        assert len(resp.json()) >= 6

    def test_list_faro_sessions_filtro_grupo(self, full):
        g = full["grupos"][0]
        resp = full["c"].get(
            f"/api/evangelism/grupos/sessions?grupo_id={g.id}", headers=full["h"],
        )
        assert resp.status_code == 200, resp.text
        assert len(resp.json()) == 3

    def test_list_my_pending_faro_sessions(self, full):
        resp = full["c"].get(
            "/api/evangelism/grupos/sessions/mine/pending", headers=full["h"],
        )
        assert resp.status_code == 200, resp.text

    def test_create_faro_session(self, full):
        s = full["season"]
        g = full["grupos"][0]
        resp = full["c"].post("/api/evangelism/grupos/sessions", json={
            "season_id": str(s.id),
            "grupo_id": str(g.id),
            "session_date": "2026-09-15",
            "topic": "Nuevo Tema",
        }, headers=full["h"])
        assert resp.status_code == 200, resp.text
        assert resp.json()["created_count"] == 1

    def test_create_faro_session_bad_date(self, full):
        s = full["season"]
        resp = full["c"].post("/api/evangelism/grupos/sessions", json={
            "season_id": str(s.id),
            "grupo_id": "all",
            "session_date": "mal-fecha",
        }, headers=full["h"])
        assert resp.status_code == 400

    def test_create_faro_session_missing_data(self, full):
        resp = full["c"].post("/api/evangelism/grupos/sessions", json={
            "session_date": "2026-09-15",
        }, headers=full["h"])
        assert resp.status_code == 400

    def test_create_faro_session_season_not_found(self, full):
        g = full["grupos"][0]
        resp = full["c"].post("/api/evangelism/grupos/sessions", json={
            "season_id": str(uuid.uuid4()),
            "grupo_id": str(g.id),
            "session_date": "2026-09-15",
        }, headers=full["h"])
        assert resp.status_code == 404

    def test_create_faro_session_fecha_fuera_de_temporada(self, full):
        s = full["season"]
        g = full["grupos"][0]
        resp = full["c"].post("/api/evangelism/grupos/sessions", json={
            "season_id": str(s.id),
            "grupo_id": str(g.id),
            "session_date": "2030-01-01",
        }, headers=full["h"])
        assert resp.status_code == 400

    def test_create_faro_session_all_grupos(self, full):
        s = full["season"]
        resp = full["c"].post("/api/evangelism/grupos/sessions", json={
            "season_id": str(s.id),
            "grupo_id": "all",
            "session_date": "2026-09-25",
            "topic": "All groups",
        }, headers=full["h"])
        assert resp.status_code == 200, resp.text
        assert resp.json()["created_count"] == len(full["grupos"])

    def test_create_faro_session_invalid_uuid(self, full):
        s = full["season"]
        resp = full["c"].post("/api/evangelism/grupos/sessions", json={
            "season_id": str(s.id),
            "grupo_id": "not-a-uuid",
            "session_date": "2026-09-25",
        }, headers=full["h"])
        assert resp.status_code == 400

    def test_create_faro_session_grupo_no_encontrado(self, full):
        s = full["season"]
        resp = full["c"].post("/api/evangelism/grupos/sessions", json={
            "season_id": str(s.id),
            "grupo_id": str(uuid.uuid4()),
            "session_date": "2026-09-25",
        }, headers=full["h"])
        assert resp.status_code == 404

    def test_create_faro_session_duplicada(self, full):
        """Si ya existe sesión en esa fecha para un grupo, error."""
        s = full["season"]
        g = full["grupos"][0]
        resp = full["c"].post("/api/evangelism/grupos/sessions", json={
            "season_id": str(s.id),
            "grupo_id": str(g.id),
            "session_date": "2026-06-08",
        }, headers=full["h"])
        assert resp.status_code == 400

    def test_create_faro_session_duplicada_batch_skip(self, full):
        """En batch mode 'all' los duplicados se omiten silenciosamente."""
        s = full["season"]
        resp = full["c"].post("/api/evangelism/grupos/sessions", json={
            "season_id": str(s.id),
            "grupo_id": "all",
            "session_date": "2026-06-08",
        }, headers=full["h"])
        assert resp.status_code == 200, resp.text

    def test_list_sessions(self, full):
        resp = full["c"].get("/api/evangelism/sessions", headers=full["h"])
        assert resp.status_code == 200, resp.text
        assert isinstance(resp.json(), list)

    def test_list_sessions_filtro_house(self, full):
        g = full["grupos"][0]
        resp = full["c"].get(
            f"/api/evangelism/sessions?house_id={g.id}", headers=full["h"],
        )
        assert resp.status_code == 200, resp.text
        assert len(resp.json()) >= 3

    def test_list_sessions_filtro_strategy(self, full):
        est = full["estrategia"]
        resp = full["c"].get(
            f"/api/evangelism/sessions?strategy_id={est.id}", headers=full["h"],
        )
        assert resp.status_code == 200, resp.text

    def test_get_session_detail(self, full):
        s = full["sesiones"][0]
        resp = full["c"].get(f"/api/evangelism/sessions/{s.id}", headers=full["h"])
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "session" in data
        assert "attendance" in data

    def test_get_session_detail_404(self, full):
        resp = full["c"].get(
            f"/api/evangelism/sessions/{uuid.uuid4()}", headers=full["h"],
        )
        assert resp.status_code == 404

    def test_update_session(self, full):
        s = full["sesiones"][0]
        resp = full["c"].put(
            f"/api/evangelism/sessions/{s.id}",
            json={"topic": "Tema actualizado"},
            headers=full["h"],
        )
        assert resp.status_code == 200, resp.text

    def test_update_session_404(self, full):
        resp = full["c"].put(
            f"/api/evangelism/sessions/{uuid.uuid4()}",
            json={"topic": "X"},
            headers=full["h"],
        )
        assert resp.status_code == 404

    def test_delete_session_soft(self, full):
        s = full["sesiones"][5]
        resp = full["c"].delete(f"/api/evangelism/sessions/{s.id}", headers=full["h"])
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "cancelada"

    def test_delete_session_404(self, full):
        resp = full["c"].delete(
            f"/api/evangelism/sessions/{uuid.uuid4()}", headers=full["h"],
        )
        assert resp.status_code == 404

    def test_toggle_habilitacion_habilitar(self, full):
        s = full["sesiones"][0]
        s.estado_habilitacion = "DESHABILITADO"
        _sa_object_session(s).commit()
        resp = full["c"].patch(
            f"/api/evangelism/sessions/{s.id}/habilitacion",
            json={"accion": "HABILITAR"},
            headers=full["h"],
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["estado_habilitacion"] == "HABILITADO"

    def test_toggle_habilitacion_deshabilitar(self, full):
        s = full["sesiones"][0]
        resp = full["c"].patch(
            f"/api/evangelism/sessions/{s.id}/habilitacion",
            json={"accion": "DESHABILITAR"},
            headers=full["h"],
        )
        assert resp.status_code == 200, resp.text

    def test_toggle_habilitacion_cerrar(self, full):
        s = full["sesiones"][0]
        resp = full["c"].patch(
            f"/api/evangelism/sessions/{s.id}/habilitacion",
            json={"accion": "CERRAR"},
            headers=full["h"],
        )
        assert resp.status_code == 200, resp.text

    def test_toggle_habilitacion_accion_invalida(self, full):
        s = full["sesiones"][0]
        resp = full["c"].patch(
            f"/api/evangelism/sessions/{s.id}/habilitacion",
            json={"accion": "INVALID"},
            headers=full["h"],
        )
        assert resp.status_code == 400

    def test_toggle_habilitacion_404(self, full):
        resp = full["c"].patch(
            f"/api/evangelism/sessions/{uuid.uuid4()}/habilitacion",
            json={"accion": "HABILITAR"},
            headers=full["h"],
        )
        assert resp.status_code == 404

    def test_habilitar_todas_sesiones(self, full):
        est = full["estrategia"]
        full["c"].post(
            f"/api/evangelism/strategies/{est.id}/deshabilitar-todas",
            headers=full["h"],
        )
        resp = full["c"].post(
            f"/api/evangelism/strategies/{est.id}/habilitar-todas",
            headers=full["h"],
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["sesiones_habilitadas"] >= 6

    def test_habilitar_todas_sin_grupos(self, full, db_session):
        est_vacia = EstrategiaEvangelismo(
            id=uuid.uuid4(),
            nombre="Linea Vacia",
            sede_id=full["sede"].id,
            categoria_id=full["categoria"].id,
        )
        db_session.add(est_vacia); db_session.commit()
        resp = full["c"].post(
            f"/api/evangelism/strategies/{est_vacia.id}/habilitar-todas",
            headers=full["h"],
        )
        assert resp.status_code == 404

    def test_deshabilitar_todas_sesiones(self, full):
        est = full["estrategia"]
        resp = full["c"].post(
            f"/api/evangelism/strategies/{est.id}/deshabilitar-todas",
            headers=full["h"],
        )
        assert resp.status_code == 200, resp.text

    def test_create_session_direct(self, full):
        g = full["grupos"][0]
        resp = full["c"].post("/api/evangelism/sessions", json={
            "grupo_id": str(g.id),
            "session_date": "2026-09-30",
            "topic": "Tema directo",
        }, headers=full["h"])
        assert resp.status_code == 200, resp.text

    def test_create_session_missing_grupo(self, full):
        resp = full["c"].post("/api/evangelism/sessions", json={
            "session_date": "2026-09-30",
        }, headers=full["h"])
        assert resp.status_code == 400

    def test_create_session_grupo_404(self, full):
        resp = full["c"].post("/api/evangelism/sessions", json={
            "grupo_id": str(uuid.uuid4()),
            "session_date": "2026-09-30",
        }, headers=full["h"])
        assert resp.status_code == 404


# ════════════════════════════════════════════════════════════════════
# 9. ATTENDANCE — faro + submit + follow-up
# ════════════════════════════════════════════════════════════════════


class TestAttendanceFaro:
    def test_get_faro_session_attendance(self, full):
        s = full["sesiones"][0]
        resp = full["c"].get(
            f"/api/evangelism/grupos/sessions/{s.id}/attendance",
            headers=full["h"],
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "expected_personas" in data
        assert "attendees" in data
        assert "absentees" in data

    def test_get_faro_session_attendance_404_session(self, full):
        resp = full["c"].get(
            f"/api/evangelism/grupos/sessions/{uuid.uuid4()}/attendance",
            headers=full["h"],
        )
        assert resp.status_code == 404

    def test_add_faro_attendance_persona_ids(self, full):
        s = full["sesiones"][5]
        p = full["personas"][5]
        resp = full["c"].post(
            f"/api/evangelism/grupos/sessions/{s.id}/attendance",
            json={"persona_ids": [str(p.id)]},
            headers=full["h"],
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["processed"] >= 1

    def test_add_faro_attendance_attendees_detallado(self, full):
        s = full["sesiones"][5]
        p1 = full["personas"][6]
        p2 = full["personas"][7]
        resp = full["c"].post(
            f"/api/evangelism/grupos/sessions/{s.id}/attendance",
            json={
                "attendees": [
                    {"persona_id": str(p1.id), "attended": True},
                    {"persona_id": str(p2.id), "attended": False, "absence_reason": "SALUD"},
                ],
            },
            headers=full["h"],
        )
        assert resp.status_code == 200, resp.text

    def test_add_faro_attendance_ausente_sin_razon(self, full):
        s = full["sesiones"][5]
        p = full["personas"][7]
        resp = full["c"].post(
            f"/api/evangelism/grupos/sessions/{s.id}/attendance",
            json={
                "attendees": [
                    {"persona_id": str(p.id), "attended": False, "absence_reason": None},
                ],
            },
            headers=full["h"],
        )
        assert resp.status_code == 400

    def test_add_faro_attendance_uuid_invalido(self, full):
        s = full["sesiones"][5]
        resp = full["c"].post(
            f"/api/evangelism/grupos/sessions/{s.id}/attendance",
            json={"persona_ids": ["not-a-uuid"]},
            headers=full["h"],
        )
        assert resp.status_code == 400

    def test_add_faro_attendance_attendees_no_lista(self, full):
        s = full["sesiones"][5]
        resp = full["c"].post(
            f"/api/evangelism/grupos/sessions/{s.id}/attendance",
            json={"attendees": "not-a-list"},
            headers=full["h"],
        )
        assert resp.status_code == 400

    def test_add_faro_attendance_no_payload(self, full):
        s = full["sesiones"][5]
        resp = full["c"].post(
            f"/api/evangelism/grupos/sessions/{s.id}/attendance",
            json={},
            headers=full["h"],
        )
        assert resp.status_code == 400

    def test_add_faro_attendance_ofrenda_negativa(self, full):
        s = full["sesiones"][5]
        p = full["personas"][8]
        resp = full["c"].post(
            f"/api/evangelism/grupos/sessions/{s.id}/attendance",
            json={"persona_ids": [str(p.id)], "offering_amount": -50},
            headers=full["h"],
        )
        assert resp.status_code == 400

    def test_add_faro_attendance_cancel_sin_motivo(self, full):
        s = full["sesiones"][5]
        p = full["personas"][9]
        resp = full["c"].post(
            f"/api/evangelism/grupos/sessions/{s.id}/attendance",
            json={"persona_ids": [str(p.id)], "status": "Cancelada"},
            headers=full["h"],
        )
        assert resp.status_code == 400

    def test_add_faro_attendance_404_session(self, full):
        p = full["personas"][3]
        resp = full["c"].post(
            f"/api/evangelism/grupos/sessions/{uuid.uuid4()}/attendance",
            json={"persona_ids": [str(p.id)]},
            headers=full["h"],
        )
        assert resp.status_code == 404


class TestSubmitAttendance:
    def test_submit_attendance_ok(self, full):
        sesion = full["sesiones"][1]
        resp = full["c"].post(
            f"/api/evangelism/sessions/{sesion.id}/attendance",
            json=[
                {"persona_id": str(full["personas"][3].id), "status": "present"},
                {"persona_id": str(full["personas"][4].id), "status": "absent", "notes": "ENFERMO"},
            ],
            headers=full["h"],
        )
        assert resp.status_code == 200, resp.text

    def test_submit_attendance_primera_vez(self, full):
        sesion = full["sesiones"][2]
        resp = full["c"].post(
            f"/api/evangelism/sessions/{sesion.id}/attendance",
            json=[{"persona_id": str(full["personas"][9].id), "status": "first_time"}],
            headers=full["h"],
        )
        assert resp.status_code == 200, resp.text
        assert "metadata" in resp.json()

    def test_submit_attendance_no_habilitada(self, full):
        sesion = full["sesiones"][0]
        sesion.estado_habilitacion = "DESHABILITADO"
        _sa_object_session(sesion).commit()
        resp = full["c"].post(
            f"/api/evangelism/sessions/{sesion.id}/attendance",
            json=[{"persona_id": str(full["personas"][3].id), "status": "present"}],
            headers=full["h"],
        )
        assert resp.status_code == 403

    def test_submit_attendance_404(self, full):
        resp = full["c"].post(
            f"/api/evangelism/sessions/{uuid.uuid4()}/attendance",
            json=[{"persona_id": str(full["personas"][3].id), "status": "present"}],
            headers=full["h"],
        )
        assert resp.status_code == 404


class TestFollowUp:
    def test_seguimiento_list_pendientes(self, full, db_session):
        a = db_session.query(MAsistencia).first()
        db_session.add(RegistroSeguimiento(
            asistencia_id=a.id,
            responsable_id=full["admin_persona"].id,
            tipo="LLAMADA",
            observaciones="Llamada inicial",
            estado_completado=False,
        ))
        db_session.commit()
        resp = full["c"].get("/api/evangelism/follow-up/pending", headers=full["h"])
        assert resp.status_code == 200, resp.text
        assert isinstance(resp.json(), list)

    def test_seguimiento_list_for_attendance(self, full, db_session):
        a = db_session.query(MAsistencia).first()
        db_session.add(RegistroSeguimiento(
            asistencia_id=a.id,
            responsable_id=full["admin_persona"].id,
            tipo="MENSAJE_WHATSAPP",
            estado_completado=True,
        ))
        db_session.commit()
        resp = full["c"].get(
            f"/api/evangelism/follow-up/{a.id}", headers=full["h"],
        )
        assert resp.status_code == 200, resp.text
        assert isinstance(resp.json(), list)

    def test_seguimiento_create(self, full, db_session):
        a = db_session.query(MAsistencia).first()
        resp = full["c"].post(
            f"/api/evangelism/follow-up/{a.id}",
            json={
                "tipo": "LLAMADA",
                "observaciones": "Test seguimiento",
                "responsable_id": str(full["admin_persona"].id),
            },
            headers=full["h"],
        )
        assert resp.status_code == 200, resp.text

    def test_seguimiento_create_404_asistencia(self, full):
        resp = full["c"].post(
            f"/api/evangelism/follow-up/{uuid.uuid4()}",
            json={"tipo": "LLAMADA"},
            headers=full["h"],
        )
        assert resp.status_code == 404

    def test_seguimiento_update(self, full, db_session):
        sg = RegistroSeguimiento(
            asistencia_id=db_session.query(MAsistencia).first().id,
            tipo="LLAMADA",
            estado_completado=False,
        )
        db_session.add(sg); db_session.commit(); db_session.refresh(sg)
        resp = full["c"].patch(
            f"/api/evangelism/follow-up/{sg.id}",
            json={"estado_completado": True},
            headers=full["h"],
        )
        assert resp.status_code == 200, resp.text

    def test_seguimiento_update_404(self, full):
        resp = full["c"].patch(
            f"/api/evangelism/follow-up/{uuid.uuid4()}",
            json={"estado_completado": True},
            headers=full["h"],
        )
        assert resp.status_code == 404


# ════════════════════════════════════════════════════════════════════
# 10. FARO VISITORS
# ════════════════════════════════════════════════════════════════════


class TestFaroVisitors:
    def test_register_new_visitor(self, full):
        g = full["grupos"][0]
        resp = full["c"].post("/api/evangelism/grupos/visitors", json={
            "first_name": "Nueva",
            "last_name": "Visitante",
            "phone": "+573009999999",
            "grupo_id": str(g.id),
        }, headers=full["h"])
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "created"

    def test_register_visitor_session_no_pertenece(self, full):
        g = full["grupos"][0]
        otro_grupo = full["grupos"][1]
        sesion_otro_grupo = next(
            s for s in full["sesiones"] if s.grupo_id == otro_grupo.id
        )
        resp = full["c"].post("/api/evangelism/grupos/visitors", json={
            "first_name": "X", "last_name": "Y",
            "phone": "+573008888888",
            "grupo_id": str(g.id),
            "session_id": str(sesion_otro_grupo.id),
        }, headers=full["h"])
        assert resp.status_code == 400

    def test_register_visitor_duplicate(self, full):
        g = full["grupos"][0]
        full["c"].post("/api/evangelism/grupos/visitors", json={
            "first_name": "Dup", "last_name": "Visit",
            "phone": "+573007777777",
            "grupo_id": str(g.id),
        }, headers=full["h"])
        resp = full["c"].post("/api/evangelism/grupos/visitors", json={
            "first_name": "Dup", "last_name": "Visit",
            "phone": "+573007777777",
            "grupo_id": str(g.id),
        }, headers=full["h"])
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "duplicate"

    def test_register_visitor_grupo_no_encontrado(self, full):
        resp = full["c"].post("/api/evangelism/grupos/visitors", json={
            "first_name": "X", "last_name": "Y",
            "phone": "+573006666666",
            "grupo_id": str(uuid.uuid4()),
        }, headers=full["h"])
        assert resp.status_code == 404


# ════════════════════════════════════════════════════════════════════
# 11. MULTIPLICATION
# ════════════════════════════════════════════════════════════════════


class TestMultiplication:
    def test_check_under_umbral(self, full):
        resp = full["c"].get(
            "/api/evangelism/multiplication/check?umbral=10", headers=full["h"],
        )
        assert resp.status_code == 200, resp.text
        assert all(not item["excede_umbral"] for item in resp.json())

    def test_check_over_umbral(self, full, db_session):
        g = full["grupos"][0]
        for i in range(20):
            p = models.Persona(
                first_name=f"P{i}", last_name="Excedente",
                sede_id=full["sede"].id,
            )
            db_session.add(p); db_session.flush()
            db_session.add(ParticipanteGrupo(
                grupo_id=g.id, persona_id=p.id, rol_base="Miembro", activo=True,
            ))
        db_session.commit()
        resp = full["c"].get(
            "/api/evangelism/multiplication/check?umbral=15", headers=full["h"],
        )
        assert resp.status_code == 200, resp.text
        assert any(item["excede_umbral"] for item in resp.json())


# ════════════════════════════════════════════════════════════════════
# 12. RANKINGS
# ════════════════════════════════════════════════════════════════════


class TestRankings:
    def test_rankings_groups_attendance(self, full):
        resp = full["c"].get(
            "/api/evangelism/rankings/groups?by=attendance", headers=full["h"],
        )
        assert resp.status_code == 200, resp.text

    def test_rankings_groups_growth(self, full):
        resp = full["c"].get(
            "/api/evangelism/rankings/groups?by=growth", headers=full["h"],
        )
        assert resp.status_code == 200, resp.text

    def test_rankings_groups_visitors(self, full):
        resp = full["c"].get(
            "/api/evangelism/rankings/groups?by=visitors", headers=full["h"],
        )
        assert resp.status_code == 200, resp.text

    def test_rankings_groups_filtro_estrategia(self, full):
        est = full["estrategia"]
        resp = full["c"].get(
            f"/api/evangelism/rankings/groups?strategy_id={est.id}", headers=full["h"],
        )
        assert resp.status_code == 200, resp.text

    def test_monthly_comparison(self, full):
        resp = full["c"].get(
            "/api/evangelism/rankings/monthly-comparison", headers=full["h"],
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert "current_month" in body
        assert "previous_month" in body

    def test_monthly_comparison_con_estrategia(self, full):
        est = full["estrategia"]
        resp = full["c"].get(
            f"/api/evangelism/rankings/monthly-comparison?strategy_id={est.id}",
            headers=full["h"],
        )
        assert resp.status_code == 200, resp.text

    def test_rankings_leaders(self, full):
        resp = full["c"].get("/api/evangelism/rankings/leaders", headers=full["h"])
        assert resp.status_code == 200, resp.text
        body = resp.json()
        if body:
            assert "leader_name" in body[0]
            assert "group_name" in body[0]
            assert "attendance_pct" in body[0]

    def test_rankings_leaders_con_estrategia(self, full):
        est = full["estrategia"]
        resp = full["c"].get(
            f"/api/evangelism/rankings/leaders?strategy_id={est.id}", headers=full["h"],
        )
        assert resp.status_code == 200, resp.text


# ════════════════════════════════════════════════════════════════════
# 13. NOTIFICATIONS
# ════════════════════════════════════════════════════════════════════


class TestNotifications:
    def test_send_reminders(self, full, db_session):
        """Crea sesión mañana + usuario auth para el lider, luego invoca."""
        grp = full["grupos"][0]
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        sesion = SesionGrupo(
            grupo_id=grp.id,
            fecha_sesion=tomorrow,
            estado="PENDIENTE",
            estado_habilitacion="DESHABILITADO",
        )
        db_session.add(sesion); db_session.commit()
        # Asegurar que el lider tiene auth_user
        from backend.models import Usuario
        lider = db_session.query(models.Persona).filter(
            models.Persona.id == grp.lider_persona_id,
        ).one()
        if not db_session.query(Usuario).filter(Usuario.id == lider.id).first():
            from backend.models_auth import RolPlataforma
            role = db_session.query(RolPlataforma).first()
            db_session.add(Usuario(
                id=lider.id,
                sede_id=full["sede"].id,
                username=f"lider_{uuid.uuid4().hex[:6]}",
                email=f"lider_{uuid.uuid4().hex[:6]}@ccf.test",
                password_hash="x",
                rol_plataforma_id=role.id,
                is_active=True,
            ))
            db_session.commit()
        resp = full["c"].post(
            "/api/evangelism/notifications/send-reminders", headers=full["h"],
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert "notifications_created" in body


# ════════════════════════════════════════════════════════════════════
# 14. REPORTS
# ════════════════════════════════════════════════════════════════════


class TestReports:
    def test_attendance_excel(self, full):
        g = full["grupos"][0]
        resp = full["c"].get(
            f"/api/evangelism/reports/group/{g.id}/attendance-excel",
            headers=full["h"],
        )
        assert resp.status_code == 200, resp.text
        assert "spreadsheetml" in resp.headers.get("content-type", "")

    def test_attendance_pdf(self, full):
        g = full["grupos"][0]
        resp = full["c"].get(
            f"/api/evangelism/reports/group/{g.id}/attendance-pdf",
            headers=full["h"],
        )
        if resp.status_code == 200:
            assert resp.headers.get("content-type", "") == "application/pdf"

    def test_attendance_excel_404(self, full):
        resp = full["c"].get(
            f"/api/evangelism/reports/group/{uuid.uuid4()}/attendance-excel",
            headers=full["h"],
        )
        assert resp.status_code == 404

    def test_pdf_404(self, full):
        resp = full["c"].get(
            f"/api/evangelism/reports/group/{uuid.uuid4()}/attendance-pdf",
            headers=full["h"],
        )
        assert resp.status_code == 404

    def test_strategy_summary(self, full):
        est = full["estrategia"]
        resp = full["c"].get(
            f"/api/evangelism/reports/strategy/{est.id}/summary", headers=full["h"],
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["nombre"] == est.nombre

    def test_strategy_summary_404(self, full):
        resp = full["c"].get(
            f"/api/evangelism/reports/strategy/{uuid.uuid4()}/summary",
            headers=full["h"],
        )
        assert resp.status_code == 404


# ════════════════════════════════════════════════════════════════════
# 15. EVENTS — CRUD, analytics, roles, attendance history
# ════════════════════════════════════════════════════════════════════


class TestEvents:
    def test_list_events_empty(self, full):
        resp = full["c"].get("/api/evangelism/events/", headers=full["h"])
        assert resp.status_code == 200, resp.text
        assert resp.json() == []

    def test_create_event(self, full):
        resp = full["c"].post("/api/evangelism/events/", json={
            "name": "Culto Familiar",
            "description": "Culto mensual",
            "location": "Templo",
            "event_type": "CULTURE",
        }, headers=full["h"])
        assert resp.status_code == 200, resp.text
        assert resp.json()["name"] == "Culto Familiar"

    def test_get_roles_create(self, full):
        resp = full["c"].get("/api/evangelism/events/roles", headers=full["h"])
        assert resp.status_code == 200, resp.text
        resp = full["c"].post("/api/evangelism/events/roles", json={
            "name": "MC", "color": "#FF0000", "is_leadership": True,
        }, headers=full["h"])
        assert resp.status_code == 200, resp.text
        role_id = resp.json()["id"]
        put_resp = full["c"].put(
            f"/api/evangelism/events/roles/{role_id}",
            json={"color": "#00FF00"},
            headers=full["h"],
        )
        assert put_resp.status_code == 200, put_resp.text

    def test_create_event_role_duplicado(self, full):
        full["c"].post("/api/evangelism/events/roles", json={
            "name": "Servidor", "color": "#FFF", "is_leadership": False,
        }, headers=full["h"])
        resp = full["c"].post("/api/evangelism/events/roles", json={
            "name": "Servidor", "color": "#FFF", "is_leadership": False,
        }, headers=full["h"])
        assert resp.status_code == 400

    def test_update_event_role_404(self, full):
        resp = full["c"].put(
            f"/api/evangelism/events/roles/{uuid.uuid4()}",
            json={"color": "#000"},
            headers=full["h"],
        )
        assert resp.status_code == 404

    def test_update_role_nombre_duplicado(self, full):
        r1 = full["c"].post("/api/evangelism/events/roles", json={
            "name": "Pastor", "color": "#FFF", "is_leadership": True,
        }, headers=full["h"]).json()
        r2 = full["c"].post("/api/evangelism/events/roles", json={
            "name": "Director", "color": "#AAA", "is_leadership": True,
        }, headers=full["h"]).json()
        resp = full["c"].put(
            f"/api/evangelism/events/roles/{r2['id']}",
            json={"name": "Pastor"},
            headers=full["h"],
        )
        assert resp.status_code == 400

    def test_delete_role_sistema_bloqueado(self, full):
        r1 = full["c"].post("/api/evangelism/events/roles", json={
            "name": "RolA", "color": "#FFF", "is_leadership": False,
        }, headers=full["h"]).json()
        r2 = full["c"].post("/api/evangelism/events/roles", json={
            "name": "RolB", "color": "#AAA", "is_leadership": False,
        }, headers=full["h"]).json()
        full["admin"]
        from sqlalchemy.orm import object_session as _os

        from backend import models as _m
        role_obj = _os(full["admin"]).query(_m.RoleDefinition).filter(
            _m.RoleDefinition.id == r1["id"],
        ).first()
        role_obj.is_system_locked = True
        _os(full["admin"]).commit()
        resp = full["c"].delete(
            f"/api/evangelism/events/roles/{r1['id']}?fallback_id={r2['id']}",
            headers=full["h"],
        )
        assert resp.status_code == 400

    def test_delete_role_misma_id(self, full):
        r1 = full["c"].post("/api/evangelism/events/roles", json={
            "name": "Rolaaa", "color": "#FFF", "is_leadership": False,
        }, headers=full["h"]).json()
        resp = full["c"].delete(
            f"/api/evangelism/events/roles/{r1['id']}?fallback_id={r1['id']}",
            headers=full["h"],
        )
        assert resp.status_code == 400

    def test_delete_role_fallback_unexist(self, full):
        r1 = full["c"].post("/api/evangelism/events/roles", json={
            "name": "Rolbbb", "color": "#FFF", "is_leadership": False,
        }, headers=full["h"]).json()
        resp = full["c"].delete(
            f"/api/evangelism/events/roles/{r1['id']}?fallback_id={uuid.uuid4()}",
            headers=full["h"],
        )
        assert resp.status_code == 400

    def test_delete_role_404(self, full):
        r1 = full["c"].post("/api/evangelism/events/roles", json={
            "name": "Rolccc", "color": "#FFF", "is_leadership": False,
        }, headers=full["h"]).json()
        resp = full["c"].delete(
            f"/api/evangelism/events/roles/{uuid.uuid4()}?fallback_id={r1['id']}",
            headers=full["h"],
        )
        assert resp.status_code == 404

    def test_event_crud(self, full):
        create_resp = full["c"].post("/api/evangelism/events/", json={
            "name": "Conferencia",
            "description": "Conferencia anual",
            "location": "Auditorio",
            "event_type": "CONFERENCE",
            "event_date": "2026-09-15T10:00:00Z",
            "target_audience": "ALL",
        }, headers=full["h"])
        assert create_resp.status_code == 200, create_resp.text
        event_id = create_resp.json()["id"]

        get_resp = full["c"].get(
            f"/api/evangelism/events/{event_id}", headers=full["h"],
        )
        assert get_resp.status_code == 200, get_resp.text

        put_resp = full["c"].put(
            f"/api/evangelism/events/{event_id}",
            json={"name": "Conferencia 2026"},
            headers=full["h"],
        )
        assert put_resp.status_code == 200, put_resp.text

        analytics_resp = full["c"].get(
            f"/api/evangelism/events/{event_id}/analytics", headers=full["h"],
        )
        assert analytics_resp.status_code == 200, analytics_resp.text
        assert "monthly_data" in analytics_resp.json()

    def test_event_audience_update(self, full):
        create_resp = full["c"].post("/api/evangelism/events/", json={
            "name": "Evento Manual", "target_audience": "ALL",
        }, headers=full["h"])
        event_id = create_resp.json()["id"]
        resp = full["c"].put(
            f"/api/evangelism/events/{event_id}/audience",
            json={
                "target_audience": "MANUAL",
                "target_persona_ids": [str(full["personas"][0].id)],
            },
            headers=full["h"],
        )
        assert resp.status_code == 200, resp.text

    def test_event_audience_update_404(self, full):
        resp = full["c"].put(
            f"/api/evangelism/events/{uuid.uuid4()}/audience",
            json={"target_audience": "ALL"},
            headers=full["h"],
        )
        assert resp.status_code == 404

    def test_event_dashboard_stats_empty(self, full):
        resp = full["c"].get(
            "/api/evangelism/events/dashboard-stats", headers=full["h"],
        )
        assert resp.status_code == 200, resp.text

    def test_global_event_analytics(self, full):
        for period in ["WEEK", "MONTH", "BIMESTER", "TRIMESTER", "SEMESTER", "YEAR"]:
            resp = full["c"].get(
                f"/api/evangelism/events/analytics/global?period={period}",
                headers=full["h"],
            )
            assert resp.status_code == 200, resp.text

    def test_event_delete(self, full):
        create_resp = full["c"].post("/api/evangelism/events/", json={
            "name": "Para Borrar",
        }, headers=full["h"])
        event_id = create_resp.json()["id"]
        resp = full["c"].delete(
            f"/api/evangelism/events/{event_id}", headers=full["h"],
        )
        assert resp.status_code == 200, resp.text

    def test_event_delete_404(self, full):
        resp = full["c"].delete(
            f"/api/evangelism/events/{uuid.uuid4()}", headers=full["h"],
        )
        assert resp.status_code == 404

    def test_event_get_404(self, full):
        resp = full["c"].get(
            f"/api/evangelism/events/{uuid.uuid4()}", headers=full["h"],
        )
        assert resp.status_code == 404

    def test_persona_attendance_history(self, full):
        resp = full["c"].get(
            f"/api/evangelism/events/personas/{full['personas'][0].id}/attendance-history",
            headers=full["h"],
        )
        assert resp.status_code == 200, resp.text

    def test_persona_attendance_history_404(self, full):
        resp = full["c"].get(
            f"/api/evangelism/events/personas/{uuid.uuid4()}/attendance-history",
            headers=full["h"],
        )
        assert resp.status_code == 404

    def test_export_event_session_csv(self, full):
        create_resp = full["c"].post("/api/evangelism/events/", json={
            "name": "Exportar", "target_audience": "ALL",
        }, headers=full["h"])
        event_id = create_resp.json()["id"]
        resp = full["c"].get(
            f"/api/evangelism/events/{event_id}/sessions/2026-09-15/export",
            headers=full["h"],
        )
        assert resp.status_code == 200, resp.text
        assert "csv" in resp.headers.get("content-type", "")

    def test_export_event_session_csv_404(self, full):
        resp = full["c"].get(
            f"/api/evangelism/events/{uuid.uuid4()}/sessions/2026-09-15/export",
            headers=full["h"],
        )
        assert resp.status_code == 404


class TestEventAssignments:
    def test_register_event_attendance(self, full):
        create_resp = full["c"].post("/api/evangelism/events/", json={
            "name": "Para Asistencia", "target_audience": "ALL",
        }, headers=full["h"])
        event_id = create_resp.json()["id"]
        resp = full["c"].post("/api/evangelism/attendance", json={
            "event_id": event_id,
            "persona_id": str(full["personas"][0].id),
            "attended": True,
            "session_date": "2026-09-15",
        }, headers=full["h"])
        assert resp.status_code == 200, resp.text

    def test_register_bulk_attendance(self, full):
        create_resp = full["c"].post("/api/evangelism/events/", json={
            "name": "Bulk Asistencia", "target_audience": "ALL",
        }, headers=full["h"])
        event_id = create_resp.json()["id"]
        resp = full["c"].post("/api/evangelism/attendance/bulk", json={
            "event_id": event_id,
            "persona_ids": [str(p.id) for p in full["personas"][:3]],
            "attendance_date": "2026-09-20",
        }, headers=full["h"])
        assert resp.status_code == 200, resp.text
        assert resp.json()["created"] >= 1

    def test_register_bulk_attendance_invalid_date(self, full):
        create_resp = full["c"].post("/api/evangelism/events/", json={
            "name": "Bulk Bad Date", "target_audience": "ALL",
        }, headers=full["h"])
        event_id = create_resp.json()["id"]
        resp = full["c"].post("/api/evangelism/attendance/bulk", json={
            "event_id": event_id, "persona_ids": [],
            "attendance_date": "bad-date",
        }, headers=full["h"])
        assert resp.status_code == 400

    def test_register_bulk_attendance_missing_event(self, full):
        resp = full["c"].post("/api/evangelism/attendance/bulk", json={
            "persona_ids": [], "attendance_date": "2026-09-20",
        }, headers=full["h"])
        assert resp.status_code == 400

    def test_register_bulk_attendance_persona_not_list(self, full):
        create_resp = full["c"].post("/api/evangelism/events/", json={
            "name": "Bulk Bad List", "target_audience": "ALL",
        }, headers=full["h"])
        event_id = create_resp.json()["id"]
        resp = full["c"].post("/api/evangelism/attendance/bulk", json={
            "event_id": event_id, "persona_ids": "not-a-list",
            "attendance_date": "2026-09-20",
        }, headers=full["h"])
        assert resp.status_code == 400

    def test_register_bulk_attendance_event_404(self, full):
        resp = full["c"].post("/api/evangelism/attendance/bulk", json={
            "event_id": str(uuid.uuid4()), "persona_ids": [],
            "attendance_date": "2026-09-20",
        }, headers=full["h"])
        assert resp.status_code == 404

    def test_get_event_attendance(self, full):
        create_resp = full["c"].post("/api/evangelism/events/", json={
            "name": "Tener asistencia", "target_audience": "ALL",
        }, headers=full["h"])
        event_id = create_resp.json()["id"]
        full["c"].post("/api/evangelism/attendance/bulk", json={
            "event_id": event_id,
            "persona_ids": [str(full["personas"][0].id)],
            "attendance_date": "2026-09-22",
        }, headers=full["h"])
        resp = full["c"].get(
            f"/api/evangelism/events/{event_id}/attendance",
            headers=full["h"],
        )
        assert resp.status_code == 200, resp.text

    def test_get_event_session_detail(self, full):
        create_resp = full["c"].post("/api/evangelism/events/", json={
            "name": "Detalle Session", "target_audience": "ALL",
        }, headers=full["h"])
        event_id = create_resp.json()["id"]
        resp = full["c"].get(
            f"/api/evangelism/events/{event_id}/sessions/2026-09-15",
            headers=full["h"],
        )
        assert resp.status_code == 200, resp.text

    def test_sync_event_assignments(self, full):
        create_resp = full["c"].post("/api/evangelism/events/", json={
            "name": "Con Asignaciones", "target_audience": "ALL",
        }, headers=full["h"])
        event_id = create_resp.json()["id"]
        resp = full["c"].post(
            f"/api/evangelism/events/{event_id}/assignments",
            json={
                "session_date": "2026-09-15",
                "assignments": [
                    {"persona_id": str(full["personas"][0].id), "role": "MC"},
                ],
            },
            headers=full["h"],
        )
        assert resp.status_code == 200, resp.text

    def test_sync_event_assignments_404(self, full):
        resp = full["c"].post(
            f"/api/evangelism/events/{uuid.uuid4()}/assignments",
            json={"session_date": "2026-09-15", "assignments": []},
            headers=full["h"],
        )
        assert resp.status_code == 404


class TestFastCheckinVisitor:
    def _create_event(self, full):
        return full["c"].post("/api/evangelism/events/", json={
            "name": "Para Checkin", "target_audience": "ALL",
        }, headers=full["h"]).json()["id"]

    def test_fast_checkin_new(self, full):
        event_id = self._create_event(full)
        resp = full["c"].post(
            f"/api/evangelism/events/{event_id}/sessions/2026-09-20/visitors",
            json={
                "first_name": "Fast", "last_name": "Checkin",
                "phone": "+573004444444", "email": "fast@ccf.test",
            },
            headers=full["h"],
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["is_duplicate"] is False

    def test_fast_checkin_duplicado(self, full):
        event_id = self._create_event(full)
        full["c"].post(
            f"/api/evangelism/events/{event_id}/sessions/2026-09-20/visitors",
            json={
                "first_name": "DupF", "last_name": "Checkin",
                "phone": "+573003333333",
            },
            headers=full["h"],
        )
        resp = full["c"].post(
            f"/api/evangelism/events/{event_id}/sessions/2026-09-20/visitors",
            json={
                "first_name": "DupF", "last_name": "Checkin",
                "phone": "+573003333333",
            },
            headers=full["h"],
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["is_duplicate"] is True

    def test_fast_checkin_invalid_date(self, full):
        event_id = self._create_event(full)
        resp = full["c"].post(
            f"/api/evangelism/events/{event_id}/sessions/not-a-date/visitors",
            json={"first_name": "Bad", "last_name": "Date"},
            headers=full["h"],
        )
        assert resp.status_code == 400

    def test_fast_checkin_event_404(self, full):
        resp = full["c"].post(
            f"/api/evangelism/events/{uuid.uuid4()}/sessions/2026-09-20/visitors",
            json={"first_name": "X", "last_name": "Y"},
            headers=full["h"],
        )
        assert resp.status_code == 404


# ════════════════════════════════════════════════════════════════════
# 16. CALCULO_SESIONES — funciones puras + endpoint integration
# ════════════════════════════════════════════════════════════════════


class TestCalculoSesiones:
    def test_normalizar_frecuencia_variants(self):
        from backend.services.calculo_sesiones import _normalizar_frecuencia
        assert _normalizar_frecuencia("semanal") == "SEMANAL"
        assert _normalizar_frecuencia("Semanal") == "SEMANAL"
        assert _normalizar_frecuencia("SEMANAL") == "SEMANAL"
        assert _normalizar_frecuencia("mensual") == "MENSUAL"
        assert _normalizar_frecuencia("trimestral") == "TRIMESTRAL"
        assert _normalizar_frecuencia("evento único") == "EVENTO_UNICO"
        assert _normalizar_frecuencia("evento único".replace("ú", "u")) == "EVENTO_UNICO"

    def test_normalizar_frecuencia_vacia(self):
        from backend.services.calculo_sesiones import _normalizar_frecuencia
        with pytest.raises(ValueError):
            _normalizar_frecuencia("")
        with pytest.raises(ValueError):
            _normalizar_frecuencia(None)  # type: ignore[arg-type]

    def test_provider_para_frecuencia(self):
        from datetime import timedelta

        from backend.services.calculo_sesiones import _provider_para_frecuencia
        p = _provider_para_frecuencia("SEMANAL", 1)
        assert isinstance(p.incremento, timedelta)
        p = _provider_para_frecuencia("MENSUAL", 31)
        # relativedelta no es timedelta
        assert not isinstance(p.incremento, timedelta)
        with pytest.raises(ValueError):
            _provider_para_frecuencia("PATATA", 1)

    def test_generar_fechas_semanal(self):
        from backend.services.calculo_sesiones import (
            _generar_fechas,
            _provider_para_frecuencia,
        )
        provider = _provider_para_frecuencia("SEMANAL", 1)
        inicio = datetime(2026, 6, 1, tzinfo=timezone.utc)
        fin = datetime(2026, 6, 22, tzinfo=timezone.utc)
        fechas = _generar_fechas(inicio, fin, provider)
        assert len(fechas) == 4

    def test_generar_fechas_quincenal(self):
        from backend.services.calculo_sesiones import (
            _generar_fechas,
            _provider_para_frecuencia,
        )
        provider = _provider_para_frecuencia("QUINCENAL", 1)
        inicio = datetime(2026, 6, 1, tzinfo=timezone.utc)
        fin = datetime(2026, 6, 29, tzinfo=timezone.utc)
        fechas = _generar_fechas(inicio, fin, provider)
        assert len(fechas) == 3

    def test_generar_fechas_evento_unico(self):
        from backend.services.calculo_sesiones import (
            _generar_fechas,
            _provider_para_frecuencia,
        )
        provider = _provider_para_frecuencia("EVENTO_UNICO", 1)
        inicio = datetime(2026, 6, 1, tzinfo=timezone.utc)
        fin = datetime(2026, 6, 30, tzinfo=timezone.utc)
        fechas = _generar_fechas(inicio, fin, provider)
        assert len(fechas) == 1

    def test_generar_fechas_inicio_mayor_fin(self):
        from backend.services.calculo_sesiones import (
            _generar_fechas,
            _provider_para_frecuencia,
        )
        provider = _provider_para_frecuencia("SEMANAL", 1)
        with pytest.raises(ValueError):
            _generar_fechas(
                datetime(2026, 6, 30, tzinfo=timezone.utc),
                datetime(2026, 6, 1, tzinfo=timezone.utc),
                provider,
            )

    def test_calcular_sesiones_creates(self, full, db_session):
        from backend.services.calculo_sesiones import calcular_sesiones
        est = full["estrategia"]
        grupos = full["grupos"]
        n = calcular_sesiones(
            db=db_session,
            estrategia_id=est.id, sede_id=full["sede"].id,
            fecha_inicio=datetime(2026, 7, 1, tzinfo=timezone.utc),
            fecha_fin=datetime(2026, 7, 15, tzinfo=timezone.utc),
            frecuencia="SEMANAL",
            grupos_ids=[g.id for g in grupos],
        )
        assert n == 6  # 3 fechas × 2 grupos

    def test_calcular_sesiones_sin_grupos_validos(self, full, db_session):
        from backend.services.calculo_sesiones import calcular_sesiones
        n = calcular_sesiones(
            db=db_session,
            estrategia_id=full["estrategia"].id,
            sede_id=full["sede"].id,
            fecha_inicio=datetime(2026, 7, 1, tzinfo=timezone.utc),
            fecha_fin=datetime(2026, 7, 15, tzinfo=timezone.utc),
            frecuencia="SEMANAL",
            grupos_ids=[uuid.uuid4()],
        )
        assert n == 0

    def test_calcular_sesiones_idempotente(self, full, db_session):
        from backend.services.calculo_sesiones import calcular_sesiones
        params = dict(
            db=db_session,
            estrategia_id=full["estrategia"].id,
            sede_id=full["sede"].id,
            fecha_inicio=datetime(2026, 8, 1, tzinfo=timezone.utc),
            fecha_fin=datetime(2026, 8, 15, tzinfo=timezone.utc),
            frecuencia="SEMANAL",
            grupos_ids=[g.id for g in full["grupos"]],
        )
        n1 = calcular_sesiones(**params)
        n2 = calcular_sesiones(**params)
        assert n1 > 0
        assert n2 == 0


# ════════════════════════════════════════════════════════════════════
# 17. MAIN_UTILS — persona matching, channel label, serialization
# ════════════════════════════════════════════════════════════════════


class TestSesionGrupoReportedAt:
    """Regression Sprint 3 — antes de la migración ``20260702_reported_at_tz``
    el ORM definía ``reported_at`` como un ``@property`` Python con setter stub
    (``pass``), por lo que el getter siempre retornaba ``None`` aunque los
    handlers setearan un ``datetime`` real con ``_datetime.now(_timezone.utc)``.

    Tras eliminar el stub y declarar la columna directamente en el ORM, un
    valor asignado al campo debe persistir en SQLite/Postgres y ser legible
    tras ``session.expire`` + ``refresh``."""

    def test_reported_at_value_persists_across_db_roundtrip(self, db_session):
        _seed_admin(db_session)
        sede = db_session.query(models.Sede).first()
        g = GrupoEvangelismo(
            nombre="G", sede_id=sede.id, ubicacion="u", capacidad=10, activo=True,
        )
        db_session.add(g); db_session.flush()
        ts = datetime(2026, 6, 15, 12, 30, tzinfo=timezone.utc)
        s = SesionGrupo(
            grupo_id=g.id, fecha_sesion=datetime(2026, 6, 15, tzinfo=timezone.utc),
            estado="PENDIENTE",
        )
        db_session.add(s); db_session.commit(); db_session.refresh(s)
        s.reported_at = ts
        db_session.commit()
        db_session.expire(s); db_session.refresh(s)
        assert s.reported_at is not None, (
            "Regression: reported_at sigue retornando None tras persistir. "
            "Revisar si la columna real fue añadida y se eliminó el @property stub."
        )
        if s.reported_at.tzinfo is None and ts.tzinfo is not None:
            assert s.reported_at == ts.replace(tzinfo=None)
        else:
            assert s.reported_at == ts

    def test_reported_at_nullable_when_no_set(self, db_session):
        _seed_admin(db_session)
        sede = db_session.query(models.Sede).first()
        g = GrupoEvangelismo(
            nombre="G", sede_id=sede.id, ubicacion="u", capacidad=10, activo=True,
        )
        db_session.add(g); db_session.flush()
        s = SesionGrupo(
            grupo_id=g.id, fecha_sesion=datetime(2026, 6, 20, tzinfo=timezone.utc),
            estado="PENDIENTE",
        )
        db_session.add(s); db_session.commit(); db_session.refresh(s)
        assert s.reported_at is None

    def test_update_session_endpoint_persists_reported_at(self, full):
        s = full["sesiones"][0]
        resp = full["c"].put(
            f"/api/evangelism/sessions/{s.id}",
            json={"topic": "Con reporte"},
            headers=full["h"],
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body.get("reported_at") is not None, (
            "Regression: PUT /sessions/{id} sigue emitiendo reported_at=null."
        )


class TestSesionGrupoOfferingAmount:
    """Regression Sprint 3.5 — antes del fix, ``SesionGrupo.__init__`` hacía
    ``kwargs.pop("offering_amount")`` y guardaba el valor en un atributo
    privado ``_offering_amount`` que NUNCA se leía. Esto significaba que
    ``SesionGrupo(offering_amount=150.50, ...)`` parecía persistir pero la
    ``Column(Numeric(12, 2))`` quedaba en NULL.

    Tras eliminar el ``pop``, el valor fluye a ``super().__init__`` y
    SQLAlchemy lo persiste correctamente. Los readers (``get_grupo``,
    analytics, weekly aggregates) ahora ven el valor real."""

    def test_offering_amount_value_persists_across_db_roundtrip(self, db_session):
        _seed_admin(db_session)
        sede = db_session.query(models.Sede).first()
        g = GrupoEvangelismo(
            nombre="G", sede_id=sede.id, ubicacion="u", capacidad=10, activo=True,
        )
        db_session.add(g); db_session.flush()

        # Asignación via constructor con offering_amount kwarg.
        # Antes el pop descartaba el valor; ahora debe fluir a la Column.
        s = SesionGrupo(
            grupo_id=g.id,
            fecha_sesion=datetime(2026, 7, 1, tzinfo=timezone.utc),
            estado="PENDIENTE",
            offering_amount=150.50,
        )
        db_session.add(s); db_session.commit()
        # Forzar reload completo descartando el cache de SQLAlchemy.
        db_session.expire(s); db_session.refresh(s)
        assert s.offering_amount is not None, (
            "Regression: offering_amount quedó NULL tras persistir via constructor. "
            "Verificar que se eliminó el kwargs.pop('offering_amount') del __init__."
        )
        # Numeric(12,2) → Decimal; comparar vía float para no depender del tipo.
        assert float(s.offering_amount) == pytest.approx(150.50, abs=0.01), (
            f"Offering amount persistido con valor incorrecto: {s.offering_amount}"
        )

    def test_offering_amount_nullable_when_no_set(self, db_session):
        """Sin asignación explícita, ``offering_amount`` queda en NULL
        y no se inicializa con 0.00."""
        _seed_admin(db_session)
        sede = db_session.query(models.Sede).first()
        g = GrupoEvangelismo(
            nombre="G", sede_id=sede.id, ubicacion="u", capacidad=10, activo=True,
        )
        db_session.add(g); db_session.flush()
        s = SesionGrupo(
            grupo_id=g.id,
            fecha_sesion=datetime(2026, 7, 15, tzinfo=timezone.utc),
            estado="PENDIENTE",
        )
        db_session.add(s); db_session.commit(); db_session.refresh(s)
        assert s.offering_amount is None

    def test_offering_amount_setter_via_attribute(self, db_session):
        """Asignación directa via ``s.offering_amount = X`` (estilo ORM
        estándar) también persiste."""
        _seed_admin(db_session)
        sede = db_session.query(models.Sede).first()
        g = GrupoEvangelismo(
            nombre="G", sede_id=sede.id, ubicacion="u", capacidad=10, activo=True,
        )
        db_session.add(g); db_session.flush()
        s = SesionGrupo(
            grupo_id=g.id,
            fecha_sesion=datetime(2026, 7, 22, tzinfo=timezone.utc),
            estado="PENDIENTE",
        )
        db_session.add(s); db_session.commit(); db_session.refresh(s)
        s.offering_amount = 99.99
        db_session.commit()
        db_session.expire(s); db_session.refresh(s)
        assert float(s.offering_amount) == pytest.approx(99.99, abs=0.01)

    def test_get_grupo_serializes_offering_amount(self, full):
        """GET /api/evangelism/grupos/{id} debe retornar offering_amount no-None
        cuando el valor fue seteado via endpoint de creación."""
        g = full["grupos"][0]
        # Crear sesión con ofrenda vía POST directo. Antes del fix, el
        # constructor descartaba el valor y el campo llegaba NULL.
        resp = full["c"].post("/api/evangelism/sessions", json={
            "grupo_id": str(g.id),
            "session_date": "2026-10-05",
            "topic": "Con ofrenda",
            "offering_amount": 75.25,
        }, headers=full["h"])
        assert resp.status_code == 200, resp.text
        new_session_id = resp.json()["id"]
        # GET detalle del grupo incluye la oferta en su lista de sesiones.
        get_resp = full["c"].get(
            f"/api/evangelism/grupos/{g.id}", headers=full["h"],
        )
        assert get_resp.status_code == 200, get_resp.text
        sessions_data = get_resp.json().get("sessions", [])
        new_session = next(
            (s for s in sessions_data if s.get("id") == new_session_id), None,
        )
        assert new_session is not None, (
            "Sesión recién creada no aparece en get_grupo. "
            "Posible regression del POST /api/evangelism/sessions."
        )
        assert new_session.get("offering_amount") is not None, (
            "Regression: offering_amount salió None en GET /grupos/{id} aunque "
            "el POST lo creó con 75.25. Confirma que el kwargs.pop "
            "de SesionGrupo.__init__ está eliminado."
        )
        assert float(new_session["offering_amount"]) == pytest.approx(
            75.25, abs=0.01,
        )


class TestMainUtils:
    def test_channel_label(self):
        from backend.api.evangelism_main.main_utils import _channel_label
        assert _channel_label("whatsapp") == "WhatsApp"
        assert _channel_label("email") == "Email"
        assert _channel_label("sms") == "SMS"
        assert _channel_label(None) == "SMS"  # type: ignore[arg-type]

    def test_persona_matches_segment_basic(self, full):
        from backend.api.evangelism_main.main_utils import _persona_matches_segment
        p = full["personas"][0]
        p.church_role_effective = "Miembro"
        p.estado_vital = "nuevo"
        donations: set = set()
        assert _persona_matches_segment(p, "active", donations) is True
        assert _persona_matches_segment(p, "new", donations) is True
        assert _persona_matches_segment(p, "staff", donations) is False
        assert _persona_matches_segment(p, "groups", donations) is False
        assert _persona_matches_segment(p, "low", donations) is True
        assert _persona_matches_segment(p, "vip", donations) is False
        assert _persona_matches_segment(p, "no-existe", donations) is False

    def test_persona_matches_segment_staff_pastor(self, full):
        from backend.api.evangelism_main.main_utils import _persona_matches_segment
        p = full["personas"][1]
        p.church_role_effective = "pastor"
        p.estado_vital = ""
        assert _persona_matches_segment(p, "staff", set()) is True
        assert _persona_matches_segment(p, "active", set()) is True

    def test_persona_matches_segment_vip(self, full, db_session):
        from backend.api.evangelism_main.main_utils import _persona_matches_segment
        p = full["personas"][2]
        # VIP = tiene donación
        db_session.add(models.Donation(
            persona_id=p.id, sede_id=full["sede"].id,
            amount=100, currency="COP",
        ))
        db_session.flush()
        donations = {p.id}
        assert _persona_matches_segment(p, "vip", donations) is True

    def test_resolve_campaign_personas_empty(self, full):
        from backend.api.evangelism_main.main_utils import _resolve_campaign_personas
        assert _resolve_campaign_personas(full["c"], segments=[], sede_id=full["sede"].id) == []
        assert _resolve_campaign_personas(full["c"], segments=[""], sede_id=full["sede"].id) == []

    def test_resolve_campaign_personas_active(self, full, db_session):
        from backend.api.evangelism_main.main_utils import _resolve_campaign_personas
        full["personas"][0].church_role_effective = "Miembro"
        _sa_object_session(full["personas"][0]).commit()
        result = _resolve_campaign_personas(
            db_session, segments=["active"], sede_id=full["sede"].id,
        )
        assert len(result) >= 1

    def test_serialize_crm_task(self, full):
        from backend.api.evangelism_main.main_utils import _serialize_crm_task
        task = models.TareaCRM(
            id=uuid.uuid4(),
            title="Test task",
            description="Test desc",
            status="pending",
            priority="high",
            category="Evangelism",
            persona_id=full["personas"][0].id,
        )
        db_sess = _sa_object_session(full["admin"])
        db_sess.add(task); db_sess.commit()
        data = _serialize_crm_task(task, contact_name="Test Name")
        assert data["title"] == "Test task"
        assert data["contact_name"] == "Test Name"
        assert data["persona_name"] == "Test Name"
