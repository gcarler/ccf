"""Tests for evangelism_reports.py — all endpoints."""

from __future__ import annotations

import uuid

import pytest

from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin


def _ok(status):
    return status in (200, 201, 204)


@pytest.fixture
def full(client, db_session):
    admin, _, _ = _seed_admin(db_session, email="evrp@test.com")
    headers = _auth_headers(client, email="evrp@test.com", password="testpass123")
    return {"c": client, "h": headers}


class TestReports:
    def test_attendance_pdf_not_found(self, full):
        assert (
            full["c"].get(f"/api/evangelism/reports/group/{uuid.uuid4()}/attendance-pdf", headers=full["h"]).status_code
            == 404
        )

    def test_attendance_excel_not_found(self, full):
        assert (
            full["c"]
            .get(f"/api/evangelism/reports/group/{uuid.uuid4()}/attendance-excel", headers=full["h"])
            .status_code
            == 404
        )

    def test_strategy_summary_not_found(self, full):
        assert (
            full["c"].get(f"/api/evangelism/reports/strategy/{uuid.uuid4()}/summary", headers=full["h"]).status_code
            == 404
        )
