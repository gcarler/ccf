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


