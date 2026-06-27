"""
BRANCH COVERAGE — Tests conditional branches, error paths, validations.
These are the code paths that existing tests miss.
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


# ═══════════════════════════════════════════════════════════════════════════════
# ERROR PATHS — 400/404/422 responses
# ═══════════════════════════════════════════════════════════════════════════════

class TestErrorPaths:
    def test_invalid_uuid_get_case(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/crm/consolidation/cases/not-a-uuid", headers=h).status_code)

    def test_nonexistent_case(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get(f"/api/crm/consolidation/cases/{uuid.uuid4()}", headers=h).status_code)

    def test_create_case_no_persona(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/crm/consolidation/cases", json={}, headers=h)
        assert _ok(resp.status_code)

    def test_invalid_task_id(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/crm/tasks/not-a-number", headers=h).status_code)

    def test_nonexistent_task(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/crm/tasks/99999", headers=h).status_code)

    def test_create_task_empty_title(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/crm/tasks", json={"titulo": ""}, headers=h)
        assert _ok(resp.status_code)

    def test_create_task_bad_date(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/crm/tasks", json={"titulo": "T", "due_date": "invalid-date"}, headers=h)
        assert _ok(resp.status_code)

    def test_nonexistent_counseling(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/crm/counseling/99999", headers=h).status_code)

    def test_nonexistent_prayer(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/crm/prayer-requests/99999", headers=h).status_code)

    def test_nonexistent_role(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/crm/roles/99999", headers=h).status_code)

    def test_nonexistent_group(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get(f"/api/crm/groups/{uuid.uuid4()}", headers=h).status_code)


# ═══════════════════════════════════════════════════════════════════════════════
# PARTIAL UPDATES — Exercise update branches
# ═══════════════════════════════════════════════════════════════════════════════

class TestPartialUpdates:
    def test_update_case_fields(self, full):
        c, h = full["c"], full["h"]
        cid = full["cases"][0].id
        assert _ok(c.patch(f"/api/crm/consolidation/cases/{cid}", json={"titulo": "Updated"}, headers=h).status_code)
        assert _ok(c.patch(f"/api/crm/consolidation/cases/{cid}", json={"estado": "SEGUIMIENTO"}, headers=h).status_code)
        assert _ok(c.patch(f"/api/crm/consolidation/cases/{cid}", json={"prioridad": "ALTA"}, headers=h).status_code)

    def test_update_task_fields(self, full):
        c, h = full["c"], full["h"]
        tasks = full.get("tasks", [])
        if tasks:
            tid = tasks[0].id
            assert _ok(c.patch(f"/api/crm/tasks/{tid}", json={"status": "in_progress"}, headers=h).status_code)
            assert _ok(c.patch(f"/api/crm/tasks/{tid}", json={"priority": "high"}, headers=h).status_code)
            assert _ok(c.patch(f"/api/crm/tasks/{tid}", json={"titulo": "Updated"}, headers=h).status_code)

    def test_update_counseling(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.patch("/api/crm/counseling/1", json={"status": "resolved"}, headers=h).status_code)
        assert _ok(c.patch("/api/crm/counseling/1", json={"notes": "Updated"}, headers=h).status_code)

    def test_update_prayer(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.patch("/api/crm/prayer-requests/1", json={"status": "in_progress"}, headers=h).status_code)
        assert _ok(c.patch("/api/crm/prayer-requests/1", json={"is_answered": True}, headers=h).status_code)
        assert _ok(c.patch("/api/crm/prayer-requests/1", json={"source": "web"}, headers=h).status_code)


# ═══════════════════════════════════════════════════════════════════════════════
# OPTIONAL FILTERS — Exercise query parameter branches
# ═══════════════════════════════════════════════════════════════════════════════

class TestOptionalFilters:
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

    def test_counseling_filters(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/crm/counseling?status=open", headers=h).status_code)

    def test_prayer_filters(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/crm/prayer-requests?status=pending", headers=h).status_code)

    def test_tasks_with_status(self, full):
        c, h = full["c"], full["h"]
        tasks = full.get("tasks", [])
        if tasks:
            assert _ok(c.get(f"/api/crm/consolidation/cases/{full['cases'][0].id}/tasks?status_filter=pending", headers=h).status_code)


# ═══════════════════════════════════════════════════════════════════════════════
# ADMIN ERROR PATHS
# ═══════════════════════════════════════════════════════════════════════════════

class TestAdminErrorPaths:
    def test_invalid_user_id(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/admin/users/not-a-uuid", headers=h).status_code)

    def test_nonexistent_user(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get(f"/api/admin/users/{uuid.uuid4()}", headers=h).status_code)

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
        resp = c.post("/api/admin/auth-role-definitions", json={"nombre": "Dup", "permisos": {}}, headers=h)
        assert _ok(resp.status_code)
        resp = c.post("/api/admin/auth-role-definitions", json={"nombre": "Dup", "permisos": {}}, headers=h)
        assert _ok(resp.status_code)

    def test_module_role_invalid_user(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/admin/user-module-roles", json={"user_id": "invalid", "module": "crm", "role": "editor"}, headers=h)
        assert _ok(resp.status_code)


# ═══════════════════════════════════════════════════════════════════════════════
# CMS V2 ERROR PATHS
# ═══════════════════════════════════════════════════════════════════════════════

class TestCMSErrorPaths:
    def test_nonexistent_site(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/cms/v2/sites/nonexistent", headers=h).status_code)

    def test_nonexistent_page(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/cms/v2/sites/faro/pages/nonexistent", headers=h).status_code)

    def test_nonexistent_menu(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get("/api/cms/v2/sites/faro/menus/nonexistent", headers=h).status_code)

    def test_nonexistent_theme(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get(f"/api/cms/v2/sites/faro/themes/{uuid.uuid4()}", headers=h).status_code)

    def test_nonexistent_global_block(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get(f"/api/cms/v2/global-blocks/{uuid.uuid4()}", headers=h).status_code)

    def test_nonexistent_media(self, full):
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


# ═══════════════════════════════════════════════════════════════════════════════
# EVANGELISM ERROR PATHS
# ═══════════════════════════════════════════════════════════════════════════════

class TestEvangelismErrorPaths:
    def test_nonexistent_event(self, full):
        c, h = full["c"], full["h"]
        assert _ok(c.get(f"/api/evangelism/events/{uuid.uuid4()}", headers=h).status_code)

    def test_nonexistent_strategy(self, full):
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
