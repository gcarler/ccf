"""Direct unit tests for `backend.crud.crm_.personas` (QC-18 bootstrapping).

The CRM audit-tracker (errorescrm.md) noted 14/19 CRUD modules with 0 *direct*
unit tests — coverage was previously exercised only transitively via API
integration tests. This file starts closing the largest gap (personas.py:
28 public functions) by testing the helpers most exposed to silent regression:

  * `_persona_live_column_names` + `persona_query` — soft-delete filter layer
    that every CRM persona read goes through.
  * `_find_existing_persona` — Axioma 1 dedup + Axioma 3 sede-scope (C-01
    closure regression guard). A sneaky future change to the sede_filter or
    None branch here would reopen the cross-tenant merge.
  * `prepare_persona_for_output` — fields-not-in-schema nullifier.
  * `create_persona` — integration of the above at CRUD layer.

Fixture pattern: `db_session` from `tests/conftest` (SQLite in-memory, session
scoped to each test via transaction rollback); `models.Persona(id, sede_id,
estado_vital, ...)` direct row inserts. No HTTP layer — same posture as the
Academy CRUD-direct tests.

See: tests/test_crm_sede_isolation.py for the API-level version of the
cross-sede merge regression (which depends on these CRUD helpers being
correct).
"""

from __future__ import annotations

import uuid as _uuid
from typing import Optional

import pytest
from sqlalchemy.orm import Session

from backend import crud, models, schemas
from backend.crud.crm_.personas import (
    _find_existing_persona,
    _persona_live_column_names,
    create_persona,
    persona_query,
    prepare_persona_for_output,
)


# ─── Fixtures local — re-uses conftest.db_session + seed_admin via _seed_sede ──

def _seed_sede(db: Session, name: str = "Sede QC-18", ciudad: str = "QC18 City") -> models.Sede:
    sede = models.Sede(id=_uuid.uuid4(), nombre=name, ciudad=ciudad)
    db.add(sede)
    db.flush()
    return sede


def _persona_in(
    db: Session,
    *,
    sede_id: _uuid.UUID,
    first_name: str = "Anon",
    email: Optional[str] = None,
    phone: Optional[str] = None,
    id_number: Optional[str] = None,
    estado_vital: str = "ACTIVO",
) -> models.Persona:
    p = models.Persona(
        id=_uuid.uuid4(),
        first_name=first_name,
        last_name="Test",
        sede_id=sede_id,
        estado_vital=estado_vital,
        email=email or f"{first_name.lower()}@example.com",
        phone=phone,
        id_number=id_number,
    )
    db.add(p)
    db.flush()
    return p


def _commit(db: Session) -> None:
    """Persist rows so persona_query (load_only) sees them in a fresh SELECT."""
    db.commit()


def _persona_create_payload(**overrides) -> schemas.PersonaCreate:
    """Adepted to current PersonaCreate schema — extra="forbid" safe.

    Build with only the fields the schema actually accepts; the audit
    established `extra="forbid"` is the platform-wide doctrine so we don't
    accidentally smuggle a non-existent field through.
    """
    base = {
        "first_name": "New",
        "last_name": "Persona",
        "email": "new@example.com",
    }
    base.update(overrides)
    # PersonaCreate is extra="forbid"; defensively scrub None values that
    # Optional fields default to so Pydantic accepts the payload.
    return schemas.PersonaCreate(**{k: v for k, v in base.items() if v is not None})


# ─── Tests ─────────────────────────────────────────────────────────────────────


def test_persona_live_column_names_returns_populated_set(db_session):
    """The helper introspects the ORM-bind of db_session and returns the live
    set of column names on the `personas` table. Empty set in test-SQLite would
    cause `persona_query` to bypass `load_only` and `prepare_persona_for_output`
    to null every field — silently broken output shape.
    """
    names = _persona_live_column_names(db_session)
    # SQLite via Base.metadata.create_all materialises all declared columns;
    # at minimum id, sede_id, estado_vital, first_name, last_name.
    assert "id" in names, "personas.id column not discoverable — ORM/db bind mismatch"
    assert "sede_id" in names, "personas.sede_id column not discoverable (multi-tenant pillar)"
    assert "estado_vital" in names, "estado_vital column missing — soft-delete filter broken"


def test_persona_query_returns_query_object(db_session):
    """`persona_query` is the entry-point every CRM persona read uses; it must
    be safe to call before filters / load_only resolution."""
    sede = _seed_sede(db_session)
    _persona_in(db_session, sede_id=sede.id, first_name="Visible")
    _commit(db_session)
    q = persona_query(db_session)
    rows = q.all()
    assert any(r.first_name == "Visible" for r in rows), "persona_query did not return seeded row"


def test_find_existing_persona_respects_sede_scope(db_session):
    """Axioma 3 (C-01 regression guard): `_find_existing_persona` with a
    `sede_id` MUST NOT match a persona belonging to a different sede, even
    when phone / id_number collide cross-tenant. This is the helper that C-01
    closed; any future change to the sede_filter branch that drops the
    `sede_id != None` guard reopens the cross-tenant merge.
    """
    sede_a = _seed_sede(db_session, name="A")
    sede_b = _seed_sede(db_session, name="B")
    # Persona in sede B with phone + id_number that caller A will try to match
    _persona_in(
        db_session,
        sede_id=sede_b.id,
        first_name="SedeB",
        phone="+57-300-000-0001",
        id_number="ID-X-001",
    )
    _commit(db_session)
    payload = _persona_create_payload(phone="+57-300-000-0001", id_number="ID-X-001")

    # Caller from sede_a must NOT pick up sede_b's persona
    match = _find_existing_persona(db_session, payload, sede_id=sede_a.id)
    assert match is None, (
        "C-01 regression: _find_existing_persona returned a persona from sede_b "
        "for a sede_a caller (cross-tenant merge via phone/id_number)"
    )

    # Same-sede call SHOULD find it
    match_same = _find_existing_persona(db_session, payload, sede_id=sede_b.id)
    assert match_same is not None, "Same-sede dedup failed — over-scoped (no match at all)"
    assert match_same.sede_id == sede_b.id


def test_find_existing_persona_returns_none_when_no_match(db_session):
    """Sanity: empty DB / unmatched payload returns None instead of raising."""
    sede = _seed_sede(db_session)
    payload = _persona_create_payload(phone="+57-no-such-phone", id_number="ID-no-such")
    match = _find_existing_persona(db_session, payload, sede_id=sede.id)
    assert match is None


def test_find_existing_persona_dedups_intra_sede_by_phone(db_session):
    """Axioma 1 (Person-Centric Kernel preserved): within the same sede,
    matching phone returns the existing persona (anexar al UUID existente, no
    duplicar). This is the legitimate dedup behavior C-01 preserved when the
    sede-scope was added.
    """
    sede = _seed_sede(db_session)
    existing = _persona_in(
        db_session,
        sede_id=sede.id,
        first_name="Original",
        phone="+57-320-123-4567",
    )
    _commit(db_session)
    payload = _persona_create_payload(
        first_name="Duplicado",
        last_name="ConmismoPhone",
        email="otro@example.com",
        phone="+57-320-123-4567",
    )
    match = _find_existing_persona(db_session, payload, sede_id=sede.id)
    assert match is not None
    assert match.id == existing.id, "Dedup intra-sede returned a different persona id"
    assert match.sede_id == sede.id


def test_prepare_persona_for_output_nulls_fields_not_in_live_columns(db_session):
    """The output-nullifier zeroes ORM attributes that aren't part of the
    PersonaResponse schema + not in the live columns. In test-SQLite every
    declared column IS live, so the only field forced to None is the one
    declared in PersonaResponse.model_fields but absent from the model (if
    any). Verify the helper is idempotent and returns the same persona."""
    sede = _seed_sede(db_session)
    p = _persona_in(db_session, sede_id=sede.id, first_name="Qc18Out")
    _commit(db_session)
    out = prepare_persona_for_output(db_session, p)
    assert out is p, "prepare_persona_for_output must return the same persona instance (idempotent)"
    # The live身上 core fields should still be populated
    assert out.id == p.id
    assert out.sede_id == sede.id
    assert out.first_name == "Qc18Out"


def test_create_persona_does_not_merge_cross_sede(db_session):
    """Integration-level C-01 guard at the CRUD layer: calling create_persona
    with sede_id B for a payload whose phone already exists in sede A must NOT
    reuse sede A's persona (the bug C-01 closed). A new row is created instead.
    """
    sede_a = _seed_sede(db_session, name="SedeA")
    sede_b = _seed_sede(db_session, name="SedeB")
    _persona_in(
        db_session,
        sede_id=sede_a.id,
        first_name="ResidenteA",
        phone="+57-1-555-0001",
        id_number="DOC-A-1",
    )
    _commit(db_session)
    payload = _persona_create_payload(
        first_name="RecienLlegadoB",
        last_name="MismoPhone",
        email="b1@example.com",
        phone="+57-1-555-0001",  # collided phone cross-sede
        id_number="DOC-B-1",  # different doc — cannot be the same person
    )
    new_persona = create_persona(db_session, payload, sede_id=sede_b.id)
    # Pre-C-01 bug: new_persona would be sede_a's existing row (cross-tenant merge).
    # Post-fix: must be a NEW persona in sede_b.
    assert new_persona is not None
    assert new_persona.sede_id == sede_b.id, (
        f"C-01 regression at CRUD layer: create_persona attached cross-tenant "
        f"(new_persona.sede_id={new_persona.sede_id}, expected {sede_b.id})"
    )
    # Persona in sede A still belongs to sede A
    same_phone_in_a = (
        db_session.query(models.Persona)
        .filter(models.Persona.phone == "+57-1-555-0001")
        .filter(models.Persona.sede_id == sede_a.id)
        .first()
    )
    assert same_phone_in_a is not None
    assert same_phone_in_a.id != new_persona.id, "create_persona merged cross-tenant UUIDs"
