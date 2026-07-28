"""Final tests for remaining uncovered evangelism endpoints."""
from __future__ import annotations

import uuid

import pytest

from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin


def _ok(status):
    return status in (200, 201, 204)


@pytest.fixture
def full(client, db_session):
    admin, _, _ = _seed_admin(db_session, email="last@test.com")
    headers = _auth_headers(client, email="last@test.com", password="testpass123")
    return {"c": client, "h": headers}


class TestMultiplicacion:
    def test_check(self, full):
        assert _ok(full["c"].get("/api/evangelism/multiplication/check", headers=full["h"]).status_code)
    def test_history(self, full):
        assert _ok(full["c"].get("/api/evangelism/multiplication/history", headers=full["h"]).status_code)


class TestEventsParticipantes:
    def test_create_not_found(self, full):
        assert full["c"].post(f"/api/evangelism/events/{uuid.uuid4()}/participants",
            json={"persona_id": str(uuid.uuid4()), "role": "asistente"},
            headers=full["h"]).status_code == 404

    def test_list_not_found(self, full):
        assert full["c"].get(f"/api/evangelism/events/{uuid.uuid4()}/participants",
            headers=full["h"]).status_code == 404

    def test_delete_not_found(self, full):
        assert full["c"].delete(f"/api/evangelism/events/{uuid.uuid4()}/participants/{uuid.uuid4()}",
            headers=full["h"]).status_code == 404


class TestReports:
    def test_pdf_not_found(self, full):
        assert full["c"].get(f"/api/evangelism/reports/group/{uuid.uuid4()}/attendance-pdf",
            headers=full["h"]).status_code == 404
    def test_excel_not_found(self, full):
        assert full["c"].get(f"/api/evangelism/reports/group/{uuid.uuid4()}/attendance-excel",
            headers=full["h"]).status_code == 404
    def test_summary_not_found(self, full):
        assert full["c"].get(f"/api/evangelism/reports/strategy/{uuid.uuid4()}/summary",
            headers=full["h"]).status_code == 404


class TestAnalyticsRemaining:
    def test_heatmap_404(self, full):
        assert full["c"].get(f"/api/evangelism/analytics/strategy/{uuid.uuid4()}/heatmap",
            headers=full["h"]).status_code == 404

    def test_alerts_404(self, full):
        assert full["c"].get(f"/api/evangelism/analytics/strategy/{uuid.uuid4()}/alerts",
            headers=full["h"]).status_code == 404

    def test_groups_404(self, full):
        assert full["c"].get(f"/api/evangelism/analytics/strategy/{uuid.uuid4()}/groups",
            headers=full["h"]).status_code == 404
