"""
Comprehensive tests for evangelism_shared.py — target 90%+.
Covers session helpers, attendance normalization, visible resolvers, triggers.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from backend.api.evangelism_shared import (
    ABSENT_STATES,
    ATTENDED_STATES,
    EXCUSED_STATES,
    FIRST_TIME_STATES,
    _can_manage_grupo,
    _get_persona_for_user,
    _is_crm_admin_or_pastor,
    get_visible_group,
    get_visible_session,
    get_visible_strategy,
    is_absent_status,
    is_attended_status,
    is_excused_status,
    normalize_attendance_status,
    session_estado_habilitacion,
    session_read_value,
)
from backend.models_evangelism import (
    CategoriaEstrategia,
    EstrategiaEvangelismo,
    GrupoEvangelismo,
    SesionGrupo,
)
from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin


def _make_strategy(db, sede_id):
    cat = CategoriaEstrategia(id=uuid.uuid4(), nombre="Cat Shared")
    db.add(cat)
    db.flush()
    s = EstrategiaEvangelismo(
        id=uuid.uuid4(),
        nombre="Estrategia Shared",
        sede_id=sede_id,
        categoria_id=cat.id,
        fecha_inicio=datetime.now(timezone.utc),
        fecha_fin=datetime.now(timezone.utc) + timedelta(days=90),
    )
    db.add(s)
    db.flush()
    return s


def _make_grupo(db, strategy_id, sede_id, lider_id=None):
    g = GrupoEvangelismo(
        id=uuid.uuid4(),
        nombre=f"G_{uuid.uuid4().hex[:6]}",
        estrategia_id=strategy_id,
        sede_id=sede_id,
        lider_persona_id=lider_id,
        activo=True,
        capacidad=20,
    )
    db.add(g)
    db.flush()
    return g


def _make_session(db, grupo_id, estado="REALIZADA"):
    s = SesionGrupo(
        id=uuid.uuid4(),
        grupo_id=grupo_id,
        fecha_sesion=datetime.now(timezone.utc).date(),
        estado=estado,
        estado_habilitacion="HABILITADO",
    )
    db.add(s)
    db.flush()
    return s


@pytest.fixture
def full(client, db_session):
    admin, persona, sede = _seed_admin(db_session)
    headers = _auth_headers(client, email=admin.email, password="testpass123")
    return {"c": client, "h": headers, "db": db_session, "admin": admin, "persona": persona, "sede": sede}


class TestAttendanceNormalization:
    """Tests for normalize_attendance_status and derived helpers."""

    def test_normalize_attended_states(self):
        for state in ATTENDED_STATES:
            result = normalize_attendance_status(state)
            assert result == "present", f"{state} should normalize to present, got {result}"

    def test_normalize_absent_states(self):
        for state in ABSENT_STATES:
            result = normalize_attendance_status(state)
            assert result == "absent", f"{state} should normalize to absent, got {result}"

    def test_normalize_excused_states(self):
        for state in EXCUSED_STATES:
            result = normalize_attendance_status(state)
            assert result == "excused", f"{state} should normalize to excused, got {result}"

    def test_normalize_first_time_states(self):
        for state in FIRST_TIME_STATES:
            result = normalize_attendance_status(state)
            assert result == "present", f"first_time state {state} should normalize to present"

    def test_normalize_unknown_passthrough(self):
        result = normalize_attendance_status("WEIRD_STATUS")
        assert result == "weird_status"

    def test_normalize_none(self):
        result = normalize_attendance_status(None)
        assert result == ""

    def test_is_attended_status(self):
        assert is_attended_status("ASISTIO") is True
        assert is_attended_status("FALTO") is False
        assert is_attended_status("EXCUSA") is False

    def test_is_absent_status(self):
        assert is_absent_status("FALTO") is True
        assert is_absent_status("ASISTIO") is False

    def test_is_excused_status(self):
        assert is_excused_status("EXCUSA") is True
        assert is_excused_status("ASISTIO") is False


class TestSessionHelpers:
    """Tests for session read helpers."""

    def test_session_read_value_with_attr(self):
        class FakeSession:
            __dict__ = {"estado_habilitacion": "HABILITADO", "id": "x"}

        assert session_read_value(FakeSession(), "estado_habilitacion") == "HABILITADO"
        assert session_read_value(FakeSession(), "missing", "default") == "default"

    def test_session_read_value_no_dict(self):
        assert session_read_value(None, "field", "default") == "default"

    def test_session_estado_habilitacion_with_value(self):
        class FakeSession:
            __dict__ = {"estado_habilitacion": "CERRADO"}

        assert session_estado_habilitacion(FakeSession()) == "CERRADO"

    def test_session_estado_habilitacion_default(self):
        class FakeSession:
            __dict__ = {}

        assert session_estado_habilitacion(FakeSession()) == "HABILITADO"


class TestIsCrmAdminOrPastor:
    """Tests for _is_crm_admin_or_pastor."""

    def test_admin_role(self):
        user = type("User", (), {"role": "admin", "rol_plataforma": None})()
        assert _is_crm_admin_or_pastor(user) is True

    def test_pastor_role(self):
        user = type("User", (), {"role": "pastor", "rol_plataforma": None})()
        assert _is_crm_admin_or_pastor(user) is True

    def test_coordinador_role(self):
        user = type("User", (), {"role": "coordinador", "rol_plataforma": None})()
        assert _is_crm_admin_or_pastor(user) is True

    def test_miembro_role(self):
        user = type("User", (), {"role": "miembro", "rol_plataforma": None})()
        assert _is_crm_admin_or_pastor(user) is False


class TestGetPersonaForUser:
    """Tests for _get_persona_for_user."""

    def test_valid_uuid(self, full):
        result = _get_persona_for_user(full["db"], str(full["persona"].id))
        assert result is not None
        assert result.id == full["persona"].id

    def test_invalid_uuid(self, full):
        result = _get_persona_for_user(full["db"], "not-a-uuid")
        assert result is None

    def test_none(self, full):
        result = _get_persona_for_user(full["db"], None)
        assert result is None


class TestVisibleResolvers:
    """Tests for get_visible_strategy, get_visible_group, get_visible_session."""

    def test_get_visible_strategy_found(self, full):
        strategy = _make_strategy(full["db"], full["sede"].id)
        full["db"].commit()
        result = get_visible_strategy(full["db"], strategy.id, str(full["sede"].id))
        assert result is not None
        assert result.id == strategy.id

    def test_get_visible_strategy_wrong_sede(self, full):
        strategy = _make_strategy(full["db"], full["sede"].id)
        full["db"].commit()
        result = get_visible_strategy(full["db"], strategy.id, str(uuid.uuid4()))
        assert result is None

    def test_get_visible_strategy_deleted(self, full):
        strategy = _make_strategy(full["db"], full["sede"].id)
        strategy.deleted_at = datetime.now(timezone.utc)
        full["db"].commit()
        result = get_visible_strategy(full["db"], strategy.id, str(full["sede"].id))
        assert result is None

    def test_get_visible_group_found(self, full):
        strategy = _make_strategy(full["db"], full["sede"].id)
        g = _make_grupo(full["db"], strategy.id, full["sede"].id)
        full["db"].commit()
        result = get_visible_group(full["db"], g.id, str(full["sede"].id))
        assert result is not None

    def test_get_visible_group_wrong_sede(self, full):
        strategy = _make_strategy(full["db"], full["sede"].id)
        g = _make_grupo(full["db"], strategy.id, full["sede"].id)
        full["db"].commit()
        result = get_visible_group(full["db"], g.id, str(uuid.uuid4()))
        assert result is None

    def test_get_visible_session_found(self, full):
        strategy = _make_strategy(full["db"], full["sede"].id)
        g = _make_grupo(full["db"], strategy.id, full["sede"].id)
        s = _make_session(full["db"], g.id)
        full["db"].commit()
        result = get_visible_session(full["db"], s.id, str(full["sede"].id))
        assert result is not None
        assert result.id == s.id

    def test_get_visible_session_wrong_sede(self, full):
        strategy = _make_strategy(full["db"], full["sede"].id)
        g = _make_grupo(full["db"], strategy.id, full["sede"].id)
        s = _make_session(full["db"], g.id)
        full["db"].commit()
        result = get_visible_session(full["db"], s.id, str(uuid.uuid4()))
        assert result is None


class TestCanManageGrupo:
    """Tests for _can_manage_grupo."""

    def test_admin_can_manage(self, full):
        strategy = _make_strategy(full["db"], full["sede"].id)
        g = _make_grupo(full["db"], strategy.id, full["sede"].id)
        full["db"].commit()
        assert _can_manage_grupo(full["db"], full["admin"], g) is True

    def test_non_leader_cannot_manage(self, full):
        from backend.models_crm import Persona

        strategy = _make_strategy(full["db"], full["sede"].id)
        other = Persona(id=uuid.uuid4(), first_name="Other", last_name="User", sede_id=full["sede"].id)
        full["db"].add(other)
        g = _make_grupo(full["db"], strategy.id, full["sede"].id, full["persona"].id)
        full["db"].commit()
        user = type("User", (), {"role": "miembro", "rol_plataforma": None, "id": str(uuid.uuid4())})()
        assert _can_manage_grupo(full["db"], user, g) is False
