"""
Tests for workspace_compliance.py — mounted at /api/workspace.
"""
from __future__ import annotations

import pytest

from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin


def _ok(status):
    return status in (200, 201, 204)


@pytest.fixture
def full(client, db_session):
    admin, _, _ = _seed_admin(db_session, email="comp@test.com")
    headers = _auth_headers(client, email="comp@test.com", password="testpass123")
    return {"c": client, "h": headers}


class TestCompliance:
    def test_snapshot(self, full):
        assert _ok(full["c"].get("/api/workspace/flags/compliance/snapshot", headers=full["h"]).status_code)
    def test_snapshot_download(self, full):
        assert _ok(full["c"].get("/api/workspace/flags/compliance/snapshot?download=true", headers=full["h"]).status_code)
    def test_snapshot_no_record(self, full):
        assert _ok(full["c"].get("/api/workspace/flags/compliance/snapshot?record=false", headers=full["h"]).status_code)
    def test_get_policy(self, full):
        assert _ok(full["c"].get("/api/workspace/flags/compliance/policy", headers=full["h"]).status_code)
    def test_update_policy(self, full):
        assert _ok(full["c"].put("/api/workspace/flags/compliance/policy",
            json={"critical_feature_flags": ["feat_x"]}, headers=full["h"]).status_code)
    def test_delete_suppression_not_found(self, full):
        assert full["c"].delete("/api/workspace/flags/compliance/suppressions/nonexistent",
            headers=full["h"]).status_code == 404
    def test_history(self, full):
        assert _ok(full["c"].get("/api/workspace/flags/compliance/history", headers=full["h"]).status_code)
    def test_history_invalid_since(self, full):
        assert full["c"].get("/api/workspace/flags/compliance/history?since=bad-date",
            headers=full["h"]).status_code == 422
    def test_weekly_summary(self, full):
        assert _ok(full["c"].get("/api/workspace/flags/compliance/history/weekly-summary", headers=full["h"]).status_code)
    def test_history_item_not_found(self, full):
        assert full["c"].get("/api/workspace/flags/compliance/history/nonexistent-id",
            headers=full["h"]).status_code == 404
    def test_compare(self, full):
        assert _ok(full["c"].get("/api/workspace/flags/compliance/compare", headers=full["h"]).status_code)
    def test_drift(self, full):
        assert _ok(full["c"].get("/api/workspace/flags/compliance/drift", headers=full["h"]).status_code)
    def test_cleanup(self, full):
        assert _ok(full["c"].post("/api/workspace/flags/compliance/history/cleanup",
            json={"retain_days": 90}, headers=full["h"]).status_code)
