"""Tests for backend.crud.crm_.shared utilities."""
from __future__ import annotations

import uuid

from backend import models
from backend.crud.crm_.shared import (
    _get_live_column_names,
    _is_uuid_like,
    _persona_live_column_names,
    _resolve_anchor_sede,
    case_query,
    get_user_sede_id,
    persona_query,
    prepare_case_for_output,
    prepare_persona_for_output,
    resolve_persona_id_for_user,
)

# ── _is_uuid_like ─────────────────────────────────────────────────────────


class TestIsUuidLike:
    def test_valid_uuid_str(self):
        assert _is_uuid_like(str(uuid.uuid4())) is True

    def test_invalid_str(self):
        assert _is_uuid_like("not-a-uuid") is False
        assert _is_uuid_like("") is False

    def test_none(self):
        assert _is_uuid_like(None) is False

    def test_uuid_object(self):
        assert _is_uuid_like(uuid.uuid4()) is True

    def test_int(self):
        assert _is_uuid_like(12345) is False


# ── resolve_persona_id_for_user ───────────────────────────────────────────


class TestResolvePersonaIdForUser:
    def test_none(self, db_session):
        assert resolve_persona_id_for_user(db_session, None) is None

    def test_existing_persona(self, db_session):
        p = models.Persona(id=uuid.uuid4(), first_name="Resolve", last_name="Test")
        db_session.add(p)
        db_session.commit()

        result = resolve_persona_id_for_user(db_session, p.id)
        assert result == p.id

    def test_nonexistent_uuid(self, db_session):
        result = resolve_persona_id_for_user(db_session, uuid.uuid4())
        assert result is None

    def test_invalid_uuid_string(self, db_session):
        result = resolve_persona_id_for_user(db_session, "not-a-uuid")
        assert result is None


# ── get_user_sede_id ──────────────────────────────────────────────────────


class TestGetUserSedeId:
    def test_persona_with_sede(self, db_session):
        sede = models.Sede(id=uuid.uuid4(), nombre="Sede", ciudad="City")
        db_session.add(sede)
        db_session.commit()
        p = models.Persona(id=uuid.uuid4(), first_name="Sede", last_name="User", sede_id=sede.id)
        db_session.add(p)
        db_session.commit()

        result = get_user_sede_id(db_session, p.id)
        assert result == sede.id

    def test_persona_no_sede(self, db_session):
        p = models.Persona(id=uuid.uuid4(), first_name="NoSede", last_name="User")
        db_session.add(p)
        db_session.commit()

        result = get_user_sede_id(db_session, p.id)
        assert result is None

    def test_nonexistent_user(self, db_session):
        result = get_user_sede_id(db_session, uuid.uuid4())
        assert result is None


# ── _resolve_anchor_sede ──────────────────────────────────────────────────


class TestResolveAnchorSede:
    def test_caso_id(self, db_session):
        from backend.models_crm_pipeline import CanalOrigenEnum, CasoCRM, EtapaPipeline, PipelineCRM, TipoPipelineEnum

        sede = models.Sede(id=uuid.uuid4(), nombre="Sede", ciudad="City")
        db_session.add(sede)
        db_session.commit()
        p = models.Persona(id=uuid.uuid4(), first_name="Caso", last_name="Owner")
        db_session.add(p)
        db_session.commit()
        pipe = PipelineCRM(id=uuid.uuid4(), sede_id=sede.id, nombre="P", tipo=TipoPipelineEnum.CONSEJERIA)
        db_session.add(pipe)
        db_session.commit()
        stage = EtapaPipeline(id=uuid.uuid4(), pipeline_id=pipe.id, nombre="E1", orden=1)
        db_session.add(stage)
        db_session.commit()
        caso = CasoCRM(
            id=uuid.uuid4(), persona_id=p.id, sede_id=sede.id, pipeline_id=pipe.id,
            etapa_actual_id=stage.id, titulo_caso="Test", origen_canal=CanalOrigenEnum.EVANGELISMO,
        )
        db_session.add(caso)
        db_session.commit()

        result = _resolve_anchor_sede(db_session, "caso_id", caso.id)
        assert result == sede.id

    def test_persona_id(self, db_session):
        sede = models.Sede(id=uuid.uuid4(), nombre="Sede", ciudad="City")
        db_session.add(sede)
        db_session.commit()
        p = models.Persona(id=uuid.uuid4(), first_name="Anchor", last_name="Test", sede_id=sede.id)
        db_session.add(p)
        db_session.commit()

        result = _resolve_anchor_sede(db_session, "persona_id", p.id)
        assert result == sede.id

    def test_asignado_a_id(self, db_session):
        sede = models.Sede(id=uuid.uuid4(), nombre="Sede", ciudad="City")
        db_session.add(sede)
        db_session.commit()
        p = models.Persona(id=uuid.uuid4(), first_name="Assign", last_name="Test", sede_id=sede.id)
        db_session.add(p)
        db_session.commit()

        result = _resolve_anchor_sede(db_session, "asignado_a_id", p.id)
        assert result == sede.id

    def test_none_value(self, db_session):
        result = _resolve_anchor_sede(db_session, "caso_id", None)
        assert result is None

    def test_unknown_anchor(self, db_session):
        result = _resolve_anchor_sede(db_session, "unknown_field", uuid.uuid4())
        assert result is None

    def test_nonexistent_target(self, db_session):
        result = _resolve_anchor_sede(db_session, "persona_id", uuid.uuid4())
        assert result is None


# ── _get_live_column_names / schema introspection ─────────────────────────


class TestGetLiveColumnNames:
    def test_known_table(self, db_session):
        names = _get_live_column_names(db_session, "personas")
        assert isinstance(names, set)
        assert len(names) > 0
        assert "id" in names

    def test_cache_hit(self, db_session):
        first = _get_live_column_names(db_session, "personas")
        second = _get_live_column_names(db_session, "personas")
        assert first == second

    def test_unknown_table(self, db_session):
        names = _get_live_column_names(db_session, "nonexistent_table_xyz")
        assert names == set()

    def test_persona_live_column_names(self, db_session):
        names = _persona_live_column_names(db_session)
        assert isinstance(names, set)
        assert len(names) > 0


# ── Query builders ────────────────────────────────────────────────────────


class TestPersonaQuery:
    def test_basic_query(self, db_session):
        p = models.Persona(id=uuid.uuid4(), first_name="Query", last_name="Person")
        db_session.add(p)
        db_session.commit()

        q = persona_query(db_session)
        assert q is not None
        results = q.all()
        assert any(r.id == p.id for r in results)


class TestCaseQuery:
    def test_basic_query(self, db_session):
        from backend.models_crm_pipeline import CanalOrigenEnum, CasoCRM, EtapaPipeline, PipelineCRM, TipoPipelineEnum

        sede = models.Sede(id=uuid.uuid4(), nombre="Sede", ciudad="City")
        db_session.add(sede)
        db_session.commit()
        p = models.Persona(id=uuid.uuid4(), first_name="Case", last_name="Owner")
        db_session.add(p)
        db_session.commit()
        pipe = PipelineCRM(id=uuid.uuid4(), sede_id=sede.id, nombre="P", tipo=TipoPipelineEnum.CONSEJERIA)
        db_session.add(pipe)
        db_session.commit()
        stage = EtapaPipeline(id=uuid.uuid4(), pipeline_id=pipe.id, nombre="E1", orden=1)
        db_session.add(stage)
        db_session.commit()
        caso = CasoCRM(
            id=uuid.uuid4(), persona_id=p.id, sede_id=sede.id, pipeline_id=pipe.id,
            etapa_actual_id=stage.id, titulo_caso="Case Query", origen_canal=CanalOrigenEnum.EVANGELISMO,
        )
        db_session.add(caso)
        db_session.commit()

        q = case_query(db_session)
        assert q is not None
        results = q.all()
        assert any(r.id == caso.id for r in results)


# ── prepare_*_for_output ──────────────────────────────────────────────────


class TestPreparePersonaForOutput:
    def test_basic(self, db_session):
        p = models.Persona(id=uuid.uuid4(), first_name="Prep", last_name="Person")
        db_session.add(p)
        db_session.commit()

        result = prepare_persona_for_output(db_session, p)
        assert result.first_name == "Prep"
        assert result.last_name == "Person"


class TestPrepareCaseForOutput:
    def test_basic(self, db_session):
        from backend.models_crm_pipeline import CanalOrigenEnum, CasoCRM, EtapaPipeline, PipelineCRM, TipoPipelineEnum

        sede = models.Sede(id=uuid.uuid4(), nombre="Sede", ciudad="City")
        db_session.add(sede)
        db_session.commit()
        p = models.Persona(id=uuid.uuid4(), first_name="Prep", last_name="Case")
        db_session.add(p)
        db_session.commit()
        pipe = PipelineCRM(id=uuid.uuid4(), sede_id=sede.id, nombre="P", tipo=TipoPipelineEnum.CONSEJERIA)
        db_session.add(pipe)
        db_session.commit()
        stage = EtapaPipeline(id=uuid.uuid4(), pipeline_id=pipe.id, nombre="E1", orden=1)
        db_session.add(stage)
        db_session.commit()
        caso = CasoCRM(
            id=uuid.uuid4(), persona_id=p.id, sede_id=sede.id, pipeline_id=pipe.id,
            etapa_actual_id=stage.id, titulo_caso="Prep Case", origen_canal=CanalOrigenEnum.EVANGELISMO,
        )
        db_session.add(caso)
        db_session.commit()

        result = prepare_case_for_output(db_session, caso)
        assert result.id == caso.id
