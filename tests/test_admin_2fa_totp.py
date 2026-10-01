"""Unit and integration tests for Admin 2FA TOTP RFC 6238 authentication.

Covers:
1. Cryptographic Base32 secret generation.
2. Derivation of 6-digit numeric TOTP codes according to RFC 6238 / RFC 4226.
3. Temporal window tolerance coverage (+/- 1 step: T-1, T0, T+1, and boundary rejection at T-2, T+2).
4. Code format normalization (spaces, hyphens) and malformed payload rejection.
5. Backup codes generation and single-use consumption.
6. API endpoint integration: /2fa/setup, /2fa/verify, /2fa/status, /2fa/disable.
7. Critical security mutation guard (change-password requires 2FA).
8. Login enforcement when 2FA is active.
"""

from __future__ import annotations

import base64
import time
import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend import models
from backend.core.security import get_password_hash
from backend.core.totp import (
    generate_backup_codes,
    generate_totp_code,
    generate_totp_secret,
    generate_totp_uri,
    verify_and_consume_backup_code,
    verify_totp_code,
)

# ─────────────────────────────────────────────────────────────────────────────
# UNIT TESTS: CRYPTO & TOTP RFC 6238
# ─────────────────────────────────────────────────────────────────────────────


def test_generate_totp_secret_valid_base32():
    secret = generate_totp_secret()
    assert isinstance(secret, str)
    assert len(secret) >= 26  # 20 bytes in base32 is 32 chars without padding
    # Must decode cleanly as base32
    padding = "=" * ((8 - len(secret) % 8) % 8)
    decoded = base64.b32decode((secret + padding).encode("ascii"), casefold=True)
    assert len(decoded) == 20


def test_totp_code_generation_is_deterministic():
    secret = "JBSWY3DPEHPK3PXP"  # Standard RFC test vector Base32 secret
    fixed_time = 1700000000.0

    code_1 = generate_totp_code(secret, timestamp=fixed_time)
    code_2 = generate_totp_code(secret, timestamp=fixed_time)

    assert code_1 == code_2
    assert len(code_1) == 6
    assert code_1.isdigit()


def test_totp_temporal_window_coverage():
    """Verify tolerance window (+/- 1 step of 30 seconds).

    At t0:
    - Step t0 must pass with tolerance 0 and tolerance 1.
    - Step t-1 (-30s) must pass with tolerance 1, fail with tolerance 0.
    - Step t+1 (+30s) must pass with tolerance 1, fail with tolerance 0.
    - Step t-2 (-60s) must fail with tolerance 1.
    - Step t+2 (+60s) must fail with tolerance 1.
    """
    secret = generate_totp_secret()
    t0 = 1700000000.0
    step = 30

    code_t0 = generate_totp_code(secret, timestamp=t0, step_seconds=step)
    code_t_minus_1 = generate_totp_code(secret, timestamp=t0 - step, step_seconds=step)
    code_t_plus_1 = generate_totp_code(secret, timestamp=t0 + step, step_seconds=step)
    code_t_minus_2 = generate_totp_code(secret, timestamp=t0 - (2 * step), step_seconds=step)
    code_t_plus_2 = generate_totp_code(secret, timestamp=t0 + (2 * step), step_seconds=step)

    # Strict window (valid_window = 0 / tolerance = 0)
    assert verify_totp_code(secret, code_t0, timestamp=t0, valid_window=0) is True
    assert verify_totp_code(secret, code_t_minus_1, timestamp=t0, valid_window=0) is False
    assert verify_totp_code(secret, code_t_plus_1, timestamp=t0, valid_window=0) is False

    # Tolerance window +/- 1 step (valid_window = 1 / tolerance = 1)
    assert verify_totp_code(secret, code_t0, timestamp=t0, tolerance=1) is True
    assert verify_totp_code(secret, code_t_minus_1, timestamp=t0, tolerance=1) is True
    assert verify_totp_code(secret, code_t_plus_1, timestamp=t0, tolerance=1) is True

    # Out of tolerance window (+/- 2 steps = +/- 60s)
    assert verify_totp_code(secret, code_t_minus_2, timestamp=t0, tolerance=1) is False
    assert verify_totp_code(secret, code_t_plus_2, timestamp=t0, tolerance=1) is False


def test_totp_code_normalization_and_formatting():
    secret = generate_totp_secret()
    t = time.time()
    valid_code = generate_totp_code(secret, timestamp=t)

    # Hyphenated format "123-456"
    hyphenated = f"{valid_code[:3]}-{valid_code[3:]}"
    assert verify_totp_code(secret, hyphenated, timestamp=t) is True

    # Spaced format "123 456"
    spaced = f"{valid_code[:3]} {valid_code[3:]}"
    assert verify_totp_code(secret, spaced, timestamp=t) is True

    # Invalid entries
    assert verify_totp_code(secret, "abc123", timestamp=t) is False
    assert verify_totp_code(secret, "12345", timestamp=t) is False
    assert verify_totp_code(secret, "", timestamp=t) is False
    assert verify_totp_code("", valid_code, timestamp=t) is False


def test_totp_uri_generation():
    secret = "JBSWY3DPEHPK3PXP"
    uri = generate_totp_uri(secret, account_name="admin@ccf.com", issuer="CCF Plataforma")
    assert uri.startswith("otpauth://totp/CCF%20Plataforma:admin%40ccf.com?")
    assert "secret=JBSWY3DPEHPK3PXP" in uri
    assert "issuer=CCF%20Plataforma" in uri
    assert "digits=6" in uri
    assert "period=30" in uri


def test_backup_codes_generation_and_consumption():
    codes = generate_backup_codes(count=5)
    assert len(codes) == 5
    for c in codes:
        assert len(c) == 9  # XXXX-XXXX format
        assert "-" in c

    target_code = codes[2]

    # Valid consumption
    is_valid, remaining = verify_and_consume_backup_code(codes, target_code)
    assert is_valid is True
    assert len(remaining) == 4
    assert target_code not in remaining

    # Second consumption of the same code must fail (single-use guarantee)
    is_valid_again, remaining_2 = verify_and_consume_backup_code(remaining, target_code)
    assert is_valid_again is False
    assert len(remaining_2) == 4

    # Invalid code
    is_valid_fake, remaining_fake = verify_and_consume_backup_code(remaining, "INVALID-CODE")
    assert is_valid_fake is False
    assert len(remaining_fake) == 4


# ─────────────────────────────────────────────────────────────────────────────
# INTEGRATION TESTS: HTTP API 2FA WORKFLOW
# ─────────────────────────────────────────────────────────────────────────────


def _setup_test_user(db_session: Session, email: str = "test2fa@ccf.com", password: str = "Secret1234!"):
    # Ensure Sede exists
    sede = db_session.query(models.Sede).first()
    if not sede:
        sede = models.Sede(nombre="Sede Central", ciudad="Bogota")
        db_session.add(sede)
        db_session.flush()

    user_id = uuid.uuid4()
    persona = models.Persona(
        id=user_id,
        first_name="Admin",
        last_name="2FA",
        email=email,
        sede_id=sede.id,
        estado_vital="ACTIVO",
    )
    db_session.add(persona)

    user = models.User(
        id=user_id,
        email=email,
        username=email.split("@")[0],
        password_hash=get_password_hash(password),
        sede_id=sede.id,
        is_active=True,
        is_mfa_enabled=False,
    )
    db_session.add(user)
    db_session.commit()
    return user


def test_api_2fa_full_lifecycle(client: TestClient, db_session: Session):
    email = f"totp-{uuid.uuid4().hex[:6]}@example.com"
    raw_password = "SecurePassword123!"
    user = _setup_test_user(db_session, email=email, password=raw_password)

    # 1. Login to get auth token
    login_resp = client.post(
        "/api/v3/auth/login",
        json={"email": email, "password": raw_password},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Check 2FA status: disabled initially
    status_resp = client.get("/api/v3/auth/2fa/status", headers=headers)
    assert status_resp.status_code == 200
    assert status_resp.json()["is_mfa_enabled"] is False

    # 3. Setup 2FA
    setup_resp = client.post("/api/v3/auth/2fa/setup", headers=headers)
    assert setup_resp.status_code == 200
    setup_data = setup_resp.json()
    secret = setup_data["secret"]
    assert "otpauth_uri" in setup_data
    assert len(setup_data["backup_codes"]) > 0

    # 4. Verify with invalid code should fail
    verify_bad = client.post("/api/v3/auth/2fa/verify", headers=headers, json={"code": "000000"})
    assert verify_bad.status_code == 400

    # 5. Verify with valid TOTP code
    current_code = generate_totp_code(secret)
    verify_good = client.post("/api/v3/auth/2fa/verify", headers=headers, json={"code": current_code})
    assert verify_good.status_code == 200
    assert verify_good.json()["verified"] is True
    assert verify_good.json()["is_mfa_enabled"] is True

    # 6. Status now reports enabled
    status_enabled = client.get("/api/v3/auth/2fa/status", headers=headers)
    assert status_enabled.json()["is_mfa_enabled"] is True

    # 7. Critical security mutation: change password requires 2FA
    # Without 2FA code -> 403 Forbidden
    change_without_2fa = client.post(
        "/api/v3/auth/change-password",
        headers=headers,
        json={"current_password": raw_password, "new_password": "NewSecurePassword456!"},
    )
    assert change_without_2fa.status_code == 403
    assert "2FA_REQUIRED" in change_without_2fa.text

    # With valid 2FA code -> 200 OK
    code_for_pwd = generate_totp_code(secret)
    change_with_2fa = client.post(
        "/api/v3/auth/change-password",
        headers=headers,
        json={
            "current_password": raw_password,
            "new_password": "NewSecurePassword456!",
            "totp_code": code_for_pwd,
        },
    )
    assert change_with_2fa.status_code == 200

    # 8. Login now requires 2FA
    # Login without TOTP code -> 401 with 2FA_REQUIRED
    login_need_2fa = client.post(
        "/api/v3/auth/login",
        json={"email": email, "password": "NewSecurePassword456!"},
    )
    assert login_need_2fa.status_code == 401
    assert "2FA_REQUIRED" in login_need_2fa.text

    # Login with valid TOTP code -> 200 OK
    code_for_login = generate_totp_code(secret)
    login_success = client.post(
        "/api/v3/auth/login",
        json={"email": email, "password": "NewSecurePassword456!", "totp_code": code_for_login},
    )
    assert login_success.status_code == 200
    assert "access_token" in login_success.json()

    # 9. Disable 2FA with valid TOTP code
    code_for_disable = generate_totp_code(secret)
    disable_resp = client.post(
        "/api/v3/auth/2fa/disable",
        headers=headers,
        json={"code": code_for_disable},
    )
    assert disable_resp.status_code == 200
    assert disable_resp.json()["status"] == "success"

    # Status is now disabled
    status_disabled = client.get("/api/v3/auth/2fa/status", headers=headers)
    assert status_disabled.json()["is_mfa_enabled"] is False
