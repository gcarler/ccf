"""Direct unit tests for `backend.crud.crm_.tasks`.

`tasks.py` is already extensively tested in `test_crm_crud_support_tasks_volunteers.py`
for Axioma-3 defense-in-depth and audit logging. This file provides a dedicated,
lightweight suite focusing on the core CRUD contract of each public function
without duplicating the deep security tests.
"""
from __future__ import annotations

import uuid as _uuid

from sqlalchemy.orm import Session

from backend import models
from backend.crud.crm_ import tasks as crud_tasks
from backend.schemas.crm.base import CrmTaskCreate, CrmTaskPriority, CrmTaskStatus, CrmTaskUpdate


def _seed_sede(db: Session, name: str = "Sede Tasks") -> models.Sede:
    sede = models.Sede(id=_uuid.uuid4(), nombre=name, ciudad="Bogota", es_activa=True)
    db.add(sede)
    db.flush()
    return sede


def _seed_persona(db: Session, *, sede_id: _uuid.UUID, first: str = "P") -> models.Persona:
    p = models.Persona(
        id=_uuid.uuid4(),
        first_name=first,
        last_name="T",
        sede_id=sede_id,
        estado_vital="ACTIVO",
        email=f"{first.lower()}{_uuid.uuid4().hex[:6]}@example.com",
    )
    db.add(p)
    db.flush()
    return p


def _commit(db: Session) -> None:
    db.commit()


def test_get_crm_tasks_returns_empty_when_no_rows(db_session):
    assert crud_tasks.get_crm_tasks(db_session) == []


def test_get_crm_tasks_filters_by_assignee(db_session):
    sede = _seed_sede(db_session)
    p = _seed_persona(db_session, sede_id=sede.id)
    p_other = _seed_persona(db_session, sede_id=sede.id, first="Other")
    task = models.TareaCRM(
        id=_uuid.uuid4(),
        persona_id=p.id,
        asignado_a_id=p.id,
        titulo="T1",
        estado="pending",
        prioridad="medium",
    )
    task_other = models.TareaCRM(
        id=_uuid.uuid4(),
        persona_id=p_other.id,
        asignado_a_id=p_other.id,
        titulo="T2",
        estado="pending",
        prioridad="medium",
    )
    db_session.add_all([task, task_other])
    _commit(db_session)

    ids = {t.id for t in crud_tasks.get_crm_tasks(db_session, assignee_persona_id=p.id)}
    assert task.id in ids
    assert task_other.id not in ids


def test_create_crm_task_persists_fields(db_session):
    sede = _seed_sede(db_session)
    actor = _seed_persona(db_session, sede_id=sede.id, first="Actor")
    target = _seed_persona(db_session, sede_id=sede.id, first="Target")
    _commit(db_session)

    payload = CrmTaskCreate(
        title="Nueva tarea",
        description="desc",
        persona_id=target.id,
        assignee_id=None,
        category="FOLLOWUP",
        due_date=None,
        status=CrmTaskStatus.pending,
        priority=CrmTaskPriority.medium,
        completed_at=None,
    )
    row = crud_tasks.create_crm_task(db_session, payload, actor_user_id=actor.id)
    assert row.id is not None
    assert row.titulo == "Nueva tarea"
    assert row.persona_id == target.id
    assert row.estado == "pending"


def test_update_crm_task_changes_fields(db_session):
    sede = _seed_sede(db_session)
    actor = _seed_persona(db_session, sede_id=sede.id, first="Actor")
    target = _seed_persona(db_session, sede_id=sede.id, first="Target")
    task = models.TareaCRM(
        id=_uuid.uuid4(),
        persona_id=target.id,
        titulo="Old",
        estado="pending",
        prioridad="medium",
    )
    db_session.add(task)
    _commit(db_session)

    out = crud_tasks.update_crm_task(
        db_session,
        task.id,
        CrmTaskUpdate(title="New"),
        actor_user_id=actor.id,
    )
    assert out is not None
    assert out.titulo == "New"


def test_delete_crm_task_soft_deletes(db_session):
    sede = _seed_sede(db_session)
    target = _seed_persona(db_session, sede_id=sede.id, first="Target")
    task = models.TareaCRM(
        id=_uuid.uuid4(),
        persona_id=target.id,
        titulo="ToDelete",
        estado="pending",
        prioridad="medium",
    )
    db_session.add(task)
    _commit(db_session)

    assert crud_tasks.delete_crm_task(db_session, task.id) is True
    db_session.expire_all()
    assert crud_tasks.get_crm_tasks(db_session, persona_id=target.id) == []
