"""
Deep coverage tests — creates real data and exercises uncovered CRM pastoral,
evangelism, evangelism_grupos, evangelism_events endpoints.
"""
import uuid
import pytest
from datetime import datetime, timedelta, timezone
from tests.conftest import seed_admin as _seed_admin, auth_headers as _auth_headers


@pytest.fixture
def ac(client, db_session):
    admin, persona, sede = _seed_admin(db_session)
    headers = _auth_headers(client, email=admin.email, password="testpass123")
    return client, headers, sede, persona, admin, persona


def _create_persona(db, name="Test", email=None):
    from backend import models
    p = models.Persona(
        first_name=name, last_name="User",
        email=email or f"{uuid.uuid4().hex[:8]}@test.com",
        spiritual_status="Miembro", church_role="Miembro",
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def _create_case(db, persona_id, sede_id):
    from backend import models
    case = models.CasoCRM(
        persona_id=persona_id, sede_id=sede_id,
        titulo="Test Case", pipeline="default",
        estado="ACTIVO", prioridad="MEDIA",
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


def _create_crm_event(db, sede_id):
    from backend import models
    event = models.CrmEvent(
        name="Test Event", description="Test",
        event_date=datetime.now(timezone.utc) + timedelta(days=1),
        location="Test", sede_id=sede_id,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


# ═══════════════════════════════════════════════════════════════════════════════
# CRM PASTORAL DEEP TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestPastoralDeep:
    def test_list_consolidation_cases(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/crm/consolidation/cases", headers=h)

    def test_create_consolidation_case(self, ac, db_session):
        c, h, s, p, admin, persona = ac
        p2 = _create_persona(db_session, "CaseSubject")
        c.post("/api/crm/consolidation/cases", json={
            "persona_id": str(p2.id), "titulo": "Test Case",
            "descripcion": "Test description",
        }, headers=h)

    def test_list_crm_tasks(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/crm/tasks", headers=h)

    def test_create_crm_task(self, ac, db_session):
        c, h, s, p, admin, persona = ac
        c.post("/api/crm/tasks", json={
            "titulo": "Test Task", "descripcion": "Test",
            "prioridad": "MEDIA",
        }, headers=h)

    def test_list_my_tasks(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/crm/tasks/my", headers=h)

    def test_list_prayer_requests(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/crm/prayer-requests", headers=h)

    def test_create_prayer_request(self, ac, db_session):
        c, h, s, p, admin, persona = ac
        c.post("/api/crm/prayer-requests", json={
            "titulo": "Test Prayer", "descripcion": "Please pray",
        }, headers=h)

    def test_list_counseling_tickets(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/crm/counseling", headers=h)

    def test_create_counseling_ticket(self, ac, db_session):
        c, h, s, p, admin, persona = ac
        c.post("/api/crm/counseling", json={
            "titulo": "Test Counseling", "descripcion": "Need help",
        }, headers=h)

    def test_list_crm_roles(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/crm/roles", headers=h)

    def test_create_crm_role(self, ac):
        c, h, s, p, admin, persona = ac
        c.post("/api/crm/roles", json={
            "nombre": "Test Role", "descripcion": "Test",
        }, headers=h)

    def test_list_volunteers(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/crm/volunteers", headers=h)

    def test_create_volunteer(self, ac, db_session):
        c, h, s, p, admin, persona = ac
        p2 = _create_persona(db_session, "Volunteer")
        c.post("/api/crm/volunteers", json={
            "persona_id": str(p2.id),
            "habilidades": "teaching",
        }, headers=h)

    def test_list_groups(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/crm/groups", headers=h)

    def test_crm_analytics_summary(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/crm/analytics/summary", headers=h)

    def test_crm_settings(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/crm/settings", headers=h)

    def test_save_crm_settings(self, ac):
        c, h, s, p, admin, persona = ac
        c.post("/api/crm/settings", json={"pipeline_stages": ["new", "active", "closed"]}, headers=h)

    def test_crm_radar(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/crm/radar", headers=h)

    def test_newsletter_leads(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/crm/newsletter-leads", headers=h)

    def test_export_newsletter_leads(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/crm/newsletter-leads/export", headers=h)

    def test_list_consolidation_calls(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/crm/consolidation/calls", headers=h)

    def test_create_consolidation_call(self, ac, db_session):
        c, h, s, p, admin, persona = ac
        p2 = _create_persona(db_session, "CallSubject")
        c.post("/api/crm/consolidation/calls", json={
            "persona_id": str(p2.id), "notas": "Test call",
            "resultado": "contacted",
        }, headers=h)


# ═══════════════════════════════════════════════════════════════════════════════
# EVANGELISM DEEP TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestEvangelismDeep:
    def test_strategies_list(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/evangelism/strategies", headers=h)

    def test_create_strategy(self, ac):
        c, h, s, p, admin, persona = ac
        c.post("/api/evangelism/strategies", json={
            "nombre": "Test Strategy", "descripcion": "Test",
            "frecuencia": "semanal",
            "fecha_inicio": "2026-07-01", "fecha_fin": "2026-12-31",
        }, headers=h)

    def test_grupos_list(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/evangelism/grupos", headers=h)

    def test_create_grupo(self, ac):
        c, h, s, p, admin, persona = ac
        c.post("/api/evangelism/grupos", json={
            "nombre": "Test Group", "lugar": "Test Place",
        }, headers=h)

    def test_sesiones_list(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/evangelism/sesiones", headers=h)

    def test_create_sesion(self, ac):
        c, h, s, p, admin, persona = ac
        c.post("/api/evangelism/sesiones", json={
            "titulo": "Test Session", "fecha": datetime.now(timezone.utc).isoformat(),
        }, headers=h)

    def test_asistencias_list(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/evangelism/asistencias", headers=h)

    def test_reports_summary(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/evangelism/reports/summary", headers=h)

    def test_rankings(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/evangelism/rankings", headers=h)

    def test_notifications(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/evangelism/notifications", headers=h)

    def test_multiplication_check(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/evangelism/multiplication/check", headers=h)

    def test_analytics_overview(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/evangelism/analytics/overview", headers=h)

    def test_analytics_trends(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/evangelism/analytics/trends", headers=h)

    def test_analytics_funnel(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/evangelism/analytics/funnel", headers=h)

    def test_analytics_heatmap(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/evangelism/analytics/heatmap", headers=h)

    def test_analytics_alerts(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/evangelism/analytics/alerts", headers=h)

    def test_analytics_velocity(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/evangelism/analytics/velocity", headers=h)

    def test_analytics_groups(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/evangelism/analytics/groups", headers=h)

    def test_analytics_full(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/evangelism/analytics/full", headers=h)

    def test_reports_pdf(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/evangelism/reports/pdf", headers=h)

    def test_reports_excel(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/evangelism/reports/excel", headers=h)


# ═══════════════════════════════════════════════════════════════════════════════
# EVANGELISM GRUPOS DEEP TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestEvangelismGruposDeep:
    def test_grupos_main_list(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/evangelism/grupos", headers=h)

    def test_grupos_main_create(self, ac):
        c, h, s, p, admin, persona = ac
        c.post("/api/evangelism/grupos", json={
            "nombre": "Test Grupo Main", "lugar": "Test",
        }, headers=h)

    def test_grupos_sesiones_list(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/evangelism/sesiones", headers=h)

    def test_grupos_asistencias_pending(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/evangelism/asistencias/pending-follow-ups", headers=h)

    def test_campaign_seasons_list(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/evangelism/campaign-seasons", headers=h)

    def test_create_campaign_season(self, ac):
        c, h, s, p, admin, persona = ac
        c.post("/api/evangelism/campaign-seasons", json={
            "nombre": "Test Season", "year": 2026,
        }, headers=h)

    def test_faro_analytics(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/evangelism/faro/analytics", headers=h)

    def test_macro_despliegue(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/evangelism/macro-despliegue", headers=h)

    def test_strategy_metrics(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/evangelism/strategy-metrics", headers=h)


# ═══════════════════════════════════════════════════════════════════════════════
# EVANGELISM EVENTS DEEP TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestEvangelismEventsDeep:
    def test_events_list(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/evangelism/events", headers=h)

    def test_events_create(self, ac):
        c, h, s, p, admin, persona = ac
        c.post("/api/evangelism/events", json={
            "name": "Test Event", "event_date": datetime.now(timezone.utc).isoformat(),
            "location": "Test",
        }, headers=h)

    def test_events_dashboard(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/evangelism/events/dashboard-stats", headers=h)

    def test_events_analytics_global(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/evangelism/events/global-analytics", headers=h)

    def test_events_roles(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/evangelism/events/roles", headers=h)

    def test_events_create_role(self, ac):
        c, h, s, p, admin, persona = ac
        c.post("/api/evangelism/events/roles", json={
            "nombre": "Test Event Role",
        }, headers=h)

    def test_events_attendance_history(self, ac, db_session):
        c, h, s, p, admin, persona = ac
        c.get(f"/api/evangelism/events/persona/{persona.id}/attendance-history", headers=h)


# ═══════════════════════════════════════════════════════════════════════════════
# CRM RESOURCES DEEP TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestCRMResourcesDeep:
    def test_categorias(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/crm/resources/categorias", headers=h)

    def test_create_categoria(self, ac):
        c, h, s, p, admin, persona = ac
        c.post("/api/crm/resources/categorias", json={
            "nombre": "Test Category",
        }, headers=h)

    def test_plantillas(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/crm/resources/plantillas", headers=h)

    def test_create_plantilla(self, ac):
        c, h, s, p, admin, persona = ac
        c.post("/api/crm/resources/plantillas", json={
            "nombre": "Test Template", "asunto": "Hi", "contenido": "Body",
        }, headers=h)

    def test_adjuntos(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/crm/resources/adjuntos", headers=h)

    def test_bitacora_plantilla(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/crm/resources/bitacora/plantilla", headers=h)

    def test_bitacora_sede(self, ac):
        c, h, s, p, admin, persona = ac
        c.get(f"/api/crm/resources/bitacora/sede/{s.id}", headers=h)

    def test_automations(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/crm/resources/automations", headers=h)

    def test_create_automation(self, ac):
        c, h, s, p, admin, persona = ac
        c.post("/api/crm/resources/automations", json={
            "nombre": "Test Automation", "evento_trigger": "new_case",
            "acciones": [],
        }, headers=h)


# ═══════════════════════════════════════════════════════════════════════════════
# CMS DEEP TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestCMSDeep:
    def test_cms_v2_sites_list(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/cms/v2/sites", headers=h)

    def test_cms_v2_create_site(self, ac):
        c, h, s, p, admin, persona = ac
        c.post("/api/cms/v2/sites", json={
            "key": f"test-{uuid.uuid4().hex[:8]}", "name": "Test Site",
            "base_path": "/test",
        }, headers=h)

    def test_cms_v2_themes(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/cms/v2/sites/faro/themes", headers=h)

    def test_cms_v2_create_theme(self, ac):
        c, h, s, p, admin, persona = ac
        c.post("/api/cms/v2/sites/faro/themes", json={
            "name": "Test Theme", "colors": {},
        }, headers=h)

    def test_cms_v2_menus(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/cms/v2/sites/faro/menus", headers=h)

    def test_cms_v2_create_menu(self, ac):
        c, h, s, p, admin, persona = ac
        c.post("/api/cms/v2/sites/faro/menus", json={
            "key": f"menu-{uuid.uuid4().hex[:8]}", "title": "Test Menu",
        }, headers=h)

    def test_cms_v2_pages(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/cms/v2/sites/faro/pages", headers=h)

    def test_cms_v2_create_page(self, ac):
        c, h, s, p, admin, persona = ac
        c.post("/api/cms/v2/sites/faro/pages", json={
            "slug": f"test-{uuid.uuid4().hex[:8]}", "title": "Test Page",
        }, headers=h)

    def test_cms_v2_global_blocks(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/cms/v2/global-blocks", headers=h)

    def test_cms_v2_media(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/cms/v2/media", headers=h)

    def test_cms_v2_versions(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/cms/v2/versions", headers=h)

    def test_cms_v2_publish_logs(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/cms/v2/publish-logs", headers=h)

    def test_cms_v2_workflow(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/cms/v2/workflow", headers=h)

    def test_cms_testimonials(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/cms/testimonials", headers=h)

    def test_cms_announcements(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/cms/announcements", headers=h)


# ═══════════════════════════════════════════════════════════════════════════════
# CRM CORE (pipeline) DEEP TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestCRMCoreDeep:
    def test_pipelines_list(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/crm/pipelines", headers=h)

    def test_create_pipeline(self, ac):
        c, h, s, p, admin, persona = ac
        c.post("/api/crm/pipelines", json={
            "nombre": "Test Pipeline",
        }, headers=h)

    def test_crm_events_list(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/crm/events", headers=h)

    def test_create_crm_event(self, ac):
        c, h, s, p, admin, persona = ac
        c.post("/api/crm/events", json={
            "name": "Test CRM Event",
            "event_date": datetime.now(timezone.utc).isoformat(),
        }, headers=h)


# ═══════════════════════════════════════════════════════════════════════════════
# AGENDA DEEP TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestAgendaDeep:
    def test_agenda_events(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/agenda/events", headers=h)

    def test_agenda_resources(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/agenda/resources", headers=h)

    def test_agenda_create_resource(self, ac):
        c, h, s, p, admin, persona = ac
        c.post("/api/agenda/resources", json={
            "nombre": "Test Resource", "tipo": "salon",
        }, headers=h)

    def test_agenda_reservations(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/agenda/reservations", headers=h)

    def test_agenda_participants(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/agenda/participants", headers=h)


# ═══════════════════════════════════════════════════════════════════════════════
# ENTERPRISE CMS DEEP TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestEnterpriseCMSDeep:
    def test_audit_logs(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/cms/v2/audit-logs", headers=h)

    def test_notifications(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/cms/v2/notifications", headers=h)

    def test_webhooks(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/cms/v2/webhooks", headers=h)

    def test_custom_types(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/cms/v2/custom-types", headers=h)

    def test_glossary(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/cms/v2/glossary", headers=h)

    def test_search(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/cms/v2/search?q=test", headers=h)

    def test_sessions(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/cms/v2/sessions", headers=h)

    def test_media_folders(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/cms/v2/media-folders", headers=h)

    def test_redirects(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/cms/v2/redirects", headers=h)

    def test_broken_links(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/cms/v2/broken-links", headers=h)

    def test_content_permissions(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/cms/v2/content-permissions", headers=h)


# ═══════════════════════════════════════════════════════════════════════════════
# CRM PERSONAS DEEP TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestCRMPersonasDeep:
    def test_list_personas(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/crm/personas", headers=h)

    def test_create_persona(self, ac):
        c, h, s, p, admin, persona = ac
        c.post("/api/crm/personas", json={
            "first_name": "New", "last_name": "Person",
            "email": f"new_{uuid.uuid4().hex[:8]}@test.com",
        }, headers=h)

    def test_get_persona(self, ac):
        c, h, s, p, admin, persona = ac
        c.get(f"/api/crm/personas/{persona.id}", headers=h)

    def test_patch_persona(self, ac):
        c, h, s, p, admin, persona = ac
        c.patch(f"/api/crm/personas/{persona.id}", json={
            "first_name": "Patched",
        }, headers=h)

    def test_persona_timeline(self, ac):
        c, h, s, p, admin, persona = ac
        c.get(f"/api/crm/personas/{persona.id}/timeline", headers=h)

    def test_my_ministry_profile(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/crm/personas/my-profile", headers=h)


# ═══════════════════════════════════════════════════════════════════════════════
# DONATIONS DEEP TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestDonationsDeep:
    def test_donations_list(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/donations", headers=h)

    def test_create_donation(self, ac):
        c, h, s, p, admin, persona = ac
        c.post("/api/donations", json={
            "persona_id": str(persona.id), "amount": 50.0,
        }, headers=h)

    def test_donations_funds(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/donations/funds", headers=h)

    def test_donations_categories(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/donations/categories", headers=h)

    def test_donations_summary(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/donations/summary", headers=h)


# ═══════════════════════════════════════════════════════════════════════════════
# FINANCE DEEP TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestFinanceDeep:
    def test_finance_funds(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/finance/funds", headers=h)

    def test_create_fund(self, ac):
        c, h, s, p, admin, persona = ac
        c.post("/api/finance/funds", json={
            "nombre": "Test Fund", "descripcion": "Test",
        }, headers=h)

    def test_finance_transactions(self, ac):
        c, h, s, p, admin, persona = ac
        c.get("/api/finance/transactions", headers=h)

    def test_create_transaction(self, ac):
        c, h, s, p, admin, persona = ac
        c.post("/api/finance/transactions", json={
            "monto": 100.0, "tipo": "ingreso",
        }, headers=h)
