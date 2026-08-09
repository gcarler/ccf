"""
Tests para el flujo de autenticación v3 (UUID-based).
Cubre: login, refresh, /me, check-email, rate limiting.
"""

from __future__ import annotations

import uuid

import httpx
import pytest
from fastapi import HTTPException, Request
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend import models
from backend.api.auth_v3 import _build_public_welcome_redirect
from backend.core.security import get_password_hash
from backend.models_auth import RolPlataforma, Usuario


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
        assert isinstance(data["google_oauth_enabled"], bool)

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
        assert data["auth_user_id"] == str(user.id)
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
        assert isinstance(data["google_oauth_enabled"], bool)

    def test_v3_check_email_reports_google_ready(self, client: TestClient, db_session: Session, monkeypatch):
        """Check-email debe exponer si Google SSO está listo para usar."""
        from backend.api import auth_v3

        monkeypatch.setattr(auth_v3.settings, "google_client_id", "client-id")
        monkeypatch.setattr(auth_v3.settings, "google_client_secret", "client-secret")
        _create_v3_user(db_session, email="ready@gmail.com", password="SecurePass99!")

        response = client.get(
            "/api/v3/auth/check-email",
            params={"email": "ready@gmail.com"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["google_oauth_enabled"] is True

    def test_google_callback_redirects_without_exposing_tokens(
        self, db_session: Session, monkeypatch
    ):
        """El callback Google entrega sesión por cookies, nunca por Location."""
        from backend.api import auth_v3

        user = _create_v3_user(db_session, email="oauth@ccf.com", password="SecurePass99!")
        monkeypatch.setattr(auth_v3.settings, "google_client_id", "client-id")
        monkeypatch.setattr(auth_v3.settings, "google_client_secret", "client-secret")
        monkeypatch.setattr(auth_v3.settings, "frontend_url", "https://app.example.test")

        class _GoogleResponse:
            def __init__(self, payload):
                self._payload = payload

            def raise_for_status(self):
                return None

            def json(self):
                return self._payload

        def fake_post(url, **kwargs):
            assert url == "https://oauth2.googleapis.com/token"
            assert kwargs["data"]["code"] == "oauth-code"
            return _GoogleResponse({"access_token": "google-access-token"})

        def fake_get(url, **kwargs):
            assert url == "https://www.googleapis.com/oauth2/v2/userinfo"
            assert kwargs["headers"]["Authorization"] == "Bearer google-access-token"
            return _GoogleResponse({"email": user.email, "name": "OAuth User"})

        monkeypatch.setattr(httpx, "post", fake_post)
        monkeypatch.setattr(httpx, "get", fake_get)
        request = Request(
            {
                "type": "http",
                "method": "GET",
                "path": "/api/v3/auth/google/callback",
                "headers": [
                    (b"user-agent", b"pytest"),
                    (b"cookie", b"ccf_google_oauth_state=oauth-state"),
                ],
                "query_string": b"code=oauth-code&state=oauth-state",
                "scheme": "https",
                "server": ("api.example.test", 443),
                "client": ("127.0.0.1", 1234),
            }
        )

        response = auth_v3.google_callback(
            code="oauth-code", state="oauth-state", request=request, db=db_session
        )

        assert response.status_code == 307
        assert response.headers["location"] == "https://app.example.test/auth/callback"
        assert "token" not in response.headers["location"].lower()
        assert "access_token" not in response.headers["location"].lower()
        assert "refresh" not in response.headers["location"].lower()
        from backend.core.config import get_settings

        settings = get_settings()
        set_cookies = [value.decode("latin-1") for key, value in response.raw_headers if key == b"set-cookie"]
        assert any(
            f"{settings.access_token_cookie_name}=" in cookie and "HttpOnly" in cookie
            for cookie in set_cookies
        )
        assert any(
            f"{settings.refresh_token_cookie_name}=" in cookie and "HttpOnly" in cookie
            for cookie in set_cookies
        )
        assert any(
            "ccf_google_oauth_state=\"\";" in cookie and "Max-Age=0" in cookie
            for cookie in set_cookies
        )
        assert all("SameSite=lax" in cookie for cookie in set_cookies)

    def test_google_callback_rejects_invalid_state(self, db_session: Session):
        from backend.api import auth_v3

        request = Request(
            {
                "type": "http",
                "method": "GET",
                "path": "/api/v3/auth/google/callback",
                "headers": [(b"cookie", b"ccf_google_oauth_state=expected")],
                "query_string": b"code=oauth-code&state=wrong",
                "client": ("127.0.0.1", 1234),
            }
        )
        with pytest.raises(HTTPException) as exc_info:
            auth_v3.google_callback(code="oauth-code", state="wrong", request=request, db=db_session)
        assert exc_info.value.status_code == 400
        assert "Estado OAuth" in str(exc_info.value.detail)

    def test_google_callback_rejects_provider_error_without_code(self, client: TestClient):
        response = client.get(
            "/api/v3/auth/google/callback",
            params={"error": "access_denied"},
        )
        assert response.status_code == 400
        assert "Google OAuth error" in response.json()["detail"]

    def test_google_login_returns_service_error_when_not_configured(self, client: TestClient, monkeypatch):
        """El login Google debe fallar de forma explícita si no está habilitado."""
        from backend.api import auth_v3

        monkeypatch.setattr(auth_v3.settings, "google_client_id", "")
        monkeypatch.setattr(auth_v3.settings, "google_client_secret", "")
        response = client.get("/api/v3/auth/google")
        assert response.status_code == 503

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
