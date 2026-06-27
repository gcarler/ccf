from tests.conftest import auth_headers, seed_admin, seed_user_with_role


def test_admin_users_uuid_crud(client, db_session):
    admin, _, _ = seed_admin(db_session)
    user, _, _ = seed_user_with_role(
        db_session,
        role_name="persona",
        email="persona-change@test.com",
        password="secret123",
    )
    headers = auth_headers(client, email=admin.email, password="testpass123")

    get_resp = client.get(f"/api/admin/users/{user.id}", headers=headers)
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["id"] == str(user.id)
    assert data["email"] == "persona-change@test.com"
    assert data["is_active"] is True

    patch_resp = client.patch(
        f"/api/admin/users/{user.id}",
        headers=headers,
        json={"email": "persona-updated@test.com", "is_active": False},
    )
    assert patch_resp.status_code == 200
    patch_data = patch_resp.json()
    assert patch_data["email"] == "persona-updated@test.com"
    assert patch_data["is_active"] is False

    from backend.models_auth import RolPlataforma

    editor_role = db_session.query(RolPlataforma).filter(RolPlataforma.nombre == "EDITOR").first()
    if not editor_role:
        editor_role = RolPlataforma(
            nombre="EDITOR",
            permisos={"crm:read": "allow", "crm:edit": "allow"},
        )
        db_session.add(editor_role)
        db_session.commit()

    role_patch_resp = client.patch(
        f"/api/admin/users/{user.id}",
        headers=headers,
        json={"rol_plataforma_id": str(editor_role.id)},
    )
    assert role_patch_resp.status_code == 200
    role_patch_data = role_patch_resp.json()
    assert role_patch_data["rol_plataforma_id"] == str(editor_role.id)
    assert role_patch_data["role_id"] == str(editor_role.id)

    alias_role_resp = client.patch(
        f"/api/admin/users/{user.id}/role",
        headers=headers,
        params={"role_id": str(editor_role.id)},
    )
    assert alias_role_resp.status_code == 200
    alias_role_data = alias_role_resp.json()
    assert alias_role_data["role_id"] == str(editor_role.id)
    assert alias_role_data["user"]["rol_plataforma_id"] == str(editor_role.id)

    delete_resp = client.delete(f"/api/admin/users/{user.id}", headers=headers)
    assert delete_resp.status_code == 204

    get_after_delete = client.get(f"/api/admin/users/{user.id}", headers=headers)
    assert get_after_delete.status_code == 200
    assert get_after_delete.json()["is_active"] is False
