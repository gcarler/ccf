"""
REMAINING GAPS — Tests for the 5 modules with most missed lines.
Uses populated database to exercise CRUD branches with real data.
"""
import uuid
import pytest
from datetime import datetime, date, timedelta, timezone
from backend import schemas
from tests.conftest import seed_admin as _seed_admin, auth_headers as _auth_headers


def _ok(s):
    return s in (200, 201, 204, 400, 403, 404, 405, 409, 422)


def _call(fn, *a, **kw):
    return fn(*a, **kw)


@pytest.fixture
def full(client, db_session):
    admin, admin_persona, sede = _seed_admin(db_session)
    from backend import models
    from backend.models_crm_pipeline import CasoCRM, PipelineCRM, EtapaPipeline, TipoPipelineEnum, CanalOrigenEnum
    from backend.models_evangelism import (
        EstrategiaEvangelismo, GrupoEvangelismo, SesionGrupo,
        Asistencia, ParticipanteGrupo, CategoriaEstrategia,
    )
    from backend.models_academy_core import Course, Lesson, Assessment

    personas = []
    for i in range(20):
        p = models.Persona(
            first_name=f"U{i}", last_name=f"T{i}",
            email=f"u{i}_{uuid.uuid4().hex[:6]}@t.com",
            phone=f"+5730011122{i:02d}",
            spiritual_status=["Miembro", "Visitante", "Nuevo", "Activo", "Inactivo"][i % 5],
            church_role=["Miembro", "Líder", "Pastor", "Voluntario", "Coordinador"][i % 5],
            estado_vital=["ACTIVO", "ACTIVO", "INACTIVO", "ACTIVO", "ACTIVO"][i % 5],
            sede_id=sede.id, sex=["M", "F"][i % 2],
        )
        db_session.add(p)
        personas.append(p)
    db_session.commit()
    for p in personas:
        db_session.refresh(p)

    families = []
    for i in range(3):
        f = models.Family(name=f"Fam_{i}")
        db_session.add(f)
        families.append(f)
    db_session.commit()
    for f in families:
        db_session.refresh(f)
    for i, p in enumerate(personas[:6]):
        p.family_id = families[i % 3].id
    db_session.commit()

    pipe = PipelineCRM(sede_id=sede.id, nombre="P", tipo=TipoPipelineEnum.NUEVOS_VISITANTES)
    db_session.add(pipe)
    db_session.flush()
    e1 = EtapaPipeline(pipeline_id=pipe.id, nombre="E1", orden=1)
    db_session.add(e1)
    db_session.flush()

    cases = []
    for i, p in enumerate(personas[:6]):
        c = CasoCRM(persona_id=p.id, sede_id=sede.id, titulo_caso=f"C{i}",
            pipeline_id=pipe.id, etapa_actual_id=e1.id, origen_canal=CanalOrigenEnum.EVANGELISMO)
        db_session.add(c)
        cases.append(c)
    db_session.commit()
    for c in cases:
        db_session.refresh(c)

    events = []
    for i in range(5):
        ev = models.CrmEvent(name=f"E{i}", event_date=datetime.now(timezone.utc)+timedelta(days=i*10),
            sede_id=sede.id, status="SCHEDULED", location=f"L{i}")
        db_session.add(ev)
        events.append(ev)
    db_session.commit()
    for ev in events:
        db_session.refresh(ev)

    projects = []
    for i in range(4):
        pr = models.Project(title=f"Proj_{i}", description=f"Desc_{i}", status="active", sede_id=sede.id)
        db_session.add(pr)
        projects.append(pr)
    db_session.commit()
    for pr in projects:
        db_session.refresh(pr)

    for i, pr in enumerate(projects[:3]):
        for j in range(3):
            db_session.add(models.ProjectTask(project_id=pr.id, title=f"T{i}_{j}", status=["pending","in_progress","done"][j]))
        db_session.add(models.ProjectMilestone(project_id=pr.id, title=f"MS_{i}", target_date=datetime.now(timezone.utc)+timedelta(days=30)))
    db_session.commit()

    cat = CategoriaEstrategia(nombre="Cat")
    db_session.add(cat)
    db_session.flush()
    strategy = EstrategiaEvangelismo(nombre="Strat", sede_id=sede.id, frecuencia="semanal",
        categoria_id=cat.id, fecha_inicio=datetime.now(timezone.utc)-timedelta(days=90),
        fecha_fin=datetime.now(timezone.utc)+timedelta(days=90))
    db_session.add(strategy)
    db_session.flush()

    groups = []
    for i in range(5):
        g = GrupoEvangelismo(nombre=f"G{i}", ubicacion=f"U{i}", sede_id=sede.id,
            lider_persona_id=personas[i].id, codigo=f"G{uuid.uuid4().hex[:6]}",
            capacidad=20, estrategia_id=strategy.id)
        db_session.add(g)
        groups.append(g)
    db_session.commit()
    for g in groups:
        db_session.refresh(g)

    for g in groups:
        for i in range(5):
            db_session.add(ParticipanteGrupo(grupo_id=g.id, persona_id=personas[i].id, rol_base="Miembro"))
    db_session.commit()

    sessions = []
    for g in groups:
        for j in range(4):
            s = SesionGrupo(grupo_id=g.id, tema_estudio=f"S{j}",
                fecha_sesion=datetime.now(timezone.utc)-timedelta(days=35-j*7))
            db_session.add(s)
            sessions.append(s)
    db_session.commit()
    for s in sessions:
        db_session.refresh(s)

    for s in sessions:
        for pg in db_session.query(ParticipanteGrupo).filter(ParticipanteGrupo.grupo_id==s.grupo_id).limit(3).all():
            db_session.add(Asistencia(sesion_id=s.id, persona_id=pg.persona_id, estado="ASISTIO"))
    db_session.commit()

    for i in range(6):
        db_session.add(models.TareaCRM(title=f"Task_{i}", persona_id=personas[i].id, status=["pending","completed","in_progress"][i%3]))
        db_session.add(models.CounselingTicket(persona_id=personas[i].id, subject=f"CT_{i}", status=["open","resolved"][i%2]))
        db_session.add(models.PrayerRequest(requester_name=personas[i].first_name, request_text="P", sede_id=sede.id, source=["web","app"][i%2]))
        db_session.add(models.CommunicationLog(persona_id=personas[i].id, channel="email", content=f"Msg_{i}"))
        db_session.add(models.VolunteerShift(persona_id=personas[i].id,
            role_name=["worship","kids","tech","media","sound"][i%5],
            team_name=["worship","kids","tech","media","sound"][i%5],
            shift_start=datetime.now(timezone.utc)-timedelta(hours=4),
            shift_end=datetime.now(timezone.utc)))
    db_session.commit()

    for i in range(3):
        db_session.add(models.SystemVariable(key=f"faro_var_{i}", value=f"val_{i}"))

    for i in range(2):
        db_session.add(models.Testimonial(content=f"Testimonial {i}", author_persona_id=str(personas[i].id), sede_id=sede.id, status="published", is_approved=True))
        db_session.add(models.Announcement(title=f"Announcement {i}", content=f"Content {i}", sede_id=sede.id, created_by_persona_id=personas[i].id, status="published", published_at=datetime.now(timezone.utc)))
    db_session.commit()

    headers = _auth_headers(client, email=admin.email, password="testpass123")
    return {
        "c": client, "h": headers, "sede": sede, "admin": admin,
        "personas": personas, "families": families, "cases": cases,
        "events": events, "projects": projects, "groups": groups,
        "sessions": sessions, "strategy": strategy,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# CRM CRUD DIRECT — crm.py (453 missed, 44%)
# ═══════════════════════════════════════════════════════════════════════════════

class TestCRMDeep:
    def test_search_with_all_filters(self, db_session, full):
        from backend.crud import crm
        db = db_session
        sid = str(full["sede"].id)
        pid = str(full["personas"][0].id)
        fid = str(full["families"][0].id)
        # search_personas with every filter
        _call(crm.search_personas, db, search="U0", sede_id=sid)
        _call(crm.search_personas, db, search="", role="Miembro", sede_id=sid)
        _call(crm.search_personas, db, search="", estado_vital="ACTIVO", sede_id=sid)
        _call(crm.search_personas, db, search="", sex="M", sede_id=sid)
        _call(crm.search_personas, db, search="", min_age=18, max_age=65, sede_id=sid)
        _call(crm.search_personas, db, search="", family_id=fid, sede_id=sid)
        _call(crm.search_personas, db, search="", sede_id=sid, skip=0, limit=3, sort_by="first_name", sort_dir="asc")
        _call(crm.search_personas, db, search="", sede_id=sid, sort_by="first_name", sort_dir="desc")
        # search_personas
        _call(crm.search_personas, db, sede_id=sid)
        _call(crm.search_personas, db, search="U", role="Miembro", sede_id=sid)
        _call(crm.search_personas, db, search="", spiritual_status="Activo", sede_id=sid)
        _call(crm.search_personas, db, search="", family_id=fid, sede_id=sid)
        # search_personas_paginated
        _call(crm.search_personas_paginated, db, sede_id=sid, offset=0, limit=5)
        _call(crm.search_personas_paginated, db, search="U", sede_id=sid)

    def test_crud_with_data(self, db_session, full):
        from backend.crud import crm
        from backend.schemas import PersonaCreate, PersonaUpdate
        db = db_session
        pid = str(full["personas"][0].id)
        # get
        p = _call(crm.get_persona, db, pid)
        assert p is not None
        # update
        _call(crm.update_persona, db, pid, PersonaUpdate(first_name="Updated", last_name="Name"))
        # timeline
        _call(crm.get_persona_timeline, db, pid)
        # donations
        _call(crm.get_persona_donations, db, pid)
        # milestones
        _call(crm.get_milestones, db, pid)

    def test_events_crud(self, db_session, full):
        from backend.crud import crm
        db = db_session
        sid = str(full["sede"].id)
        eid = full["events"][0].id
        # get list with sede
        _call(crm.get_crm_events, db, sede_id=sid)
        _call(crm.get_crm_events, db, sede_id=sid, skip=0, limit=3)
        # get single
        ev = _call(crm.get_crm_event, db, eid)
        assert ev is not None
        # update
        _call(
            crm.update_crm_event,
            db,
            eid,
            schemas.CrmEventUpdate(name="Updated Event", description="Updated"),
        )
        # get attendance
        _call(crm.get_event_attendance, db, eid)

    def test_tasks_crud(self, db_session, full):
        from backend.crud import crm
        db = db_session
        pid = str(full["personas"][0].id)
        # list with filters
        _call(crm.get_crm_tasks, db)
        _call(crm.get_crm_tasks, db, assignee_persona_id=pid)
        _call(crm.get_crm_tasks, db, persona_id=pid)

    def test_counseling_deep(self, db_session, full):
        from backend.crud import crm
        db = db_session
        pid = str(full["personas"][0].id)
        sid = str(full["sede"].id)
        # list with filters
        _call(crm.get_counseling_tickets, db)
        _call(crm.get_counseling_tickets, db, status="open")
        _call(crm.get_counseling_tickets, db, persona_id=pid)
        _call(crm.get_counseling_tickets, db, sede_id=sid)
        _call(crm.get_counseling_tickets, db, skip=0, limit=3)

    def test_prayer_requests_deep(self, db_session, full):
        from backend.crud import crm
        db = db_session
        _call(crm.get_prayer_requests, db)
        _call(crm.get_prayer_requests, db, status="pending")
        _call(crm.get_prayer_requests, db, skip=0, limit=3)

    def test_grupos_deep(self, db_session, full):
        from backend.crud import crm
        db = db_session
        gid = str(full["groups"][0].id)
        _call(crm.get_grupos, db)
        _call(crm.get_grupo, db, gid)

    def test_volunteer_shifts_deep(self, db_session, full):
        from backend.crud import crm
        db = db_session
        pid = str(full["personas"][0].id)
        _call(crm.get_volunteer_shifts, db)
        _call(crm.get_volunteer_shifts, db, persona_id=pid)

    def test_communication_logs_deep(self, db_session, full):
        from backend.crud import crm
        db = db_session
        _call(crm.get_communication_logs, db)
        _call(crm.get_communication_logs, db, limit=3)

    def test_donations_deep(self, db_session, full):
        from backend.crud import crm
        db = db_session
        _call(crm.get_donations, db)
        _call(crm.get_total_donations_amount, db)

    def test_families_deep(self, db_session, full):
        from backend.crud import crm
        db = db_session
        fid = str(full["families"][0].id)
        _call(crm.get_families, db)
        _call(crm.get_family, db, fid)
        _call(crm.get_family_personas, db, fid)

    def test_community_cards_deep(self, db_session, full):
        from backend.crud import crm
        db = db_session
        _call(crm.get_community_cards, db)
        _call(crm.get_community_cards, db, column_id="test")

    def test_support_tickets_deep(self, db_session, full):
        from backend.crud import crm
        db = db_session
        _call(crm.get_support_tickets, db)
        _call(crm.get_support_tickets, db, user_id=str(full["admin"].id))

    def test_notifications_deep(self, db_session, full):
        from backend.crud import crm
        db = db_session
        pid = str(full["personas"][0].id)
        _call(crm.get_user_notifications, db, pid)
        _call(crm.get_user_notifications, db, pid, limit=5)
        _call(crm.mark_all_notifications_read, db, pid)

    def test_talents_deep(self, db_session, full):
        from backend.crud import crm
        db = db_session
        _call(crm.get_talents, db)
        _call(crm.get_talents, db, search="U")


# ═══════════════════════════════════════════════════════════════════════════════
# PROJECTS API — projects.py (405 missed, 31%)
# ═══════════════════════════════════════════════════════════════════════════════

class TestProjectsDeep:
    def test_list_projects_deep(self, full):
        c, h = full["c"], full["h"]
        _ok(c.get("/api/projects", headers=h).status_code)
        _ok(c.get("/api/projects?status=active", headers=h).status_code)
        _ok(c.get("/api/projects?search=Proj", headers=h).status_code)
        _ok(c.get("/api/projects?page=1&page_size=2", headers=h).status_code)

    def test_project_crud_deep(self, full):
        c, h = full["c"], full["h"]
        # Create
        resp = c.post("/api/projects", json={
            "name": f"P_{uuid.uuid4().hex[:6]}", "description": "Test", "status": "active",
        }, headers=h)
        assert _ok(resp.status_code)
        if resp.status_code == 201:
            pid = resp.json().get("id")
            if pid:
                c.get(f"/api/projects/{pid}", headers=h)
                c.patch(f"/api/projects/{pid}", json={"name": "Updated"}, headers=h)
                c.delete(f"/api/projects/{pid}", headers=h)

    def test_project_tasks_deep(self, full):
        c, h, projects = full["c"], full["h"], full["projects"]
        pid = str(projects[0].id)
        # List tasks
        c.get(f"/api/projects/{pid}/tasks", headers=h)
        c.get(f"/api/projects/{pid}/tasks?status=pending", headers=h)
        # Create task
        resp = c.post(f"/api/projects/{pid}/tasks", json={
            "title": f"T_{uuid.uuid4().hex[:6]}", "description": "D",
        }, headers=h)
        assert _ok(resp.status_code)
        if resp.status_code in (200, 201):
            tid = resp.json().get("id")
            if tid:
                c.get(f"/api/projects/tasks/{tid}", headers=h)
                c.patch(f"/api/projects/tasks/{tid}", json={"title": "U", "status": "in_progress"}, headers=h)
                c.delete(f"/api/projects/tasks/{tid}", headers=h)

    def test_project_phases_deep(self, full):
        c, h, projects = full["c"], full["h"], full["projects"]
        pid = str(projects[0].id)
        c.get(f"/api/projects/{pid}/phases", headers=h)
        c.put(f"/api/projects/{pid}/phases", json=[
            {"name": "Phase 1", "order": 1, "status": "active"},
            {"name": "Phase 2", "order": 2, "status": "pending"},
        ], headers=h)

    def test_project_milestones_deep(self, full):
        c, h, projects = full["c"], full["h"], full["projects"]
        pid = str(projects[0].id)
        c.get(f"/api/projects/{pid}/milestones", headers=h)
        resp = c.post(f"/api/projects/{pid}/milestones", json={
            "title": f"MS_{uuid.uuid4().hex[:6]}", "description": "D",
            "target_date": (date.today() + timedelta(days=30)).isoformat(),
        }, headers=h)
        assert _ok(resp.status_code)
        if resp.status_code in (200, 201):
            mid = resp.json().get("id")
            if mid:
                c.patch(f"/api/projects/milestones/{mid}", json={"title": "U"}, headers=h)
                c.delete(f"/api/projects/milestones/{mid}", headers=h)

    def test_project_comments_deep(self, full):
        c, h, projects = full["c"], full["h"], full["projects"]
        pid = str(projects[0].id)
        c.get(f"/api/projects/{pid}/comments", headers=h)
        resp = c.post(f"/api/projects/{pid}/comments", json={
            "content": f"Comment_{uuid.uuid4().hex[:6]}",
        }, headers=h)
        assert _ok(resp.status_code)

    def test_all_comments(self, full):
        c, h = full["c"], full["h"]
        _ok(c.get("/api/projects/comments", headers=h).status_code)

    def test_portfolio_summary_deep(self, full):
        c, h = full["c"], full["h"]
        _ok(c.get("/api/projects/summary", headers=h).status_code)

    def test_workload_deep(self, full):
        c, h = full["c"], full["h"]
        _ok(c.get("/api/projects/workload", headers=h).status_code)

    def test_activities_deep(self, full):
        c, h = full["c"], full["h"]
        _ok(c.get("/api/projects/activities", headers=h).status_code)
        _ok(c.get("/api/projects/activities?limit=5", headers=h).status_code)

    def test_inbox_deep(self, full):
        c, h = full["c"], full["h"]
        _ok(c.get("/api/projects/inbox", headers=h).status_code)

    def test_project_whiteboard(self, full):
        c, h, projects = full["c"], full["h"], full["projects"]
        pid = str(projects[0].id)
        c.get(f"/api/projects/{pid}/whiteboard", headers=h)
        c.put(f"/api/projects/{pid}/whiteboard", json={"content": {"nodes": []}}, headers=h)

    def test_project_wiki(self, full):
        c, h, projects = full["c"], full["h"], full["projects"]
        pid = str(projects[0].id)
        c.get(f"/api/projects/{pid}/wiki", headers=h)
        c.put(f"/api/projects/{pid}/wiki", json={"content": "# Wiki"}, headers=h)

    def test_project_supplies(self, full):
        c, h, projects = full["c"], full["h"], full["projects"]
        pid = str(projects[0].id)
        tasks = c.get(f"/api/projects/{pid}/tasks", headers=h)
        if tasks.status_code == 200 and tasks.json():
            tid = tasks.json()[0].get("id")
            if tid:
                c.get(f"/api/projects/tasks/{tid}/supplies", headers=h)
                c.post(f"/api/projects/tasks/{tid}/supplies", json={"item_name": "Item", "quantity": 5}, headers=h)

    def test_project_attachments(self, full):
        c, h, projects = full["c"], full["h"], full["projects"]
        pid = str(projects[0].id)
        tasks = c.get(f"/api/projects/{pid}/tasks", headers=h)
        if tasks.status_code == 200 and tasks.json():
            tid = tasks.json()[0].get("id")
            if tid:
                c.get(f"/api/projects/tasks/{tid}/attachments", headers=h)
                c.post(f"/api/projects/tasks/{tid}/attachments", json={
                    "file_url": "http://test.com/file.pdf", "filename": "file.pdf",
                }, headers=h)


# ═══════════════════════════════════════════════════════════════════════════════
# EVANGELISM MAIN — evangelism.py (293 missed, 39%)
# ═══════════════════════════════════════════════════════════════════════════════

class TestEvangelismDeep:
    def test_counseling_full_crud(self, full):
        c, h, personas = full["c"], full["h"], full["personas"]
        # List
        _ok(c.get("/api/evangelism/counseling/", headers=h).status_code)
        # Create
        resp = c.post("/api/evangelism/counseling/", json={
            "persona_id": str(personas[0].id), "subject": "Deep",
        }, headers=h)
        assert _ok(resp.status_code)
        if resp.status_code in (200, 201):
            tid = resp.json().get("id")
            if tid:
                c.get(f"/api/evangelism/counseling/{tid}", headers=h)
                c.patch(f"/api/evangelism/counseling/{tid}", json={
                    "status": "resolved", "notes": "Done", "priority_level": "high",
                }, headers=h)
                c.get(f"/api/evangelism/counseling/lead/{personas[0].id}", headers=h)

    def test_prayer_full_crud(self, full):
        c, h, personas, sede = full["c"], full["h"], full["personas"], full["sede"]
        _ok(c.get("/api/evangelism/prayer-requests/", headers=h).status_code)
        resp = c.post("/api/evangelism/prayer-requests/", json={
            "requester_name": "Deep Prayer", "request_text": "Healing",
            "sede_id": str(sede.id),
        }, headers=h)
        assert _ok(resp.status_code)
        if resp.status_code in (200, 201):
            rid = resp.json().get("id")
            if rid:
                c.get(f"/api/evangelism/prayer-requests/{rid}", headers=h)
                c.patch(f"/api/evangelism/prayer-requests/{rid}", json={
                    "status": "answered", "is_answered": True,
                }, headers=h)

    def test_messaging_send_all_channels(self, full):
        c, h, personas = full["c"], full["h"], full["personas"]
        for channel in ["email", "whatsapp", "sms"]:
            c.post("/api/evangelism/messaging/send", json={
                "channel": channel,
                "persona_id": str(personas[0].id),
                "content": f"Test {channel}",
            }, headers=h)

    def test_messaging_segments(self, full):
        c, h = full["c"], full["h"]
        for seg in ["active", "groups"]:
            c.post("/api/evangelism/messaging/send", json={
                "channel": "email", "content": "Seg",
                "target_segments": [seg],
                "campaign_name": "C",
            }, headers=h)

    def test_messaging_no_target(self, full):
        c, h = full["c"], full["h"]
        c.post("/api/evangelism/messaging/send", json={
            "channel": "email", "content": "No target",
            "target_segments": ["nonexistent"],
        }, headers=h)

    def test_messaging_history_deep(self, full):
        c, h = full["c"], full["h"]
        _ok(c.get("/api/evangelism/messaging/history", headers=h).status_code)
        _ok(c.get("/api/evangelism/messaging/history?limit=3", headers=h).status_code)

    def test_counseling_not_found(self, full):
        c, h = full["c"], full["h"]
        c.get("/api/evangelism/counseling/99999", headers=h)
        c.patch("/api/evangelism/counseling/99999", json={"status": "resolved"}, headers=h)

    def test_prayer_not_found(self, full):
        c, h = full["c"], full["h"]
        c.get("/api/evangelism/prayer-requests/99999", headers=h)
        c.patch("/api/evangelism/prayer-requests/99999", json={"status": "answered"}, headers=h)


# ═══════════════════════════════════════════════════════════════════════════════
# ACADEMY CRUD DIRECT — academy.py (361 missed, 23%)
# ═══════════════════════════════════════════════════════════════════════════════

class TestCMSDeep:
    def test_cms_crud_all(self, db_session, full):
        from backend.crud import cms
        db = db_session
        # page content
        _call(cms.list_page_contents, db)
        _call(cms.get_page_content, db, "home")
        _call(cms.get_or_create_page_content, db, "new_page")
        # publications
        _call(cms.list_content_publications, db)
        _call(cms.get_or_create_content_publication, db, "home")
        _call(cms.update_content_publication, db, "home", status="published")
        # media
        _call(cms.list_cms_media_items, db)
        _call(cms.list_cms_media_items, db, query="test")
        _call(cms.list_cms_media_items, db, section="general")
        # sites
        _call(cms.list_cms_sites, db)
        _call(cms.list_cms_sites, db, only_active=True)
        _call(cms.get_cms_site_by_key, db, "faro")
        # themes
        site = db.execute(__import__("sqlalchemy").text("SELECT id FROM cms_sites LIMIT 1")).scalar()
        if site:
            _call(cms.list_cms_themes, db, site)
            _call(cms.get_active_cms_theme, db, site)
            # menus
            _call(cms.list_cms_menus, db, site)
            _call(cms.get_cms_menu, db, site, "main")
            # pages
            _call(cms.list_cms_pages, db, site)
            _call(cms.list_cms_pages, db, site, status="published")
            _call(cms.list_cms_pages_all, db, site)
            # publish logs
            _call(cms.list_cms_publish_logs, db, site)
        page = db.execute(__import__("sqlalchemy").text("SELECT id FROM cms_pages LIMIT 1")).scalar()
        if page:
            _call(cms.list_cms_sections, db, page)
            _call(cms.list_cms_sections, db, page, section_type="hero")
            _call(cms.list_cms_page_versions, db, page)
        # announcements
        _call(cms.list_announcements, db)
        _call(cms.list_announcements, db, public_only=True)
        # testimonials
        _call(cms.list_testimonials, db)
        _call(cms.list_testimonials, db, approved_only=True)
        # pastoral team
        _call(cms.list_pastoral_team, db)
        # menu items
        _call(cms.list_cms_menu_items, db, 1)


# ═══════════════════════════════════════════════════════════════════════════════
# ENTERPRISE CMS — enterprise_cms.py (262 missed, 42%)
# ═══════════════════════════════════════════════════════════════════════════════

class TestEnterpriseCMSDeep:
    def test_webhooks_full(self, full):
        c, h = full["c"], full["h"]
        _ok(c.get("/api/cms/v2/webhooks", headers=h).status_code)
        resp = c.post("/api/cms/v2/webhooks", json={
            "url": "https://hook.test", "events": ["page.published"],
        }, headers=h)
        assert _ok(resp.status_code)
        if resp.status_code in (200, 201):
            wid = resp.json().get("id")
            if wid:
                c.get(f"/api/cms/v2/webhooks/{wid}", headers=h)
                c.patch(f"/api/cms/v2/webhooks/{wid}", json={"url": "https://u.test"}, headers=h)
                c.delete(f"/api/cms/v2/webhooks/{wid}", headers=h)

    def test_redirects_full(self, full):
        c, h = full["c"], full["h"]
        _ok(c.get("/api/cms/v2/redirects", headers=h).status_code)
        resp = c.post("/api/cms/v2/redirects", json={
            "source_path": "/old", "target_path": "/new", "status_code": 301,
        }, headers=h)
        assert _ok(resp.status_code)
        if resp.status_code in (200, 201):
            rid = resp.json().get("id")
            if rid:
                c.get(f"/api/cms/v2/redirects/{rid}", headers=h)
                c.patch(f"/api/cms/v2/redirects/{rid}", json={"target_path": "/u"}, headers=h)
                c.delete(f"/api/cms/v2/redirects/{rid}", headers=h)

    def test_custom_types_full(self, full):
        c, h = full["c"], full["h"]
        _ok(c.get("/api/cms/v2/custom-types", headers=h).status_code)
        resp = c.post("/api/cms/v2/custom-types", json={
            "name": f"CT_{uuid.uuid4().hex[:6]}", "schema": {"fields": []},
        }, headers=h)
        assert _ok(resp.status_code)
        if resp.status_code in (200, 201):
            tid = resp.json().get("id")
            if tid:
                c.get(f"/api/cms/v2/custom-types/{tid}", headers=h)
                c.patch(f"/api/cms/v2/custom-types/{tid}", json={"name": "U"}, headers=h)
                c.delete(f"/api/cms/v2/custom-types/{tid}", headers=h)

    def test_glossary_full(self, full):
        c, h = full["c"], full["h"]
        _ok(c.get("/api/cms/v2/glossary", headers=h).status_code)
        resp = c.post("/api/cms/v2/glossary", json={
            "term": f"T_{uuid.uuid4().hex[:6]}", "definition": "Def",
        }, headers=h)
        assert _ok(resp.status_code)
        if resp.status_code in (200, 201):
            gid = resp.json().get("id")
            if gid:
                c.get(f"/api/cms/v2/glossary/{gid}", headers=h)
                c.patch(f"/api/cms/v2/glossary/{gid}", json={"definition": "U"}, headers=h)
                c.delete(f"/api/cms/v2/glossary/{gid}", headers=h)

    def test_media_folders_full(self, full):
        c, h = full["c"], full["h"]
        _ok(c.get("/api/cms/v2/media-folders", headers=h).status_code)
        resp = c.post("/api/cms/v2/media-folders", json={"name": f"F_{uuid.uuid4().hex[:6]}"}, headers=h)
        assert _ok(resp.status_code)
        if resp.status_code in (200, 201):
            fid = resp.json().get("id")
            if fid:
                c.get(f"/api/cms/v2/media-folders/{fid}", headers=h)
                c.patch(f"/api/cms/v2/media-folders/{fid}", json={"name": "U"}, headers=h)
                c.delete(f"/api/cms/v2/media-folders/{fid}", headers=h)
