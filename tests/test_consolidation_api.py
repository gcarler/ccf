from datetime import datetime

from backend import models
from backend.core.security import get_password_hash


def seed_admin(db_session, email="admin@example.com", password="secret123"):
    user = models.User(
        username="admin",
        email=email,
        password_hash=get_password_hash(password),
        role="admin",
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


def test_consolidation_flow_creates_case_assignment_and_follow_up(client, db_session):
    admin = seed_admin(db_session)
    pastor = models.Member(
        first_name="Pedro",
        last_name="Pastor",
        email="pedro@example.com",
        user_id=admin.id,
    )
    leader = models.Member(
        first_name="Laura", last_name="Leader", email="laura@example.com"
    )
    member = models.Member(first_name="Ana", last_name="Nueva", email="ana@example.com")
    db_session.add_all([pastor, leader, member])
    db_session.commit()
    db_session.refresh(pastor)
    db_session.refresh(leader)
    db_session.refresh(member)

    headers = auth_headers(client)

    position_response = client.post(
        "/api/crm/positions",
        json={
            "name": "Pastor de Consolidación",
            "description": "Supervisa visitas y consejería",
            "category": "consolidation",
            "is_active": True,
        },
        headers=headers,
    )
    assert position_response.status_code == 200
    position_id = position_response.json()["id"]

    member_position_response = client.post(
        f"/api/crm/personas-legacy/{pastor.id}/positions",
        json={
            "persona_id": str(pastor.id),
            "position_id": position_id,
            "start_date": datetime(2026, 5, 1).isoformat(),
            "is_active": True,
        },
        headers=headers,
    )
    print("MEMBER_POSITION_RESPONSE:", member_position_response.json())
    assert member_position_response.status_code == 200

    case_response = client.post(
        "/api/crm/consolidation/cases",
        json={
            "persona_id": str(member.id),
            "stage": "new",
            "status": "active",
            "source": "public register",
        },
        headers=headers,
    )
    print("CASE_RESPONSE:", case_response.json())
    assert case_response.status_code == 200
    case_id = case_response.json()["id"]

    assignment_response = client.post(
        f"/api/crm/consolidation/cases/{case_id}/assignments",
        json={
            "case_id": case_id,
            "assigned_by_id": str(pastor.id),
            "assigned_to_id": str(leader.id),
            "reason": "Seguimiento semanal",
            "priority": "high",
            "status": "active",
        },
        headers=headers,
    )
    assert assignment_response.status_code == 200
    assignment_id = assignment_response.json()["id"]

    interaction_response = client.post(
        f"/api/crm/consolidation/cases/{case_id}/interactions",
        json={
            "case_id": case_id,
            "performed_by_id": str(pastor.id),
            "interaction_type": "visit",
            "result": "ok",
            "notes": "Primera visita",
        },
        headers=headers,
    )
    assert interaction_response.status_code == 200

    task_response = client.post(
        f"/api/crm/consolidation/cases/{case_id}/tasks",
        json={
            "case_id": case_id,
            "assignment_id": assignment_id,
            "title": "Llamar el jueves",
            "status": "pending",
        },
        headers=headers,
    )
    assert task_response.status_code == 200

    profile_response = client.get(
        f"/api/crm/personas-legacy/{member.id}/consolidation", headers=headers
    )
    assert profile_response.status_code == 200
    profile = profile_response.json()
    assert profile["persona"]["id"] == str(member.id)
    assert profile["cases"][0]["assignments_count"] == 1
    assert profile["cases"][0]["interactions_count"] == 1
    assert profile["cases"][0]["open_tasks_count"] == 1
