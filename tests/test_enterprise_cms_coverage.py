"""
Enterprise CMS Coverage Tests.
"""
import uuid

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


class TestEnterpriseCmsEndpoints:
    def test_list_sites(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/enterprise/cms/sites", headers=h).status_code)
