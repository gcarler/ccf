from tests.conftest import auth_headers_v2, seed_admin_v2, seed_user_with_role_v2


def test_admin_users_uuid_crud(client, db_session):
    admin, _, _ = seed_admin_v2(db_session)
    user, _, _ = seed_user_with_role_v2(
        db_session,
        role_name="member",
        email="member-change@test.com",
        password="secret123",
    )
    headers = auth_headers_v2(client, email=admin.email, password="testpass123")

    get_resp = client.get(f"/api/admin/users/{user.id}", headers=headers)
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["id"] == str(user.id)
    assert data["email"] == "member-change@test.com"
    assert data["is_active"] is True

    patch_resp = client.patch(
        f"/api/admin/users/{user.id}",
        headers=headers,
        json={"email": "member-updated@test.com", "is_active": False},
    )
    assert patch_resp.status_code == 200
    patch_data = patch_resp.json()
    assert patch_data["email"] == "member-updated@test.com"
    assert patch_data["is_active"] is False

    delete_resp = client.delete(f"/api/admin/users/{user.id}", headers=headers)
    assert delete_resp.status_code == 204

    get_after_delete = client.get(f"/api/admin/users/{user.id}", headers=headers)
    assert get_after_delete.status_code == 200
    assert get_after_delete.json()["is_active"] is False
