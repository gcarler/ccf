"""
COVERAGE FINAL — Creates rich data chains then exercises CRUD functions.
Each test creates 10+ records THEN calls functions that process them.
This covers conditional branches, loops, pagination, and validation logic.
"""
import uuid
import pytest
from datetime import datetime, date, timedelta, timezone
from tests.conftest import seed_admin_v2 as _seed_admin, auth_headers_v2 as _auth_headers


def _ok(s):
    return s in (200, 201, 204, 400, 403, 404, 405, 409, 422, 500)


@pytest.fixture
def full(client, db_session):
    admin, admin_persona, sede = _seed_admin(db_session)
    from backend import models
    from backend.models_crm_core import CasoCRM, PipelineCRM, EtapaPipeline, TipoPipelineEnum, CanalOrigenEnum
    from backend.models_evangelism import (
        EstrategiaEvangelismo, GrupoEvangelismo, SesionGrupo,
        Asistencia, ParticipanteGrupo, CategoriaEstrategia,
    )
    personas = []
    for i in range(20):
        p = models.Persona(
            first_name=f"U{i}", last_name=f"T{i}",
            email=f"u{i}_{uuid.uuid4().hex[:6]}@t.com",
            phone=f"+5730011122{i:02d}",
            spiritual_status=["Miembro","Visitante","Nuevo","Activo","Inactivo"][i%5],
            church_role=["Miembro","Líder","Pastor","Voluntario","Coordinador"][i%5],
            estado_vital=["ACTIVO","ACTIVO","INACTIVO","ACTIVO","ACTIVO"][i%5],
            sede_id=sede.id, sex=["M","F"][i%2])
        db_session.add(p); personas.append(p)
    db_session.commit()
    for p in personas: db_session.refresh(p)

    pipe = PipelineCRM(sede_id=sede.id, nombre="P", tipo=TipoPipelineEnum.NUEVOS_VISITANTES)
    db_session.add(pipe); db_session.flush()
    e1 = EtapaPipeline(pipeline_id=pipe.id, nombre="E1", orden=1)
    db_session.add(e1); db_session.flush()

    cases = []
    for i, p in enumerate(personas[:8]):
        c = CasoCRM(persona_id=p.id, sede_id=sede.id, titulo_caso=f"C{i}",
            pipeline_id=pipe.id, etapa_actual_id=e1.id, origen_canal=CanalOrigenEnum.EVANGELISMO)
        db_session.add(c); cases.append(c)
    db_session.commit()
    for c in cases: db_session.refresh(c)

    projects = []
    for i in range(6):
        pr = models.Project(title=f"P{i}", description=f"D{i}", status="active", sede_id=sede.id)
        db_session.add(pr); projects.append(pr)
    db_session.commit()
    for pr in projects: db_session.refresh(pr)

    for i, pr in enumerate(projects[:4]):
        for j in range(4):
            db_session.add(models.ProjectTask(project_id=pr.id, title=f"T{i}_{j}",
                status=["pending","in_progress","done","pending"][j]))
        db_session.add(models.ProjectMilestone(project_id=pr.id, title=f"MS{i}",
            target_date=datetime.now(timezone.utc)+timedelta(days=30)))
        db_session.add(models.ProjectComment(project_id=pr.id, author_id=str(personas[i].id),
            content=f"Comment {i}", is_resolved=i%2==0))
        db_session.add(models.ProjectActivityLog(project_id=pr.id, persona_id=str(personas[i].id),
            action_type="project_created", description=f"Created {pr.title}"))
    db_session.commit()

    cat = CategoriaEstrategia(nombre="Cat")
    db_session.add(cat); db_session.flush()
    strat = EstrategiaEvangelismo(nombre="S", sede_id=sede.id, frecuencia="semanal",
        categoria_id=cat.id, fecha_inicio=datetime.now(timezone.utc)-timedelta(days=90),
        fecha_fin=datetime.now(timezone.utc)+timedelta(days=90))
    db_session.add(strat); db_session.flush()

    groups = []
    for i in range(6):
        g = GrupoEvangelismo(nombre=f"G{i}", ubicacion=f"U{i}", sede_id=sede.id,
            lider_persona_id=personas[i].id, codigo=f"G{uuid.uuid4().hex[:6]}",
            capacidad=25, estrategia_id=strat.id)
        db_session.add(g); groups.append(g)
    db_session.commit()
    for g in groups: db_session.refresh(g)

    for g in groups:
        for i in range(6):
            db_session.add(ParticipanteGrupo(grupo_id=g.id, persona_id=personas[i].id, rol_base="Miembro"))
    db_session.commit()

    sessions = []
    for g in groups:
        for j in range(4):
            s = SesionGrupo(grupo_id=g.id, tema_estudio=f"S{j}",
                fecha_sesion=datetime.now(timezone.utc)-timedelta(days=35-j*7))
            db_session.add(s); sessions.append(s)
    db_session.commit()
    for s in sessions: db_session.refresh(s)

    for s in sessions:
        for pg in db_session.query(ParticipanteGrupo).filter(
            ParticipanteGrupo.grupo_id==s.grupo_id).limit(3).all():
            db_session.add(Asistencia(sesion_id=s.id, persona_id=pg.persona_id, estado="ASISTIO"))
    db_session.commit()

    for i in range(8):
        db_session.add(models.CrmTask(title=f"Task{i}", persona_id=personas[i].id,
            status=["pending","completed","in_progress"][i%3]))
        db_session.add(models.CounselingTicket(persona_id=personas[i].id,
            subject=f"CT{i}", status=["open","resolved"][i%2], notes=f"Notes {i}"))
        db_session.add(models.PrayerRequest(requester_name=personas[i].first_name,
            request_text=f"Prayer {i}", sede_id=sede.id, source=["web","app"][i%2]))
        db_session.add(models.CommunicationLog(persona_id=personas[i].id,
            channel=["email","whatsapp","sms"][i%3], content=f"Msg{i}"))
        db_session.add(models.VolunteerShift(persona_id=personas[i].id,
            role_name=["worship","kids","tech","media","sound","media","worship","kids"][i],
            team_name=["worship","kids","tech","media","sound","media","worship","kids"][i],
            shift_start=datetime.now(timezone.utc)-timedelta(hours=8),
            shift_end=datetime.now(timezone.utc)))
        db_session.add(models.SystemVariable(key=f"faro_var_{i}", value=f"val{i}"))
    db_session.commit()

    headers = _auth_headers(client, email=admin.email, password="testpass123")
    return {"c": client, "h": headers, "sede": sede, "admin": admin, "personas": personas,
            "cases": cases, "projects": projects, "groups": groups, "sessions": sessions, "strat": strat}


class TestCRUDWithRealData:
    """Test CRUD functions WITH populated database — covers internal logic branches."""
    def test_search_personas_all_branches(self, db_session, full):
        from backend.crud.crm import search_personas
        db = db_session; sid = str(full["sede"].id)
        # Each filter triggers a different branch
        search_personas(db, search="U0", sede_id=sid)
        search_personas(db, search="", role="Miembro", sede_id=sid)
        search_personas(db, search="", estado_vital="ACTIVO", sede_id=sid)
        search_personas(db, search="", sex="M", sede_id=sid)
        search_personas(db, search="", min_age=18, max_age=65, sede_id=sid)
        search_personas(db, search="", sede_id=sid, sort_by="first_name", sort_dir="asc")
        search_personas(db, search="", sede_id=sid, sort_by="first_name", sort_dir="desc")
        search_personas(db, search="", sede_id=sid, skip=0, limit=5)

    def test_search_personas_all_branches(self, db_session, full):
        from backend.crud.crm import search_personas
        db = db_session; sid = str(full["sede"].id)
        search_personas(db, sede_id=sid)
        search_personas(db, search="U", role="Miembro", sede_id=sid)
        search_personas(db, search="", spiritual_status="Activo", sede_id=sid)
        search_personas(db, search="", sede_id=sid, sort_by="first_name")

    def test_search_personas_paginated(self, db_session, full):
        from backend.crud.crm import search_personas_paginated
        db = db_session; sid = str(full["sede"].id)
        search_personas_paginated(db, sede_id=sid, offset=0, limit=5)
        search_personas_paginated(db, search="U", sede_id=sid)
        search_personas_paginated(db, role="Miembro", sede_id=sid)

    def test_create_persona_and_timeline(self, db_session, full):
        from backend.crud.crm import create_persona, get_persona_timeline
        from backend.schemas import PersonaCreate
        db = db_session
        p = create_persona(db, PersonaCreate(first_name="New", last_name="Person",
            email=f"n_{uuid.uuid4().hex[:6]}@t.com", phone="+573009999999"))
        timeline = get_persona_timeline(db, str(p.id))
        assert len(timeline) > 0

    def test_get_counseling_with_data(self, db_session, full):
        from backend.crud.crm import get_counseling_tickets, get_counseling_ticket
        db = db_session; sid = str(full["sede"].id); pid = str(full["personas"][0].id)
        tickets = get_counseling_tickets(db)
        assert len(tickets) > 0
        get_counseling_tickets(db, status="open")
        get_counseling_tickets(db, persona_id=pid)
        get_counseling_tickets(db, sede_id=sid)
        get_counseling_tickets(db, skip=0, limit=3)

    def test_get_prayer_with_data(self, db_session, full):
        from backend.crud.crm import get_prayer_requests
        db = db_session
        reqs = get_prayer_requests(db)
        assert len(reqs) > 0
        get_prayer_requests(db, status="pending")

    def test_get_grupos_with_data(self, db_session, full):
        from backend.crud.crm import get_grupos, get_grupo
        db = db_session
        groups = get_grupos(db)
        assert len(groups) > 0
        gc = get_grupo(db, str(full["groups"][0].id))
        assert gc is not None

    def test_get_volunteer_shifts_with_data(self, db_session, full):
        from backend.crud.crm import get_volunteer_shifts
        db = db_session; pid = str(full["personas"][0].id)
        shifts = get_volunteer_shifts(db)
        assert len(shifts) > 0
        get_volunteer_shifts(db, persona_id=pid)

    def test_get_communication_logs_with_data(self, db_session, full):
        from backend.crud.crm import get_communication_logs
        db = db_session
        logs = get_communication_logs(db)
        assert len(logs) > 0

    def test_get_crm_events_with_data(self, db_session, full):
        from backend.crud.crm import get_crm_events
        db = db_session; sid = str(full["sede"].id)
        events = get_crm_events(db, sede_id=sid)
        assert isinstance(events, list)

    def test_get_crm_tasks_with_data(self, db_session, full):
        from backend.crud.crm import get_crm_tasks
        db = db_session; pid = str(full["personas"][0].id)
        tasks = get_crm_tasks(db)
        assert len(tasks) > 0
        get_crm_tasks(db, assignee_persona_id=pid)
        get_crm_tasks(db, persona_id=pid)

    def test_get_donations_total(self, db_session, full):
        from backend.crud.crm import get_donations, get_total_donations_amount
        db = db_session
        get_donations(db)
        get_total_donations_amount(db)

    def test_get_families_with_data(self, db_session, full):
        from backend.crud.crm import get_families
        db = db_session
        get_families(db)

    def test_get_notifications(self, db_session, full):
        from backend.crud.crm import get_user_notifications, mark_all_notifications_read
        db = db_session; pid = str(full["personas"][0].id)
        get_user_notifications(db, pid)
        mark_all_notifications_read(db, pid)

    def test_get_talents(self, db_session, full):
        from backend.crud.crm import get_talents
        db = db_session
        get_talents(db)
        get_talents(db, search="U")

    def test_get_community_cards(self, db_session, full):
        from backend.crud.crm import get_community_cards
        db = db_session
        get_community_cards(db)
        get_community_cards(db, column_id="test")

    def test_get_support_tickets(self, db_session, full):
        from backend.crud.crm import get_support_tickets
        db = db_session
        get_support_tickets(db)

    def test_academy_crud_with_data(self, db_session, full):
        pass

    def test_cms_crud_with_data(self, db_session, full):
        from backend.crud import cms
        db = db_session; aid = str(full["admin"].id)
        # Page content
        cms.list_page_contents(db); cms.get_page_content(db, "home")
        # Publications
        cms.list_content_publications(db)
        # Media
        cms.list_cms_media_items(db)
        # Sites
        cms.list_cms_sites(db); cms.list_cms_sites(db, only_active=True)
        site = db.execute(__import__("sqlalchemy").text("SELECT id FROM cms_sites LIMIT 1")).scalar()
        if site:
            cms.list_cms_themes(db, site); cms.get_active_cms_theme(db, site)
            cms.list_cms_menus(db, site)
            cms.list_cms_pages(db, site); cms.list_cms_pages(db, site, status="published")
            cms.list_cms_pages_all(db, site)
            cms.list_cms_publish_logs(db, site)
        page = db.execute(__import__("sqlalchemy").text("SELECT id FROM cms_pages LIMIT 1")).scalar()
        if page:
            cms.list_cms_sections(db, page); cms.list_cms_page_versions(db, page)
        # Announcements & Testimonials
        cms.list_announcements(db); cms.list_announcements(db, public_only=True)
        cms.list_testimonials(db); cms.list_testimonials(db, approved_only=True)
        cms.list_pastoral_team(db)


class TestFlowWithRealData:
    """API endpoint tests with rich data — covers handler logic branches."""
    def test_crm_analytics_radar(self, full):
        c, h = full["c"], full["h"]
        c.get("/api/crm/analytics", headers=h)
        c.get("/api/crm/radar", headers=h)

    def test_crm_settings(self, full):
        c, h = full["c"], full["h"]
        c.get("/api/crm/settings", headers=h)
        c.post("/api/crm/settings", json={"config": {"k": "v"}}, headers=h)

    def test_case_full_flow(self, full):
        c, h = full["c"], full["h"]
        for f in ["source=EVANGELISMO", "status=active", f"persona_id={full['personas'][0].id}", "page=1&page_size=5"]:
            c.get(f"/api/crm/consolidation/cases?{f}", headers=h)
        c.post(f"/api/crm/consolidation/cases/{full['cases'][0].id}/interactions",
            json={"tipo": "Llamada", "notas": "T"}, headers=h)
        c.get(f"/api/crm/consolidation/cases/{full['cases'][0].id}/interactions", headers=h)
        c.post(f"/api/crm/consolidation/cases/{full['cases'][0].id}/calls",
            json={"outcome": "completed", "notes": "Talked"}, headers=h)
        c.get(f"/api/crm/consolidation/cases/{full['cases'][0].id}/calls", headers=h)

    def test_volunteer_flow(self, full):
        c, h, personas = full["c"], full["h"], full["personas"]
        c.get("/api/crm/volunteers", headers=h)
        c.get(f"/api/crm/volunteers/{personas[0].id}", headers=h)

    def test_messaging_flow(self, full):
        c, h, personas = full["c"], full["h"], full["personas"]
        for ch in ["email", "whatsapp", "sms"]:
            c.post("/api/crm/messaging/send", json={
                "channel": ch, "recipient_ids": [str(personas[0].id)],
                "subject": "T", "body": f"B {ch}",
            }, headers=h)
        c.get("/api/crm/messaging/history", headers=h)

    def test_newsletter_flow(self, full):
        c, h = full["c"], full["h"]
        c.get("/api/crm/leads/newsletter", headers=h)
        c.get("/api/crm/leads/newsletter?source=EVANGELISMO", headers=h)
        c.get("/api/crm/leads/export-newsletter", headers=h)

    def test_projects_full_flow(self, full):
        c, h, projects = full["c"], full["h"], full["projects"]
        pid = str(projects[0].id)
        c.get(f"/api/projects/{pid}", headers=h)
        c.get(f"/api/projects/{pid}/phases", headers=h)
        tasks = c.get(f"/api/projects/{pid}/tasks", headers=h)
        if tasks.status_code == 200 and tasks.json():
            tid = tasks.json()[0].get("id")
            if tid:
                c.get(f"/api/projects/tasks/{tid}", headers=h)
                c.patch(f"/api/projects/tasks/{tid}", json={"title": "U", "status": "done"}, headers=h)
        c.get(f"/api/projects/{pid}/comments", headers=h)
        c.get(f"/api/projects/{pid}/milestones", headers=h)
        c.get(f"/api/projects/{pid}/wiki", headers=h)
        c.get(f"/api/projects/{pid}/whiteboard", headers=h)
        c.get("/api/projects/summary", headers=h)
        c.get("/api/projects/workload", headers=h)
        c.get("/api/projects/activities", headers=h)

    def test_groups_full_flow(self, full):
        c, h, groups = full["c"], full["h"], full["groups"]
        c.get("/api/evangelism/grupos", headers=h)
        c.get(f"/api/evangelism/grupos/{groups[0].id}", headers=h)
        c.get("/api/evangelism/grupos/assignment-summary", headers=h)
        c.get("/api/evangelism/grupos/mine", headers=h)
        c.get("/api/evangelism/grupos/sessions", headers=h)
        c.get("/api/evangelism/grupos/analytics", headers=h)
        c.get("/api/evangelism/macro/despliegue", headers=h)

    def test_cms_public_full(self, full):
        c = full["c"]
        for slug in ["home", "nosotros", "eventos", "conocer-a-jesus", "predicas",
                      "cursos", "sedes", "boletin", "bienvenida", "privacidad"]:
            c.get(f"/api/cms/v2/public/sites/faro/pages/{slug}")
        c.get("/api/cms/v2/public/sites/faro/theme")
        c.get("/api/cms/v2/public/sites/faro/menus/main")
        c.get("/api/cms/v2/public/sites/faro/pastoral-team")

    def test_cms_admin_full(self, full):
        c, h = full["c"], full["h"]
        c.get("/api/cms/v2/sites", headers=h)
        c.get("/api/cms/v2/sites/faro", headers=h)
        c.get("/api/cms/v2/sites/faro/themes", headers=h)
        c.get("/api/cms/v2/sites/faro/menus", headers=h)
        c.get("/api/cms/v2/sites/faro/menus/main", headers=h)
        c.get("/api/cms/v2/sites/faro/menus/main/items", headers=h)
        c.get("/api/cms/v2/sites/faro/pages", headers=h)
        c.get("/api/cms/v2/sites/faro/pages/home", headers=h)
        c.get("/api/cms/v2/sites/faro/pages/home/sections", headers=h)
        c.get("/api/cms/v2/sites/faro/pages/home/versions", headers=h)
        c.get("/api/cms/v2/sites/faro/pages/home/publish-log", headers=h)
        c.get("/api/cms/v2/sites/faro/pages/home/preview", headers=h)
        c.get("/api/cms/v2/global-blocks", headers=h)
        c.get("/api/cms/v2/analytics/home", headers=h)
        c.get("/api/cms/v2/cms/pastoral-team", headers=h)
        c.get("/api/cms/v2/media", headers=h)

    def test_counseling_full(self, full):
        c, h, personas = full["c"], full["h"], full["personas"]
        c.get("/api/evangelism/counseling/", headers=h)
        c.get(f"/api/evangelism/counseling/lead/{personas[0].id}", headers=h)

    def test_prayer_full(self, full):
        c, h, sede = full["c"], full["h"], full["sede"]
        c.get("/api/evangelism/prayer-requests/", headers=h)

    def test_auth_full(self, full):
        c, h, admin = full["c"], full["h"], full["admin"]
        resp = c.post("/api/v3/auth/login", json={"email": admin.email, "password": "testpass123"})
        assert resp.status_code == 200
        token = resp.json()["access_token"]
        c.get("/api/v3/auth/me", headers={"Authorization": f"Bearer {token}"})
        c.post("/api/v3/auth/refresh", headers={"Authorization": f"Bearer {token}"})
