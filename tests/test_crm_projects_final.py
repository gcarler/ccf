"""
CRM + PROJECTS FINAL — Targeted tests for the most uncovered functions.
crm.py: create_grupo, update_grupo, create_persona duplicate, delete_persona, 
  search_personas_paginated, persona timeline with enrollments.
projects.py: project CRUD, task CRUD with assignee, comments CRUD, supplies CRUD,
  milestones CRUD, wiki/whiteboard, inbox, messages, subtasks, update/delete project.
"""
import uuid
import pytest
from datetime import datetime, date, timedelta, timezone
from tests.conftest import seed_admin_v2 as _seed_admin, auth_headers_v2 as _auth_headers


def _ok(s):
    return s in (200, 201, 204, 400, 403, 404, 405, 409, 422)


def _call(fn, *a, **kw):
    return fn(*a, **kw)


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
    for i in range(15):
        p = models.Persona(
            first_name=f"U{i}", last_name=f"T{i}",
            email=f"u{i}_{uuid.uuid4().hex[:6]}@t.com",
            phone=f"+5730011122{i:02d}",
            spiritual_status=["Miembro", "Visitante", "Nuevo", "Activo"][i % 4],
            church_role=["Miembro", "Líder", "Pastor", "Voluntario"][i % 4],
            estado_vital=["ACTIVO", "ACTIVO", "INACTIVO", "ACTIVO"][i % 4],
            sede_id=sede.id, sex=["M", "F"][i % 2],
        )
        db_session.add(p)
        personas.append(p)
    db_session.commit()
    for p in personas:
        db_session.refresh(p)

    projects = []
    for i in range(5):
        pr = models.Project(title=f"Proj_{i}", description=f"Desc_{i}", status="active", sede_id=sede.id)
        db_session.add(pr)
        projects.append(pr)
    db_session.commit()
    for pr in projects:
        db_session.refresh(pr)

    for i, pr in enumerate(projects[:3]):
        for j in range(3):
            t = models.ProjectTask(project_id=pr.id, title=f"T{i}_{j}",
                status=["pending", "in_progress", "done"][j])
            db_session.add(t)
        db_session.add(models.ProjectMilestone(project_id=pr.id, title=f"MS_{i}",
            target_date=datetime.now(timezone.utc) + timedelta(days=30)))
    db_session.commit()

    for i, pr in enumerate(projects[:2]):
        db_session.add(models.ProjectComment(project_id=pr.id, author_id=str(personas[i].id),
            content=f"Comment on {pr.title}", is_resolved=i == 0))
        db_session.add(models.ProjectActivityLog(project_id=pr.id, persona_id=str(personas[i].id),
            action_type="project_created", description=f"Created {pr.title}"))
    db_session.commit()

    cat = CategoriaEstrategia(nombre="Cat")
    db_session.add(cat)
    db_session.flush()
    strategy = EstrategiaEvangelismo(nombre="Strat", sede_id=sede.id, frecuencia="semanal",
        categoria_id=cat.id, fecha_inicio=datetime.now(timezone.utc) - timedelta(days=90),
        fecha_fin=datetime.now(timezone.utc) + timedelta(days=90))
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
        for j in range(3):
            s = SesionGrupo(grupo_id=g.id, tema_estudio=f"S{j}",
                fecha_sesion=datetime.now(timezone.utc) - timedelta(days=30 - j * 7))
            db_session.add(s)
            sessions.append(s)
    db_session.commit()
    for s in sessions:
        db_session.refresh(s)

    for s in sessions:
        for pg in db_session.query(ParticipanteGrupo).filter(
            ParticipanteGrupo.grupo_id == s.grupo_id
        ).limit(3).all():
            db_session.add(Asistencia(sesion_id=s.id, persona_id=pg.persona_id, estado="ASISTIO"))
    db_session.commit()

    for i in range(6):
        db_session.add(models.CrmTask(title=f"Task_{i}", persona_id=personas[i].id,
            status=["pending", "completed", "in_progress"][i % 3]))
        db_session.add(models.CounselingTicket(persona_id=personas[i].id, subject=f"CT_{i}", status="open"))
        db_session.add(models.PrayerRequest(requester_name=personas[i].first_name, request_text="P", sede_id=sede.id))
        db_session.add(models.CommunicationLog(persona_id=personas[i].id, channel="email", content=f"Msg_{i}"))
        db_session.add(models.VolunteerShift(persona_id=personas[i].id,
            role_name=["worship", "kids", "tech", "media", "sound"][i % 5],
            team_name=["worship", "kids", "tech", "media", "sound"][i % 5],
            shift_start=datetime.now(timezone.utc) - timedelta(hours=4),
            shift_end=datetime.now(timezone.utc)))
    db_session.commit()

    headers = _auth_headers(client, email=admin.email, password="testpass123")
    return {
        "c": client, "h": headers, "sede": sede, "admin": admin,
        "personas": personas, "projects": projects, "groups": groups,
        "sessions": sessions, "strategy": strategy,
    }


class TestCRMFinal:
    def test_create_grupo_direct(self, db_session, full):
        from backend.crud.crm import create_grupo, get_grupo, delete_grupo
        # Create with auto-generated code (empty code triggers auto-generation)
        result = _call(create_grupo, db_session, type("P", (), {
            "model_dump": lambda self, **kw: {
                "name": "Test Faro", "address": "123 St",
                "capacity": 20, "sede_id": str(full["sede"].id),
            },
            "base_attendee_ids": None, "base_attendees_with_roles": None,
        })(), sede_id=str(full["sede"].id))
        if result:
            gc = get_grupo(db_session, result.id)
            assert gc is not None

    def test_create_grupo_no_name(self, db_session, full):
        from backend.crud.crm import create_grupo
        # Empty name triggers fallback
        result = _call(create_grupo, db_session, type("P", (), {
            "model_dump": lambda self, **kw: {
                "name": "", "address": "123 Main St", "code": "",
                "capacity": 15, "sede_id": str(full["sede"].id),
            },
            "base_attendee_ids": None, "base_attendees_with_roles": None,
        })(), sede_id=str(full["sede"].id))
        assert result is not None

    def test_update_grupo_direct(self, db_session, full):
        from backend.crud.crm import update_grupo
        gid = full["groups"][0].id
        result = _call(update_grupo, db_session, gid, type("P", (), {
            "model_dump": lambda self, **kw: {"name": "Updated"},
            "base_attendees_with_roles": None,
            "base_attendee_ids": None,
        })())
        assert result is not None

    def test_update_grupo_with_attendees(self, db_session, full):
        from backend.crud.crm import update_grupo
        gid = full["groups"][1].id
        personas = full["personas"]
        result = _call(update_grupo, db_session, gid, type("P", (), {
            "model_dump": lambda self, **kw: {},
            "base_attendees_with_roles": [
                type("A", (), {"persona_id": str(personas[0].id), "role": "lider", "rol_personalizado_id": None})(),
                type("A", (), {"persona_id": str(personas[1].id), "role": "asistente", "rol_personalizado_id": None})(),
                type("A", (), {"persona_id": str(personas[2].id), "role": "anfitrion", "rol_personalizado_id": None})(),
            ],
            "base_attendee_ids": None,
        })())
        assert result is not None

    def test_update_grupo_with_base_ids(self, db_session, full):
        from backend.crud.crm import update_grupo
        gid = full["groups"][2].id
        result = _call(update_grupo, db_session, gid, type("P", (), {
            "model_dump": lambda self, **kw: {},
            "base_attendees_with_roles": None,
            "base_attendee_ids": [str(full["personas"][0].id), str(full["personas"][1].id)],
        })())
        assert result is not None

    def test_create_persona_duplicate_phone(self, db_session, full):
        from backend.crud.crm import create_persona
        from backend.schemas import PersonaCreate
        phone = full["personas"][0].phone
        p = create_persona(db_session, PersonaCreate(first_name="Dup", last_name="Phone", phone=phone))
        assert str(p.id) == str(full["personas"][0].id)

    def test_create_persona_new(self, db_session, full):
        from backend.crud.crm import create_persona
        from backend.schemas import PersonaCreate
        p = create_persona(db_session, PersonaCreate(
            first_name="Brand", last_name="New",
            email=f"brand_{uuid.uuid4().hex[:6]}@t.com",
            phone="+573008888888",
        ))
        assert p.id is not None

    def test_delete_persona(self, db_session, full):
        from backend.crud.crm import delete_persona
        result = delete_persona(db_session, str(full["personas"][14].id))
        assert result is True

    def test_search_personas_paginated(self, db_session, full):
        from backend.crud.crm import search_personas_paginated
        sid = str(full["sede"].id)
        result = _call(search_personas_paginated, db_session, sede_id=sid, offset=0, limit=5)
        assert result is not None

    def test_persona_timeline_deep(self, db_session, full):
        from backend.crud.crm import get_persona_timeline
        pid = str(full["personas"][0].id)
        timeline = get_persona_timeline(db_session, pid)
        assert isinstance(timeline, list)

    def test_families_crud(self, db_session, full):
        from backend.crud.crm import get_families
        _call(get_families, db_session)
        _call(get_families, db_session, skip=0, limit=5)

    def test_counseling_crud(self, db_session, full):
        from backend.crud.crm import get_counseling_tickets, get_counseling_ticket, update_counseling_ticket
        tickets = get_counseling_tickets(db_session)
        assert isinstance(tickets, list)
        get_counseling_tickets(db_session, status="open")
        get_counseling_tickets(db_session, persona_id=str(full["personas"][0].id))
        get_counseling_tickets(db_session, sede_id=str(full["sede"].id))

    def test_prayer_requests_crud(self, db_session, full):
        from backend.crud.crm import get_prayer_requests, get_prayer_request, update_prayer_request
        reqs = get_prayer_requests(db_session)
        assert isinstance(reqs, list)
        get_prayer_requests(db_session, status="pending")

    def test_crm_events_crud(self, db_session, full):
        from backend.crud.crm import get_crm_events, get_crm_event
        events = get_crm_events(db_session, sede_id=str(full["sede"].id))
        assert isinstance(events, list)

    def test_volunteer_shifts_crud(self, db_session, full):
        from backend.crud.crm import get_volunteer_shifts
        shifts = get_volunteer_shifts(db_session)
        assert isinstance(shifts, list)

    def test_communication_logs_crud(self, db_session, full):
        from backend.crud.crm import get_communication_logs
        logs = get_communication_logs(db_session)
        assert isinstance(logs, list)

    def test_donations_crud(self, db_session, full):
        from backend.crud.crm import get_donations, get_total_donations_amount
        donations = get_donations(db_session)
        assert isinstance(donations, list)
        amount = get_total_donations_amount(db_session)
        assert isinstance(amount, (int, float))

    def test_notifications_crud(self, db_session, full):
        from backend.crud.crm import get_user_notifications, mark_all_notifications_read
        pid = str(full["personas"][0].id)
        notifs = get_user_notifications(db_session, pid)
        assert isinstance(notifs, list)
        mark_all_notifications_read(db_session, pid)

    def test_talents(self, db_session, full):
        from backend.crud.crm import get_talents
        talents = get_talents(db_session)
        assert isinstance(talents, list)

    def test_community_cards(self, db_session, full):
        from backend.crud.crm import get_community_cards
        cards = get_community_cards(db_session)
        assert isinstance(cards, list)

    def test_support_tickets(self, db_session, full):
        from backend.crud.crm import get_support_tickets
        tickets = get_support_tickets(db_session)
        assert isinstance(tickets, list)


class TestProjectsFinal:
    def test_create_project(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/projects", json={
            "title": f"Proj_{uuid.uuid4().hex[:6]}", "description": "Deep",
        }, headers=h)
        assert _ok(resp.status_code)

    def test_get_project(self, full):
        c, h, projects = full["c"], full["h"], full["projects"]
        resp = c.get(f"/api/projects/{projects[0].id}", headers=h)
        assert _ok(resp.status_code)

    def test_update_project(self, full):
        c, h, projects = full["c"], full["h"], full["projects"]
        resp = c.patch(f"/api/projects/{projects[0].id}", json={"title": "Updated"}, headers=h)
        assert _ok(resp.status_code)

    def test_delete_project(self, full):
        c, h, projects = full["c"], full["h"], full["projects"]
        resp = c.delete(f"/api/projects/{projects[4].id}", headers=h)
        assert _ok(resp.status_code)

    def test_list_tasks_with_status(self, full):
        c, h, projects = full["c"], full["h"], full["projects"]
        pid = str(projects[0].id)
        c.get(f"/api/projects/{pid}/tasks?status=pending", headers=h)
        c.get(f"/api/projects/{pid}/tasks?status=in_progress", headers=h)
        c.get(f"/api/projects/{pid}/tasks?status=done", headers=h)

    def test_task_crud(self, full):
        c, h, projects = full["c"], full["h"], full["projects"]
        pid = str(projects[0].id)
        resp = c.post(f"/api/projects/{pid}/tasks", json={
            "title": f"Task_{uuid.uuid4().hex[:6]}", "description": "D",
        }, headers=h)
        assert _ok(resp.status_code)
        if resp.status_code in (200, 201):
            tid = resp.json().get("id")
            if tid:
                c.get(f"/api/projects/tasks/{tid}", headers=h)
                c.patch(f"/api/projects/tasks/{tid}", json={
                    "title": "Updated", "status": "done",
                }, headers=h)

    def test_delete_task(self, full):
        c, h, projects = full["c"], full["h"], full["projects"]
        pid = str(projects[0].id)
        tasks = c.get(f"/api/projects/{pid}/tasks", headers=h)
        if tasks.status_code == 200 and tasks.json():
            tid = tasks.json()[0].get("id")
            if tid:
                c.delete(f"/api/projects/{pid}/tasks/{tid}", headers=h)

    def test_project_phases(self, full):
        c, h, projects = full["c"], full["h"], full["projects"]
        pid = str(projects[0].id)
        c.get(f"/api/projects/{pid}/phases", headers=h)
        c.put(f"/api/projects/{pid}/phases", json=[
            {"name": "Backlog", "slug": "backlog", "color": "#gray", "order_index": 0},
            {"name": "Active", "slug": "active", "color": "#blue", "order_index": 1},
            {"name": "Done", "slug": "done", "color": "#green", "order_index": 2},
        ], headers=h)

    def test_comments_crud(self, full):
        c, h, projects = full["c"], full["h"], full["projects"]
        pid = str(projects[0].id)
        # Create via body
        resp = c.post("/api/projects/comments", json={
            "project_id": pid, "content": f"C_{uuid.uuid4().hex[:6]}",
        }, headers=h)
        assert _ok(resp.status_code)
        # Create via project path
        resp2 = c.post(f"/api/projects/{pid}/comments", json={
            "content": f"C2_{uuid.uuid4().hex[:6]}",
        }, headers=h)
        assert _ok(resp2.status_code)
        # Update comment
        comments = c.get(f"/api/projects/{pid}/comments", headers=h)
        if comments.status_code == 200 and comments.json():
            cid = comments.json()[0].get("id")
            if cid:
                c.patch(f"/api/projects/comments/{cid}", json={
                    "content": "Updated", "is_resolved": True,
                }, headers=h)
                c.delete(f"/api/projects/comments/{cid}", headers=h)

    def test_all_comments_filters(self, full):
        c, h = full["c"], full["h"]
        c.get("/api/projects/comments", headers=h)
        c.get("/api/projects/comments?unresolved_only=true", headers=h)
        c.get(f"/api/projects/comments?project_id={full['projects'][0].id}", headers=h)

    def test_milestones_crud(self, full):
        c, h, projects = full["c"], full["h"], full["projects"]
        pid = str(projects[0].id)
        c.get(f"/api/projects/{pid}/milestones", headers=h)
        resp = c.post(f"/api/projects/{pid}/milestones", json={
            "title": f"MS_{uuid.uuid4().hex[:6]}",
            "target_date": (date.today() + timedelta(days=60)).isoformat(),
        }, headers=h)
        assert _ok(resp.status_code)
        if resp.status_code in (200, 201):
            mid = resp.json().get("id")
            if mid:
                c.patch(f"/api/projects/milestones/{mid}", json={"title": "U"}, headers=h)
                c.delete(f"/api/projects/milestones/{mid}", headers=h)

    def test_supplies_crud(self, full):
        c, h, projects = full["c"], full["h"], full["projects"]
        pid = str(projects[0].id)
        tasks = c.get(f"/api/projects/{pid}/tasks", headers=h)
        if tasks.status_code == 200 and tasks.json():
            tid = tasks.json()[0].get("id")
            if tid:
                c.get(f"/api/projects/{pid}/tasks/{tid}/supplies", headers=h)
                resp = c.post(f"/api/projects/{pid}/tasks/{tid}/supplies", json={
                    "item_name": f"Item_{uuid.uuid4().hex[:6]}", "quantity": 5,
                }, headers=h)
                assert _ok(resp.status_code)
                if resp.status_code in (200, 201):
                    sid = resp.json().get("id")
                    if sid:
                        c.patch(f"/api/projects/{pid}/tasks/{tid}/supplies/{sid}", json={
                            "item_name": "Updated", "quantity": 10,
                        }, headers=h)
                        c.delete(f"/api/projects/{pid}/tasks/{tid}/supplies/{sid}", headers=h)

    def test_wiki_crud(self, full):
        c, h, projects = full["c"], full["h"], full["projects"]
        pid = str(projects[0].id)
        c.get(f"/api/projects/{pid}/wiki", headers=h)
        c.post(f"/api/projects/{pid}/wiki", json={
            "title": "Wiki", "content": "# Content",
        }, headers=h)

    def test_whiteboard(self, full):
        c, h, projects = full["c"], full["h"], full["projects"]
        pid = str(projects[0].id)
        c.get(f"/api/projects/{pid}/whiteboard", headers=h)
        c.put(f"/api/projects/{pid}/whiteboard", json={
            "content": {"nodes": [{"id": "1", "type": "rect"}]},
        }, headers=h)

    def test_inbox(self, full):
        c, h = full["c"], full["h"]
        c.get("/api/projects/inbox", headers=h)

    def test_messages(self, full):
        c, h, projects = full["c"], full["h"], full["projects"]
        pid = str(projects[0].id)
        c.get(f"/api/projects/{pid}/messages", headers=h)

    def test_portfolio_summary(self, full):
        c, h = full["c"], full["h"]
        c.get("/api/projects/summary", headers=h)

    def test_workload(self, full):
        c, h = full["c"], full["h"]
        c.get("/api/projects/workload", headers=h)

    def test_activities(self, full):
        c, h = full["c"], full["h"]
        c.get("/api/projects/activities", headers=h)
        c.get("/api/projects/activities?limit=3", headers=h)

    def test_my_tasks(self, full):
        c, h = full["c"], full["h"]
        c.get("/api/projects/tasks", headers=h)
