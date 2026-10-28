"""Real two-sede regressions for the academic queries found by the platform audit."""

import uuid
from datetime import date, datetime, timezone

import pytest

from backend import models
from tests.conftest import auth_headers, seed_admin


def offering(db, sede_id):
    token = uuid.uuid4().hex[:8]
    program = models.AcademyProgram(id=uuid.uuid4(), code=token, name=token, sede_id=sede_id)
    period = models.AcademyAcademicPeriod(
        id=uuid.uuid4(),
        code=token,
        name=token,
        sede_id=sede_id,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )
    scheme = models.AcademyGradingScheme(id=uuid.uuid4(), name=token, sede_id=sede_id)
    plan = models.AcademyStudyPlan(id=uuid.uuid4(), program_id=program.id, code=token, name=token, sede_id=sede_id)
    subject = models.AcademyStudyPlanSubject(id=uuid.uuid4(), study_plan_id=plan.id, code=token, name=token)
    row = models.AcademyPeriodOffering(
        id=uuid.uuid4(),
        sede_id=sede_id,
        academic_period_id=period.id,
        grading_scheme_id=scheme.id,
        subject_id=subject.id,
    )
    db.add_all([program, period, scheme, plan, subject, row])
    db.commit()
    return row, plan, subject


@pytest.fixture
def tenants(client, db_session):
    actor, _, local = seed_admin(db_session, email="audit-local@example.com")
    _, _, foreign = seed_admin(db_session, email="audit-foreign@example.com")
    headers = auth_headers(client, email=actor.email, password="testpass123")
    return actor, local, foreign, headers


@pytest.mark.parametrize(
    "suffix",
    [
        "/admin/offerings/{id}/students",
        "/knowledge/{id}/graph",
        "/knowledge/{id}/student-progress",
        "/wellness/{id}/signals",
        "/study-groups/{id}",
        "/analytics/cohort-health/{id}",
    ],
)
def test_foreign_offering_is_blocked_even_when_child_sede_is_null(client, db_session, tenants, suffix):
    _, _, foreign, headers = tenants
    row, _, _ = offering(db_session, foreign.id)
    db_session.add(models.AcademyKnowledgeNode(offering_id=row.id, title="foreign-secret", sede_id=None))
    db_session.commit()
    response = client.get("/api/academy" + suffix.format(id=row.id), headers=headers)
    assert response.status_code == 404, response.text
    assert "foreign-secret" not in response.text


def test_foreign_subject_mutations_leave_parent_and_subject_unchanged(client, db_session, tenants):
    _, _, foreign, headers = tenants
    _, plan, subject = offering(db_session, foreign.id)
    original_name = subject.name
    response = client.patch(f"/api/academy/admin/subjects/{subject.id}", json={"name": "intrusion"}, headers=headers)
    assert response.status_code == 404
    response = client.delete(f"/api/academy/admin/subjects/{subject.id}", headers=headers)
    assert response.status_code == 404
    response = client.post(
        f"/api/academy/admin/study-plans/{plan.id}/subjects",
        json={"name": "intrusion", "code": "intrusion"},
        headers=headers,
    )
    assert response.status_code == 404
    db_session.refresh(subject)
    assert subject.name == original_name
    assert subject.deleted_at is None
    assert db_session.query(models.AcademyStudyPlanSubject).filter_by(study_plan_id=plan.id).count() == 1


def test_calendar_keeps_local_and_ministerial_rows_only(client, db_session, tenants):
    actor, local, foreign, headers = tenants
    for index, sede_id in enumerate([local.id, foreign.id, None]):
        db_session.add(
            models.AcademyCalendarEvent(
                title=f"event-{index}",
                event_type="assignment",
                sede_id=sede_id,
                created_by=actor.id,
                start_date=datetime(2026, 10, 1, tzinfo=timezone.utc),
                end_date=datetime(2026, 10, 2, tzinfo=timezone.utc),
            )
        )
    db_session.commit()
    response = client.get("/api/academy/calendar/events", headers=headers)
    assert response.status_code == 200
    assert {row["title"] for row in response.json()} == {"event-0", "event-2"}
    response = client.get(f"/api/academy/calendar/events?student_id={uuid.uuid4()}", headers=headers)
    assert response.status_code == 404


def test_cohort_health_does_not_aggregate_other_offering_nodes(client, db_session, tenants):
    actor, local, foreign, headers = tenants
    local_offering, _, _ = offering(db_session, local.id)
    foreign_offering, _, _ = offering(db_session, foreign.id)
    for row, title in [(local_offering, "local-node"), (foreign_offering, "foreign-node")]:
        node = models.AcademyKnowledgeNode(id=uuid.uuid4(), offering_id=row.id, title=title, sede_id=row.sede_id)
        db_session.add(node)
        db_session.flush()
        db_session.add(
            models.AcademyStudentNodeProgress(
                student_id=actor.id, node_id=node.id, mastery_score=0.1, sede_id=row.sede_id
            )
        )
    db_session.commit()
    response = client.get(f"/api/academy/analytics/cohort-health/{local_offering.id}", headers=headers)
    assert response.status_code == 200, response.text
    assert "local-node" in response.text
    assert "foreign-node" not in response.text


def test_ministerial_offering_remains_readable_for_a_sede_actor(client, db_session, tenants):
    _, _, _, headers = tenants
    global_offering, _, _ = offering(db_session, None)
    db_session.add(models.AcademyKnowledgeNode(offering_id=global_offering.id, title="ministerial-node", sede_id=None))
    db_session.commit()
    response = client.get(f"/api/academy/knowledge/{global_offering.id}/graph", headers=headers)
    assert response.status_code == 200, response.text
    assert "ministerial-node" in response.text


def test_mentor_inventory_keeps_local_and_ministerial_profiles_only(client, db_session, tenants):
    actor, local, foreign, headers = tenants
    foreign_actor = db_session.query(models.Persona).filter_by(sede_id=foreign.id).first()
    global_actor = models.Persona(id=uuid.uuid4(), first_name="Global", last_name="Mentor", sede_id=None)
    db_session.add(global_actor)
    db_session.flush()
    for persona, sede_id in [(actor, local.id), (foreign_actor, foreign.id), (global_actor, None)]:
        db_session.add(models.AcademyMentorProfile(mentor_persona_id=persona.id, sede_id=sede_id))
    db_session.commit()
    response = client.get("/api/academy/mentorship/available-mentors", headers=headers)
    assert response.status_code == 200, response.text
    assert {p["mentor_persona_id"] for p in response.json()} == {str(actor.id), str(global_actor.id)}


@pytest.mark.parametrize("operation", ["create", "update", "delete"])
def test_subject_mutations_require_sede_even_with_a_valid_actor_uuid(
    client, db_session, tenants, monkeypatch, operation
):
    _, _, foreign, headers = tenants
    _, plan, subject = offering(db_session, foreign.id)
    original = subject.name
    monkeypatch.setattr("backend.api.academy.get_user_sede_id", lambda db, user_id: None)
    if operation == "create":
        response = client.post(
            f"/api/academy/admin/study-plans/{plan.id}/subjects",
            json={"code": "rejected", "name": "rejected"},
            headers=headers,
        )
    elif operation == "update":
        response = client.patch(f"/api/academy/admin/subjects/{subject.id}", json={"name": "rejected"}, headers=headers)
    else:
        response = client.delete(f"/api/academy/admin/subjects/{subject.id}", headers=headers)
    assert response.status_code == 409, response.text
    db_session.refresh(subject)
    assert subject.name == original
    assert subject.deleted_at is None
    assert db_session.query(models.AcademyStudyPlanSubject).filter_by(study_plan_id=plan.id).count() == 1


def test_global_parent_does_not_expose_foreign_tenant_children(client, db_session, tenants):
    _, local, foreign, headers = tenants
    global_offering, _, _ = offering(db_session, None)
    for title, sede_id in [("global-node", None), ("local-node", local.id), ("foreign-secret", foreign.id)]:
        db_session.add(models.AcademyKnowledgeNode(offering_id=global_offering.id, title=title, sede_id=sede_id))
    db_session.commit()
    response = client.get(f"/api/academy/knowledge/{global_offering.id}/graph", headers=headers)
    assert response.status_code == 200
    assert {row["title"] for row in response.json()["nodes"]} == {"global-node", "local-node"}


def test_actor_without_sede_can_read_only_ministerial_rows(client, db_session, tenants, monkeypatch):
    _, local, foreign, headers = tenants
    row, _, _ = offering(db_session, None)
    for title, sede_id in [("global-node", None), ("local-secret", local.id), ("foreign-secret", foreign.id)]:
        db_session.add(models.AcademyKnowledgeNode(offering_id=row.id, title=title, sede_id=sede_id))
    db_session.commit()
    monkeypatch.setattr("backend.api.academy.get_user_sede_id", lambda db, user_id: None)
    response = client.get(f"/api/academy/knowledge/{row.id}/graph", headers=headers)
    assert response.status_code == 200, response.text
    assert {node["title"] for node in response.json()["nodes"]} == {"global-node"}
