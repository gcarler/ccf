from fastapi.testclient import TestClient

from backend import models
from backend.core.security import get_password_hash


def seed_admin(db_session, email="admin@example.com", password="secret123"):
    user = models.User(
        username="admin",
        email=email,
        password_hash=get_password_hash(password),
        role="admin",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def auth_headers(client: TestClient, email="admin@example.com", password="secret123"):
    response = client.post(
        "/api/auth/login",
        data={"username": email, "password": password, "grant_type": "password"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_admin_automation_crud_roundtrip(client: TestClient, db_session):
    seed_admin(db_session)
    headers = auth_headers(client)

    create_response = client.post(
        "/api/admin/automations",
        json={
            "name": "Reminder rule",
            "trigger_type": "deadline_due",
            "action_type": "create_task",
            "action_payload": {"priority": "high"},
            "is_active": True,
        },
        headers=headers,
    )
    assert create_response.status_code == 200
    created = create_response.json()
    assert created["trigger_type"] == "deadline_due"
    assert created["action_type"] == "create_task"

    list_response = client.get("/api/admin/automations", headers=headers)
    assert list_response.status_code == 200
    listed = list_response.json()
    assert any(item["name"] == "Reminder rule" for item in listed)

    rule_id = created["id"]
    update_response = client.patch(
        f"/api/admin/automations/{rule_id}",
        json={"is_active": False, "action_payload": {"priority": "low"}},
        headers=headers,
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["is_active"] is False
    assert updated["action_payload"]["priority"] == "low"
