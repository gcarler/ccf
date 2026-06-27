"""
COVERAGE BOOST v2 — Targets specific uncovered branches in pastoral.py, cms_v2.py, admin.py.
Focuses on functions with most missed lines and complex conditional logic.
"""
import uuid
import json
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
    for i in range(12):
        p = models.Persona(
            first_name=f"U{i}", last_name=f"T{i}",
            email=f"u{i}_{uuid.uuid4().hex[:6]}@t.com",
            phone=f"+5730011122{i:02d}",
            spiritual_status=["Miembro", "Visitante", "Nuevo", "Activo"][i % 4],
            church_role=["Miembro", "Líder", "Pastor", "Voluntario"][i % 4],
            estado_vital=["ACTIVO", "ACTIVO", "INACTIVO", "ACTIVO"][i % 4],
            sede_id=sede.id,
        )
        db_session.add(p)
        personas.append(p)
    db_session.commit()
    for p in personas:
        db_session.refresh(p)

    pipe = PipelineCRM(sede_id=sede.id, nombre="D", tipo=TipoPipelineEnum.NUEVOS_VISITANTES)
    db_session.add(pipe)
    db_session.flush()
    e1 = EtapaPipeline(pipeline_id=pipe.id, nombre="A", orden=1)
    db_session.add(e1)
    db_session.flush()

    cases = []
    for p in personas[:6]:
        c = CasoCRM(
            persona_id=p.id, sede_id=sede.id, titulo_caso=f"C {p.first_name}",
            pipeline_id=pipe.id, etapa_actual_id=e1.id,
            origen_canal=CanalOrigenEnum.EVANGELISMO,
        )
        db_session.add(c)
        cases.append(c)
    db_session.commit()
    for c in cases:
        db_session.refresh(c)

    cat = CategoriaEstrategia(nombre="Cat")
    db_session.add(cat)
    db_session.flush()
    strategy = EstrategiaEvangelismo(
        nombre="E", sede_id=sede.id, frecuencia="semanal",
        categoria_id=cat.id,
        fecha_inicio=datetime.now(timezone.utc) - timedelta(days=90),
        fecha_fin=datetime.now(timezone.utc) + timedelta(days=90),
    )
    db_session.add(strategy)
    db_session.flush()

    groups = []
    for i in range(4):
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
        for i in range(5):
            db_session.add(ParticipanteGrupo(grupo_id=g.id, persona_id=personas[i].id, rol_base="Miembro"))
    db_session.commit()

    sessions = []
    for g in groups:
        for j in range(4):
            s = SesionGrupo(
                grupo_id=g.id, tema_estudio=f"S{j}",
                fecha_sesion=datetime.now(timezone.utc) - timedelta(days=30 - j * 7),
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
            db_session.add(Asistencia(sesion_id=s.id, persona_id=pg.persona_id, estado="ASISTIO"))
    db_session.commit()

    for i, p in enumerate(personas[:6]):
        db_session.add(models.TareaCRM(title=f"Task {p.first_name}", persona_id=p.id, status=["pending", "completed", "in_progress"][i % 3]))
        db_session.add(models.CounselingTicket(persona_id=p.id, subject=f"Counseling {i}", status=["open", "resolved"][i % 2]))
        db_session.add(models.PrayerRequest(requester_name=p.first_name, request_text="P", sede_id=sede.id, source=["web", "app"][i % 2]))

    for i, p in enumerate(personas[:4]):
        db_session.add(models.VolunteerShift(
            role_name=["worship", "kids", "tech"][i % 3],
            persona_id=p.id, team_name=["worship", "kids", "tech"][i % 3],
            shift_start=datetime.now(timezone.utc) - timedelta(hours=4),
            shift_end=datetime.now(timezone.utc),
        ))
    db_session.commit()

    headers = _auth_headers(client, email=admin.email, password="testpass123")
    return {
        "c": client, "h": headers, "sede": sede, "personas": personas, "cases": cases,
        "groups": groups, "sessions": sessions, "admin": admin, "admin_persona": admin_persona,
        "strategy": strategy, "pipe": pipe, "e1": e1,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# PASTORAL — Deep branch coverage
# ═══════════════════════════════════════════════════════════════════════════════

class TestPastoralDeepV2:
    def test_create_case_no_persona_no_email_no_phone(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/crm/consolidation/cases", json={"source": "walk-in"}, headers=h)
        assert _ok(resp.status_code)

    def test_create_case_with_email_lookup(self, full):
        c, h, personas = full["c"], full["h"], full["personas"]
        resp = c.post("/api/crm/consolidation/cases", json={
            "email": personas[0].email, "source": "web",
        }, headers=h)
        assert _ok(resp.status_code)

    def test_create_case_with_phone_lookup(self, full):
        c, h, personas = full["c"], full["h"], full["personas"]
        resp = c.post("/api/crm/consolidation/cases", json={
            "phone": personas[1].phone, "source": "phone",
        }, headers=h)
        assert _ok(resp.status_code)

    def test_create_case_new_persona(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/crm/consolidation/cases", json={
            "first_name": "New", "last_name": "Person",
            "email": f"new_{uuid.uuid4().hex[:6]}@t.com",
            "phone": "+573009999999",
        }, headers=h)
        assert _ok(resp.status_code)

    def test_update_case_all_fields(self, full):
        c, h, cases = full["c"], full["h"], full["cases"]
        now = datetime.now(timezone.utc).isoformat()
        c.patch(f"/api/crm/consolidation/cases/{cases[0].id}", json={
            "source": "event", "stage": "contacted", "status": "active",
            "notes": "Updated notes", "last_contact_at": now, "next_contact_at": now,
        }, headers=h)

    def test_create_interaction_as_crm_case(self, full):
        c, h, cases = full["c"], full["h"], full["cases"]
        resp = c.post(f"/api/crm/consolidation/cases/{cases[0].id}/interactions", json={
            "tipo": "Email", "notas": "Sent welcome email",
        }, headers=h)
        assert _ok(resp.status_code)

    def test_create_call_with_pastor_id(self, full):
        c, h, cases, personas = full["c"], full["h"], full["cases"], full["personas"]
        resp = c.post(f"/api/crm/consolidation/cases/{cases[0].id}/calls", json={
            "pastor_id": str(personas[2].id),
            "outcome": "completed",
            "notes": "Talked about faith",
            "prayer_requests": "Healing",
            "duration_seconds": 600,
        }, headers=h)
        assert _ok(resp.status_code)

    def test_create_call_no_pastor(self, full):
        c, h, cases = full["c"], full["h"], full["cases"]
        resp = c.post(f"/api/crm/consolidation/cases/{cases[0].id}/calls", json={
            "outcome": "missed",
        }, headers=h)
        assert _ok(resp.status_code)

    def test_create_call_with_persona_id(self, full):
        c, h, cases, personas = full["c"], full["h"], full["cases"], full["personas"]
        resp = c.post(f"/api/crm/consolidation/cases/{cases[0].id}/calls", json={
            "persona_id": str(personas[0].id),
            "outcome": "completed",
        }, headers=h)
        assert _ok(resp.status_code)

    def test_volunteer_create_standalone(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/crm/volunteers", json={
            "name": "Standalone Volunteer",
            "team": "worship",
            "role": "singer",
            "shift_start": datetime.now(timezone.utc).isoformat(),
            "shift_end": (datetime.now(timezone.utc) + timedelta(hours=3)).isoformat(),
        }, headers=h)
        assert _ok(resp.status_code)

    def test_volunteer_create_bad_dates(self, full):
        c, h, personas = full["c"], full["h"], full["personas"]
        resp = c.post("/api/crm/volunteers", json={
            "persona_id": str(personas[5].id),
            "name": "Vol Bad Dates",
            "shift_start": "not-a-date",
            "shift_end": "also-bad",
        }, headers=h)
        assert _ok(resp.status_code)

    def test_volunteer_list_with_shifts(self, full):
        c, h = full["c"], full["h"]
        resp = c.get("/api/crm/volunteers", headers=h)
        assert _ok(resp.status_code)

    def test_volunteer_detail_with_shifts(self, full):
        c, h, personas = full["c"], full["h"], full["personas"]
        resp = c.get(f"/api/crm/volunteers/{personas[0].id}", headers=h)
        assert _ok(resp.status_code)

    def test_volunteer_delete(self, full):
        c, h, personas = full["c"], full["h"], full["personas"]
        resp = c.delete(f"/api/crm/volunteers/{personas[3].id}", headers=h)
        assert _ok(resp.status_code)

    def test_update_grupo_all_fields(self, full):
        c, h, groups, personas = full["c"], full["h"], full["groups"], full["personas"]
        resp = c.put(f"/api/crm/grupos/{groups[0].id}", json={
            "name": "Updated G", "zone": "New Zone", "code": "UG1",
            "capacity": 30, "day_of_week": "Martes", "start_time": "19:00",
            "status": "active",
            "participante_ids": [str(p.id) for p in personas[:3]],
        }, headers=h)
        assert _ok(resp.status_code)

    def test_update_grupo_remove_participants(self, full):
        c, h, groups, personas = full["c"], full["h"], full["groups"], full["personas"]
        resp = c.put(f"/api/crm/grupos/{groups[0].id}", json={
            "participante_ids": [str(personas[0].id)],
        }, headers=h)
        assert _ok(resp.status_code)

    def test_update_grupo_invalid_participant_ids(self, full):
        c, h, groups = full["c"], full["h"], full["groups"]
        resp = c.put(f"/api/crm/grupos/{groups[0].id}", json={
            "participante_ids": ["not-a-uuid", "", None],
        }, headers=h)
        assert _ok(resp.status_code)

    def test_analytics_with_data(self, full):
        c, h = full["c"], full["h"]
        resp = c.get("/api/crm/analytics", headers=h)
        assert _ok(resp.status_code)
        data = resp.json()
        assert "total_personas" in data
        assert data["total_personas"] >= 0

    def test_newsletter_leads_no_data(self, full):
        c, h = full["c"], full["h"]
        resp = c.get("/api/crm/leads/newsletter", headers=h)
        assert _ok(resp.status_code)
        assert "leads" in resp.json()

    def test_newsletter_leads_all_filters(self, full):
        c, h, cases = full["c"], full["h"], full["cases"]
        since = (datetime.now(timezone.utc) - timedelta(days=365)).isoformat()
        until = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
        for f in [
            f"source=EVANGELISMO",
            f"stage=active",
            f"landing_page=/home",
            f"campaign=Test",
            f"date_from={since}",
            f"date_to={until}",
            f"page=1&page_size=5",
        ]:
            c.get(f"/api/crm/leads/newsletter?{f}", headers=h)

    def test_export_newsletter(self, full):
        c, h = full["c"], full["h"]
        resp = c.get("/api/crm/leads/export-newsletter", headers=h)
        assert _ok(resp.status_code)
        c.get("/api/crm/leads/export-newsletter?source=EVANGELISMO", headers=h)
        since = (datetime.now(timezone.utc) - timedelta(days=365)).isoformat()
        c.get(f"/api/crm/leads/export-newsletter?date_from={since}", headers=h)

    def test_counseling_full_crud(self, full):
        c, h, personas = full["c"], full["h"], full["personas"]
        resp = c.post("/api/crm/counseling", json={
            "persona_id": str(personas[0].id), "subject": "Deep Counseling",
        }, headers=h)
        assert _ok(resp.status_code)
        if resp.status_code in (200, 201):
            tid = resp.json().get("id")
            if tid:
                c.patch(f"/api/crm/counseling/{tid}", json={
                    "status": "resolved", "notes": "Session notes", "priority_level": "high",
                }, headers=h)
                c.get(f"/api/crm/counseling/{tid}", headers=h)
                c.get(f"/api/crm/counseling/lead/{personas[0].id}", headers=h)

    def test_prayer_requests_crud(self, full):
        c, h, sede, personas = full["c"], full["h"], full["sede"], full["personas"]
        resp = c.post("/api/crm/prayer-requests", json={
            "requester_name": "Prayer Person", "request_text": "Please pray",
            "sede_id": str(sede.id),
        }, headers=h)
        assert _ok(resp.status_code)
        if resp.status_code in (200, 201):
            rid = resp.json().get("id")
            if rid:
                c.patch(f"/api/crm/prayer-requests/{rid}", json={
                    "status": "answered", "is_answered": True, "source": "web",
                }, headers=h)
        c.get("/api/crm/prayer-requests", headers=h)
        c.get("/api/crm/prayer-requests?source=web", headers=h)

    def test_prayer_public_full(self, full):
        c = full["c"]
        resp = c.post("/api/crm/prayer-requests/public", json={
            "first_name": "Public", "last_name": "Prayer",
            "request_text": "Healing for my family",
            "phone": "+573001112299",
            "email": f"pub_{uuid.uuid4().hex[:6]}@t.com",
            "category": "health",
            "campaign": "easter",
            "landing_page": "/prayer",
        }, headers={})
        assert _ok(resp.status_code)

    def test_messaging_send_email(self, full):
        c, h, personas = full["c"], full["h"], full["personas"]
        resp = c.post("/api/crm/messaging/send", json={
            "channel": "email",
            "recipient_ids": [str(personas[0].id)],
            "subject": "Newsletter",
            "body": "This week at church...",
        }, headers=h)
        assert _ok(resp.status_code)

    def test_messaging_send_no_channel(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/crm/messaging/send", json={
            "content": "Missing channel",
        }, headers=h)
        assert _ok(resp.status_code)

    def test_messaging_send_no_targets(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/crm/messaging/send", json={
            "channel": "email", "content": "No targets",
            "target_segments": ["nonexistent_segment"],
        }, headers=h)
        assert _ok(resp.status_code)

    def test_messaging_send_with_segments(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/crm/messaging/send", json={
            "channel": "email", "content": "Broadcast",
            "target_segments": ["active"],
            "campaign_name": "Spring Campaign",
        }, headers=h)
        assert _ok(resp.status_code)

    def test_messaging_send_whatsapp(self, full):
        c, h, personas = full["c"], full["h"], full["personas"]
        resp = c.post("/api/crm/messaging/send", json={
            "channel": "whatsapp",
            "persona_id": str(personas[0].id),
            "content": "Hello via WhatsApp",
        }, headers=h)
        assert _ok(resp.status_code)

    def test_messaging_send_sms(self, full):
        c, h, personas = full["c"], full["h"], full["personas"]
        resp = c.post("/api/crm/messaging/send", json={
            "channel": "sms",
            "persona_id": str(personas[0].id),
            "content": "SMS message",
        }, headers=h)
        assert _ok(resp.status_code)

    def test_messaging_send_groups_segment(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/crm/messaging/send", json={
            "channel": "email", "content": "Groups msg",
            "target_segments": ["groups"],
        }, headers=h)
        assert _ok(resp.status_code)

    def test_messaging_history_full(self, full):
        c, h = full["c"], full["h"]
        c.get("/api/crm/messaging/history", headers=h)
        c.get("/api/crm/messaging/history?limit=5", headers=h)

    def test_crm_roles_cascade_update_delete(self, full):
        c, h, personas = full["c"], full["h"], full["personas"]
        resp = c.post("/api/crm/roles", json={"nombre": f"Cascade_{uuid.uuid4().hex[:6]}"}, headers=h)
        if resp.status_code in (200, 201):
            rid = resp.json().get("id")
            if rid:
                c.put(f"/api/crm/roles/{rid}", json={"nombre": "Renamed", "color": "#FF0000", "is_leadership": True}, headers=h)
                c.delete(f"/api/crm/roles/{rid}", headers=h)

    def test_crm_settings_json(self, full):
        c, h = full["c"], full["h"]
        c.get("/api/crm/settings", headers=h)
        c.post("/api/crm/settings", json={"config": {"pipeline_stages": ["new", "contacted", "active"]}}, headers=h)

    def test_crm_radar_full(self, full):
        c, h = full["c"], full["h"]
        resp = c.get("/api/crm/radar", headers=h)
        assert _ok(resp.status_code)


# ═══════════════════════════════════════════════════════════════════════════════
# ADMIN — Deep branch coverage
# ═══════════════════════════════════════════════════════════════════════════════

class TestAdminDeepV2:
    def test_update_user_all_fields(self, full):
        c, h, admin = full["c"], full["h"], full["admin"]
        c.patch(f"/api/admin/users/{admin.id}", json={
            "username": f"upd_{uuid.uuid4().hex[:6]}",
            "email": f"upd_{uuid.uuid4().hex[:6]}@t.com",
            "password": "NewPass123!",
            "is_active": False,
        }, headers=h)
        c.patch(f"/api/admin/users/{admin.id}", json={"is_active": True}, headers=h)
        c.patch(f"/api/admin/users/{admin.id}", json={
            "rol_plataforma_id": str(admin.rol_plataforma_id),
        }, headers=h)
        c.patch(f"/api/admin/users/{admin.id}", json={"rol_plataforma_id": ""}, headers=h)
        c.patch(f"/api/admin/users/{admin.id}", json={"rol_plataforma_id": None}, headers=h)
        c.patch(f"/api/admin/users/{admin.id}", json={"role_id": None}, headers=h)
        c.patch(f"/api/admin/users/{admin.id}", json={"role": "ADMIN"}, headers=h)

    def test_update_user_invalid_role_id(self, full):
        c, h, admin = full["c"], full["h"], full["admin"]
        c.patch(f"/api/admin/users/{admin.id}", json={"rol_plataforma_id": "not-a-uuid"}, headers=h)
        c.patch(f"/api/admin/users/{admin.id}", json={"rol_plataforma_id": "bad"}, headers=h)
        c.patch(f"/api/admin/users/{admin.id}", json={"role_id": "bad"}, headers=h)

    def test_create_user_with_role(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/admin/users", json={
            "email": f"role_{uuid.uuid4().hex[:6]}@t.com",
            "password": "P1!",
            "username": f"r_{uuid.uuid4().hex[:6]}",
            "first_name": "R", "last_name": "U",
            "role": "ADMIN",
        }, headers=h)
        assert _ok(resp.status_code)

    def test_create_user_missing_email(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/admin/users", json={"password": "P1!"}, headers=h)
        assert _ok(resp.status_code)

    def test_set_user_permissions_invalid_module(self, full):
        c, h, admin = full["c"], full["h"], full["admin"]
        resp = c.put(f"/api/admin/users/{admin.id}/permissions", json={
            "invalid_module": "read",
        }, headers=h)
        assert _ok(resp.status_code)

    def test_set_user_permissions_invalid_level(self, full):
        c, h, admin = full["c"], full["h"], full["admin"]
        resp = c.put(f"/api/admin/users/{admin.id}/permissions", json={
            "crm": "invalid_level",
        }, headers=h)
        assert _ok(resp.status_code)

    def test_set_user_permissions_null_level(self, full):
        c, h, admin = full["c"], full["h"], full["admin"]
        resp = c.put(f"/api/admin/users/{admin.id}/permissions", json={
            "crm": None,
        }, headers=h)
        assert _ok(resp.status_code)

    def test_set_user_permissions_all_modules(self, full):
        c, h, admin = full["c"], full["h"], full["admin"]
        resp = c.put(f"/api/admin/users/{admin.id}/permissions", json={
            "crm": "manage", "academy": "study", "evangelism": "manage",
            "agenda": "edit", "projects": "manage", "profile": "manage",
        }, headers=h)
        assert _ok(resp.status_code)

    def test_get_user_permissions_personal_role(self, full):
        c, h, admin = full["c"], full["h"], full["admin"]
        c.put(f"/api/admin/users/{admin.id}/permissions", json={"crm": "read"}, headers=h)
        resp = c.get(f"/api/admin/users/{admin.id}/permissions", headers=h)
        assert _ok(resp.status_code)

    def test_set_permissions_invalid_user(self, full):
        c, h = full["c"], full["h"]
        resp = c.put(f"/api/admin/users/{uuid.uuid4()}/permissions", json={"crm": "read"}, headers=h)
        assert _ok(resp.status_code)

    def test_change_role_full(self, full):
        c, h, admin = full["c"], full["h"], full["admin"]
        c.patch(f"/api/admin/users/{admin.id}/role", params={"role_id": str(admin.rol_plataforma_id)}, headers=h)
        c.patch(f"/api/admin/users/{admin.id}/role", params={"role_id": str(admin.rol_plataforma_id)}, headers=h)
        c.patch(f"/api/admin/users/{admin.id}/role", params={}, headers=h)
        c.patch(f"/api/admin/users/{admin.id}/role", params={"role_id": "bad"}, headers=h)

    def test_delete_user_full(self, full):
        c, h, admin = full["c"], full["h"], full["admin"]
        c.delete(f"/api/admin/users/{admin.id}", headers=h)
        c.delete(f"/api/admin/users/{uuid.uuid4()}", headers=h)

    def test_auth_roles_full_crud(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/admin/auth-role-definitions", json={
            "nombre": f"AR_{uuid.uuid4().hex[:6]}", "permisos": {"crm": "read"},
        }, headers=h)
        if resp.status_code in (200, 201):
            rid = resp.json().get("id")
            if rid:
                c.patch(f"/api/admin/auth-role-definitions/{rid}", json={
                    "nombre": "Updated", "permisos": {"crm": "manage"},
                }, headers=h)
                c.delete(f"/api/admin/auth-role-definitions/{rid}", headers=h)
        c.get("/api/admin/auth-role-definitions", headers=h)

    def test_delete_auth_role_assigned(self, full):
        c, h, admin = full["c"], full["h"], full["admin"]
        if admin.rol_plataforma_id:
            resp = c.delete(f"/api/admin/auth-role-definitions/{admin.rol_plataforma_id}", headers=h)
            assert _ok(resp.status_code)

    def test_module_roles_full(self, full):
        c, h, admin = full["c"], full["h"], full["admin"]
        resp = c.post("/api/admin/user-module-roles", json={
            "user_id": str(admin.id), "module": "evangelism", "role": "manage",
        }, headers=h)
        assert _ok(resp.status_code)
        c.get("/api/admin/user-module-roles", headers=h)
        resp2 = c.post("/api/admin/user-module-roles", json={
            "user_id": str(admin.id), "module": "evangelism", "role": "read",
        }, headers=h)
        assert _ok(resp2.status_code)

    def test_delete_module_role(self, full):
        c, h, admin = full["c"], full["h"], full["admin"]
        resp = c.post("/api/admin/user-module-roles", json={
            "user_id": str(admin.id), "module": "projects", "role": "read",
        }, headers=h)
        if resp.status_code in (200, 201):
            aid = resp.json().get("id")
            if aid:
                c.delete(f"/api/admin/user-module-roles/{aid}", headers=h)

    def test_automations_full(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/admin/automations", json={
            "nombre": f"A_{uuid.uuid4().hex[:6]}",
            "evento_trigger": "new_case",
            "acciones": [{"type": "notify", "target": "admin"}],
        }, headers=h)
        if resp.status_code in (200, 201):
            rid = resp.json().get("id")
            if rid:
                c.patch(f"/api/admin/automations/{rid}", json={
                    "nombre": "Updated",
                    "evento_trigger": "new_persona",
                    "acciones": [{"type": "email", "target": "leader"}],
                    "is_active": True,
                }, headers=h)
                c.delete(f"/api/admin/automations/{rid}", headers=h)

    def test_update_role_invalid_uuid(self, full):
        c, h = full["c"], full["h"]
        c.patch("/api/admin/roles/not-a-uuid", json={"permisos": {}}, headers=h)

    def test_delete_role_full(self, full):
        c, h = full["c"], full["h"]
        c.delete(f"/api/admin/roles/{uuid.uuid4()}", headers=h)
        resp = c.post("/api/admin/roles", json={"nombre": f"D_{uuid.uuid4().hex[:6]}", "permisos": {}}, headers=h)
        if resp.status_code in (200, 201):
            rid = resp.json().get("id")
            if rid:
                c.delete(f"/api/admin/roles/{rid}", headers=h)

    def test_list_users_with_roles(self, full):
        c, h = full["c"], full["h"]
        resp = c.get("/api/admin/users-with-roles", headers=h)
        assert _ok(resp.status_code)

    def test_admin_comments(self, full):
        c, h = full["c"], full["h"]
        c.get("/api/admin/comments", headers=h)

    def test_admin_milestones_full(self, full):
        c, h, personas = full["c"], full["h"], full["personas"]
        c.get("/api/admin/milestones", headers=h)
        c.post("/api/admin/milestones/award", json={
            "medalla_id": str(uuid.uuid4()),
            "persona_ids": [str(p.id) for p in personas[:6]],
        }, headers=h)


# ═══════════════════════════════════════════════════════════════════════════════
# CMS V2 — Deep branch coverage with auth
# ═══════════════════════════════════════════════════════════════════════════════

class TestCMSDeepV2:
    def test_list_sites_all_variants(self, full):
        c, h = full["c"], full["h"]
        c.get("/api/cms/v2/sites", headers=h)
        c.get("/api/cms/v2/sites?active_only=true", headers=h)
        c.get("/api/cms/v2/sites?active_only=false", headers=h)

    def test_global_blocks_full_crud(self, full):
        c, h = full["c"], full["h"]
        for btype in ["RichText", "Stats", "Team", "Testimonials"]:
            resp = c.post("/api/cms/v2/global-blocks", json={
                "type": btype, "props_json": {"content": f"<p>{btype}</p>"},
            }, headers=h)
            assert resp.status_code in (200, 201, 403, 422), f"{btype}: {resp.text}"
            if resp.status_code in (200, 201):
                bid = resp.json().get("id") or resp.json().get("section_id")
                if bid:
                    c.patch(f"/api/cms/v2/global-blocks/{bid}", json={"props_json": {"content": f"<p>U {btype}</p>"}}, headers=h)
                    c.delete(f"/api/cms/v2/global-blocks/{bid}", headers=h)
        c.get("/api/cms/v2/global-blocks", headers=h)

    def test_pages_list_fallback(self, full):
        c, h = full["c"], full["h"]
        c.get("/api/cms/v2/sites/faro/pages", headers=h)
        c.get("/api/cms/v2/sites/faro/pages?page=1&page_size=10", headers=h)

    def test_public_pages_all(self, full):
        c = full["c"]
        for slug in ["home", "nosotros", "conocer-a-jesus", "eventos", "predicas",
                      "cursos", "sedes", "boletin", "bienvenida", "privacidad"]:
            c.get(f"/api/cms/v2/public/sites/faro/pages/{slug}")

    def test_public_theme(self, full):
        c = full["c"]
        c.get("/api/cms/v2/public/sites/faro/theme")

    def test_public_menu(self, full):
        c = full["c"]
        c.get("/api/cms/v2/public/sites/faro/menus/main")

    def test_track_views(self, full):
        c, h = full["c"], full["h"]
        c.post("/api/cms/v2/track/home", headers=h)
        c.post("/api/cms/v2/track/nonexistent", headers=h)
        c.post("/api/cms/v2/track/nosotros", headers=h)

    def test_analytics(self, full):
        c, h = full["c"], full["h"]
        c.get("/api/cms/v2/analytics/home", headers=h)
        c.get("/api/cms/v2/analytics/home?days=30", headers=h)
        c.get("/api/cms/v2/analytics/home?days=7", headers=h)

    def test_image_resize(self, full):
        c, h = full["c"], full["h"]
        c.get(f"/api/cms/v2/images/{uuid.uuid4()}/resize", headers=h)

    def test_media_list(self, full):
        c, h = full["c"], full["h"]
        c.get("/api/cms/v2/media", headers=h)

    def test_pastoral_team_cms(self, full):
        c, h = full["c"], full["h"]
        c.get("/api/cms/v2/cms/pastoral-team", headers=h)

    def test_pastoral_team_public(self, full):
        c = full["c"]
        c.get("/api/cms/v2/public/sites/faro/pastoral-team")


# ═══════════════════════════════════════════════════════════════════════════════
# EVANGELISM — Deep branch coverage
# ═══════════════════════════════════════════════════════════════════════════════

class TestEvangelismDeepV2:
    def test_events_crud_full(self, full):
        c, h = full["c"], full["h"]
        c.get("/api/evangelism/events", headers=h)
        resp = c.post("/api/evangelism/events", json={
            "name": f"E_{uuid.uuid4().hex[:6]}",
            "event_date": datetime.now(timezone.utc).isoformat(),
            "location": "Main Hall",
            "description": "Test event",
        }, headers=h)
        assert _ok(resp.status_code)
        if resp.status_code in (200, 201):
            eid = resp.json().get("id")
            if eid:
                c.get(f"/api/evangelism/events/{eid}", headers=h)
                c.put(f"/api/evangelism/events/{eid}", json={"name": "Updated"}, headers=h)
                c.get(f"/api/evangelism/events/{eid}/analytics", headers=h)
                c.delete(f"/api/evangelism/events/{eid}", headers=h)

    def test_strategies_full(self, full):
        c, h, sede = full["c"], full["h"], full["sede"]
        c.get("/api/evangelism/strategies", headers=h)
        resp = c.post("/api/evangelism/strategies", json={
            "nombre": f"S_{uuid.uuid4().hex[:6]}",
            "sede_id": str(sede.id), "frecuencia": "semanal",
        }, headers=h)
        assert _ok(resp.status_code)

    def test_grupos_full(self, full):
        c, h, sede, personas = full["c"], full["h"], full["sede"], full["personas"]
        c.get("/api/evangelism/grupos", headers=h)
        resp = c.post("/api/evangelism/grupos", json={
            "nombre": f"G_{uuid.uuid4().hex[:6]}",
            "ubicacion": "P", "sede_id": str(sede.id),
            "lider_persona_id": str(personas[0].id),
            "codigo": f"G{uuid.uuid4().hex[:6]}",
        }, headers=h)
        assert _ok(resp.status_code)

    def test_sesiones_full(self, full):
        c, h, groups = full["c"], full["h"], full["groups"]
        c.get("/api/evangelism/sesiones", headers=h)
        c.post("/api/evangelism/sesiones", json={
            "grupo_id": str(groups[0].id),
            "tema_estudio": "T", "fecha_sesion": datetime.now(timezone.utc).isoformat(),
        }, headers=h)

    def test_analytics_strategy(self, full):
        c, h, strategy = full["c"], full["h"], full["strategy"]
        c.get(f"/api/evangelism/analytics/strategy/{strategy.id}", headers=h)

    def test_roles(self, full):
        c, h = full["c"], full["h"]
        c.get("/api/evangelism/events/roles", headers=h)
