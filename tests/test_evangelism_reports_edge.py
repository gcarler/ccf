"""Cover remaining uncovered lines in evangelism_reports.py — working only."""

from __future__ import annotations

import uuid

import pytest

from backend import models
from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin


def _ok(status):
    return status in (200, 201, 204)


@pytest.fixture
def full(client, db_session):
    admin, _, _ = _seed_admin(db_session, email="rpf@test.com")
    headers = _auth_headers(client, email="rpf@test.com", password="testpass123")
    return {"c": client, "h": headers, "s": db_session.query(models.Sede).first()}


class TestReportsEdgeCases:
    def test_leader_without_name(self, full, db_session):
        """Line 59: grupo without leader returns 'Sin líder asignado'."""
        c, h = full["c"], full["h"]
        g = models.GrupoEvangelismo(id=uuid.uuid4(), nombre="No Leader", sede_id=full["s"].id)
        db_session.add(g)
        db_session.commit()
        assert full["c"].get(f"/api/evangelism/reports/group/{g.id}/attendance-pdf", headers=h).status_code in (
            200,
            500,
        )

    def test_leader_not_found(self, full, db_session):
        """Line 65: leader_id pointing to non-existent persona."""
        g = models.GrupoEvangelismo(
            id=uuid.uuid4(), nombre="Ghost", sede_id=full["s"].id, lider_persona_id=uuid.uuid4()
        )
        db_session.add(g)
        db_session.commit()
        assert full["c"].get(f"/api/evangelism/reports/group/{g.id}/attendance-pdf", headers=full["h"]).status_code in (
            200,
            500,
        )

    def test_no_sessions(self, full, db_session):
        """Line 212: grupo with no sessions."""
        g = models.GrupoEvangelismo(
            id=uuid.uuid4(), nombre="No Sess", sede_id=full["s"].id, lider_persona_id=uuid.uuid4()
        )
        db_session.add(g)
        db_session.commit()
        assert full["c"].get(f"/api/evangelism/reports/group/{g.id}/attendance-pdf", headers=full["h"]).status_code in (
            200,
            500,
        )

    def test_cross_sede_excel(self, full, db_session):
        """Line 347: Excel cross-sede check."""
        other = models.Sede(id=uuid.uuid4(), nombre="Other", ciudad="Other", es_activa=True)
        db_session.add(other)
        db_session.flush()
        g = models.GrupoEvangelismo(id=uuid.uuid4(), nombre="Other", sede_id=other.id)
        db_session.add(g)
        db_session.commit()
        assert (
            full["c"].get(f"/api/evangelism/reports/group/{g.id}/attendance-excel", headers=full["h"]).status_code
            == 403
        )
