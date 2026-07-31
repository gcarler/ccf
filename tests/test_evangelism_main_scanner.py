"""Tests for evangelism.py — scanner token generation and validation."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from backend import models
from backend.api.evangelism import (
    _generate_scanner_token,
    _get_scoped_scanner_persona,
)
from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin


def _ok(status):
    return status in (200, 201, 204)


@pytest.fixture
def full(client, db_session):
    admin, _, _ = _seed_admin(db_session, email="evan@test.com")
    headers = _auth_headers(client, email="evan@test.com", password="testpass123")
    sede = db_session.query(models.Sede).first()
    return {"c": client, "h": headers, "s": sede}


# ── Unit: _get_scoped_scanner_persona ─────────────────────────────────────────


class TestGetScopedScannerPersona:
    def test_found(self, db_session, full):
        p = models.Persona(id=uuid.uuid4(), first_name="Scan", last_name="Test", sede_id=full["s"].id)
        db_session.add(p)
        db_session.commit()

        # Get current user
        user = db_session.query(models.Usuario).filter_by(email="evan@test.com").first()
        result = _get_scoped_scanner_persona(p.id, db_session, user)
        assert result.id == p.id

    def test_not_found(self, db_session, full):
        from fastapi import HTTPException

        user = db_session.query(models.Usuario).filter_by(email="evan@test.com").first()
        with pytest.raises(HTTPException) as exc:
            _get_scoped_scanner_persona(uuid.uuid4(), db_session, user)
        assert exc.value.status_code == 404


# ── Unit: _generate_scanner_token ─────────────────────────────────────────────


class TestGenerateScannerToken:
    def test_generates_token(self, db_session, full):
        p = models.Persona(id=uuid.uuid4(), first_name="Tok", last_name="Test", sede_id=full["s"].id)
        db_session.add(p)
        db_session.commit()

        result = _generate_scanner_token(p, db_session)
        assert "token" in result
        assert result["token"].startswith("CCF-PER-")
        assert p.scanner_token_hash is not None


# ── Integration: API endpoints ────────────────────────────────────────────────


class TestScannerGenerate:
    def test_generate(self, full, db_session):
        c, h, s = full["c"], full["h"], full["s"]
        p = models.Persona(id=uuid.uuid4(), first_name="Gen", last_name="Test", sede_id=s.id)
        db_session.add(p)
        db_session.commit()

        resp = c.post(f"/api/evangelism/scanner/generate/{p.id}", headers=h)
        assert _ok(resp.status_code), f"generate: {resp.status_code} {resp.text[:200]}"
        data = resp.json()
        assert data["token"].startswith("CCF-PER-")
        assert "expires_at" in data

    def test_generate_cross_sede_404(self, full, db_session):
        """Persona from another sede returns 404."""
        c, h, s = full["c"], full["h"], full["s"]
        other = models.Sede(id=uuid.uuid4(), nombre="Other", ciudad="Other", es_activa=True)
        db_session.add(other)
        db_session.flush()
        p = models.Persona(id=uuid.uuid4(), first_name="Cross", last_name="Test", sede_id=other.id)
        db_session.add(p)
        db_session.commit()

        resp = c.post(f"/api/evangelism/scanner/generate/{p.id}", headers=h)
        assert resp.status_code == 404


class TestScannerValidate:
    def test_validate_valid_token(self, full, db_session):
        """Full flow: generate -> validate."""
        c, h, s = full["c"], full["h"], full["s"]
        p = models.Persona(id=uuid.uuid4(), first_name="Val", last_name="Test", sede_id=s.id, church_role="miembro")
        db_session.add(p)
        db_session.commit()

        # Generate token
        gen = c.post(f"/api/evangelism/scanner/generate/{p.id}", headers=h).json()
        token = gen["token"]

        # Validate token
        resp = c.post(f"/api/evangelism/scanner/validate/{token}", headers=h)
        assert _ok(resp.status_code), f"validate: {resp.status_code} {resp.text[:200]}"
        data = resp.json()
        assert data["valid"] is True

    def test_validate_invalid_prefix(self, full):
        """Invalid token prefix -> 400."""
        resp = full["c"].post("/api/evangelism/scanner/validate/BAD-PREFIX-xxx", headers=full["h"])
        assert resp.status_code == 400

    def test_validate_malformed_short(self, full):
        """Too short token -> 400."""
        resp = full["c"].post("/api/evangelism/scanner/validate/CCF-PER-short", headers=full["h"])
        assert resp.status_code == 400

    def test_validate_wrong_separator(self, full):
        """Missing separator after persona_id -> 400."""
        # CCF-PER-{uuid} (no separator after uuid before secret)
        resp = full["c"].post(
            "/api/evangelism/scanner/validate/CCF-PER-" + str(uuid.uuid4()).replace("-", "") + "secret",
            headers=full["h"],
        )
        assert resp.status_code in (400, 404)

    def test_validate_expired_token(self, full, db_session):
        """Expired scanner token -> 403."""
        c, h, s = full["c"], full["h"], full["s"]
        p = models.Persona(id=uuid.uuid4(), first_name="Exp", last_name="Test", sede_id=s.id)
        db_session.add(p)
        db_session.commit()

        # Set an expired token hash
        secret = secrets.token_hex(16)
        p.scanner_token_hash = hashlib.sha256(secret.encode()).hexdigest()
        p.scanner_token_expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        db_session.commit()

        token = f"CCF-PER-{p.id}-{secret}"
        resp = c.post(f"/api/evangelism/scanner/validate/{token}", headers=h)
        assert resp.status_code == 403

    def test_validate_no_token_set(self, full, db_session):
        """Persona without token -> 403."""
        c, h, s = full["c"], full["h"], full["s"]
        p = models.Persona(id=uuid.uuid4(), first_name="NoTok", last_name="Test", sede_id=s.id)
        db_session.add(p)
        db_session.commit()

        # Generate a token as if we had one
        secret = secrets.token_hex(16)
        token = f"CCF-PER-{p.id}-{secret}"

        resp = c.post(f"/api/evangelism/scanner/validate/{token}", headers=h)
        assert resp.status_code == 403

    def test_validate_wrong_secret(self, full, db_session):
        """Wrong secret hash -> 403."""
        c, h, s = full["c"], full["h"], full["s"]
        p = models.Persona(id=uuid.uuid4(), first_name="Wrng", last_name="Test", sede_id=s.id)
        db_session.add(p)
        db_session.commit()

        secret = secrets.token_hex(16)
        wrong_secret = secrets.token_hex(16)
        p.scanner_token_hash = hashlib.sha256(wrong_secret.encode()).hexdigest()
        p.scanner_token_expires_at = datetime.now(timezone.utc) + timedelta(days=365)
        db_session.commit()

        token = f"CCF-PER-{p.id}-{secret}"
        resp = c.post(f"/api/evangelism/scanner/validate/{token}", headers=h)
        assert resp.status_code == 403
