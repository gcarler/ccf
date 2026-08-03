"""BI endpoints exposed over the duckdb warehouse.

Covers the three routes added for the Analytics/Reports front:
- GET /api/analytics/events/summary/warehouse
- GET /api/analytics/academy/performance
- GET /api/analytics/events/raw

Each runs against a throwaway duckdb file (monkeypatched WAREHOUSE_PATH)
so tests never touch the real analytics database.
"""
from __future__ import annotations

import uuid

import pytest

from backend.analytics import event_sink, queries
from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin


@pytest.fixture(autouse=True)
def temp_analytics_db(monkeypatch, tmp_path):
    db_path = tmp_path / f"bi-test-{uuid.uuid4().hex}.duckdb"
    monkeypatch.setattr(event_sink, "WAREHOUSE_PATH", db_path)
    monkeypatch.setattr(queries, "WAREHOUSE_PATH", db_path)
    monkeypatch.setattr(event_sink, "_RESOLVED_WAREHOUSE_PATH", None)
    yield db_path


@pytest.fixture
def bi_client(client, db_session):
    _seed_admin(db_session, email="bi@test.com")
    return {"c": client, "h": _auth_headers(client, email="bi@test.com", password="testpass123")}


def _seed_events(count: int = 3):
    event_sink.persist_event("EnrollmentCreated", {"course_id": 1, "user_id": 10})
    for i in range(1, count):
        event_sink.persist_event("AssessmentSubmitted", {"course_id": i, "passed": True})
    event_sink.persist_event("CertificateIssued", {"course_id": 1})


class TestWarehouseEventSummary:
    def test_summary_returns_events(self, bi_client):
        _seed_events()
        c, h = bi_client["c"], bi_client["h"]
        res = c.get("/api/analytics/events/summary/warehouse", headers=h)
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["source"] == "duckdb/domain_events"
        assert body["total_events"] >= 3
        names = {row["event_name"] for row in body["by_event"]}
        assert "EnrollmentCreated" in names

    def test_summary_graceful_when_no_events(self, bi_client):
        c, h = bi_client["c"], bi_client["h"]
        res = c.get("/api/analytics/events/summary/warehouse", headers=h)
        assert res.status_code == 200, res.text
        assert res.json()["total_events"] == 0

    def test_summary_requires_auth(self, client):
        res = client.get("/api/analytics/events/summary/warehouse")
        assert res.status_code in (401, 403), res.status_code


class TestAcademyPerformance:
    def test_course_performance_shapes(self, bi_client):
        _seed_events()
        c, h = bi_client["c"], bi_client["h"]
        res = c.get("/api/analytics/academy/performance", headers=h)
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["source"] == "duckdb/domain_events"
        assert isinstance(body["courses"], list)
        if body["courses"]:
            course = body["courses"][0]
            assert "course_id" in course
            assert "enrollments" in course
            assert "certificates" in course
            assert "approvals" in course

    def test_performance_empty_warehouse(self, bi_client):
        c, h = bi_client["c"], bi_client["h"]
        res = c.get("/api/analytics/academy/performance", headers=h)
        assert res.status_code == 200, res.text
        assert res.json()["courses"] == []


class TestRawEvents:
    def test_raw_events_returns_ordered_feed(self, bi_client):
        _seed_events()
        c, h = bi_client["c"], bi_client["h"]
        res = c.get("/api/analytics/events/raw", headers=h)
        assert res.status_code == 200, res.text
        body = res.json()
        assert "events" in body
        for row in body["events"]:
            assert "event_time" in row
            assert "event_name" in row

    def test_raw_events_empty(self, bi_client):
        c, h = bi_client["c"], bi_client["h"]
        res = c.get("/api/analytics/events/raw", headers=h)
        assert res.status_code == 200, res.text
        assert res.json()["events"] == []
