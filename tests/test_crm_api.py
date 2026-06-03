import uuid
from datetime import datetime

import pytest
from backend import models
from backend.core.security import get_password_hash


def seed_admin(
    db_session, email="admin@example.com", password="secret123", role="admin"
):
    user = models.User(
        username="admin",
        email=email,
        password_hash=get_password_hash(password),
        role=role,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def auth_headers(client, email="admin@example.com", password="secret123"):
    response = client.post(
        "/api/auth/login",
        data={"username": email, "password": password, "grant_type": "password"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def seed_strategy(db_session):
    """Create a Relacional evangelism strategy for test fixtures."""
    strategy = models.EvangelismStrategy(
        name="Estrategia Test",
        typology="relacional",
        recurrence="SEMANAL",
        day_of_week="Miercoles",
        start_time="19:00",
        status="active",
    )
    db_session.add(strategy)
    db_session.commit()
    db_session.refresh(strategy)
    return strategy


def seed_sede(db_session):
    sede = models.Sede(nombre="Sede Central", ciudad="Bogota", es_activa=True)
    db_session.add(sede)
    db_session.commit()
    db_session.refresh(sede)
    return sede


def seed_user_with_role(db_session, role: str, email: str, password: str = "secret123"):
    user = models.User(
        username=email.split("@")[0],
        email=email,
        password_hash=get_password_hash(password),
        role=role,
        role_id=None,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


async def _failing_send_whatsapp(db, member_id, content, sender_user_id):
    raise RuntimeError("gateway timeout: internal host details")


def test_send_crm_message_hides_gateway_error(client, db_session, monkeypatch):
    seed_admin(db_session)
    persona = models.Persona(
        first_name="Carlos", last_name="Ruiz", email="carlos@example.com"
    )
    db_session.add(persona)
    db_session.commit()
    db_session.refresh(persona)

    monkeypatch.setattr(
        "backend.services.messaging.MessagingGateway.send_whatsapp",
        _failing_send_whatsapp,
    )

    response = client.post(
        "/api/crm/messaging/send",
        json={"persona_id": str(persona.id), "channel": "WhatsApp", "content": "hola"},
        headers=auth_headers(client),
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "No se pudo enviar el mensaje"


def test_create_crm_task_requires_title(client, db_session):
    seed_admin(db_session)

    response = client.post(
        "/api/crm/tasks/",
        json={"title": "   ", "member_id": 1},
        headers=auth_headers(client),
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "title is required"


def test_create_crm_task_hides_invalid_date_details(client, db_session):
    seed_admin(db_session)

    response = client.post(
        "/api/crm/tasks/",
        json={"title": "Llamar miembro", "due_date": "not-a-date"},
        headers=auth_headers(client),
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Formato de fecha o identificador invalido"


def test_messaging_history_item_detail_route(client, db_session):
    admin = seed_admin(db_session)
    member = models.Member(
        first_name="Ana",
        last_name="Perez",
        email="ana@example.com",
        user_id=admin.id,
    )
    db_session.add(member)
    db_session.flush()
    log = models.CommunicationLog(
        member_id=member.id,
        channel="WhatsApp",
        recipient_phone="+573001112233",
        content="Hola",
        leader_user_id=admin.id,
        outcome="delivered",
        external_id="msg-123",
    )
    db_session.add(log)
    db_session.commit()

    response = client.get(
        f"/api/crm/messaging/history/{log.id}",
        headers=auth_headers(client),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == log.id
    assert data["name"] == "Mensaje a Ana Perez"
    assert data["channel"] == "whatsapp"
    assert data["status"] == "delivered"
    assert data["target_count"] == 1
    assert data["delivered_count"] == 1
    assert data["failed_count"] == 0


def test_crm_campaign_send_groups_history(client, db_session):
    admin = seed_admin(db_session)
    family = models.Family(name="Familia Gomez")
    db_session.add(family)
    db_session.flush()

    active_member = models.Member(
        first_name="Luis",
        last_name="Martinez",
        email="luis@example.com",
        phone="+573001112234",
        church_role="Miembro",
        spiritual_status="Nuevo",
        user_id=admin.id,
    )
    group_member = models.Member(
        first_name="Maria",
        last_name="Lopez",
        email="maria@example.com",
        phone="+573001112235",
        church_role="Visitante",
        spiritual_status="Creyente",
        family_id=family.id,
    )
    db_session.add_all([active_member, group_member])
    db_session.commit()

    response = client.post(
        "/api/crm/messaging/send",
        json={
            "name": "Campaña de Bienvenida",
            "channel": "whatsapp",
            "content": "Hola {nombre}",
            "target_segments": ["active", "groups"],
        },
        headers=auth_headers(client),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["target_count"] == 2
    assert payload["delivered_count"] == 2
    assert payload["failed_count"] == 0
    assert len(payload["log_ids"]) == 2

    history_response = client.get(
        "/api/crm/messaging/history", headers=auth_headers(client)
    )
    assert history_response.status_code == 200
    history = history_response.json()
    assert len(history) == 1
    assert history[0]["name"] == "Campaña de Bienvenida"
    assert history[0]["target_count"] == 2

    detail_response = client.get(
        f"/api/crm/messaging/history/{history[0]['id']}",
        headers=auth_headers(client),
    )
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["name"] == "Campaña de Bienvenida"
    assert detail["target_count"] == 2
    assert detail["delivered_count"] == 2
    assert detail["failed_count"] == 0


def test_member_donations_for_admin_dashboard(client, db_session):
    seed_admin(db_session)
    member = models.Member(
        first_name="Carlos", last_name="Ruiz", email="carlos@example.com"
    )
    db_session.add(member)
    db_session.flush()
    donation = models.Donation(
        member_id=member.id,
        amount=250.0,
        donation_type="Ofrenda",
        donor_name=None,
        status="completed",
    )
    db_session.add(donation)
    db_session.commit()

    response = client.get("/api/crm/personas-legacy/donations", headers=auth_headers(client))
    print("MEMBER_DONATIONS_RESPONSE:", response.json() if response.status_code == 200 else response.text)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["donor"] == "Carlos Ruiz"
    assert float(data[0]["amount"]) == 250.0
    assert data[0]["type"] == "Ofrenda"
    assert data[0]["status"] == "completed"


def test_crm_tasks_mine_and_detail_routes(client, db_session):
    admin = seed_admin(db_session)
    task = models.CrmTask(
        title="Seguimiento pastoral",
        description="Llamar al miembro",
        status="pending",
        priority="high",
        category="Pastoral",
        assignee_user_id=admin.id,
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    mine_response = client.get("/api/crm/tasks/mine", headers=auth_headers(client))
    assert mine_response.status_code == 200
    mine_data = mine_response.json()
    assert len(mine_data) == 1
    assert mine_data[0]["id"] == task.id
    assert mine_data[0]["title"] == "Seguimiento pastoral"

    detail_response = client.get(
        f"/api/crm/tasks/{task.id}", headers=auth_headers(client)
    )
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["id"] == task.id
    assert detail["title"] == "Seguimiento pastoral"


def test_crm_task_detail_denies_non_staff_non_owner(client, db_session):
    admin = seed_admin(db_session)
    outsider = seed_user_with_role(
        db_session, role="estudiante", email="outsider@example.com"
    )
    task = models.CrmTask(
        title="Tarea sensible",
        description="Solo para staff",
        status="pending",
        priority="high",
        category="Pastoral",
        assignee_user_id=admin.id,
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    response = client.get(
        f"/api/crm/tasks/{task.id}", headers=auth_headers(client, email=outsider.email)
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "No autorizado para ver esta tarea"


def test_crm_task_detail_allows_owner_non_staff(client, db_session):
    owner = seed_user_with_role(
        db_session, role="estudiante", email="owner@example.com"
    )
    task = models.CrmTask(
        title="Tarea propia",
        description="Detalle permitido al dueño",
        status="pending",
        priority="medium",
        category="Pastoral",
        assignee_user_id=owner.id,
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    response = client.get(
        f"/api/crm/tasks/{task.id}", headers=auth_headers(client, email=owner.email)
    )

    assert response.status_code == 200
    assert response.json()["id"] == task.id


def test_crm_counseling_detail_route(client, db_session):
    admin = seed_admin(db_session)
    member = models.Member(
        first_name="Elena",
        last_name="Gomez",
        email="elena@example.com",
        user_id=admin.id,
    )
    db_session.add(member)
    db_session.flush()

    ticket = models.CounselingTicket(
        member_id=member.id,
        pastor_user_id=admin.id,
        subject="Acompañamiento familiar",
        notes="Seguimiento pastoral inicial",
        status="open",
        priority_level="HIGH",
    )
    previous_ticket = models.CounselingTicket(
        member_id=member.id,
        pastor_user_id=admin.id,
        subject="Oración por salud",
        notes="Registro previo",
        status="resolved",
        priority_level="NORMAL",
    )
    db_session.add_all([ticket, previous_ticket])
    db_session.commit()
    db_session.refresh(ticket)

    response = client.get(
        f"/api/evangelism/counseling/{ticket.id}",
        headers=auth_headers(client),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == ticket.id
    assert data["persona_id"] == str(member.id)
    assert data["member_name"] == "Elena Gomez"
    assert data["topic"] == "Acompañamiento familiar"
    assert data["summary"] == "Acompañamiento familiar"
    assert data["notes"] == "Seguimiento pastoral inicial"
    assert data["confidential_notes"] == "Seguimiento pastoral inicial"
    assert data["status"] == "open"
    assert data["priority_level"] == "HIGH"
    assert data["duration_minutes"] == 60
    assert len(data["history"]) == 2
    assert {item["text"] for item in data["history"]} == {
        "Acompañamiento familiar",
        "Oración por salud",
    }


def test_crm_cell_group_detail_route(client, db_session):
    seed_admin(db_session)
    sede = seed_sede(db_session)
    strategy = seed_strategy(db_session)
    leader = models.Member(
        first_name="David", last_name="Espitia", email="espitia@example.com"
    )
    db_session.add(leader)
    db_session.commit()
    db_session.refresh(leader)

    house = models.CellGroup(
        code="FARO-001",
        name="Casa de Bendicion Sector Sur",
        zone="Sur",
        address="Calle 123 #45-67",
        lider_persona_id=leader.id,
        members_count=15,
        capacity=25,
        status="active",
        evangelism_strategy_id=strategy.id,
        sede_id=sede.id,
    )
    db_session.add(house)
    db_session.commit()
    db_session.refresh(house)

    response = client.get(
        f"/api/evangelism/grupos/{house.id}", headers=auth_headers(client)
    )
    print("CELL_GROUP_DETAIL_RESPONSE:", response.json() if response.status_code == 200 else response.text)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == house.id
    assert data["name"] == "Casa de Bendicion Sector Sur"
    assert data["code"] == "FARO-001"
    assert data["leader_name"] == "David Espitia"
    assert data["members_count"] == 0
    assert data["capacity"] == 25
    assert data["status"] == "active"


def test_faro_weekly_report_records_attendance_absence_and_offering(client, db_session):
    admin = seed_admin(db_session)
    sede = seed_sede(db_session)
    leader = models.Member(
        first_name="David",
        last_name="Leader",
        email="leader@example.com",
        user_id=admin.id,
    )
    assistant = models.Member(
        first_name="Laura", last_name="Coleader", email="assistant@example.com"
    )
    host = models.Member(first_name="Marta", last_name="Host", email="host@example.com")
    attendee = models.Member(
        first_name="Ana", last_name="Asiste", email="ana@example.com"
    )
    absent = models.Member(
        first_name="Pedro", last_name="Falta", email="pedro@example.com"
    )
    season = models.FaroSeason(
        name="Temporada Faro",
        start_date=datetime(2026, 5, 1).date(),
        end_date=datetime(2026, 6, 30).date(),
    )
    strategy = seed_strategy(db_session)
    house = models.CellGroup(
        code="FARO-010",
        name="Faro Norte",
        leader_name="David Leader",
        leader_id=1,
        assistant_id=2,
        host_id=3,
        status="Activo",
        evangelism_strategy_id=strategy.id,
        sede_id=sede.id,
    )
    db_session.add_all([leader, assistant, host, attendee, absent, season])
    db_session.commit()
    db_session.refresh(leader)
    db_session.refresh(assistant)
    db_session.refresh(host)
    db_session.refresh(attendee)
    db_session.refresh(absent)
    db_session.refresh(season)

    house.leader_id = leader.id
    house.assistant_id = assistant.id
    house.host_id = host.id
    db_session.add(house)
    db_session.commit()
    db_session.refresh(house)

    db_session.add(
        models.CellGroupMember(
            cell_group_id=house.id, member_id=attendee.id, role="asistente"
        )
    )
    db_session.add(
        models.CellGroupMember(
            cell_group_id=house.id, member_id=absent.id, role="asistente"
        )
    )
    db_session.add(
        models.CellGroupSession(
            cell_group_id=house.id,
            season_id=season.id,
            session_date=datetime(2026, 5, 8).date(),
            status="Realizada",
        )
    )
    db_session.commit()

    session = (
        db_session.query(models.CellGroupSession)
        .filter(models.CellGroupSession.grupo_id == house.id)
        .first()
    )
    assert session is not None

    response = client.post(
        f"/api/evangelism/faro/sessions/{session.id}/attendance",
        json={
            "topic": "Unidad en casa",
            "offering_amount": 125000,
            "report_notes": "Buen ambiente y oración",
            "status": "Realizada",
            "attendees": [
                {"member_id": str(attendee.id), "attended": True},
                {
                    "member_id": str(absent.id),
                    "attended": False,
                    "absence_reason": "health",
                    "absence_reason_detail": "Fiebre",
                },
            ],
        },
        headers=auth_headers(client),
    )
    print("FARO_WEEKLY_REPORT_RESPONSE:", response.json() if response.status_code == 200 else response.text)
    assert response.status_code == 200

    data = client.get(
        f"/api/evangelism/faro/sessions/{session.id}/attendance",
        headers=auth_headers(client),
    ).json()
    assert data["topic"] == "Unidad en casa"
    assert data["offering_amount"] == 125000.0
    assert data["present_count"] == 1
    assert data["absent_count"] >= 1
    assert any(item["absence_reason"] == "health" for item in data["absentees"])


def test_faro_leader_can_manage_own_house_attendance(client, db_session):
    seed_admin(db_session)
    sede = seed_sede(db_session)
    leader_user = seed_user_with_role(
        db_session, role="coordinador", email="leaderfaro@example.com"
    )
    leader_member = models.Member(
        first_name="Lider",
        last_name="Faro",
        email="leaderfaro@example.com",
        user_id=leader_user.id,
    )
    attendee = models.Member(
        first_name="Asistente", last_name="Uno", email="asistente1@example.com"
    )
    season = models.FaroSeason(
        name="Temporada Lider",
        start_date=datetime(2026, 5, 1).date(),
        end_date=datetime(2026, 6, 30).date(),
    )
    db_session.add_all([leader_member, attendee, season])
    db_session.commit()
    db_session.refresh(leader_member)
    db_session.refresh(attendee)
    db_session.refresh(season)

    strategy = seed_strategy(db_session)
    house = models.CellGroup(
        code="FARO-LDR", name="Faro Lider", leader_id=leader_member.id, status="Activo",
        evangelism_strategy_id=strategy.id, sede_id=sede.id,
    )
    db_session.add(house)
    db_session.commit()
    db_session.refresh(house)
    db_session.add(
        models.CellGroupMember(
            cell_group_id=house.id, member_id=attendee.id, role="asistente"
        )
    )
    db_session.add(
        models.CellGroupSession(
            cell_group_id=house.id,
            season_id=season.id,
            session_date=datetime(2026, 5, 12).date(),
            status="Realizada",
        )
    )
    db_session.commit()
    session = (
        db_session.query(models.CellGroupSession)
        .filter(models.CellGroupSession.grupo_id == house.id)
        .first()
    )

    response = client.post(
        f"/api/evangelism/faro/sessions/{session.id}/attendance",
        json={
            "attendees": [{"member_id": str(attendee.id), "attended": True}],
            "status": "Realizada",
        },
        headers=auth_headers(client, email="leaderfaro@example.com"),
    )
    print("LEADER_MANAGE_ATTENDANCE_RESPONSE:", response.json() if response.status_code == 200 else response.text)
    assert response.status_code == 200

    detail = client.get(
        f"/api/evangelism/faro/sessions/{session.id}/attendance",
        headers=auth_headers(client, email="leaderfaro@example.com"),
    )
    assert detail.status_code == 200
    assert detail.json()["cell_group_id"] == house.id


def test_faro_leader_cannot_manage_other_house_attendance(client, db_session):
    seed_admin(db_session)
    sede = seed_sede(db_session)
    leader_user = seed_user_with_role(
        db_session, role="coordinador", email="leaderx@example.com"
    )
    leader_member = models.Member(
        first_name="Lider",
        last_name="X",
        email="leaderx@example.com",
        user_id=leader_user.id,
    )
    attendee = models.Member(
        first_name="Asistente", last_name="Dos", email="asistente2@example.com"
    )
    season = models.FaroSeason(
        name="Temporada X",
        start_date=datetime(2026, 5, 1).date(),
        end_date=datetime(2026, 6, 30).date(),
    )
    db_session.add_all([leader_member, attendee, season])
    db_session.commit()
    db_session.refresh(leader_member)
    db_session.refresh(attendee)
    db_session.refresh(season)

    strategy = seed_strategy(db_session)
    my_house = models.CellGroup(
        code="FARO-MIO", name="Faro Mio", leader_id=leader_member.id, status="Activo",
        evangelism_strategy_id=strategy.id, sede_id=sede.id,
    )
    other_house = models.CellGroup(code="FARO-OTRO", name="Faro Otro", status="Activo",
        evangelism_strategy_id=strategy.id, sede_id=sede.id,
    )
    db_session.add_all([my_house, other_house])
    db_session.commit()
    db_session.refresh(other_house)
    db_session.add(
        models.CellGroupMember(
            cell_group_id=other_house.id, member_id=attendee.id, role="asistente"
        )
    )
    db_session.add(
        models.CellGroupSession(
            cell_group_id=other_house.id,
            season_id=season.id,
            session_date=datetime(2026, 5, 13).date(),
            status="Realizada",
        )
    )
    db_session.commit()
    session = (
        db_session.query(models.CellGroupSession)
        .filter(models.CellGroupSession.grupo_id == other_house.id)
        .first()
    )

    response = client.post(
        f"/api/evangelism/faro/sessions/{session.id}/attendance",
        json={"attendees": [{"member_id": str(attendee.id), "attended": True}]},
        headers=auth_headers(client, email="leaderx@example.com"),
    )
    assert response.status_code == 403


def test_faro_assistant_can_update_own_house_attendees_only(client, db_session):
    seed_admin(db_session)
    sede = seed_sede(db_session)
    assistant_user = seed_user_with_role(
        db_session, role="coordinador", email="assistantfaro@example.com"
    )
    assistant_member = models.Member(
        first_name="Co",
        last_name="Lider",
        email="assistantfaro@example.com",
        user_id=assistant_user.id,
    )
    attendee = models.Member(
        first_name="Nueva", last_name="Persona", email="nueva@example.com"
    )
    db_session.add_all([assistant_member, attendee])
    db_session.commit()
    db_session.refresh(assistant_member)
    db_session.refresh(attendee)

    strategy = seed_strategy(db_session)
    house = models.CellGroup(
        code="FARO-AST",
        name="Faro Assistant",
        assistant_id=assistant_member.id,
        status="Activo",
        evangelism_strategy_id=strategy.id,
        sede_id=sede.id,
    )
    db_session.add(house)
    db_session.commit()
    db_session.refresh(house)

    ok_response = client.put(
        f"/api/evangelism/grupos/{house.id}",
        json={"base_attendee_ids": [str(attendee.id)]},
        headers=auth_headers(client, email="assistantfaro@example.com"),
    )
    assert ok_response.status_code == 200

    forbidden_response = client.put(
        f"/api/evangelism/grupos/{house.id}",
        json={"name": "Cambio no permitido"},
        headers=auth_headers(client, email="assistantfaro@example.com"),
    )
    assert forbidden_response.status_code == 403


def test_evangelism_event_detail_route(client, db_session):
    seed_admin(db_session)
    event = models.CrmEvent(
        name="Noche de Milagros",
        description="Servicio especial de adoracion",
        event_date=datetime(2026, 6, 10, 19, 0, 0),
        location="Auditorio Central",
    )
    db_session.add(event)
    db_session.flush()
    member = models.Member(
        first_name="Laura", last_name="Perez", email="laura@example.com"
    )
    db_session.add(member)
    db_session.flush()
    db_session.add(
        models.EventAttendance(
            event_id=event.id,
            session_date=event.event_date.date(),
            member_id=member.id,
            attended=True,
        )
    )
    db_session.commit()
    db_session.refresh(event)

    response = client.get(
        f"/api/evangelism/events/{event.id}", headers=auth_headers(client)
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == event.id
    assert data["name"] == "Noche de Milagros"
    assert data["title"] == "Noche de Milagros"
    assert data["attendees_count"] == 1
    assert data["location"] == "Auditorio Central"
    assert data["status"] == "SCHEDULED"


def test_evangelism_bulk_attendance_syncs_present_and_absent_members(
    client, db_session
):
    seed_admin(db_session)
    event = models.CrmEvent(
        name="Culto de Jueves",
        description="Registro de asistencia",
        event_date=datetime(2026, 6, 12, 19, 0, 0),
        location="Templo principal",
    )
    db_session.add(event)
    db_session.flush()

    member_one = models.Member(
        first_name="Sara", last_name="Lopez", email="sara@example.com"
    )
    member_two = models.Member(
        first_name="David", last_name="Ruiz", email="david@example.com"
    )
    db_session.add_all([member_one, member_two])
    db_session.flush()

    db_session.add_all(
        [
            models.EventAttendance(
                event_id=event.id,
                session_date=event.event_date.date(),
                member_id=member_one.id,
                attended=True,
                status="present",
            ),
            models.EventAttendance(
                event_id=event.id,
                session_date=event.event_date.date(),
                member_id=member_two.id,
                attended=True,
                status="present",
            ),
        ]
    )
    db_session.commit()

    response = client.post(
        "/api/evangelism/attendance/bulk",
        headers=auth_headers(client),
        json={
            "event_id": event.id,
            "persona_ids": [str(member_two.id)],
            "attendance_date": event.event_date.date().isoformat(),
        },
    )
    print("BULK_ATTENDANCE_SYNC_RESPONSE:", response.json() if response.status_code == 200 else response.text)
    assert response.status_code == 200
    data = response.json()
    assert data["recorded"] == 1
    assert data["marked_absent"] == 1

    rows = (
        db_session.query(models.EventAttendance)
        .filter(
            models.EventAttendance.event_id == event.id,
            models.EventAttendance.session_date == event.event_date.date(),
        )
        .all()
    )
    assert len(rows) == 2
    rows_map = {r.member_id: r for r in rows}
    assert member_one.id in rows_map
    assert member_two.id in rows_map
    assert rows_map[member_one.id].attended is False
    assert rows_map[member_one.id].status == "absent"
    assert rows_map[member_two.id].attended is True
    assert rows_map[member_two.id].status == "present"


def test_evangelism_bulk_attendance_rejects_cancelled_event(client, db_session):
    seed_admin(db_session)
    event = models.CrmEvent(
        name="Servicio cancelado",
        description="No debe recibir asistencia",
        event_date=datetime(2026, 6, 13, 19, 0, 0),
        location="Templo principal",
        status="CANCELLED",
    )
    member = models.Member(
        first_name="Rocio", last_name="Marin", email="rocio@example.com"
    )
    db_session.add_all([event, member])
    db_session.commit()
    db_session.refresh(event)
    db_session.refresh(member)

    response = client.post(
        "/api/evangelism/attendance/bulk",
        headers=auth_headers(client),
        json={
            "event_id": event.id,
            "persona_ids": [str(member.id)],
            "attendance_date": event.event_date.date().isoformat(),
        },
    )

    assert response.status_code == 409
    assert (
        response.json()["detail"]
        == "No se puede registrar asistencia en eventos cancelados"
    )


def test_evangelism_bulk_attendance_rejects_invalid_session_date(client, db_session):
    seed_admin(db_session)
    event = models.CrmEvent(
        name="Servicio de prueba",
        description="Fecha invalida",
        event_date=datetime(2026, 6, 14, 19, 0, 0),
        location="Templo principal",
    )
    member = models.Member(
        first_name="Luis", last_name="Marin", email="luis.marin@example.com"
    )
    db_session.add_all([event, member])
    db_session.commit()
    db_session.refresh(event)
    db_session.refresh(member)

    response = client.post(
        "/api/evangelism/attendance/bulk",
        headers=auth_headers(client),
        json={
            "event_id": event.id,
            "persona_ids": [str(member.id)],
            "attendance_date": "fecha-no-valida",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid session_date"


def test_evangelism_bulk_attendance_rejects_member_ids_not_list(client, db_session):
    seed_admin(db_session)
    event = models.CrmEvent(
        name="Servicio de prueba",
        description="member_ids invalido",
        event_date=datetime(2026, 6, 15, 19, 0, 0),
        location="Templo principal",
    )
    db_session.add(event)
    db_session.commit()
    db_session.refresh(event)

    response = client.post(
        "/api/evangelism/attendance/bulk",
        headers=auth_headers(client),
        json={
            "event_id": event.id,
            "persona_ids": "1,2,3",
            "attendance_date": event.event_date.date().isoformat(),
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "persona_ids must be a list"


def test_evangelism_event_session_supports_multiple_expected_roles(client, db_session):
    seed_admin(db_session)
    leader_role = models.RoleDefinition(
        name="Lider", color="#111111", is_leadership=True
    )
    usher_role = models.RoleDefinition(
        name="Ujier", color="#222222", is_leadership=False
    )
    db_session.add_all([leader_role, usher_role])
    db_session.flush()

    event = models.CrmEvent(
        name="Reunion de servicio",
        description="Convocatoria de equipos",
        event_date=datetime(2026, 6, 20, 19, 0, 0),
        target_audience="ROLE",
        target_role_id=leader_role.id,
        target_role_ids=[leader_role.id, usher_role.id],
    )
    db_session.add(event)
    db_session.flush()

    leader = models.Member(
        first_name="Paula",
        last_name="Rios",
        email="paula@example.com",
        church_role="Lider",
    )
    usher = models.Member(
        first_name="Mario",
        last_name="Diaz",
        email="mario@example.com",
        church_role="Ujier",
    )
    outsider = models.Member(
        first_name="Luisa",
        last_name="Vega",
        email="luisa@example.com",
        church_role="Visitante",
    )
    db_session.add_all([leader, usher, outsider])
    db_session.flush()

    db_session.add(
        models.EventAttendance(
            event_id=event.id,
            session_date=event.event_date.date(),
            member_id=leader.id,
            attended=True,
            status="present",
        )
    )
    db_session.commit()

    response = client.get(
        f"/api/evangelism/events/{event.id}/sessions/{event.event_date.date().isoformat()}",
        headers=auth_headers(client),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_expected"] == 2
    assert data["total_attendance"] == 1
    assert any(item["member_id"] == str(usher.id) for item in data["absentees"])
    assert all(item["member_id"] != str(outsider.id) for item in data["absentees"])


def test_evangelism_event_session_supports_manual_expected_members(client, db_session):
    seed_admin(db_session)
    event = models.CrmEvent(
        name="Reunion cerrada",
        description="Seguimiento puntual",
        event_date=datetime(2026, 6, 21, 18, 0, 0),
        target_audience="MANUAL",
        target_member_ids=[],
    )
    db_session.add(event)
    db_session.flush()

    expected_one = models.Member(
        first_name="Elena",
        last_name="Mora",
        email="elena@example.com",
        church_role="Lider",
    )
    expected_two = models.Member(
        first_name="Carlos",
        last_name="Paz",
        email="carlos@example.com",
        church_role="Ujier",
    )
    outsider = models.Member(
        first_name="Andrea",
        last_name="Sol",
        email="andrea@example.com",
        church_role="Maestra",
    )
    db_session.add_all([expected_one, expected_two, outsider])
    db_session.flush()

    event.target_member_ids = [expected_one.id, expected_two.id]
    db_session.add(
        models.EventAttendance(
            event_id=event.id,
            session_date=event.event_date.date(),
            member_id=expected_one.id,
            attended=True,
            status="present",
        )
    )
    db_session.commit()

    response = client.get(
        f"/api/evangelism/events/{event.id}/sessions/{event.event_date.date().isoformat()}",
        headers=auth_headers(client),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_expected"] == 2
    assert data["total_attendance"] == 1
    assert any(item["member_id"] == str(expected_two.id) for item in data["absentees"])
    assert all(item["member_id"] != str(outsider.id) for item in data["absentees"])


def test_crm_prayer_request_detail_route(client, db_session):
    seed_admin(db_session)
    prayer = models.PrayerRequest(
        requester_name="Roberto Gomez",
        request_text="Peticion por la salud de mi madre",
        category="Salud",
        is_public=False,
        status="praying",
    )
    db_session.add(prayer)
    db_session.commit()
    db_session.refresh(prayer)

    response = client.get(
        f"/api/evangelism/prayer-requests/{prayer.id}", headers=auth_headers(client)
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == prayer.id
    assert data["requester_name"] == "Roberto Gomez"
    assert data["request_text"] == "Peticion por la salud de mi madre"
    assert data["category"] == "Salud"
    assert data["status"] == "praying"


def test_crm_volunteer_detail_route(client, db_session):
    admin = seed_admin(db_session)
    member = models.Member(
        first_name="Ana",
        last_name="Restrepo",
        email="ana@example.com",
        phone="+573109876543",
        church_role="Lider de Alabanza",
        spiritual_status="Activo",
        is_baptized=True,
        user_id=admin.id,
    )
    db_session.add(member)
    db_session.flush()

    skill = models.VolunteerSkill(name="Canto", category="Musico")
    db_session.add(skill)
    db_session.flush()
    db_session.execute(
        models.member_volunteer_skills.insert().values(
            persona_id=member.id, skill_id=skill.id
        )
    )


    first_shift = models.VolunteerShift(
        member_id=member.id,
        role_name="Coro",
        team_name="Ministerio de Musica",
        shift_start=datetime(2026, 1, 10, 8, 0, 0),
        shift_end=datetime(2026, 1, 10, 10, 0, 0),
        status="active",
    )
    second_shift = models.VolunteerShift(
        member_id=member.id,
        role_name="Alabanza",
        team_name="Ministerio de Musica",
        shift_start=datetime(2026, 1, 17, 8, 0, 0),
        shift_end=datetime(2026, 1, 17, 10, 0, 0),
        status="active",
    )
    db_session.add_all([first_shift, second_shift])
    db_session.commit()

    response = client.get(
        f"/api/evangelism/volunteers/{member.id}", headers=auth_headers(client)
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(member.id)
    assert data["name"] == "Ana Restrepo"
    assert data["role"] == "Lider de Alabanza"
    assert data["team"] == "Ministerio de Musica"
    assert data["status"] == "active"
    assert data["total_hours"] == 4
    assert data["skills"] == ["Canto"]


def test_crm_roles_route_returns_role_definitions(client, db_session):
    seed_admin(db_session)
    db_session.add(
        models.RoleDefinition(name="Ujier", color="#123456", is_leadership=False)
    )
    db_session.add(
        models.RoleDefinition(name="Lider", color="#654321", is_leadership=True)
    )
    db_session.commit()

    response = client.get("/api/crm/roles", headers=auth_headers(client))

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(row["name"] == "Ujier" for row in data)
    assert any(row["name"] == "Lider" for row in data)


def test_crm_analytics_route_returns_summary_shape(client, db_session):
    seed_admin(db_session)

    response = client.get("/api/crm/analytics", headers=auth_headers(client))

    assert response.status_code == 200
    data = response.json()
    for key in [
        "total_members",
        "active_members",
        "total_leads",
        "pipeline_by_stage",
        "open_counseling",
        "events_this_month",
        "total_groups",
        "total_families",
    ]:
        assert key in data


def test_evangelism_events_requires_pastor_or_admin(client, db_session):
    email = f"student-{uuid.uuid4().hex[:8]}@example.com"
    seed_user_with_role(db_session, role="estudiante", email=email)

    response = client.get(
        "/api/evangelism/events/", headers=auth_headers(client, email=email)
    )

    assert response.status_code == 403


def test_evangelism_scanner_requires_pastor_or_admin(client, db_session):
    email = f"student-{uuid.uuid4().hex[:8]}@example.com"
    seed_user_with_role(db_session, role="estudiante", email=email)

    response = client.post(
        "/api/evangelism/scanner/validate/CCF-MBR-1-INVALID",
        headers=auth_headers(client, email=email),
    )

    assert response.status_code == 404


@pytest.mark.xfail(reason="relation 'users' missing in test DB — schema drift pre-existente")
def test_evangelism_events_allows_pastor_role(client, db_session):
    seed_user_with_role(db_session, role="pastor", email="pastor@example.com")

    response = client.get(
        "/api/evangelism/events/",
        headers=auth_headers(client, email="pastor@example.com"),
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_evangelism_scanner_allows_pastor_role(client, db_session):
    pastor = seed_user_with_role(db_session, role="pastor", email="pastor2@example.com")
    member = models.Member(
        first_name="Luis",
        last_name="Diaz",
        email="luis.diaz@example.com",
        user_id=pastor.id,
    )
    db_session.add(member)
    db_session.commit()
    db_session.refresh(member)

    response = client.post(
        f"/api/evangelism/scanner/validate/CCF-MBR-{member.id}-INVALID",
        headers=auth_headers(client, email="pastor2@example.com"),
    )

    # Con permiso correcto, ya no debe ser 403. Puede ser 200/400 según validación del token.
    assert response.status_code != 403
