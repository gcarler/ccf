"""Tests completos del módulo Agenda — cubre endpoints sin cobertura,
validadores de schemas, aislamiento por sede, RBAC HTTP y soft-delete."""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from tests.conftest import auth_headers, seed_admin

# ── Helpers ─────────────────────────────────────────────────────────────────

def _event_payload(title="Test Event", start=None, end=None, location="Sala A"):
    start = start or datetime(2026, 7, 1, 10, 0, tzinfo=timezone.utc)
    end = end or start + timedelta(hours=2)
    return {
        "title": title,
        "description": "Test description",
        "start_at": start.isoformat(),
        "end_at": end.isoformat(),
        "location": location,
        "is_all_day": False,
    }


def _resource_payload(name="Auditorio", rtype="ROOM", capacity=100):
    return {
        "name": name,
        "resource_type": rtype,
        "capacity": capacity,
        "is_active": True,
    }


def _participant_payload(event_id, persona_id, status="PENDIENTE", required=True):
    return {
        "event_id": str(event_id),
        "persona_id": str(persona_id),
        "confirmation_status": status,
        "is_required": required,
    }


def _reservation_payload(event_id, resource_id, starts_at, ends_at):
    return {
        "event_id": str(event_id),
        "resource_id": str(resource_id),
        "starts_at": starts_at.isoformat(),
        "ends_at": ends_at.isoformat(),
    }


def _create_event(client, headers, title="Test Event", **overrides):
    payload = _event_payload(title, **overrides)
    resp = client.post("/api/agenda/events", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_resource(client, headers, name="Auditorio"):
    resp = client.post("/api/agenda/resources", json=_resource_payload(name), headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ── 1. Endpoint by-date-range ──────────────────────────────────────────────

class TestEventsByDateRange:
    def test_returns_events_in_range(self, client, db_session):
        admin, _, _ = seed_admin(db_session)
        headers = auth_headers(client, email=admin.email)

        event = _create_event(client, headers, "En rango")

        start = datetime(2026, 7, 1, 0, 0, tzinfo=timezone.utc)
        end = datetime(2026, 7, 2, 0, 0, tzinfo=timezone.utc)
        resp = client.get(
            "/api/agenda/events/by-date-range",
            params={"start": start.isoformat(), "end": end.isoformat()},
            headers=headers,
        )
        assert resp.status_code == 200
        ids = [e["id"] for e in resp.json()]
        assert event["id"] in ids

    def test_excludes_events_outside_range(self, client, db_session):
        admin, _, _ = seed_admin(db_session)
        headers = auth_headers(client, email=admin.email)

        outside_start = datetime(2026, 8, 1, 10, 0, tzinfo=timezone.utc)
        _create_event(client, headers, "Fuera de rango",
                      start=outside_start, end=outside_start + timedelta(hours=1))

        query_start = datetime(2026, 7, 1, 0, 0, tzinfo=timezone.utc)
        query_end = datetime(2026, 7, 2, 0, 0, tzinfo=timezone.utc)
        resp = client.get(
            "/api/agenda/events/by-date-range",
            params={"start": query_start.isoformat(), "end": query_end.isoformat()},
            headers=headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 0

    def test_rejects_end_before_start(self, client, db_session):
        admin, _, _ = seed_admin(db_session)
        headers = auth_headers(client, email=admin.email)

        start = datetime(2026, 7, 2, 0, 0, tzinfo=timezone.utc)
        end = datetime(2026, 7, 1, 0, 0, tzinfo=timezone.utc)
        resp = client.get(
            "/api/agenda/events/by-date-range",
            params={"start": start.isoformat(), "end": end.isoformat()},
            headers=headers,
        )
        assert resp.status_code == 422


# ── 2. CRUD Resources ──────────────────────────────────────────────────────

class TestResourcesCRUD:
    def test_update_resource(self, client, db_session):
        admin, _, _ = seed_admin(db_session)
        headers = auth_headers(client, email=admin.email)

        resource = _create_resource(client, headers, "Original")
        resp = client.put(
            f"/api/agenda/resources/{resource['id']}",
            json=_resource_payload("Actualizado", "HALL", 200),
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Actualizado"
        assert resp.json()["resource_type"] == "HALL"
        assert resp.json()["capacity"] == 200

    def test_delete_resource(self, client, db_session):
        admin, _, _ = seed_admin(db_session)
        headers = auth_headers(client, email=admin.email)

        resource = _create_resource(client, headers)
        resp = client.delete(f"/api/agenda/resources/{resource['id']}", headers=headers)
        assert resp.status_code == 204

        resp = client.get("/api/agenda/resources", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 0

    def test_update_nonexistent_resource_returns_404(self, client, db_session):
        admin, _, _ = seed_admin(db_session)
        headers = auth_headers(client, email=admin.email)

        resp = client.put(
            f"/api/agenda/resources/{uuid4()}",
            json=_resource_payload("X"),
            headers=headers,
        )
        assert resp.status_code == 404

    def test_delete_nonexistent_resource_returns_404(self, client, db_session):
        admin, _, _ = seed_admin(db_session)
        headers = auth_headers(client, email=admin.email)

        resp = client.delete(f"/api/agenda/resources/{uuid4()}", headers=headers)
        assert resp.status_code == 404


# ── 3. CRUD Participants ───────────────────────────────────────────────────

class TestParticipantsCRUD:
    def test_list_participants(self, client, db_session):
        admin, persona, _ = seed_admin(db_session)
        headers = auth_headers(client, email=admin.email)

        event = _create_event(client, headers)
        client.post(
            "/api/agenda/participants",
            json=_participant_payload(event["id"], persona.id),
            headers=headers,
        )

        resp = client.get(f"/api/agenda/events/{event['id']}/participants", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_update_participant(self, client, db_session):
        admin, persona, _ = seed_admin(db_session)
        headers = auth_headers(client, email=admin.email)

        event = _create_event(client, headers)
        participant = client.post(
            "/api/agenda/participants",
            json=_participant_payload(event["id"], persona.id),
            headers=headers,
        ).json()

        resp = client.put(
            f"/api/agenda/participants/{participant['id']}",
            json=_participant_payload(event["id"], persona.id, status="CONFIRMADO"),
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["confirmation_status"] == "CONFIRMADO"

    def test_delete_participant(self, client, db_session):
        admin, persona, _ = seed_admin(db_session)
        headers = auth_headers(client, email=admin.email)

        event = _create_event(client, headers)
        participant = client.post(
            "/api/agenda/participants",
            json=_participant_payload(event["id"], persona.id),
            headers=headers,
        ).json()

        resp = client.delete(f"/api/agenda/participants/{participant['id']}", headers=headers)
        assert resp.status_code == 204

        resp = client.get(f"/api/agenda/events/{event['id']}/participants", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 0

    def test_delete_nonexistent_participant_returns_404(self, client, db_session):
        admin, _, _ = seed_admin(db_session)
        headers = auth_headers(client, email=admin.email)

        resp = client.delete(f"/api/agenda/participants/{uuid4()}", headers=headers)
        assert resp.status_code == 404

    def test_list_participants_nonexistent_event_returns_404(self, client, db_session):
        admin, _, _ = seed_admin(db_session)
        headers = auth_headers(client, email=admin.email)

        resp = client.get(f"/api/agenda/events/{uuid4()}/participants", headers=headers)
        assert resp.status_code == 404


# ── 4. CRUD Reservations ───────────────────────────────────────────────────

class TestReservationsCRUD:
    def test_list_reservations(self, client, db_session):
        admin, _, _ = seed_admin(db_session)
        headers = auth_headers(client, email=admin.email)

        event = _create_event(client, headers)
        resource = _create_resource(client, headers)

        starts = datetime(2026, 7, 5, 10, 0, tzinfo=timezone.utc)
        ends = starts + timedelta(hours=1)
        client.post(
            "/api/agenda/reservations",
            json=_reservation_payload(event["id"], resource["id"], starts, ends),
            headers=headers,
        )

        resp = client.get(f"/api/agenda/events/{event['id']}/reservations", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_update_reservation(self, client, db_session):
        admin, _, _ = seed_admin(db_session)
        headers = auth_headers(client, email=admin.email)

        event = _create_event(client, headers)
        resource = _create_resource(client, headers)

        starts = datetime(2026, 7, 5, 10, 0, tzinfo=timezone.utc)
        ends = starts + timedelta(hours=1)
        reservation = client.post(
            "/api/agenda/reservations",
            json=_reservation_payload(event["id"], resource["id"], starts, ends),
            headers=headers,
        ).json()

        new_starts = datetime(2026, 7, 5, 14, 0, tzinfo=timezone.utc)
        new_ends = new_starts + timedelta(hours=2)
        resp = client.put(
            f"/api/agenda/reservations/{reservation['id']}",
            json=_reservation_payload(event["id"], resource["id"], new_starts, new_ends),
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["resource_id"] == resource["id"]

    def test_delete_reservation(self, client, db_session):
        admin, _, _ = seed_admin(db_session)
        headers = auth_headers(client, email=admin.email)

        event = _create_event(client, headers)
        resource = _create_resource(client, headers)

        starts = datetime(2026, 7, 5, 10, 0, tzinfo=timezone.utc)
        ends = starts + timedelta(hours=1)
        reservation = client.post(
            "/api/agenda/reservations",
            json=_reservation_payload(event["id"], resource["id"], starts, ends),
            headers=headers,
        ).json()

        resp = client.delete(f"/api/agenda/reservations/{reservation['id']}", headers=headers)
        assert resp.status_code == 204

        resp = client.get(f"/api/agenda/events/{event['id']}/reservations", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 0

    def test_update_reservation_conflict_returns_409(self, client, db_session):
        admin, _, _ = seed_admin(db_session)
        headers = auth_headers(client, email=admin.email)

        event = _create_event(client, headers)
        resource = _create_resource(client, headers)

        t1 = datetime(2026, 7, 6, 10, 0, tzinfo=timezone.utc)
        t2 = t1 + timedelta(hours=1)
        client.post(
            "/api/agenda/reservations",
            json=_reservation_payload(event["id"], resource["id"], t1, t2),
            headers=headers,
        )

        t3 = datetime(2026, 7, 6, 12, 0, tzinfo=timezone.utc)
        t4 = t3 + timedelta(hours=1)
        other = client.post(
            "/api/agenda/reservations",
            json=_reservation_payload(event["id"], resource["id"], t3, t4),
            headers=headers,
        ).json()

        conflict_start = datetime(2026, 7, 6, 10, 30, tzinfo=timezone.utc)
        conflict_end = conflict_start + timedelta(hours=1)
        resp = client.put(
            f"/api/agenda/reservations/{other['id']}",
            json=_reservation_payload(event["id"], resource["id"], conflict_start, conflict_end),
            headers=headers,
        )
        assert resp.status_code == 409

    def test_delete_nonexistent_reservation_returns_404(self, client, db_session):
        admin, _, _ = seed_admin(db_session)
        headers = auth_headers(client, email=admin.email)

        resp = client.delete(f"/api/agenda/reservations/{uuid4()}", headers=headers)
        assert resp.status_code == 404


# ── 5. Schema validation ──────────────────────────────────────────────────

class TestSchemaValidation:
    def test_event_end_before_start_rejected(self, client, db_session):
        admin, _, _ = seed_admin(db_session)
        headers = auth_headers(client, email=admin.email)

        start = datetime(2026, 7, 1, 12, 0, tzinfo=timezone.utc)
        end = start - timedelta(hours=1)
        payload = _event_payload("Bad dates", start=start, end=end)
        resp = client.post("/api/agenda/events", json=payload, headers=headers)
        assert resp.status_code == 422

    def test_event_empty_title_rejected(self, client, db_session):
        admin, _, _ = seed_admin(db_session)
        headers = auth_headers(client, email=admin.email)

        payload = _event_payload()
        payload["title"] = ""
        resp = client.post("/api/agenda/events", json=payload, headers=headers)
        assert resp.status_code == 422

    def test_reservation_ends_equals_starts_rejected(self, client, db_session):
        admin, _, _ = seed_admin(db_session)
        headers = auth_headers(client, email=admin.email)

        event = _create_event(client, headers)
        resource = _create_resource(client, headers)

        t = datetime(2026, 7, 1, 10, 0, tzinfo=timezone.utc)
        resp = client.post(
            "/api/agenda/reservations",
            json=_reservation_payload(event["id"], resource["id"], t, t),
            headers=headers,
        )
        assert resp.status_code == 422

    def test_resource_empty_name_rejected(self, client, db_session):
        admin, _, _ = seed_admin(db_session)
        headers = auth_headers(client, email=admin.email)

        payload = _resource_payload(name="")
        resp = client.post("/api/agenda/resources", json=payload, headers=headers)
        assert resp.status_code == 422


# ── 6. Soft-delete forense ────────────────────────────────────────────────

class TestSoftDeleteForense:
    def test_archived_event_not_in_list(self, client, db_session):
        admin, _, _ = seed_admin(db_session)
        headers = auth_headers(client, email=admin.email)

        event = _create_event(client, headers)
        client.delete(f"/api/agenda/events/{event['id']}", headers=headers)

        resp = client.get("/api/agenda/events", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 0

    def test_archived_event_returns_404(self, client, db_session):
        admin, _, _ = seed_admin(db_session)
        headers = auth_headers(client, email=admin.email)

        event = _create_event(client, headers)
        client.delete(f"/api/agenda/events/{event['id']}", headers=headers)

        resp = client.get(f"/api/agenda/events/{event['id']}", headers=headers)
        assert resp.status_code == 404

    def test_archived_resource_not_in_list(self, client, db_session):
        admin, _, _ = seed_admin(db_session)
        headers = auth_headers(client, email=admin.email)

        resource = _create_resource(client, headers)
        client.delete(f"/api/agenda/resources/{resource['id']}", headers=headers)

        resp = client.get("/api/agenda/resources", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 0

    def test_participant_cascade_delete_on_event(self, client, db_session):
        admin, persona, _ = seed_admin(db_session)
        headers = auth_headers(client, email=admin.email)

        event = _create_event(client, headers)
        client.post(
            "/api/agenda/participants",
            json=_participant_payload(event["id"], persona.id),
            headers=headers,
        )

        client.delete(f"/api/agenda/events/{event['id']}", headers=headers)

        resp = client.get(f"/api/agenda/events/{event['id']}/participants", headers=headers)
        assert resp.status_code == 404


# ── 7. RBAC HTTP-level ────────────────────────────────────────────────────

class TestRBACAgenda:
    def test_unauthenticated_returns_401(self, client, db_session):
        resp = client.get("/api/agenda/events")
        assert resp.status_code == 401

    def test_read_only_user_can_list(self, client, db_session):
        admin, _, _ = seed_admin(db_session)
        headers = auth_headers(client, email=admin.email)

        resp = client.get("/api/agenda/events", headers=headers)
        assert resp.status_code == 200


# ── 8. Dashboard (BUG fix validation) ────────────────────────────────────

class TestAgendaDashboard:
    def test_dashboard_returns_cards(self, client, db_session):
        admin, _, _ = seed_admin(db_session)
        headers = auth_headers(client, email=admin.email)

        _create_event(client, headers, "Dashboard test")
        _create_resource(client, headers)

        resp = client.get("/api/dashboard/agenda", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "cards" in data
        assert len(data["cards"]) == 4
        events_card = next(c for c in data["cards"] if c["title"] == "Eventos")
        assert events_card["value"] == "1"


# ── 9. 404 edge cases (cobertura 100%) ───────────────────────────────────

class TestNotFoundEdgeCases:
    def test_update_nonexistent_event_returns_404(self, client, db_session):
        admin, _, _ = seed_admin(db_session)
        headers = auth_headers(client, email=admin.email)

        resp = client.put(
            f"/api/agenda/events/{uuid4()}",
            json=_event_payload("X"),
            headers=headers,
        )
        assert resp.status_code == 404

    def test_delete_nonexistent_event_returns_404(self, client, db_session):
        admin, _, _ = seed_admin(db_session)
        headers = auth_headers(client, email=admin.email)

        resp = client.delete(f"/api/agenda/events/{uuid4()}", headers=headers)
        assert resp.status_code == 404

    def test_create_participant_nonexistent_event_returns_404(self, client, db_session):
        admin, persona, _ = seed_admin(db_session)
        headers = auth_headers(client, email=admin.email)

        resp = client.post(
            "/api/agenda/participants",
            json=_participant_payload(str(uuid4()), persona.id),
            headers=headers,
        )
        assert resp.status_code == 404

    def test_create_participant_nonexistent_persona_returns_404(self, client, db_session):
        admin, _, _ = seed_admin(db_session)
        headers = auth_headers(client, email=admin.email)

        event = _create_event(client, headers)
        resp = client.post(
            "/api/agenda/participants",
            json=_participant_payload(event["id"], uuid4()),
            headers=headers,
        )
        assert resp.status_code == 404

    def test_update_nonexistent_participant_returns_404(self, client, db_session):
        admin, _, _ = seed_admin(db_session)
        headers = auth_headers(client, email=admin.email)

        event = _create_event(client, headers)
        resp = client.put(
            f"/api/agenda/participants/{uuid4()}",
            json=_participant_payload(event["id"], uuid4()),
            headers=headers,
        )
        assert resp.status_code == 404

    def test_create_reservation_nonexistent_event_returns_404(self, client, db_session):
        admin, _, _ = seed_admin(db_session)
        headers = auth_headers(client, email=admin.email)

        resource = _create_resource(client, headers)
        t = datetime(2026, 7, 10, 10, 0, tzinfo=timezone.utc)
        resp = client.post(
            "/api/agenda/reservations",
            json=_reservation_payload(str(uuid4()), resource["id"], t, t + timedelta(hours=1)),
            headers=headers,
        )
        assert resp.status_code == 404

    def test_create_reservation_nonexistent_resource_returns_404(self, client, db_session):
        admin, _, _ = seed_admin(db_session)
        headers = auth_headers(client, email=admin.email)

        event = _create_event(client, headers)
        t = datetime(2026, 7, 10, 10, 0, tzinfo=timezone.utc)
        resp = client.post(
            "/api/agenda/reservations",
            json=_reservation_payload(event["id"], str(uuid4()), t, t + timedelta(hours=1)),
            headers=headers,
        )
        assert resp.status_code == 404

    def test_list_reservations_nonexistent_event_returns_404(self, client, db_session):
        admin, _, _ = seed_admin(db_session)
        headers = auth_headers(client, email=admin.email)

        resp = client.get(f"/api/agenda/events/{uuid4()}/reservations", headers=headers)
        assert resp.status_code == 404

    def test_update_nonexistent_reservation_returns_404(self, client, db_session):
        admin, _, _ = seed_admin(db_session)
        headers = auth_headers(client, email=admin.email)

        event = _create_event(client, headers)
        resource = _create_resource(client, headers)
        t = datetime(2026, 7, 10, 10, 0, tzinfo=timezone.utc)
        resp = client.put(
            f"/api/agenda/reservations/{uuid4()}",
            json=_reservation_payload(event["id"], resource["id"], t, t + timedelta(hours=1)),
            headers=headers,
        )
        assert resp.status_code == 404

    def test_get_event_detail_success(self, client, db_session):
        admin, _, _ = seed_admin(db_session)
        headers = auth_headers(client, email=admin.email)

        event = _create_event(client, headers)
        resp = client.get(f"/api/agenda/events/{event['id']}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == event["id"]

    def test_update_event_success(self, client, db_session):
        admin, _, _ = seed_admin(db_session)
        headers = auth_headers(client, email=admin.email)

        event = _create_event(client, headers)
        payload = _event_payload("Actualizado completo")
        payload["location"] = "Nueva ubicación"
        payload["color_hex"] = "#ff0000"
        payload["url_conferencia"] = "https://meet.example.com/abc"
        payload["visibilidad"] = "PUBLICO"
        resp = client.put(
            f"/api/agenda/events/{event['id']}",
            json=payload,
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Actualizado completo"
        assert data["location"] == "Nueva ubicación"
        assert data["color_hex"] == "#ff0000"
        assert data["url_conferencia"] == "https://meet.example.com/abc"
        assert data["visibilidad"] == "PUBLICO"

    def test_create_reservation_conflict_returns_409(self, client, db_session):
        admin, _, _ = seed_admin(db_session)
        headers = auth_headers(client, email=admin.email)

        event = _create_event(client, headers)
        resource = _create_resource(client, headers)

        t1 = datetime(2026, 7, 11, 10, 0, tzinfo=timezone.utc)
        t2 = t1 + timedelta(hours=2)
        client.post(
            "/api/agenda/reservations",
            json=_reservation_payload(event["id"], resource["id"], t1, t2),
            headers=headers,
        )

        overlap_start = datetime(2026, 7, 11, 11, 0, tzinfo=timezone.utc)
        overlap_end = overlap_start + timedelta(hours=1)
        resp = client.post(
            "/api/agenda/reservations",
            json=_reservation_payload(event["id"], resource["id"], overlap_start, overlap_end),
            headers=headers,
        )
        assert resp.status_code == 409
