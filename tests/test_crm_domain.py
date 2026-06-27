from backend import crud, schemas
from tests.conftest import seed_admin


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
