"""
Enterprise CMS Integration Tests — Audit Trail, Content Permissions,
Notifications, Webhooks, Custom Post Types, Glossary, Search, Sessions,
Media Folders, Redirects, Broken Links.

Tests the full CRUD cycle: Create → Read → Update → Delete for each feature.
Validates HTTP status codes, JSON contracts, and database state.
"""
import pytest

from tests.conftest import auth_headers, seed_admin, seed_user_with_role

# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def admin_setup():
    """Shared admin user for all enterprise tests."""
    return {}


@pytest.fixture(scope="function")
def authed_client(client, db_session):
    """Client with authenticated admin user."""
    user, persona, sede = seed_admin(db_session)
    headers = auth_headers(client)
    return client, headers, sede


# ═══════════════════════════════════════════════════════════════════════════════
# 1. AUDIT TRAIL TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestAuditTrail:
    def test_list_audit_logs_empty(self, authed_client):
        client, headers, sede = authed_client
        resp = client.get("/api/cms/v2/audit-logs", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_list_audit_logs_with_filter(self, authed_client):
        client, headers, sede = authed_client
        resp = client.get("/api/cms/v2/audit-logs?entity_type=cms_page&limit=10", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_audit_log_structure(self, authed_client):
        client, headers, sede = authed_client
        resp = client.get("/api/cms/v2/audit-logs?limit=1", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        if len(data) > 0:
            log = data[0]
            assert "id" in log
            assert "action" in log
            assert "entity_type" in log
            assert "created_at" in log

    def test_audit_logs_requires_auth(self, client):
        resp = client.get("/api/cms/v2/audit-logs")
        assert resp.status_code in (401, 403)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. CONTENT PERMISSIONS TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestContentPermissions:
    def test_create_permission(self, authed_client):
        client, headers, sede = authed_client
        resp = client.post("/api/cms/v2/content-permissions", headers=headers, json={
            "site_key": "faro",
            "entity_type": "page",
            "entity_id": "nosotros",
            "permission_type": "read",
            "grant_type": "role",
            "grant_target": "admin",
            "is_denied": False,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert data["status"] == "created"

    def test_list_permissions(self, authed_client):
        client, headers, sede = authed_client
        resp = client.get("/api/cms/v2/content-permissions?site_key=faro", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_delete_permission(self, authed_client):
        client, headers, sede = authed_client
        # Create first
        create_resp = client.post("/api/cms/v2/content-permissions", headers=headers, json={
            "site_key": "faro", "entity_type": "page", "entity_id": "test-delete",
            "permission_type": "edit", "grant_type": "role", "grant_target": "editor",
        })
        perm_id = create_resp.json()["id"]
        # Delete
        resp = client.delete(f"/api/cms/v2/content-permissions/{perm_id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "deleted"

    def test_delete_nonexistent_permission(self, authed_client):
        client, headers, sede = authed_client
        resp = client.delete("/api/cms/v2/content-permissions/00000000-0000-0000-0000-000000000000", headers=headers)
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# 3. NOTIFICATIONS TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestNotifications:
    def test_list_notifications(self, authed_client):
        client, headers, sede = authed_client
        resp = client.get("/api/cms/v2/notifications", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total_unread" in data
        assert isinstance(data["items"], list)

    def test_list_unread_only(self, authed_client):
        client, headers, sede = authed_client
        resp = client.get("/api/cms/v2/notifications?unread_only=true", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        for item in data["items"]:
            assert item["is_read"] is False

    def test_mark_all_read(self, authed_client):
        client, headers, sede = authed_client
        resp = client.post("/api/cms/v2/notifications/read-all", headers=headers)
        assert resp.status_code == 200
        assert "count" in resp.json()

    def test_notifications_requires_auth(self, client):
        resp = client.get("/api/cms/v2/notifications")
        assert resp.status_code in (401, 403)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. WEBHOOKS TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestWebhooks:
    def test_create_webhook(self, authed_client):
        client, headers, sede = authed_client
        resp = client.post("/api/cms/v2/webhooks", headers=headers, json={
            "site_key": "faro",
            "name": "Test Webhook",
            "url": "https://example.com/webhook",
            "events": ["page.published"],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert data["status"] == "created"

    def test_list_webhooks(self, authed_client):
        client, headers, sede = authed_client
        resp = client.get("/api/cms/v2/webhooks?site_key=faro", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_update_webhook(self, authed_client):
        client, headers, sede = authed_client
        # Create
        create_resp = client.post("/api/cms/v2/webhooks", headers=headers, json={
            "site_key": "faro", "name": "To Update", "url": "https://example.com/hook",
        })
        hook_id = create_resp.json()["id"]
        # Update
        resp = client.patch(f"/api/cms/v2/webhooks/{hook_id}", headers=headers, json={
            "name": "Updated Hook",
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "updated"

    def test_delete_webhook(self, authed_client):
        client, headers, sede = authed_client
        create_resp = client.post("/api/cms/v2/webhooks", headers=headers, json={
            "site_key": "faro", "name": "To Delete", "url": "https://example.com/del",
        })
        hook_id = create_resp.json()["id"]
        resp = client.delete(f"/api/cms/v2/webhooks/{hook_id}", headers=headers)
        assert resp.status_code == 200

    def test_webhook_deliveries(self, authed_client):
        client, headers, sede = authed_client
        create_resp = client.post("/api/cms/v2/webhooks", headers=headers, json={
            "site_key": "faro", "name": "Deliveries Test", "url": "https://example.com/d",
        })
        hook_id = create_resp.json()["id"]
        resp = client.get(f"/api/cms/v2/webhooks/{hook_id}/deliveries", headers=headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# ═══════════════════════════════════════════════════════════════════════════════
# 5. CUSTOM POST TYPES TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestCustomTypes:
    def test_create_custom_type(self, authed_client):
        client, headers, sede = authed_client
        resp = client.post("/api/cms/v2/custom-types", headers=headers, json={
            "site_key": "faro",
            "type_key": "policy",
            "label": "Politica",
            "label_plural": "Politicas",
            "supports": ["title", "editor", "excerpt"],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data

    def test_list_custom_types(self, authed_client):
        client, headers, sede = authed_client
        resp = client.get("/api/cms/v2/custom-types?site_key=faro", headers=headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_create_custom_entry(self, authed_client):
        client, headers, sede = authed_client
        # Create type first
        client.post("/api/cms/v2/custom-types", headers=headers, json={
            "site_key": "faro", "type_key": "wiki", "label": "Wiki",
        })
        # Create entry
        resp = client.post("/api/cms/v2/custom-entries", headers=headers, json={
            "site_key": "faro",
            "type_key": "wiki",
            "slug": "test-article",
            "title": "Test Article",
            "content_html": "<p>Hello world</p>",
            "status": "draft",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data

    def test_list_custom_entries(self, authed_client):
        client, headers, sede = authed_client
        resp = client.get("/api/cms/v2/custom-entries?site_key=faro&type_key=wiki", headers=headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_custom_entry(self, authed_client):
        client, headers, sede = authed_client
        # Create
        create_resp = client.post("/api/cms/v2/custom-entries", headers=headers, json={
            "site_key": "faro", "type_key": "wiki", "slug": "get-test", "title": "Get Test",
        })
        entry_id = create_resp.json()["id"]
        # Get
        resp = client.get(f"/api/cms/v2/custom-entries/{entry_id}", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Get Test"

    def test_update_custom_entry(self, authed_client):
        client, headers, sede = authed_client
        create_resp = client.post("/api/cms/v2/custom-entries", headers=headers, json={
            "site_key": "faro", "type_key": "wiki", "slug": "update-test", "title": "Original",
        })
        entry_id = create_resp.json()["id"]
        resp = client.patch(f"/api/cms/v2/custom-entries/{entry_id}", headers=headers, json={
            "title": "Updated Title",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["version"] == 2

    def test_rollback_custom_entry(self, authed_client):
        client, headers, sede = authed_client
        create_resp = client.post("/api/cms/v2/custom-entries", headers=headers, json={
            "site_key": "faro", "type_key": "wiki", "slug": "rollback-test", "title": "V1",
        })
        entry_id = create_resp.json()["id"]
        # Update to v2
        client.patch(f"/api/cms/v2/custom-entries/{entry_id}", headers=headers, json={"title": "V2"})
        # Get versions
        versions_resp = client.get(f"/api/cms/v2/custom-entries/{entry_id}/versions", headers=headers)
        versions = versions_resp.json()
        v1_id = [v for v in versions if v["version_number"] == 1][0]["id"]
        # Rollback
        resp = client.post(f"/api/cms/v2/custom-entries/{entry_id}/rollback/{v1_id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["new_version"] == 3

    def test_delete_custom_entry(self, authed_client):
        client, headers, sede = authed_client
        create_resp = client.post("/api/cms/v2/custom-entries", headers=headers, json={
            "site_key": "faro", "type_key": "wiki", "slug": "delete-test", "title": "Delete Me",
        })
        entry_id = create_resp.json()["id"]
        resp = client.delete(f"/api/cms/v2/custom-entries/{entry_id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "archived"


# ═══════════════════════════════════════════════════════════════════════════════
# 6. GLOSSARY TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestGlossary:
    def test_create_glossary_term(self, authed_client):
        client, headers, sede = authed_client
        resp = client.post("/api/cms/v2/glossary", headers=headers, json={
            "site_key": "faro",
            "term": "CRM",
            "definition": "Customer Relationship Management",
            "aliases": ["Gestion de clientes"],
            "category": "Tecnologia",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data

    def test_list_glossary_terms(self, authed_client):
        client, headers, sede = authed_client
        resp = client.get("/api/cms/v2/glossary?site_key=faro", headers=headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_search_glossary(self, authed_client):
        client, headers, sede = authed_client
        # Create
        client.post("/api/cms/v2/glossary", headers=headers, json={
            "site_key": "faro", "term": "API", "definition": "Application Programming Interface",
        })
        # Search
        resp = client.get("/api/cms/v2/glossary?site_key=faro&search=API", headers=headers)
        assert resp.status_code == 200
        terms = resp.json()
        assert any("API" in t["term"] for t in terms)


# ═══════════════════════════════════════════════════════════════════════════════
# 7. SEARCH TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestSearch:
    def test_search_content(self, authed_client):
        client, headers, sede = authed_client
        resp = client.post("/api/cms/v2/search", headers=headers, json={
            "site_key": "faro",
            "query": "test",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "query" in data
        assert "results" in data
        assert "promoted" in data

    def test_create_search_promotion(self, authed_client):
        client, headers, sede = authed_client
        resp = client.post("/api/cms/v2/search/promotions", headers=headers, json={
            "site_key": "faro",
            "query_text": "vacaciones",
            "entity_type": "cms_page",
            "entity_id": "politica-vacaciones",
            "title": "Politica de Vacaciones",
            "boost_score": 100,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data


# ═══════════════════════════════════════════════════════════════════════════════
# 8. SESSIONS TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestSessions:
    def test_list_sessions(self, authed_client):
        client, headers, sede = authed_client
        resp = client.get("/api/cms/v2/sessions", headers=headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_revoke_all_sessions(self, authed_client):
        client, headers, sede = authed_client
        resp = client.post("/api/cms/v2/sessions/revoke-all", headers=headers)
        assert resp.status_code == 200
        assert "count" in resp.json()


# ═══════════════════════════════════════════════════════════════════════════════
# 9. MEDIA FOLDERS TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestMediaFolders:
    def test_create_folder(self, authed_client):
        client, headers, sede = authed_client
        resp = client.post("/api/cms/v2/media-folders", headers=headers, json={
            "site_key": "faro",
            "name": "Brand Assets",
            "slug": "brand",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert data["path"] == "/brand/"

    def test_create_nested_folder(self, authed_client):
        client, headers, sede = authed_client
        # Parent
        parent_resp = client.post("/api/cms/v2/media-folders", headers=headers, json={
            "site_key": "faro", "name": "Documents", "slug": "docs",
        })
        parent_id = parent_resp.json()["id"]
        # Child
        resp = client.post("/api/cms/v2/media-folders", headers=headers, json={
            "site_key": "faro", "name": "Policies", "slug": "policies", "parent_id": parent_id,
        })
        assert resp.status_code == 200
        assert resp.json()["path"] == "/docs/policies/"

    def test_list_folders(self, authed_client):
        client, headers, sede = authed_client
        resp = client.get("/api/cms/v2/media-folders?site_key=faro", headers=headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# ═══════════════════════════════════════════════════════════════════════════════
# 10. REDIRECTS TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestRedirects:
    def test_create_redirect(self, authed_client):
        client, headers, sede = authed_client
        resp = client.post("/api/cms/v2/redirects", headers=headers, json={
            "site_key": "faro",
            "from_path": "/old-page",
            "to_path": "/new-page",
            "status_code": 301,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data

    def test_list_redirects(self, authed_client):
        client, headers, sede = authed_client
        resp = client.get("/api/cms/v2/redirects?site_key=faro", headers=headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_delete_redirect(self, authed_client):
        client, headers, sede = authed_client
        create_resp = client.post("/api/cms/v2/redirects", headers=headers, json={
            "site_key": "faro", "from_path": "/to-delete", "to_path": "/somewhere",
        })
        redir_id = create_resp.json()["id"]
        resp = client.delete(f"/api/cms/v2/redirects/{redir_id}", headers=headers)
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# 11. BROKEN LINKS TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestBrokenLinks:
    def test_list_broken_links(self, authed_client):
        client, headers, sede = authed_client
        resp = client.get("/api/cms/v2/broken-links?site_key=faro", headers=headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# ═══════════════════════════════════════════════════════════════════════════════
# 12. AUTH & SECURITY TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestEnterpriseAuth:
    """All enterprise endpoints require authentication."""

    @pytest.mark.parametrize("endpoint", [
        "/api/cms/v2/audit-logs",
        "/api/cms/v2/notifications",
        "/api/cms/v2/webhooks?site_key=faro",
        "/api/cms/v2/custom-types?site_key=faro",
        "/api/cms/v2/glossary?site_key=faro",
        "/api/cms/v2/sessions",
        "/api/cms/v2/media-folders?site_key=faro",
        "/api/cms/v2/redirects?site_key=faro",
        "/api/cms/v2/broken-links?site_key=faro",
        "/api/cms/v2/content-permissions?site_key=faro",
    ])
    def test_endpoint_requires_auth(self, client, endpoint):
        resp = client.get(endpoint)
        assert resp.status_code in (401, 403), f"{endpoint} should require auth, got {resp.status_code}"


# ═══════════════════════════════════════════════════════════════════════════════
# 13. CRUD CYCLE TESTS (Full lifecycle)
# ═══════════════════════════════════════════════════════════════════════════════

class TestCrudLifecycle:
    """End-to-end CRUD lifecycle for custom entries."""

    def test_custom_entry_full_lifecycle(self, authed_client):
        client, headers, sede = authed_client

        # 1. Create type
        type_resp = client.post("/api/cms/v2/custom-types", headers=headers, json={
            "site_key": "faro", "type_key": "procedure", "label": "Procedimiento",
        })
        assert type_resp.status_code == 200

        # 2. Create entry
        entry_resp = client.post("/api/cms/v2/custom-entries", headers=headers, json={
            "site_key": "faro", "type_key": "procedure", "slug": "onboarding",
            "title": "Onboarding Procedure", "content_html": "<p>Step 1</p>",
            "status": "draft",
        })
        assert entry_resp.status_code == 200
        entry_id = entry_resp.json()["id"]

        # 3. Read entry
        get_resp = client.get(f"/api/cms/v2/custom-entries/{entry_id}", headers=headers)
        assert get_resp.status_code == 200
        assert get_resp.json()["title"] == "Onboarding Procedure"
        assert get_resp.json()["status"] == "draft"

        # 4. Update to published
        update_resp = client.patch(f"/api/cms/v2/custom-entries/{entry_id}", headers=headers, json={
            "status": "published", "content_html": "<p>Step 1: Complete</p>",
        })
        assert update_resp.status_code == 200
        assert update_resp.json()["version"] == 2

        # 5. Verify version history
        versions_resp = client.get(f"/api/cms/v2/custom-entries/{entry_id}/versions", headers=headers)
        assert versions_resp.status_code == 200
        versions = versions_resp.json()
        assert len(versions) == 2

        # 6. Rollback to v1
        v1_id = [v for v in versions if v["version_number"] == 1][0]["id"]
        rollback_resp = client.post(f"/api/cms/v2/custom-entries/{entry_id}/rollback/{v1_id}", headers=headers)
        assert rollback_resp.status_code == 200

        # 7. Verify rollback
        final_resp = client.get(f"/api/cms/v2/custom-entries/{entry_id}", headers=headers)
        assert final_resp.json()["version"] == 3

        # 8. Archive (soft delete)
        del_resp = client.delete(f"/api/cms/v2/custom-entries/{entry_id}", headers=headers)
        assert del_resp.status_code == 200
        assert del_resp.json()["status"] == "archived"


class TestEnterpriseAuthorization:
    def test_lector_cannot_access_enterprise_cms(self, client, db_session):
        seed_user_with_role(db_session, role_name="lector", email="enterprise-lector@example.com")
        headers = auth_headers(client, email="enterprise-lector@example.com", password="testpass123")

        read_resp = client.get("/api/cms/v2/audit-logs", headers=headers)
        assert read_resp.status_code == 403

        write_resp = client.post(
            "/api/cms/v2/webhooks",
            headers=headers,
            json={
                "site_key": "faro",
                "name": "Blocked Hook",
                "url": "https://example.com/webhook",
            },
        )
        assert write_resp.status_code == 403
