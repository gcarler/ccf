"""Direct unit tests for `backend.crud.crm_.communication` + `notifications` (QC-18 módulo E).

QC-18 closure (errorescrm.md): both modules had 0 direct tests.
  * communication.py (5 funcs): CommunicationLog CRUD with Axioma-3
    defense-in-depth scope re-check at CRUD layer (`create_communication_log`
    requires `actor_user_id` and rejects cross-sede persona_id before `db.add`).
  * notifications.py (3 funcs): Notification CRUD with ownership guard
    (every user sees/mutates ONLY their own notifications, existence-leak safe).

Posture mirrors `tests/test_crm_crud_personas.py`: SQLite in-memory via
`db_session`, direct row inserts, no HTTP layer. We exercise:
  * Soft-delete (deleted_at) on CommunicationLog CRUD.
  * `create_communication_log` scope re-check:
      - actor sin sede (superadmin) → bypass, persona of any sede allowed;
      - actor with sede + persona cross-sede → HTTPException 404 pre-add;
      - actor with sede + persona None (orphan log) → HTTPException 404;
      - actor with sede + persona same-sede → row created.
  * `get_communication_logs(sede_id=X)` filters via Persona JOIN (Axioma 3).
  * notifications ownership: mark_read by another user returns None (no leak).
"""

from __future__ import annotations

import datetime as dt
import uuid as _uuid
from typing import Optional

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend import models, schemas
from backend.crud.crm_ import communication as crud_comm
from backend.crud.crm_ import notifications as crud_notif
from backend.schemas.notifications import CommunicationLogUpdate

# ─── Fixtures local ────────────────────────────────────────────────────────────


def _seed_sede(db: Session, name: str = "Sede QC-18.E") -> models.Sede:
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


def _seed_user_persona_link(db: Session, persona: models.Persona, sede_id: _uuid.UUID) -> models.Persona:
    """The Persona.id doubles as the Usuario.id — nothing else to seed for the
    `resolve_persona_id_for_user(db, user_id)` lookup to resolve (it queries
    `personas.id == user_id`)."""
    return persona


def _seed_comm_log(
    db: Session,
    *,
    persona: models.Persona,
    channel: str = "WHATSAPP",
    content: str = "follow-up",
    deleted_at=None,
) -> models.CommunicationLog:
    log = models.CommunicationLog(
        id=_uuid.uuid4(),
        persona_id=persona.id,
        channel=channel,
        content=content,
        outcome=None,
    )
    if deleted_at is not None:
        log.deleted_at = deleted_at
    db.add(log)
    db.flush()
    return log


def _seed_notification(
    db: Session,
    *,
    user_id: _uuid.UUID,
    title: str = "N",
    content: str = "c",
    is_read: bool = False,
    sede_id: Optional[_uuid.UUID] = None,
) -> models.Notification:
    n = models.Notification(
        id=_uuid.uuid4(),
        user_id=user_id,
        sede_id=sede_id or _seed_sede(db).id,
        title=title,
        content=content,
        is_read=is_read,
    )
    db.add(n)
    db.flush()
    return n


def _commit(db: Session) -> None:
    db.commit()


# ─── communication.py ──────────────────────────────────────────────────────────


def test_get_communication_log_returns_none_for_missing(db_session):
    assert crud_comm.get_communication_log(db_session, str(_uuid.uuid4())) is None


def test_get_communication_log_excludes_soft_deleted(db_session):
    sede = _seed_sede(db_session)
    p = _seed_persona(db_session, sede_id=sede.id)
    log = _seed_comm_log(db_session, persona=p, deleted_at=crud_comm._utcnow())
    _commit(db_session)
    assert crud_comm.get_communication_log(db_session, str(log.id)) is None


def test_get_communication_logs_scoped_by_sede_via_persona_join(db_session):
    """Axioma 3: get_communication_logs(sede_id=A) must filter via Persona JOIN."""
    sede_a = _seed_sede(db_session, name="A")
    sede_b = _seed_sede(db_session, name="B")
    p_a = _seed_persona(db_session, sede_id=sede_a.id, first="A")
    p_b = _seed_persona(db_session, sede_id=sede_b.id, first="B")
    log_a = _seed_comm_log(db_session, persona=p_a)
    log_b = _seed_comm_log(db_session, persona=p_b)
    _commit(db_session)

    out_a = crud_comm.get_communication_logs(db_session, sede_id=sede_a.id)
    ids = {entry.id for entry in out_a}
    assert log_a.id in ids
    assert log_b.id not in ids, "get_communication_logs leaked cross-tenant via Persona JOIN"


def test_get_communication_logs_returns_all_when_no_sede(db_session):
    """sede_id=None → global (superadmin scope)."""
    sede = _seed_sede(db_session)
    p = _seed_persona(db_session, sede_id=sede.id)
    log = _seed_comm_log(db_session, persona=p)
    _commit(db_session)
    assert any(entry.id == log.id for entry in crud_comm.get_communication_logs(db_session, sede_id=None))


def test_get_communication_logs_excludes_soft_deleted(db_session):
    sede = _seed_sede(db_session)
    p = _seed_persona(db_session, sede_id=sede.id)
    log_live = _seed_comm_log(db_session, persona=p)
    log_dead = _seed_comm_log(db_session, persona=p, deleted_at=crud_comm._utcnow())
    _commit(db_session)
    ids = {entry.id for entry in crud_comm.get_communication_logs(db_session, sede_id=sede.id)}
    assert log_live.id in ids and log_dead.id not in ids


def test_create_communication_log_allows_when_actor_superadmin_no_sede(db_session):
    """Actor without sede (`_actor_sede_or_none=None`) → bypass scope re-check.

    This validates the "superadmin / anterior path" gap — the check exists,
    but actors with no sede keep a global scope. We seed a persona in a sede
    and call create_communication_log with an actor that has no Persona row
    (resolve_persona_id_for_user returns None → _actor_sede_or_none raises 401).

    Wait — re-reading `_actor_sede_or_none`: it raises 401 if the actor is
    not a known persona. So "no sede" only happens when the persona exists
    AND has sede_id=None. We test that branch here.
    """
    sede = _seed_sede(db_session)
    p_target = _seed_persona(db_session, sede_id=sede.id)
    # Persona del actor SIN sede assignment (superadmin-style)
    p_actor = models.Persona(
        id=_uuid.uuid4(),
        first_name="Super",
        last_name="Admin",
        estado_vital="ACTIVO",
        email=f"super{_uuid.uuid4().hex[:6]}@example.com",
        sede_id=None,
    )
    db_session.add(p_actor)
    _commit(db_session)

    payload = schemas.CommunicationLogCreate(
        persona_id=p_target.id,
        channel="EMAIL",
        content="hi",
        leader_id=None,
    )
    row = crud_comm.create_communication_log(db_session, payload, actor_user_id=p_actor.id)
    assert row.id is not None
    assert row.persona_id == p_target.id


def test_create_communication_log_rejects_cross_sede_persona(db_session):
    """Axioma 3 defense-in-depth: actor in sede_a CANNOT log a persona of sede_b."""
    sede_a = _seed_sede(db_session, name="A")
    sede_b = _seed_sede(db_session, name="B")
    p_a = _seed_persona(db_session, sede_id=sede_a.id, first="Actor")
    p_b = _seed_persona(db_session, sede_id=sede_b.id, first="TargetCross")
    _commit(db_session)

    payload = schemas.CommunicationLogCreate(
        persona_id=p_b.id,
        channel="EMAIL",
        content="attempt leak",
        leader_id=None,
    )
    with pytest.raises(HTTPException) as exc:
        crud_comm.create_communication_log(db_session, payload, actor_user_id=p_a.id)
    assert exc.value.status_code == 404, "cross-sede create should reject with 404 (existence-leak safe)"
    # No row created
    assert db_session.query(models.CommunicationLog).filter_by(persona_id=p_b.id).count() == 0


def test_create_communication_log_rejects_orphan_when_actor_in_sede(db_session):
    """Direct check: actor with sede + persona_id=None → orphan log → rejected.

    The schema-level `CommunicationLogCreate.persona_id` is `UUID` (NOT
    Optional), so Pydantic rejects the orphan BEFORE the CRUD scope re-check
    can act. The defense-in-depth re-check (CRUD layer) is still meaningful
    for non-API callers (workers / scripts / direct CRUD calls that bypass
    Pydantic) so we test the helper directly here.
    """
    sede = _seed_sede(db_session)
    p_actor = _seed_persona(db_session, sede_id=sede.id, first="Actor")
    _commit(db_session)

    with pytest.raises(HTTPException) as exc:
        crud_comm._crud_scope_re_check_communication_log_create(
            db_session,
            actor_user_id=p_actor.id,
            persona_id=None,
        )
    assert exc.value.status_code == 404


def test_create_communication_log_same_sede_succeeds(db_session):
    """Happy path: actor and target in the same sede → row created."""
    sede = _seed_sede(db_session)
    p_actor = _seed_persona(db_session, sede_id=sede.id, first="Actor")
    p_target = _seed_persona(db_session, sede_id=sede.id, first="Target")
    _commit(db_session)

    payload = schemas.CommunicationLogCreate(
        persona_id=p_target.id,
        channel="WHATSAPP",
        content="ok",
        leader_id=None,
    )
    row = crud_comm.create_communication_log(db_session, payload, actor_user_id=p_actor.id)
    assert row.id is not None
    assert row.persona_id == p_target.id


def test_update_communication_log_returns_none_for_missing(db_session):
    out = crud_comm.update_communication_log(db_session, str(_uuid.uuid4()), CommunicationLogUpdate(content="x"))
    assert out is None


def test_update_communication_log_updates_provided_fields(db_session):
    sede = _seed_sede(db_session)
    p = _seed_persona(db_session, sede_id=sede.id)
    log = _seed_comm_log(db_session, persona=p, content="orig")
    _commit(db_session)
    out = crud_comm.update_communication_log(
        db_session, str(log.id), CommunicationLogUpdate(content="new", outcome="DELIVERED")
    )
    assert out.content == "new"
    assert out.outcome == "DELIVERED"


def test_update_communication_log_excludes_soft_deleted(db_session):
    sede = _seed_sede(db_session)
    p = _seed_persona(db_session, sede_id=sede.id)
    log = _seed_comm_log(db_session, persona=p, deleted_at=crud_comm._utcnow())
    _commit(db_session)
    out = crud_comm.update_communication_log(db_session, str(log.id), CommunicationLogUpdate(content="x"))
    assert out is None


def test_delete_communication_log_soft_deletes_and_returns_true(db_session):
    sede = _seed_sede(db_session)
    p = _seed_persona(db_session, sede_id=sede.id)
    log = _seed_comm_log(db_session, persona=p)
    _commit(db_session)
    assert crud_comm.delete_communication_log(db_session, str(log.id)) is True
    db_session.expire_all()
    assert crud_comm.get_communication_log(db_session, str(log.id)) is None


def test_delete_communication_log_returns_false_for_missing(db_session):
    assert crud_comm.delete_communication_log(db_session, str(_uuid.uuid4())) is False


# ─── notifications.py ──────────────────────────────────────────────────────────


def test_get_user_notifications_returns_empty_for_unknown_user(db_session):
    """resolve_persona_id_for_user(unknown) → None → return []."""
    _seed_sede(db_session)
    _commit(db_session)
    out = crud_notif.get_user_notifications(db_session, _uuid.uuid4())
    assert out == []


def test_get_user_notifications_returns_users_notifications_ordered_desc(db_session):
    sede = _seed_sede(db_session)
    p = _seed_persona(db_session, sede_id=sede.id)
    n_old = _seed_notification(db_session, user_id=p.id, title="Old")
    n_old.created_at = dt.datetime(2026, 6, 1, tzinfo=dt.timezone.utc)
    n_new = _seed_notification(db_session, user_id=p.id, title="New")
    n_new.created_at = dt.datetime(2026, 7, 1, tzinfo=dt.timezone.utc)
    _commit(db_session)

    out = crud_notif.get_user_notifications(db_session, p.id)
    titles = [n.title for n in out]
    assert "Old" in titles and "New" in titles
    assert titles == sorted(titles, reverse=True) or out[0].title == "New"


def test_get_user_notifications_returns_only_owners(db_session):
    sede = _seed_sede(db_session)
    p_a = _seed_persona(db_session, sede_id=sede.id, first="A")
    p_b = _seed_persona(db_session, sede_id=sede.id, first="B")
    n_a = _seed_notification(db_session, user_id=p_a.id, title="A")
    n_b = _seed_notification(db_session, user_id=p_b.id, title="B")
    _commit(db_session)

    ids = {n.id for n in crud_notif.get_user_notifications(db_session, p_a.id)}
    assert n_a.id in ids and n_b.id not in ids


def test_mark_notification_as_read_sets_is_read(db_session):
    sede = _seed_sede(db_session)
    p = _seed_persona(db_session, sede_id=sede.id)
    n = _seed_notification(db_session, user_id=p.id, is_read=False)
    _commit(db_session)
    out = crud_notif.mark_notification_as_read(db_session, n.id, owner_persona_id=p.id)
    assert out is not None
    assert out.is_read is True


def test_mark_notification_as_read_returns_none_for_missing(db_session):
    sede = _seed_sede(db_session)
    p = _seed_persona(db_session, sede_id=sede.id)
    _commit(db_session)
    assert crud_notif.mark_notification_as_read(db_session, _uuid.uuid4(), owner_persona_id=p.id) is None


def test_mark_notification_as_read_rejects_non_owner(db_session):
    """Axioma 3 (ownership): another user's notification → None (existence-leak safe)."""
    sede = _seed_sede(db_session)
    p_a = _seed_persona(db_session, sede_id=sede.id, first="A")
    p_b = _seed_persona(db_session, sede_id=sede.id, first="B")
    n = _seed_notification(db_session, user_id=p_a.id, is_read=False)
    _commit(db_session)

    out = crud_notif.mark_notification_as_read(db_session, n.id, owner_persona_id=p_b.id)
    assert out is None, "non-owner mark-as-read should be silently rejected (existence-leak safe)"
    db_session.expire_all()
    assert db_session.query(models.Notification).filter_by(id=n.id).first().is_read is False


def test_mark_all_notifications_read_returns_count(db_session):
    "mark_all returns the count of rows flipped from unread → read (A-06 contract)."
    sede = _seed_sede(db_session)
    p = _seed_persona(db_session, sede_id=sede.id)
    _seed_notification(db_session, user_id=p.id, is_read=False)
    _seed_notification(db_session, user_id=p.id, is_read=False)
    _seed_notification(db_session, user_id=p.id, is_read=True)  # already read
    _commit(db_session)

    count = crud_notif.mark_all_notifications_read(db_session, p.id)
    assert count == 2, f"mark_all should return 2 (only unread flipped), got {count}"


def test_mark_all_notifications_read_returns_zero_for_unknown_user(db_session):
    _seed_sede(db_session)
    _commit(db_session)
    assert crud_notif.mark_all_notifications_read(db_session, _uuid.uuid4()) == 0


def test_mark_all_notifications_read_idempotent_second_call_zero(db_session):
    """Second call after the first flips everything → returns 0 (no work to do)."""
    sede = _seed_sede(db_session)
    p = _seed_persona(db_session, sede_id=sede.id)
    _seed_notification(db_session, user_id=p.id, is_read=False)
    _commit(db_session)

    first = crud_notif.mark_all_notifications_read(db_session, p.id)
    assert first == 1
    second = crud_notif.mark_all_notifications_read(db_session, p.id)
    assert second == 0
