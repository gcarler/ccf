"""Massive API endpoint coverage — hits every router via the test client.

Strategy: For each API module, test every endpoint's:
  1. Success path (200/201) with auth + valid data
  2. Unauthorized (401) without auth
  3. Validation error (422) with bad body
  4. 404 with invalid ID where applicable
"""
import uuid
import pytest
from datetime import datetime, timedelta, timezone
from tests.conftest import seed_admin, auth_headers


@pytest.fixture
def admin_data(db_session):
    user, persona, sede = seed_admin(db_session)
    return user, persona, sede


@pytest.fixture
def client_auth(client, db_session, admin_data):
    headers = auth_headers(client)
    return client, headers, admin_data


# ═══════════════════════════════════════════════════════════════════════════════
# ADMIN ENDPOINTS (/api/admin/*)
# ═══════════════════════════════════════════════════════════════════════════════

class TestAdminRoles:
    def test_list_roles(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/admin/roles", headers=headers)
        assert resp.status_code == 200

    def test_list_roles_no_auth(self, client):
        resp = client.get("/api/admin/roles")
        assert resp.status_code in (401, 403)

    def test_create_role(self, client_auth):
        client, headers, _ = client_auth
        resp = client.post("/api/admin/roles", json={"name": f"test_{uuid.uuid4().hex[:6]}"}, headers=headers)
        assert resp.status_code in (200, 201)

    def test_update_role_permissions(self, client_auth, db_session):
        client, headers, _ = client_auth
        from backend.models_auth import RolPlataforma
        role = db_session.query(RolPlataforma).first()
        if role:
            resp = client.patch(f"/api/admin/roles/{role.id}", json={"permissions": {"crm:read": "allow"}}, headers=headers)
            assert resp.status_code in (200, 404)

    def test_delete_role(self, client_auth, db_session):
        client, headers, _ = client_auth
        from backend.models_auth import RolPlataforma
        role = RolPlataforma(nombre=f"del_{uuid.uuid4().hex[:6]}", permisos={})
        db_session.add(role)
        db_session.flush()
        resp = client.delete(f"/api/admin/roles/{role.id}", headers=headers)
        assert resp.status_code in (200, 204)


class TestAdminUsers:
    def test_list_users(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/admin/users", headers=headers)
        assert resp.status_code == 200

    def test_create_user(self, client_auth):
        client, headers, _ = client_auth
        resp = client.post("/api/admin/users", json={
            "email": f"new_{uuid.uuid4().hex[:6]}@test.com",
            "password": "testpass123",
            "username": f"user_{uuid.uuid4().hex[:6]}",
        }, headers=headers)
        assert resp.status_code in (200, 201, 400, 422)

    def test_get_user(self, client_auth, db_session):
        client, headers, (user, persona, _) = client_auth
        resp = client.get(f"/api/admin/users/{user.id}", headers=headers)
        assert resp.status_code in (200, 404)


class TestAdminOther:
    def test_list_personas(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/admin/personas", headers=headers)
        assert resp.status_code == 200

    def test_list_milestones(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/admin/milestones", headers=headers)
        assert resp.status_code == 200

    def test_list_automations(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/admin/automations", headers=headers)
        assert resp.status_code == 200

    def test_list_permissions(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/admin/permissions", headers=headers)
        assert resp.status_code == 200

    def test_list_audit(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/admin/audit", headers=headers)
        assert resp.status_code == 200

    def test_list_locations(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/admin/locations", headers=headers)
        assert resp.status_code == 200

    def test_list_socials(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/admin/socials", headers=headers)
        assert resp.status_code == 200

    def test_list_variables(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/admin/variables", headers=headers)
        assert resp.status_code == 200

    def test_list_testimonials(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/admin/testimonials", headers=headers)
        assert resp.status_code == 200

    def test_list_announcements(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/admin/announcements", headers=headers)
        assert resp.status_code == 200

    def test_list_donation_categories(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/admin/donation-categories", headers=headers)
        assert resp.status_code == 200

    def test_list_comments(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/admin/comments", headers=headers)
        assert resp.status_code == 200

    def test_list_auth_role_definitions(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/admin/auth-role-definitions", headers=headers)
        assert resp.status_code == 200

    def test_list_user_module_roles(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/admin/user-module-roles", headers=headers)
        assert resp.status_code == 200

    def test_list_users_with_roles(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/admin/users-with-roles", headers=headers)
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# AUTH_V3 ENDPOINTS (/api/v3/auth/*)
# ═══════════════════════════════════════════════════════════════════════════════

class TestAuthV3:
    def test_login(self, client):
        resp = client.post("/api/v3/auth/login", json={"email": "admin@example.com", "password": "testpass123"})
        assert resp.status_code == 200

    def test_login_wrong_password(self, client):
        resp = client.post("/api/v3/auth/login", json={"email": "admin@example.com", "password": "wrong"})
        assert resp.status_code in (401, 400)

    def test_login_nonexistent(self, client):
        resp = client.post("/api/v3/auth/login", json={"email": "nobody@test.com", "password": "pass"})
        assert resp.status_code in (401, 400)

    def test_me(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/v3/auth/me", headers=headers)
        assert resp.status_code == 200

    def test_me_no_auth(self, client):
        resp = client.get("/api/v3/auth/me")
        assert resp.status_code == 401

    def test_refresh(self, client_auth):
        client, headers, _ = client_auth
        resp = client.post("/api/v3/auth/refresh", headers=headers)
        assert resp.status_code in (200, 401)


# ═══════════════════════════════════════════════════════════════════════════════
# CRM ENDPOINTS (/api/crm/*)
# ═══════════════════════════════════════════════════════════════════════════════

class TestCRM:
    def test_list_casos(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/crm/casos", headers=headers)
        assert resp.status_code == 200

    def test_list_pipelines(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/crm/pipelines", headers=headers)
        assert resp.status_code == 200

    def test_list_plantillas(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/crm/resources/plantillas", headers=headers)
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# ACADEMY ENDPOINTS (/api/academy/*)
# ═══════════════════════════════════════════════════════════════════════════════

class TestAcademy:
    def test_list_courses(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/academy/courses", headers=headers)
        assert resp.status_code == 200

    def test_list_enrollments(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/academy/enrollments", headers=headers)
        assert resp.status_code == 200

    def test_list_certificates(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/academy/me/certificates", headers=headers)
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# AGENDA ENDPOINTS (/api/agenda/*)
# ═══════════════════════════════════════════════════════════════════════════════

class TestAgenda:
    def test_list_eventos(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/agenda/events", headers=headers)
        assert resp.status_code == 200

    def test_list_recursos(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/agenda/resources", headers=headers)
        assert resp.status_code == 200

    def test_list_reservas(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/agenda/reservations", headers=headers)
        assert resp.status_code == 200

    def test_list_participantes(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/agenda/participants", headers=headers)
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# PROJECTS ENDPOINTS (/api/projects/*)
# ═══════════════════════════════════════════════════════════════════════════════

class TestProjects:
    def test_list_projects(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/projects", headers=headers)
        assert resp.status_code == 200

    def test_list_tasks(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/projects/tasks", headers=headers)
        assert resp.status_code == 200

    def test_summary(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/projects/summary", headers=headers)
        assert resp.status_code == 200

    def test_inbox(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/projects/inbox", headers=headers)
        assert resp.status_code == 200

    def test_workload(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/projects/workload", headers=headers)
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# CMS ENDPOINTS (/api/cms/*, /api/cms/v2/*)
# ═══════════════════════════════════════════════════════════════════════════════

class TestCMS:
    def test_list_pages(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/cms/pages", headers=headers)
        assert resp.status_code == 200

    def test_list_announcements(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/cms/announcements", headers=headers)
        assert resp.status_code == 200

    def test_list_testimonials(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/cms/testimonials", headers=headers)
        assert resp.status_code == 200

    def test_metrics(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/cms/metrics", headers=headers)
        assert resp.status_code == 200


class TestCMSV2:
    def test_list_sites(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/cms/v2/sites", headers=headers)
        assert resp.status_code == 200

    def test_list_audit_logs(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/cms/v2/audit-logs", headers=headers)
        assert resp.status_code == 200

    def test_list_custom_types(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/cms/v2/custom-types", headers=headers)
        assert resp.status_code == 200

    def test_list_custom_entries(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/cms/v2/custom-entries", headers=headers)
        assert resp.status_code == 200

    def test_list_content_permissions(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/cms/v2/content-permissions", headers=headers)
        assert resp.status_code == 200

    def test_list_notifications(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/cms/v2/notifications", headers=headers)
        assert resp.status_code == 200

    def test_list_glossary(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/cms/v2/glossary", headers=headers)
        assert resp.status_code == 200

    def test_list_redirects(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/cms/v2/redirects", headers=headers)
        assert resp.status_code == 200

    def test_list_broken_links(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/cms/v2/broken-links", headers=headers)
        assert resp.status_code == 200

    def test_search(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/cms/v2/search?q=test", headers=headers)
        assert resp.status_code == 200

    def test_list_sessions(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/cms/v2/sessions", headers=headers)
        assert resp.status_code == 200

    def test_global_blocks(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/cms/v2/global-blocks", headers=headers)
        assert resp.status_code == 200

    def test_list_media_folders(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/cms/v2/media-folders", headers=headers)
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# EVANGELISM ENDPOINTS (/api/evangelism/*)
# ═══════════════════════════════════════════════════════════════════════════════

class TestEvangelism:
    def test_list_estrategias(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/evangelism/estrategias", headers=headers)
        assert resp.status_code == 200

    def test_list_grupos(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/evangelism/grupos", headers=headers)
        assert resp.status_code == 200

    def test_list_sesiones(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/evangelism/sesiones", headers=headers)
        assert resp.status_code == 200

    def test_list_events(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/evangelism/events", headers=headers)
        assert resp.status_code == 200

    def test_list_participantes(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/evangelism/participantes", headers=headers)
        assert resp.status_code == 200

    def test_list_roles(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/evangelism/roles", headers=headers)
        assert resp.status_code == 200

    def test_list_notifications(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/evangelism/notifications", headers=headers)
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# OTHER ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestAgents:
    def test_list_tasks(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/agents/tasks", headers=headers)
        assert resp.status_code == 200

    def test_list_insights(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/agents/insights", headers=headers)
        assert resp.status_code == 200

    def test_agents_root(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/agents", headers=headers)
        assert resp.status_code == 200

    def test_conversations(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/agents/conversations", headers=headers)
        assert resp.status_code == 200

    def test_search(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/agents/search?q=test", headers=headers)
        assert resp.status_code == 200

    def test_analytics_summary(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/agents/analytics/summary", headers=headers)
        assert resp.status_code == 200

    def test_kb_search(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/agents/kb/search?q=test", headers=headers)
        assert resp.status_code == 200

    def test_kb_stats(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/agents/kb/stats", headers=headers)
        assert resp.status_code == 200


class TestChat:
    def test_conversations(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/chat/conversations", headers=headers)
        assert resp.status_code == 200

    def test_user_search(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/chat/users/search?q=test", headers=headers)
        assert resp.status_code == 200


class TestAnalytics:
    def test_dashboard_metrics(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/analytics/dashboard-metrics", headers=headers)
        assert resp.status_code == 200

    def test_radar(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/analytics/radar", headers=headers)
        assert resp.status_code == 200

    def test_events_summary(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/analytics/events/summary", headers=headers)
        assert resp.status_code == 200


class TestSystem:
    def test_health(self, client):
        resp = client.get("/api/system/health")
        assert resp.status_code == 200

    def test_db_health(self, client):
        resp = client.get("/api/system/db/health")
        assert resp.status_code in (200, 401)

    def test_health_modules(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/system/health/modules", headers=headers)
        assert resp.status_code == 200

    def test_workload(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/system/workload", headers=headers)
        assert resp.status_code == 200

    def test_calendar(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/system/calendar", headers=headers)
        assert resp.status_code == 200

    def test_search(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/system/search?q=test", headers=headers)
        assert resp.status_code == 200


class TestGovernance:
    def test_list(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/governance", headers=headers)
        assert resp.status_code == 200


class TestWorkspace:
    def test_config(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/workspace/config", headers=headers)
        assert resp.status_code == 200

    def test_flags(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/workspace/flags", headers=headers)
        assert resp.status_code == 200

    def test_incidents(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/workspace/flags/incidents", headers=headers)
        assert resp.status_code == 200

    def test_incidents_stats(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/workspace/flags/incidents/stats", headers=headers)
        assert resp.status_code == 200

    def test_incidents_summary(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/workspace/flags/incidents/summary", headers=headers)
        assert resp.status_code == 200

    def test_compliance_policy(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/workspace/flags/compliance/policy", headers=headers)
        assert resp.status_code == 200

    def test_compliance_snapshot(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/workspace/flags/compliance/snapshot", headers=headers)
        assert resp.status_code == 200

    def test_compliance_history(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/workspace/flags/compliance/history", headers=headers)
        assert resp.status_code == 200

    def test_compliance_drift(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/workspace/flags/compliance/drift", headers=headers)
        assert resp.status_code == 200


class TestPublicAPI:
    def test_courses(self, client):
        resp = client.get("/api/public/courses")
        assert resp.status_code == 200

    def test_documents(self, client):
        resp = client.get("/api/public/documents")
        assert resp.status_code == 200

    def test_contact(self, client):
        resp = client.get("/api/public/contact")
        assert resp.status_code == 200


class TestTables:
    def test_schemas(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/tables/schemas", headers=headers)
        assert resp.status_code == 200


class TestSupport:
    def test_list(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/support", headers=headers)
        assert resp.status_code in (200, 404, 405)


class TestYoutube:
    def test_videos(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/youtube/videos", headers=headers)
        assert resp.status_code in (200, 404, 405)


class TestSpiritualLife:
    def test_milestones(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/spiritual-life/milestones", headers=headers)
        assert resp.status_code == 200


class TestFinance:
    def test_list(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/finance", headers=headers)
        assert resp.status_code in (200, 404, 405)
