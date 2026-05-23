"""Tests que verifican que la configuración rechaza defaults inseguros en producción."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from backend.core.config import Settings


class TestProductionSecurityDefaults:
    """Settings debe rechazar configuraciones inseguras en modo producción."""

    def test_production_rejects_default_secret_key(self):
        with pytest.raises(ValueError, match="SECRET_KEY"):
            Settings(_env_file=None, environment="production")

    def test_production_rejects_empty_encryption_key(self):
        with pytest.raises(ValueError, match="ENCRYPTION_KEY"):
            Settings(
                _env_file=None,
                environment="production",
                secret_key="strong-secret-key-here",
            )

    def test_production_rejects_sqlite(self):
        with pytest.raises(ValueError, match="SQLite"):
            Settings(
                _env_file=None,
                environment="production",
                secret_key="strong-secret-key-here",
                encryption_key="strong-encryption-key-here",
                database_url="sqlite:///./test.db",
            )

    def test_production_allows_localhost_redis(self):
        """Redis restriction was removed — production now allows localhost Redis (optional with MemoryRedis fallback)."""
        s = Settings(
            _env_file=None,
            environment="production",
            secret_key="strong-secret-key-here",
            encryption_key="strong-encryption-key-here",
            database_url="postgresql://user:pass@host:5432/db",
            redis_url="redis://localhost:6379/0",
        )
        assert s.redis_url == "redis://localhost:6379/0"

    def test_production_auto_enables_secure_cookie(self):
        s = Settings(
            _env_file=None,
            environment="production",
            secret_key="strong-secret-key-here",
            encryption_key="strong-encryption-key-here",
            database_url="postgresql://user:pass@host:5432/db",
            redis_url="redis://redis:6379/0",
        )
        assert s.access_token_cookie_secure is True


class TestTokenExpiry:
    """Los tokens deben tener expiración razonable."""

    def test_access_token_default_is_sane(self):
        s = Settings(_env_file=None)
        assert s.access_token_expire_minutes <= 60, (
            f"Access token expiry {s.access_token_expire_minutes}min excede el máximo de 60min"
        )

    def test_refresh_token_default_is_sane(self):
        s = Settings(_env_file=None)
        assert s.refresh_token_expire_days <= 180, (
            f"Refresh token expiry {s.refresh_token_expire_days}d excede el máximo de 180d"
        )

    def test_rejects_zero_access_token_expiry(self):
        with pytest.raises(ValueError):
            Settings(_env_file=None, access_token_expire_minutes=0)

    def test_rejects_zero_refresh_token_expiry(self):
        with pytest.raises(ValueError):
            Settings(_env_file=None, refresh_token_expire_days=0)
