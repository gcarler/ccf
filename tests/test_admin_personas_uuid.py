from tests.conftest import auth_headers_v2, seed_admin_v2, seed_user_with_role_v2


def test_admin_personas_lists_entire_person_registry(client, db_session):
    admin, _, _ = seed_admin_v2(db_session, email="admin-personas@test.com")
    user, _, _ = seed_user_with_role_v2(
        db_session,
        role_name="persona",
        email="persona-personas@test.com",
        password="secret123",
    )
    headers = auth_headers_v2(client, email=admin.email, password="testpass123")

    resp = client.get("/api/admin/personas", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    ids = {item["id"] for item in data}

    assert str(admin.id) in ids
    assert str(user.id) in ids
