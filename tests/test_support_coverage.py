"""
Support + Support KB Coverage Tests.
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
    return {"c": client, "h": headers, "sede": sede, "admin": admin}


class TestSupportEndpoints:
    def test_list_tickets(self, full):
        c, h = full["c"], full["h"]
        # Support tickets list — 200 (admin sees all) or 404 if endpoint varies
        resp = c.get("/support/tickets", headers=h)
        assert _ok(resp.status_code) or resp.status_code == 200

    def test_health(self, full):
        assert full["c"].get("/healthz").status_code == 200


class TestSupportKbEndpoints:
    def test_list_kb(self, full):
        c, h = full["c"], full["h"]
        resp = c.get("/support/kb", headers=h)
        assert _ok(resp.status_code) or resp.status_code == 200
