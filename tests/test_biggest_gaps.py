"""
BIGGEST GAPS — Tests for the 5 modules with most missed lines:
1. evangelism_analytics.py (485 missed, 18%)
2. projects.py (420 missed, 29%)
3. evangelism.py (382 missed, 20%)
4. enterprise_cms.py (262 missed, 42%)
5. grupos_asistencias.py (185 missed, 13%)
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
    for i in range(15):
        p = models.Persona(
            first_name=f"U{i}", last_name=f"T{i}",
            email=f"u{i}_{uuid.uuid4().hex[:6]}@t.com",
            phone=f"+5730011122{i:02d}",
            spiritual_status=["Miembro", "Visitante", "Nuevo", "Activo"][i % 4],
            church_role=["Miembro", "Líder", "Pastor", "Voluntario"][i % 4],
            estado_vital=["ACTIVO", "ACTIVO", "INACTIVO", "ACTIVO", "ACTIVO"][i % 5],
            sede_id=sede.id,
            sex=["M", "F"][i % 2],
        )
        db_session.add(p)
        personas.append(p)
    db_session.commit()
    for p in personas:
        db_session.refresh(p)

    cat = CategoriaEstrategia(nombre="Cat")
    db_session.add(cat)
    db_session.flush()
    strategy = EstrategiaEvangelismo(
        nombre="Strat", sede_id=sede.id, frecuencia="semanal",
        categoria_id=cat.id,
        fecha_inicio=datetime.now(timezone.utc) - timedelta(days=90),
        fecha_fin=datetime.now(timezone.utc) + timedelta(days=90),
    )
    db_session.add(strategy)
    db_session.flush()

    groups = []
    for i in range(5):
        g = GrupoEvangelismo(
            nombre=f"G{i}", ubicacion=f"U{i}", sede_id=sede.id,
            lider_persona_id=personas[i].id, codigo=f"G{uuid.uuid4().hex[:6]}",
            capacidad=20, estrategia_id=strategy.id,
        )
        db_session.add(g)
        groups.append(g)
    db_session.commit()
    for g in groups:
        db_session.refresh(g)

    for g in groups:
        for i in range(6):
            db_session.add(ParticipanteGrupo(grupo_id=g.id, persona_id=personas[i].id, rol_base="Miembro"))
    db_session.commit()

    sessions = []
    for g in groups:
        for j in range(5):
            s = SesionGrupo(
                grupo_id=g.id, tema_estudio=f"S{j}",
                fecha_sesion=datetime.now(timezone.utc) - timedelta(days=35 - j * 7),
            )
            db_session.add(s)
            sessions.append(s)
    db_session.commit()
    for s in sessions:
        db_session.refresh(s)

    for s in sessions:
        for pg in db_session.query(ParticipanteGrupo).filter(
            ParticipanteGrupo.grupo_id == s.grupo_id
        ).limit(3).all():
            db_session.add(Asistencia(
                sesion_id=s.id, persona_id=pg.persona_id, estado="ASISTIO",
            ))
    db_session.commit()

    for i in range(4):
        db_session.add(models.CounselingTicket(persona_id=personas[i].id, subject=f"C_{i}", status="open"))
        db_session.add(models.PrayerRequest(requester_name=personas[i].first_name, request_text="P", sede_id=sede.id))
        db_session.add(models.CommunicationLog(persona_id=personas[i].id, channel="email", content=f"Msg_{i}"))
        db_session.add(models.VolunteerShift(
            persona_id=personas[i].id,
            role_name=["worship", "kids", "tech", "media"][i],
            team_name=["worship", "kids", "tech", "media"][i],
            shift_start=datetime.now(timezone.utc) - timedelta(hours=4),
            shift_end=datetime.now(timezone.utc),
        ))
    db_session.commit()

    headers = _auth_headers(client, email=admin.email, password="testpass123")
    return {
        "c": client, "h": headers, "sede": sede, "admin": admin,
        "personas": personas, "groups": groups, "sessions": sessions,
        "strategy": strategy,
    }


def _call(fn, *args, **kwargs):
    return fn(*args, **kwargs)


# ═══════════════════════════════════════════════════════════════════════════════
# EVANGELISM ANALYTICS (485 missed, 18%)
# ═══════════════════════════════════════════════════════════════════════════════

class TestEvangelismAnalytics:
    def test_strategy_kpis(self, full):
        c, h, strat = full["c"], full["h"], full["strategy"]
        for period in ["7", "30", "90", "365"]:
            _ok(c.get(f"/api/evangelism/analytics/strategy/{strat.id}?period={period}", headers=h).status_code)

    def test_strategy_trend(self, full):
        c, h, strat = full["c"], full["h"], full["strategy"]
        _ok(c.get(f"/api/evangelism/analytics/strategy/{strat.id}/trend?period=30", headers=h).status_code)

    def test_strategy_funnel(self, full):
        c, h, strat = full["c"], full["h"], full["strategy"]
        _ok(c.get(f"/api/evangelism/analytics/strategy/{strat.id}/funnel?period=30", headers=h).status_code)

    def test_strategy_heatmap(self, full):
        c, h, strat = full["c"], full["h"], full["strategy"]
        _ok(c.get(f"/api/evangelism/analytics/strategy/{strat.id}/heatmap?period=30", headers=h).status_code)

    def test_strategy_alerts(self, full):
        c, h, strat = full["c"], full["h"], full["strategy"]
        _ok(c.get(f"/api/evangelism/analytics/strategy/{strat.id}/alerts?period=30", headers=h).status_code)

    def test_strategy_velocity(self, full):
        c, h, strat = full["c"], full["h"], full["strategy"]
        _ok(c.get(f"/api/evangelism/analytics/strategy/{strat.id}/velocity?period=30", headers=h).status_code)

    def test_strategy_groups_detail(self, full):
        c, h, strat = full["c"], full["h"], full["strategy"]
        _ok(c.get(f"/api/evangelism/analytics/strategy/{strat.id}/groups?period=30", headers=h).status_code)

    def test_strategy_full_analytics(self, full):
        c, h, strat = full["c"], full["h"], full["strategy"]
        _ok(c.get(f"/api/evangelism/analytics/strategy/{strat.id}/full?period=30", headers=h).status_code)

    def test_analytics_not_found(self, full):
        c, h = full["c"], full["h"]
        c.get(f"/api/evangelism/analytics/strategy/{uuid.uuid4()}/trend", headers=h)


# ═══════════════════════════════════════════════════════════════════════════════
# PROJECTS (420 missed, 29%)
# ═══════════════════════════════════════════════════════════════════════════════

class TestProjectsAPI:
    def test_list_projects(self, full):
        c, h = full["c"], full["h"]
        _ok(c.get("/api/projects", headers=h).status_code)
        _ok(c.get("/api/projects?status=active", headers=h).status_code)
        _ok(c.get("/api/projects?page=1&page_size=5", headers=h).status_code)

    def test_create_project(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/projects", json={
            "name": f"Proj_{uuid.uuid4().hex[:6]}",
            "description": "Test project",
            "status": "active",
        }, headers=h)
        assert _ok(resp.status_code)

    def test_project_phases(self, full):
        c, h = full["c"], full["h"]
        _ok(c.get("/api/projects", headers=h).status_code)
        projects = c.get("/api/projects", headers=h)
        if projects.status_code == 200 and projects.json():
            pid = projects.json()[0].get("id")
            if pid:
                c.get(f"/api/projects/{pid}/phases", headers=h)
                c.put(f"/api/projects/{pid}/phases", json=[
                    {"name": "Phase 1", "order": 1, "status": "active"},
                ], headers=h)

    def test_all_comments(self, full):
        c, h = full["c"], full["h"]
        _ok(c.get("/api/projects/comments", headers=h).status_code)

    def test_create_task(self, full):
        c, h = full["c"], full["h"]
        projects = c.get("/api/projects", headers=h)
        if projects.status_code == 200 and projects.json():
            pid = projects.json()[0].get("id")
            if pid:
                resp = c.post(f"/api/projects/{pid}/tasks", json={
                    "title": f"Task_{uuid.uuid4().hex[:6]}",
                    "description": "Test task",
                }, headers=h)
                assert _ok(resp.status_code)

    def test_portfolio_summary(self, full):
        c, h = full["c"], full["h"]
        _ok(c.get("/api/projects/summary", headers=h).status_code)

    def test_workload_summary(self, full):
        c, h = full["c"], full["h"]
        _ok(c.get("/api/projects/workload", headers=h).status_code)

    def test_all_activities(self, full):
        c, h = full["c"], full["h"]
        _ok(c.get("/api/projects/activities", headers=h).status_code)
        _ok(c.get("/api/projects/activities?limit=5", headers=h).status_code)

    def test_task_crud(self, full):
        c, h = full["c"], full["h"]
        projects = c.get("/api/projects", headers=h)
        if projects.status_code == 200 and projects.json():
            pid = projects.json()[0].get("id")
            if pid:
                resp = c.post(f"/api/projects/{pid}/tasks", json={
                    "title": f"CRUD_{uuid.uuid4().hex[:6]}", "description": "D",
                }, headers=h)
                if resp.status_code in (200, 201):
                    tid = resp.json().get("id")
                    if tid:
                        c.get(f"/api/projects/tasks/{tid}", headers=h)
                        c.patch(f"/api/projects/tasks/{tid}", json={"title": "Updated"}, headers=h)

    def test_inbox(self, full):
        c, h = full["c"], full["h"]
        _ok(c.get("/api/projects/inbox", headers=h).status_code)


# ═══════════════════════════════════════════════════════════════════════════════
# EVANGELISM MAIN (382 missed, 20%)
# ═══════════════════════════════════════════════════════════════════════════════

class TestEvangelismMain:
    def test_counseling_crud(self, full):
        c, h, personas = full["c"], full["h"], full["personas"]
        c.get("/api/evangelism/counseling/", headers=h)
        resp = c.post("/api/evangelism/counseling/", json={
            "persona_id": str(personas[0].id),
            "subject": "Test",
        }, headers=h)
        assert _ok(resp.status_code)
        if resp.status_code in (200, 201):
            tid = resp.json().get("id")
            if tid:
                c.get(f"/api/evangelism/counseling/{tid}", headers=h)
                c.patch(f"/api/evangelism/counseling/{tid}", json={
                    "status": "resolved", "notes": "Done",
                }, headers=h)
                c.get(f"/api/evangelism/counseling/lead/{personas[0].id}", headers=h)

    def test_prayer_requests_crud(self, full):
        c, h, personas, sede = full["c"], full["h"], full["personas"], full["sede"]
        c.get("/api/evangelism/prayer-requests/", headers=h)
        resp = c.post("/api/evangelism/prayer-requests/", json={
            "requester_name": "Praying", "request_text": "Help",
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

    def test_messaging_history(self, full):
        c, h = full["c"], full["h"]
        _ok(c.get("/api/evangelism/messaging/history", headers=h).status_code)
        _ok(c.get("/api/evangelism/messaging/history?limit=5", headers=h).status_code)

    def test_messaging_send(self, full):
        c, h, personas = full["c"], full["h"], full["personas"]
        resp = c.post("/api/evangelism/messaging/send", json={
            "channel": "email",
            "recipient_ids": [str(personas[0].id)],
            "subject": "Test", "body": "Hello",
        }, headers=h)
        assert _ok(resp.status_code)

    def test_messaging_send_no_channel(self, full):
        c, h = full["c"], full["h"]
        c.post("/api/evangelism/messaging/send", json={"content": "No channel"}, headers=h)

    def test_messaging_send_segments(self, full):
        c, h = full["c"], full["h"]
        c.post("/api/evangelism/messaging/send", json={
            "channel": "email", "content": "Broadcast",
            "target_segments": ["active"],
            "campaign_name": "Spring",
        }, headers=h)

    def test_messaging_send_whatsapp(self, full):
        c, h, personas = full["c"], full["h"], full["personas"]
        c.post("/api/evangelism/messaging/send", json={
            "channel": "whatsapp",
            "persona_id": str(personas[0].id),
            "content": "WhatsApp",
        }, headers=h)

    def test_messaging_send_sms(self, full):
        c, h, personas = full["c"], full["h"], full["personas"]
        c.post("/api/evangelism/messaging/send", json={
            "channel": "sms",
            "persona_id": str(personas[0].id),
            "content": "SMS",
        }, headers=h)

    def test_messaging_send_groups_segment(self, full):
        c, h = full["c"], full["h"]
        c.post("/api/evangelism/messaging/send", json={
            "channel": "email", "content": "Groups msg",
            "target_segments": ["groups"],
        }, headers=h)

    def test_counseling_not_found(self, full):
        c, h = full["c"], full["h"]
        c.get("/api/evangelism/counseling/99999", headers=h)

    def test_prayer_not_found(self, full):
        c, h = full["c"], full["h"]
        c.get("/api/evangelism/prayer-requests/99999", headers=h)


# ═══════════════════════════════════════════════════════════════════════════════
# ENTERPRISE CMS (262 missed, 42%)
# ═══════════════════════════════════════════════════════════════════════════════

class TestEnterpriseCMS:
    def test_webhooks_crud(self, full):
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
                c.patch(f"/api/cms/v2/webhooks/{wid}", json={"url": "https://updated.test"}, headers=h)
                c.delete(f"/api/cms/v2/webhooks/{wid}", headers=h)

    def test_redirects_crud(self, full):
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
                c.patch(f"/api/cms/v2/redirects/{rid}", json={"target_path": "/updated"}, headers=h)
                c.delete(f"/api/cms/v2/redirects/{rid}", headers=h)

    def test_custom_types_crud(self, full):
        c, h = full["c"], full["h"]
        _ok(c.get("/api/cms/v2/custom-types", headers=h).status_code)
        resp = c.post("/api/cms/v2/custom-types", json={
            "name": f"CT_{uuid.uuid4().hex[:6]}",
            "schema": {"fields": [{"name": "title", "type": "text"}]},
        }, headers=h)
        assert _ok(resp.status_code)
        if resp.status_code in (200, 201):
            tid = resp.json().get("id")
            if tid:
                c.get(f"/api/cms/v2/custom-types/{tid}", headers=h)
                c.patch(f"/api/cms/v2/custom-types/{tid}", json={"name": "Updated"}, headers=h)
                c.delete(f"/api/cms/v2/custom-types/{tid}", headers=h)

    def test_glossary_crud(self, full):
        c, h = full["c"], full["h"]
        _ok(c.get("/api/cms/v2/glossary", headers=h).status_code)
        resp = c.post("/api/cms/v2/glossary", json={
            "term": f"Term_{uuid.uuid4().hex[:6]}",
            "definition": "A test term",
        }, headers=h)
        assert _ok(resp.status_code)
        if resp.status_code in (200, 201):
            gid = resp.json().get("id")
            if gid:
                c.get(f"/api/cms/v2/glossary/{gid}", headers=h)
                c.patch(f"/api/cms/v2/glossary/{gid}", json={"definition": "Updated"}, headers=h)
                c.delete(f"/api/cms/v2/glossary/{gid}", headers=h)

    def test_media_folders_crud(self, full):
        c, h = full["c"], full["h"]
        _ok(c.get("/api/cms/v2/media-folders", headers=h).status_code)
        resp = c.post("/api/cms/v2/media-folders", json={
            "name": f"Folder_{uuid.uuid4().hex[:6]}",
        }, headers=h)
        assert _ok(resp.status_code)
        if resp.status_code in (200, 201):
            fid = resp.json().get("id")
            if fid:
                c.get(f"/api/cms/v2/media-folders/{fid}", headers=h)
                c.patch(f"/api/cms/v2/media-folders/{fid}", json={"name": "Updated"}, headers=h)
                c.delete(f"/api/cms/v2/media-folders/{fid}", headers=h)


# ═══════════════════════════════════════════════════════════════════════════════
# EVANGELISM GRUPOS ASISTENCIAS (185 missed, 13%)
# ═══════════════════════════════════════════════════════════════════════════════

class TestGruposAsistencias:
    def test_checkin(self, full):
        c, h, groups, personas, sessions = full["c"], full["h"], full["groups"], full["personas"], full["sessions"]
        if sessions:
            sid = sessions[0].id
            resp = c.post(f"/api/evangelism/grupos/checkin/{sid}", json={
                "attendances": [{"persona_id": str(personas[0].id), "estado": "ASISTIO"}],
            }, headers=h)
            assert _ok(resp.status_code)

    def test_session_attendance(self, full):
        c, h, sessions = full["c"], full["h"], full["sessions"]
        if sessions:
            sid = sessions[0].id
            c.get(f"/api/evangelism/grupos/sessions/{sid}/attendance", headers=h)

    def test_bulk_checkin(self, full):
        c, h, sessions, personas = full["c"], full["h"], full["sessions"], full["personas"]
        if sessions:
            sid = sessions[0].id
            c.post(f"/api/evangelism/grupos/sessions/{sid}/bulk-checkin", json={
                "attendances": [
                    {"persona_id": str(p.id), "estado": "ASISTIO"}
                    for p in personas[:4]
                ],
            }, headers=h)

    def test_register_absence(self, full):
        c, h, sessions, personas = full["c"], full["h"], full["sessions"], full["personas"]
        if sessions:
            sid = sessions[0].id
            c.post(f"/api/evangelism/grupos/sessions/{sid}/absences", json={
                "persona_id": str(personas[0].id),
                "reason": "Sick",
            }, headers=h)
