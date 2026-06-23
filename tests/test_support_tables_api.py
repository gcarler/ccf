"""Tests for support and tables API modules (UUID PK compliant)."""
import uuid

from backend import models
from tests.conftest import seed_admin_v2 as _seed_admin
from tests.conftest import auth_headers_v2 as _auth_headers


def _seed_sede(db_session):
    sede = models.Sede(
        id=uuid.uuid4(), nombre="Test Sede", ciudad="Bogota", es_activa=True
    )
    db_session.add(sede)
    db_session.commit()
    db_session.refresh(sede)
    return sede


# ── Support Ticket Tests ─────────────────────────────────────────


def test_support_create_ticket(client, db_session):
    admin, persona, sede = _seed_admin(db_session)
    headers = _auth_headers(client, email=admin.email, password="testpass123")

    resp = client.post(
        "/api/support",
        json={"subject": "Test Ticket", "description": "Help needed"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["subject"] == "Test Ticket"
    assert data["status"] == "open"
    assert "id" in data


def test_support_list_tickets(client, db_session):
    admin, persona, sede = _seed_admin(db_session)
    headers = _auth_headers(client, email=admin.email, password="testpass123")

    resp = client.get("/api/support", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


def test_support_patch_ticket(client, db_session):
    admin, persona, sede = _seed_admin(db_session)
    headers = _auth_headers(client, email=admin.email, password="testpass123")

    create_resp = client.post(
        "/api/support",
        json={"subject": "Patch Test", "description": "To be patched"},
        headers=headers,
    )
    assert create_resp.status_code == 200
    ticket_id = create_resp.json()["id"]

    resp = client.patch(
        f"/api/support/{ticket_id}",
        json={"status": "in_progress"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "in_progress"


# ── Tables (Saved Views) Tests ────────────────────────────────────


def test_tables_list_schemas(client, db_session):
    admin, persona, sede = _seed_admin(db_session)
    headers = _auth_headers(client, email=admin.email, password="testpass123")

    resp = client.get("/api/tables/schemas", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


def test_tables_create_schema(client, db_session):
    admin, persona, sede = _seed_admin(db_session)
    headers = _auth_headers(client, email=admin.email, password="testpass123")

    payload = {
        "name": "Test View",
        "schema": [{"field": "name", "type": "text"}],
        "filters": [],
        "grouping": [],
    }
    resp = client.post("/api/tables/schemas", json=payload, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Test View"
    assert "id" in data


def test_tables_update_schema(client, db_session):
    admin, persona, sede = _seed_admin(db_session)
    headers = _auth_headers(client, email=admin.email, password="testpass123")

    create_resp = client.post(
        "/api/tables/schemas",
        json={"name": "Update Me", "schema": [], "filters": [], "grouping": []},
        headers=headers,
    )
    assert create_resp.status_code == 201
    view_id = create_resp.json()["id"]

    resp = client.patch(
        f"/api/tables/schemas/{view_id}",
        json={"name": "Updated View"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Updated View"


def test_tables_delete_schema(client, db_session):
    admin, persona, sede = _seed_admin(db_session)
    headers = _auth_headers(client, email=admin.email, password="testpass123")

    create_resp = client.post(
        "/api/tables/schemas",
        json={"name": "Delete Me", "schema": [], "filters": [], "grouping": []},
        headers=headers,
    )
    assert create_resp.status_code == 201
    view_id = create_resp.json()["id"]

    resp = client.delete(f"/api/tables/schemas/{view_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    list_resp = client.get("/api/tables/schemas", headers=headers)
    assert list_resp.status_code == 200
    views = list_resp.json()
    assert all(v["id"] != view_id for v in views)
