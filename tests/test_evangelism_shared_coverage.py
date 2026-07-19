"""
Coverage tests for evangelism_shared.py — target 90%+.
"""
import uuid
from unittest.mock import MagicMock, patch

import pytest

from backend.api.evangelism_shared import (
    normalize_attendance_status,
    is_attended_status,
    is_absent_status,
    is_excused_status,
    _is_crm_admin_or_pastor,
    _get_persona_for_user,
    session_read_value,
    session_estado_habilitacion,
    sessions_grupo_has_estado_habilitacion,
    get_visible_strategy,
    get_visible_group,
    get_visible_session,
    _can_manage_grupo,
)
from tests.conftest import seed_admin as _seed_admin


@pytest.fixture
def full(client, db_session):
    admin, persona, sede = _seed_admin(db_session)
    return {
        "db": db_session, "admin": admin, "persona": persona, "sede": sede,
    }


class TestAttendanceStatus:
    """Covers normalize_attendance_status and helpers (pure logic)."""

    def test_normalize_present_variants(self):
        assert normalize_attendance_status("ASISTIO") == "present"
        assert normalize_attendance_status("Presente") == "present"
        assert normalize_attendance_status("presente") == "present"
        assert normalize_attendance_status("PRESENT") == "present"

    def test_normalize_absent_variants(self):
        assert normalize_attendance_status("FALTO") == "absent"
        assert normalize_attendance_status("Ausente") == "absent"
        assert normalize_attendance_status("ausente") == "absent"
        assert normalize_attendance_status("ABSENT") == "absent"

    def test_normalize_excused_variants(self):
        assert normalize_attendance_status("EXCUSA") == "excused"
        assert normalize_attendance_status("Excusa") == "excused"
        assert normalize_attendance_status("excusa") == "excused"

    def test_normalize_first_time_as_present(self):
        assert normalize_attendance_status("first_time") == "present"
        assert normalize_attendance_status("primera_vez") == "present"

    def test_normalize_unknown_returns_raw(self):
        assert normalize_attendance_status("unknown_value") == "unknown_value"

    def test_normalize_empty_returns_empty(self):
        assert normalize_attendance_status("") == ""
        assert normalize_attendance_status(None) == ""

    def test_is_attended_status(self):
        assert is_attended_status("ASISTIO") is True
        assert is_attended_status("FALTO") is False

    def test_is_absent_status(self):
        assert is_absent_status("FALTO") is True
        assert is_absent_status("ASISTIO") is False

    def test_is_excused_status(self):
        assert is_excused_status("EXCUSA") is True
        assert is_excused_status("ASISTIO") is False


class TestAdminCheck:
    """Covers _is_crm_admin_or_pastor."""

    def test_admin_role(self):
        user = MagicMock(role="admin")
        assert _is_crm_admin_or_pastor(user) is True

    def test_pastor_role(self):
        user = MagicMock(role="pastor")
        assert _is_crm_admin_or_pastor(user) is True

    def test_reader_role(self):
        user = MagicMock(role="reader")
        assert _is_crm_admin_or_pastor(user) is False

    def test_via_rol_plataforma(self):
        user = MagicMock()
        user.role = ""
        user.rol_plataforma = MagicMock()
        user.rol_plataforma.nombre = "ADMINISTRADOR"
        assert _is_crm_admin_or_pastor(user) is True

    def test_no_role_returns_false(self):
        user = MagicMock(spec=[])
        assert _is_crm_admin_or_pastor(user) is False


class TestGetPersona:
    """Covers _get_persona_for_user."""

    def test_found(self, full):
        p = _get_persona_for_user(full["db"], full["persona"].id)
        assert p is not None
        assert p.id == full["persona"].id

    def test_not_found(self, full):
        p = _get_persona_for_user(full["db"], uuid.uuid4())
        assert p is None

    def test_invalid_uuid(self, full):
        p = _get_persona_for_user(full["db"], "not-a-uuid")
        assert p is None


class TestSessionRead:
    """Covers session_read_value and session_estado_habilitacion."""

    def test_read_value_exists(self):
        session = type("FakeSession", (), {"__dict__": {"estado_habilitacion": "HABILITADO"}})()
        assert session_read_value(session, "estado_habilitacion") == "HABILITADO"

    def test_read_value_default(self):
        session = type("FakeSession", (), {"__dict__": {}})()
        assert session_read_value(session, "nonexistent", "default") == "default"

    def test_read_value_none(self):
        assert session_read_value(None, "field", "default") == "default"


class TestSessionHabilitacion:
    def test_estado_habilitacion_returns_value(self):
        session = MagicMock()
        session.__dict__ = {"estado_habilitacion": "DESHABILITADO"}
        assert session_estado_habilitacion(session) == "DESHABILITADO"

    def test_estado_habilitacion_default(self):
        session = MagicMock()
        session.__dict__ = {}
        assert session_estado_habilitacion(session, "HABILITADO") == "HABILITADO"


class TestVisibleQueries:
    """Covers get_visible_strategy, get_visible_group, get_visible_session."""

    def test_get_visible_strategy_found(self, full):
        from backend.models_evangelism import EstrategiaEvangelismo, CategoriaEstrategia
        from datetime import datetime, timezone
        cat = CategoriaEstrategia(id=uuid.uuid4(), nombre="Cat")
        full["db"].add(cat)
        full["db"].flush()
        s = EstrategiaEvangelismo(
            id=uuid.uuid4(), nombre="Test", sede_id=full["sede"].id,
            categoria_id=cat.id, activa=True,
            fecha_inicio=datetime.now(timezone.utc),
            fecha_fin=datetime.now(timezone.utc),
        )
        full["db"].add(s)
        full["db"].commit()
        result = get_visible_strategy(full["db"], s.id, str(full["sede"].id))
        assert result is not None
        assert result.id == s.id

    def test_get_visible_strategy_not_found(self, full):
        result = get_visible_strategy(full["db"], uuid.uuid4(), str(full["sede"].id))
        assert result is None

    def test_get_visible_group_found(self, full):
        from backend import models
        g = models.GrupoEvangelismo(
            id=uuid.uuid4(), nombre="G", sede_id=full["sede"].id, activo=True,
        )
        full["db"].add(g)
        full["db"].commit()
        result = get_visible_group(full["db"], g.id, str(full["sede"].id))
        assert result is not None

    def test_get_visible_group_not_found(self, full):
        result = get_visible_group(full["db"], uuid.uuid4(), str(full["sede"].id))
        assert result is None

    def test_get_visible_session_found(self, full):
        from backend import models
        from datetime import datetime, timezone
        g = models.GrupoEvangelismo(
            id=uuid.uuid4(), nombre="G2", sede_id=full["sede"].id, activo=True,
        )
        full["db"].add(g)
        full["db"].flush()
        s = models.SesionGrupo(grupo_id=g.id, fecha_sesion=datetime.now(timezone.utc))
        full["db"].add(s)
        full["db"].commit()
        result = get_visible_session(full["db"], s.id, str(full["sede"].id))
        assert result is not None

    def test_get_visible_session_not_found(self, full):
        result = get_visible_session(full["db"], uuid.uuid4(), str(full["sede"].id))
        assert result is None


class TestCanManageGrupo:
    """Covers _can_manage_grupo."""

    def test_admin_can_manage(self, full):
        # admin user should have admin role
        house = MagicMock()
        result = _can_manage_grupo(full["db"], full["admin"], house)
        # Admin role returns True
        assert result is True

    def test_without_persona_returns_false(self, full):
        user = MagicMock(id=uuid.uuid4())
        user.role = "member"
        house = MagicMock()
        result = _can_manage_grupo(full["db"], user, house)
        assert result is False
