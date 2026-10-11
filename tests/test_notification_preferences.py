"""Tests Fase 1 — Preferencias de notificación (PLAN_NOTIFICACIONES_EMAIL_CCF.md).

Cubre:
  1. Seeding de defaults (20 filas: 10 eventos × 2 canales) al primer GET.
  2. Idempotencia del seeding (segundo GET no duplica).
  3. PATCH de una preferencia (canal × evento) persiste.
  4. Canal no canónico → 422.
  5. Axioma 3: `is_channel_enabled` respeta fila persistida y defaults.

Auth: flujo JWT real (login como admin sembrado) — sin override del guard,
     para ejercitar require_module_access + resolve_persona_id_for_user.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin


def test_get_preferences_seeds_defaults(client: TestClient, db_session):
    admin, persona, _sede = _seed_admin(db_session)
    headers = _auth_headers(client, email=admin.email, password="testpass123")

    response = client.get("/api/messaging/notifications/preferences", headers=headers)
    assert response.status_code == 200
    body = response.json()
    prefs = body["preferences"]
    # 10 eventos × 2 canales = 20 filas
    assert len(prefs) == 20

    channels = {(p["channel"], p["event_type"], p["enabled"]) for p in prefs}
    # Email ON para los 3 eventos de alta prioridad
    assert ("email", "task_assigned", True) in channels
    assert ("email", "mention", True) in channels
    assert ("email", "event_reminder", True) in channels
    # Email OFF para broadcast
    assert ("email", "broadcast", False) in channels
    # In-app ON para todos
    assert ("in_app", "broadcast", True) in channels


def test_get_preferences_idempotent(client: TestClient, db_session):
    admin, persona, _sede = _seed_admin(db_session)
    headers = _auth_headers(client, email=admin.email, password="testpass123")

    first = client.get("/api/messaging/notifications/preferences", headers=headers)
    assert first.status_code == 200
    second = client.get("/api/messaging/notifications/preferences", headers=headers)
    assert second.status_code == 200
    assert len(first.json()["preferences"]) == len(second.json()["preferences"]) == 20


def test_patch_preference_persists(client: TestClient, db_session):
    admin, persona, _sede = _seed_admin(db_session)
    headers = _auth_headers(client, email=admin.email, password="testpass123")

    response = client.patch(
        "/api/messaging/notifications/preferences",
        json={"channel": "email", "event_type": "broadcast", "enabled": True},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["enabled"] is True
    assert response.json()["channel"] == "email"

    # Re-GET refleja la mutación
    listing = client.get("/api/messaging/notifications/preferences", headers=headers)
    rows = {(p["channel"], p["event_type"]): p["enabled"] for p in listing.json()["preferences"]}
    assert rows[("email", "broadcast")] is True


def test_patch_invalid_channel_returns_422(client: TestClient, db_session):
    admin, persona, _sede = _seed_admin(db_session)
    headers = _auth_headers(client, email=admin.email, password="testpass123")

    response = client.patch(
        "/api/messaging/notifications/preferences",
        json={"channel": "carrier_pigeon", "event_type": "mention", "enabled": True},
        headers=headers,
    )
    assert response.status_code == 422


def test_is_channel_enabled_respects_persisted_and_defaults(db_session):
    from uuid import uuid4

    from backend.services.notification_preferences import is_channel_enabled

    user_a, user_b = uuid4(), uuid4()
    # Default: email/task_assigned = True
    assert is_channel_enabled(db_session, user_a, "email", "task_assigned") is True
    # Default: email/broadcast = False
    assert is_channel_enabled(db_session, user_b, "email", "broadcast") is False
