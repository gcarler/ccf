"""
Targeted tests for uncovered branches in evangelism modules.

Covers edge cases in main_estrategias, main_utils, events_main,
events_participantes, grupos_main, and evangelism_shared.
"""
import uuid
from datetime import datetime, timezone, timedelta

import pytest

from backend import models
from backend.api.evangelism_main.main_utils import (
    _channel_label,
    _persona_matches_segment,
    _resolve_campaign_personas,
    _serialize_message_group,
    _serialize_crm_task,
)
from backend.api.evangelism_shared import (
    _persona_matches_segment as _sh_persona_matches_segment,
    _resolve_campaign_personas as _sh_resolve_campaign_personas,
    _serialize_message_group as _sh_serialize_message_group,
    _serialize_crm_task as _sh_serialize_crm_task,
    persona_payload,
    _check_absence_trigger,
    _check_first_time_lead_trigger,
    resolve_target_role_ids,
    get_expected_personas_for_event,
    _sessions_grupo_live_column_names,
    expected_group_rows,
)
from tests.conftest import seed_admin as _seed_admin, auth_headers as _auth_headers


@pytest.fixture
def full(client, db_session):
    admin, persona, sede = _seed_admin(db_session)
    headers = _auth_headers(client, email=admin.email, password="testpass123")
    return {
        "c": client, "h": headers, "db": db_session,
        "admin": admin, "persona": persona, "sede": sede,
    }


# ================================================================
# main_utils.py supplemental
# ================================================================

class TestMainUtilsSupplemental:

    def test_channel_label_email(self):
        assert _channel_label("email") == "Email"

    def test_channel_label_whatsapp(self):
        assert _channel_label("whatsapp") == "WhatsApp"

    def test_channel_label_sms_fallback(self):
        assert _channel_label("telegram") == "SMS"
        assert _channel_label(None) == "SMS"
        assert _channel_label("") == "SMS"

    def test_persona_matches_segment_active(self, full):
        p = full["persona"]
        p.church_role = "miembro"
        full["db"].flush()
        assert _persona_matches_segment(p, "active", set()) is True

    def test_persona_matches_segment_staff(self, full):
        p = full["persona"]
        p.church_role = "pastor"
        full["db"].flush()
        assert _persona_matches_segment(p, "staff", set()) is True

    def test_persona_matches_segment_new(self, full):
        p = full["persona"]
        p.estado_vital = "nuevo"
        full["db"].flush()
        assert _persona_matches_segment(p, "new", set()) is True

    def test_persona_matches_segment_low(self, full):
        p = full["persona"]
        p.estado_vital = "creyente"
        full["db"].flush()
        assert _persona_matches_segment(p, "low", set()) is True

    def test_persona_matches_segment_groups(self, full):
        p = full["persona"]
        p.family_id = uuid.uuid4()
        full["db"].flush()
        assert _persona_matches_segment(p, "groups", set()) is True

    def test_persona_matches_segment_vip(self, full):
        p = full["persona"]
        assert _persona_matches_segment(p, "vip", {str(p.id)}) is True

    def test_persona_matches_segment_unknown(self, full):
        p = full["persona"]
        assert _persona_matches_segment(p, "unknown", set()) is False

    def test_resolve_campaign_personas_empty_segments(self, full):
        result = _resolve_campaign_personas(full["db"], [])
        assert result == []

    def test_resolve_campaign_personas_with_sede(self, full):
        from backend.models_crm import Persona
        p = Persona(id=uuid.uuid4(), first_name="Activo", church_role_effective="miembro",
                    sede_id=full["sede"].id)
        full["db"].add(p)
        full["db"].flush()
        result = _resolve_campaign_personas(full["db"], ["active"], sede_id=str(full["sede"].id))
        assert len(result) >= 1

    def test_resolve_campaign_personas_with_sede(self, full):
        p = full["persona"]
        p.church_role = "miembro"
        full["db"].flush()
        result = _resolve_campaign_personas(full["db"], ["active"], sede_id=str(full["sede"].id))
        assert len(result) >= 1

    def test_serialize_message_group_single(self, full):
        log = models.CommunicationLog(
            id=uuid.uuid4(), persona_id=full["persona"].id,
            channel="whatsapp", outcome="sent_real",
            content="Hola", campaign_name="Campaña Test",
        )
        full["db"].add(log)
        full["db"].flush()
        result = _serialize_message_group([log])
        assert result["channel"] == "whatsapp"
        assert result["status"] == "sent_real"
        assert result["campaign_name"] == "Campaña Test"

    def test_serialize_message_group_failed(self, full):
        logs = [
            models.CommunicationLog(id=uuid.uuid4(), persona_id=full["persona"].id,
                                    channel="sms", outcome="failed", content="Fail"),
            models.CommunicationLog(id=uuid.uuid4(), persona_id=full["persona"].id,
                                    channel="sms", outcome="failed", content="Fail2"),
        ]
        for log in logs:
            full["db"].add(log)
        full["db"].flush()
        result = _serialize_message_group(logs)
        assert result["status"] == "failed"

    def test_serialize_message_group_partial(self, full):
        logs = [
            models.CommunicationLog(id=uuid.uuid4(), persona_id=full["persona"].id,
                                    channel="sms", outcome="sent_real", content="Ok"),
            models.CommunicationLog(id=uuid.uuid4(), persona_id=full["persona"].id,
                                    channel="sms", outcome="failed", content="Fail"),
        ]
        for log in logs:
            full["db"].add(log)
        full["db"].flush()
        result = _serialize_message_group(logs)
        assert result["status"] == "partial"

    def test_serialize_crm_task_with_persona(self, full):
        from backend.models_crm_pipeline import TareaCRM
        task = TareaCRM(id=uuid.uuid4(), titulo="Test Task", estado="pendiente",
                        prioridad="alta", categoria="seguimiento",
                        persona_id=full["persona"].id)
        full["db"].add(task)
        full["db"].flush()
        result = _serialize_crm_task(task)
        assert result["title"] == "Test Task"
        assert result["persona_id"] == task.persona_id

    def test_serialize_crm_task_with_assignee(self, full):
        from backend.models_crm_pipeline import TareaCRM
        task = TareaCRM(id=uuid.uuid4(), titulo="Assigned", estado="en_progreso",
                        prioridad="media", categoria="llamada")
        full["db"].add(task)
        full["db"].flush()
        result = _serialize_crm_task(task, contact_name="Juan", assignee_name="Admin")
        assert result["persona_name"] == "Juan"
        assert result["assigned_to"] == "Admin"


# ================================================================
# evangelism_shared.py supplemental
# ================================================================

class TestEvangelismSharedSupplemental:

    def test_sessions_grupo_live_column_names_none_bind(self, full):
        result = _sessions_grupo_live_column_names(full["db"])
        assert isinstance(result, set)

    def test_expected_group_rows_with_extra_leaders(self, full):
        from backend.models_evangelism import GrupoEvangelismo, ParticipanteGrupo
        p1 = full["persona"]
        g = GrupoEvangelismo(id=uuid.uuid4(), nombre="G", sede_id=full["sede"].id,
                             lider_persona_id=p1.id)
        full["db"].add(g)
        full["db"].flush()
        pg = ParticipanteGrupo(grupo_id=g.id, persona_id=p1.id, activo=True, rol_base="miembro")
        full["db"].add(pg)
        full["db"].flush()
        rows = expected_group_rows(full["db"], g.id)
        assert len(rows) >= 1

    def test_resolve_target_role_ids_none(self):
        from backend.api.evangelism_shared import resolve_target_role_ids
        event = type("Event", (), {"target_role_ids": None, "target_role_id": None})()
        assert resolve_target_role_ids(event) == []

    def test_resolve_target_role_ids_single(self):
        rid = uuid.uuid4()
        event = type("Event", (), {"target_role_ids": None, "target_role_id": rid})()
        result = resolve_target_role_ids(event)
        assert len(result) == 1
        assert str(result[0]) == str(rid)

    def test_get_expected_personas_manual_empty(self, full):
        event = type("Event", (), {
            "target_audience": "MANUAL",
            "target_persona_ids": ["not-a-valid-uuid"],
            "sede_id": full["sede"].id,
        })()
        result = get_expected_personas_for_event(full["db"], event)
        assert result == []

    def test_get_expected_personas_manual_valid(self, full):
        event = type("Event", (), {
            "target_audience": "MANUAL",
            "target_persona_ids": [str(full["persona"].id)],
            "sede_id": full["sede"].id,
        })()
        result = get_expected_personas_for_event(full["db"], event)
        assert len(result) >= 1

    def test_get_expected_personas_fallback(self, full):
        event = type("Event", (), {
            "target_audience": "ALL",
            "target_role_ids": None,
            "target_role_id": None,
            "sede_id": full["sede"].id,
        })()
        result = get_expected_personas_for_event(full["db"], event)
        assert len(result) >= 1

    def test_get_expected_personas_role_none(self, full):
        event = type("Event", (), {
            "target_audience": "ROLE",
            "target_role_ids": None,
            "target_role_id": None,
            "sede_id": full["sede"].id,
        })()
        result = get_expected_personas_for_event(full["db"], event)
        assert result == []

    def test_persona_payload_defaults(self, full):
        result = persona_payload(full["persona"], attended=True)
        assert result["attended"] is True
        assert result["es_primera_vez"] is False

    def test_persona_payload_full(self, full):
        now = datetime.now(timezone.utc)
        result = persona_payload(full["persona"], attended=False,
                                 scanned_at=now, estado="FALTO")
        assert result["attended"] is False
        assert result["estado"] == "FALTO"
        assert result["scanned_at"] == now.isoformat()


# ================================================================
# events_main.py supplemental
# ================================================================

class TestEventsMainSupplemental:

    def test_create_event_role_duplicate_name(self, full):
        c, h = full["c"], full["h"]
        payload = {"name": "TestRoleSupp", "color": "#000", "is_leadership": False}
        resp = c.post("/api/evangelism/events/roles", headers=h, json=payload)
        assert resp.status_code == 200
        resp2 = c.post("/api/evangelism/events/roles", headers=h, json=payload)
        assert resp2.status_code == 400

    def test_update_role_duplicate_name(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/evangelism/events/roles", headers=h,
                      json={"name": "RoleA", "color": "#111", "is_leadership": False})
        assert resp.status_code == 200
        rid_a = resp.json()["id"]
        resp = c.post("/api/evangelism/events/roles", headers=h,
                      json={"name": "RoleB", "color": "#222", "is_leadership": False})
        assert resp.status_code == 200
        rid_b = resp.json()["id"]
        resp = c.put(f"/api/evangelism/events/roles/{rid_b}", headers=h,
                     json={"name": "RoleA"})
        assert resp.status_code == 400

    def test_delete_role_system_locked(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/evangelism/events/roles", headers=h,
                      json={"name": "Lockable", "color": "#333", "is_leadership": False})
        assert resp.status_code == 200
        rid = resp.json()["id"]
        from backend import models as m
        role = full["db"].query(m.RoleDefinition).filter(m.RoleDefinition.id == rid).first()
        if role:
            role.is_system_locked = True
            full["db"].commit()
        resp = c.delete(f"/api/evangelism/events/roles/{rid}?fallback_id={uuid.uuid4()}", headers=h)
        assert resp.status_code == 400

    def test_delete_role_same_id(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/evangelism/events/roles", headers=h,
                      json={"name": "SelfDel", "color": "#444", "is_leadership": False})
        assert resp.status_code == 200
        rid = resp.json()["id"]
        resp = c.delete(f"/api/evangelism/events/roles/{rid}?fallback_id={rid}", headers=h)
        assert resp.status_code == 400

    def test_events_global_analytics_week(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/evangelism/events/", headers=h, json={
            "name": "GA Week", "event_date": (datetime.now(timezone.utc) + timedelta(days=10)).date().isoformat(),
        })
        assert resp.status_code in (200, 201)
        resp = c.get("/api/evangelism/events/analytics/global?period=WEEK&event_type=ALL", headers=h)
        assert resp.status_code == 200

    def test_events_dashboard_stats_not_empty(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/evangelism/events/", headers=h, json={
            "name": "Dash Test",
            "event_date": (datetime.now(timezone.utc) + timedelta(days=5)).date().isoformat(),
        })
        assert resp.status_code in (200, 201)
        eid = resp.json()["id"]
        full["db"].add(models.EventAttendance(
            event_id=eid, persona_id=full["persona"].id, attended=True,
            session_date=datetime.now(timezone.utc).date(),
        ))
        full["db"].commit()
        resp = c.get("/api/evangelism/events/dashboard-stats", headers=h)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_event_analytics_single_event(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/evangelism/events/", headers=h, json={
            "name": "Analytic Evt",
            "event_date": (datetime.now(timezone.utc) + timedelta(days=3)).date().isoformat(),
        })
        assert resp.status_code in (200, 201)
        eid = resp.json()["id"]
        resp = c.get(f"/api/evangelism/events/{eid}/analytics", headers=h)
        assert resp.status_code == 200

    def test_persona_attendance_history(self, full):
        c, h = full["c"], full["h"]
        pid = full["persona"].id
        resp = c.get(f"/api/evangelism/personas/{pid}/attendance-history", headers=h)
        assert resp.status_code == 200

    def test_persona_attendance_history_404(self, full):
        c, h = full["c"], full["h"]
        resp = c.get(f"/api/evangelism/personas/{uuid.uuid4()}/attendance-history", headers=h)
        assert resp.status_code == 404


# ================================================================
# events_participantes.py supplemental
# ================================================================

class TestEventsParticipantesSupplemental:

    def test_bulk_attendance_invalid_persona_ids(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/evangelism/events/", headers=h, json={
            "name": "Bulk Bad",
            "event_date": (datetime.now(timezone.utc) + timedelta(days=1)).date().isoformat(),
        })
        assert resp.status_code in (200, 201)
        eid = resp.json()["id"]
        resp = c.post("/api/evangelism/attendance/bulk", headers=h, json={
            "event_id": eid,
            "persona_ids": ["not-a-uuid", 12345],
            "attendance_date": datetime.now(timezone.utc).date().isoformat(),
        })
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["invalid_persona_ids"]) >= 1

    def test_bulk_attendance_no_event_id(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/evangelism/attendance/bulk", headers=h, json={
            "persona_ids": [],
            "attendance_date": datetime.now(timezone.utc).date().isoformat(),
        })
        assert resp.status_code == 400

    def test_bulk_attendance_cancelled_event(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/evangelism/events/", headers=h, json={
            "name": "Cancelled Evt",
            "event_date": (datetime.now(timezone.utc) + timedelta(days=1)).date().isoformat(),
        })
        assert resp.status_code in (200, 201)
        eid = resp.json()["id"]
        event = full["db"].query(models.CrmEvent).filter(models.CrmEvent.id == eid).first()
        event.status = "CANCELLED"
        full["db"].commit()
        resp = c.post("/api/evangelism/attendance/bulk", headers=h, json={
            "event_id": eid,
            "persona_ids": [str(full["persona"].id)],
            "attendance_date": datetime.now(timezone.utc).date().isoformat(),
        })
        assert resp.status_code == 409


# ================================================================
# grupos_main.py supplemental
# ================================================================

class TestGruposMainSupplemental:

    def test_list_grupos_filter_strategy(self, full):
        from backend.models_evangelism import EstrategiaEvangelismo, CategoriaEstrategia
        cat = CategoriaEstrategia(id=uuid.uuid4(), nombre="CatFilter")
        full["db"].add(cat)
        full["db"].flush()
        s = EstrategiaEvangelismo(id=uuid.uuid4(), nombre="Filtered", sede_id=full["sede"].id,
                                  categoria_id=cat.id)
        full["db"].add(s)
        full["db"].flush()
        c, h = full["c"], full["h"]
        resp = c.get(f"/api/evangelism/groups?evangelism_strategy_id={s.id}", headers=h)
        assert resp.status_code == 200

    def test_create_grupo_with_all_fields(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/evangelism/groups", headers=h, json={
            "name": "FullGroup",
            "leader_id": str(full["persona"].id),
            "capacity": 15,
        })
        assert resp.status_code in (200, 201), resp.text

    def test_update_grupo_non_admin_restricted(self, full):
        from backend.models_evangelism import GrupoEvangelismo
        g = GrupoEvangelismo(id=uuid.uuid4(), nombre="Restricted", sede_id=full["sede"].id,
                             lider_persona_id=full["persona"].id)
        full["db"].add(g)
        full["db"].commit()
        c, h = full["c"], full["h"]
        resp = c.put(f"/api/evangelism/groups/{g.id}", headers=h, json={"name": "Changed"})
        assert resp.status_code in (200, 403), resp.text

    def test_campaign_season_update_404(self, full):
        c, h = full["c"], full["h"]
        resp = c.patch(f"/api/evangelism/groups/seasons/{uuid.uuid4()}", headers=h,
                       json={"name": "Ghost"})
        assert resp.status_code == 404

    def test_groups_analytics_with_season(self, full):
        from backend.api.evangelism_grupos.grupos_main import get_groups_analytics
        c, h = full["c"], full["h"]
        resp = c.get("/api/evangelism/groups/analytics", headers=h)
        assert resp.status_code == 200

    def test_strategy_metrics_no_houses(self, full):
        c, h = full["c"], full["h"]
        resp = c.get(f"/api/evangelism/strategies/{uuid.uuid4()}/metrics", headers=h)
        assert resp.status_code == 200
        data = resp.json()
        assert data["summary"]["total_groups"] == 0

    def test_get_macro_despliegue_no_active_season(self, full):
        c, h = full["c"], full["h"]
        resp = c.get("/api/evangelism/macro-despliegue", headers=h)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_houses"] == 0

    def test_create_season_end_before_start(self, full):
        c, h = full["c"], full["h"]
        resp = c.post("/api/evangelism/groups/seasons", headers=h, json={
            "name": "Bad Dates",
            "start_date": "2026-12-01",
            "end_date": "2026-01-01",
        })
        assert resp.status_code == 400


# ================================================================
# main_estrategias.py supplemental
# ================================================================

class TestEstrategiasSupplemental:

    def test_update_strategy_not_found(self, full):
        c, h = full["c"], full["h"]
        resp = c.put(f"/api/evangelism/strategies/{uuid.uuid4()}", headers=h, json={"name": "Ghost"})
        assert resp.status_code == 404

    def test_delete_strategy(self, full):
        from backend.models_evangelism import EstrategiaEvangelismo, CategoriaEstrategia
        cat = CategoriaEstrategia(id=uuid.uuid4(), nombre="CatDel")
        full["db"].add(cat)
        full["db"].flush()
        s = EstrategiaEvangelismo(id=uuid.uuid4(), nombre="ToDelete", sede_id=full["sede"].id,
                                  categoria_id=cat.id)
        full["db"].add(s)
        full["db"].commit()
        c, h = full["c"], full["h"]
        resp = c.delete(f"/api/evangelism/strategies/{s.id}", headers=h)
        assert resp.status_code == 204

    def test_delete_strategy_404(self, full):
        c, h = full["c"], full["h"]
        resp = c.delete(f"/api/evangelism/strategies/{uuid.uuid4()}", headers=h)
        assert resp.status_code == 404

    def test_generate_sessions_no_frecuencia(self, full):
        from backend.models_evangelism import EstrategiaEvangelismo, CategoriaEstrategia
        cat = CategoriaEstrategia(id=uuid.uuid4(), nombre="CatNoFreq")
        full["db"].add(cat)
        full["db"].flush()
        s = EstrategiaEvangelismo(id=uuid.uuid4(), nombre="NoFreq", sede_id=full["sede"].id,
                                  categoria_id=cat.id)
        full["db"].add(s)
        full["db"].commit()
        c, h = full["c"], full["h"]
        resp = c.post(f"/api/evangelism/strategies/{s.id}/generate-sessions", headers=h)
        assert resp.status_code == 400

    def test_generate_sessions_strategy_not_found(self, full):
        c, h = full["c"], full["h"]
        resp = c.post(f"/api/evangelism/strategies/{uuid.uuid4()}/generate-sessions", headers=h)
        assert resp.status_code == 404

    def test_list_strategies_cross_sede_returns_empty(self, full):
        c, h = full["c"], full["h"]
        other_sede = uuid.uuid4()
        resp = c.get(f"/api/evangelism/strategies?sede_id={other_sede}", headers=h)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_strategies_filter_activa(self, full):
        from backend.models_evangelism import EstrategiaEvangelismo, CategoriaEstrategia
        cat = CategoriaEstrategia(id=uuid.uuid4(), nombre="CatFilterActiva")
        full["db"].add(cat)
        full["db"].flush()
        s = EstrategiaEvangelismo(id=uuid.uuid4(), nombre="FilterActiva", sede_id=full["sede"].id,
                                  categoria_id=cat.id, activa=True)
        full["db"].add(s)
        full["db"].commit()
        c, h = full["c"], full["h"]
        resp = c.get("/api/evangelism/strategies?activa=true", headers=h)
        assert resp.status_code == 200

    def test_hydrate_strategy_synonyms_recurrence(self):
        from backend.api.evangelism_main.main_estrategias import _hydrate_strategy_synonyms
        from backend.schemas.crm.base import EvangelismStrategy
        src = type("S", (), {"frecuencia": "SEMANAL", "dia_reunion": None,
                             "hora_reunion": None, "fecha_inicio": None,
                             "fecha_fin": None})()
        obj = EvangelismStrategy.model_validate({
            "id": uuid.uuid4(), "name": "Test", "typology": "formativo",
            "start_date": "2026-01-01", "end_date": "2026-12-31",
        })
        result = _hydrate_strategy_synonyms(obj, src)
        assert result.recurrence == "SEMANAL"

    def test_hydrate_strategy_synonyms_all(self):
        from backend.api.evangelism_main.main_estrategias import _hydrate_strategy_synonyms
        from backend.schemas.crm.base import EvangelismStrategy
        src = type("S", (), {
            "frecuencia": "SEMANAL", "dia_reunion": "lunes",
            "hora_reunion": "10:00", "fecha_inicio": datetime.now(timezone.utc),
            "fecha_fin": datetime.now(timezone.utc) + timedelta(days=30),
        })()
        obj = EvangelismStrategy.model_validate({
            "id": uuid.uuid4(), "name": "Test", "typology": "formativo",
            "start_date": "2026-01-01", "end_date": "2026-12-31",
        })
        result = _hydrate_strategy_synonyms(obj, src)
        assert result.day_of_week == "lunes"
        assert result.start_time == "10:00"
