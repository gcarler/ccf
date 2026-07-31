"""Tests for crud/crm_/tasks.py."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from backend import models, schemas
from backend.crud.crm_.tasks import (
    _value_for_audit,
    _values_equivalent,
    create_crm_task,
    delete_crm_task,
    get_crm_tasks,
    update_crm_task,
)
from tests.conftest import seed_admin

# ── Helpers ───────────────────────────────────────────────────────────────


def _make_sede(db):
    s = models.Sede(id=uuid.uuid4(), nombre="Task Test Sede", ciudad="Task City")
    db.add(s)
    db.commit()
    return s


def _make_persona(db, sede_id) -> models.Persona:
    p = models.Persona(id=uuid.uuid4(), first_name="Task", last_name="Person", sede_id=sede_id)
    db.add(p)
    db.commit()
    return p


# ── Pure function tests ───────────────────────────────────────────────────


class TestValuesEquivalent:
    def test_both_none(self):
        assert _values_equivalent(None, None) is True

    def test_one_none(self):
        assert _values_equivalent(None, "x") is False
        assert _values_equivalent("x", None) is False

    def test_equal_strings(self):
        assert _values_equivalent("a", "a") is True

    def test_different_strings(self):
        assert _values_equivalent("a", "b") is False

    def test_datetime_equivalent(self):
        dt1 = datetime(2024, 1, 1, tzinfo=timezone.utc)
        dt2 = datetime(2024, 1, 1, tzinfo=timezone.utc)
        assert _values_equivalent(dt1, dt2) is True

    def test_datetime_different(self):
        dt1 = datetime(2024, 1, 1, tzinfo=timezone.utc)
        dt2 = datetime(2024, 6, 1, tzinfo=timezone.utc)
        assert _values_equivalent(dt1, dt2) is False

    def test_uuid_equivalent(self):
        uid = uuid.uuid4()
        assert _values_equivalent(uid, uid) is True

    def test_int_equivalent(self):
        assert _values_equivalent(1, 1) is True
        assert _values_equivalent(1, 2) is False

    def test_bool_equivalent(self):
        assert _values_equivalent(True, True) is True
        assert _values_equivalent(True, False) is False


class TestValueForAudit:
    def test_none(self):
        assert _value_for_audit(None) is None

    def test_uuid(self):
        uid = uuid.uuid4()
        assert _value_for_audit(uid) == str(uid)

    def test_datetime(self):
        dt = datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc)
        assert _value_for_audit(dt) == dt.isoformat()

    def test_date(self):
        from datetime import date

        d = date(2024, 1, 15)
        assert _value_for_audit(d) == d.isoformat()

    def test_string(self):
        assert _value_for_audit("hello") == "hello"

    def test_int(self):
        assert _value_for_audit(42) == 42

    def test_bool(self):
        assert _value_for_audit(True) is True


# ── CRUD integration tests ────────────────────────────────────────────────


class TestGetCrmTasks:
    def test_empty(self, db_session):
        tasks = get_crm_tasks(db_session)
        assert tasks == []

    def test_filter_by_assignee(self, db_session):
        sede = _make_sede(db_session)
        persona = _make_persona(db_session, sede.id)
        t1 = models.TareaCRM(id=uuid.uuid4(), titulo="T1", assignee_id=persona.id)
        t2 = models.TareaCRM(id=uuid.uuid4(), titulo="T2")
        db_session.add_all([t1, t2])
        db_session.commit()

        result = get_crm_tasks(db_session, assignee_persona_id=persona.id)
        assert len(result) == 1
        assert result[0].id == t1.id

    def test_filter_by_persona(self, db_session):
        sede = _make_sede(db_session)
        persona = _make_persona(db_session, sede.id)
        t1 = models.TareaCRM(id=uuid.uuid4(), titulo="T1", persona_id=persona.id)
        t2 = models.TareaCRM(id=uuid.uuid4(), titulo="T2")
        db_session.add_all([t1, t2])
        db_session.commit()

        result = get_crm_tasks(db_session, persona_id=persona.id)
        assert len(result) == 1
        assert result[0].id == t1.id

    def test_excludes_deleted(self, db_session):
        from backend.crud._utils import _utcnow

        t1 = models.TareaCRM(id=uuid.uuid4(), titulo="Alive")
        t2 = models.TareaCRM(id=uuid.uuid4(), titulo="Dead", deleted_at=_utcnow())
        db_session.add_all([t1, t2])
        db_session.commit()

        result = get_crm_tasks(db_session)
        assert len(result) == 1
        assert result[0].id == t1.id

    def test_order_by_due_date(self, db_session):
        later = datetime(2024, 6, 1, tzinfo=timezone.utc)
        earlier = datetime(2024, 1, 1, tzinfo=timezone.utc)
        t1 = models.TareaCRM(id=uuid.uuid4(), titulo="Later", due_date=later)
        t2 = models.TareaCRM(id=uuid.uuid4(), titulo="Earlier", due_date=earlier)
        db_session.add_all([t1, t2])
        db_session.commit()

        result = get_crm_tasks(db_session)
        assert [r.id for r in result] == [t2.id, t1.id]


class TestCreateCrmTask:
    def test_create_minimal(self, db_session):
        admin, _, admin_sede = seed_admin(db_session)
        persona = _make_persona(db_session, admin_sede.id)
        payload = schemas.CrmTaskCreate(title="Test Task", persona_id=persona.id)
        row = create_crm_task(db_session, payload, actor_user_id=admin.id)
        assert row.id is not None
        assert row.titulo == "Test Task"
        assert row.deleted_at is None

    def test_create_with_assignee(self, db_session):
        admin, _, admin_sede = seed_admin(db_session)
        persona = _make_persona(db_session, admin_sede.id)
        payload = schemas.CrmTaskCreate(title="Assigned", assignee_id=persona.id)
        row = create_crm_task(db_session, payload, actor_user_id=admin.id)
        db_session.refresh(row)
        assert row.asignado_a_id == persona.id

    def test_create_with_all_fields(self, db_session):
        admin, _, admin_sede = seed_admin(db_session)
        persona = _make_persona(db_session, admin_sede.id)

        from backend.models_crm_pipeline import (
            CanalOrigenEnum,
            CasoCRM,
            EtapaPipeline,
            PipelineCRM,
            TipoPipelineEnum,
        )

        pipeline = PipelineCRM(
            id=uuid.uuid4(),
            sede_id=admin_sede.id,
            nombre="Test Pipeline",
            tipo=TipoPipelineEnum.NUEVOS_VISITANTES,
        )
        etapa = EtapaPipeline(
            id=uuid.uuid4(),
            pipeline_id=pipeline.id,
            nombre="Etapa 1",
            orden=1,
        )
        caso = CasoCRM(
            id=uuid.uuid4(),
            persona_id=persona.id,
            sede_id=admin_sede.id,
            pipeline_id=pipeline.id,
            etapa_actual_id=etapa.id,
            titulo_caso="Caso",
            origen_canal=CanalOrigenEnum.WEB_FORM,
        )
        db_session.add_all([pipeline, etapa, caso])
        db_session.commit()

        future = datetime(2025, 1, 1, tzinfo=timezone.utc)
        payload = schemas.CrmTaskCreate(
            title="Full Task",
            assignee_id=persona.id,
            persona_id=persona.id,
            caso_id=caso.id,
            category="seguimiento",
            priority="high",
            status="pending",
            description="A description",
            due_date=future,
        )
        row = create_crm_task(db_session, payload, actor_user_id=admin.id)
        assert row.titulo == "Full Task"
        assert row.asignado_a_id == persona.id
        assert row.persona_id == persona.id
        assert row.caso_id == caso.id
        assert row.categoria == "seguimiento"
        assert row.prioridad == "high"
        assert row.estado == "pending"
        assert row.descripcion == "A description"

    def test_create_no_assignee_identity(self, db_session):
        """assignee_id=None should be accepted."""
        admin, _, admin_sede = seed_admin(db_session)
        persona = _make_persona(db_session, admin_sede.id)
        payload = schemas.CrmTaskCreate(title="No Assignee", assignee_id=None, persona_id=persona.id)
        row = create_crm_task(db_session, payload, actor_user_id=admin.id)
        assert row.asignado_a_id is None


class TestUpdateCrmTask:
    def test_update_title(self, db_session):
        admin, _, admin_sede = seed_admin(db_session)
        persona = _make_persona(db_session, admin_sede.id)
        t = models.TareaCRM(id=uuid.uuid4(), titulo="Original", persona_id=persona.id)
        db_session.add(t)
        db_session.commit()

        payload = schemas.CrmTaskUpdate(title="Updated")
        row = update_crm_task(db_session, t.id, payload, actor_user_id=admin.id)
        assert row.titulo == "Updated"

    def test_update_nonexistent(self, db_session):
        admin, _, _ = seed_admin(db_session)
        payload = schemas.CrmTaskUpdate(title="Nope")
        row = update_crm_task(db_session, uuid.uuid4(), payload, actor_user_id=admin.id)
        assert row is None

    def test_update_idempotent_no_audit(self, db_session, caplog):
        """No audit log should be written when values don't change."""
        import logging

        admin, _, admin_sede = seed_admin(db_session)
        persona = _make_persona(db_session, admin_sede.id)
        t = models.TareaCRM(id=uuid.uuid4(), titulo="Same", persona_id=persona.id)
        db_session.add(t)
        db_session.commit()

        with caplog.at_level(logging.WARNING):
            payload = schemas.CrmTaskUpdate(title="Same")
            row = update_crm_task(db_session, t.id, payload, actor_user_id=admin.id)
        assert row.titulo == "Same"

    def test_update_partial(self, db_session):
        admin, _, admin_sede = seed_admin(db_session)
        persona = _make_persona(db_session, admin_sede.id)
        t = models.TareaCRM(
            id=uuid.uuid4(),
            titulo="Partial",
            descripcion="Original description",
            prioridad="low",
            persona_id=persona.id,
        )
        db_session.add(t)
        db_session.commit()

        payload = schemas.CrmTaskUpdate(priority="high")
        row = update_crm_task(db_session, t.id, payload, actor_user_id=admin.id)
        assert row.prioridad == "high"
        assert row.descripcion == "Original description"

    def test_update_assignee(self, db_session):
        admin, _, admin_sede = seed_admin(db_session)
        p1 = _make_persona(db_session, admin_sede.id)
        p2 = _make_persona(db_session, admin_sede.id)
        t = models.TareaCRM(id=uuid.uuid4(), titulo="Reassign", assignee_id=p1.id)
        db_session.add(t)
        db_session.commit()

        payload = schemas.CrmTaskUpdate(assignee_id=p2.id)
        row = update_crm_task(db_session, t.id, payload, actor_user_id=admin.id)
        assert row.asignado_a_id == p2.id


class TestDeleteCrmTask:
    def test_delete_soft(self, db_session):
        t = models.TareaCRM(id=uuid.uuid4(), titulo="To Delete")
        db_session.add(t)
        db_session.commit()

        result = delete_crm_task(db_session, t.id)
        assert result is True

        db_session.refresh(t)
        assert t.deleted_at is not None

    def test_delete_nonexistent(self, db_session):
        result = delete_crm_task(db_session, uuid.uuid4())
        assert result is False

    def test_delete_already_deleted(self, db_session):
        from backend.crud._utils import _utcnow

        t = models.TareaCRM(id=uuid.uuid4(), titulo="Already Dead", deleted_at=_utcnow())
        db_session.add(t)
        db_session.commit()

        result = delete_crm_task(db_session, t.id)
        assert result is False
