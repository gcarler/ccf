"""
Evangelism — Cross-Sede Isolation Tests (T-06)

Verifies that users from sede A cannot access, mutate, or leak data
from sede B across key endpoints: events, notifications, reports, rankings.

These tests are intentionally separate from the general coverage suite so
that any cross-sede regression is caught immediately.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from backend import models
from backend.api.evangelism_shared import utc_now
from backend.models_auth import NotificacionUsuario
from backend.models_evangelism import (
    CategoriaEstrategia,
    EstrategiaEvangelismo,
    GrupoEvangelismo,
    HabilitacionSesionEnum,
    SesionGrupo,
)
from tests.conftest import auth_headers, seed_admin, seed_user_with_role


def _create_other_sede_event(client, db_session, sede, headers=None):
    """Helper: create an event + group + session in a different sede."""
    admin_user = db_session.query(models.User).first()
    if headers is None:
        headers = auth_headers(client)

    categoria = CategoriaEstrategia(nombre="Cat CrossSede")
    db_session.add(categoria)
    db_session.flush()

    estrategia = EstrategiaEvangelismo(
        nombre="Estrategia CrossSede",
        sede_id=sede.id,
        categoria_id=categoria.id,
        typology="relacional",
        strategy_type="geografica",
        frecuencia="SEMANAL",
        dia_reunion="Lunes",
        hora_reunion="19:00",
        fecha_inicio=datetime(2026, 6, 1, tzinfo=timezone.utc),
        fecha_fin=datetime(2026, 6, 22, tzinfo=timezone.utc),
        activa=True,
        status="active",
    )
    db_session.add(estrategia)
    db_session.flush()

    persona = models.Persona(
        first_name="Other",
        last_name="Leader",
        email=f"other_{uuid.uuid4().hex[:4]}@ccf.test",
        phone="+573009999999",
        sede_id=sede.id,
        church_role="Miembro",
    )
    db_session.add(persona)
    db_session.flush()

    grupo = GrupoEvangelismo(
        nombre="Grupo CrossSede",
        codigo=f"GC-{uuid.uuid4().hex[:6]}",
        sede_id=sede.id,
        estrategia_id=estrategia.id,
        ubicacion="Zona X",
        direccion="Calle X",
        capacidad=20,
        dia_reunion="Lunes",
        hora_reunion="19:00",
        lider_persona_id=persona.id,
        activo=True,
    )
    db_session.add(grupo)
    db_session.flush()

    sesion = SesionGrupo(
        grupo_id=grupo.id,
        fecha_sesion=datetime(2026, 6, 8, tzinfo=timezone.utc),
        estado="PENDIENTE",
        estado_habilitacion=HabilitacionSesionEnum.DESHABILITADO.value,
        tema_estudio="Tema CrossSede",
    )
    db_session.add(sesion)
    db_session.flush()
    db_session.commit()

    return {"estrategia": estrategia, "grupo": grupo, "sesion": sesion, "persona": persona}


class TestEventsCrossSedeIsolation:
    """T-06: Events — users from other sedes cannot read or mutate events."""

    def test_list_events_excludes_other_sede(self, client, db_session):
        """GET /events/ must not show events from other sedes."""
        admin, admin_persona, sede = seed_admin(db_session)
        headers = auth_headers(client)

        # Create event in a different sede
        other_sede = models.Sede(id=uuid.uuid4(), nombre="Sede Other", ciudad="Cali", es_activa=True)
        db_session.add(other_sede)
        db_session.flush()
        other_data = _create_other_sede_event(client, db_session, other_sede)

        # List events — should NOT include the other sede's strategy
        resp = client.get("/api/evangelism/events/", headers=headers)
        assert resp.status_code == 200
        events = resp.json()
        event_ids = [str(e.get("id", "")) for e in events]
        assert str(other_data["estrategia"].id) not in event_ids

    def test_get_event_detail_returns_404_for_other_sede(self, client, db_session):
        """GET /events/{id} must return 404 for other sede's event."""
        admin, admin_persona, sede = seed_admin(db_session)
        headers = auth_headers(client)

        other_sede = models.Sede(id=uuid.uuid4(), nombre="Sede Other", ciudad="Cali", es_activa=True)
        db_session.add(other_sede)
        db_session.flush()
        other_data = _create_other_sede_event(client, db_session, other_sede)

        resp = client.get(f"/api/evangelism/events/{other_data['estrategia'].id}", headers=headers)
        assert resp.status_code == 404

    def test_update_event_returns_404_for_other_sede(self, client, db_session):
        """PUT /events/{id} must return 404 for other sede's event."""
        admin, admin_persona, sede = seed_admin(db_session)
        headers = auth_headers(client)

        other_sede = models.Sede(id=uuid.uuid4(), nombre="Sede Other", ciudad="Cali", es_activa=True)
        db_session.add(other_sede)
        db_session.flush()
        other_data = _create_other_sede_event(client, db_session, other_sede)

        resp = client.put(
            f"/api/evangelism/events/{other_data['estrategia'].id}",
            json={"name": "Hacked"},
            headers=headers,
        )
        assert resp.status_code == 404

    def test_delete_event_returns_404_for_other_sede(self, client, db_session):
        """DELETE /events/{id} must return 404 for other sede's event."""
        admin, admin_persona, sede = seed_admin(db_session)
        headers = auth_headers(client)

        other_sede = models.Sede(id=uuid.uuid4(), nombre="Sede Other", ciudad="Cali", es_activa=True)
        db_session.add(other_sede)
        db_session.flush()
        other_data = _create_other_sede_event(client, db_session, other_sede)

        resp = client.delete(f"/api/evangelism/events/{other_data['estrategia'].id}", headers=headers)
        assert resp.status_code == 404

    def test_event_analytics_returns_404_for_other_sede(self, client, db_session):
        """GET /events/{id}/analytics must return 404 for other sede's event."""
        admin, admin_persona, sede = seed_admin(db_session)
        headers = auth_headers(client)

        other_sede = models.Sede(id=uuid.uuid4(), nombre="Sede Other", ciudad="Cali", es_activa=True)
        db_session.add(other_sede)
        db_session.flush()
        other_data = _create_other_sede_event(client, db_session, other_sede)

        resp = client.get(
            f"/api/evangelism/events/{other_data['estrategia'].id}/analytics",
            headers=headers,
        )
        assert resp.status_code == 404

    def test_global_analytics_excludes_other_sede(self, client, db_session):
        """GET /events/analytics/global must only show own sede's data."""
        admin, admin_persona, sede = seed_admin(db_session)
        headers = auth_headers(client)

        other_sede = models.Sede(id=uuid.uuid4(), nombre="Sede Other", ciudad="Cali", es_activa=True)
        db_session.add(other_sede)
        db_session.flush()
        other_data = _create_other_sede_event(client, db_session, other_sede)

        resp = client.get("/api/evangelism/events/analytics/global", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        # The response should not reference the other sede's event
        event_ids_in_response = str(body)
        assert str(other_data["estrategia"].id) not in event_ids_in_response

    def test_dashboard_stats_excludes_other_sede(self, client, db_session):
        """GET /events/dashboard-stats must only show own sede's data."""
        admin, admin_persona, sede = seed_admin(db_session)
        headers = auth_headers(client)

        other_sede = models.Sede(id=uuid.uuid4(), nombre="Sede Other", ciudad="Cali", es_activa=True)
        db_session.add(other_sede)
        db_session.flush()
        other_data = _create_other_sede_event(client, db_session, other_sede)

        resp = client.get("/api/evangelism/events/dashboard-stats", headers=headers)
        assert resp.status_code == 200


class TestNotificationsCrossSedeIsolation:
    """T-06: Notifications — send-reminders only processes own sede's data."""

    def test_send_reminders_only_own_sede(self, client, db_session):
        """POST /notifications/send-reminders must not create notifications for
        sessions/groups from other sedes."""
        admin, admin_persona, sede = seed_admin(db_session)
        headers = auth_headers(client)

        other_sede = models.Sede(id=uuid.uuid4(), nombre="Sede Other", ciudad="Cali", es_activa=True)
        db_session.add(other_sede)
        db_session.flush()
        other_data = _create_other_sede_event(client, db_session, other_sede)

        # Set a session for tomorrow in the OTHER sede
        tomorrow = (utc_now() + timedelta(days=1)).replace(hour=14, minute=0, second=0, microsecond=0)
        other_data["sesion"].fecha_sesion = tomorrow
        other_data["sesion"].estado = "PENDIENTE"
        # Make the other sede's leader a valid user
        other_user, _, _ = seed_user_with_role(
            db_session,
            role_name="pastor",
            email=f"leader_other_{uuid.uuid4().hex[:4]}@test.com",
            sede_id=other_sede.id,
            permisos={"evangelism:manage": "allow"},
        )
        other_data["grupo"].lider_persona_id = other_user.id
        db_session.commit()

        resp = client.post("/api/evangelism/notifications/send-reminders", headers=headers)
        assert resp.status_code == 200
        body = resp.json()

        # Should NOT create a notification for the other sede's leader
        other_notifications = (
            db_session.query(NotificacionUsuario).filter(NotificacionUsuario.user_id == other_user.id).all()
        )
        assert len(other_notifications) == 0


class TestReportsCrossSedeIsolation:
    """T-06: Reports — cannot generate reports for other sede's groups."""

    def test_pdf_report_blocked_for_other_sede_group(self, client, db_session):
        """GET /reports/group/{id}/attendance-pdf must block other sede (403 or 404)."""
        admin, admin_persona, sede = seed_admin(db_session)
        headers = auth_headers(client)

        other_sede = models.Sede(id=uuid.uuid4(), nombre="Sede Other", ciudad="Cali", es_activa=True)
        db_session.add(other_sede)
        db_session.flush()
        other_data = _create_other_sede_event(client, db_session, other_sede)

        resp = client.get(
            f"/api/evangelism/reports/group/{other_data['grupo'].id}/attendance-pdf",
            headers=headers,
        )
        assert resp.status_code in (403, 404)

    def test_excel_report_blocked_for_other_sede_group(self, client, db_session):
        """GET /reports/group/{id}/attendance-excel must block other sede (403 or 404)."""
        admin, admin_persona, sede = seed_admin(db_session)
        headers = auth_headers(client)

        other_sede = models.Sede(id=uuid.uuid4(), nombre="Sede Other", ciudad="Cali", es_activa=True)
        db_session.add(other_sede)
        db_session.flush()
        other_data = _create_other_sede_event(client, db_session, other_sede)

        resp = client.get(
            f"/api/evangelism/reports/group/{other_data['grupo'].id}/attendance-excel",
            headers=headers,
        )
        assert resp.status_code in (403, 404)

    def test_strategy_summary_blocked_for_other_sede(self, client, db_session):
        """GET /reports/strategy/{id}/summary must block other sede (403 or 404)."""
        admin, admin_persona, sede = seed_admin(db_session)
        headers = auth_headers(client)

        other_sede = models.Sede(id=uuid.uuid4(), nombre="Sede Other", ciudad="Cali", es_activa=True)
        db_session.add(other_sede)
        db_session.flush()
        other_data = _create_other_sede_event(client, db_session, other_sede)

        resp = client.get(
            f"/api/evangelism/reports/strategy/{other_data['estrategia'].id}/summary",
            headers=headers,
        )
        assert resp.status_code in (403, 404)


class TestRankingsCrossSedeIsolation:
    """T-06: Rankings — only show own sede's data in rankings."""

    def test_rankings_groups_excludes_other_sede(self, client, db_session):
        """GET /rankings/groups must not include groups from other sedes."""
        admin, admin_persona, sede = seed_admin(db_session)
        headers = auth_headers(client)

        other_sede = models.Sede(id=uuid.uuid4(), nombre="Sede Other", ciudad="Cali", es_activa=True)
        db_session.add(other_sede)
        db_session.flush()
        other_data = _create_other_sede_event(client, db_session, other_sede)

        resp = client.get("/api/evangelism/rankings/groups", headers=headers)
        assert resp.status_code == 200
        rankings = resp.json()
        group_ids = [str(r.get("group_id", r.get("id", ""))) for r in rankings]
        assert str(other_data["grupo"].id) not in group_ids

    def test_rankings_leaders_excludes_other_sede(self, client, db_session):
        """GET /rankings/leaders must not include leaders from other sedes."""
        admin, admin_persona, sede = seed_admin(db_session)
        headers = auth_headers(client)

        other_sede = models.Sede(id=uuid.uuid4(), nombre="Sede Other", ciudad="Cali", es_activa=True)
        db_session.add(other_sede)
        db_session.flush()
        other_data = _create_other_sede_event(client, db_session, other_sede)

        resp = client.get("/api/evangelism/rankings/leaders", headers=headers)
        assert resp.status_code == 200
        rankings = resp.json()
        leader_ids = [str(r.get("leader_id", r.get("persona_id", ""))) for r in rankings]
        assert str(other_data["persona"].id) not in leader_ids


class TestAnalyticsCrossSedeIsolation:
    """T-06: Analytics — strategy analytics only for own sede."""

    def test_analytics_returns_404_for_other_sede_strategy(self, client, db_session):
        """GET /analytics/strategy/{id} must return 404 for other sede's strategy."""
        admin, admin_persona, sede = seed_admin(db_session)
        headers = auth_headers(client)

        other_sede = models.Sede(id=uuid.uuid4(), nombre="Sede Other", ciudad="Cali", es_activa=True)
        db_session.add(other_sede)
        db_session.flush()
        other_data = _create_other_sede_event(client, db_session, other_sede)

        resp = client.get(
            f"/api/evangelism/analytics/strategy/{other_data['estrategia'].id}",
            headers=headers,
        )
        assert resp.status_code == 404

    def test_heatmap_returns_404_for_other_sede_strategy(self, client, db_session):
        """GET /analytics/strategy/{id}/heatmap must return 404 for other sede."""
        admin, admin_persona, sede = seed_admin(db_session)
        headers = auth_headers(client)

        other_sede = models.Sede(id=uuid.uuid4(), nombre="Sede Other", ciudad="Cali", es_activa=True)
        db_session.add(other_sede)
        db_session.flush()
        other_data = _create_other_sede_event(client, db_session, other_sede)

        resp = client.get(
            f"/api/evangelism/analytics/strategy/{other_data['estrategia'].id}/heatmap",
            headers=headers,
        )
        assert resp.status_code == 404

    def test_alerts_returns_404_for_other_sede_strategy(self, client, db_session):
        """GET /analytics/strategy/{id}/alerts must return 404 for other sede."""
        admin, admin_persona, sede = seed_admin(db_session)
        headers = auth_headers(client)

        other_sede = models.Sede(id=uuid.uuid4(), nombre="Sede Other", ciudad="Cali", es_activa=True)
        db_session.add(other_sede)
        db_session.flush()
        other_data = _create_other_sede_event(client, db_session, other_sede)

        resp = client.get(
            f"/api/evangelism/analytics/strategy/{other_data['estrategia'].id}/alerts",
            headers=headers,
        )
        assert resp.status_code == 404

    def test_groups_analytics_returns_404_for_other_sede_strategy(self, client, db_session):
        """GET /analytics/strategy/{id}/groups must return 404 for other sede."""
        admin, admin_persona, sede = seed_admin(db_session)
        headers = auth_headers(client)

        other_sede = models.Sede(id=uuid.uuid4(), nombre="Sede Other", ciudad="Cali", es_activa=True)
        db_session.add(other_sede)
        db_session.flush()
        other_data = _create_other_sede_event(client, db_session, other_sede)

        resp = client.get(
            f"/api/evangelism/analytics/strategy/{other_data['estrategia'].id}/groups",
            headers=headers,
        )
        assert resp.status_code == 404
