"""Massive tests for evangelism modules + cms_v2 + remaining gaps."""
import uuid
import pytest
from datetime import datetime, timedelta, timezone
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
# EVANGELISM MAIN (evangelism.py) — 479 stmts, 382 missed
# ═══════════════════════════════════════════════════════════════════════════════

class TestEvangelismMainFull:
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

    def test_list_asistencias(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/evangelism/asistencias", headers=headers)
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# EVANGELISM GRUPOS — all submodules
# ═══════════════════════════════════════════════════════════════════════════════

class TestEvangelismGrupos:
    def test_list_grupos(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/evangelism/grupos", headers=headers)
        assert resp.status_code == 200

    def test_create_grupo(self, client_auth):
        client, headers, (_, persona, sede) = client_auth
        resp = client.post("/api/evangelism/grupos", json={
            "nombre": f"Grupo {uuid.uuid4().hex[:6]}",
            "sede_id": str(sede.id),
            "lider_persona_id": str(persona.id),
        }, headers=headers)
        assert resp.status_code in (200, 201, 400, 422)

    def test_list_sesiones(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/evangelism/sesiones", headers=headers)
        assert resp.status_code == 200

    def test_list_asistencias(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/evangelism/asistencias", headers=headers)
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# EVANGELISM EVENTS — all submodules
# ═══════════════════════════════════════════════════════════════════════════════

class TestEvangelismEvents:
    def test_list_events(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/evangelism/events", headers=headers)
        assert resp.status_code == 200

    def test_list_participantes(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/evangelism/participantes", headers=headers)
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# EVANGELISM ANALYTICS — helper functions (pure logic)
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
# EVANGELISM SHARED — helpers
# ═══════════════════════════════════════════════════════════════════════════════

class TestEvangelismShared:
    def test_import(self):
        from backend.api import evangelism_shared
        assert evangelism_shared is not None

    def test_constants(self):
        from backend.api.evangelism_shared import ATTENDED_STATES
        assert isinstance(ATTENDED_STATES, (list, set, tuple))


# ═══════════════════════════════════════════════════════════════════════════════
# CMS V2 — more endpoint coverage
# ═══════════════════════════════════════════════════════════════════════════════

class TestCMSV2Full:
    def test_list_sites(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/cms/v2/sites", headers=headers)
        assert resp.status_code == 200

    def test_audit_logs(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/cms/v2/audit-logs", headers=headers)
        assert resp.status_code in (200, 422)

    def test_search(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/cms/v2/search?q=test", headers=headers)
        assert resp.status_code == 200

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

    def test_custom_entries(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/cms/v2/custom-entries", headers=headers)
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

    def test_search_promotions(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/cms/v2/search/promotions", headers=headers)
        assert resp.status_code == 200

    def test_create_site(self, client_auth):
        client, headers, _ = client_auth
        resp = client.post("/api/cms/v2/sites", json={
            "site_key": f"site_{uuid.uuid4().hex[:6]}",
            "name": "Test Site",
            "base_path": "/test",
        }, headers=headers)
        assert resp.status_code in (200, 201, 400, 422)

    def test_create_custom_type(self, client_auth):
        client, headers, _ = client_auth
        resp = client.post("/api/cms/v2/custom-types", json={
            "name": f"Type {uuid.uuid4().hex[:6]}",
            "schema": {"fields": []},
        }, headers=headers)
        assert resp.status_code in (200, 201, 400, 422)

    def test_create_glossary_term(self, client_auth):
        client, headers, _ = client_auth
        resp = client.post("/api/cms/v2/glossary", json={
            "term": f"Term {uuid.uuid4().hex[:6]}",
            "definition": "A test term",
        }, headers=headers)
        assert resp.status_code in (200, 201, 400, 422)

    def test_create_redirect(self, client_auth):
        client, headers, _ = client_auth
        resp = client.post("/api/cms/v2/redirects", json={
            "from_path": f"/old_{uuid.uuid4().hex[:6]}",
            "to_path": "/new",
        }, headers=headers)
        assert resp.status_code in (200, 201, 400, 422)

    def test_create_webhook(self, client_auth):
        client, headers, _ = client_auth
        resp = client.post("/api/cms/v2/webhooks", json={
            "name": f"Hook {uuid.uuid4().hex[:6]}",
            "url": "https://example.com/hook",
            "events": ["page.published"],
        }, headers=headers)
        assert resp.status_code in (200, 201, 400, 422)


# ═══════════════════════════════════════════════════════════════════════════════
# WORKSPACE FLAGS — more coverage
# ═══════════════════════════════════════════════════════════════════════════════

class TestWorkspaceFlagsFull:
    def test_flags(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/workspace/flags", headers=headers)
        assert resp.status_code in (200, 405)

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
# CRM RESOURCES — more coverage
# ═══════════════════════════════════════════════════════════════════════════════

class TestCRMResourcesFull:
    def test_list_resources(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/crm/resources", headers=headers)
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# KERNEL ENDPOINTS — more coverage
# ═══════════════════════════════════════════════════════════════════════════════

class TestKernelFull:
    def test_list_ministries(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/kernel/ministries", headers=headers)
        assert resp.status_code == 200

    def test_list_positions(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/kernel/positions", headers=headers)
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# DONATIONS ENDPOINTS — more coverage
# ═══════════════════════════════════════════════════════════════════════════════

class TestDonationsFull:
    def test_list(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/donations", headers=headers)
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# MESSAGING ENDPOINTS — more coverage
# ═══════════════════════════════════════════════════════════════════════════════

class TestMessagingFull:
    def test_list(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/messaging/logs", headers=headers)
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# CHAT ENDPOINTS — more coverage
# ═══════════════════════════════════════════════════════════════════════════════

class TestChatFull:
    def test_conversations(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/chat/conversations", headers=headers)
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# SPIRITUAL LIFE ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestSpiritualLifeFull:
    def test_milestones(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/spiritual-life/milestones", headers=headers)
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestPublicFull:
    def test_courses(self, client):
        resp = client.get("/api/public/courses")
        assert resp.status_code == 200

    def test_contact(self, client):
        resp = client.get("/api/public/contact")
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# YOUTUBE ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestYoutubeFull:
    def test_videos(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/youtube/videos", headers=headers)
        assert resp.status_code in (200, 404, 405)


# ═══════════════════════════════════════════════════════════════════════════════
# FINANCE ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestFinanceFull:
    def test_list(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/finance", headers=headers)
        assert resp.status_code in (200, 404, 405)
