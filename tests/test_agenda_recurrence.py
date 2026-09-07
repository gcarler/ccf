"""Suite adversarial de recurrencia (RRULE) para la Agenda CCF.

Cubre validación de reglas, expansión en ventana, excepciones, techo de
ocurrencias, semántica de preservación en PUT y el contrato de expansión del
agregador system/calendar.
"""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from backend.services.agenda_recurrence import (
    MAX_OCCURRENCES_PER_SERIES,
    MAX_SERIES_LOOKBACK_DAYS,
    expand_event,
    validate_rrule,
)
from tests.conftest import auth_headers, seed_admin


def _base_payload(**overrides):
    starts_at = datetime(2026, 9, 7, 19, 0, tzinfo=timezone.utc)  # lunes
    payload = {
        "title": "Culto semanal",
        "description": "Servicio dominical entre semana",
        "start_at": starts_at.isoformat(),
        "end_at": (starts_at + timedelta(hours=1)).isoformat(),
        "location": "Templo principal",
        "is_all_day": False,
        "recurrence_rule": "RRULE:FREQ=WEEKLY;BYDAY=MO",
    }
    payload.update(overrides)
    return payload


def _create(client, headers, **overrides):
    response = client.post("/api/agenda/events", json=_base_payload(**overrides), headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


# ── Validación de reglas ────────────────────────────────────────────────


def test_create_recurring_event_returns_series_fields(client, db_session):
    admin, _, _ = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email)

    event = _create(client, headers)
    assert event["is_recurring"] is True
    assert event["recurrence_id"] is None
    assert event["recurrence_rule"].startswith("RRULE:")
    assert event["start_at"].startswith("2026-09-07T19:00")


def test_invalid_rrule_rejected(client, db_session):
    admin, _, _ = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email)

    response = client.post(
        "/api/agenda/events",
        json=_base_payload(recurrence_rule="RRULE:FREQ=NOPE"),
        headers=headers,
    )
    assert response.status_code == 422


def test_rrule_count_above_cap_rejected(client, db_session):
    admin, _, _ = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email)

    response = client.post(
        "/api/agenda/events",
        json=_base_payload(recurrence_rule="RRULE:FREQ=DAILY;COUNT=999999"),
        headers=headers,
    )
    assert response.status_code == 422


def test_validate_rrule_normalizes_prefix():
    assert validate_rrule("FREQ=DAILY;COUNT=3").startswith("RRULE:")
    assert validate_rrule("RRULE:FREQ=DAILY;COUNT=3") == "RRULE:FREQ=DAILY;COUNT=3"


# ── Expansión en ventana ────────────────────────────────────────────────


def test_by_date_range_expands_series(client, db_session):
    admin, _, _ = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email)
    event = _create(client, headers)

    start = datetime(2026, 9, 1, tzinfo=timezone.utc)
    end = datetime(2026, 10, 1, tzinfo=timezone.utc)
    response = client.get(
        "/api/agenda/events/by-date-range",
        params={"start": start.isoformat(), "end": end.isoformat()},
        headers=headers,
    )
    assert response.status_code == 200
    rows = response.json()
    starts = [row["start_at"] for row in rows]
    # Lunes: 7, 14, 21 y 28 de septiembre de 2026.
    assert len(rows) == 4
    assert any(s.startswith("2026-09-07T19:00") for s in starts)
    assert all(row["recurrence_id"] for row in rows)
    assert all(row["is_recurring"] is False for row in rows)
    assert any(row["id"] == event["id"] for row in rows)


def test_by_date_range_single_day_window(client, db_session):
    admin, _, _ = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email)
    _create(client, headers)

    response = client.get(
        "/api/agenda/events/by-date-range",
        params={
            "start": datetime(2026, 9, 21, tzinfo=timezone.utc).isoformat(),
            "end": datetime(2026, 9, 22, tzinfo=timezone.utc).isoformat(),
        },
        headers=headers,
    )
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["start_at"].startswith("2026-09-21T19:00")


def test_expansion_respects_exceptions(client, db_session):
    admin, _, _ = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email)
    _create(client, headers, recurrence_exceptions=["2026-09-14"])

    start = datetime(2026, 9, 1, tzinfo=timezone.utc)
    end = datetime(2026, 10, 1, tzinfo=timezone.utc)
    response = client.get(
        "/api/agenda/events/by-date-range",
        params={"start": start.isoformat(), "end": end.isoformat()},
        headers=headers,
    )
    starts = [row["start_at"] for row in response.json()]
    assert len(starts) == 3
    assert not any(s.startswith("2026-09-14") for s in starts)


def test_occurrence_crossing_window_start_is_included():
    row = SimpleNamespace(
        id="cross",
        fecha_inicio=datetime(2026, 9, 7, 19, 0, tzinfo=timezone.utc),
        fecha_fin=datetime(2026, 9, 7, 21, 0, tzinfo=timezone.utc),
        regla_recurrencia="RRULE:FREQ=WEEKLY;BYDAY=MO",
        excepciones_recurrencia=[],
    )
    occs = expand_event(
        row,
        datetime(2026, 9, 7, 20, 0, tzinfo=timezone.utc),
        datetime(2026, 9, 8, tzinfo=timezone.utc),
    )
    assert len(occs) == 1
    assert occs[0][0] == datetime(2026, 9, 7, 19, 0, tzinfo=timezone.utc)
    assert occs[0][1] == datetime(2026, 9, 7, 21, 0, tzinfo=timezone.utc)


# ── Límites defensivos del servicio ─────────────────────────────────────


def test_service_caps_occurrences_per_series():
    row = SimpleNamespace(
        id="cap",
        fecha_inicio=datetime(2026, 9, 7, tzinfo=timezone.utc),
        fecha_fin=datetime(2026, 9, 7, 0, 1, tzinfo=timezone.utc),
        regla_recurrencia="RRULE:FREQ=SECONDLY",
        excepciones_recurrencia=[],
    )
    occs = expand_event(
        row,
        datetime(2026, 9, 7, tzinfo=timezone.utc),
        datetime(2026, 9, 8, tzinfo=timezone.utc),
    )
    assert len(occs) == MAX_OCCURRENCES_PER_SERIES


def test_service_skips_ancient_series():
    ancient = datetime.now(timezone.utc) - timedelta(days=MAX_SERIES_LOOKBACK_DAYS + 5)
    row = SimpleNamespace(
        id="old",
        fecha_inicio=ancient,
        fecha_fin=ancient + timedelta(hours=1),
        regla_recurrencia="RRULE:FREQ=DAILY",
        excepciones_recurrencia=[],
    )
    assert (
        expand_event(
            row,
            datetime.now(timezone.utc),
            datetime.now(timezone.utc) + timedelta(days=7),
        )
        == []
    )


def test_service_never_raises_on_corrupt_rule():
    row = SimpleNamespace(
        id="bad",
        fecha_inicio=datetime(2026, 9, 7, tzinfo=timezone.utc),
        fecha_fin=datetime(2026, 9, 7, 1, tzinfo=timezone.utc),
        regla_recurrencia="RRULE:FREQ=GIBBERISH",
        excepciones_recurrencia=None,
    )
    assert (
        expand_event(
            row,
            datetime(2026, 9, 1, tzinfo=timezone.utc),
            datetime(2026, 10, 1, tzinfo=timezone.utc),
        )
        == []
    )


# ── Semántica de PUT sobre la serie ────────────────────────────────────


def test_put_without_recurrence_field_preserves_series(client, db_session):
    admin, _, _ = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email)
    event = _create(client, headers)

    response = client.put(
        f"/api/agenda/events/{event['id']}",
        json={
            "title": "Culto renombrado",
            "start_at": event["start_at"],
            "end_at": event["end_at"],
            "is_all_day": False,
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["title"] == "Culto renombrado"
    assert body["is_recurring"] is True


def test_put_with_empty_string_clears_series(client, db_session):
    admin, _, _ = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email)
    event = _create(client, headers)

    response = client.put(
        f"/api/agenda/events/{event['id']}",
        json={
            "title": "Culto único",
            "start_at": event["start_at"],
            "end_at": event["end_at"],
            "is_all_day": False,
            "recurrence_rule": "",
        },
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["recurrence_rule"] is None
    assert body["is_recurring"] is False


# ── Contrato del agregador system/calendar ─────────────────────────────


def test_system_calendar_expands_recurring_series(client, db_session):
    admin, _, _ = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email)
    event = _create(client, headers)

    response = client.get("/api/system/calendar", headers=headers)
    assert response.status_code == 200
    events = response.json()
    assert isinstance(events, list)
    agenda_rows = [e for e in events if str(e.get("id", "")).startswith("agenda-")]
    series_rows = [e for e in agenda_rows if e["id"].startswith(f"agenda-{event['id']}:")]
    assert len(series_rows) >= 1
    assert all(e.get("is_recurring") is True for e in series_rows)
    assert all(e["href"].startswith(f"/plataforma/agenda/events/{event['id']}?occurrence=") for e in series_rows)


# ── Edición por ocurrencia (v2) ──────────────────────────────────────


def test_edit_single_occurrence_materializes_standalone(client, db_session):
    admin, _, _ = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email)
    event = _create(client, headers)

    response = client.put(
        f"/api/agenda/events/{event['id']}",
        params={"occurrence_date": "2026-09-14"},
        json=_base_payload(
            title="Culto especial",
            start_at=datetime(2026, 9, 14, 20, 0, tzinfo=timezone.utc).isoformat(),
            end_at=datetime(2026, 9, 14, 21, 0, tzinfo=timezone.utc).isoformat(),
        ),
        headers=headers,
    )
    assert response.status_code == 200, response.text
    standalone = response.json()
    assert standalone["is_recurring"] is False
    assert standalone["recurrence_rule"] is None
    assert standalone["title"] == "Culto especial"
    assert standalone["derived_from"] == f"serie:{event['id']}:2026-09-14"

    start = datetime(2026, 9, 1, tzinfo=timezone.utc)
    end = datetime(2026, 10, 5, tzinfo=timezone.utc)
    range_response = client.get(
        "/api/agenda/events/by-date-range",
        params={"start": start.isoformat(), "end": end.isoformat()},
        headers=headers,
    )
    assert range_response.status_code == 200, range_response.text
    rows = range_response.json()
    series_days = [r["start_at"][:10] for r in rows if r["id"] == event["id"]]
    assert "2026-09-14" not in series_days
    for day in ("2026-09-07", "2026-09-21", "2026-09-28"):
        assert day in series_days
    standalone_rows = [r for r in rows if r["id"] == standalone["id"]]
    assert len(standalone_rows) == 1
    assert standalone_rows[0]["start_at"].startswith("2026-09-14T20:00")

    anchor = client.get(f"/api/agenda/events/{event['id']}", headers=headers).json()
    assert "2026-09-14" in anchor["recurrence_exceptions"]


def test_delete_single_occurrence_keeps_series(client, db_session):
    admin, _, _ = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email)
    event = _create(client, headers)

    response = client.delete(
        f"/api/agenda/events/{event['id']}",
        params={"occurrence_date": "2026-09-14"},
        headers=headers,
    )
    assert response.status_code == 204

    start = datetime(2026, 9, 1, tzinfo=timezone.utc)
    end = datetime(2026, 10, 1, tzinfo=timezone.utc)
    rows = client.get(
        "/api/agenda/events/by-date-range",
        params={"start": start.isoformat(), "end": end.isoformat()},
        headers=headers,
    ).json()
    starts = [r["start_at"][:10] for r in rows]
    assert "2026-09-14" not in starts
    assert {"2026-09-07", "2026-09-21", "2026-09-28"}.issubset(set(starts))


def test_delete_occurrence_twice_returns_422(client, db_session):
    admin, _, _ = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email)
    event = _create(client, headers)

    first = client.delete(
        f"/api/agenda/events/{event['id']}",
        params={"occurrence_date": "2026-09-14"},
        headers=headers,
    )
    assert first.status_code == 204
    second = client.delete(
        f"/api/agenda/events/{event['id']}",
        params={"occurrence_date": "2026-09-14"},
        headers=headers,
    )
    assert second.status_code == 422


def test_edit_occurrence_on_non_recurring_event_422(client, db_session):
    admin, _, _ = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email)
    event = _create(client, headers, recurrence_rule=None)

    response = client.put(
        f"/api/agenda/events/{event['id']}",
        params={"occurrence_date": "2026-09-14"},
        json=_base_payload(recurrence_rule=None),
        headers=headers,
    )
    assert response.status_code == 422


def test_occurrence_date_not_in_series_422(client, db_session):
    admin, _, _ = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email)
    event = _create(client, headers)

    response = client.delete(
        f"/api/agenda/events/{event['id']}",
        params={"occurrence_date": "2026-09-15"},  # martes: la serie es semanal los lunes
        headers=headers,
    )
    assert response.status_code == 422


def test_malformed_occurrence_date_422(client, db_session):
    admin, _, _ = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email)
    event = _create(client, headers)

    response = client.delete(
        f"/api/agenda/events/{event['id']}",
        params={"occurrence_date": "2026-13-45"},
        headers=headers,
    )
    assert response.status_code == 422


def test_edit_anchor_occurrence_excludes_first(client, db_session):
    admin, _, _ = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email)
    event = _create(client, headers)

    response = client.delete(
        f"/api/agenda/events/{event['id']}",
        params={"occurrence_date": "2026-09-07"},
        headers=headers,
    )
    assert response.status_code == 204

    start = datetime(2026, 9, 1, tzinfo=timezone.utc)
    end = datetime(2026, 10, 1, tzinfo=timezone.utc)
    rows = client.get(
        "/api/agenda/events/by-date-range",
        params={"start": start.isoformat(), "end": end.isoformat()},
        headers=headers,
    ).json()
    starts = [r["start_at"][:10] for r in rows]
    assert "2026-09-07" not in starts
    assert "2026-09-14" in starts


def test_occurrence_start_for_and_add_exception_unit(db_session):
    """Unidad: detección de ocurrencia y deduplicación de excepciones."""
    from types import SimpleNamespace

    from backend.services.agenda_recurrence import add_exception, occurrence_start_for

    row = SimpleNamespace(
        fecha_inicio=datetime(2026, 9, 7, 19, 0, tzinfo=timezone.utc),
        fecha_fin=datetime(2026, 9, 7, 20, 0, tzinfo=timezone.utc),
        regla_recurrencia="RRULE:FREQ=WEEKLY;BYDAY=MO",
        excepciones_recurrencia=["2026-09-14"],
    )
    occ = occurrence_start_for(row, "2026-09-21")
    assert occ is not None and occ.date().isoformat() == "2026-09-21"
    assert occurrence_start_for(row, "2026-09-15") is None  # martes
    assert occurrence_start_for(row, "2026-09-14") is None  # ya exceptuada
    assert occurrence_start_for(row, "no-es-fecha") is None

    assert add_exception(row, "2026-09-21") == ["2026-09-14", "2026-09-21"]
    assert add_exception(row, "2026-09-21") == ["2026-09-14", "2026-09-21"]  # idempotente
