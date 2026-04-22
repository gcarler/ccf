from backend import crud, models, schemas
from backend.core.security import get_password_hash


def seed_user(db_session, email="pastor@example.com", role="admin"):
    user = models.User(
        username=email.split("@")[0],
        email=email,
        password_hash=get_password_hash("secret123"),
        role=role,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_member_filtering_and_update(db_session):
    seed_user(db_session)
    crud.create_member(
        db_session,
        schemas.MemberCreate(
            first_name="Ana",
            last_name="Lopez",
            email="ana@example.com",
            family_id=None,
            church_role="Servidor",
        ),
    )
    member_two = crud.create_member(
        db_session,
        schemas.MemberCreate(
            first_name="Carlos",
            last_name="Diaz",
            email="carlos@example.com",
            family_id=None,
            church_role="Miembro",
        ),
    )

    search_result = crud.get_members(db_session, search="Ana")
    assert len(search_result) == 1
    role_result = crud.get_members(db_session, role="Miembro")
    assert len(role_result) == 1

    updated = crud.update_member(
        db_session,
        member_two.id,
        schemas.MemberUpdate(phone="123456", church_role="Servidor"),
    )
    assert updated and updated.phone == "123456"


def test_pipeline_lead_create_and_update(db_session):
    pastor = seed_user(db_session, email="leadpastor@example.com")
    lead = crud.create_pipeline_lead(
        db_session,
        schemas.ConsolidationPipelineCreate(
            first_name="Maria",
            last_name="Gonzalez",
            phone="555",
            source="Web",
            stage="new",
            assigned_pastor_id=pastor.id,
        ),
    )
    assert lead.stage == "new"

    updated = crud.update_pipeline_lead(
        db_session,
        lead.id,
        schemas.ConsolidationPipelineUpdate(stage="call"),
    )
    assert updated and updated.stage == "call"

    results = crud.get_pipeline_leads(
        db_session,
        stage="call",
        assigned_pastor_id=pastor.id,
        search="Maria",
    )
    assert len(results) == 1


def test_create_pastoral_call_log(db_session):
    pastor = seed_user(db_session, email="calls@example.com")
    lead = crud.create_pipeline_lead(
        db_session,
        schemas.ConsolidationPipelineCreate(
            first_name="Luis",
            last_name="Perez",
            phone="999",
            source="Evento",
            stage="call",
            assigned_pastor_id=pastor.id,
        ),
    )
    log_entry = crud.create_pastoral_call_log(
        db_session,
        lead_id=lead.id,
        call_log=schemas.PastoralCallLogCreate(
            lead_id=lead.id,
            pastor_id=pastor.id,
            outcome="Exitosa",
        ),
    )
    assert log_entry is not None
    logs = crud.get_pastoral_call_logs(db_session, lead_id=lead.id)
    assert len(logs) == 1
