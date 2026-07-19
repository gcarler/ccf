"""
Coverage tests for evangelism_reports.py — target 90%+.
"""
import uuid
from datetime import datetime, timezone

import pytest

from backend import models
from backend.api.evangelism_reports import (
    _get_group_or_404,
    _get_leader_name,
    _count_participants,
    _build_session_rows,
)
from tests.conftest import seed_admin as _seed_admin


@pytest.fixture
def full(client, db_session):
    admin, persona, sede = _seed_admin(db_session)
    return {"db": db_session, "admin": admin, "persona": persona, "sede": sede}


def _make_grupo(db, sede_id, persona_id=None):
    g = models.GrupoEvangelismo(
        id=uuid.uuid4(), nombre="TestGrupo", sede_id=sede_id,
        lider_persona_id=persona_id,
    )
    db.add(g)
    db.flush()
    return g


class TestReportsHelpers:
    def test_get_group_or_404_found(self, full):
        grupo = _make_grupo(full["db"], full["sede"].id, full["persona"].id)
        full["db"].commit()
        result = _get_group_or_404(full["db"], grupo.id)
        assert result.id == grupo.id

    def test_get_leader_name_with_persona(self, full):
        grupo = _make_grupo(full["db"], full["sede"].id, full["persona"].id)
        name = _get_leader_name(full["db"], grupo)
        assert full["persona"].first_name in name

    def test_get_leader_name_no_leader(self, full):
        grupo = _make_grupo(full["db"], full["sede"].id, None)
        name = _get_leader_name(full["db"], grupo)
        assert "Sin líder" in name

    def test_count_participants_zero(self, full):
        grupo = _make_grupo(full["db"], full["sede"].id)
        full["db"].commit()
        assert _count_participants(full["db"], grupo.id) == 0

    def test_build_session_rows_empty(self, full):
        grupo = _make_grupo(full["db"], full["sede"].id)
        full["db"].commit()
        assert _build_session_rows(full["db"], grupo.id) == []

    def test_build_session_rows_with_data(self, full):
        grupo = _make_grupo(full["db"], full["sede"].id, full["persona"].id)

        # Need explicit flush or commit between adds
        p = models.ParticipanteGrupo(
            grupo_id=grupo.id, persona_id=full["persona"].id,
            activo=True, rol_base="miembro",
        )
        full["db"].add(p)

        s = models.SesionGrupo(grupo_id=grupo.id, fecha_sesion=datetime.now(timezone.utc))
        full["db"].add(s)
        full["db"].commit()

        rows = _build_session_rows(full["db"], grupo.id)
        assert len(rows) >= 1
