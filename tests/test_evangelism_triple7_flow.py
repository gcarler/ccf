from datetime import datetime, timezone

from backend import models
from tests.conftest import auth_headers, seed_admin


def _seed_personas(db_session, sede_id, count=40):
    personas = []
    for idx in range(1, count + 1):
        persona = models.Persona(
            first_name=f"Triple7",
            last_name=f"Persona {idx:02d}",
            email=f"triple7.persona{idx:02d}@ccf.test",
            phone=f"300777{idx:04d}",
            sede_id=sede_id,
            church_role="Miembro",
        )
        db_session.add(persona)
        personas.append(persona)
    db_session.commit()
    for persona in personas:
        db_session.refresh(persona)
    return personas


def test_flujo_estrategia_triple7_geografica_relacional_semanal(client, db_session):
    seed_admin(db_session)
    headers = auth_headers(client)

    admin = db_session.query(models.Usuario).filter(models.Usuario.email == "admin@example.com").one()
    personas = _seed_personas(db_session, admin.sede_id, count=40)

    strategy_response = client.post(
        "/api/evangelism/strategies",
        json={
            "name": "estrategia triple 7",
            "description": "Validacion integral de estrategia geografica relacional semanal",
            "typology": "relacional",
            "strategy_type": "geografica",
            "recurrence": "SEMANAL",
            "day_of_week": "Lunes",
            "start_time": "19:00",
            "start_date": "2026-06-01T19:00:00Z",
            "end_date": "2026-06-22T19:00:00Z",
            "status": "active",
            "activa": True,
        },
        headers=headers,
    )
    assert strategy_response.status_code == 200, strategy_response.text
    strategy = strategy_response.json()
    assert strategy["id"]
    assert strategy["name"] == "estrategia triple 7"
    assert strategy["typology"] == "relacional"
    assert strategy["strategy_type"] == "geografica"
    assert strategy["recurrence"] == "SEMANAL"

    groups = []
    for group_index in range(4):
        group_personas = personas[group_index * 10 : (group_index + 1) * 10]
        group_name = f"g{group_index + 1}"
        group_response = client.post(
            "/api/evangelism/grupos",
            json={
                "name": group_name,
                "zone": f"Zona {group_index + 1}",
                "address": f"Direccion {group_index + 1}",
                "capacity": 10,
                "day_of_week": "Lunes",
                "start_time": "19:00",
                "estrategia_id": strategy["id"],
                "base_attendee_ids": [str(persona.id) for persona in group_personas],
            },
            headers=headers,
        )
        assert group_response.status_code == 200, group_response.text
        group = group_response.json()
        assert group["name"] == group_name
        assert group["evangelism_strategy_id"] == strategy["id"]
        groups.append((group, group_personas))

        detail_response = client.get(f"/api/evangelism/grupos/{group['id']}", headers=headers)
        assert detail_response.status_code == 200, detail_response.text
        detail = detail_response.json()
        assert detail["base_attendee_ids"] == [str(persona.id) for persona in group_personas]
        assert len(detail["base_attendees"]) == 10

    generate_response = client.post(
        f"/api/evangelism/strategies/{strategy['id']}/generate-sessions",
        headers=headers,
    )
    assert generate_response.status_code == 200, generate_response.text
    generated = generate_response.json()
    assert generated["groups"] == 4
    assert generated["sessions_per_group"] == 4
    assert generated["total_sessions_created"] == 16

    sessions_response = client.get(
        "/api/evangelism/sessions",
        params={"strategy_id": strategy["id"]},
        headers=headers,
    )
    assert sessions_response.status_code == 200, sessions_response.text
    sessions = sessions_response.json()
    assert len(sessions) == 16
    assert {session["estado_habilitacion"] for session in sessions} == {"DESHABILITADO"}

    blocked_session = sessions[0]
    blocked_response = client.post(
        f"/api/evangelism/sessions/{blocked_session['id']}/attendance",
        json=[{"persona_id": str(groups[0][1][0].id), "status": "present"}],
        headers=headers,
    )
    assert blocked_response.status_code == 403

    habilitar_response = client.post(
        f"/api/evangelism/strategies/{strategy['id']}/habilitar-todas",
        headers=headers,
    )
    assert habilitar_response.status_code == 200, habilitar_response.text
    assert habilitar_response.json()["sesiones_habilitadas"] == 16

    sessions_by_group = {group["id"]: [] for group, _ in groups}
    sessions_response = client.get(
        "/api/evangelism/sessions",
        params={"strategy_id": strategy["id"]},
        headers=headers,
    )
    assert sessions_response.status_code == 200, sessions_response.text
    for session in sessions_response.json():
        assert session["estado_habilitacion"] == "HABILITADO"
        sessions_by_group[session["grupo_id"]].append(session)

    for group, group_personas in groups:
        group_sessions = sorted(sessions_by_group[group["id"]], key=lambda item: item["session_date"])
        assert len(group_sessions) == 4
        assert [
            datetime.fromisoformat(item["session_date"].replace("Z", "+00:00")).date().isoformat()
            for item in group_sessions
        ] == ["2026-06-01", "2026-06-08", "2026-06-15", "2026-06-22"]

        for week_index, session in enumerate(group_sessions):
            attendance_payload = [
                {
                    "persona_id": str(persona.id),
                    "status": "absent" if persona_index == week_index else "present",
                    "notes": "Ausencia validada en prueba" if persona_index == week_index else None,
                }
                for persona_index, persona in enumerate(group_personas)
            ]
            attendance_response = client.post(
                f"/api/evangelism/sessions/{session['id']}/attendance",
                json=attendance_payload,
                headers=headers,
            )
            assert attendance_response.status_code == 200, attendance_response.text

            attendance_rows = (
                db_session.query(models.Asistencia)
                .filter(
                    models.Asistencia.sesion_id == session["id"],
                    models.Asistencia.deleted_at.is_(None),
                )
                .all()
            )
            assert len(attendance_rows) == 10
            assert sum(1 for row in attendance_rows if row.estado == "presente") == 9
            assert sum(1 for row in attendance_rows if row.estado == "FALTO") == 1

    strategy_detail = client.get(f"/api/evangelism/strategies/{strategy['id']}", headers=headers)
    assert strategy_detail.status_code == 200, strategy_detail.text
    assert strategy_detail.json()["group_count"] == 4


def test_faro_temporada_crea_sesion_habilitada_para_reporte(client, db_session):
    seed_admin(db_session)
    headers = auth_headers(client)

    admin = db_session.query(models.Usuario).filter(models.Usuario.email == "admin@example.com").one()
    persona = _seed_personas(db_session, admin.sede_id, count=1)[0]

    group_response = client.post(
        "/api/evangelism/grupos",
        json={
            "name": "faro test",
            "zone": "Zona FARO",
            "address": "Direccion FARO",
            "capacity": 10,
            "base_attendee_ids": [str(persona.id)],
        },
        headers=headers,
    )
    assert group_response.status_code == 200, group_response.text
    group = group_response.json()

    season_response = client.post(
        "/api/evangelism/faro/seasons",
        json={
            "name": "Temporada FARO",
            "start_date": "2026-06-01",
            "end_date": "2026-06-30",
            "periodicity": "SEMANAL",
        },
        headers=headers,
    )
    assert season_response.status_code == 200, season_response.text
    season = season_response.json()

    session_response = client.post(
        "/api/evangelism/faro/sessions",
        json={
            "season_id": season["id"],
            "grupo_id": group["id"],
            "session_date": "2026-06-08",
            "topic": "S1",
        },
        headers=headers,
    )
    assert session_response.status_code == 200, session_response.text
    data = session_response.json()
    assert data["created_count"] == 1
    assert len(data["session_ids"]) == 1

    session_id = data["session_ids"][0]
    session = db_session.query(models.SesionGrupo).filter(models.SesionGrupo.id == session_id).one()
    assert session.estado_habilitacion == "HABILITADO"

    attendance_response = client.post(
        f"/api/evangelism/faro/sessions/{session_id}/attendance",
        json={"persona_ids": [str(persona.id)]},
        headers=headers,
    )
    assert attendance_response.status_code == 200, attendance_response.text
    assert attendance_response.json()["processed"] == 1
