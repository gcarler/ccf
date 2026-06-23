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

    from backend.models_kernel import PlatformRoleDefinition, PlatformRole

    editor_role = db_session.query(PlatformRoleDefinition).filter(PlatformRoleDefinition.role == PlatformRole.EDITOR).first()
    if not editor_role:
        editor_role = PlatformRoleDefinition(
            role=PlatformRole.EDITOR,
            permissions={"crm": ["read", "update"]},
        )
        db_session.add(editor_role)
        db_session.commit()

    role_patch_resp = client.patch(
        f"/api/admin/users/{user.id}",
        headers=headers,
        json={"platform_role_id": str(editor_role.id)},
    )
    assert role_patch_resp.status_code == 200
    role_patch_data = role_patch_resp.json()
    assert role_patch_data["platform_role_id"] == str(editor_role.id)
    assert role_patch_data["role_id"] == str(editor_role.id)

    alias_role_resp = client.patch(
        f"/api/admin/users/{user.id}/role",
        headers=headers,
        params={"platform_role_id": str(editor_role.id)},
    )
    assert alias_role_resp.status_code == 200
    alias_role_data = alias_role_resp.json()
    assert alias_role_data["platform_role_id"] == str(editor_role.id)
    assert alias_role_data["user"]["platform_role_id"] == str(editor_role.id)

    delete_resp = client.delete(f"/api/admin/users/{user.id}", headers=headers)
    assert delete_resp.status_code == 204

    get_after_delete = client.get(f"/api/admin/users/{user.id}", headers=headers)
    assert get_after_delete.status_code == 200
    assert get_after_delete.json()["is_active"] is False
