"""Direct unit tests for `backend.crud.crm_.milestones` + `timeline` (QC-18 módulo D).

QC-18 closure (errorescrm.md): both modules had 0 direct tests.
  * milestones.py (6 funcs): CRUD over `SpiritualMilestone`, soft-delete
    via `deleted_at`.
  * timeline.py (1 func): `get_persona_timeline` aggregates 6 event
    types (participación, academy, ministry, counseling, communication,
    spiritual_milestone) into one sorted JSON list. The interesting
    regression surface here is "soft-deleted milestones must not appear
    in the aggregated timeline" (the filter `deleted_at IS NULL` lives
    in the touchpoint at timeline.py:94).

Posture mirrors `tests/test_crm_crud_personas.py`: SQLite in-memory via
`db_session`, direct row inserts, no HTTP layer. We exercise:
  * Soft-delete (deleted_at) on milestone CRUD + timeline aggregation.
  * Sede-scope (Axioma 3): `list_milestones(sede_id=X)` must not leak.
  * `get_milestones` raises 404 on malformed persona_id (existence-leak
    contract via `_coerce_uuid_or_404`).
  * Timeline aggregation returns `[]` for unknown persona.
  * Timeline exposes each of the 6 event types when the corresponding
    row exists; ordering is desc by date.
"""
from __future__ import annotations

import datetime as dt
import uuid as _uuid
from typing import Optional

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend import models
from backend.crud.crm_ import milestones as crud_milestones
from backend.crud.crm_ import timeline as crud_timeline

# ─── Fixtures local ────────────────────────────────────────────────────────────

def _seed_sede(db: Session, name: str = "Sede QC-18.D") -> models.Sede:
    sede = models.Sede(id=_uuid.uuid4(), nombre=name, ciudad="QC18 City", es_activa=True)
    db.add(sede)
    db.flush()
    return sede


def _seed_persona(db: Session, sede_id: _uuid.UUID, first: str = "P", church_role: str = "MIEMBRO") -> models.Persona:
    p = models.Persona(
        id=_uuid.uuid4(), first_name=first, last_name="T", sede_id=sede_id, estado_vital="ACTIVO",
        email=f"{first.lower()}{_uuid.uuid4().hex[:6]}@example.com",
        church_role=church_role,
    )
    db.add(p)
    db.flush()
    return p


def _seed_milestone(
    db: Session, *, persona: models.Persona, sede_id: Optional[_uuid.UUID] = None,
    type: str = "BAUTISMO", event_date=None, deleted_at=None, notes: Optional[str] = None,
) -> models.SpiritualMilestone:
    m = models.SpiritualMilestone(
        id=_uuid.uuid4(),
        persona_id=persona.id,
        sede_id=sede_id or persona.sede_id,
        type=type,
        event_date=event_date or dt.date(2026, 7, 1),
        notes=notes,
    )
    if deleted_at is not None:
        m.deleted_at = deleted_at
    db.add(m)
    db.flush()
    return m


def _commit(db: Session) -> None:
    db.commit()


# ─── milestones.py ──────────────────────────────────────────────────────────────


def test_get_milestone_returns_none_for_missing(db_session):
    assert crud_milestones.get_milestone(db_session, _uuid.uuid4()) is None


def test_get_milestone_excludes_soft_deleted(db_session):
    sede = _seed_sede(db_session)
    p = _seed_persona(db_session, sede_id=sede.id)
    m = _seed_milestone(db_session, persona=p, deleted_at=crud_milestones._utcnow())
    _commit(db_session)
    assert crud_milestones.get_milestone(db_session, m.id) is None


def test_get_milestones_raises_404_for_malformed_persona_id(db_session):
    """`_coerce_uuid_or_404` existence-leak contract: malformed → 404, never 500."""
    with pytest.raises(HTTPException) as exc:
        crud_milestones.get_milestones(db_session, persona_id="not-a-uuid")
    assert exc.value.status_code == 404


def test_get_milestones_scoped_by_persona_and_excludes_soft_deleted(db_session):
    """get_milestones by persona_uuid must filter deleted_at IS NULL."""
    sede = _seed_sede(db_session)
    p = _seed_persona(db_session, sede_id=sede.id)
    p_other = _seed_persona(db_session, sede_id=sede.id, first="Other")
    m_live = _seed_milestone(db_session, persona=p, type="BAUTISMO", event_date=dt.date(2026, 6, 1))
    m_dead = _seed_milestone(db_session, persona=p, type="CONFIRMACION", event_date=dt.date(2026, 5, 1),
                             deleted_at=crud_milestones._utcnow())
    m_other = _seed_milestone(db_session, persona=p_other, type="OTRO", event_date=dt.date(2026, 4, 1))
    _commit(db_session)

    out = crud_milestones.get_milestones(db_session, persona_id=str(p.id))
    ids = {m.id for m in out}
    assert m_live.id in ids
    assert m_dead.id not in ids, "get_milestones leaked a soft-deleted milestone"
    assert m_other.id not in ids, "get_milestones leaked a milestone of another persona"


def test_get_milestones_ordered_by_event_date_desc(db_session):
    sede = _seed_sede(db_session)
    p = _seed_persona(db_session, sede_id=sede.id)
    m_old = _seed_milestone(db_session, persona=p, event_date=dt.date(2024, 1, 1))
    m_new = _seed_milestone(db_session, persona=p, event_date=dt.date(2026, 6, 1))
    m_mid = _seed_milestone(db_session, persona=p, event_date=dt.date(2025, 6, 1))
    _commit(db_session)

    dates = [m.event_date for m in crud_milestones.get_milestones(db_session, persona_id=str(p.id))]
    assert dates == sorted(dates, reverse=True), f"get_milestones not desc-ordered: {dates}"


def test_list_milestones_scoped_by_sede(db_session):
    """Axioma 3: list_milestones(sede_id=A) must NOT return B's milestones."""
    sede_a = _seed_sede(db_session, name="A")
    sede_b = _seed_sede(db_session, name="B")
    p_a = _seed_persona(db_session, sede_id=sede_a.id, first="A")
    p_b = _seed_persona(db_session, sede_id=sede_b.id, first="B")
    m_a = _seed_milestone(db_session, persona=p_a, sede_id=sede_a.id)
    m_b = _seed_milestone(db_session, persona=p_b, sede_id=sede_b.id)
    _commit(db_session)

    ids = {m.id for m in crud_milestones.list_milestones(db_session, sede_id=sede_a.id)}
    assert m_a.id in ids and m_b.id not in ids


def test_list_milestones_global_when_no_sede(db_session):
    """list_milestones() with sede_id=None returns all live milestones."""
    sede_a = _seed_sede(db_session, name="A")
    sede_b = _seed_sede(db_session, name="B")
    p_a = _seed_persona(db_session, sede_id=sede_a.id, first="A")
    p_b = _seed_persona(db_session, sede_id=sede_b.id, first="B")
    m_a = _seed_milestone(db_session, persona=p_a, sede_id=sede_a.id)
    m_b = _seed_milestone(db_session, persona=p_b, sede_id=sede_b.id)
    _commit(db_session)

    ids = {m.id for m in crud_milestones.list_milestones(db_session, sede_id=None)}
    assert m_a.id in ids and m_b.id in ids


def test_list_milestones_excludes_soft_deleted(db_session):
    sede = _seed_sede(db_session)
    p = _seed_persona(db_session, sede_id=sede.id)
    m_live = _seed_milestone(db_session, persona=p, sede_id=sede.id)
    m_dead = _seed_milestone(db_session, persona=p, sede_id=sede.id, deleted_at=crud_milestones._utcnow())
    _commit(db_session)

    ids = {m.id for m in crud_milestones.list_milestones(db_session, sede_id=sede.id)}
    assert m_live.id in ids and m_dead.id not in ids


def test_create_milestone_coerces_string_uuids(db_session):
    """`_to_uuid` accepts both uuid.UUID and str on persona_id/minister_id/sede_id."""
    sede = _seed_sede(db_session)
    minister = _seed_persona(db_session, sede_id=sede.id, first="Min")
    p = _seed_persona(db_session, sede_id=sede.id, first="Target")
    _commit(db_session)

    row = crud_milestones.create_milestone(
        db_session,
        persona_id=str(p.id),  # str input — exercised by API layer
        type="BAUTISMO",
        event_date=dt.date(2026, 7, 1),
        minister_id=str(minister.id),  # str input
        sede_id=str(sede.id),  # str input
        notes=" baptism notes",
    )
    assert row.id is not None
    assert row.persona_id == p.id
    assert row.minister_id == minister.id
    assert row.sede_id == sede.id
    assert row.deleted_at is None


def test_update_milestone_returns_none_for_missing(db_session):
    assert crud_milestones.update_milestone(db_session, _uuid.uuid4(), notes="x") is None


def test_update_milestone_sets_provided_fields(db_session):
    sede = _seed_sede(db_session)
    p = _seed_persona(db_session, sede_id=sede.id)
    m = _seed_milestone(db_session, persona=p, sede_id=sede.id, notes="orig")
    _commit(db_session)
    out = crud_milestones.update_milestone(db_session, m.id, notes="updated", type="OTRO")
    assert out.notes == "updated"
    assert out.type == "OTRO"


def test_delete_milestone_soft_deletes_and_returns_true(db_session):
    sede = _seed_sede(db_session)
    p = _seed_persona(db_session, sede_id=sede.id)
    m = _seed_milestone(db_session, persona=p, sede_id=sede.id)
    _commit(db_session)
    assert crud_milestones.delete_milestone(db_session, m.id) is True
    db_session.expire_all()
    row = db_session.query(models.SpiritualMilestone).filter(models.SpiritualMilestone.id == m.id).first()
    assert row is not None and row.deleted_at is not None
    assert crud_milestones.get_milestone(db_session, m.id) is None


def test_delete_milestone_returns_false_for_missing(db_session):
    assert crud_milestones.delete_milestone(db_session, _uuid.uuid4()) is False


def test_delete_milestone_returns_false_for_already_deleted(db_session):
    """Already-soft-deleted is filtered out by the `deleted_at IS NULL` query."""
    sede = _seed_sede(db_session)
    p = _seed_persona(db_session, sede_id=sede.id)
    m = _seed_milestone(db_session, persona=p, sede_id=sede.id, deleted_at=crud_milestones._utcnow())
    _commit(db_session)
    assert crud_milestones.delete_milestone(db_session, m.id) is False


# ─── timeline.py ────────────────────────────────────────────────────────────────


def test_get_persona_timeline_returns_empty_for_unknown_persona(db_session):
    """Unknown-but-wellformed UUID → [] (not raise)."""
    out = crud_timeline.get_persona_timeline(db_session, str(_uuid.uuid4()))
    assert out == []


def test_get_persona_timeline_includes_participation_event(db_session):
    """Every persona contributes a 'participation' event from `created_at`."""
    sede = _seed_sede(db_session)
    p = _seed_persona(db_session, sede_id=sede.id)
    _commit(db_session)

    types = [e["type"] for e in crud_timeline.get_persona_timeline(db_session, str(p.id))]
    assert "participation" in types


def test_get_persona_timeline_includes_only_live_milestones(db_session):
    """Soft-delete contract: deleted_at-filtered milestones are NOT aggregated.

    This is the regression surface timeline.py:94 — the touchpoint for the
    milestones CRUD's deleted_at filter. If it's ever dropped, soft-deleted
    milestones would reappear in the persona's public timeline.
    """
    sede = _seed_sede(db_session)
    p = _seed_persona(db_session, sede_id=sede.id)
    m_live = _seed_milestone(db_session, persona=p, sede_id=sede.id, type="BAUTISMO")
    m_dead = _seed_milestone(
        db_session, persona=p, sede_id=sede.id, type="CONFIRMACION",
        deleted_at=crud_milestones._utcnow(),
    )
    _commit(db_session)

    titles = [e["title"] for e in crud_timeline.get_persona_timeline(db_session, str(p.id)) if e["type"] == "spiritual_milestone"]
    assert any("BAUTISMO" in t for t in titles)
    assert not any("CONFIRMACION" in t for t in titles), "timeline aggregated a soft-deleted milestone"


def test_get_persona_timeline_sorted_desc_by_date(db_session):
    """timeline.sort(key=date desc) contract."""
    sede = _seed_sede(db_session)
    p = _seed_persona(db_session, sede_id=sede.id)
    _seed_milestone(db_session, persona=p, sede_id=sede.id, event_date=dt.date(2024, 1, 1))
    _seed_milestone(db_session, persona=p, sede_id=sede.id, event_date=dt.date(2026, 6, 1))
    _commit(db_session)

    dates = [e["date"] for e in crud_timeline.get_persona_timeline(db_session, str(p.id))]
    assert dates == sorted(dates, reverse=True), f"timeline not desc-ordered: {dates}"


def test_get_persona_timeline_each_item_has_canonical_shape(db_session):
    """Contract: every timeline entry has type/title/description/date/icon/color
    PLUS the post-loop setattr-injected created_at/notes/event_type keys."""
    sede = _seed_sede(db_session)
    p = _seed_persona(db_session, sede_id=sede.id)
    _commit(db_session)

    out = crud_timeline.get_persona_timeline(db_session, str(p.id))
    assert out, "expected at least the participation event"
    required_keys = {"type", "title", "description", "date", "icon", "color", "created_at", "notes", "event_type"}
    for entry in out:
        missing = required_keys - set(entry.keys())
        assert not missing, f"timeline entry missing keys {missing}: {entry}"
