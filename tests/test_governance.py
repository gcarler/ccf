from __future__ import annotations

from fastapi.testclient import TestClient

from backend import crud, models
from backend.core.security import get_password_hash


def seed_admin(db_session, email: str = "admin@example.com", password: str = "secret123") -> tuple[models.User, str]:
    admin = models.User(
        username="admin",
        email=email,
        password_hash=get_password_hash(password),
        role="admin",
        is_active=True,
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    return admin, password


def obtain_token(client: TestClient, email: str, password: str) -> str:
    response = client.post(
        "/api/auth/login",
        data={"username": email, "password": password, "grant_type": "password"},
    )
    assert response.status_code == 200
    data = response.json()
    return data["access_token"]


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_agent_task_creation_logs_audit(client: TestClient, db_session):
    admin, password = seed_admin(db_session)
    token = obtain_token(client, admin.email, password)

    response = client.post(
        "/api/agents/tasks",
        headers=auth_headers(token),
        json={"title": "Revisar reportes", "priority": "high", "source": "test"},
    )
    assert response.status_code == 200

    logs = db_session.query(models.AdminAuditLog).all()
    assert len(logs) == 1
    assert logs[0].action == "create_agent_task"
    assert logs[0].actor_user_id == admin.id


def test_audit_logs_endpoint_returns_entries(client: TestClient, db_session):
    admin, password = seed_admin(db_session)
    crud.create_admin_audit_log(
        db_session,
        actor_user_id=admin.id,
        action="manual_entry",
        resource_type="test",
        metadata={"note": "ok"},
    )
    token = obtain_token(client, admin.email, password)

    response = client.get("/api/governance/audit-logs", headers=auth_headers(token))
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["action"] == "manual_entry"
