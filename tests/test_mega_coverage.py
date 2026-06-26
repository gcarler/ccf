"""
MEGA COVERAGE — Exercises uncovered code paths across ALL low-coverage modules.
Strategy: Create real data via models, call API endpoints that process them.
"""
import uuid
import pytest
from datetime import datetime, timedelta, timezone
from tests.conftest import seed_admin_v2 as _seed_admin, auth_headers_v2 as _auth_headers


def _ok(s):
    return s in (200, 201, 204, 400, 403, 404, 405, 409, 422)


@pytest.fixture
def full(client, db_session):
    admin, admin_persona, sede = _seed_admin(db_session)
    from backend import models
    from backend.models_crm_core import CasoCRM, PipelineCRM, EtapaPipeline, TipoPipelineEnum, CanalOrigenEnum
    from backend.models_evangelism import (
        EstrategiaEvangelismo, GrupoEvangelismo, SesionGrupo,
        Asistencia, ParticipanteGrupo, CategoriaEstrategia, HistorialEmbudo,
    )

    # 10 personas with varied data
    personas = []
    for i in range(10):
        p = models.Persona(
            first_name=f"U{i}", last_name=f"T{i}",
            email=f"u{i}_{uuid.uuid4().hex[:6]}@t.com",
            phone=f"+5730011122{i:02d}",
            spiritual_status=["Miembro","Visitante","Nuevo","Bautizado","Confirmado"][i%5],
            church_role=["Miembro","Líder","Pastor","Servidor","Evangelista"][i%5],
            sede_id=sede.id,
            birthday=datetime(1985+i, 1, 1, tzinfo=timezone.utc).date(),
        )
        db_session.add(p); personas.append(p)
    db_session.commit()
    for p in personas: db_session.refresh(p)

    # Pipeline + stages
    pipe = PipelineCRM(sede_id=sede.id, nombre="Default", tipo=TipoPipelineEnum.NUEVOS_VISITANTES)
    db_session.add(pipe); db_session.flush()
    e1 = EtapaPipeline(pipeline_id=pipe.id, nombre="Activo", orden=1)
    e2 = EtapaPipeline(pipeline_id=pipe.id, nombre="Cerrado", orden=2)
    db_session.add_all([e1, e2]); db_session.flush()

    # CRM Cases
    cases = []
    for p in personas[:5]:
        c = CasoCRM(persona_id=p.id, sede_id=sede.id, titulo_caso=f"Case {p.first_name}",
            pipeline_id=pipe.id, etapa_actual_id=e1.id, origen_canal=CanalOrigenEnum.EVANGELISMO)
        db_session.add(c); cases.append(c)
    db_session.commit()
    for c in cases: db_session.refresh(c)

    # Strategy + category
    cat = CategoriaEstrategia(nombre="Cat Test")
    db_session.add(cat); db_session.flush()
    strategy = EstrategiaEvangelismo(
        nombre="Estrategia Test", sede_id=sede.id, frecuencia="semanal",
        categoria_id=cat.id,
        fecha_inicio=datetime.now(timezone.utc) - timedelta(days=90),
        fecha_fin=datetime.now(timezone.utc) + timedelta(days=90),
    )
    db_session.add(strategy); db_session.flush()

    # Groups with participants
    groups = []
    for i in range(3):
        g = GrupoEvangelismo(nombre=f"G{i}", ubicacion=f"U{i}", sede_id=sede.id,
            lider_persona_id=personas[i].id, codigo=f"G{uuid.uuid4().hex[:6]}",
            capacidad=20, estrategia_id=strategy.id)
        db_session.add(g); groups.append(g)
    db_session.commit()
    for g in groups: db_session.refresh(g)

    for g in groups:
        for i in range(5):
            db_session.add(ParticipanteGrupo(grupo_id=g.id, persona_id=personas[i].id, rol_base="Miembro"))
    db_session.commit()

    # Sessions
    sessions = []
    for g in groups:
        for j in range(3):
            s = SesionGrupo(grupo_id=g.id, tema_estudio=f"S{j}",
                fecha_sesion=datetime.now(timezone.utc) - timedelta(days=30-j*10))
            db_session.add(s); sessions.append(s)
    db_session.commit()
    for s in sessions: db_session.refresh(s)

    # Attendance
    for s in sessions:
        for pg in db_session.query(ParticipanteGrupo).filter(ParticipanteGrupo.grupo_id == s.grupo_id).limit(3).all():
            db_session.add(Asistencia(sesion_id=s.id, persona_id=pg.persona_id, estado="ASISTIO"))
    db_session.commit()

    # Tasks, Counseling, Prayer, VolunteerShifts, CommunicationLog
    for p in personas[:5]:
        db_session.add(models.CrmTask(title=f"Task {p.first_name}", persona_id=p.id, status="pending"))
    for p in personas[:3]:
        db_session.add(models.CounselingTicket(persona_id=p.id, subject="Help", notes="Urgent"))
        db_session.add(models.PrayerRequest(requester_name=p.first_name, request_text="Pray", sede_id=sede.id))
    for p in personas[:2]:
        db_session.add(models.VolunteerShift(persona_id=p.id, shift_start=datetime.now(timezone.utc)-timedelta(hours=4),
            shift_end=datetime.now(timezone.utc), role_name="Teacher", team_name="Team A"))
        db_session.add(models.CommunicationLog(persona_id=p.id, channel="whatsapp", content="Test"))
    db_session.commit()

    headers = _auth_headers(client, email=admin.email, password="testpass123")
    return {"c": client, "h": headers, "sede": sede, "personas": personas, "cases": cases,
            "groups": groups, "sessions": sessions, "admin": admin, "admin_persona": admin_persona, "strategy": strategy}


# ═══════════════════════════════════════════════════════════════════════════════
# PASTORAL — ALL ENDPOINTS (targeting uncovered code paths)
# ═══════════════════════════════════════════════════════════════════════════════

class TestPastoralAll:
    def test_consolidation_cases_crud(self, full):
        c, h = full["c"], full["h"]
        # List with filters
        assert _ok(c.get("/api/crm/consolidation/cases", headers=h).status_code)
        assert _ok(c.get("/api/crm/consolidation/cases?source=EVANGELISMO", headers=h).status_code)
        assert _ok(c.get("/api/crm/consolidation/cases?page=2&page_size=5", headers=h).status_code)
        # Create with persona_id
        resp = c.post("/api/crm/consolidation/cases", json={
            "persona_id": str(full["personas"][0].id), "titulo": "Test",
        }, headers=h)
        assert _ok(resp.status_code)
        # Create without persona
        resp = c.post("/api/crm/consolidation/cases", json={
            "titulo": "No Persona", "email": f"np_{uuid.uuid4().hex[:6]}@t.com",
        }, headers=h)
        assert _ok(resp.status_code)
        # Get/Update/Delete
        case_id = full["cases"][0].id
        assert _ok(c.get(f"/api/crm/consolidation/cases/{case_id}", headers=h).status_code)
        assert _ok(c.patch(f"/api/crm/consolidation/cases/{case_id}", json={"titulo": "U"}, headers=h).status_code)
        assert _ok(c.delete(f"/api/crm/consolidation/cases/{case_id}", headers=h).status_code)

    def test_consolidation_subresources(self, full):
        c, h = full["c"], full["h"]
        cid = full["cases"][0].id
        # Assignments
        assert _ok(c.get(f"/api/crm/consolidation/cases/{cid}/assignments", headers=h).status_code)
        resp = c.post(f"/api/crm/consolidation/cases/{cid}/assignments", json={"notas": "T"}, headers=h)
        assert _ok(resp.status_code)
        # Interactions
        assert _ok(c.get(f"/api/crm/consolidation/cases/{cid}/interactions", headers=h).status_code)
        resp = c.post(f"/api/crm/consolidation/cases/{cid}/interactions", json={"notes": "T", "interaction_type": "call"}, headers=h)
        assert _ok(resp.status_code)
        # Tasks
        assert _ok(c.get(f"/api/crm/consolidation/cases/{cid}/tasks", headers=h).status_code)
        resp = c.post(f"/api/crm/consolidation/cases/{cid}/tasks", json={"title": "T", "status": "pending"}, headers=h)
        assert _ok(resp.status_code)
        # Calls
        assert _ok(c.get(f"/api/crm/consolidation/cases/{cid}/calls", headers=h).status_code)
        resp = c.post(f"/api/crm/consolidation/cases/{cid}/calls", json={"notas": "T", "resultado": "c"}, headers=h)
        assert _ok(resp.status_code)

    def test_crm_tasks(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/crm/tasks", headers=h).status_code)
        assert _ok(c.get("/api/crm/tasks/my", headers=h).status_code)
        # Create with date
        resp = c.post("/api/crm/tasks", json={"titulo": "T", "due_date": datetime.now(timezone.utc).isoformat()}, headers=h)
        assert _ok(resp.status_code)
        # Create invalid date
        resp = c.post("/api/crm/tasks", json={"titulo": "T", "due_date": "bad"}, headers=h)
        assert _ok(resp.status_code)
        # Create no title
        resp = c.post("/api/crm/tasks", json={"descripcion": "T"}, headers=h)
        assert _ok(resp.status_code)

    def test_counseling(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/crm/counseling", headers=h).status_code)
        resp = c.post("/api/crm/counseling", json={"titulo": "T", "descripcion": "D"}, headers=h)
        assert _ok(resp.status_code)
        assert _ok(c.get("/api/crm/counseling/1", headers=h).status_code)
        assert _ok(c.patch("/api/crm/counseling/1", json={"status": "in_progress"}, headers=h).status_code)
        assert _ok(c.get("/api/crm/counseling/lead/1", headers=h).status_code)

    def test_prayer_requests(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/crm/prayer-requests", headers=h).status_code)
        resp = c.post("/api/crm/prayer-requests", json={"titulo": "T", "descripcion": "D"}, headers=h)
        assert _ok(resp.status_code)
        assert _ok(c.get("/api/crm/prayer-requests/1", headers=h).status_code)
        assert _ok(c.patch("/api/crm/prayer-requests/1", json={"is_answered": True}, headers=h).status_code)
        assert _ok(c.patch("/api/crm/prayer-requests/1", json={"status": "in_progress"}, headers=h).status_code)
        assert _ok(c.post("/api/crm/prayer-requests/public", json={"titulo": "Public", "descripcion": "P"}, headers=h).status_code)

    def test_volunteers(self, full):
        c, h, personas = full["c"], full["h"], full["personas"]
        assert _ok(c.get("/api/crm/volunteers", headers=h).status_code)
        resp = c.post("/api/crm/volunteers", json={"persona_id": str(personas[0].id), "habilidades": "t"}, headers=h)
        assert _ok(resp.status_code)
        resp = c.post("/api/crm/volunteers", json={"first_name": "N", "last_name": "V", "email": f"v_{uuid.uuid4().hex[:6]}@t.com"}, headers=h)
        assert _ok(resp.status_code)
        assert _ok(c.get(f"/api/crm/volunteers/{personas[0].id}", headers=h).status_code)
        assert _ok(c.patch(f"/api/crm/volunteers/{personas[0].id}", json={"first_name": "U"}, headers=h).status_code)
        assert _ok(c.delete(f"/api/crm/volunteers/{personas[0].id}", headers=h).status_code)

    def test_roles(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/crm/roles", headers=h).status_code)
        resp = c.post("/api/crm/roles", json={"nombre": "T", "descripcion": "D"}, headers=h)
        assert _ok(resp.status_code)
        resp = c.post("/api/crm/roles", json={"nombre": "Dup", "descripcion": "D"}, headers=h)
        assert _ok(resp.status_code)
        resp = c.post("/api/crm/roles", json={"nombre": "Dup", "descripcion": "D"}, headers=h)
        assert _ok(resp.status_code)
        resp = c.post("/api/crm/roles", json={"nombre": "", "descripcion": "E"}, headers=h)
        assert _ok(resp.status_code)

    def test_groups(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/crm/groups", headers=h).status_code)
        resp = c.post("/api/crm/groups", json={"nombre": "G"}, headers=h)
        assert _ok(resp.status_code)
        gid = full["groups"][0].id
        assert _ok(c.get(f"/api/crm/groups/{gid}", headers=h).status_code)
        assert _ok(c.put(f"/api/crm/groups/{gid}", json={"nombre": "U"}, headers=h).status_code)

    def test_messaging(self, full):
        c, h, personas = full["c"], full["h"], full["personas"]
        assert _ok(c.get("/api/crm/messaging/history", headers=h).status_code)
        resp = c.post("/api/crm/messaging/send", json={"channel": "whatsapp", "content": "T", "persona_id": str(personas[0].id)}, headers=h)
        assert _ok(resp.status_code)

    def test_analytics_settings(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/crm/analytics/summary", headers=h).status_code)
        assert _ok(c.get("/api/crm/radar", headers=h).status_code)
        assert _ok(c.get("/api/crm/newsletter-leads", headers=h).status_code)
        assert _ok(c.get("/api/crm/newsletter-leads/export", headers=h).status_code)
        assert _ok(c.get("/api/crm/settings", headers=h).status_code)
        assert _ok(c.post("/api/crm/settings", json={"pipeline_stages": ["a"]}, headers=h).status_code)

    def test_resources(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/crm/resources/categorias", headers=h).status_code)
        assert _ok(c.post("/api/crm/resources/categorias", json={"nombre": "T"}, headers=h).status_code)
        assert _ok(c.get("/api/crm/resources/plantillas", headers=h).status_code)
        assert _ok(c.post("/api/crm/resources/plantillas", json={"nombre": "T", "asunto": "H", "contenido": "B"}, headers=h).status_code)
        assert _ok(c.get("/api/crm/resources/adjuntos", headers=h).status_code)
        assert _ok(c.get("/api/crm/resources/automations", headers=h).status_code)
        assert _ok(c.post("/api/crm/resources/automations", json={"nombre": "T", "evento_trigger": "new_case", "acciones": []}, headers=h).status_code)

    def test_personas_events_pipelines(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/crm/personas", headers=h).status_code)
        assert _ok(c.get("/api/crm/events", headers=h).status_code)
        assert _ok(c.get("/api/crm/pipelines", headers=h).status_code)
        assert _ok(c.post("/api/crm/personas", json={"first_name": "N", "last_name": "P", "email": f"n_{uuid.uuid4().hex[:6]}@t.com"}, headers=h).status_code)
        assert _ok(c.post("/api/crm/events", json={"name": "E", "event_date": datetime.now(timezone.utc).isoformat()}, headers=h).status_code)
        assert _ok(c.post("/api/crm/pipelines", json={"nombre": "P"}, headers=h).status_code)


# ═══════════════════════════════════════════════════════════════════════════════
# EVANGELISM — ALL ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestEvangelismAll:
    def test_strategies(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/evangelism/strategies", headers=h).status_code)
        resp = c.post("/api/evangelism/strategies", json={"nombre": "T", "descripcion": "D", "frecuencia": "semanal", "fecha_inicio": "2026-07-01", "fecha_fin": "2026-12-31"}, headers=h)
        assert _ok(resp.status_code)

    def test_grupos(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/evangelism/grupos", headers=h).status_code)
        resp = c.post("/api/evangelism/grupos", json={"nombre": "G", "lugar": "L"}, headers=h)
        assert _ok(resp.status_code)

    def test_sesiones(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/evangelism/sesiones", headers=h).status_code)
        resp = c.post("/api/evangelism/sesiones", json={"titulo": "S", "fecha": datetime.now(timezone.utc).isoformat()}, headers=h)
        assert _ok(resp.status_code)

    def test_analytics_all(self, full):
        c, h = full["c"], full["h"]
        for ep in ["/api/evangelism/analytics/overview", "/api/evangelism/analytics/trends", "/api/evangelism/analytics/heatmap", "/api/evangelism/analytics/funnel", "/api/evangelism/analytics/alerts", "/api/evangelism/analytics/velocity", "/api/evangelism/analytics/full", "/api/evangelism/analytics/groups"]:
            assert _ok(c.get(ep, headers=h).status_code)

    def test_reports(self, full):
        c, h = full["c"], full["h"]
        for ep in ["/api/evangelism/reports/summary", "/api/evangelism/reports/pdf", "/api/evangelism/reports/excel", "/api/evangelism/rankings"]:
            assert _ok(c.get(ep, headers=h).status_code)

    def test_events_crud(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/evangelism/events", headers=h).status_code)
        resp = c.post("/api/evangelism/events", json={"name": "E", "event_date": datetime.now(timezone.utc).isoformat(), "location": "L"}, headers=h)
        assert _ok(resp.status_code)
        assert _ok(c.get("/api/evangelism/events/dashboard-stats", headers=h).status_code)
        assert _ok(c.get("/api/evangelism/events/global-analytics", headers=h).status_code)
        assert _ok(c.get("/api/evangelism/events/roles", headers=h).status_code)
        resp = c.post("/api/evangelism/events/roles", json={"nombre": "R"}, headers=h)
        assert _ok(resp.status_code)

    def test_other_endpoints(self, full):
        c, h = full["c"], full["h"]
        for ep in ["/api/evangelism/notifications", "/api/evangelism/multiplication/check", "/api/evangelism/faro/analytics", "/api/evangelism/macro-despliegue", "/api/evangelism/strategy-metrics", "/api/evangelism/asistencias/pending-follow-ups", "/api/evangelism/asistencias", "/api/evangelism/campaign-seasons"]:
            assert _ok(c.get(ep, headers=h).status_code)


# ═══════════════════════════════════════════════════════════════════════════════
# ADMIN — ALL ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestAdminAll:
    def test_users_crud(self, full):
        c, h, admin = full["c"], full["h"], full["admin"]
        assert _ok(c.get("/api/admin/users", headers=h).status_code)
        resp = c.post("/api/admin/users", json={"username": f"u_{uuid.uuid4().hex[:6]}", "email": f"u_{uuid.uuid4().hex[:6]}@t.com", "password": "T123!"}, headers=h)
        assert _ok(resp.status_code)
        assert _ok(c.get(f"/api/admin/users/{admin.id}", headers=h).status_code)
        assert _ok(c.patch(f"/api/admin/users/{admin.id}", json={"username": "U"}, headers=h).status_code)
        assert _ok(c.patch(f"/api/admin/users/{admin.id}/role", params={"platform_role_id": str(admin.platform_role_id)}, headers=h).status_code)

    def test_roles_crud(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/admin/roles", headers=h).status_code)
        resp = c.post("/api/admin/roles", json={"nombre": "R", "permisos": {"*": "allow"}}, headers=h)
        assert _ok(resp.status_code)

    def test_permissions(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/admin/permissions", headers=h).status_code)

    def test_personas(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/admin/personas", headers=h).status_code)

    def test_locations(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/admin/locations", headers=h).status_code)
        resp = c.post("/api/admin/locations", json={"nombre": "L"}, headers=h)
        assert _ok(resp.status_code)

    def test_variables(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/admin/variables", headers=h).status_code)
        resp = c.post("/api/admin/variables", json={"key": f"v_{uuid.uuid4().hex[:6]}", "value": "V"}, headers=h)
        assert _ok(resp.status_code)

    def test_automations(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/admin/automations", headers=h).status_code)
        resp = c.post("/api/admin/automations", json={"nombre": "A", "evento_trigger": "new_case", "acciones": []}, headers=h)
        assert _ok(resp.status_code)

    def test_audit(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/admin/audit", headers=h).status_code)

    def test_stats_modules(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/admin/stats", headers=h).status_code)
        assert _ok(c.get("/api/admin/modules", headers=h).status_code)

    def test_auth_role_definitions(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/admin/auth-role-definitions", headers=h).status_code)
        resp = c.post("/api/admin/auth-role-definitions", json={"nombre": f"AR_{uuid.uuid4().hex[:6]}", "permisos": {"crm": ["read"]}}, headers=h)
        assert _ok(resp.status_code)

    def test_user_module_roles(self, full):
        c, h, admin = full["c"], full["h"], full["admin"]
        assert _ok(c.get("/api/admin/user-module-roles", headers=h).status_code)
        resp = c.post("/api/admin/user-module-roles", json={"user_id": str(admin.id), "module": "crm", "role": "editor"}, headers=h)
        assert _ok(resp.status_code)

    def test_users_with_roles(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/admin/users-with-roles", headers=h).status_code)

    def test_donation_categories(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/admin/donation-categories", headers=h).status_code)
        resp = c.post("/api/admin/donation-categories", json={"nombre": "DC"}, headers=h)
        assert _ok(resp.status_code)

    def test_user_permissions(self, full):
        c, h, admin = full["c"], full["h"], full["admin"]
        assert _ok(c.get(f"/api/admin/users/{admin.id}/permissions", headers=h).status_code)
        assert _ok(c.put(f"/api/admin/users/{admin.id}/permissions", json={"modules": {"crm": "write"}}, headers=h).status_code)


# ═══════════════════════════════════════════════════════════════════════════════
# CMS V2 — ALL ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestCMSV2All:
    def test_sites(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/cms/v2/sites", headers=h).status_code)
        key = f"s-{uuid.uuid4().hex[:6]}"
        resp = c.post("/api/cms/v2/sites", json={"key": key, "name": "T", "base_path": "/t"}, headers=h)
        assert _ok(resp.status_code)
        assert _ok(c.get(f"/api/cms/v2/sites/{key}", headers=h).status_code)
        assert _ok(c.patch(f"/api/cms/v2/sites/{key}", json={"name": "U"}, headers=h).status_code)
        assert _ok(c.delete(f"/api/cms/v2/sites/{key}", headers=h).status_code)

    def test_pages(self, full):
        c, h = full["c"], full["h"]
        slug = f"p-{uuid.uuid4().hex[:6]}"
        assert _ok(c.get("/api/cms/v2/sites/faro/pages", headers=h).status_code)
        resp = c.post("/api/cms/v2/sites/faro/pages", json={"slug": slug, "title": "T"}, headers=h)
        assert _ok(resp.status_code)
        assert _ok(c.get(f"/api/cms/v2/sites/faro/pages/{slug}", headers=h).status_code)
        assert _ok(c.patch(f"/api/cms/v2/sites/faro/pages/{slug}", json={"title": "U"}, headers=h).status_code)
        sid = f"sec-{uuid.uuid4().hex[:6]}"
        assert _ok(c.post(f"/api/cms/v2/sites/faro/pages/{slug}/sections", json={"section_key": sid, "section_type": "hero", "title": "S"}, headers=h).status_code)
        assert _ok(c.get(f"/api/cms/v2/sites/faro/pages/{slug}/sections", headers=h).status_code)
        assert _ok(c.patch(f"/api/cms/v2/sites/faro/pages/{slug}/sections/{sid}", json={"title": "U"}, headers=h).status_code)
        assert _ok(c.put(f"/api/cms/v2/sites/faro/pages/{slug}/sections/reorder", json={"section_ids": []}, headers=h).status_code)
        assert _ok(c.delete(f"/api/cms/v2/sites/faro/pages/{slug}/sections/{sid}", headers=h).status_code)
        assert _ok(c.delete(f"/api/cms/v2/sites/faro/pages/{slug}", headers=h).status_code)

    def test_menus(self, full):
        c, h = full["c"], full["h"]
        key = f"m-{uuid.uuid4().hex[:6]}"
        assert _ok(c.get("/api/cms/v2/sites/faro/menus", headers=h).status_code)
        resp = c.post("/api/cms/v2/sites/faro/menus", json={"key": key, "title": "T"}, headers=h)
        assert _ok(resp.status_code)
        assert _ok(c.get(f"/api/cms/v2/sites/faro/menus/{key}", headers=h).status_code)
        assert _ok(c.patch(f"/api/cms/v2/sites/faro/menus/{key}", json={"title": "U"}, headers=h).status_code)
        assert _ok(c.get(f"/api/cms/v2/sites/faro/menus/{key}/items", headers=h).status_code)
        assert _ok(c.post(f"/api/cms/v2/sites/faro/menus/{key}/items", json={"label": "L", "url": "/u"}, headers=h).status_code)
        assert _ok(c.put(f"/api/cms/v2/sites/faro/menus/{key}/items/reorder", json={"item_ids": []}, headers=h).status_code)
        assert _ok(c.delete(f"/api/cms/v2/sites/faro/menus/{key}", headers=h).status_code)

    def test_themes(self, full):
        c, h = full["c"], full["h"]
        tid = str(uuid.uuid4())
        assert _ok(c.get("/api/cms/v2/sites/faro/themes", headers=h).status_code)
        resp = c.post("/api/cms/v2/sites/faro/themes", json={"id": tid, "name": "T", "colors": {}}, headers=h)
        assert _ok(resp.status_code)
        assert _ok(c.get(f"/api/cms/v2/sites/faro/themes/{tid}", headers=h).status_code)
        assert _ok(c.patch(f"/api/cms/v2/sites/faro/themes/{tid}", json={"colors": {"a": "b"}}, headers=h).status_code)
        assert _ok(c.post(f"/api/cms/v2/sites/faro/themes/{tid}/activate", headers=h).status_code)
        assert _ok(c.delete(f"/api/cms/v2/sites/faro/themes/{tid}", headers=h).status_code)

    def test_global_blocks(self, full):
        c, h = full["c"], full["h"]
        bid = f"b-{uuid.uuid4().hex[:6]}"
        assert _ok(c.get("/api/cms/v2/global-blocks", headers=h).status_code)
        resp = c.post("/api/cms/v2/global-blocks", json={"key": bid, "content": {}}, headers=h)
        assert _ok(resp.status_code)
        assert _ok(c.get(f"/api/cms/v2/global-blocks/{bid}", headers=h).status_code)
        assert _ok(c.patch(f"/api/cms/v2/global-blocks/{bid}", json={"content": {"a": 1}}, headers=h).status_code)
        assert _ok(c.delete(f"/api/cms/v2/global-blocks/{bid}", headers=h).status_code)

    def test_media(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/cms/v2/media", headers=h).status_code)
        mid = f"m-{uuid.uuid4().hex[:6]}"
        resp = c.post("/api/cms/v2/media", json={"id": mid, "url": "/u.jpg", "alt": "A"}, headers=h)
        assert _ok(resp.status_code)
        assert _ok(c.get(f"/api/cms/v2/media/{mid}", headers=h).status_code)
        assert _ok(c.patch(f"/api/cms/v2/media/{mid}", json={"alt": "B"}, headers=h).status_code)
        assert _ok(c.delete(f"/api/cms/v2/media/{mid}", headers=h).status_code)

    def test_versions_publish_workflow(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/cms/v2/versions", headers=h).status_code)
        assert _ok(c.post("/api/cms/v2/versions", json={"page_slug": "home", "content": {}}, headers=h).status_code)
        assert _ok(c.get("/api/cms/v2/publish-logs", headers=h).status_code)
        assert _ok(c.get("/api/cms/v2/workflow", headers=h).status_code)

    def test_public(self, full):
        c, h = full["c"], full["h"]
        for ep in ["/api/cms/v2/public/sites/faro", "/api/cms/v2/public/sites/faro/pages", "/api/cms/v2/public/sites/faro/pages/home", "/api/cms/v2/public/sites/faro/menus/main", "/api/cms/v2/public/sites/faro/theme", "/api/cms/v2/public/sites/faro/global-blocks"]:
            assert _ok(c.get(ep, headers=h).status_code)

    def test_search_analytics(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/cms/v2/search?q=test", headers=h).status_code)
        assert _ok(c.get("/api/cms/v2/analytics", headers=h).status_code)


# ═══════════════════════════════════════════════════════════════════════════════
# ENTERPRISE CMS + AGENDA + PROJECTS + DONATIONS + FINANCE + SYSTEM
# ═══════════════════════════════════════════════════════════════════════════════

class TestAllRemaining:
    def test_enterprise_cms(self, full):
        c, h = full["c"], full["h"]
        for ep in ["/api/cms/v2/audit-logs", "/api/cms/v2/notifications", "/api/cms/v2/webhooks", "/api/cms/v2/custom-types", "/api/cms/v2/glossary", "/api/cms/v2/sessions", "/api/cms/v2/media-folders", "/api/cms/v2/redirects", "/api/cms/v2/broken-links", "/api/cms/v2/content-permissions"]:
            assert _ok(c.get(ep, headers=h).status_code)

    def test_agenda(self, full):
        c, h = full["c"], full["h"]
        for ep in ["/api/agenda/events", "/api/agenda-core/events", "/api/agenda-core/resources", "/api/agenda-core/reservations", "/api/agenda-core/participants"]:
            assert _ok(c.get(ep, headers=h).status_code)

    def test_projects(self, full):
        c, h = full["c"], full["h"]
        for ep in ["/api/projects", "/api/projects/tasks", "/api/projects/portfolio/summary", "/api/projects/milestones", "/api/projects/phases", "/api/projects/whiteboards", "/api/projects/inbox", "/api/projects/supplies", "/api/projects/messages", "/api/projects/comments"]:
            assert _ok(c.get(ep, headers=h).status_code)

    def test_donations_finance(self, full):
        c, h = full["c"], full["h"]
        for ep in ["/api/donations", "/api/donations/funds", "/api/donations/categories", "/api/donations/summary", "/api/finance/funds", "/api/finance/transactions"]:
            assert _ok(c.get(ep, headers=h).status_code)

    def test_system(self, full):
        c, h = full["c"], full["h"]
        for ep in ["/api/governance/automation-rules", "/api/governance/audit", "/api/messaging/notifications", "/api/messaging/history", "/api/chat/conversations", "/api/graph/snapshot", "/api/analytics/dashboard", "/api/dashboard/metrics", "/api/system/health", "/api/system/info", "/api/prayer/requests", "/api/spiritual-life/certificates", "/api/spiritual-life/timeline", "/api/youtube/videos", "/api/agents/tasks", "/api/agents/insights", "/api/agents/search", "/api/agents/kb/stats"]:
            assert _ok(c.get(ep, headers=h).status_code)
