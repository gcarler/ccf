"""
Coverage tests for evangelism.py — target 90%+.
"""
import uuid
import hashlib
import secrets

import pytest

from backend import models
from backend.api.evangelism import (
    _get_scoped_scanner_persona,
    _generate_scanner_token,
)
from tests.conftest import seed_admin as _seed_admin, auth_headers as _auth_headers


@pytest.fixture
def full(client, db_session):
    admin, persona, sede = _seed_admin(db_session)
    headers = _auth_headers(client, email=admin.email, password="testpass123")
    return {
        "c": client, "h": headers, "db": db_session,
        "admin": admin, "persona": persona, "sede": sede,
    }


class TestScannerHelpers:
    """Covers helper functions."""

    def test_get_scoped_scanner_persona_found(self, full):
        p = _get_scoped_scanner_persona(full["persona"].id, full["db"], full["admin"])
        assert p.id == full["persona"].id

    def test_get_scoped_scanner_persona_not_found(self, full):
        with pytest.raises(Exception):
            _get_scoped_scanner_persona(uuid.uuid4(), full["db"], full["admin"])

    def test_generate_scanner_token_returns_dict(self, full):
        result = _generate_scanner_token(full["persona"], full["db"])
        assert "token" in result
        assert result["token"].startswith("CCF-PER-")
        assert "expires_at" in result

    def test_generate_scanner_token_saves_hash(self, full):
        _generate_scanner_token(full["persona"], full["db"])
        full["db"].refresh(full["persona"])
        assert full["persona"].scanner_token_hash is not None


class TestScannerEndpoints:
    """Covers the /scanner endpoints."""

    def test_generate_endpoint_success(self, full):
        c, h = full["c"], full["h"]
        resp = c.post(f"/api/evangelism/scanner/generate/{full['persona'].id}", headers=h)
        assert resp.status_code == 200
        data = resp.json()
        assert "token" in data
        assert data["token"].startswith("CCF-PER-")

    def test_generate_endpoint_not_found(self, full):
        c, h = full["c"], full["h"]
        resp = c.post(f"/api/evangelism/scanner/generate/{uuid.uuid4()}", headers=h)
        assert resp.status_code == 404

    def test_validate_endpoint_invalid_format(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/evangelism/scanner/validate/invalid", headers=h)
        assert resp.status_code == 400

    def test_validate_endpoint_malformed_token(self, full):
        c, h = full["c"], full["h"]
        resp = c.post(f"/api/evangelism/scanner/validate/CCF-PER-{uuid.uuid4()}-short", headers=h)
        assert resp.status_code in (400, 403, 404)

    def test_validate_endpoint_valid_token(self, full):
        # First generate a token
        c, h = full["c"], full["h"]
        gen = c.post(f"/api/evangelism/scanner/generate/{full['persona'].id}", headers=h)
        assert gen.status_code == 200
        token = gen.json()["token"]

        # Then validate it
        resp = c.post(f"/api/evangelism/scanner/validate/{token}", headers=h)
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is True
        assert data["persona_id"] == str(full["persona"].id)
