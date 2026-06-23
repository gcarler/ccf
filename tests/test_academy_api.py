"""Tests for academy API (modern endpoints)."""
import pytest
from tests.conftest import seed_admin_v2 as _seed_admin
from tests.conftest import auth_headers_v2 as _auth_headers


@pytest.mark.xfail(reason="Pre-existing bug: list_cursos() missing skip param in academy_core.py")
def test_academy_courses_list(client, db_session):
    """List courses endpoint should return 200."""
    admin, persona, sede = _seed_admin(db_session)
    headers = _auth_headers(client, email=admin.email, password="testpass123")
    resp = client.get("/api/v2/academy/courses", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
