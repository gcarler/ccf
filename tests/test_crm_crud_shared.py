"""Coverage for backend/crud/crm_/shared.py — target 90%+."""

from __future__ import annotations

import uuid as _uuid

import pytest

from backend import models
from backend.crud.crm_ import shared as crud_shared


def _seed_sede(db, name="Sede") -> models.Sede:
    s = models.Sede(id=_uuid.uuid4(), nombre=name, ciudad="City")
    db.add(s)
    db.flush()
    return s


def _seed_persona(db, sede_id, first="Persona") -> models.Persona:
    p = models.Persona(id=_uuid.uuid4(), first_name=first, last_name="Test", sede_id=sede_id)
    db.add(p)
    db.flush()
    return p


def _seed_caso(db, sede_id, persona_id) -> models.CasoCRM:
    from backend.models_crm_pipeline import CanalOrigenEnum, CasoCRM, EstadoCasoEnum, PrioridadCasoEnum

    pipeline_id = _uuid.uuid4()
    etapa_id = _uuid.uuid4()
    c = CasoCRM(
        id=_uuid.uuid4(),
        sede_id=sede_id,
        persona_id=persona_id,
        titulo_caso="Caso Test",
        pipeline_id=pipeline_id,
        etapa_actual_id=etapa_id,
        origen_canal=CanalOrigenEnum.WEB_FORM,
        prioridad=PrioridadCasoEnum.MEDIA,
        estado=EstadoCasoEnum.ABIERTO,
    )
    db.add(c)
    db.flush()
    return c


def _commit(db):
    db.commit()


class TestIsUuidLike:
    def test_valid_uuid(self):
        assert crud_shared._is_uuid_like(_uuid.uuid4()) is True

    def test_valid_uuid_str(self):
        assert crud_shared._is_uuid_like(str(_uuid.uuid4())) is True

    def test_invalid_string(self):
        assert crud_shared._is_uuid_like("not-a-uuid") is False

    def test_none(self):
        assert crud_shared._is_uuid_like(None) is False

    def test_empty_string(self):
        assert crud_shared._is_uuid_like("") is False


class TestResolvePersonaIdForUser:
    def test_none_input(self, db_session):
        assert crud_shared.resolve_persona_id_for_user(db_session, None) is None

    def test_invalid_uuid(self, db_session):
        assert crud_shared.resolve_persona_id_for_user(db_session, "bad") is None

    def test_persona_found(self, db_session):
        sede = _seed_sede(db_session)
        p = _seed_persona(db_session, sede.id)
        _commit(db_session)
        result = crud_shared.resolve_persona_id_for_user(db_session, p.id)
        assert result == p.id

    def test_persona_not_found(self, db_session):
        result = crud_shared.resolve_persona_id_for_user(db_session, _uuid.uuid4())
        assert result is None


class TestResolvePersonaIdFromIdentity:
    def test_delegates(self, db_session):
        assert crud_shared.resolve_persona_id_from_identity(db_session, None) is None
        sede = _seed_sede(db_session)
        p = _seed_persona(db_session, sede.id)
        _commit(db_session)
        result = crud_shared.resolve_persona_id_from_identity(db_session, p.id)
        assert result == p.id


class TestGetUserSedeId:
    def test_no_persona(self, db_session):
        assert crud_shared.get_user_sede_id(db_session, _uuid.uuid4()) is None

    def test_invalid_uuid(self, db_session):
        from unittest.mock import patch

        with patch("backend.core.tenant.get_user_sede_id", return_value="not-a-uuid"):
            assert crud_shared.get_user_sede_id(db_session, _uuid.uuid4()) is None

    def test_found(self, db_session):
        sede = _seed_sede(db_session)
        p = _seed_persona(db_session, sede.id)
        _commit(db_session)
        result = crud_shared.get_user_sede_id(db_session, p.id)
        assert result == sede.id


class TestActorSedeOrNone:
    def test_invalid_uuid_raises(self, db_session):
        with pytest.raises(Exception):
            crud_shared._actor_sede_or_none(db_session, "bad-uuid")

    def test_no_persona_raises(self, db_session):
        with pytest.raises(Exception):
            crud_shared._actor_sede_or_none(db_session, _uuid.uuid4())

    def test_found(self, db_session):
        sede = _seed_sede(db_session)
        p = _seed_persona(db_session, sede.id)
        _commit(db_session)
        result = crud_shared._actor_sede_or_none(db_session, p.id)
        assert result == sede.id


class TestResolveAnchorSede:
    def test_none_anchor_value(self, db_session):
        assert crud_shared._resolve_anchor_sede(db_session, "caso_id", None) is None

    def test_unknown_anchor_name(self, db_session):
        assert crud_shared._resolve_anchor_sede(db_session, "unknown", _uuid.uuid4()) is None

    def test_caso_id_found(self, db_session):
        sede = _seed_sede(db_session)
        p = _seed_persona(db_session, sede.id)
        caso = _seed_caso(db_session, sede.id, p.id)
        _commit(db_session)
        result = crud_shared._resolve_anchor_sede(db_session, "caso_id", caso.id)
        assert result == sede.id

    def test_caso_id_not_found(self, db_session):
        result = crud_shared._resolve_anchor_sede(db_session, "caso_id", _uuid.uuid4())
        assert result is None

    def test_persona_id_found(self, db_session):
        sede = _seed_sede(db_session)
        p = _seed_persona(db_session, sede.id)
        _commit(db_session)
        result = crud_shared._resolve_anchor_sede(db_session, "persona_id", p.id)
        assert result == sede.id

    def test_asignado_a_id_found(self, db_session):
        sede = _seed_sede(db_session)
        p = _seed_persona(db_session, sede.id)
        _commit(db_session)
        result = crud_shared._resolve_anchor_sede(db_session, "asignado_a_id", p.id)
        assert result == sede.id


class TestCrudScopeReCheckTask:
    def test_no_user_sede_returns(self, db_session):
        p = models.Persona(id=_uuid.uuid4(), first_name="NoSede", last_name="X")
        db_session.add(p)
        _commit(db_session)
        crud_shared._crud_scope_re_check_task(db_session, p.id)

    def test_orphan_all_none_raises(self, db_session):
        sede = _seed_sede(db_session)
        p = _seed_persona(db_session, sede.id)
        _commit(db_session)
        with pytest.raises(Exception):
            crud_shared._crud_scope_re_check_task(
                db_session,
                p.id,
                incoming_anchors={"caso_id": None},
                current_row_anchors={"persona_id": None},
            )

    def test_no_combined_anchors_returns(self, db_session):
        sede = _seed_sede(db_session)
        p = _seed_persona(db_session, sede.id)
        _commit(db_session)
        crud_shared._crud_scope_re_check_task(db_session, p.id)

    def test_cross_sede_raises(self, db_session):
        s1 = _seed_sede(db_session, "S1")
        s2 = _seed_sede(db_session, "S2")
        p1 = _seed_persona(db_session, s1.id, "Actor")
        p2 = _seed_persona(db_session, s2.id, "Other")
        _commit(db_session)
        with pytest.raises(Exception):
            crud_shared._crud_scope_re_check_task(
                db_session,
                p1.id,
                incoming_anchors={"persona_id": p2.id},
            )

    def test_same_sede_passes(self, db_session):
        sede = _seed_sede(db_session)
        p1 = _seed_persona(db_session, sede.id, "Actor")
        p2 = _seed_persona(db_session, sede.id, "Other")
        _commit(db_session)
        crud_shared._crud_scope_re_check_task(
            db_session,
            p1.id,
            incoming_anchors={"persona_id": p2.id},
        )

    def test_mixed_none_and_value_anchors(self, db_session):
        sede = _seed_sede(db_session)
        p1 = _seed_persona(db_session, sede.id, "Actor")
        p2 = _seed_persona(db_session, sede.id, "Other")
        _commit(db_session)
        crud_shared._crud_scope_re_check_task(
            db_session,
            p1.id,
            incoming_anchors={"persona_id": p2.id, "caso_id": None},
        )


class TestAuditLog:
    def test_basic(self, db_session):
        from backend.models_evangelism import LogAuditoria

        crud_shared._audit_log(db_session, "test_table", "123", "CREATE", {"key": "val"})
        _commit(db_session)
        entry = db_session.query(LogAuditoria).first()
        assert entry is not None
        assert entry.tabla_afectada == "test_table"

    def test_with_usuario_id(self, db_session):
        from backend.models_evangelism import LogAuditoria

        uid = _uuid.uuid4()
        crud_shared._audit_log(db_session, "t", "1", "UPDATE", usuario_id=str(uid))
        _commit(db_session)
        entry = db_session.query(LogAuditoria).first()
        assert entry is not None


class TestGetLiveColumnNames:
    def test_personas(self, db_session):
        result = crud_shared._get_live_column_names(db_session, "personas")
        assert "id" in result

    def test_cache_hit(self, db_session):
        result1 = crud_shared._get_live_column_names(db_session, "personas")
        result2 = crud_shared._get_live_column_names(db_session, "personas")
        assert result1 == result2

    def test_nonexistent_table(self, db_session):
        result = crud_shared._get_live_column_names(db_session, "nonexistent_table_xyz")
        assert result == set()


class TestCaseCreatedColumn:
    def test_returns_something(self, db_session):
        result = crud_shared._case_created_column(db_session)
        assert result is not None


class TestPersonaQuery:
    def test_returns_query(self, db_session):
        q = crud_shared.persona_query(db_session)
        assert q is not None


class TestCaseQuery:
    def test_returns_query(self, db_session):
        q = crud_shared.case_query(db_session)
        assert q is not None


class TestPreparePersonaForOutput:
    def test_basic(self, db_session):
        sede = _seed_sede(db_session)
        p = _seed_persona(db_session, sede.id, "Output")
        _commit(db_session)
        result = crud_shared.prepare_persona_for_output(db_session, p)
        assert result is p


class TestPrepareCaseForOutput:
    def test_basic(self, db_session):
        sede = _seed_sede(db_session)
        p = _seed_persona(db_session, sede.id)
        caso = _seed_caso(db_session, sede.id, p.id)
        _commit(db_session)
        result = crud_shared.prepare_case_for_output(db_session, caso)
        assert result is caso

    def test_with_relationships(self, db_session):
        sede = _seed_sede(db_session)
        p = _seed_persona(db_session, sede.id, "Owner")
        caso = _seed_caso(db_session, sede.id, p.id)
        caso.asignado_a_id = p.id
        _commit(db_session)
        result = crud_shared.prepare_case_for_output(db_session, caso)
        assert result is caso
