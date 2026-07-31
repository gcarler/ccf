"""Tests for events_participantes.py — working endpoints."""

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
    admin, _, _ = _seed_admin(db_session, email="ep@test.com")
    headers = _auth_headers(client, email="ep@test.com", password="testpass123")
    return {"c": client, "h": headers, "s": db_session.query(models.Sede).first()}


class TestEventAttendance:
    def test_get_report_not_found(self, full):
        assert full["c"].get(f"/api/evangelism/events/{uuid.uuid4()}/attendance", headers=full["h"]).status_code == 404

    def test_get_report_with_event(self, full, db_session):
        c, h = full["c"], full["h"]
        evt = c.post(
            "/api/evangelism/events",
            json={"name": f"E-{uuid.uuid4().hex[:6]}", "event_date": "2026-09-01T10:00:00Z"},
            headers=h,
        ).json()
        resp = c.get(f"/api/evangelism/events/{evt['id']}/attendance", headers=h)
        assert _ok(resp.status_code)

    def test_get_session_detail_not_found(self, full):
        assert (
            full["c"].get(f"/api/evangelism/events/{uuid.uuid4()}/sessions/2026-09-01", headers=full["h"]).status_code
            == 404
        )


class TestReportsRevisited:
    def test_pdf_not_found(self, full):
        assert (
            full["c"].get(f"/api/evangelism/reports/group/{uuid.uuid4()}/attendance-pdf", headers=full["h"]).status_code
            == 404
        )

    def test_excel_not_found(self, full):
        assert (
            full["c"]
            .get(f"/api/evangelism/reports/group/{uuid.uuid4()}/attendance-excel", headers=full["h"])
            .status_code
            == 404
        )

    def test_summary_not_found(self, full):
        assert (
            full["c"].get(f"/api/evangelism/reports/strategy/{uuid.uuid4()}/summary", headers=full["h"]).status_code
            == 404
        )
