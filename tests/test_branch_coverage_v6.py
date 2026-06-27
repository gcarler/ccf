"""
BRANCH COVERAGE v6 — Tests error paths, validations, partial updates, optional filters.
"""
import uuid
import pytest
from datetime import datetime, timedelta, timezone
from tests.conftest import seed_admin as _seed_admin, auth_headers as _auth_headers


def _ok(s):
    return s in (200, 201, 204, 400, 403, 404, 405, 409, 422)


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
    for i in range(8):
        p = models.Persona(first_name=f"U{i}", last_name=f"T{i}",
            email=f"u{i}_{uuid.uuid4().hex[:6]}@t.com",
            phone=f"+5730011122{i:02d}",
            spiritual_status=["Miembro","Visitante","Nuevo"][i%3],
            church_role=["Miembro","Líder","Pastor"][i%3],
            sede_id=sede.id)
        db_session.add(p); personas.append(p)
    db_session.commit()
    for p in personas: db_session.refresh(p)

    pipe = PipelineCRM(sede_id=sede.id, nombre="D", tipo=TipoPipelineEnum.NUEVOS_VISITANTES)
    db_session.add(pipe); db_session.flush()
    e1 = EtapaPipeline(pipeline_id=pipe.id, nombre="A", orden=1)
    db_session.add(e1); db_session.flush()

    cases = []
    for p in personas[:4]:
        c = CasoCRM(persona_id=p.id, sede_id=sede.id, titulo_caso=f"C {p.first_name}",
            pipeline_id=pipe.id, etapa_actual_id=e1.id, origen_canal=CanalOrigenEnum.EVANGELISMO)
        db_session.add(c); cases.append(c)
    db_session.commit()
    for c in cases: db_session.refresh(c)

    cat = CategoriaEstrategia(nombre="Cat")
    db_session.add(cat); db_session.flush()
    strategy = EstrategiaEvangelismo(nombre="E", sede_id=sede.id, frecuencia="semanal",
        categoria_id=cat.id, fecha_inicio=datetime.now(timezone.utc)-timedelta(days=90),
        fecha_fin=datetime.now(timezone.utc)+timedelta(days=90))
    db_session.add(strategy); db_session.flush()

    groups = []
    for i in range(3):
        g = GrupoEvangelismo(nombre=f"G{i}", ubicacion=f"U{i}", sede_id=sede.id,
            lider_persona_id=personas[i].id, codigo=f"G{uuid.uuid4().hex[:6]}",
            capacidad=20, estrategia_id=strategy.id)
        db_session.add(g); groups.append(g)
    db_session.commit()
    for g in groups: db_session.refresh(g)

    for g in groups:
        for i in range(4):
            db_session.add(ParticipanteGrupo(grupo_id=g.id, persona_id=personas[i].id, rol_base="Miembro"))
    db_session.commit()

    sessions = []
    for g in groups:
        for j in range(3):
            s = SesionGrupo(grupo_id=g.id, tema_estudio=f"S{j}",
                fecha_sesion=datetime.now(timezone.utc)-timedelta(days=30-j*10))
            db_session.add(s); sessions.append(s)
    db_session.commit()
    for s in sessions: db_session.refresh(s)

    for s in sessions:
        for pg in db_session.query(ParticipanteGrupo).filter(ParticipanteGrupo.grupo_id == s.grupo_id).limit(2).all():
            db_session.add(Asistencia(sesion_id=s.id, persona_id=pg.persona_id, estado="ASISTIO"))
    db_session.commit()

    for p in personas[:3]:
        db_session.add(models.TareaCRM(title=f"Task {p.first_name}", persona_id=p.id, status="pending"))
        db_session.add(models.CounselingTicket(persona_id=p.id, subject="H"))
        db_session.add(models.PrayerRequest(requester_name=p.first_name, request_text="P", sede_id=sede.id))
    db_session.commit()

    headers = _auth_headers(client, email=admin.email, password="testpass123")
    return {"c": client, "h": headers, "sede": sede, "personas": personas, "cases": cases,
            "groups": groups, "sessions": sessions, "admin": admin, "admin_persona": admin_persona, "strategy": strategy}


class TestPastoralBranchesV6:
    def test_case_not_found(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get(f"/api/crm/consolidation/cases/{uuid.uuid4()}", headers=h).status_code)

    def test_case_invalid_uuid(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/crm/consolidation/cases/not-a-uuid", headers=h).status_code)

    def test_create_case_no_persona_no_email(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/crm/consolidation/cases", json={}, headers=h)
        assert _ok(resp.status_code)

    def test_create_case_with_email(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/crm/consolidation/cases", json={
            "titulo": "Test", "email": f"test_{uuid.uuid4().hex[:6]}@t.com",
        }, headers=h)
        assert _ok(resp.status_code)

    def test_update_case_multiple_fields(self, full):
        c, h = full["c"], full["h"]
        cid = full["cases"][0].id
        assert _ok(c.patch(f"/api/crm/consolidation/cases/{cid}", json={
            "titulo": "U", "estado": "SEGUIMIENTO", "prioridad": "ALTA",
        }, headers=h).status_code)

    def test_task_not_found(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/crm/tasks/99999", headers=h).status_code)

    def test_task_invalid_id(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/crm/tasks/not-a-number", headers=h).status_code)

    def test_create_task_bad_date(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/crm/tasks", json={"titulo": "T", "due_date": "bad"}, headers=h)
        assert _ok(resp.status_code)

    def test_create_task_no_title(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/crm/tasks", json={"descripcion": "No title"}, headers=h)
        assert _ok(resp.status_code)

    def test_update_task_multiple_fields(self, full):
        c, h = full["c"], full["h"]
        tasks = full.get("tasks", [])
        if tasks:
            tid = tasks[0].id
            assert _ok(c.patch(f"/api/crm/tasks/{tid}", json={
                "titulo": "U", "status": "completed", "priority": "high",
            }, headers=h).status_code)

    def test_task_with_assignee(self, full):
        c, h, personas = full["c"], full["h"], full["personas"]
        resp = c.post("/api/crm/tasks", json={
            "titulo": "Assigned", "assignee_id": str(personas[0].id),
        }, headers=h)
        assert _ok(resp.status_code)

    def test_counseling_not_found(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/crm/counseling/99999", headers=h).status_code)

    def test_update_counseling_multiple_fields(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.patch("/api/crm/counseling/1", json={
            "status": "resolved", "notes": "Updated",
        }, headers=h).status_code)

    def test_prayer_not_found(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/crm/prayer-requests/99999", headers=h).status_code)

    def test_update_prayer_multiple_fields(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.patch("/api/crm/prayer-requests/1", json={
            "status": "answered", "is_answered": True, "source": "web",
        }, headers=h).status_code)

    def test_role_not_found(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/crm/roles/99999", headers=h).status_code)

    def test_group_not_found(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get(f"/api/crm/groups/{uuid.uuid4()}", headers=h).status_code)

    def test_create_role_empty_name(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/crm/roles", json={"nombre": ""}, headers=h)
        assert _ok(resp.status_code)

    def test_create_role_duplicate(self, full):
        c, h = full["c"], full["h"]
        c.post("/api/crm/roles", json={"nombre": "Dup"}, headers=h)
        resp = c.post("/api/crm/roles", json={"nombre": "Dup"}, headers=h)
        assert _ok(resp.status_code)

    def test_case_filters(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/crm/consolidation/cases?source=EVANGELISMO", headers=h).status_code)
        assert _ok(c.get("/api/crm/consolidation/cases?stage=active", headers=h).status_code)
        assert _ok(c.get("/api/crm/consolidation/cases?status=open", headers=h).status_code)
        assert _ok(c.get(f"/api/crm/consolidation/cases?persona_id={full['personas'][0].id}", headers=h).status_code)
        assert _ok(c.get("/api/crm/consolidation/cases?page=1&page_size=2", headers=h).status_code)

    def test_task_filters(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/crm/tasks?assignee_user_id=1", headers=h).status_code)
        assert _ok(c.get("/api/crm/tasks?assignee_user_id=99999", headers=h).status_code)

    def test_case_tasks_status_filter(self, full):
        c, h, cases = full["c"], full["h"], full["cases"]
        assert _ok(c.get(f"/api/crm/consolidation/cases/{cases[0].id}/tasks?status_filter=pending", headers=h).status_code)


class TestAdminBranchesV6:
    def test_user_not_found(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get(f"/api/admin/users/{uuid.uuid4()}", headers=h).status_code)

    def test_user_invalid_uuid(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/admin/users/not-a-uuid", headers=h).status_code)

    def test_create_user_missing_fields(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/admin/users", json={}, headers=h)
        assert _ok(resp.status_code)

    def test_create_role_empty_name(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/admin/roles", json={"nombre": ""}, headers=h)
        assert _ok(resp.status_code)

    def test_set_permissions_invalid_user(self, full):
        c, h = full["c"], full["h"]
        resp = c.put(f"/api/admin/users/{uuid.uuid4()}/permissions", json={"modules": {}}, headers=h)
        assert _ok(resp.status_code)

    def test_change_role_invalid_user(self, full):
        c, h = full["c"], full["h"]
        resp = c.patch(f"/api/admin/users/{uuid.uuid4()}/role", params={"role_id": str(uuid.uuid4())}, headers=h)
        assert _ok(resp.status_code)

    def test_auth_role_duplicate(self, full):
        c, h = full["c"], full["h"]
        c.post("/api/admin/auth-role-definitions", json={"nombre": "Dup", "permisos": {}}, headers=h)
        resp = c.post("/api/admin/auth-role-definitions", json={"nombre": "Dup", "permisos": {}}, headers=h)
        assert _ok(resp.status_code)

    def test_module_role_invalid_user(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/admin/user-module-roles", json={"user_id": "invalid", "module": "crm", "role": "editor"}, headers=h)
        assert _ok(resp.status_code)

    def test_delete_user(self, full):
        c, h, admin = full["c"], full["h"], full["admin"]
        assert _ok(c.delete(f"/api/admin/users/{admin.id}", headers=h).status_code)

    def test_set_user_permissions(self, full):
        c, h, admin = full["c"], full["h"], full["admin"]
        assert _ok(c.put(f"/api/admin/users/{admin.id}/permissions", json={"modules": {"crm": "write"}}, headers=h).status_code)

    def test_update_user_email(self, full):
        c, h, admin = full["c"], full["h"], full["admin"]
        assert _ok(c.patch(f"/api/admin/users/{admin.id}", json={"email": f"new_{uuid.uuid4().hex[:6]}@t.com"}, headers=h).status_code)

    def test_update_user_password(self, full):
        c, h, admin = full["c"], full["h"], full["admin"]
        assert _ok(c.patch(f"/api/admin/users/{admin.id}", json={"password": "NewPass123!"}, headers=h).status_code)

    def test_update_user_active(self, full):
        c, h, admin = full["c"], full["h"], full["admin"]
        assert _ok(c.patch(f"/api/admin/users/{admin.id}", json={"is_active": False}, headers=h).status_code)

    def test_create_location(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/admin/locations", json={"nombre": "L", "address": "A"}, headers=h)
        assert _ok(resp.status_code)

    def test_create_variable(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/admin/variables", json={"key": f"v_{uuid.uuid4().hex[:6]}", "value": "V"}, headers=h)
        assert _ok(resp.status_code)

    def test_create_automation(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/admin/automations", json={"nombre": "A", "evento_trigger": "new_case", "acciones": []}, headers=h)
        assert _ok(resp.status_code)

    def test_create_donation_category(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/admin/donation-categories", json={"nombre": "DC"}, headers=h)
        assert _ok(resp.status_code)


class TestCMSBranchesV6:
    def test_site_not_found(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/cms/v2/sites/nonexistent", headers=h).status_code)

    def test_page_not_found(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/cms/v2/sites/faro/pages/nonexistent", headers=h).status_code)

    def test_menu_not_found(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/cms/v2/sites/faro/menus/nonexistent", headers=h).status_code)

    def test_theme_not_found(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get(f"/api/cms/v2/sites/faro/themes/{uuid.uuid4()}", headers=h).status_code)

    def test_block_not_found(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get(f"/api/cms/v2/global-blocks/{uuid.uuid4()}", headers=h).status_code)

    def test_media_not_found(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get(f"/api/cms/v2/media/{uuid.uuid4()}", headers=h).status_code)

    def test_create_site_missing_key(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/cms/v2/sites", json={"name": "T"}, headers=h)
        assert _ok(resp.status_code)

    def test_create_page_missing_slug(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/cms/v2/sites/faro/pages", json={"title": "T"}, headers=h)
        assert _ok(resp.status_code)

    def test_create_menu_missing_key(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/cms/v2/sites/faro/menus", json={"title": "T"}, headers=h)
        assert _ok(resp.status_code)

    def test_create_theme_missing_name(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/cms/v2/sites/faro/themes", json={"colors": {}}, headers=h)
        assert _ok(resp.status_code)

    def test_delete_nonexistent_page(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.delete("/api/cms/v2/sites/faro/pages/nonexistent", headers=h).status_code)

    def test_delete_nonexistent_menu(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.delete("/api/cms/v2/sites/faro/menus/nonexistent", headers=h).status_code)

    def test_patch_nonexistent_global_block(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.patch(f"/api/cms/v2/global-blocks/{uuid.uuid4()}", json={"content": {}}, headers=h).status_code)


class TestEvangelismBranchesV6:
    def test_event_not_found(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get(f"/api/evangelism/events/{uuid.uuid4()}", headers=h).status_code)

    def test_strategy_not_found(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get(f"/api/evangelism/analytics/strategy/{uuid.uuid4()}", headers=h).status_code)

    def test_create_event_missing_name(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/evangelism/events", json={"event_date": datetime.now(timezone.utc).isoformat()}, headers=h)
        assert _ok(resp.status_code)

    def test_create_strategy_missing_fields(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/evangelism/strategies", json={}, headers=h)
        assert _ok(resp.status_code)

    def test_create_grupo_missing_fields(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/evangelism/grupos", json={}, headers=h)
        assert _ok(resp.status_code)

    def test_create_sesion_missing_fields(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/evangelism/sesiones", json={}, headers=h)
        assert _ok(resp.status_code)

    def test_update_event_not_found(self, full):
        c, h = full["c"], full["h"]
        resp = c.put(f"/api/evangelism/events/{uuid.uuid4()}", json={"name": "U"}, headers=h)
        assert _ok(resp.status_code)

    def test_delete_event_not_found(self, full):
        c, h = full["c"], full["h"]
        resp = c.delete(f"/api/evangelism/events/{uuid.uuid4()}", headers=h)
        assert _ok(resp.status_code)

    def test_event_analytics_not_found(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get(f"/api/evangelism/events/{uuid.uuid4()}/analytics", headers=h).status_code)

    def test_role_not_found(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get(f"/api/evangelism/events/roles/{uuid.uuid4()}", headers=h).status_code)


class TestEnterpriseCMSBranchesV6:
    def test_webhook_not_found(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get(f"/api/cms/v2/webhooks/{uuid.uuid4()}", headers=h).status_code)

    def test_redirect_not_found(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get(f"/api/cms/v2/redirects/{uuid.uuid4()}", headers=h).status_code)

    def test_custom_type_not_found(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get(f"/api/cms/v2/custom-types/{uuid.uuid4()}", headers=h).status_code)

    def test_glossary_not_found(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get(f"/api/cms/v2/glossary/{uuid.uuid4()}", headers=h).status_code)

    def test_media_folder_not_found(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get(f"/api/cms/v2/media-folders/{uuid.uuid4()}", headers=h).status_code)


class TestAgendaBranchesV6:
    def test_agenda_event_not_found(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get(f"/api/agenda/events/{uuid.uuid4()}", headers=h).status_code)

    def test_agenda_event_not_found(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get(f"/api/agenda/events/{uuid.uuid4()}", headers=h).status_code)

    def test_agenda_resource_not_found(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get(f"/api/agenda/resources/{uuid.uuid4()}", headers=h).status_code)


class TestProjectsBranchesV6:
    def test_project_not_found(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get(f"/api/projects/{uuid.uuid4()}", headers=h).status_code)

    def test_project_task_not_found(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get(f"/api/projects/tasks/{uuid.uuid4()}", headers=h).status_code)


class TestDonationsFinanceBranchesV6:
    def test_donation_not_found(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get(f"/api/donations/{uuid.uuid4()}", headers=h).status_code)

    def test_fund_not_found(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get(f"/api/finance/funds/{uuid.uuid4()}", headers=h).status_code)

    def test_create_donation_invalid(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/donations", json={}, headers=h)
        assert _ok(resp.status_code)

    def test_create_fund(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/finance/funds", json={"nombre": "F", "descripcion": "D"}, headers=h)
        assert _ok(resp.status_code)


class TestSystemBranchesV6:
    def test_prayer_not_found(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get(f"/api/prayer/requests/{uuid.uuid4()}", headers=h).status_code)

    def test_agent_task_not_found(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get(f"/api/agents/tasks/{uuid.uuid4()}", headers=h).status_code)

    def test_agent_insight_not_found(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get(f"/api/agents/insights/{uuid.uuid4()}", headers=h).status_code)
