"""Tests for the CRM resource bank (system templates catalog)."""
import uuid

import pytest

from backend.models_auth import RolPlataforma
from tests.conftest import auth_headers, seed_admin, seed_user_with_role


@pytest.fixture
def admin_data(db_session):
    user, persona, sede = seed_admin(db_session)
    return user, persona, sede


@pytest.fixture
def client_auth(client, db_session, admin_data):
    headers = auth_headers(client)
    return client, headers, admin_data


class TestCRMResourceBank:
    def test_list_system_templates(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/crm/resources/system-templates", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "categorias" in data
        assert "plantillas" in data
        assert len(data["categorias"]) > 0
        assert len(data["plantillas"]) > 0

    def test_apply_system_template(self, client_auth):
        client, headers, _ = client_auth
        # Get a template from the catalog
        resp = client.get("/api/crm/resources/system-templates", headers=headers)
        assert resp.status_code == 200
        catalog = resp.json()
        template = catalog["plantillas"][0]

        resp = client.post(
            "/api/crm/resources/system-templates/apply",
            json={"template_id": template["id"]},
            headers=headers,
        )
        assert resp.status_code == 201
        created = resp.json()
        assert created["titulo"] == template["titulo"]
        assert created["canal"] == template["canal"]
        assert created["contenido_texto"] == template["contenido_texto"]

    def test_apply_system_template_creates_category(self, client_auth):
        client, headers, _ = client_auth
        resp = client.get("/api/crm/resources/system-templates", headers=headers)
        assert resp.status_code == 200
        catalog = resp.json()
        template = catalog["plantillas"][0]

        resp = client.post(
            "/api/crm/resources/system-templates/apply",
            json={"template_id": template["id"]},
            headers=headers,
        )
        assert resp.status_code == 201

        # The category should now exist
        resp = client.get("/api/crm/resources/categorias", headers=headers)
        assert resp.status_code == 200
        categorias = resp.json()
        assert any(c["nombre"] == template["categoria"] for c in categorias)

    def test_apply_rejects_unknown_system_template(self, client_auth):
        client, headers, _ = client_auth
        resp = client.post(
            "/api/crm/resources/system-templates/apply",
            json={"template_id": "contenido-arbitrario"},
            headers=headers,
        )
        assert resp.status_code == 404

    def test_crm_reader_cannot_apply_system_template(self, client, db_session, admin_data):
        _, _, sede = admin_data
        user, _, _ = seed_user_with_role(
            db_session,
            role_name="crm_resource_reader",
            email="crm-reader@example.com",
            sede_id=sede.id,
        )
        role = db_session.query(RolPlataforma).filter_by(id=user.rol_plataforma_id).one()
        role.permisos = {"crm:read": "allow"}
        db_session.commit()
        headers = auth_headers(client, email="crm-reader@example.com")

        catalog = client.get("/api/crm/resources/system-templates", headers=headers).json()
        resp = client.post(
            "/api/crm/resources/system-templates/apply",
            json={"template_id": catalog["plantillas"][0]["id"]},
            headers=headers,
        )
        assert resp.status_code == 403

    def test_template_log_is_hidden_from_another_sede(self, client, db_session, admin_data):
        admin_headers = auth_headers(client)
        category = client.post(
            "/api/crm/resources/categorias",
            json={"nombre": "Privada", "color_ui_hex": "#123456"},
            headers=admin_headers,
        ).json()
        _, _, other_sede = seed_user_with_role(
            db_session,
            role_name="ADMIN",
            email="other-admin@example.com",
            sede_id=uuid.uuid4(),
        )
        other_headers = auth_headers(client, email="other-admin@example.com")
        created = client.post(
            "/api/crm/resources/plantillas",
            json={
                "categoria_id": category["id"],
                "titulo": "Solo otra sede",
                "canal": "EMAIL",
                "contenido_texto": "Contenido privado",
                "variables_requeridas": [],
            },
            headers=other_headers,
        )
        assert created.status_code == 201
        assert other_sede.id != admin_data[2].id

        response = client.get(
            f"/api/crm/resources/plantillas/{created.json()['id']}/bitacora",
            headers=admin_headers,
        )
        assert response.status_code == 404
