"""Security regressions for CRM routes mounted in the production application."""

from tests.conftest import auth_headers, seed_admin


def test_automation_palette_requires_authentication(client):
    response = client.get("/api/crm/automations/palette")
    assert response.status_code == 401


def test_automation_flow_creation_requires_edit_access(client, db_session):
    seed_admin(db_session)
    headers = auth_headers(client)

    response = client.post(
        "/api/crm/automations/flows",
        json={"name": "Flujo autenticado"},
        headers=headers,
    )
    assert response.status_code == 200
