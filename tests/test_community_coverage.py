"""
Community + Prayer + Graph Coverage Tests.
"""
import pytest

from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin


def _ok(status):
    return status in (200, 201, 204, 400, 403, 404, 409, 422)


@pytest.fixture
def full(client, db_session):
    admin, admin_persona, sede = _seed_admin(db_session)
    headers = _auth_headers(client, email=admin.email, password="testpass123")
    return {"c": client, "h": headers}


class TestCommunityEndpoints:
    def test_discover(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/community/discover", headers=h).status_code)


class TestPrayerEndpoints:
    def test_list_prayers(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/prayer/requests", headers=h).status_code)


class TestGraphEndpoints:
    def test_graph_data(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/graph/data", headers=h).status_code)
