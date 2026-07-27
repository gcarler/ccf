"""
Tests for finance.py, dashboard.py, public.py
"""
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
    admin, _, _ = _seed_admin(db_session, email="cov2@test.com")
    headers = _auth_headers(client, email="cov2@test.com", password="testpass123")
    return {"c": client, "h": headers}


class TestFinance:
    def test_summary(self, full):
        assert _ok(full["c"].get("/api/finance/summary", headers=full["h"]).status_code)
    def test_funds(self, full):
        assert _ok(full["c"].get("/api/finance/funds", headers=full["h"]).status_code)
    def test_transactions(self, full):
        assert _ok(full["c"].get("/api/finance/transactions", headers=full["h"]).status_code)
    def test_impact(self, full):
        assert _ok(full["c"].get("/api/finance/impact", headers=full["h"]).status_code)
    def test_list_funds_admin(self, full):
        assert _ok(full["c"].get("/api/finance/admin/funds", headers=full["h"]).status_code)
    def test_create_fund(self, full):
        assert _ok(full["c"].post("/api/finance/admin/funds",
            json={"name": f"F-{uuid.uuid4().hex[:6]}"}, headers=full["h"]).status_code)
    def test_create_and_update_fund(self, full):
        r = full["c"].post("/api/finance/admin/funds", json={"name": f"FU-{uuid.uuid4().hex[:6]}"}, headers=full["h"])
        assert _ok(full["c"].patch(f"/api/finance/admin/funds/{r.json()['fund_id']}",
            json={"name": "Upd"}, headers=full["h"]).status_code)
    def test_delete_fund(self, full):
        r = full["c"].post("/api/finance/admin/funds", json={"name": f"FD-{uuid.uuid4().hex[:6]}"}, headers=full["h"])
        assert full["c"].delete(f"/api/finance/admin/funds/{r.json()['fund_id']}", headers=full["h"]).status_code == 204
    def test_update_fund_not_found(self, full):
        assert full["c"].patch(f"/api/finance/admin/funds/{uuid.uuid4()}", json={"name": "X"},
            headers=full["h"]).status_code == 404
    def test_delete_fund_not_found(self, full):
        assert full["c"].delete(f"/api/finance/admin/funds/{uuid.uuid4()}",
            headers=full["h"]).status_code == 404
    def test_donation_no_fund(self, full):
        assert full["c"].post("/api/finance/donations",
            json={"amount": 100, "donation_type": "Ofrenda", "fund_id": str(uuid.uuid4())},
            headers=full["h"]).status_code == 404


class TestDashboard:
    def test_list_modules(self, full):
        assert _ok(full["c"].get("/api/dashboard/modules/list", headers=full["h"]).status_code)
    def test_crm(self, full):
        assert _ok(full["c"].get("/api/dashboard/crm", headers=full["h"]).status_code)
    def test_academy(self, full):
        assert _ok(full["c"].get("/api/dashboard/academy", headers=full["h"]).status_code)
    def test_finance(self, full):
        assert _ok(full["c"].get("/api/dashboard/finance", headers=full["h"]).status_code)
    def test_agenda(self, full):
        assert _ok(full["c"].get("/api/dashboard/agenda", headers=full["h"]).status_code)
    def test_cms(self, full):
        assert _ok(full["c"].get("/api/dashboard/cms", headers=full["h"]).status_code)
    def test_projects(self, full):
        assert _ok(full["c"].get("/api/dashboard/projects", headers=full["h"]).status_code)
    def test_unknown(self, full):
        assert full["c"].get("/api/dashboard/unknown", headers=full["h"]).status_code == 404


class TestPublic:
    def test_register_not_found(self, full):
        assert full["c"].post("/api/register",
            json={"event_id": str(uuid.uuid4()), "first_name": "T", "last_name": "U"},
            headers=full["h"]).status_code == 404
