"""Web Push API (VAPID RFC 8292 / RFC 8291) Service.

Provides cryptographic VAPID keypair generation (NIST P-256 / prime256v1),
ES256 JWT generation with raw 64-byte ECDSA signatures (RFC 7515),
subscription management per user and device, and push delivery via HTTP/2 push services.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse
import uuid

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, utils

logger = logging.getLogger("CCF-WebPush")

# Fallback in-memory and persistent state file
_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_VAPID_FILE = _DATA_DIR / "vapid_keys.json"
_SUBSCRIPTIONS_FILE = _DATA_DIR / "web_push_subscriptions.json"

_lock = threading.Lock()
_CACHED_VAPID: dict[str, str] | None = None


# ─────────────────────────────────────────────────────────────────────────────
# 1. CRYPTO & VAPID KEY MANAGEMENT (RFC 8292)
# ─────────────────────────────────────────────────────────────────────────────


def b64url_encode(data: bytes) -> str:
    """Encode bytes into URL-safe base64 without padding."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def b64url_decode(encoded: str) -> bytes:
    """Decode URL-safe base64 string with optional missing padding."""
    rem = len(encoded) % 4
    if rem > 0:
        encoded += "=" * (4 - rem)
    return base64.urlsafe_b64decode(encoded)


def generate_vapid_keypair() -> tuple[str, str]:
    """Generate an ECDSA NIST P-256 keypair formatted for VAPID.

    Returns:
        (public_key_b64, private_key_b64)
        - Public key: 65 bytes uncompressed EC point (0x04 || X || Y)
        - Private key: 32 bytes big-endian integer
    """
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key = private_key.public_key()

    # Raw 65-byte uncompressed point: 0x04 + 32-byte X + 32-byte Y
    raw_pub = public_key.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint,
    )

    priv_val = private_key.private_numbers().private_value
    raw_priv = priv_val.to_bytes(32, byteorder="big")

    return b64url_encode(raw_pub), b64url_encode(raw_priv)


def load_or_create_vapid_keys() -> tuple[str, str]:
    """Load VAPID keys from environment, persistent file, or generate new ones."""
    global _CACHED_VAPID

    with _lock:
        if _CACHED_VAPID:
            return _CACHED_VAPID["public_key"], _CACHED_VAPID["private_key"]

        env_pub = os.getenv("VAPID_PUBLIC_KEY")
        env_priv = os.getenv("VAPID_PRIVATE_KEY")
        if env_pub and env_priv:
            _CACHED_VAPID = {"public_key": env_pub.strip(), "private_key": env_priv.strip()}
            return _CACHED_VAPID["public_key"], _CACHED_VAPID["private_key"]

        # Check persistent storage
        if _VAPID_FILE.exists():
            try:
                data = json.loads(_VAPID_FILE.read_text(encoding="utf-8"))
                if "public_key" in data and "private_key" in data:
                    _CACHED_VAPID = data
                    return data["public_key"], data["private_key"]
            except Exception as e:
                logger.warning("Could not read vapid_keys.json: %s", e)

        # Generate new keys and persist
        pub, priv = generate_vapid_keypair()
        _CACHED_VAPID = {"public_key": pub, "private_key": priv}
        try:
            _DATA_DIR.mkdir(parents=True, exist_ok=True)
            _VAPID_FILE.write_text(json.dumps(_CACHED_VAPID, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning("Could not persist vapid_keys.json: %s", e)

        return pub, priv


def get_vapid_public_key() -> str:
    """Return the application server VAPID public key."""
    pub, _ = load_or_create_vapid_keys()
    return pub


def get_vapid_private_key() -> str:
    """Return the application server VAPID private key."""
    _, priv = load_or_create_vapid_keys()
    return priv


def create_vapid_jwt(
    endpoint: str,
    subject: str = "mailto:admin@ccf.org",
    ttl: int = 86400,
    private_key_b64: Optional[str] = None,
) -> str:
    """Create a signed VAPID JWT (ES256) according to RFC 8292 and RFC 7515.

    Uses ECDSA with SHA-256 and converts DER signature to 64-byte raw R||S.
    """
    if private_key_b64 is None:
        private_key_b64 = get_vapid_private_key()

    priv_bytes = b64url_decode(private_key_b64)
    priv_num = int.from_bytes(priv_bytes, byteorder="big")
    private_key = ec.derive_private_key(priv_num, ec.SECP256R1())

    parsed = urlparse(endpoint)
    origin = f"{parsed.scheme}://{parsed.netloc}"

    now = int(time.time())
    header = {"typ": "JWT", "alg": "ES256"}
    claims = {
        "aud": origin,
        "exp": now + ttl,
        "sub": subject,
    }

    header_b64 = b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    claims_b64 = b64url_encode(json.dumps(claims, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{claims_b64}".encode("ascii")

    der_signature = private_key.sign(signing_input, ec.ECDSA(hashes.SHA256()))
    r, s = utils.decode_dss_signature(der_signature)
    raw_signature = r.to_bytes(32, byteorder="big") + s.to_bytes(32, byteorder="big")
    sig_b64 = b64url_encode(raw_signature)

    return f"{header_b64}.{claims_b64}.{sig_b64}"


def create_vapid_headers(
    endpoint: str,
    subject: str = "mailto:admin@ccf.org",
    ttl: int = 86400,
) -> dict[str, str]:
    """Build HTTP headers required by push services for VAPID."""
    jwt = create_vapid_jwt(endpoint, subject=subject, ttl=ttl)
    pub_key = get_vapid_public_key()
    return {
        "Authorization": f"vapid t={jwt}, k={pub_key}",
        "Crypto-Key": f"p256ecdsa={pub_key}",
        "TTL": str(ttl),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 2. SUBSCRIPTION REPOSITORY
# ─────────────────────────────────────────────────────────────────────────────


class SubscriptionStore:
    """Thread-safe storage for Web Push subscriptions per user."""

    def __init__(self, storage_path: Path = _SUBSCRIPTIONS_FILE):
        self._path = storage_path
        self._subscriptions: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        with _lock:
            if self._path.exists():
                try:
                    data = json.loads(self._path.read_text(encoding="utf-8"))
                    if isinstance(data, dict):
                        self._subscriptions = data
                except Exception as e:
                    logger.warning("Could not read web_push_subscriptions.json: %s", e)

    def _persist(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(
                json.dumps(self._subscriptions, indent=2), encoding="utf-8"
            )
        except Exception as e:
            logger.warning("Could not persist web_push_subscriptions.json: %s", e)

    def subscribe(
        self,
        user_id: str,
        endpoint: str,
        p256dh: str,
        auth: str,
        device_name: Optional[str] = None,
    ) -> dict[str, Any]:
        """Register or update a push subscription for a user."""
        with _lock:
            # Use endpoint as canonical deduplication key
            sub_id = str(uuid.uuid4())
            record = {
                "id": sub_id,
                "user_id": str(user_id),
                "endpoint": endpoint,
                "p256dh": p256dh,
                "auth": auth,
                "device_name": device_name or "Navegador Web",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            self._subscriptions[endpoint] = record
            self._persist()
            return record

    def unsubscribe(self, user_id: str, endpoint: str) -> bool:
        """Remove a push subscription by endpoint for a given user."""
        with _lock:
            if endpoint in self._subscriptions:
                rec = self._subscriptions[endpoint]
                if rec.get("user_id") == str(user_id):
                    del self._subscriptions[endpoint]
                    self._persist()
                    return True
            return False

    def get_user_subscriptions(self, user_id: str) -> list[dict[str, Any]]:
        """List all active subscriptions for a user."""
        with _lock:
            uid = str(user_id)
            return [
                sub
                for sub in self._subscriptions.values()
                if sub.get("user_id") == uid
            ]

    def clear(self) -> None:
        """Clear all subscriptions (used in testing)."""
        with _lock:
            self._subscriptions.clear()
            self._persist()


store = SubscriptionStore()


# ─────────────────────────────────────────────────────────────────────────────
# 3. PUSH DELIVERY
# ─────────────────────────────────────────────────────────────────────────────


def send_web_push(
    subscription: dict[str, Any],
    payload: dict[str, Any] | str,
    ttl: int = 86400,
    subject: str = "mailto:admin@ccf.org",
) -> bool:
    """Send a push notification to a client's subscription endpoint.

    Handles VAPID header attachment and stale endpoint auto-pruning.
    """
    import httpx

    endpoint = subscription.get("endpoint")
    if not endpoint:
        return False

    headers = create_vapid_headers(endpoint, subject=subject, ttl=ttl)
    headers["Content-Type"] = "application/json"

    data_bytes = (
        json.dumps(payload).encode("utf-8")
        if isinstance(payload, dict)
        else str(payload).encode("utf-8")
    )

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(endpoint, headers=headers, content=data_bytes)
            if resp.status_code in (200, 201, 202):
                return True
            if resp.status_code in (404, 410):
                # Stale subscription, remove it automatically
                user_id = subscription.get("user_id", "")
                store.unsubscribe(user_id, endpoint)
                logger.info("Removed stale push subscription: %s", endpoint)
                return False
            logger.warning(
                "Push service responded with status %s: %s",
                resp.status_code,
                resp.text[:200],
            )
            return False
    except Exception as e:
        logger.error("Failed to send web push to %s: %s", endpoint, e)
        return False


def broadcast_to_user(
    user_id: str,
    title: str,
    body: str,
    icon: Optional[str] = None,
    url: Optional[str] = None,
    tag: Optional[str] = None,
) -> int:
    """Send a push notification to all devices registered for a user."""
    subs = store.get_user_subscriptions(user_id)
    if not subs:
        return 0

    payload = {
        "title": title,
        "body": body,
        "icon": icon or "/icon-192x192.png",
        "url": url or "/plataforma/messages",
        "tag": tag or "ccf-notification",
    }

    sent_count = 0
    for sub in subs:
        if send_web_push(sub, payload):
            sent_count += 1

    return sent_count
