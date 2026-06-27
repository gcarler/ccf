from tests.conftest import auth_headers, seed_admin


def test_admin_roles_uuid_crud(client, db_session):
    admin, _, _ = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email, password="testpass123")

    create_resp = client.post(
        "/api/admin/roles",
        headers=headers,
        json={"name": "ROL_UUID", "permissions": {"crm:read": "allow"}},
    )
    assert create_resp.status_code == 200
    created = create_resp.json()
    assert created["name"] == "ROL_UUID"

    list_resp = client.get("/api/admin/roles", headers=headers)
    assert list_resp.status_code == 200
    assert any(item["name"] == "ROL_UUID" for item in list_resp.json())

    role_id = created["id"]
    patch_resp = client.patch(
        f"/api/admin/roles/{role_id}",
        headers=headers,
        json={"permissions": {"crm:read": "allow", "crm:edit": "allow"}},
    )
    assert patch_resp.status_code == 200

    delete_resp = client.delete(f"/api/admin/roles/{role_id}", headers=headers)
    assert delete_resp.status_code == 204
