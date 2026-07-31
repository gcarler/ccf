"""Direct unit tests for `backend.crud.crm_.families`.

QC follow-up: `families.py` lacked a dedicated test file (covered only
transitively in `test_crm_extended_coverage.py`). This module tests all
public functions directly against SQLite in-memory via the `db_session`
fixture, mirroring the posture of `tests/test_crm_crud_pipeline.py`.

Coverage targets:
  * get_families (with/without sede scope, personas_count aggregation)
  * create_family
  * get_family
  * update_family
  * delete_family (soft-delete via deleted_at ORM attribute)
  * get_family_personas

Axioma 3 note: `Family` does not have a `sede_id` column. Scope is
inferred via the join with `Persona.family_id`. Therefore `get_families`
only returns families that have at least one persona in the actor's sede.
"""

from __future__ import annotations

import uuid as _uuid

from sqlalchemy.orm import Session

from backend import models
from backend.crud.crm_.families import (
    create_family,
    delete_family,
    get_families,
    get_family,
    get_family_personas,
    update_family,
)


def _seed_sede(db: Session, name: str = "Sede Fam") -> models.Sede:
    sede = models.Sede(id=_uuid.uuid4(), nombre=name, ciudad="Bogota", es_activa=True)
    db.add(sede)
    db.flush()
    return sede


def _seed_persona(
    db: Session, *, sede_id: _uuid.UUID, family_id: _uuid.UUID | None = None, first: str = "P"
) -> models.Persona:
    p = models.Persona(
        id=_uuid.uuid4(),
        first_name=first,
        last_name="T",
        sede_id=sede_id,
        family_id=family_id,
        estado_vital="ACTIVO",
        email=f"{first.lower()}{_uuid.uuid4().hex[:6]}@example.com",
    )
    db.add(p)
    db.flush()
    return p


def _commit(db: Session) -> None:
    db.commit()


# ─── Family CRUD ────────────────────────────────────────────────────────────────


def test_create_family_persists_name(db_session):
    fam = create_family(db_session, name="Familia Garcia")
    assert fam.id is not None
    assert fam.name == "Familia Garcia"


def test_get_family_returns_none_for_missing(db_session):
    assert get_family(db_session, _uuid.uuid4()) is None


def test_get_family_fetches_existing(db_session):
    fam = create_family(db_session, name="Familia Lopez")
    _commit(db_session)
    fetched = get_family(db_session, fam.id)
    assert fetched is not None
    assert fetched.id == fam.id
    assert fetched.name == "Familia Lopez"


def test_update_family_returns_none_for_missing(db_session):
    assert update_family(db_session, _uuid.uuid4(), "X") is None


def test_update_family_changes_name(db_session):
    fam = create_family(db_session, name="Familia Old")
    _commit(db_session)
    out = update_family(db_session, fam.id, "Familia New")
    assert out is not None
    assert out.name == "Familia New"
    # Re-fetch to ensure persistence
    db_session.expire_all()
    fetched = get_family(db_session, fam.id)
    assert fetched.name == "Familia New"


def test_delete_family_returns_false_for_missing(db_session):
    assert delete_family(db_session, _uuid.uuid4()) is False


def test_delete_family_soft_deletes_and_blocks_get(db_session):
    fam = create_family(db_session, name="Familia Gone")
    _commit(db_session)
    assert delete_family(db_session, fam.id) is True
    db_session.expire_all()
    assert get_family(db_session, fam.id) is None


# ─── Scope via Personas & Aggregation ───────────────────────────────────────────


def test_get_families_scoped_by_sede(db_session):
    """Axioma 3: only families with a persona in the requested sede are visible."""
    sede_a = _seed_sede(db_session, name="A")
    sede_b = _seed_sede(db_session, name="B")
    fam_a = create_family(db_session, name="Familia A")
    fam_b = create_family(db_session, name="Familia B")
    _seed_persona(db_session, sede_id=sede_a.id, family_id=fam_a.id, first="A")
    _seed_persona(db_session, sede_id=sede_b.id, family_id=fam_b.id, first="B")
    _commit(db_session)

    ids_a = {f.id for f in get_families(db_session, sede_id=sede_a.id)}
    assert fam_a.id in ids_a
    assert fam_b.id not in ids_a


def test_get_families_without_sede_returns_all(db_session):
    sede = _seed_sede(db_session)
    fam_a = create_family(db_session, name="Familia A")
    fam_b = create_family(db_session, name="Familia B")
    _seed_persona(db_session, sede_id=sede.id, family_id=fam_a.id)
    _seed_persona(db_session, sede_id=sede.id, family_id=fam_b.id)
    _commit(db_session)

    ids = {f.id for f in get_families(db_session)}
    assert fam_a.id in ids
    assert fam_b.id in ids


def test_get_families_ordered_by_name(db_session):
    sede = _seed_sede(db_session)
    fam_z = create_family(db_session, name="Zeta")
    fam_a = create_family(db_session, name="Alfa")
    fam_b = create_family(db_session, name="Beta")
    _seed_persona(db_session, sede_id=sede.id, family_id=fam_z.id)
    _seed_persona(db_session, sede_id=sede.id, family_id=fam_a.id)
    _seed_persona(db_session, sede_id=sede.id, family_id=fam_b.id)
    _commit(db_session)

    names = [f.name for f in get_families(db_session, sede_id=sede.id)]
    assert names == sorted(names)


def test_get_families_personas_count_aggregation(db_session):
    """personas_count is attached via batch GROUP BY instead of N+1 queries."""
    sede = _seed_sede(db_session)
    fam = create_family(db_session, name="Familia Count")
    _seed_persona(db_session, sede_id=sede.id, family_id=fam.id, first="One")
    _seed_persona(db_session, sede_id=sede.id, family_id=fam.id, first="Two")
    _commit(db_session)

    families = get_families(db_session, sede_id=sede.id)
    assert len(families) == 1
    assert families[0].personas_count == 2


def test_get_family_personas_returns_members(db_session):
    sede = _seed_sede(db_session)
    fam = create_family(db_session, name="Familia Members")
    p1 = _seed_persona(db_session, sede_id=sede.id, family_id=fam.id, first="One")
    p2 = _seed_persona(db_session, sede_id=sede.id, family_id=fam.id, first="Two")
    _commit(db_session)

    members = get_family_personas(db_session, fam.id)
    member_ids = {p.id for p in members}
    assert p1.id in member_ids
    assert p2.id in member_ids


def test_get_families_pagination(db_session):
    sede = _seed_sede(db_session)
    for i in range(5):
        fam = create_family(db_session, name=f"Familia {i:02d}")
        _seed_persona(db_session, sede_id=sede.id, family_id=fam.id, first=f"P{i}")
    _commit(db_session)

    page = get_families(db_session, sede_id=sede.id, skip=1, limit=2)
    assert len(page) == 2
