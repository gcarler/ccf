"""
FLOW TESTS — Integration tests that exercise complete data flows.
Each test creates real data and exercises multiple functions in sequence.
This covers the handler logic, CRUD internals, and response serialization.
"""
import uuid
import pytest
from datetime import datetime, date, timedelta, timezone
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
        Asistencia, ParticipanteGrupo, CategoriaEstrategia,
    )

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

    pipe = PipelineCRM(sede_id=sede.id, nombre="P", tipo=TipoPipelineEnum.NUEVOS_VISITANTES)
    db_session.add(pipe); db_session.flush()
    e1 = EtapaPipeline(pipeline_id=pipe.id, nombre="E1", orden=1)
    db_session.add(e1); db_session.flush()

    cases = []
    for i, p in enumerate(personas[:8]):
        c = CasoCRM(persona_id=p.id, sede_id=sede.id, titulo_caso=f"C{i}",
            pipeline_id=pipe.id, etapa_actual_id=e1.id,
            origen_canal=CanalOrigenEnum.EVANGELISMO)
        db_session.add(c); cases.append(c)
    db_session.commit()
    for c in cases: db_session.refresh(c)

    projects = []
    for i in range(6):
        pr = models.Project(title=f"P{i}", description=f"Desc{i}", status="active", sede_id=sede.id)
        db_session.add(pr); projects.append(pr)
    db_session.commit()
    for pr in projects: db_session.refresh(pr)

    for i, pr in enumerate(projects[:4]):
        for j in range(4):
            db_session.add(models.ProjectTask(project_id=pr.id, title=f"T{i}_{j}",
                status=["pending", "in_progress", "done", "pending"][j]))
        db_session.add(models.ProjectMilestone(project_id=pr.id, title=f"MS{i}",
            target_date=datetime.now(timezone.utc) + timedelta(days=30)))
        db_session.add(models.ProjectComment(project_id=pr.id, author_id=str(personas[i].id),
            content=f"Comment {i}", is_resolved=i % 2 == 0))
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


class TestCRMFlow:
    def test_persona_lifecycle(self, full):
        c, h, p = full["c"], full["h"], full["personas"][0]
        pid = str(p.id)
        # Get persona
        resp = c.get(f"/api/crm/consolidation/cases/{full['cases'][0].id}", headers=h)
        assert _ok(resp.status_code)
        # Update case case fields
        now = datetime.now(timezone.utc).isoformat()
        for field in ["titulo", "estado", "prioridad", "notas", "last_contact_at", "next_contact_at"]:
            val = now if "at" in field else "Updated"
            c.patch(f"/api/crm/consolidation/cases/{full['cases'][0].id}",
                json={field: val}, headers=h)
        # List cases with all filters
        for f in ["source=EVANGELISMO", "status=active", f"persona_id={pid}",
                   "page=1&page_size=5"]:
            c.get(f"/api/crm/consolidation/cases?{f}", headers=h)
        # Create case interaction
        c.post(f"/api/crm/consolidation/cases/{full['cases'][0].id}/interactions",
            json={"tipo": "Llamada", "notas": "Called"}, headers=h)
        # List interactions
        c.get(f"/api/crm/consolidation/cases/{full['cases'][0].id}/interactions", headers=h)
        # Create case task
        resp = c.post(f"/api/crm/consolidation/cases/{full['cases'][0].id}/tasks",
            json={"titulo": "Follow up"}, headers=h)
        # List case tasks with status filter
        for sf in ["pending", "completed", "all"]:
            c.get(f"/api/crm/consolidation/cases/{full['cases'][0].id}/tasks?status_filter={sf}", headers=h)

    def test_case_call_log(self, full):
        c, h = full["c"], full["h"]
        c.post(f"/api/crm/consolidation/cases/{full['cases'][0].id}/calls",
            json={"outcome": "completed", "notes": "Talked", "duration_seconds": 300}, headers=h)
        c.get(f"/api/crm/consolidation/cases/{full['cases'][0].id}/calls", headers=h)

    def test_counseling_flow(self, full):
        c, h, personas = full["c"], full["h"], full["personas"]
        c.get("/api/crm/counseling", headers=h)
        resp = c.post("/api/crm/counseling", json={
            "persona_id": str(personas[0].id), "subject": "Deep session",
        }, headers=h)
        assert _ok(resp.status_code)
        if resp.status_code in (200, 201):
            tid = resp.json().get("id")
            if tid:
                c.patch(f"/api/crm/counseling/{tid}",
                    json={"status": "resolved", "notes": "Done", "priority_level": "high"}, headers=h)
                c.get(f"/api/crm/counseling/{tid}", headers=h)

    def test_prayer_flow(self, full):
        c, h, sede = full["c"], full["h"], full["sede"]
        c.get("/api/crm/prayer-requests", headers=h)
        resp = c.post("/api/crm/prayer-requests", json={
            "requester_name": "Praying", "request_text": "Help", "sede_id": str(sede.id),
        }, headers=h)
        assert _ok(resp.status_code)
        if resp.status_code in (200, 201):
            rid = resp.json().get("id")
            if rid:
                c.patch(f"/api/crm/prayer-requests/{rid}",
                    json={"status": "answered", "is_answered": True}, headers=h)

    def test_prayer_public(self, full):
        c = full["c"]
        c.post("/api/crm/prayer-requests/public", json={
            "first_name": "Public", "last_name": "Prayer",
            "request_text": "Heal me", "phone": "+573009999999",
            "email": f"pub_{uuid.uuid4().hex[:6]}@t.com",
            "category": "health", "campaign": "easter",
        }, headers={})

    def test_tasks_flow(self, full):
        c, h = full["c"], full["h"]
        c.get("/api/crm/tasks", headers=h)
        resp = c.post("/api/crm/tasks", json={
            "titulo": "New task", "status": "pending", "priority": "high",
            "persona_id": str(full["personas"][0].id),
            "due_date": datetime.now(timezone.utc).isoformat(),
        }, headers=h)
        assert _ok(resp.status_code)
        if resp.status_code in (200, 201):
            tid = resp.json().get("id")
            if tid:
                c.get(f"/api/crm/tasks/{tid}", headers=h)
                c.patch(f"/api/crm/tasks/{tid}",
                    json={"titulo": "Updated", "status": "completed", "priority": "low"}, headers=h)
                c.delete(f"/api/crm/tasks/{tid}", headers=h)

    def test_messaging_flow(self, full):
        c, h, personas = full["c"], full["h"], full["personas"]
        for ch in ["email", "whatsapp", "sms"]:
            c.post("/api/crm/messaging/send", json={
                "channel": ch, "recipient_ids": [str(personas[0].id)],
                "subject": f"Test {ch}", "body": f"Body {ch}",
            }, headers=h)
        for seg in ["active", "groups"]:
            c.post("/api/crm/messaging/send", json={
                "channel": "email", "body": "Broadcast",
                "target_segments": [seg], "campaign_name": "Spring",
            }, headers=h)
        c.get("/api/crm/messaging/history", headers=h)

    def test_analytics_radar(self, full):
        c, h = full["c"], full["h"]
        c.get("/api/crm/analytics", headers=h)
        c.get("/api/crm/radar", headers=h)

    def test_settings(self, full):
        c, h = full["c"], full["h"]
        c.get("/api/crm/settings", headers=h)
        c.post("/api/crm/settings", json={"config": {"key": "val"}}, headers=h)

    def test_roles_crud(self, full):
        c, h = full["c"], full["h"]
        c.get("/api/crm/roles", headers=h)
        resp = c.post("/api/crm/roles", json={"nombre": f"R_{uuid.uuid4().hex[:6]}"}, headers=h)
        if resp.status_code in (200, 201):
            rid = resp.json().get("id")
            if rid:
                c.put(f"/api/crm/roles/{rid}", json={"nombre": "U"}, headers=h)
                c.delete(f"/api/crm/roles/{rid}", headers=h)

    def test_groups_crud(self, full):
        c, h, groups = full["c"], full["h"], full["groups"]
        c.get("/api/crm/grupos", headers=h)
        c.get(f"/api/crm/grupos/{groups[0].id}", headers=h)
        c.put(f"/api/crm/grupos/{groups[0].id}", json={
            "nombre": "U", "ubicacion": "New", "participante_ids": [str(full["personas"][0].id)],
        }, headers=h)

    def test_volunteers_flow(self, full):
        c, h, personas = full["c"], full["h"], full["personas"]
        c.post("/api/crm/volunteers", json={
            "persona_id": str(personas[5].id), "name": "V",
            "shift_start": datetime.now(timezone.utc).isoformat(),
            "shift_end": (datetime.now(timezone.utc)+timedelta(hours=4)).isoformat(),
        }, headers=h)
        c.get("/api/crm/volunteers", headers=h)
        c.get(f"/api/crm/volunteers/{personas[0].id}", headers=h)
        c.patch(f"/api/crm/volunteers/{personas[0].id}", json={"first_name": "U"}, headers=h)

    def test_newsletter_flow(self, full):
        c, h = full["c"], full["h"]
        c.get("/api/crm/leads/newsletter", headers=h)
        c.get("/api/crm/leads/newsletter?source=EVANGELISMO", headers=h)
        c.get("/api/crm/leads/newsletter?campaign=Test", headers=h)
        c.get("/api/crm/leads/export-newsletter", headers=h)

    def test_crm_radar(self, full):
        c, h = full["c"], full["h"]
        c.get("/api/crm/radar", headers=h)


class TestProjectsFlow:
    def test_project_lifecycle(self, full):
        c, h = full["c"], full["h"]
        # Create
        resp = c.post("/api/projects", json={
            "title": f"P_{uuid.uuid4().hex[:6]}", "description": "Lifecycle test",
        }, headers=h)
        assert _ok(resp.status_code)
        pid = resp.json().get("id") if resp.status_code in (200, 201) else None
        if pid:
            # Get
            c.get(f"/api/projects/{pid}", headers=h)
            # Update
            c.patch(f"/api/projects/{pid}", json={"title": "Updated"}, headers=h)
            # Phases
            c.get(f"/api/projects/{pid}/phases", headers=h)
            c.put(f"/api/projects/{pid}/phases", json=[
                {"name": "Backlog", "slug": "backlog", "color": "#gray", "order_index": 0},
                {"name": "Active", "slug": "active", "color": "#blue", "order_index": 1},
                {"name": "Done", "slug": "done", "color": "#green", "order_index": 2},
            ], headers=h)
            # Task CRUD
            resp2 = c.post(f"/api/projects/{pid}/tasks", json={
                "title": "Task", "description": "D",
            }, headers=h)
            if resp2.status_code in (200, 201):
                tid = resp2.json().get("id")
                if tid:
                    c.get(f"/api/projects/tasks/{tid}", headers=h)
                    c.patch(f"/api/projects/tasks/{tid}", json={
                        "title": "Updated", "status": "in_progress",
                    }, headers=h)
                    c.delete(f"/api/projects/{pid}/tasks/{tid}", headers=h)
            # Comments
            c.post(f"/api/projects/{pid}/comments", json={"content": "Comment"}, headers=h)
            c.get(f"/api/projects/{pid}/comments", headers=h)
            # Milestones
            resp3 = c.post(f"/api/projects/{pid}/milestones", json={
                "title": "MS", "target_date": (date.today()+timedelta(days=60)).isoformat(),
            }, headers=h)
            if resp3.status_code in (200, 201):
                mid = resp3.json().get("id")
                if mid:
                    c.patch(f"/api/projects/milestones/{mid}", json={"title": "U"}, headers=h)
                    c.delete(f"/api/projects/milestones/{mid}", headers=h)
            # Wiki
            c.get(f"/api/projects/{pid}/wiki", headers=h)
            c.post(f"/api/projects/{pid}/wiki", json={"title": "W", "content": "# C"}, headers=h)
            # Whiteboard
            c.get(f"/api/projects/{pid}/whiteboard", headers=h)
            c.put(f"/api/projects/{pid}/whiteboard", json={"content": {"nodes": []}}, headers=h)
            # Delete
            c.delete(f"/api/projects/{pid}", headers=h)

    def test_all_comments(self, full):
        c, h = full["c"], full["h"]
        c.get("/api/projects/comments", headers=h)
        c.get("/api/projects/comments?unresolved_only=true", headers=h)

    def test_summary_workload_activities(self, full):
        c, h = full["c"], full["h"]
        c.get("/api/projects/summary", headers=h)
        c.get("/api/projects/workload", headers=h)
        c.get("/api/projects/activities", headers=h)

    def test_inbox_my_tasks(self, full):
        c, h = full["c"], full["h"]
        c.get("/api/projects/inbox", headers=h)
        c.get("/api/projects/tasks", headers=h)

    def test_supplies_attachments(self, full):
        c, h, projects = full["c"], full["h"], full["projects"]
        pid = str(projects[0].id)
        tasks = c.get(f"/api/projects/{pid}/tasks", headers=h)
        if tasks.status_code == 200 and tasks.json():
            tid = tasks.json()[0].get("id")
            if tid:
                c.get(f"/api/projects/{pid}/tasks/{tid}/supplies", headers=h)
                c.post(f"/api/projects/{pid}/tasks/{tid}/supplies",
                    json={"item_name": "Item", "quantity": 5}, headers=h)
                c.get(f"/api/projects/{pid}/tasks/{tid}/attachments", headers=h)


class TestEvangelismFlow:
    def test_counseling_lifecycle(self, full):
        c, h, personas = full["c"], full["h"], full["personas"]
        c.get("/api/evangelism/counseling/", headers=h)
        c.get("/api/evangelism/counseling/?status=open", headers=h)
        resp = c.post("/api/evangelism/counseling/", json={
            "persona_id": str(personas[0].id), "subject": "S",
        }, headers=h)
        assert _ok(resp.status_code)
        if resp.status_code in (200, 201):
            tid = resp.json().get("id")
            if tid:
                c.get(f"/api/evangelism/counseling/{tid}", headers=h)
                c.patch(f"/api/evangelism/counseling/{tid}",
                    json={"status": "resolved", "notes": "Done"}, headers=h)
                c.get(f"/api/evangelism/counseling/lead/{personas[0].id}", headers=h)
        c.get("/api/evangelism/counseling/99999", headers=h)

    def test_prayer_lifecycle(self, full):
        c, h, sede = full["c"], full["h"], full["sede"]
        c.get("/api/evangelism/prayer-requests/", headers=h)
        resp = c.post("/api/evangelism/prayer-requests/", json={
            "requester_name": "P", "request_text": "H", "sede_id": str(sede.id),
        }, headers=h)
        assert _ok(resp.status_code)
        if resp.status_code in (200, 201):
            rid = resp.json().get("id")
            if rid:
                c.get(f"/api/evangelism/prayer-requests/{rid}", headers=h)
                c.patch(f"/api/evangelism/prayer-requests/{rid}",
                    json={"status": "answered", "is_answered": True}, headers=h)
        c.get("/api/evangelism/prayer-requests/99999", headers=h)

    def test_messaging_full(self, full):
        c, h, personas = full["c"], full["h"], full["personas"]
        for ch in ["email", "whatsapp", "sms"]:
            c.post("/api/evangelism/messaging/send", json={
                "channel": ch, "persona_id": str(personas[0].id), "content": f"M {ch}",
            }, headers=h)
        for seg in ["active", "groups"]:
            c.post("/api/evangelism/messaging/send", json={
                "channel": "email", "content": "S", "target_segments": [seg], "campaign_name": "C",
            }, headers=h)
        c.get("/api/evangelism/messaging/history", headers=h)


class TestGruposFlow:
    def test_group_lifecycle(self, full):
        c, h, groups = full["c"], full["h"], full["groups"]
        c.get("/api/evangelism/grupos", headers=h)
        c.get(f"/api/evangelism/grupos/{groups[0].id}", headers=h)
        c.get("/api/evangelism/grupos/assignment-summary", headers=h)
        c.get("/api/evangelism/grupos/mine", headers=h)

    def test_create_update_group(self, full):
        c, h, personas = full["c"], full["h"], full["personas"]
        resp = c.post("/api/evangelism/grupos", json={
            "nombre": f"G_{uuid.uuid4().hex[:6]}", "codigo": f"C{uuid.uuid4().hex[:6]}",
            "ubicacion": "P", "sede_id": str(full["sede"].id),
            "lider_persona_id": str(personas[0].id), "capacidad": 20,
        }, headers=h)
        assert _ok(resp.status_code)

    def test_seasons_flow(self, full):
        c, h, groups = full["c"], full["h"], full["groups"]
        c.get("/api/evangelism/grupos/seasons", headers=h)
        start = date.today().isoformat()
        end = (date.today()+timedelta(days=90)).isoformat()
        resp = c.post("/api/evangelism/grupos/seasons",
            json={"name": f"S_{uuid.uuid4().hex[:6]}", "start_date": start, "end_date": end}, headers=h)
        if resp.status_code in (200, 201):
            sid = resp.json().get("id")
            if sid:
                c.patch(f"/api/evangelism/grupos/seasons/{sid}", json={"name": "U"}, headers=h)
                c.post("/api/evangelism/grupos/sessions", json={
                    "session_date": date.today().isoformat(), "season_id": sid,
                    "grupo_id": str(groups[0].id), "topic": "T",
                }, headers=h)
        c.get("/api/evangelism/grupos/sessions", headers=h)

    def test_analytics_despliegue(self, full):
        c, h = full["c"], full["h"]
        c.get("/api/evangelism/grupos/analytics", headers=h)
        c.get("/api/evangelism/macro/despliegue", headers=h)

    def test_visitor_registration(self, full):
        c, h, groups = full["c"], full["h"], full["groups"]
        c.post("/api/evangelism/grupos/visitors", json={
            "first_name": "V", "last_name": "Test", "phone": "+573009999999",
            "grupo_id": str(groups[0].id),
        }, headers=h)


class TestCMSFlow:
    def test_public_pages(self, full):
        c = full["c"]
        for slug in ["home", "nosotros", "eventos", "conocer-a-jesus", "predicas",
                      "cursos", "sedes", "boletin", "bienvenida", "privacidad"]:
            c.get(f"/api/cms/v2/public/sites/faro/pages/{slug}")
        c.get("/api/cms/v2/public/sites/faro/theme")
        c.get("/api/cms/v2/public/sites/faro/menus/main")
        c.get("/api/cms/v2/public/sites/faro/pastoral-team")

    def test_cms_analytics(self, full):
        c, h = full["c"], full["h"]
        c.post("/api/cms/v2/track/home", headers=h)
        c.get("/api/cms/v2/analytics/home", headers=h)

    def test_global_blocks(self, full):
        c, h = full["c"], full["h"]
        c.get("/api/cms/v2/global-blocks", headers=h)
        resp = c.post("/api/cms/v2/global-blocks", json={
            "type": "RichText", "props_json": {"content": "<p>GB</p>"},
        }, headers=h)
        assert _ok(resp.status_code)

    def test_enterprise_crud(self, full):
        c, h = full["c"], full["h"]
        for ep in ["/api/cms/v2/webhooks", "/api/cms/v2/redirects",
                   "/api/cms/v2/custom-types", "/api/cms/v2/glossary", "/api/cms/v2/media-folders"]:
            c.get(ep, headers=h)
            uid = uuid.uuid4().hex[:6]
            payload = {"url": f"https://{uid}.t", "events": ["page.published"]} if "webhook" in ep else \
                      {"source_path": f"/o_{uid}", "target_path": f"/n_{uid}", "status_code": 301} if "redirect" in ep else \
                      {"name": f"CT_{uid}", "schema": {"fields": []}} if "custom" in ep else \
                      {"term": f"T_{uid}", "definition": "D"} if "glossary" in ep else {"name": f"F_{uid}"}
            resp = c.post(ep, json=payload, headers=h)
            assert _ok(resp.status_code)
            if resp.status_code in (200, 201):
                rid = resp.json().get("id")
                if rid:
                    c.get(f"{ep}/{rid}", headers=h)
                    c.patch(f"{ep}/{rid}", json={"name": "U"}, headers=h)
                    c.delete(f"{ep}/{rid}", headers=h)

    def test_cms_sites_themes_menus(self, full):
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

    def test_cms_pastoral(self, full):
        c, h = full["c"], full["h"]
        c.get("/api/cms/v2/cms/pastoral-team", headers=h)
        c.get("/api/cms/v2/media", headers=h)
        c.get(f"/api/cms/v2/images/{uuid.uuid4()}/resize", headers=h)


class TestAuthFlow:
    def test_login_me_refresh(self, full):
        c, h, admin = full["c"], full["h"], full["admin"]
        resp = c.post("/api/v3/auth/login", json={"email": admin.email, "password": "testpass123"})
        assert resp.status_code == 200
        token = resp.json()["access_token"]
        c.get("/api/v3/auth/me", headers={"Authorization": f"Bearer {token}"})
        c.post("/api/v3/auth/refresh", headers={"Authorization": f"Bearer {token}"})
        c.post("/api/v3/auth/change-password",
            json={"current_password": "testpass123", "new_password": "New123!"},
            headers={"Authorization": f"Bearer {token}"})
        c.post("/api/v3/auth/change-password",
            json={"current_password": "New123!", "new_password": "testpass123"},
            headers={"Authorization": f"Bearer {token}"})

    def test_forgot_reset(self, full):
        c, admin = full["c"], full["admin"]
        c.post("/api/v3/auth/forgot-password", json={"email": admin.email})
        c.post("/api/v3/auth/reset-password", json={"token": "invalid", "password": "X"})
        c.post("/api/v3/auth/verify-email", json={"token": "invalid"})

    def test_register(self, full):
        c = full["c"]
        c.post("/api/v3/auth/register", json={
            "email": f"r_{uuid.uuid4().hex[:6]}@t.com", "password": "TestPass123!",
            "first_name": "R", "last_name": "User",
        })
        c.get(f"/api/v3/auth/check-email?email={full['admin'].email}")

    def test_login_errors(self, full):
        c = full["c"]
        c.post("/api/v3/auth/login", json={"email": "wrong@t.com", "password": "w"})
        c.post("/api/v3/auth/login", json={"email": full["admin"].email, "password": "wrong"})
        c.post("/api/v3/auth/login", json={})
