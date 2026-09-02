"""Contract coverage for the operational CRM completion slice."""

from tests.conftest import auth_headers, seed_admin


def test_crm_analytics_exposes_the_keys_consumed_by_the_ui(client, db_session):
    seed_admin(db_session, email="crm-slice-analytics@test.com")
    headers = auth_headers(client, email="crm-slice-analytics@test.com", password="testpass123")

    response = client.get("/api/crm/analytics", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload["total_leads"], int)
    assert isinstance(payload["pipeline_by_stage"], dict)
    assert "total_cases" not in payload
    assert "cases_by_stage" not in payload


def test_newsletter_and_messaging_return_operational_collection_shapes(client, db_session):
    seed_admin(db_session, email="crm-slice-collections@test.com")
    headers = auth_headers(client, email="crm-slice-collections@test.com", password="testpass123")

    newsletter = client.get("/api/crm/leads/newsletter?page=1&page_size=10", headers=headers)
    messaging = client.get("/api/crm/messaging/history?limit=10", headers=headers)

    assert newsletter.status_code == 200
    newsletter_payload = newsletter.json()
    assert isinstance(newsletter_payload["leads"], list)
    assert isinstance(newsletter_payload["total"], int)
    assert newsletter_payload["page"] == 1
    assert newsletter_payload["page_size"] == 10
    messaging_payload = messaging.json()
    assert isinstance(messaging_payload["items"], list)
    assert isinstance(messaging_payload["total"], int)


def test_crm_slice_remains_protected_without_authentication(client):
    for path in ("/api/crm/analytics", "/api/crm/leads/newsletter", "/api/crm/messaging/history"):
        assert client.get(path).status_code in (401, 403)
