"""
Tests for conftest.py helper functions.
Ensures seed_admin, auth_headers, seed_user_with_role work correctly
and cover edge cases (custom sede_id, custom permissions, etc.).
"""
import uuid

import pytest

from tests.conftest import seed_admin, seed_user_with_role, auth_headers


class TestSeedAdmin:
    def test_seed_admin_returns_tuple(self, db_session):
        user, persona, sede = seed_admin(db_session)
        assert user is not None
        assert persona is not None
        assert sede is not None
        assert user.id == persona.id  # Auth v3 contract
        assert persona.sede_id == sede.id

    def test_seed_admin_custom_email(self, db_session):
        user, persona, sede = seed_admin(db_session, email="custom@test.com")
        assert user.email == "custom@test.com"
        assert persona.email == "custom@test.com"

    def test_seed_admin_creates_valid(self, db_session):
        user1, _, _ = seed_admin(db_session)
        assert user1.id is not None
        assert user1.is_active is True

    def test_seed_admin_sede_has_name(self, db_session):
        _, _, sede = seed_admin(db_session)
        assert sede.nombre is not None


class TestAuthHeaders:
    def test_auth_headers_returns_bearer(self, db_session, client):
        seed_admin(db_session, email="header@test.com", password="testpass123")
        headers = auth_headers(client, email="header@test.com", password="testpass123")
        assert "Authorization" in headers
        assert headers["Authorization"].startswith("Bearer ")

    def test_auth_headers_invalid_password(self, db_session, client):
        seed_admin(db_session, email="badpw@test.com", password="correctpass")
        with pytest.raises(AssertionError):
            auth_headers(client, email="badpw@test.com", password="wrongpass")

    def test_auth_headers_default_admin(self, db_session, client):
        seed_admin(db_session)
        headers = auth_headers(client)
        assert "Authorization" in headers


class TestSeedUserWithRole:
    def test_seed_user_default(self, db_session):
        user, persona, sede = seed_user_with_role(db_session)
        assert user is not None
        assert persona is not None
        assert sede is not None
        assert user.username == "user"

    def test_seed_user_custom_role(self, db_session):
        user, persona, sede = seed_user_with_role(
            db_session, role_name="EDITOR", email="editor@test.com"
        )
        assert user.rol_plataforma.nombre == "EDITOR"

    def test_seed_user_with_sede_id(self, db_session):
        from backend import models
        custom_sede = models.Sede(
            id=uuid.uuid4(), nombre="Custom Sede", ciudad="Medellin", es_activa=True
        )
        db_session.add(custom_sede)
        db_session.commit()

        user, persona, sede = seed_user_with_role(
            db_session, role_name="GESTOR", email="gestor@test.com",
            sede_id=custom_sede.id,
        )
        assert sede.id == custom_sede.id
        assert persona.sede_id == custom_sede.id

    def test_seed_user_with_custom_permissions(self, db_session):
        user, persona, sede = seed_user_with_role(
            db_session, role_name="CUSTOM_ROLE", email="custom@test.com",
            permisos={"custom:read": "allow", "custom:write": "allow"},
        )
        rol = user.rol_plataforma
        assert rol.permisos.get("custom:read") == "allow"

    def test_seed_user_nonexistent_sede_creates(self, db_session):
        new_sede_id = uuid.uuid4()
        user, persona, sede = seed_user_with_role(
            db_session, role_name="LECTOR", email="lector@test.com",
            sede_id=new_sede_id,
        )
        assert sede.id == new_sede_id
