from backend import crud, schemas
from tests.conftest import seed_admin
import uuid


def test_persona_filtering_and_update(db_session):
    seed_admin(db_session)
    persona1 = crud.create_persona(
        db_session,
        schemas.PersonaCreate(
            first_name="Ana",
            last_name="Lopez",
            email="ana@example.com",
            family_id=None,
            church_role="Servidor",
        ),
    )
    persona2 = crud.create_persona(
        db_session,
        schemas.PersonaCreate(
            first_name="Luis",
            last_name="Garcia",
            email="luis@example.com",
            family_id=None,
            church_role="Miembro",
        ),
    )

    role_result = crud.get_personas(db_session, role="Miembro")
    assert len(role_result) >= 1

    updated = crud.update_persona(
        db_session,
        str(persona2.id),
        schemas.PersonaUpdate(church_role="Servidor"),
    )
    assert updated is not None
    assert updated.church_role == "Servidor"


def test_persona_get_by_id_and_delete(db_session):
    user, persona, sede = seed_admin(db_session)
    p = crud.create_persona(
        db_session,
        schemas.PersonaCreate(
            first_name="Delete", last_name="Me",
            email="del@test.com", church_role="Miembro",
        ),
    )
    fetched = crud.get_persona(db_session, str(p.id))
    assert fetched is not None
    assert fetched.first_name == "Delete"

    result = crud.delete_persona(db_session, str(p.id))
    assert result is True

    after = crud.get_persona(db_session, str(p.id))
    assert after is not None
    assert after.estado_vital == "INACTIVO"


def test_persona_search(db_session):
    seed_admin(db_session)
    crud.create_persona(
        db_session,
        schemas.PersonaCreate(
            first_name="Searchable", last_name="Person",
            email="search@test.com", church_role="Miembro",
        ),
    )
    results = crud.get_personas(db_session, search="Searchable")
    assert any(r.first_name == "Searchable" for r in results)


def test_crm_schema_validation(db_session):
    from backend.schemas.crm.base import (
        RoleCreate, RoleUpdate, VolunteerCreate, CounselingTicketUpdate,
        PrayerRequestCreate, CrmSettingsUpdate, GrupoUpdate, CasoCreate, MessagingSend,
    )
    role = RoleCreate(name="Test", color="red")
    assert role.name == "Test"
    assert role.color == "red"

    role_update = RoleUpdate(name="Updated")
    assert role_update.name == "Updated"

    pr = PrayerRequestCreate(requester_name="Test", request_text="Oracion")
    assert pr.requester_name == "Test"

    settings = CrmSettingsUpdate(theme="dark")
    d = settings.model_dump()
    assert d["theme"] == "dark"

    grupo = GrupoUpdate(name="Nuevo")
    assert grupo.name == "Nuevo"

    ticket = CounselingTicketUpdate(status="closed")
    assert ticket.status == "closed"

    vol = VolunteerCreate(name="Servidor", role_name="Alabanza", shift_start=None, shift_end=None)
    assert vol.name == "Servidor"

    caso = CasoCreate(persona_id=uuid.uuid4())
    assert caso.stage == "new"
    assert caso.persona_id is not None

    messaging = MessagingSend(template_id=uuid.uuid4())
    assert len(messaging.recipient_ids) == 0
    assert messaging.variables == {}
