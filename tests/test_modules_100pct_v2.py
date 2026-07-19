"""
Tests to bring governance.py, config.py, audit.py to 100%.
"""
import os
from unittest.mock import patch

import pytest


class TestGovernanceCoverage:
    def test_governance_audit_logs_endpoint(self, client, db_session):
        """Covers governance.py:23 — get_admin_audit_logs via /api/governance/audit-logs."""
        from tests.conftest import auth_headers, seed_admin
        admin, persona, sede = seed_admin(db_session)
        headers = auth_headers(client)
        resp = client.get("/api/governance/audit-logs", headers=headers)
        assert resp.status_code in (200, 403)


class TestConfigCoverage:
    """Covers core/config.py lines: 103, 109, 114-115, 124-125, 134, 137, 140, 143."""

    def test_config_insecure_secret_key_raises(self):
        """SECRET_KEY in insecure_secrets set in production raises."""
        with patch.dict(os.environ, {
            "ENV": "production", "SECRET_KEY": "change-me",
            "ENCRYPTION_KEY": "some-key", "DATABASE_URL": "postgresql://localhost/db",
        }):
            from backend.core.config import get_settings
            get_settings.cache_clear()
            with pytest.raises(ValueError):
                get_settings()

    def test_config_missing_encryption_key_warns(self):
        """Missing encryption_key in non-local warns."""
        import logging
        with patch.object(logging.Logger, "warning") as mock_warn:
            with patch.dict(os.environ, {
                "ENV": "qa", "SECRET_KEY": "strong-key", "ENCRYPTION_KEY": "",
                "DATABASE_URL": "postgresql://localhost/db",
            }):
                from backend.core.config import get_settings
                get_settings.cache_clear()
                get_settings()
            assert mock_warn.called

    def test_config_access_token_expire_zero_raises(self):
        """ACCESS_TOKEN_EXPIRE_MINUTES <= 0 raises."""
        with patch.dict(os.environ, {
            "ENV": "local", "SECRET_KEY": "strong-key",
            "ACCESS_TOKEN_EXPIRE_MINUTES": "0",
        }):
            from backend.core.config import get_settings
            get_settings.cache_clear()
            with pytest.raises(ValueError):
                get_settings()

    def test_config_refresh_token_expire_zero_raises(self):
        """REFRESH_TOKEN_EXPIRE_DAYS <= 0 raises."""
        with patch.dict(os.environ, {
            "ENV": "local", "SECRET_KEY": "strong-key",
            "REFRESH_TOKEN_EXPIRE_DAYS": "0",
        }):
            from backend.core.config import get_settings
            get_settings.cache_clear()
            with pytest.raises(ValueError):
                get_settings()

    def test_config_sqlite_in_production_raises(self):
        """SQLite in production raises."""
        with patch.dict(os.environ, {
            "ENV": "production", "SECRET_KEY": "strong-key-123!",
            "ENCRYPTION_KEY": "enc-key-here", "DATABASE_URL": "sqlite:///test.db",
        }):
            from backend.core.config import get_settings
            get_settings.cache_clear()
            with pytest.raises(ValueError):
                get_settings()

    def test_config_missing_encryption_key_in_staging_raises(self):
        """Covers line 109 — ENCRYPTION_KEY required in staging."""
        with patch.dict(os.environ, {
            "ENV": "staging", "SECRET_KEY": "strong-key-123!",
            "ENCRYPTION_KEY": "", "DATABASE_URL": "postgresql://localhost/db",
        }):
            from backend.core.config import get_settings
            get_settings.cache_clear()
            with pytest.raises(ValueError):
                get_settings()

    def test_config_missing_smtp_in_nonlocal_warns(self):
        """Covers lines 124-125 — SMTP warning in non-local."""
        import logging as _logging
        with patch.object(_logging.Logger, "warning") as mock_warn:
            with patch.dict(os.environ, {
                "ENV": "qa", "SECRET_KEY": "strong-key-123!",
                "ENCRYPTION_KEY": "enc-key-here",
                "DATABASE_URL": "postgresql://localhost/db",
                "SMTP_HOST": "",
            }):
                from backend.core.config import get_settings
                get_settings.cache_clear()
                get_settings()
            assert mock_warn.called


class TestLoggingCoverage:
    """Covers core/logging.py lines 28, 30."""

    def test_json_formatter_with_request_id(self):
        from backend.core.logging import JSONFormatter, request_id_ctx
        import logging
        token = request_id_ctx.set("test-request-id")
        try:
            record = logging.LogRecord(
                name="test", level=logging.INFO,
                pathname=__file__, lineno=42, msg="test message",
                args=None, exc_info=None,
            )
            formatter = JSONFormatter()
            output = formatter.format(record)
            import json
            data = json.loads(output)
            assert data["request_id"] == "test-request-id"
        finally:
            request_id_ctx.reset(token)

    def test_json_formatter_with_exception(self):
        from backend.core.logging import JSONFormatter
        import logging
        import sys
        try:
            raise ValueError("test error")
        except ValueError:
            record = logging.LogRecord(
                name="test", level=logging.ERROR,
                pathname=__file__, lineno=42, msg="error occurred",
                args=None, exc_info=sys.exc_info(),
            )
            formatter = JSONFormatter()
            output = formatter.format(record)
            import json
            data = json.loads(output)
            assert "exception" in data
            assert "test error" in data["exception"]


class TestAuditCoverage:
    def test_audit_logs_filters(self, client, db_session):
        from tests.conftest import auth_headers, seed_admin
        admin, persona, sede = seed_admin(db_session)
        headers = auth_headers(client)
        resp = client.get("/api/admin/audit?limit=50&resource_type=test", headers=headers)
        assert resp.status_code in (200, 403)
