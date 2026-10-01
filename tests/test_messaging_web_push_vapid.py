"""Unit and integration tests for Web Push Notifications (VAPID RFC 8292 / RFC 8291).

Tests:
1. ECDSA NIST P-256 keypair generation (65-byte uncompressed point).
2. ES256 JWT creation and cryptographic signature verification.
3. VAPID Authorization and Crypto-Key headers generation.
4. Subscription repository lifecycle (subscribe, list, unsubscribe, deduplication).
5. Auto-cleanup of stale subscriptions on 410 Gone / 404 Not Found.
6. API endpoints:
   - GET /api/messaging/push/vapid-public-key
   - POST /api/messaging/push/subscribe
   - GET /api/messaging/push/subscriptions
   - POST /api/messaging/push/test
   - POST /api/messaging/push/unsubscribe
"""

from __future__ import annotations

import base64
import json
import uuid
from unittest.mock import MagicMock, patch

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient

from backend.services.web_push import (
    b64url_decode,
    b64url_encode,
    broadcast_to_user,
    create_vapid_headers,
    create_vapid_jwt,
    generate_vapid_keypair,
    get_vapid_public_key,
    send_web_push,
    store,
)


@pytest.fixture(autouse=True)
def clean_store():
    store.clear()
    yield
    store.clear()


# ─────────────────────────────────────────────────────────────────────────────
# UNIT TESTS: CRYPTO & VAPID (RFC 8292)
# ─────────────────────────────────────────────────────────────────────────────


def test_generate_vapid_keypair():
    pub_b64, priv_b64 = generate_vapid_keypair()
    assert isinstance(pub_b64, str)
    assert isinstance(priv_b64, str)

    # Public key must decode to exactly 65 bytes (0x04 uncompressed point)
    raw_pub = b64url_decode(pub_b64)
    assert len(raw_pub) == 65
    assert raw_pub[0] == 0x04

    # Private key must decode to 32 bytes (256 bits)
    raw_priv = b64url_decode(priv_b64)
    assert len(raw_priv) == 32


def test_create_vapid_jwt_and_verify_signature():
    pub_b64, priv_b64 = generate_vapid_keypair()
    endpoint = "https://fcm.googleapis.com/fcm/send/sample-token-12345"

    jwt_token = create_vapid_jwt(
        endpoint=endpoint,
        subject="mailto:security@ccf.org",
        ttl=3600,
        private_key_b64=priv_b64,
    )

    parts = jwt_token.split(".")
    assert len(parts) == 3

    header = json.loads(b64url_decode(parts[0]).decode("utf-8"))
    claims = json.loads(b64url_decode(parts[1]).decode("utf-8"))

    assert header == {"typ": "JWT", "alg": "ES256"}
    assert claims["aud"] == "https://fcm.googleapis.com"
    assert claims["sub"] == "mailto:security@ccf.org"
    assert "exp" in claims

    # Verify signature against public key
    raw_pub = b64url_decode(pub_b64)
    public_key = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), raw_pub)

    raw_sig = b64url_decode(parts[2])
    assert len(raw_sig) == 64
    r = int.from_bytes(raw_sig[:32], byteorder="big")
    s = int.from_bytes(raw_sig[32:], byteorder="big")
    from cryptography.hazmat.primitives.asymmetric import utils

    der_sig = utils.encode_dss_signature(r, s)

    signing_input = f"{parts[0]}.{parts[1]}".encode("ascii")
    # Will raise if signature is invalid
    public_key.verify(der_sig, signing_input, ec.ECDSA(hashes.SHA256()))


def test_create_vapid_headers():
    endpoint = "https://updates.push.services.mozilla.com/wpush/v2/abcde"
    headers = create_vapid_headers(endpoint, subject="mailto:admin@ccf.org", ttl=7200)

    assert "Authorization" in headers
    assert headers["Authorization"].startswith("vapid t=")
    assert ", k=" in headers["Authorization"]

    assert "Crypto-Key" in headers
    assert headers["Crypto-Key"].startswith("p256ecdsa=")

    assert headers["TTL"] == "7200"


# ─────────────────────────────────────────────────────────────────────────────
# UNIT TESTS: SUBSCRIPTION STORE
# ─────────────────────────────────────────────────────────────────────────────


def test_subscription_store_crud():
    user_id = str(uuid.uuid4())
    endpoint = "https://fcm.googleapis.com/fcm/send/device-1"

    # 1. Subscribe
    sub = store.subscribe(
        user_id=user_id,
        endpoint=endpoint,
        p256dh="test_p256dh_key",
        auth="test_auth_secret",
        device_name="Chrome Desktop",
    )
    assert sub["user_id"] == user_id
    assert sub["endpoint"] == endpoint
    assert sub["device_name"] == "Chrome Desktop"

    # 2. Get subscriptions
    user_subs = store.get_user_subscriptions(user_id)
    assert len(user_subs) == 1
    assert user_subs[0]["endpoint"] == endpoint

    # 3. Deduplication on same endpoint updates record
    sub2 = store.subscribe(
        user_id=user_id,
        endpoint=endpoint,
        p256dh="updated_p256dh",
        auth="updated_auth",
        device_name="Chrome Desktop Reinstalled",
    )
    assert len(store.get_user_subscriptions(user_id)) == 1
    assert store.get_user_subscriptions(user_id)[0]["p256dh"] == "updated_p256dh"

    # 4. Unsubscribe
    unsub_success = store.unsubscribe(user_id=user_id, endpoint=endpoint)
    assert unsub_success is True
    assert len(store.get_user_subscriptions(user_id)) == 0


def test_send_web_push_handles_stale_subscription_410():
    user_id = str(uuid.uuid4())
    endpoint = "https://fcm.googleapis.com/fcm/send/stale-token"

    store.subscribe(user_id=user_id, endpoint=endpoint, p256dh="p", auth="a")
    assert len(store.get_user_subscriptions(user_id)) == 1

    sub = store.get_user_subscriptions(user_id)[0]

    # Mock httpx client response with 410 Gone
    mock_resp = MagicMock()
    mock_resp.status_code = 410
    mock_resp.text = "Subscription no longer valid"

    with patch("httpx.Client.post", return_value=mock_resp):
        res = send_web_push(sub, {"title": "Test", "body": "Hello"})
        assert res is False

    # Stale subscription must be automatically pruned
    assert len(store.get_user_subscriptions(user_id)) == 0


def test_broadcast_to_user():
    user_id = str(uuid.uuid4())
    endpoint1 = "https://fcm.googleapis.com/fcm/send/phone"
    endpoint2 = "https://fcm.googleapis.com/fcm/send/tablet"

    store.subscribe(user_id=user_id, endpoint=endpoint1, p256dh="p1", auth="a1")
    store.subscribe(user_id=user_id, endpoint=endpoint2, p256dh="p2", auth="a2")

    mock_resp = MagicMock()
    mock_resp.status_code = 201

    with patch("httpx.Client.post", return_value=mock_resp):
        sent = broadcast_to_user(user_id, title="Alerta CCF", body="Reunión en 10 min")
        assert sent == 2


# ─────────────────────────────────────────────────────────────────────────────
# INTEGRATION TESTS: API ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────


def test_get_vapid_public_key_api(client: TestClient):
    response = client.get("/api/messaging/push/vapid-public-key")
    assert response.status_code == 200
    data = response.json()
    assert "public_key" in data
    assert len(data["public_key"]) >= 80


def test_push_subscription_endpoints_lifecycle(client: TestClient, db_session):
    from tests.conftest import auth_headers, seed_admin

    admin_user, _, _ = seed_admin(db_session, email=f"push_{uuid.uuid4().hex[:6]}@ccf.org", password="SecretPassword123!")
    admin_email = str(admin_user.email)

    headers = auth_headers(client, email=admin_email, password="SecretPassword123!")

    # 1. Subscribe
    sub_payload = {
        "endpoint": "https://fcm.googleapis.com/fcm/send/integration-device",
        "keys": {
            "p256dh": "BNcRdreALRFXTkOOUHK1EtK2wtaz5Ry4YfYCA_0QT9Q0A4APqOM5",
            "auth": "tBHItJI5svbpez7KI4CCXg",
        },
        "device_name": "Firefox Desktop Linux",
    }
    sub_res = client.post(
        "/api/messaging/push/subscribe",
        json=sub_payload,
        headers=headers,
    )
    assert sub_res.status_code == 200
    assert sub_res.json()["subscribed"] is True

    # 2. List subscriptions
    list_res = client.get(
        "/api/messaging/push/subscriptions",
        headers=headers,
    )
    assert list_res.status_code == 200
    assert list_res.json()["count"] == 1
    assert list_res.json()["subscriptions"][0]["device_name"] == "Firefox Desktop Linux"

    # 3. Test push notification
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    with patch("httpx.Client.post", return_value=mock_resp):
        test_res = client.post(
            "/api/messaging/push/test",
            json={"title": "Test Title", "body": "Test Body"},
            headers=headers,
        )
        assert test_res.status_code == 200
        assert test_res.json()["sent_count"] == 1

    # 4. Unsubscribe
    unsub_res = client.post(
        "/api/messaging/push/unsubscribe",
        json={"endpoint": sub_payload["endpoint"]},
        headers=headers,
    )
    assert unsub_res.status_code == 200
    assert unsub_res.json()["unsubscribed"] is True

    # 5. List subscriptions again -> 0
    list_res2 = client.get(
        "/api/messaging/push/subscriptions",
        headers=headers,
    )
    assert list_res2.status_code == 200
    assert list_res2.json()["count"] == 0
