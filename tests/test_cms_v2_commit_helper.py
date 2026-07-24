"""Regresión — M-12 alineación defensiva de ``_commit_or_raise_conflict``.

Antes del fix, el helper en ``backend/api/cms_v2.py::_commit_or_raise_conflict``
tragaba TODA ``IntegrityError`` como ``409 Conflict`` — enmascarando bugs
genuinos (NOT NULL, FK, check violations) tras un código HTTP que sugiere
"recurso duplicado". El fix alinea el gate con ``crud.cms._commit_or_conflict``:
solo ``pgcode == "23505"`` (Postgres unique violations) o el mensaje SQLite
``"UNIQUE constraint failed"`` generan 409; el resto se re-raise post-rollback.

Tests:
  1. ``test_commit_or_raise_unique_conflict_returns_409`` — una violación
     UNIQUE real (slug duplicado) produce ``HTTPException(409)``.
  2. ``test_commit_or_raise_non_unique_integrity_reraises`` — una
     ``IntegrityError`` cuyo ``orig`` NO es unique (mock con pgcode None)
     se re-raise (no se traduce a 409).

Cubierto por el cierre de M-12 (alineación defensiva, no unificación de
layers).
"""
from __future__ import annotations

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from backend.api.cms_v2 import _commit_or_raise_conflict
from backend import models
from backend.models_cms import Base


def _seed_site(db_session):
    """Crea una CmsSite mínima para que los INSERT de CmsPost no fallen por FK."""
    sede = models.Sede(name="sede-test-commit", slug="sede-test-commit")
    db_session.add(sede)
    db_session.flush()
    site = models.CmsSite(
        site_key="commit-test",
        name="Commit Test Site",
        sede_id=sede.id,
        is_active=True,
    )
    db_session.add(site)
    db_session.flush()
    return site


def test_commit_or_raise_unique_conflict_returns_409(db_session):
    """UNIQUE real → 409.

    Crea dos ``CmsSectionType`` con el mismo ``name`` (que tiene UNIQUE
    constraint). El segundo commit debe propagar ``IntegrityError`` con
    pgcode 23505 (Postgres) o el mensaje SQLite "UNIQUE constraint
    failed"; el helper lo traduce a ``HTTPException(409)``.
    """
    # Mantenemos la tabla física de CmsSectionType en el schema de test
    # (Base.metadata.create_all la crea en el fixture de sesión).
    assert "cms_section_types" in Base.metadata.tables

    name = "unique_test_section"
    st1 = models.CmsSectionType(
        name=name,
        display_name="Section Type 1",
        is_active=True,
    )
    db_session.add(st1)
    _commit_or_raise_conflict(db_session)  # Primera inserción: éxito (no raise)

    # Segunda inserción con mismo nombre → UNIQUE violation.
    st2 = models.CmsSectionType(
        name=name,
        display_name="Section Type 2",
        is_active=True,
    )
    db_session.add(st2)
    with pytest.raises(HTTPException) as exc_info:
        _commit_or_raise_conflict(db_session)
    assert exc_info.value.status_code == 409


def test_commit_or_raise_non_unique_integrity_reraises(db_session):
    """``IntegrityError`` no-unique → re-raise (no 409).

    Inyecta un mock ``IntegrityError`` cuyo ``orig`` tiene ``pgcode=None``
    y mensaje sin "UNIQUE constraint failed". El helper debe hacer rollback
    y re-raise la ``IntegrityError`` original, NO traducirla a 409.
    """
    # Fabrica un IntegrityError cuyo orig no es unique (pgcode None, msg
    # neutro) — simula una NOT NULL / FK / check genérica.
    fake_orig = type("FakeOrig", (), {"pgcode": None})()
    # str(orig) no contiene "UNIQUE constraint failed"
    fake_orig.__str__ = lambda self: "NOT NULL constraint failed: x"  # type: ignore
    fake_exc = IntegrityError(
        statement="INSERT INTO fake VALUES (1)",
        params=None,
        orig=fake_orig,
    )

    # Mock db.commit() que lanza la excepción falsa; mock db.rollback() no-op.
    class _FakeDB:
        def commit(self):
            raise fake_exc

        def rollback(self):
            pass

    with pytest.raises(IntegrityError) as exc_info:
        _commit_or_raise_conflict(_FakeDB(), detail="should not be 409")
    # Confirma que se elevó la IntegrityError original, no HTTPException:
    assert not isinstance(exc_info.value, HTTPException)
    assert exc_info.value is fake_exc
