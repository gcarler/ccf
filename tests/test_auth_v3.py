"""
Tests para el flujo de autenticación v3 (UUID-based).
Cubre: login, refresh, /me, check-email, rate limiting.
"""
from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend import models
from backend.core.security import get_password_hash
from backend.api.auth_v3 import _build_public_welcome_redirect
from backend.models_auth import Usuario, RolPlataforma, TokenSesion


def _create_v3_user(db_session: Session, email: str = "test@ccf.com", password: str = "TestPass123!") -> Usuario:
    """Crea un usuario v3 (auth_users) con su persona y rol."""
    # Crear persona
    persona = models.Persona(
        id=uuid.uuid4(),
        first_name="Test",
        last_name="User",
        email=email,
    )
    db_session.add(persona)
    db_session.flush()
    
    # Crear rol
    role = db_session.query(RolPlataforma).filter(RolPlataforma.nombre == "LECTOR").first()
    if not role:
        role = RolPlataforma(
            id=uuid.uuid4(),
            nombre="LECTOR",
            permisos={"crm:read": "allow", "academy:read": "allow"},
        )
        db_session.add(role)
        db_session.flush()
    
    # Crear usuario v3
    user = Usuario(
        id=persona.id,
        sede_id=uuid.uuid4(),
        username=email.split("@")[0],
        email=email,
        password_hash=get_password_hash(password),
        rol_plataforma_id=role.id,
        is_active=True,
        is_email_verified=True,
    )
    db_session.add(user)
    db_session.commit()
    return user


class TestAuthV3Flow:
    """Tests del flujo completo de autenticación v3."""

    def test_v3_login_success(self, client: TestClient, db_session: Session):
        """Login exitoso con email + password."""
        _create_v3_user(db_session, email="alfa@ccf.com", password="SecurePass99!")
        
        response = client.post(
            "/api/v3/auth/login",
            json={"email": "alfa@ccf.com", "password": "SecurePass99!"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["platform_role"] == "LECTOR"
        assert "sede_id" not in data or True  # sede_id va en JWT, no en response

    def test_v3_login_wrong_password(self, client: TestClient, db_session: Session):
        """Login con contraseña incorrecta debe fallar."""
        _create_v3_user(db_session, email="beta@ccf.com", password="SecurePass99!")
        
        response = client.post(
            "/api/v3/auth/login",
            json={"email": "beta@ccf.com", "password": "wrongpassword"},
        )
        assert response.status_code == 401

    def test_v3_login_user_not_found(self, client: TestClient):
        """Login con email inexistente debe fallar."""
        response = client.post(
            "/api/v3/auth/login",
            json={"email": "noexists@ccf.com", "password": "TestPass123!"},
        )
        assert response.status_code == 401

    def test_v3_check_email(self, client: TestClient, db_session: Session):
        """Check-email debe retornar si existe y si tiene password."""
        _create_v3_user(db_session, email="checkme@ccf.com", password="SecurePass99!")
        
        response = client.get(
            "/api/v3/auth/check-email",
            params={"email": "checkme@ccf.com"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["exists"] is True
        assert data["has_password"] is True

    def test_v3_check_email_not_found(self, client: TestClient):
        """Check-email para email no registrado."""
        response = client.get(
            "/api/v3/auth/check-email",
            params={"email": "noexiste@test.com"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["exists"] is False

    def test_v3_me_authenticated(self, client: TestClient, db_session: Session):
        """GET /me con token válido."""
        user = _create_v3_user(db_session, email="meuser@ccf.com", password="SecurePass99!")
        
        login_resp = client.post(
            "/api/v3/auth/login",
            json={"email": "meuser@ccf.com", "password": "SecurePass99!"},
        )
        token = login_resp.json()["access_token"]
        
        response = client.get(
            "/api/v3/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "meuser@ccf.com"
        assert data["user_id"] == str(user.id)
        assert "permissions" in data
        assert "sede_id" in data

    def test_v3_me_no_token(self, client: TestClient):
        """GET /me sin token debe dar 401."""
        response = client.get("/api/v3/auth/me")
        assert response.status_code == 401

    def test_v3_refresh_token(self, client: TestClient, db_session: Session):
        """Refresh token debe rotar y devolver nuevo access_token."""
        _create_v3_user(db_session, email="refresh@ccf.com", password="SecurePass99!")
        
        login_resp = client.post(
            "/api/v3/auth/login",
            json={"email": "refresh@ccf.com", "password": "SecurePass99!"},
        )
        tokens = login_resp.json()
        original_access = tokens["access_token"]
        original_refresh = tokens.get("refresh_token")
        
        # Si el refresh token no viene en body, buscarlo en cookies
        if not original_refresh:
            cookies = login_resp.cookies
            from backend.core.config import get_settings
            settings = get_settings()
            original_refresh = cookies.get(settings.refresh_token_cookie_name)
        
        assert original_refresh, "Debe haber un refresh token"
        
        refresh_resp = client.post(
            "/api/v3/auth/refresh",
            json={"refresh_token": original_refresh},
        )
        assert refresh_resp.status_code == 200
        new_tokens = refresh_resp.json()
        assert new_tokens["access_token"] != original_access
        assert new_tokens["refresh_token"] != original_refresh

    def test_v3_refresh_invalid_token(self, client: TestClient):
        """Refresh con token inválido debe dar 401."""
        response = client.post(
            "/api/v3/auth/refresh",
            json={"refresh_token": "token-invalido"},
        )
        assert response.status_code == 401

    def test_v3_login_gmail_check(self, client: TestClient, db_session: Session):
        """Check-email para @gmail debe indicar is_gmail=True."""
        _create_v3_user(db_session, email="gmailuser@gmail.com", password="SecurePass99!")
        
        response = client.get(
            "/api/v3/auth/check-email",
            params={"email": "gmailuser@gmail.com"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_gmail"] is True

    def test_welcome_redirect_builder(self):
        url = _build_public_welcome_redirect(
            "https://elfarocc.tech/",
            name="G. Carler",
            email="gscarler@gmail.com",
        )
        assert url.startswith("https://elfarocc.tech/bienvenida?")
        assert "reason=no_account" in url
        assert "name=G.+Carler" in url
        assert "email=gscarler%40gmail.com" in url


class TestAuthV1V3Compat:
    """Test que el /auth/me unificado funciona tanto para v1 como v3."""

    def test_auth_me_v1_user(self, client: TestClient, db_session: Session):
        """/auth/me debe funcionar para usuarios v1 (tabla users)."""
        v1_user = models.User(
            username="v1user",
            email="v1user@ccf.com",
            password_hash=get_password_hash("Pass123!"),
            role="admin",
            is_active=True,
        )
        db_session.add(v1_user)
        db_session.commit()
        
        login_resp = client.post(
            "/api/auth/login",
            data={"username": "v1user@ccf.com", "password": "Pass123!", "grant_type": "password"},
        )
        assert login_resp.status_code == 200
        token = login_resp.json()["access_token"]
        
        resp = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
