from __future__ import annotations

from fastapi.testclient import TestClient

from backend import crud, models
from tests.conftest import seed_admin_v2, auth_headers_legacy


def seed_admin(
    db_session, email: str = "admin@example.com", password: str = "secret123"
) -> tuple[models.User, str]:
    user_obj, _, _ = seed_admin_v2(db_session, email, password)
    return user_obj.legacy_user, password


def obtain_token(client: TestClient, email: str, password: str) -> str:
    headers = auth_headers_legacy(email)
    return headers["Authorization"].removeprefix("Bearer ")


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
    persona = db_session.query(models.Persona).filter(models.Persona.user_id == admin.id).first()
    assert logs[0].actor_persona_id == persona.id


def test_audit_logs_endpoint_returns_entries(client: TestClient, db_session):
    admin, password = seed_admin(db_session)
    crud.create_admin_audit_log(
        db_session,
        actor_user_id=admin.id,
        action="manual_entry",
        resource_type="test",
        metadata={"note": "ok"},
    )
    persona = db_session.query(models.Persona).filter(models.Persona.user_id == admin.id).first()
    log = db_session.query(models.AdminAuditLog).one()
    assert log.actor_persona_id == persona.id
    token = obtain_token(client, admin.email, password)

    response = client.get("/api/governance/audit-logs", headers=auth_headers(token))
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["action"] == "manual_entry"
