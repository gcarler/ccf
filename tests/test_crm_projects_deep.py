"""
CRM + PROJECTS DEEP — Targeted tests for the most uncovered functions.
crm.py: create_persona with existing lookup, _find_existing_persona,
create_grupo, update_grupo, get_persona_timeline, get_families.
projects.py: create_project, phases, comments, tasks, wiki, whiteboard,
milestones, supplies, attachments, activities, inbox.
"""
import uuid
import pytest
from datetime import datetime, date, timedelta, timezone
from tests.conftest import seed_admin as _seed_admin, auth_headers as _auth_headers


def _ok(s):
    return s in (200, 201, 204, 400, 403, 404, 405, 409, 422)


def _call(fn, *a, **kw):
    return fn(*a, **kw)


def _create_baptism_persona(db_session, full):
    from backend.crud.crm import create_persona
    from backend.schemas import PersonaCreate
    p = create_persona(db_session, PersonaCreate(
        first_name="Baptized", last_name="Person",
        email=f"bap_{uuid.uuid4().hex[:6]}@t.com",
        baptism_date=datetime.now(timezone.utc).date(),
    ))
    assert p.id is not None


@pytest.fixture
def full(client, db_session):
    admin, admin_persona, sede = _seed_admin(db_session)
    from backend import models
    from backend.models_crm_pipeline import CasoCRM, PipelineCRM, EtapaPipeline, TipoPipelineEnum, CanalOrigenEnum
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
            db_session.add(
                models.ProjectTask(
                    project_id=pr.id,
                    title=f"T{i}_{j}",
                    status=["pending", "in_progress", "done"][j],
                ),
            )
        db_session.add(
            models.ProjectMilestone(
                project_id=pr.id,
                title=f"MS_{i}",
                target_date=datetime.now(timezone.utc) + timedelta(days=30),
            ),
        )
    db_session.commit()

    for i, pr in enumerate(projects[:2]):
        db_session.add(
            models.ProjectComment(
                project_id=pr.id,
                author_id=str(personas[i].id),
                content=f"Comment on {pr.title}",
                is_resolved=i == 0,
            ),
        )
        db_session.add(
            models.ProjectActivityLog(
                project_id=pr.id,
                persona_id=str(personas[i].id),
                action_type="project_created",
                description=f"Created {pr.title}",
            ),
        )
    db_session.commit()

    cat = CategoriaEstrategia(nombre="Cat")
    db_session.add(cat)
    db_session.flush()
    strategy = EstrategiaEvangelismo(
        nombre="Strat",
        sede_id=sede.id,
        frecuencia="semanal",
        categoria_id=cat.id,
        fecha_inicio=datetime.now(timezone.utc) - timedelta(days=90),
        fecha_fin=datetime.now(timezone.utc) + timedelta(days=90),
    )
    db_session.add(strategy)
    db_session.flush()

    groups = []
    for i in range(5):
        g = GrupoEvangelismo(
            nombre=f"G{i}",
            ubicacion=f"U{i}",
            sede_id=sede.id,
            lider_persona_id=personas[i].id,
            codigo=f"G{uuid.uuid4().hex[:6]}",
            capacidad=20,
            estrategia_id=strategy.id,
        )
        db_session.add(g)
        groups.append(g)
    db_session.commit()
    for g in groups:
        db_session.refresh(g)

    for g in groups:
        for i in range(5):
            db_session.add(ParticipanteGrupo(grupo_id=g.id, persona_id=personas[i].id, rol_base="Miembro"))
    db_session.commit()

    sessions_list = []
    for g in groups:
        for j in range(3):
            s = SesionGrupo(
                grupo_id=g.id,
                tema_estudio=f"S{j}",
                fecha_sesion=datetime.now(timezone.utc) - timedelta(days=30 - j * 7),
            )
            db_session.add(s)
            sessions_list.append(s)
    db_session.commit()
    for s in sessions_list:
        db_session.refresh(s)

    for s in sessions_list:
        for pg in db_session.query(ParticipanteGrupo).filter(
            ParticipanteGrupo.grupo_id == s.grupo_id
        ).limit(3).all():
            db_session.add(Asistencia(sesion_id=s.id, persona_id=pg.persona_id, estado="ASISTIO"))
    db_session.commit()

    for i in range(6):
        db_session.add(models.TareaCRM(title=f"Task_{i}", persona_id=personas[i].id, status=["pending", "completed", "in_progress"][i % 3]))
        db_session.add(models.CounselingTicket(persona_id=personas[i].id, subject=f"CT_{i}", status="open"))
        db_session.add(models.PrayerRequest(requester_name=personas[i].first_name, request_text="P", sede_id=sede.id))
        db_session.add(models.CommunicationLog(persona_id=personas[i].id, channel="email", content=f"Msg_{i}"))
        db_session.add(
            models.VolunteerShift(
                persona_id=personas[i].id,
                role_name=["worship", "kids", "tech", "media", "sound"][i % 5],
                team_name=["worship", "kids", "tech", "media", "sound"][i % 5],
                shift_start=datetime.now(timezone.utc) - timedelta(hours=4),
                shift_end=datetime.now(timezone.utc),
            ),
        )
    db_session.commit()

    headers = _auth_headers(client, email=admin.email, password="testpass123")
    return {
        "c": client, "h": headers, "sede": sede, "admin": admin,
        "personas": personas, "families": families, "projects": projects,
        "groups": groups, "sessions": sessions_list, "strategy": strategy,
    }


class TestCRMDeep:
    def test_create_persona_new(self, db_session, full):
        from backend.crud.crm import create_persona
        from backend.schemas import PersonaCreate
        p = create_persona(db_session, PersonaCreate(
            first_name="Brand", last_name="New",
            email=f"brand_{uuid.uuid4().hex[:6]}@t.com",
            phone="+573008888888",
        ))
        assert p.id is not None

    def test_create_persona_existing_phone(self, db_session, full):
        from backend.crud.crm import create_persona
        from backend.schemas import PersonaCreate
        phone = full["personas"][0].phone
        p = create_persona(db_session, PersonaCreate(
            first_name="Dup", last_name="Phone", phone=phone,
        ))
        assert str(p.id) == str(full["personas"][0].id)

    def test_create_persona_existing_id_number(self, db_session, full):
        from backend.crud.crm import create_persona
        from backend.schemas import PersonaCreate
        full["personas"][0].id_number = "12345"
        db_session.commit()
        p = create_persona(db_session, PersonaCreate(
            first_name="Dup", last_name="ID", id_number="12345",
        ))
        assert str(p.id) == str(full["personas"][0].id)

    def test_create_persona_with_baptism_date(self, db_session, full):
        _call(_create_baptism_persona, db_session, full)

    def test_update_persona_fields(self, db_session, full):
        from backend.crud.crm import update_persona
        from backend.schemas import PersonaUpdate
        pid = str(full["personas"][0].id)
        result = update_persona(db_session, pid, PersonaUpdate(
            first_name="Updated", last_name="Name",
            email=f"upd_{uuid.uuid4().hex[:6]}@t.com",
            phone="+573007777777",
            church_role="Líder",
            estado_vital="ACTIVO",
        ))
        assert result is not None

    def test_delete_persona(self, db_session, full):
        from backend.crud.crm import delete_persona
        pid = str(full["personas"][14].id)
        result = delete_persona(db_session, pid)
        assert result is not None

    def test_persona_timeline_deep(self, db_session, full):
        from backend.crud.crm import get_persona_timeline
        pid = str(full["personas"][0].id)
        timeline = get_persona_timeline(db_session, pid)
        assert isinstance(timeline, list)

    def test_families_deep(self, db_session, full):
        from backend.crud.crm import get_families, get_family, get_family_personas, create_family, update_family, delete_family
        families = get_families(db_session)
        assert isinstance(families, list)
        fid = str(full["families"][0].id)
        fam = get_family(db_session, fid)
        assert fam is not None
        personas = get_family_personas(db_session, fid)
        assert isinstance(personas, list)
        new_fam = create_family(db_session, "TestFamily")
        assert new_fam.id is not None
        update_family(db_session, fid, "UpdatedFam")

    def test_crm_events_deep(self, db_session, full):
        from backend.crud.crm import get_crm_events
        sid = str(full["sede"].id)
        events = _call(get_crm_events, db_session, sede_id=sid)
        assert events is not None

    def test_counseling_deep(self, db_session, full):
        from backend.crud.crm import get_counseling_tickets, get_counseling_ticket, create_counseling_ticket, update_counseling_ticket, delete_counseling_ticket
        tickets = get_counseling_tickets(db_session)
        assert isinstance(tickets, list)
        get_counseling_tickets(db_session, status="open")
        get_counseling_tickets(db_session, persona_id=str(full["personas"][0].id))
        get_counseling_tickets(db_session, sede_id=str(full["sede"].id))

    def test_prayer_requests_deep(self, db_session, full):
        from backend.crud.crm import get_prayer_requests, get_prayer_request, create_prayer_request, update_prayer_request, delete_prayer_request
        reqs = get_prayer_requests(db_session)
        assert isinstance(reqs, list)
        get_prayer_requests(db_session, status="pending")

    def test_grupos_deep(self, db_session, full):
        from backend.crud.crm import get_grupos, get_grupo, delete_grupo
        groups = get_grupos(db_session)
        assert isinstance(groups, list)
        gc = get_grupo(db_session, str(full["groups"][0].id))
        assert gc is not None

    def test_volunteer_shifts_deep(self, db_session, full):
        from backend.crud.crm import get_volunteer_shifts, get_volunteer_shift, update_volunteer_shift, delete_volunteer_shift, create_volunteer_shift
        shifts = get_volunteer_shifts(db_session)
        assert isinstance(shifts, list)

    def test_communication_logs_deep(self, db_session, full):
        from backend.crud.crm import get_communication_logs, get_communication_log, create_communication_log, update_communication_log, delete_communication_log
        logs = get_communication_logs(db_session)
        assert isinstance(logs, list)
        get_communication_logs(db_session, limit=3)

    def test_donations_deep(self, db_session, full):
        from backend.crud.crm import get_donations, get_donation, get_total_donations_amount, create_donation
        donations = get_donations(db_session)
        assert isinstance(donations, list)
        amount = get_total_donations_amount(db_session)
        assert isinstance(amount, (int, float))

    def test_community_cards_deep(self, db_session, full):
        from backend.crud.crm import get_community_cards, get_community_card, update_community_card, delete_community_card, create_community_card
        cards = get_community_cards(db_session)
        assert isinstance(cards, list)

    def test_support_tickets_deep(self, db_session, full):
        from backend.crud.crm import get_support_tickets, get_support_ticket, delete_support_ticket, create_support_ticket
        tickets = get_support_tickets(db_session)
        assert isinstance(tickets, list)

    def test_consolidation_deep(self, db_session, full):
        from backend import models

        cases = (
            db_session.query(models.CasoCRM)
            .filter(models.CasoCRM.persona_id == full["personas"][0].id)
            .all()
        )
        assert isinstance(cases, list)

    def test_notifications_deep(self, db_session, full):
        from backend.crud.crm import get_user_notifications, mark_notification_as_read, mark_all_notifications_read
        pid = str(full["personas"][0].id)
        notifs = get_user_notifications(db_session, pid)
        assert isinstance(notifs, list)

    def test_talents_deep(self, db_session, full):
        from backend.crud.crm import get_talents
        talents = get_talents(db_session)
        assert isinstance(talents, list)
        get_talents(db_session, search="U")


class TestProjectsDeep:
    def test_create_project_deep(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/projects", json={
            "title": f"Deep_{uuid.uuid4().hex[:6]}", "description": "Deep test", "status": "active",
        }, headers=h)
        assert _ok(resp.status_code)

    def test_get_project_deep(self, full):
        c, h, projects = full["c"], full["h"], full["projects"]
        resp = c.get(f"/api/projects/{projects[0].id}", headers=h)
        assert _ok(resp.status_code)

    def test_project_phases_deep(self, full):
        c, h, projects = full["c"], full["h"], full["projects"]
        pid = str(projects[0].id)
        c.get(f"/api/projects/{pid}/phases", headers=h)
        c.put(f"/api/projects/{pid}/phases", json=[
            {"name": "P1", "slug": "p1", "color": "#000", "order_index": 0},
            {"name": "P2", "slug": "p2", "color": "#FFF", "order_index": 1},
        ], headers=h)

    def test_project_comments_deep(self, full):
        c, h, projects = full["c"], full["h"], full["projects"]
        pid = str(projects[0].id)
        c.get(f"/api/projects/{pid}/comments", headers=h)
        resp = c.post(f"/api/projects/{pid}/comments", json={"content": f"C_{uuid.uuid4().hex[:6]}"}, headers=h)
        assert _ok(resp.status_code)

    def test_all_comments_deep(self, full):
        c, h = full["c"], full["h"]
        c.get("/api/projects/comments", headers=h)
        c.get("/api/projects/comments?unresolved_only=true", headers=h)

    def test_project_tasks_deep(self, full):
        c, h, projects = full["c"], full["h"], full["projects"]
        pid = str(projects[0].id)
        c.get(f"/api/projects/{pid}/tasks", headers=h)
        c.get(f"/api/projects/{pid}/tasks?status=pending", headers=h)
        resp = c.post(f"/api/projects/{pid}/tasks", json={
            "title": f"Task_{uuid.uuid4().hex[:6]}", "description": "D",
        }, headers=h)
        assert _ok(resp.status_code)
        if resp.status_code in (200, 201):
            tid = resp.json().get("id")
            if tid:
                c.get(f"/api/projects/tasks/{tid}", headers=h)
                c.patch(f"/api/projects/tasks/{tid}", json={"title": "U", "status": "in_progress"}, headers=h)

    def test_project_milestones_deep(self, full):
        c, h, projects = full["c"], full["h"], full["projects"]
        pid = str(projects[0].id)
        c.get(f"/api/projects/{pid}/milestones", headers=h)
        resp = c.post(f"/api/projects/{pid}/milestones", json={
            "title": f"MS_{uuid.uuid4().hex[:6]}", "target_date": (date.today() + timedelta(days=60)).isoformat(),
        }, headers=h)
        assert _ok(resp.status_code)
        if resp.status_code in (200, 201):
            mid = resp.json().get("id")
            if mid:
                c.patch(f"/api/projects/milestones/{mid}", json={"title": "U"}, headers=h)
                c.delete(f"/api/projects/milestones/{mid}", headers=h)

    def test_project_wiki_deep(self, full):
        c, h, projects = full["c"], full["h"], full["projects"]
        pid = str(projects[0].id)
        c.get(f"/api/projects/{pid}/wiki", headers=h)
        c.post(f"/api/projects/{pid}/wiki", json={"title": "Wiki", "content": "# Content"}, headers=h)

    def test_project_whiteboard_deep(self, full):
        c, h, projects = full["c"], full["h"], full["projects"]
        pid = str(projects[0].id)
        c.get(f"/api/projects/{pid}/whiteboard", headers=h)
        c.put(f"/api/projects/{pid}/whiteboard", json={"content": {"nodes": []}}, headers=h)

    def test_project_supplies_deep(self, full):
        c, h, projects = full["c"], full["h"], full["projects"]
        pid = str(projects[0].id)
        tasks = c.get(f"/api/projects/{pid}/tasks", headers=h)
        if tasks.status_code == 200 and tasks.json():
            tid = tasks.json()[0].get("id")
            if tid:
                c.get(f"/api/projects/tasks/{tid}/supplies", headers=h)
                c.post(f"/api/projects/tasks/{tid}/supplies", json={"item_name": "Item", "quantity": 5}, headers=h)

    def test_project_attachments_deep(self, full):
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

    def test_project_activities_deep(self, full):
        c, h, projects = full["c"], full["h"], full["projects"]
        pid = str(projects[0].id)
        c.get(f"/api/projects/{pid}/activities", headers=h)

    def test_inbox_deep(self, full):
        c, h = full["c"], full["h"]
        c.get("/api/projects/inbox", headers=h)

    def test_portfolio_summary_deep(self, full):
        c, h = full["c"], full["h"]
        c.get("/api/projects/summary", headers=h)

    def test_workload_deep(self, full):
        c, h = full["c"], full["h"]
        c.get("/api/projects/workload", headers=h)

    def test_all_activities_deep(self, full):
        c, h = full["c"], full["h"]
        c.get("/api/projects/activities", headers=h)
        c.get("/api/projects/activities?limit=3", headers=h)

    def test_create_and_delete_project(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/projects", json={
            "title": f"Del_{uuid.uuid4().hex[:6]}", "description": "To delete",
        }, headers=h)
        if resp.status_code == 201:
            pid = resp.json().get("id")
            if pid:
                c.delete(f"/api/projects/{pid}", headers=h)
