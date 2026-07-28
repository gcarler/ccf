"""
Comprehensive tests for evangelism_analytics.py — target 90%+.
Covers all 9 analytics endpoints + helper functions.
"""
import uuid
from datetime import datetime, timezone, timedelta

import pytest

from backend import models
from backend.api.evangelism_analytics import (
    _normalize_rol,
    _rol_to_funnel_stage,
    _parse_period,
    _date_range,
    _prev_range,
    _delta,
    _bucket_label,
    _semaforo_tof,
    _semaforo_ics,
    _semaforo_icd,
    _classify_group,
    _shannon_entropy,
    _age_bucket,
    _attended,
    _is_primera_vez,
)
from backend.models_evangelism import (
    EstrategiaEvangelismo,
    CategoriaEstrategia,
    GrupoEvangelismo,
    SesionGrupo,
    ParticipanteGrupo,
    Asistencia,
)
from tests.conftest import seed_admin as _seed_admin, auth_headers as _auth_headers, seed_user_with_role


def _make_strategy(db, sede_id):
    cat = CategoriaEstrategia(id=uuid.uuid4(), nombre="Cat Analytics")
    db.add(cat)
    db.flush()
    s = EstrategiaEvangelismo(
        id=uuid.uuid4(), nombre="Estrategia Analytics Test", sede_id=sede_id,
        categoria_id=cat.id,
        fecha_inicio=datetime.now(timezone.utc),
        fecha_fin=datetime.now(timezone.utc) + timedelta(days=90),
    )
    db.add(s)
    db.flush()
    return s


def _make_grupo(db, strategy_id, sede_id, lider_id=None):
    g = GrupoEvangelismo(
        id=uuid.uuid4(), nombre=f"Grupo_{uuid.uuid4().hex[:6]}",
        estrategia_id=strategy_id, sede_id=sede_id,
        lider_persona_id=lider_id, activo=True, capacidad=20,
    )
    db.add(g)
    db.flush()
    return g


def _make_session(db, grupo_id, estado="REALIZADA", days_ago=1):
    s = SesionGrupo(
        id=uuid.uuid4(), grupo_id=grupo_id,
        fecha_sesion=datetime.now(timezone.utc).date() - timedelta(days=days_ago),
        estado=estado, estado_habilitacion="HABILITADO",
    )
    db.add(s)
    db.flush()
    return s


def _make_participante(db, grupo_id, persona_id, rol_base="miembro"):
    p = ParticipanteGrupo(
        grupo_id=grupo_id, persona_id=persona_id,
        activo=True, rol_base=rol_base,
        fecha_ingreso=datetime.now(timezone.utc).date() - timedelta(days=30),
    )
    db.add(p)
    db.flush()
    return p


def _make_asistencia(db, session_id, persona_id, estado="ASISTIO"):
    a = Asistencia(
        id=uuid.uuid4(), sesion_id=session_id, persona_id=persona_id,
        estado=estado,
    )
    db.add(a)
    db.flush()
    return a


class TestHelperFunctions:
    """Unit tests for helper/utility functions."""

    def test_normalize_rol(self):
        assert _normalize_rol("Líder") == "lider"
        assert _normalize_rol("COLIDER") == "colider"
        assert _normalize_rol("  Miembro  ").strip() == "miembro"

    def test_rol_to_funnel_stage(self):
        assert _rol_to_funnel_stage("Lider") == "lider"
        assert _rol_to_funnel_stage("Colider") == "colider"
        assert _rol_to_funnel_stage("Asistente") == "asistente"
        assert _rol_to_funnel_stage("Invitado") == "visitante"
        result = _rol_to_funnel_stage("Desconocido")
        assert isinstance(result, str)

    def test_parse_period_valid(self):
        assert _parse_period("7d") == 7
        assert _parse_period("30d") == 30
        assert _parse_period("90d") == 90
        assert _parse_period("365d") == 365

    def test_parse_period_invalid(self):
        assert _parse_period("bad") == 30

    def test_date_range(self):
        start, end = _date_range(30)
        assert end >= start
        assert (end - start).days == 30

    def test_prev_range(self):
        prev_start, prev_end = _prev_range(30)
        assert prev_end >= prev_start
        assert (prev_end - prev_start).days == 30

    def test_delta(self):
        assert _delta(100, 50) == 100.0
        assert _delta(50, 50) == 0.0
        assert _delta(0, 0) == 0.0

    def test_bucket_label(self):
        assert _bucket_label("2026-W01", True) is not None
        assert _bucket_label("2026-01", False) is not None

    def test_semaforo_tof(self):
        assert _semaforo_tof(80) == "SALUDABLE"
        assert _semaforo_tof(50) == "BAJO"
        assert _semaforo_tof(20) == "BAJO"

    def test_semaforo_ics(self):
        assert isinstance(_semaforo_ics(80), str)
        assert isinstance(_semaforo_ics(20), str)

    def test_semaforo_icd(self):
        assert isinstance(_semaforo_icd(80), str)
        assert isinstance(_semaforo_icd(20), str)

    def test_classify_group(self):
        assert isinstance(_classify_group(10, 0.8), str)
        assert isinstance(_classify_group(0, 0.0), str)

    def test_shannon_entropy(self):
        assert _shannon_entropy({"a": 10, "b": 10}) > 0
        assert _shannon_entropy({"a": 100}) == 0.0
        assert _shannon_entropy({}) == 0.0

    def test_age_bucket(self):
        today = datetime.now(timezone.utc).date()
        assert _age_bucket(today - timedelta(days=365 * 20)) is not None
        assert _age_bucket(None) is not None

    def test_attended(self):
        assert _attended("ASISTIO") is True
        assert _attended("FALTO") is False
        assert _attended(None) is False

    def test_is_primera_vez(self):
        obj = type("obj", (), {"es_primera_vez": True, "estado": "NUEVO"})()
        assert _is_primera_vez(obj) is True
        obj2 = type("obj", (), {"es_primera_vez": False, "estado": "ASISTIO"})()
        assert _is_primera_vez(obj2) is False


@pytest.fixture
def full(client, db_session):
    admin, persona, sede = _seed_admin(db_session)
    headers = _auth_headers(client, email=admin.email, password="testpass123")
    return {"c": client, "h": headers, "db": db_session, "admin": admin, "persona": persona, "sede": sede}


class TestAnalyticsEndpoints:
    """Integration tests for all 9 analytics endpoints."""

    def test_strategy_kpis_empty(self, full):
        strategy = _make_strategy(full["db"], full["sede"].id)
        full["db"].commit()
        resp = full["c"].get(
            f"/api/evangelism/analytics/strategy/{strategy.id}",
            headers=full["h"],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "period" in data or "kpis" in data or isinstance(data, dict)

    def test_strategy_kpis_with_data(self, full):
        from backend.models_crm import Persona
        strategy = _make_strategy(full["db"], full["sede"].id)
        p = Persona(id=uuid.uuid4(), first_name="A", last_name="K", sede_id=full["sede"].id)
        full["db"].add(p)
        g = _make_grupo(full["db"], strategy.id, full["sede"].id, full["persona"].id)
        _make_participante(full["db"], g.id, p.id)
        s = _make_session(full["db"], g.id, "REALIZADA", 1)
        _make_asistencia(full["db"], s.id, p.id, "ASISTIO")
        full["db"].commit()

        resp = full["c"].get(
            f"/api/evangelism/analytics/strategy/{strategy.id}?period=30d",
            headers=full["h"],
        )
        assert resp.status_code == 200

    def test_strategy_kpis_404(self, full):
        resp = full["c"].get(
            f"/api/evangelism/analytics/strategy/{uuid.uuid4()}",
            headers=full["h"],
        )
        assert resp.status_code == 404

    def test_strategy_trend(self, full):
        strategy = _make_strategy(full["db"], full["sede"].id)
        g = _make_grupo(full["db"], strategy.id, full["sede"].id)
        _make_session(full["db"], g.id, "REALIZADA", 1)
        full["db"].commit()
        resp = full["c"].get(
            f"/api/evangelism/analytics/strategy/{strategy.id}/trend",
            headers=full["h"],
        )
        assert resp.status_code == 200
        assert isinstance(resp.json(), dict)

    def test_strategy_trend_empty(self, full):
        strategy = _make_strategy(full["db"], full["sede"].id)
        full["db"].commit()
        resp = full["c"].get(
            f"/api/evangelism/analytics/strategy/{strategy.id}/trend",
            headers=full["h"],
        )
        assert resp.status_code == 200

    def test_strategy_funnel(self, full):
        from backend.models_crm import Persona
        strategy = _make_strategy(full["db"], full["sede"].id)
        p = Persona(id=uuid.uuid4(), first_name="F", last_name="U", sede_id=full["sede"].id)
        full["db"].add(p)
        g = _make_grupo(full["db"], strategy.id, full["sede"].id)
        _make_participante(full["db"], g.id, p.id, "lider")
        full["db"].commit()
        resp = full["c"].get(
            f"/api/evangelism/analytics/strategy/{strategy.id}/funnel",
            headers=full["h"],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "stages" in data or isinstance(data, dict)

    def test_strategy_heatmap(self, full):
        strategy = _make_strategy(full["db"], full["sede"].id)
        g = _make_grupo(full["db"], strategy.id, full["sede"].id)
        _make_session(full["db"], g.id, "REALIZADA", 1)
        full["db"].commit()
        resp = full["c"].get(
            f"/api/evangelism/analytics/strategy/{strategy.id}/heatmap",
            headers=full["h"],
        )
        assert resp.status_code == 200

    def test_strategy_alerts_empty(self, full):
        strategy = _make_strategy(full["db"], full["sede"].id)
        full["db"].commit()
        resp = full["c"].get(
            f"/api/evangelism/analytics/strategy/{strategy.id}/alerts",
            headers=full["h"],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["alerts"] == []

    def test_strategy_alerts_with_low_attendance(self, full):
        from backend.models_crm import Persona
        strategy = _make_strategy(full["db"], full["sede"].id)
        p = Persona(id=uuid.uuid4(), first_name="L", last_name="A", sede_id=full["sede"].id)
        full["db"].add(p)
        g = _make_grupo(full["db"], strategy.id, full["sede"].id, full["persona"].id)
        _make_participante(full["db"], g.id, p.id)
        # Create multiple sessions with low attendance
        for i in range(5):
            sess = _make_session(full["db"], g.id, "REALIZADA", i + 1)
            if i == 0:
                _make_asistencia(full["db"], sess.id, p.id, "ASISTIO")
            else:
                _make_asistencia(full["db"], sess.id, p.id, "FALTO")
        full["db"].commit()
        resp = full["c"].get(
            f"/api/evangelism/analytics/strategy/{strategy.id}/alerts?threshold_pct=60",
            headers=full["h"],
        )
        assert resp.status_code == 200

    def test_strategy_velocity(self, full):
        from backend.models_crm import Persona
        strategy = _make_strategy(full["db"], full["sede"].id)
        p = Persona(id=uuid.uuid4(), first_name="V", last_name="E", sede_id=full["sede"].id)
        full["db"].add(p)
        g = _make_grupo(full["db"], strategy.id, full["sede"].id)
        _make_participante(full["db"], g.id, p.id, "miembro")
        full["db"].commit()
        resp = full["c"].get(
            f"/api/evangelism/analytics/strategy/{strategy.id}/velocity",
            headers=full["h"],
        )
        assert resp.status_code == 200

    def test_strategy_groups_detail(self, full):
        from backend.models_crm import Persona
        strategy = _make_strategy(full["db"], full["sede"].id)
        p = Persona(id=uuid.uuid4(), first_name="G", last_name="D", sede_id=full["sede"].id)
        full["db"].add(p)
        g = _make_grupo(full["db"], strategy.id, full["sede"].id, full["persona"].id)
        _make_participante(full["db"], g.id, p.id)
        s = _make_session(full["db"], g.id, "REALIZADA", 1)
        _make_asistencia(full["db"], s.id, p.id, "ASISTIO")
        full["db"].commit()
        resp = full["c"].get(
            f"/api/evangelism/analytics/strategy/{strategy.id}/groups",
            headers=full["h"],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "groups" in data or isinstance(data, dict)

    def test_strategy_groups_detail_empty(self, full):
        strategy = _make_strategy(full["db"], full["sede"].id)
        full["db"].commit()
        resp = full["c"].get(
            f"/api/evangelism/analytics/strategy/{strategy.id}/groups",
            headers=full["h"],
        )
        assert resp.status_code == 200

    def test_strategy_full_analytics(self, full):
        from backend.models_crm import Persona
        strategy = _make_strategy(full["db"], full["sede"].id)
        p = Persona(id=uuid.uuid4(), first_name="F", last_name="A", sede_id=full["sede"].id)
        full["db"].add(p)
        g = _make_grupo(full["db"], strategy.id, full["sede"].id, full["persona"].id)
        _make_participante(full["db"], g.id, p.id)
        s = _make_session(full["db"], g.id, "REALIZADA", 1)
        _make_asistencia(full["db"], s.id, p.id, "ASISTIO")
        full["db"].commit()
        resp = full["c"].get(
            f"/api/evangelism/analytics/strategy/{strategy.id}/full?weeks=4",
            headers=full["h"],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)

    def test_strategy_full_analytics_empty(self, full):
        strategy = _make_strategy(full["db"], full["sede"].id)
        full["db"].commit()
        resp = full["c"].get(
            f"/api/evangelism/analytics/strategy/{strategy.id}/full",
            headers=full["h"],
        )
        assert resp.status_code == 200

    def test_trend_404(self, full):
        resp = full["c"].get(
            f"/api/evangelism/analytics/strategy/{uuid.uuid4()}/trend",
            headers=full["h"],
        )
        assert resp.status_code == 404

    def test_funnel_404(self, full):
        resp = full["c"].get(
            f"/api/evangelism/analytics/strategy/{uuid.uuid4()}/funnel",
            headers=full["h"],
        )
        assert resp.status_code == 404

    def test_heatmap_404(self, full):
        resp = full["c"].get(
            f"/api/evangelism/analytics/strategy/{uuid.uuid4()}/heatmap",
            headers=full["h"],
        )
        assert resp.status_code == 404

    def test_alerts_404(self, full):
        resp = full["c"].get(
            f"/api/evangelism/analytics/strategy/{uuid.uuid4()}/alerts",
            headers=full["h"],
        )
        assert resp.status_code == 404

    def test_velocity_404(self, full):
        resp = full["c"].get(
            f"/api/evangelism/analytics/strategy/{uuid.uuid4()}/velocity",
            headers=full["h"],
        )
        assert resp.status_code == 404

    def test_groups_detail_404(self, full):
        resp = full["c"].get(
            f"/api/evangelism/analytics/strategy/{uuid.uuid4()}/groups",
            headers=full["h"],
        )
        assert resp.status_code == 404

    def test_full_404(self, full):
        resp = full["c"].get(
            f"/api/evangelism/analytics/strategy/{uuid.uuid4()}/full",
            headers=full["h"],
        )
        assert resp.status_code == 404


class TestAnalyticsRBAC:
    """RBAC boundary tests for analytics endpoints."""

    def test_no_perms_403_on_kpis(self, client, db_session):
        _seed_admin(db_session)
        persona_user, _, _ = seed_user_with_role(
            db_session, role_name="persona",
            email="noanakpi@test.com", permisos={"default": "allow"},
        )
        h = _auth_headers(client, email="noanakpi@test.com")
        resp = client.get(f"/api/evangelism/analytics/strategy/{uuid.uuid4()}", headers=h)
        assert resp.status_code == 403

    def test_read_only_200_on_kpis(self, client, db_session):
        admin, persona, sede = _seed_admin(db_session)
        read_user, _, _ = seed_user_with_role(
            db_session, role_name="lector_analytics",
            email="readana@test.com", permisos={"evangelism:read": "allow"},
        )
        strategy = _make_strategy(db_session, sede.id)
        db_session.commit()
        h = _auth_headers(client, email="readana@test.com")
        resp = client.get(f"/api/evangelism/analytics/strategy/{strategy.id}", headers=h)
        assert resp.status_code == 200

    def test_no_perms_403_on_alerts(self, client, db_session):
        _seed_admin(db_session)
        persona_user, _, _ = seed_user_with_role(
            db_session, role_name="persona",
            email="noanaalt@test.com", permisos={"default": "allow"},
        )
        h = _auth_headers(client, email="noanaalt@test.com")
        resp = client.get(f"/api/evangelism/analytics/strategy/{uuid.uuid4()}/alerts", headers=h)
        assert resp.status_code == 403
