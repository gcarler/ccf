"""More tests for evangelism — analytics helpers + API endpoints."""
from __future__ import annotations

import uuid

import pytest

from backend.api import evangelism_analytics as analytics
from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin


# ── UNIT TESTS ──────────────────────────────────────────────────────────────────

class TestAnalyticsHelpers:
    def test_get_strategy_raises(self, db_session):
        with pytest.raises(Exception):
            analytics._get_strategy_or_404(db_session, uuid.uuid4(), uuid.uuid4())
    def test_group_ids_empty(self, db_session):
        assert analytics._group_ids_for_strategy(db_session, uuid.uuid4(), uuid.uuid4()) == []
    def test_delta(self):
        assert analytics._delta(0, 0) == 0.0
        assert analytics._delta(10, 0) == 100.0
        assert analytics._delta(20, 10) == 100.0
        assert analytics._delta(10, 20) == -50.0
    def test_parse_period(self):
        assert analytics._parse_period("7d") == 7
        assert analytics._parse_period("30d") == 30
        assert analytics._parse_period("x") == 30
    def test_date_range(self):
        start, end = analytics._date_range(30)
        assert (end - start).days == 30
    def test_prev_range(self):
        start, end = analytics._prev_range(30)
        assert (end - start).days == 30
    def test_normalize_rol(self):
        assert analytics._normalize_rol("Líder") == "lider"
        assert analytics._normalize_rol("") == ""
    def test_rol_to_funnel(self):
        assert analytics._rol_to_funnel_stage("Líder") == "lider"
        assert analytics._rol_to_funnel_stage("Visitante") == "visitante"
        assert analytics._rol_to_funnel_stage("Xyz") == "personalizado"


# ── API TESTS ───────────────────────────────────────────────────────────────────

def _ok(status):
    return status in (200, 201, 204)


@pytest.fixture
def full(client, db_session):
    admin, _, _ = _seed_admin(db_session, email="more@test.com")
    headers = _auth_headers(client, email="more@test.com", password="testpass123")
    return {"c": client, "h": headers}


class TestAPI:
    def test_kpis_with_strategy(self, full):
        c, h = full["c"], full["h"]
        s = c.post("/api/evangelism/strategies", json={"name": f"S-{uuid.uuid4().hex[:6]}"}, headers=h).json()
        assert _ok(c.get(f"/api/evangelism/analytics/strategy/{s['id']}", headers=h).status_code)
    def test_trend(self, full):
        c, h = full["c"], full["h"]
        s = c.post("/api/evangelism/strategies", json={"name": f"S-{uuid.uuid4().hex[:6]}"}, headers=h).json()
        assert _ok(c.get(f"/api/evangelism/analytics/strategy/{s['id']}/trend", headers=h).status_code)
    def test_full(self, full):
        c, h = full["c"], full["h"]
        s = c.post("/api/evangelism/strategies", json={"name": f"S-{uuid.uuid4().hex[:6]}"}, headers=h).json()
        assert _ok(c.get(f"/api/evangelism/analytics/strategy/{s['id']}/full", headers=h).status_code)
    def test_follow_up(self, full):
        assert full["c"].get("/api/evangelism/follow-up/pending", headers=full["h"]).status_code in (200, 404)
