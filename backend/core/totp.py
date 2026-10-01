"""TOTP (Time-Based One-Time Password) implementation adhering to RFC 6238 and RFC 4226.

Provides cryptographic secret generation, standard Base32 encoding,
HMAC-SHA1 time-step code derivation, configurable tolerance window validation,
and backup code generation.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets
import struct
import time
from urllib.parse import quote

BASE32_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"


def generate_totp_secret(num_bytes: int = 20) -> str:
    """Generate a cryptographically secure random Base32 TOTP secret.

    RFC 6238 recommends minimum 160-bit (20-byte) shared secrets.
    """
    random_bytes = secrets.token_bytes(num_bytes)
    # RFC 4648 Base32 alphabet without padding for authenticator compatibility
    return base64.b32encode(random_bytes).decode("ascii").replace("=", "")


def _normalize_secret(secret: str) -> bytes:
    """Normalize and decode a Base32 secret string to bytes."""
    cleaned = secret.strip().replace(" ", "").upper()
    # Add necessary Base32 padding
    missing_padding = len(cleaned) % 8
    if missing_padding != 0:
        cleaned += "=" * (8 - missing_padding)
    return base64.b32decode(cleaned.encode("ascii"), casefold=True)


def generate_totp_code(
    secret: str,
    timestamp: float | None = None,
    step_seconds: int = 30,
    digits: int = 6,
    for_time: float | None = None,
) -> str:
    """Derive the numeric TOTP code for a given timestamp and secret.

    Uses HMAC-SHA1 and dynamic truncation as defined in RFC 6238 / RFC 4226.
    """
    if for_time is not None and timestamp is None:
        timestamp = for_time

    key = _normalize_secret(secret)
    current_time = time.time() if timestamp is None else float(timestamp)
    time_counter = int(current_time // step_seconds)

    # 8-byte big-endian counter
    counter_bytes = struct.pack(">Q", time_counter)

    # HMAC-SHA1
    hmac_digest = hmac.new(key, counter_bytes, hashlib.sha1).digest()

    # Dynamic truncation (RFC 4226 section 5.3)
    offset = hmac_digest[-1] & 0x0F
    code_int = struct.unpack(">I", hmac_digest[offset : offset + 4])[0] & 0x7FFFFFFF
    token = code_int % (10**digits)

    return f"{token:0{digits}d}"


def verify_totp_code(
    secret: str,
    code: str,
    timestamp: float | None = None,
    valid_window: int = 1,
    step_seconds: int = 30,
    digits: int = 6,
    tolerance: int | None = None,
    for_time: float | None = None,
) -> bool:
    """Verify a TOTP code against a secret within a tolerance window (+/- valid_window steps).

    A valid_window (or tolerance) of 1 tests t-1, t, and t+1 steps (total window of 3 steps = 90 seconds).
    Constant-time comparison is used to mitigate timing attacks.
    """
    if for_time is not None and timestamp is None:
        timestamp = for_time

    if tolerance is not None:
        valid_window = tolerance

    if not secret or not code:
        return False

    cleaned_code = re.sub(r"[\s\-]", "", str(code))
    if not cleaned_code.isdigit() or len(cleaned_code) != digits:
        return False

    try:
        # Validate that secret decodes properly
        _normalize_secret(secret)
    except Exception:
        return False

    current_time = time.time() if timestamp is None else float(timestamp)

    for offset in range(-valid_window, valid_window + 1):
        window_time = current_time + (offset * step_seconds)
        expected_code = generate_totp_code(
            secret=secret,
            timestamp=window_time,
            step_seconds=step_seconds,
            digits=digits,
        )
        if hmac.compare_digest(cleaned_code, expected_code):
            return True

    return False


def generate_totp_uri(
    secret: str,
    account_name: str,
    issuer: str = "CCF Plataforma",
    digits: int = 6,
    period: int = 30,
) -> str:
    """Generate standard otpauth:// URI for QR code generation."""
    encoded_issuer = quote(issuer)
    encoded_account = quote(account_name)
    label = f"{encoded_issuer}:{encoded_account}"
    return (
        f"otpauth://totp/{label}?"
        f"secret={secret}&"
        f"issuer={encoded_issuer}&"
        f"algorithm=SHA1&"
        f"digits={digits}&"
        f"period={period}"
    )


def generate_backup_codes(count: int = 8, chunk_len: int = 4) -> list[str]:
    """Generate high-entropy alphanumeric emergency backup recovery codes."""
    alphabet = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"  # Unambiguous characters
    codes: list[str] = []
    for _ in range(count):
        part1 = "".join(secrets.choice(alphabet) for _ in range(chunk_len))
        part2 = "".join(secrets.choice(alphabet) for _ in range(chunk_len))
        codes.append(f"{part1}-{part2}")
    return codes


def verify_and_consume_backup_code(
    stored_codes: list[str] | None,
    provided_code: str,
) -> tuple[bool, list[str]]:
    """Validate a backup code and consume it if valid (single-use).

    Returns a tuple of (is_valid, remaining_codes).
    """
    if not stored_codes or not provided_code:
        return False, stored_codes or []

    cleaned_input = re.sub(r"[\s\-]", "", provided_code).upper()
    remaining: list[str] = []
    matched = False

    for code in stored_codes:
        cleaned_stored = re.sub(r"[\s\-]", "", code).upper()
        if not matched and hmac.compare_digest(cleaned_input, cleaned_stored):
            matched = True
            # Code is consumed, omit from remaining
            continue
        remaining.append(code)

    return matched, remaining
