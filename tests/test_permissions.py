from fastapi import Depends, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend import models
from backend.auth import require_module_access
from backend.core.database import get_db
from backend.core.permissions import (
    _has_permission,
    expand_module_permissions,
    get_user_effective_permissions,
    normalize_role,
)
from backend.core.security import get_password_hash


def seed_user(
    db_session,
    email="user@test.com",
    password="secret123",
    role="estudiante",
    role_obj=None,
):
    user = models.User(
        username=f"user_{email.split('@')[0]}",
        email=email,
        password_hash=get_password_hash(password),
        role=role,
        is_active=True,
    )
    if role_obj:
        user.role_id = role_obj.role_id
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def create_role(db_session, name="Lector", permissions=None):
    role = models.Role(name=name, permissions=permissions or [])
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)
    return role


def _auth_header(client, email="user@test.com", password="secret123"):
    resp = client.post(
        "/api/auth/login",
        data={"username": email, "password": password, "grant_type": "password"},
    )
    data = resp.json()
    return {"Authorization": f"Bearer {data['access_token']}"}


# ── _has_permission unit tests ──────────────────────────────────────────


def test_admin_bypass():
    assert _has_permission("admin", set(), "crm:manage") is True
    assert _has_permission("admin", {}, "system:config") is True


def test_direct_permission_match():
    assert _has_permission("estudiante", {"academy:read"}, "academy:read") is True


def test_missing_permission():
    assert _has_permission("estudiante", {"academy:read"}, "crm:manage") is False


def test_hierarchy_manage_implies_edit():
    assert _has_permission("estudiante", {"crm:manage"}, "crm:edit") is True


def test_hierarchy_manage_implies_read():
    assert _has_permission("estudiante", {"crm:manage"}, "crm:read") is True


def test_hierarchy_edit_implies_read():
    assert _has_permission("estudiante", {"crm:edit"}, "crm:read") is True


def test_hierarchy_edit_does_not_imply_manage():
    assert _has_permission("estudiante", {"crm:edit"}, "crm:manage") is False


def test_hierarchy_read_does_not_imply_edit():
    assert _has_permission("estudiante", {"crm:read"}, "crm:edit") is False


def test_expand_module_permissions_manage():
    perms = expand_module_permissions("crm", "manage")
    assert "crm:read" in perms
    assert "crm:edit" in perms
    assert "crm:manage" in perms


def test_expand_module_permissions_read():
    perms = expand_module_permissions("crm", "read")
    assert "crm:read" in perms
    assert "crm:edit" not in perms


def test_normalize_role_aliases():
    assert normalize_role("admin") == "admin"
    assert normalize_role("student") == "estudiante"
    assert normalize_role("lider") == "coordinador"


# ── get_user_effective_permissions tests ────────────────────────────────


def test_admin_gets_all_permissions(db_session):
    user = seed_user(db_session, role="admin")
    perms = get_user_effective_permissions(db_session, user)
    assert "crm:manage" in perms
    assert "system:config" in perms
    assert "academy:manage" in perms


def test_role_based_permissions(db_session):
    role = create_role(db_session, permissions=["crm:read", "academy:study"])
    user = seed_user(db_session, role="lector", role_obj=role)
    perms = get_user_effective_permissions(db_session, user)
    assert perms.get("crm:read") == "allow"
    assert perms.get("academy:study") == "allow"
    assert perms.get("crm:manage") is None


def test_fallback_to_default_role(db_session):
    user = seed_user(db_session, role="estudiante")
    perms = get_user_effective_permissions(db_session, user)
    assert perms.get("academy:study") == "allow"
    assert perms.get("profile:manage") == "allow"
    assert perms.get("crm:read") is None  # estudiante no tiene CRM


# ── API-level require_module_access tests ───────────────────────────────


def test_access_with_correct_permission(client: TestClient, db_session):
    role = create_role(db_session, permissions=["crm:read"])
    user = seed_user(db_session, role="lector", role_obj=role)
    user.role = "lector"
    db_session.commit()

    headers = _auth_header(client)
    # GET /members list requires crm:read (via require_pastor_or_admin) in members.py
    # Actually, /members requires pastor_or_admin. Let's test via a simpler endpoint.
    # GET /members/me requires crm:read
    resp = client.get("/api/crm/members/me", headers=headers)
    assert resp.status_code == 200


def test_access_without_permission_returns_403(client: TestClient, db_session):
    role = create_role(db_session, permissions=["academy:study"])
    user = seed_user(db_session, role="estudiante", role_obj=role)
    user.role = "estudiante"
    db_session.commit()

    headers = _auth_header(client)
    # GET /members/me requires crm:read — user only has academy:study
    resp = client.get("/api/crm/members/me", headers=headers)
    assert resp.status_code == 403


def test_unauthenticated_returns_401(client: TestClient, db_session):
    resp = client.get("/api/crm/members/me")
    assert resp.status_code == 401


def test_inactive_user_blocked(client: TestClient, db_session):
    user = seed_user(db_session)
    user.is_active = False
    db_session.commit()

    # Inactive users are now blocked at login (more secure)
    resp = client.post(
        "/api/auth/login",
        data={"username": "user@test.com", "password": "secret123", "grant_type": "password"},
    )
    assert resp.status_code == 401
    assert "desactivada" in resp.json()["detail"].lower()
