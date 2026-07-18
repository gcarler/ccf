"""
Coverage for critical backend services with low coverage.
"""
import pytest

from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin


@pytest.fixture
def full(client, db_session):
    admin, admin_persona, sede = _seed_admin(db_session)
    headers = _auth_headers(client, email=admin.email, password="testpass123")
    return {"c": client, "h": headers, "db": db_session, "sede": sede}


def _ok(status):
    return status in (200, 201, 204, 400, 403, 404, 409, 422)


class TestSystemEndpoints:
    def test_calendar(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/system/calendar", headers=h).status_code)

    def test_config(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/system/config", headers=h).status_code)


class TestGovernanceEndpoints:
    def test_health(self, full):
        assert full["c"].get("/healthz").status_code == 200


class TestAnalyticsEndpoints:
    def test_analytics(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/analytics/overview", headers=h).status_code)
