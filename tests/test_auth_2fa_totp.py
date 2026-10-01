"""Unit tests for RFC 6238 Two-Factor Authentication (2FA TOTP).

Tests:
1. Cryptographic Base32 secret generation.
2. Accurate 6-digit TOTP code generation.
3. Code verification with temporal tolerance window (+/- 1 step).
4. Rejection of expired codes and malformed inputs.
5. Standard otpauth:// URI formatting for authenticator apps.
"""

from __future__ import annotations

import time
import pytest

from backend.core.totp import (
    BASE32_ALPHABET,
    generate_totp_code,
    generate_totp_secret,
    generate_totp_uri,
    verify_totp_code,
)


def test_generate_totp_secret():
    secret = generate_totp_secret()
    assert len(secret) == 32
    assert all(c in BASE32_ALPHABET for c in secret)

    # Different invocations produce unique secrets
    secret2 = generate_totp_secret()
    assert secret != secret2


def test_generate_totp_code():
    secret = "JBSWY3DPEHPK3PXP"  # standard test secret
    t0 = 1000000000.0
    code = generate_totp_code(secret, for_time=t0)
    assert len(code) == 6
    assert code.isdigit()


def test_verify_totp_code_exact_match():
    secret = generate_totp_secret()
    now = time.time()
    code = generate_totp_code(secret, for_time=now)
    assert verify_totp_code(secret, code, tolerance=0, for_time=now) is True


def test_verify_totp_code_tolerance_window():
    secret = generate_totp_secret()
    now = time.time()
    step = 30

    # Code generated 1 step in the past
    past_code = generate_totp_code(secret, for_time=now - step)
    # With tolerance=1, past_code is accepted
    assert verify_totp_code(secret, past_code, tolerance=1, for_time=now) is True
    # With tolerance=0, past_code is rejected
    assert verify_totp_code(secret, past_code, tolerance=0, for_time=now) is False

    # Code generated 1 step in the future
    future_code = generate_totp_code(secret, for_time=now + step)
    assert verify_totp_code(secret, future_code, tolerance=1, for_time=now) is True
    assert verify_totp_code(secret, future_code, tolerance=0, for_time=now) is False

    # Code generated 3 steps away is rejected even with tolerance=1
    far_code = generate_totp_code(secret, for_time=now - (3 * step))
    assert verify_totp_code(secret, far_code, tolerance=1, for_time=now) is False


def test_verify_totp_code_invalid_inputs():
    secret = generate_totp_secret()
    assert verify_totp_code(secret, "") is False
    assert verify_totp_code(secret, "12345") is False
    assert verify_totp_code(secret, "1234567") is False
    assert verify_totp_code(secret, "abcdef") is False
    assert verify_totp_code(secret, None) is False  # type: ignore


def test_generate_totp_uri():
    secret = "JBSWY3DPEHPK3PXP"
    uri = generate_totp_uri(secret, account_name="pastor@el-faro.org", issuer="CCF Plataforma")
    assert uri.startswith("otpauth://totp/")
    assert "secret=" + secret in uri
    assert "issuer=CCF%20Plataforma" in uri
    assert "digits=6" in uri
    assert "period=30" in uri
