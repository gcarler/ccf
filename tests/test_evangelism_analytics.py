"""
Tests for evangelism_analytics.py — all analytics endpoints.
"""

from __future__ import annotations

import uuid

import pytest

from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin


def _ok(status):
    return status in (200, 201, 204)


@pytest.fixture
def full(client, db_session):
    admin, _, _ = _seed_admin(db_session, email="analytics@test.com")
    headers = _auth_headers(client, email="analytics@test.com", password="testpass123")
    return {"c": client, "h": headers}


def _make_strategy(full):
    resp = full["c"].post("/api/evangelism/strategies", json={"name": f"S-{uuid.uuid4().hex[:6]}"}, headers=full["h"])
    assert _ok(resp.status_code)
    return resp.json()


class TestAnalytics:
    def test_not_found(self, full):
        assert full["c"].get(f"/api/evangelism/analytics/strategy/{uuid.uuid4()}", headers=full["h"]).status_code == 404

    def test_main(self, full):
        assert _ok(
            full["c"]
            .get(f"/api/evangelism/analytics/strategy/{_make_strategy(full)['id']}", headers=full["h"])
            .status_code
        )

    def test_trend_not_found(self, full):
        assert (
            full["c"].get(f"/api/evangelism/analytics/strategy/{uuid.uuid4()}/trend", headers=full["h"]).status_code
            == 404
        )

    def test_trend(self, full):
        assert _ok(
            full["c"]
            .get(f"/api/evangelism/analytics/strategy/{_make_strategy(full)['id']}/trend", headers=full["h"])
            .status_code
        )

    def test_funnel_not_found(self, full):
        assert (
            full["c"].get(f"/api/evangelism/analytics/strategy/{uuid.uuid4()}/funnel", headers=full["h"]).status_code
            == 404
        )

    def test_funnel(self, full):
        assert _ok(
            full["c"]
            .get(f"/api/evangelism/analytics/strategy/{_make_strategy(full)['id']}/funnel", headers=full["h"])
            .status_code
        )

    def test_heatmap_not_found(self, full):
        assert (
            full["c"].get(f"/api/evangelism/analytics/strategy/{uuid.uuid4()}/heatmap", headers=full["h"]).status_code
            == 404
        )

    def test_heatmap(self, full):
        assert _ok(
            full["c"]
            .get(f"/api/evangelism/analytics/strategy/{_make_strategy(full)['id']}/heatmap", headers=full["h"])
            .status_code
        )

    def test_alerts_not_found(self, full):
        assert (
            full["c"].get(f"/api/evangelism/analytics/strategy/{uuid.uuid4()}/alerts", headers=full["h"]).status_code
            == 404
        )

    def test_alerts(self, full):
        assert _ok(
            full["c"]
            .get(f"/api/evangelism/analytics/strategy/{_make_strategy(full)['id']}/alerts", headers=full["h"])
            .status_code
        )

    def test_velocity_not_found(self, full):
        assert (
            full["c"].get(f"/api/evangelism/analytics/strategy/{uuid.uuid4()}/velocity", headers=full["h"]).status_code
            == 404
        )

    def test_velocity(self, full):
        assert _ok(
            full["c"]
            .get(f"/api/evangelism/analytics/strategy/{_make_strategy(full)['id']}/velocity", headers=full["h"])
            .status_code
        )

    def test_groups_not_found(self, full):
        assert (
            full["c"].get(f"/api/evangelism/analytics/strategy/{uuid.uuid4()}/groups", headers=full["h"]).status_code
            == 404
        )

    def test_groups(self, full):
        assert _ok(
            full["c"]
            .get(f"/api/evangelism/analytics/strategy/{_make_strategy(full)['id']}/groups", headers=full["h"])
            .status_code
        )

    def test_full_not_found(self, full):
        assert (
            full["c"].get(f"/api/evangelism/analytics/strategy/{uuid.uuid4()}/full", headers=full["h"]).status_code
            == 404
        )

    def test_full(self, full):
        assert _ok(
            full["c"]
            .get(f"/api/evangelism/analytics/strategy/{_make_strategy(full)['id']}/full", headers=full["h"])
            .status_code
        )
