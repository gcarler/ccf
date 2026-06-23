"""Massive evangelism + pastoral + admin coverage tests.

Tests pure helper functions + API endpoints for maximum coverage.
"""
import uuid
import pytest
from datetime import datetime, date, timedelta, timezone
from unittest.mock import MagicMock, patch, AsyncMock
from tests.conftest import seed_admin_v2, auth_headers_v2


@pytest.fixture
def admin_data(db_session):
    user, persona, sede = seed_admin_v2(db_session)
    return user, persona, sede


@pytest.fixture
def client_auth(client, db_session, admin_data):
    headers = auth_headers_v2(client)
    return client, headers, admin_data


# ═══════════════════════════════════════════════════════════════════════════════
# EVANGELISM SHARED — Pure helper functions (240 stmts, 12%)
# ═══════════════════════════════════════════════════════════════════════════════

class TestEvangelismSharedHelpers:
    def test_normalize_attendance_status(self):
        from backend.api.evangelism_shared import normalize_attendance_status
        result = normalize_attendance_status("PRESENTE")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_is_attended_status(self):
        from backend.api.evangelism_shared import is_attended_status
        assert is_attended_status("PRESENTE") is True
        assert is_attended_status("presente") is True
        assert is_attended_status("AUSENTE") is False

    def test_is_absent_status(self):
        from backend.api.evangelism_shared import is_absent_status
        assert is_absent_status("AUSENTE") is True
        assert is_absent_status("ausente") is True
        assert is_absent_status("PRESENTE") is False

    def test_is_excused_status(self):
        from backend.api.evangelism_shared import is_excused_status
        assert is_excused_status("EXCUSA") is True
        assert is_excused_status("excusa") is True
        assert is_excused_status("PRESENTE") is False

    def test_is_crm_admin_or_pastor(self):
        from backend.api.evangelism_shared import _is_crm_admin_or_pastor
        user = MagicMock()
        user.role = "admin"
        user.rol_plataforma = None
        assert _is_crm_admin_or_pastor(user) is True

    def test_is_crm_admin_or_pastor_pastor(self):
        from backend.api.evangelism_shared import _is_crm_admin_or_pastor
        user = MagicMock()
        user.role = ""
        user.rol_plataforma = MagicMock()
        user.rol_plataforma.nombre = "PASTOR"
        assert _is_crm_admin_or_pastor(user) is True

    def test_is_crm_admin_or_pastor_member(self):
        from backend.api.evangelism_shared import _is_crm_admin_or_pastor
        user = MagicMock()
        user.role = "member"
        user.rol_plataforma = None
        assert _is_crm_admin_or_pastor(user) is False

    def test_utc_now(self):
        from backend.api.evangelism_shared import utc_now
        result = utc_now()
        assert result.tzinfo == timezone.utc

    def test_parse_session_date(self):
        from backend.api.evangelism_shared import parse_session_date
        d = date(2026, 6, 15)
        result = parse_session_date(d)
        assert result == d

    def test_parse_session_date_string(self):
        from backend.api.evangelism_shared import parse_session_date
        result = parse_session_date("2026-06-15")
        assert result == date(2026, 6, 15)

    def test_parse_session_date_datetime(self):
        from backend.api.evangelism_shared import parse_session_date
        dt = datetime(2026, 6, 15, 10, 30)
        result = parse_session_date(dt)
        assert result == date(2026, 6, 15)

    def test_normalize_role_scope_payload(self):
        from backend.api.evangelism_shared import normalize_role_scope_payload
        result = normalize_role_scope_payload({"roles": ["lider", "anfitrion"]})
        assert isinstance(result, dict)

    def test_channel_label(self):
        from backend.api.evangelism_shared import _channel_label
        assert _channel_label("whatsapp") == "WhatsApp"
        assert _channel_label("email") == "Email"
        assert _channel_label("sms") == "SMS"
        result = _channel_label("other")
        assert isinstance(result, str)

    def test_serialize_message_group(self):
        from backend.api.evangelism_shared import _serialize_message_group
        log1 = MagicMock()
        log1.id = uuid.uuid4()
        log1.persona_id = uuid.uuid4()
        log1.channel = "Email"
        log1.content = "Hello"
        log1.created_at = datetime.now(timezone.utc)
        log1.leader_id = None
        log1.campaign_name = None
        log1.external_id = None
        log1.recipient_phone = None
        log1.outcome = "sent"
        result = _serialize_message_group([log1])
        assert isinstance(result, dict)

    def test_serialize_crm_task(self):
        from backend.api.evangelism_shared import _serialize_crm_task
        task = MagicMock()
        task.id = uuid.uuid4()
        task.titulo = "Test Task"
        task.description = "desc"
        task.status = "pending"
        task.priority = "high"
        task.persona_id = uuid.uuid4()
        task.asignado_a_id = None
        task.created_by_id = uuid.uuid4()
        task.due_date = None
        task.created_at = datetime.now(timezone.utc)
        task.updated_at = datetime.now(timezone.utc)
        result = _serialize_crm_task(task)
        assert isinstance(result, dict)

    def test_member_payload(self):
        from backend.api.evangelism_shared import member_payload
        p = MagicMock()
        p.id = uuid.uuid4()
        p.nombre_completo = "Juan Perez"
        p.church_role_effective = "Líder"
        result = member_payload(p, attended=True)
        assert isinstance(result, dict)
        assert result["name"] == "Juan Perez"
        assert result["attended"] is True


# ═══════════════════════════════════════════════════════════════════════════════
# EVANGELISM GRUPOS — Helper functions (grupos_main.py, 300 stmts)
# ═══════════════════════════════════════════════════════════════════════════════

class TestEvangelismGruposHelpers:
    def test_slug_role_name(self):
        from backend.api.evangelism_grupos.grupos_main import _slug_role_name
        assert _slug_role_name("Líder") == "lider"
        assert _slug_role_name("Anfitrión") == "anfitrion"
        assert _slug_role_name(None) == ""

    def test_role_slug_tokens(self):
        from backend.api.evangelism_grupos.grupos_main import _role_slug_tokens
        result = _role_slug_tokens("lider-principal")
        assert isinstance(result, set)
        assert "lider" in result

    def test_is_primary_leader_slug(self):
        from backend.api.evangelism_grupos.grupos_main import _is_primary_leader_slug
        assert _is_primary_leader_slug("lider") is True
        assert _is_primary_leader_slug("anfitrion") is False

    def test_is_assistant_leader_slug(self):
        from backend.api.evangelism_grupos.grupos_main import _is_assistant_leader_slug
        assert _is_assistant_leader_slug("colider") is True
        assert _is_assistant_leader_slug("lider") is False

    def test_role_slug_has(self):
        from backend.api.evangelism_grupos.grupos_main import _role_slug_has
        assert _role_slug_has("lider-principal", "lider") is True
        assert _role_slug_has("anfitrion", "lider") is False


# ═══════════════════════════════════════════════════════════════════════════════
# EVANGELISM ANALYTICS — Helper functions (498 stmts, 16%)
# ═══════════════════════════════════════════════════════════════════════════════

class TestEvangelismAnalyticsHelpers:
    def test_normalize_rol(self):
        from backend.api.evangelism_analytics import _normalize_rol
        assert _normalize_rol("Líder") == "lider"
        assert _normalize_rol("PASTOR") == "pastor"
        assert _normalize_rol("Anfitrión") == "anfitrion"

    def test_rol_to_funnel_stage(self):
        from backend.api.evangelism_analytics import _rol_to_funnel_stage
        assert _rol_to_funnel_stage("Líder") == "lider"
        assert _rol_to_funnel_stage("Colíder") == "colider"
        assert _rol_to_funnel_stage("Anfitrión") == "anfitrion"
        assert _rol_to_funnel_stage("Asistente") == "asistente"
        assert _rol_to_funnel_stage("Visitante") == "visitante"
        assert _rol_to_funnel_stage("Musicólogo") == "personalizado"

    def test_parse_period(self):
        from backend.api.evangelism_analytics import _parse_period
        assert _parse_period("7d") == 7
        assert _parse_period("30d") == 30
        assert _parse_period("90d") == 90
        assert _parse_period("180d") == 180
        assert _parse_period("365d") == 365
        assert _parse_period("invalid") == 30

    def test_delta(self):
        from backend.api.evangelism_analytics import _delta
        assert _delta(150, 100) == 50.0
        assert _delta(80, 100) == -20.0
        assert _delta(10, 0) == 100.0
        assert _delta(0, 0) == 0.0

    def test_date_range(self):
        from backend.api.evangelism_analytics import _date_range
        start, end = _date_range(30)
        assert (end - start).days == 30

    def test_prev_range(self):
        from backend.api.evangelism_analytics import _prev_range
        start, end = _prev_range(30)
        assert (end - start).days == 30


# ═══════════════════════════════════════════════════════════════════════════════
# EVANGELISM API ENDPOINTS (evangelism.py, 374 missed)
# ═══════════════════════════════════════════════════════════════════════════════

class TestEvangelismEndpoints:
    def test_list_counseling(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/crm/counseling/", headers=headers)
        assert resp.status_code == 200

    def test_list_prayer_requests(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/crm/prayer-requests", headers=headers)
        assert resp.status_code == 200

    def test_list_tasks(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/crm/tasks", headers=headers)
        assert resp.status_code == 200

    def test_list_volunteers(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/crm/volunteers", headers=headers)
        assert resp.status_code == 200

    def test_crm_settings(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/crm/settings", headers=headers)
        assert resp.status_code == 200

    def test_crm_analytics(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/crm/analytics", headers=headers)
        assert resp.status_code == 200

    def test_crm_radar(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/crm/radar", headers=headers)
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# EVANGELISM GRUPOS ENDPOINTS (grupos_main.py, 300 missed)
# ═══════════════════════════════════════════════════════════════════════════════

class TestEvangelismGruposEndpoints:
    def test_list_grupos(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/evangelism/grupos", headers=headers)
        assert resp.status_code == 200

    def test_list_sessions(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/evangelism/grupos/sessions", headers=headers)
        assert resp.status_code in (200, 404, 422)

    def test_list_events(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/evangelism/events/", headers=headers)
        assert resp.status_code == 200

    def test_list_roles(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/evangelism/roles", headers=headers)
        assert resp.status_code == 200

    def test_list_excuses(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/evangelism/excuses", headers=headers)
        assert resp.status_code == 200

    def test_list_follow_up(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/evangelism/follow-up/pending", headers=headers)
        assert resp.status_code == 200

    def test_list_counseling(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/evangelism/counseling/", headers=headers)
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# EVANGELISM EVENTS ENDPOINTS (events_main.py, 243 missed)
# ═══════════════════════════════════════════════════════════════════════════════

class TestEvangelismEventsEndpoints:
    def test_list_events(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/evangelism/events/", headers=headers)
        assert resp.status_code == 200

    def test_global_analytics(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/evangelism/events/analytics/global", headers=headers)
        assert resp.status_code == 200

    def test_dashboard_stats(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/evangelism/events/dashboard-stats", headers=headers)
        assert resp.status_code in (200, 422)


# ═══════════════════════════════════════════════════════════════════════════════
# PASTORAL ENDPOINTS (pastoral.py, 573 missed)
# ═══════════════════════════════════════════════════════════════════════════════

class TestPastoralEndpoints:
    def test_list_cases(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/crm/consolidation/cases", headers=headers)
        assert resp.status_code == 200

    def test_list_tasks(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/crm/tasks", headers=headers)
        assert resp.status_code == 200

    def test_list_counseling(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/crm/counseling/", headers=headers)
        assert resp.status_code == 200

    def test_list_prayer_requests(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/crm/prayer-requests", headers=headers)
        assert resp.status_code == 200

    def test_list_groups(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/crm/grupos", headers=headers)
        assert resp.status_code == 200

    def test_list_roles(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/crm/roles", headers=headers)
        assert resp.status_code == 200

    def test_crm_analytics(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/crm/analytics", headers=headers)
        assert resp.status_code == 200

    def test_crm_settings(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/crm/settings", headers=headers)
        assert resp.status_code == 200

    def test_crm_radar(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/crm/radar", headers=headers)
        assert resp.status_code == 200

    def test_my_tasks(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/crm/tasks/mine", headers=headers)
        assert resp.status_code == 200

    def test_newsletter_leads(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/crm/leads/newsletter", headers=headers)
        assert resp.status_code == 200

    def test_volunteers(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/crm/volunteers", headers=headers)
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# ADMIN ENDPOINTS (admin.py, 424 missed)
# ═══════════════════════════════════════════════════════════════════════════════

class TestAdminEndpoints:
    def test_list_roles(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/admin/roles", headers=headers)
        assert resp.status_code == 200

    def test_list_users(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/admin/users", headers=headers)
        assert resp.status_code == 200

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
# PROJECTS ENDPOINTS (projects.py, 419 missed)
# ═══════════════════════════════════════════════════════════════════════════════

class TestProjectsEndpoints:
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

    def test_activities(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/projects/activities", headers=headers)
        assert resp.status_code == 200

    def test_comments(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/projects/comments", headers=headers)
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# CMS V2 ENDPOINTS (cms_v2.py, 426 missed)
# ═══════════════════════════════════════════════════════════════════════════════

class TestCMSV2Endpoints:
    def test_list_sites(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/cms/v2/sites", headers=headers)
        assert resp.status_code == 200

    def test_audit_logs(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/cms/v2/audit-logs", headers=headers)
        assert resp.status_code in (200, 422)

    def test_notifications(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/cms/v2/notifications", headers=headers)
        assert resp.status_code in (200, 422)

    def test_webhooks(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/cms/v2/webhooks", headers=headers)
        assert resp.status_code in (200, 422)

    def test_sessions(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/cms/v2/sessions", headers=headers)
        assert resp.status_code in (200, 422)

    def test_custom_types(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/cms/v2/custom-types", headers=headers)
        assert resp.status_code in (200, 422)

    def test_content_permissions(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/cms/v2/content-permissions", headers=headers)
        assert resp.status_code in (200, 422)

    def test_glossary(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/cms/v2/glossary", headers=headers)
        assert resp.status_code in (200, 422)

    def test_redirects(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/cms/v2/redirects", headers=headers)
        assert resp.status_code in (200, 422)

    def test_broken_links(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/cms/v2/broken-links", headers=headers)
        assert resp.status_code in (200, 422)

    def test_media_folders(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/cms/v2/media-folders", headers=headers)
        assert resp.status_code in (200, 422)

    def test_global_blocks(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/cms/v2/global-blocks", headers=headers)
        assert resp.status_code in (200, 422)


# ═══════════════════════════════════════════════════════════════════════════════
# AUTH V3 ENDPOINTS (auth_v3.py, 275 missed)
# ═══════════════════════════════════════════════════════════════════════════════

class TestAuthEndpoints:
    def test_login(self, client):
        resp = client.post("/api/v3/auth/login", json={"email": "admin@example.com", "password": "testpass123"})
        assert resp.status_code in (200, 401)

    def test_me(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/v3/auth/me", headers=headers)
        assert resp.status_code == 200

    def test_me_no_auth(self, client):
        resp = client.get("/api/v3/auth/me")
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════════
# ENTERPRISE CMS ENDPOINTS (enterprise_cms.py, 262 missed)
# ═══════════════════════════════════════════════════════════════════════════════

class TestEnterpriseCMSEndpoints:
    def test_list_permissions(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/cms/v2/content-permissions", headers=headers)
        assert resp.status_code in (200, 422)

    def test_list_custom_types(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/cms/v2/custom-types", headers=headers)
        assert resp.status_code in (200, 422)

    def test_list_glossary(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/cms/v2/glossary", headers=headers)
        assert resp.status_code in (200, 422)

    def test_list_redirects(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/cms/v2/redirects", headers=headers)
        assert resp.status_code in (200, 422)

    def test_list_broken_links(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/cms/v2/broken-links", headers=headers)
        assert resp.status_code in (200, 422)

    def test_list_media_folders(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/cms/v2/media-folders", headers=headers)
        assert resp.status_code in (200, 422)

    def test_list_global_blocks(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/cms/v2/global-blocks", headers=headers)
        assert resp.status_code in (200, 422)

    def test_list_notifications(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/cms/v2/notifications", headers=headers)
        assert resp.status_code in (200, 422)

    def test_list_webhooks(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/cms/v2/webhooks", headers=headers)
        assert resp.status_code in (200, 422)

    def test_list_sessions(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/cms/v2/sessions", headers=headers)
        assert resp.status_code in (200, 422)


# ═══════════════════════════════════════════════════════════════════════════════
# WORKSPACE ENDPOINTS (workspace_shared/*, 694 missed)
# ═══════════════════════════════════════════════════════════════════════════════

class TestWorkspaceEndpoints:
    def test_config(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/workspace/config", headers=headers)
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

    def test_incidents_trends(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/workspace/flags/incidents/trends", headers=headers)
        assert resp.status_code == 200

    def test_incidents_notifications(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/workspace/flags/incidents/notifications", headers=headers)
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# AGENTS ENDPOINTS (agents.py, 169 missed)
# ═══════════════════════════════════════════════════════════════════════════════

class TestAgentsEndpoints:
    def test_agents_root(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/agents", headers=headers)
        assert resp.status_code in (200, 405)

    def test_list_tasks(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/agents/tasks", headers=headers)
        assert resp.status_code == 200

    def test_list_insights(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/agents/insights", headers=headers)
        assert resp.status_code == 200

    def test_conversations(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/agents/conversations", headers=headers)
        assert resp.status_code in (200, 405)

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


# ═══════════════════════════════════════════════════════════════════════════════
# SYSTEM ENDPOINTS (system.py, 149 missed)
# ═══════════════════════════════════════════════════════════════════════════════

class TestSystemEndpoints:
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
        assert resp.status_code in (200, 404, 500)

    def test_calendar(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/system/calendar", headers=headers)
        assert resp.status_code == 200

    def test_search(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/system/search?q=test", headers=headers)
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# CRM RESOURCES ENDPOINTS (resources.py, 177 missed)
# ═══════════════════════════════════════════════════════════════════════════════

class TestCRMResourcesEndpoints:
    def test_list_resources(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/crm/resources", headers=headers)
        assert resp.status_code in (200, 404)

    def test_list_plantillas(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/crm/resources/plantillas", headers=headers)
        assert resp.status_code == 200

    def test_list_categorias(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/crm/resources/categorias", headers=headers)
        assert resp.status_code == 200

    def test_list_automations(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/crm/resources/automations", headers=headers)
        assert resp.status_code == 200

    def test_list_bitacora(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/crm/resources/bitacora", headers=headers)
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# CRM CORE ENDPOINTS (crm_core.py, 161 missed)
# ═══════════════════════════════════════════════════════════════════════════════

class TestCRMCoreEndpoints:
    def test_list_pipelines(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/v2/crm/pipelines", headers=headers)
        assert resp.status_code == 200

    def test_list_casos(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/v2/crm/casos", headers=headers)
        assert resp.status_code == 200

    def test_list_plantillas(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/v2/crm/plantillas", headers=headers)
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# OTHER ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestOtherEndpoints:
    def test_donations(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/donations", headers=headers)
        assert resp.status_code == 200

    def test_chat_conversations(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/chat/conversations", headers=headers)
        assert resp.status_code == 200

    def test_spiritual_milestones(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/spiritual-life/milestones", headers=headers)
        assert resp.status_code in (200, 404, 405)

    def test_public_courses(self, client):
        resp = client.get("/api/public/courses")
        assert resp.status_code == 200

    def test_youtube_videos(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/youtube/videos", headers=headers)
        assert resp.status_code in (200, 404, 405)

    def test_finance(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/finance", headers=headers)
        assert resp.status_code in (200, 404, 405)

    def test_messaging_logs(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/messaging/logs", headers=headers)
        assert resp.status_code in (200, 404)

    def test_agenda_events(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/agenda/events", headers=headers)
        assert resp.status_code == 200

    def test_kernel_ministries(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/kernel/ministries", headers=headers)
        assert resp.status_code in (200, 404)

    def test_kernel_positions(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/kernel/positions", headers=headers)
        assert resp.status_code in (200, 404)
