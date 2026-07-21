from fastapi.testclient import TestClient

from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin


def seed_admin(db_session, email="admin@example.com", password="secret123"):
    user_obj, _, _ = _seed_admin(db_session, email, password)
    return user_obj


def auth_headers(client, email="admin@example.com", password="secret123"):
    return _auth_headers(client, email=email, password=password)


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
    listed_data = list_response.json()
    listed = listed_data.get("items", listed_data) if isinstance(listed_data, dict) else listed_data
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
