"""Direct unit tests for `backend.crud.crm_.support` + `tasks` + `volunteers` (QC-18 módulo G).

QC-18 closure (errorescrm.md): all three modules had 0 direct tests.
  * support.py (5 funcs): SupportTicket CRUD with soft-delete (QC-06 closure
    ensured the model has `deleted_at`; reads now filter it).
  * tasks.py (4 funcs): TareaCRM CRUD with Axioma-3 defense-in-depth scope
    re-check (CREATE pre-flush + UPDATE pre-mutation) and audit-log
    persistence (Axioma 1).
  * volunteers.py (5 funcs): VolunteerShift CRUD. Soft-delete on reads is
    now consistent with the rest of the CRM CRUD.

Posture mirrors `tests/test_crm_crud_personas.py`: SQLite in-memory via
`db_session`, direct row inserts, no HTTP layer. We exercise:
  * Soft-delete (deleted_at) on support + tasks + volunteers.
  * Defense-in-depth scope re-check on create_crm_task: cross-sede persona
    anchor → 404 pre-add.
  * create_crm_task persists an audit log record (Axioma 1).
  * update_crm_task only emits an audit log entry when there are REAL changes.
"""

from __future__ import annotations

import datetime as dt
import uuid as _uuid
from typing import Optional

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend import models, schemas
from backend.crud.crm_ import support as crud_support
from backend.crud.crm_ import tasks as crud_tasks
from backend.crud.crm_ import volunteers as crud_volunteers
from backend.schemas.crm.base import CrmTaskPriority, CrmTaskStatus

# ─── Fixtures local ────────────────────────────────────────────────────────────


def _seed_sede(db: Session, name: str = "Sede QC-18.G") -> models.Sede:
    sede = models.Sede(id=_uuid.uuid4(), nombre=name, ciudad="QC18 City", es_activa=True)
    db.add(sede)
    db.flush()
    return sede


def _seed_persona(db: Session, sede_id: _uuid.UUID, first: str = "P") -> models.Persona:
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


# ─── support.py ──────────────────────────────────────────────────────────────────


def _seed_support_ticket(
    db: Session,
    *,
    user_id: _uuid.UUID,
    subject: str = "S",
    status: str = "ABIERTO",
    deleted_at=None,
) -> models.SupportTicket:
    t = models.SupportTicket(
        id=_uuid.uuid4(),
        user_id=user_id,
        subject=subject,
        description="d",
        status=status,
    )
    if deleted_at is not None:
        t.deleted_at = deleted_at
    db.add(t)
    db.flush()
    return t


def test_get_support_ticket_returns_none_for_missing(db_session):
    assert crud_support.get_support_ticket(db_session, str(_uuid.uuid4())) is None


def test_get_support_ticket_excludes_soft_deleted(db_session):
    sede = _seed_sede(db_session)
    p = _seed_persona(db_session, sede_id=sede.id)
    t = _seed_support_ticket(db_session, user_id=p.id, deleted_at=crud_support._utcnow())
    _commit(db_session)
    assert crud_support.get_support_ticket(db_session, str(t.id)) is None


def test_get_support_tickets_excludes_soft_deleted(db_session):
    """QC-06 closure guard: list filters `deleted_at IS NULL`."""
    sede = _seed_sede(db_session)
    p = _seed_persona(db_session, sede_id=sede.id)
    t_live = _seed_support_ticket(db_session, user_id=p.id)
    t_dead = _seed_support_ticket(db_session, user_id=p.id, deleted_at=crud_support._utcnow())
    _commit(db_session)
    ids = {t.id for t in crud_support.get_support_tickets(db_session)}
    assert t_live.id in ids and t_dead.id not in ids


def test_get_support_tickets_filter_by_user_id(db_session):
    sede = _seed_sede(db_session)
    p_a = _seed_persona(db_session, sede_id=sede.id, first="A")
    p_b = _seed_persona(db_session, sede_id=sede.id, first="B")
    t_a = _seed_support_ticket(db_session, user_id=p_a.id)
    t_b = _seed_support_ticket(db_session, user_id=p_b.id)
    _commit(db_session)
    ids = {t.id for t in crud_support.get_support_tickets(db_session, user_id=p_a.id)}
    assert t_a.id in ids and t_b.id not in ids


def test_create_support_ticket_persists_fields(db_session):
    sede = _seed_sede(db_session)
    p = _seed_persona(db_session, sede_id=sede.id)
    _commit(db_session)
    payload = schemas.SupportTicketCreate(
        subject="Broken",
        description="help please",
        user_id=p.id,
    )
    row = crud_support.create_support_ticket(db_session, payload)
    assert row.id is not None
    assert row.subject == "Broken"
    assert row.user_id == p.id
    assert (
        row.status == "open"
    )  # default (SupportTicketCreate does not wire a status; model default is lowercase 'open')
    assert row.deleted_at is None


def test_update_support_ticket_returns_none_for_missing(db_session):
    assert crud_support.update_support_ticket(db_session, str(_uuid.uuid4()), "X") is None


def test_update_support_ticket_updates_status(db_session):
    sede = _seed_sede(db_session)
    p = _seed_persona(db_session, sede_id=sede.id)
    t = _seed_support_ticket(db_session, user_id=p.id, status="ABIERTO")
    _commit(db_session)
    out = crud_support.update_support_ticket(db_session, str(t.id), "CERRADO")
    assert out.status == "CERRADO"


def test_update_support_ticket_skips_soft_deleted(db_session):
    """QC-06 defense-in-depth: cannot un-update a soft-deleted ticket."""
    sede = _seed_sede(db_session)
    p = _seed_persona(db_session, sede_id=sede.id)
    t = _seed_support_ticket(db_session, user_id=p.id, deleted_at=crud_support._utcnow())
    _commit(db_session)
    assert crud_support.update_support_ticket(db_session, str(t.id), "CERRADO") is None


def test_delete_support_ticket_soft_deletes_and_returns_true(db_session):
    sede = _seed_sede(db_session)
    p = _seed_persona(db_session, sede_id=sede.id)
    t = _seed_support_ticket(db_session, user_id=p.id)
    _commit(db_session)
    assert crud_support.delete_support_ticket(db_session, str(t.id)) is True
    db_session.expire_all()
    assert crud_support.get_support_ticket(db_session, str(t.id)) is None


def test_delete_support_ticket_returns_false_for_missing(db_session):
    assert crud_support.delete_support_ticket(db_session, str(_uuid.uuid4())) is False


# ─── tasks.py ──────────────────────────────────────────────────────────────────


def _seed_tarea(
    db: Session,
    *,
    persona: Optional[models.Persona] = None,
    deleted_at=None,
    title: str = "T",
    estado: str = "PENDIENTE",
    caso_id=None,
    assignee=None,
) -> models.TareaCRM:
    t = models.TareaCRM(
        id=_uuid.uuid4(),
        persona_id=persona.id if persona else None,
        caso_id=caso_id,
        asignado_a_id=assignee.id if assignee else None,
        titulo=title,
        estado=estado,
        prioridad="MEDIA",
    )
    if deleted_at is not None:
        t.deleted_at = deleted_at
    db.add(t)
    db.flush()
    return t


def test_get_crm_tasks_filters_by_persona(db_session):
    sede = _seed_sede(db_session)
    p = _seed_persona(db_session, sede_id=sede.id)
    p_other = _seed_persona(db_session, sede_id=sede.id, first="Other")
    t = _seed_tarea(db_session, persona=p)
    t_other = _seed_tarea(db_session, persona=p_other)
    _commit(db_session)
    ids = {t.id for t in crud_tasks.get_crm_tasks(db_session, persona_id=p.id)}
    assert t.id in ids and t_other.id not in ids


def test_get_crm_tasks_filters_by_assignee(db_session):
    sede = _seed_sede(db_session)
    p = _seed_persona(db_session, sede_id=sede.id)
    p_other = _seed_persona(db_session, sede_id=sede.id, first="Other")
    t = _seed_tarea(db_session, persona=p, assignee=p)
    t_other = _seed_tarea(db_session, persona=p, assignee=p_other)
    _commit(db_session)
    ids = {t.id for t in crud_tasks.get_crm_tasks(db_session, assignee_persona_id=p.id)}
    assert t.id in ids
    assert t_other.id not in ids


def test_get_crm_tasks_excludes_soft_deleted(db_session):
    sede = _seed_sede(db_session)
    p = _seed_persona(db_session, sede_id=sede.id)
    t_live = _seed_tarea(db_session, persona=p)
    t_dead = _seed_tarea(db_session, persona=p, deleted_at=crud_tasks._utcnow())
    _commit(db_session)
    ids = {t.id for t in crud_tasks.get_crm_tasks(db_session, persona_id=p.id)}
    assert t_live.id in ids and t_dead.id not in ids


def test_create_crm_task_rejects_cross_sede_persona(db_session):
    """Axioma-3 defense-in-depth: actor in sede_a cannot create a task with
    a persona_id belonging to sede_b."""
    sede_a = _seed_sede(db_session, name="A")
    sede_b = _seed_sede(db_session, name="B")
    p_actor = _seed_persona(db_session, sede_id=sede_a.id, first="Actor")
    p_target = _seed_persona(db_session, sede_id=sede_b.id, first="TargetCross")
    _commit(db_session)

    payload = schemas.CrmTaskCreate(
        title="T",
        description="d",
        persona_id=p_target.id,
        assignee_id=None,
        category="FOLLOWUP",
        due_date=None,
        status=CrmTaskStatus.pending,
        priority=CrmTaskPriority.medium,
        completed_at=None,
    )
    with pytest.raises(HTTPException) as exc:
        crud_tasks.create_crm_task(db_session, payload, actor_user_id=p_actor.id)
    assert exc.value.status_code == 404
    # No row added
    assert db_session.query(models.TareaCRM).filter_by(persona_id=p_target.id).count() == 0


def test_create_crm_task_same_sede_succeeds_and_persists_audit_log(db_session):
    """Happy path + Axioma 1 (audit log): a CREATE persists a LogAuditoria row."""
    from backend.models_evangelism import LogAuditoria

    sede = _seed_sede(db_session)
    p_actor = _seed_persona(db_session, sede_id=sede.id, first="Actor")
    p_target = _seed_persona(db_session, sede_id=sede.id, first="Target")
    _commit(db_session)

    payload = schemas.CrmTaskCreate(
        title="T",
        description="d",
        persona_id=p_target.id,
        assignee_id=None,
        category="FOLLOWUP",
        due_date=None,
        status=CrmTaskStatus.pending,
        priority=CrmTaskPriority.medium,
        completed_at=None,
    )
    row = crud_tasks.create_crm_task(db_session, payload, actor_user_id=p_actor.id)
    assert row.id is not None
    assert row.persona_id == p_target.id

    # Audit log persisted
    log = db_session.query(LogAuditoria).filter_by(tabla_afectada="crm_tareas", accion="CREATE").first()
    assert log is not None, "create_crm_task did not persist an audit log (Axioma 1 violation)"
    assert log.registro_id == str(row.id)


def test_create_crm_task_actor_without_sede_bypasses_scope_check(db_session):
    """Actor persona without sede_id (superadmin-style) → bypass scope re-check.
    `_actor_sede_or_none` returns None for such an actor → check returns early."""
    sede = _seed_sede(db_session)
    # Persona del actor SIN sede assignment
    p_actor = models.Persona(
        id=_uuid.uuid4(),
        first_name="Super",
        last_name="Admin",
        estado_vital="ACTIVO",
        email=f"super{_uuid.uuid4().hex[:6]}@example.com",
        sede_id=None,
    )
    db_session.add(p_actor)
    p_target = _seed_persona(db_session, sede_id=sede.id, first="Target")
    _commit(db_session)

    payload = schemas.CrmTaskCreate(
        title="T",
        description="d",
        persona_id=p_target.id,
        assignee_id=None,
        category="FOLLOWUP",
        due_date=None,
        status=CrmTaskStatus.pending,
        priority=CrmTaskPriority.medium,
        completed_at=None,
    )
    row = crud_tasks.create_crm_task(db_session, payload, actor_user_id=p_actor.id)
    assert row.id is not None


def test_update_crm_task_returns_none_for_missing(db_session):
    sede = _seed_sede(db_session)
    p = _seed_persona(db_session, sede_id=sede.id)
    _commit(db_session)
    out = crud_tasks.update_crm_task(
        db_session,
        _uuid.uuid4(),
        schemas.CrmTaskUpdate(status=CrmTaskStatus.cancelled),
        actor_user_id=p.id,
    )
    assert out is None


def test_update_crm_task_skips_soft_deleted(db_session):
    sede = _seed_sede(db_session)
    p = _seed_persona(db_session, sede_id=sede.id)
    t = _seed_tarea(db_session, persona=p, deleted_at=crud_tasks._utcnow())
    _commit(db_session)
    out = crud_tasks.update_crm_task(
        db_session,
        t.id,
        schemas.CrmTaskUpdate(status=CrmTaskStatus.cancelled),
        actor_user_id=p.id,
    )
    assert out is None


def test_update_crm_task_with_real_changes_emits_audit_log(db_session):
    from backend.models_evangelism import LogAuditoria

    sede = _seed_sede(db_session)
    p_actor = _seed_persona(db_session, sede_id=sede.id, first="Actor")
    p_target = _seed_persona(db_session, sede_id=sede.id, first="Target")
    t = _seed_tarea(db_session, persona=p_target, title="Orig")
    _commit(db_session)

    crud_tasks.update_crm_task(
        db_session,
        t.id,
        schemas.CrmTaskUpdate(title="Changed"),
        actor_user_id=p_actor.id,
    )
    logs = db_session.query(LogAuditoria).filter_by(tabla_afectada="crm_tareas", accion="UPDATE").all()
    assert any(str(t.id) == log.registro_id for log in logs), "no UPDATE audit log persisted for real changes"


def test_update_crm_task_idempotent_no_changes_skips_audit_log(db_session):
    """Axioma 1 noise-minimization: when no real changes occur, no audit log."""
    from backend.models_evangelism import LogAuditoria

    sede = _seed_sede(db_session)
    p_actor = _seed_persona(db_session, sede_id=sede.id, first="Actor")
    p_target = _seed_persona(db_session, sede_id=sede.id, first="Target")
    t = _seed_tarea(db_session, persona=p_target, title="Same Title")
    _commit(db_session)

    # pass the SAME title — _values_equivalent should detect no real change
    crud_tasks.update_crm_task(
        db_session,
        t.id,
        schemas.CrmTaskUpdate(title="Same Title"),
        actor_user_id=p_actor.id,
    )
    logs = (
        db_session.query(LogAuditoria)
        .filter_by(
            tabla_afectada="crm_tareas",
            accion="UPDATE",
            registro_id=str(t.id),
        )
        .all()
    )
    assert len(logs) == 0, f"noise-minimization broken; got {len(logs)} UPDATE log(s) for no-op change"


def test_delete_crm_task_soft_deletes_and_returns_true(db_session):
    sede = _seed_sede(db_session)
    p = _seed_persona(db_session, sede_id=sede.id)
    t = _seed_tarea(db_session, persona=p)
    _commit(db_session)
    assert crud_tasks.delete_crm_task(db_session, t.id) is True
    db_session.expire_all()
    assert crud_tasks.get_crm_tasks(db_session, persona_id=p.id) == []


def test_delete_crm_task_returns_false_for_missing(db_session):
    assert crud_tasks.delete_crm_task(db_session, _uuid.uuid4()) is False


# ─── volunteers.py ──────────────────────────────────────────────────────────────


def _seed_shift(
    db: Session,
    *,
    persona: models.Persona,
    role_name: str = "Greeter",
    status: str = "PROGRAMADO",
    deleted_at=None,
) -> models.VolunteerShift:
    import datetime as dt

    s = models.VolunteerShift(
        id=_uuid.uuid4(),
        persona_id=persona.id,
        role_name=role_name,
        team_name="Team A",
        shift_start=dt.datetime(2026, 7, 1, 9, 0, tzinfo=dt.timezone.utc),
        shift_end=dt.datetime(2026, 7, 1, 11, 0, tzinfo=dt.timezone.utc),
        status=status,
    )
    if deleted_at is not None:
        s.deleted_at = deleted_at
    db.add(s)
    db.flush()
    return s


def test_get_volunteer_shifts_filter_by_persona(db_session):
    sede = _seed_sede(db_session)
    p = _seed_persona(db_session, sede_id=sede.id)
    p_other = _seed_persona(db_session, sede_id=sede.id, first="Other")
    s = _seed_shift(db_session, persona=p)
    s_other = _seed_shift(db_session, persona=p_other)
    _commit(db_session)
    ids = {x.id for x in crud_volunteers.get_volunteer_shifts(db_session, persona_id=str(p.id))}
    assert s.id in ids and s_other.id not in ids


def test_get_volunteer_shifts_returns_all_when_no_persona(db_session):
    sede = _seed_sede(db_session)
    p = _seed_persona(db_session, sede_id=sede.id)
    s = _seed_shift(db_session, persona=p)
    _commit(db_session)
    ids = {x.id for x in crud_volunteers.get_volunteer_shifts(db_session)}
    assert s.id in ids


def test_get_volunteer_shifts_orders_by_shift_start_asc(db_session):
    """Contract: order by shift_start asc."""
    sede = _seed_sede(db_session)
    p = _seed_persona(db_session, sede_id=sede.id)
    s_late = _seed_shift(db_session, persona=p)
    s_late.shift_start = dt.datetime(2026, 8, 1, 9, 0, tzinfo=dt.timezone.utc)
    s_early = _seed_shift(db_session, persona=p)
    s_early.shift_start = dt.datetime(2026, 6, 1, 9, 0, tzinfo=dt.timezone.utc)
    _commit(db_session)

    starts = [x.shift_start for x in crud_volunteers.get_volunteer_shifts(db_session, persona_id=str(p.id))]
    # compare by .date() since SQLite tz-aware-as-naive invariant may surface
    assert [s.date() for s in starts] == sorted([s.date() for s in starts])


def test_get_volunteer_shift_returns_none_for_missing(db_session):
    assert crud_volunteers.get_volunteer_shift(db_session, _uuid.uuid4()) is None


def test_create_volunteer_shift_persists_fields(db_session):
    sede = _seed_sede(db_session)
    p = _seed_persona(db_session, sede_id=sede.id)
    _commit(db_session)
    payload = schemas.VolunteerShiftCreate(
        persona_id=p.id,
        role_name="Usher",
        team_name="TeamB",
        shift_start="2026-07-01T09:00",
        shift_end="2026-07-01T11:00",
        status="PROGRAMADO",
        notes=None,
    )
    row = crud_volunteers.create_volunteer_shift(db_session, payload)
    assert row.id is not None
    assert row.role_name == "Usher"
    assert row.team_name == "TeamB"


def test_update_volunteer_shift_returns_none_for_missing(db_session):
    assert (
        crud_volunteers.update_volunteer_shift(db_session, _uuid.uuid4(), schemas.VolunteerShiftUpdate(status="X"))
        is None
    )


def test_update_volunteer_shift_updates_provided_fields(db_session):
    sede = _seed_sede(db_session)
    p = _seed_persona(db_session, sede_id=sede.id)
    s = _seed_shift(db_session, persona=p, status="PROGRAMADO")
    _commit(db_session)
    out = crud_volunteers.update_volunteer_shift(db_session, s.id, schemas.VolunteerShiftUpdate(status="COMPLETADO"))
    assert out.status == "COMPLETADO"


def test_delete_volunteer_shift_soft_deletes_and_returns_true(db_session):
    sede = _seed_sede(db_session)
    p = _seed_persona(db_session, sede_id=sede.id)
    s = _seed_shift(db_session, persona=p)
    _commit(db_session)
    assert crud_volunteers.delete_volunteer_shift(db_session, s.id) is True
    db_session.expire_all()
    row = db_session.query(models.VolunteerShift).filter_by(id=s.id).first()
    assert row is not None and row.deleted_at is not None


def test_delete_volunteer_shift_returns_false_for_missing(db_session):
    assert crud_volunteers.delete_volunteer_shift(db_session, _uuid.uuid4()) is False


def test_get_volunteer_shifts_excludes_soft_deleted(db_session):
    """Soft-delete guard: get_volunteer_shifts and get_volunteer_shift
    now filter `deleted_at IS NULL`, consistent with the rest of the
    CRM CRUD. The previous A-05 LATENTE asymmetry has been closed.
    """
    sede = _seed_sede(db_session)
    p = _seed_persona(db_session, sede_id=sede.id)
    s_live = _seed_shift(db_session, persona=p)
    s_dead = _seed_shift(db_session, persona=p, deleted_at=crud_volunteers._utcnow())
    _commit(db_session)

    out_by_persona = crud_volunteers.get_volunteer_shifts(db_session, persona_id=str(p.id))
    by_id = crud_volunteers.get_volunteer_shift(db_session, s_dead.id)
    assert s_live.id in {x.id for x in out_by_persona}
    assert s_dead.id not in {x.id for x in out_by_persona}
    assert by_id is None
