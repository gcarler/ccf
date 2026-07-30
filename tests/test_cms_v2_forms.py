"""Unit and integration tests for Native Contact Forms Backend (R1-BE / Milestone 1).

Verifies:
  - Admin CRUD endpoints: GET/POST/GET_ID/PATCH/PUT/DELETE on /api/cms/v2/sites/{site_key}/forms
  - Public submission endpoint: POST /api/cms/v2/public/forms/{form_id}/submit
  - Form submissions listing endpoint: GET /api/cms/v2/sites/{site_key}/forms/{form_id}/submissions
  - Error handling (404 FormNotFoundError)
"""
from __future__ import annotations

import uuid as _uuid
import pytest
from backend import models
from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin


@pytest.fixture
def admin_client(client, db_session):
    admin, _, _ = _seed_admin(db_session)
    return client, _auth_headers(client, email=admin.email, password="testpass123")


@pytest.fixture
def cms_site(db_session):
    site = models.CmsSite(
        id=_uuid.uuid4(),
        site_key="faro_forms",
        name="El Faro Forms",
        base_path="/faro_forms",
        is_active=True,
    )
    db_session.add(site)
    db_session.commit()
    return site


class TestCmsFormsAdminApi:
    def test_create_form(self, admin_client, cms_site):
        c, h = admin_client
        payload = {
            "name": "Formulario de Contacto",
            "description": "Formulario principal de contacto",
            "fields": [
                {"id": "f1", "type": "text", "label": "Nombre", "required": True},
                {"id": "f2", "type": "email", "label": "Correo", "required": True},
            ],
            "submit_button_text": "Enviar Consulta",
            "success_message": "¡Gracias por tu mensaje!",
            "notify_emails": ["admin@ccf.org"],
            "is_active": True,
        }
        resp = c.post(f"/api/cms/v2/sites/{cms_site.site_key}/forms", json=payload, headers=h)
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["name"] == "Formulario de Contacto"
        assert data["description"] == "Formulario principal de contacto"
        assert len(data["fields"]) == 2
        assert data["submit_button_text"] == "Enviar Consulta"
        assert data["success_message"] == "¡Gracias por tu mensaje!"
        assert data["notify_emails"] == ["admin@ccf.org"]
        assert data["is_active"] is True
        assert "id" in data

    def test_list_forms(self, admin_client, cms_site, db_session):
        c, h = admin_client
        form1 = models.CmsForm(
            site_id=cms_site.id,
            name="Form 1",
            fields=[],
            is_active=True,
        )
        form2 = models.CmsForm(
            site_id=cms_site.id,
            name="Form 2",
            fields=[],
            is_active=False,
        )
        db_session.add_all([form1, form2])
        db_session.commit()

        # List all
        resp = c.get(f"/api/cms/v2/sites/{cms_site.site_key}/forms", headers=h)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 2

        # List only active
        resp_active = c.get(f"/api/cms/v2/sites/{cms_site.site_key}/forms?only_active=true", headers=h)
        assert resp_active.status_code == 200
        active_data = resp_active.json()
        assert all(f["is_active"] for f in active_data)

    def test_get_form_by_id(self, admin_client, cms_site, db_session):
        c, h = admin_client
        form = models.CmsForm(
            site_id=cms_site.id,
            name="Form ID Test",
            fields=[],
        )
        db_session.add(form)
        db_session.commit()

        resp = c.get(f"/api/cms/v2/sites/{cms_site.site_key}/forms/{form.id}", headers=h)
        assert resp.status_code == 200
        assert resp.json()["name"] == "Form ID Test"

    def test_get_form_not_found(self, admin_client, cms_site):
        c, h = admin_client
        random_id = _uuid.uuid4()
        resp = c.get(f"/api/cms/v2/sites/{cms_site.site_key}/forms/{random_id}", headers=h)
        assert resp.status_code == 404

    def test_update_form_patch_and_put(self, admin_client, cms_site, db_session):
        c, h = admin_client
        form = models.CmsForm(
            site_id=cms_site.id,
            name="Original Form",
            description="Old Description",
            is_active=True,
        )
        db_session.add(form)
        db_session.commit()

        # PATCH update
        patch_payload = {"name": "Patched Form Name", "is_active": False}
        resp = c.patch(f"/api/cms/v2/sites/{cms_site.site_key}/forms/{form.id}", json=patch_payload, headers=h)
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Patched Form Name"
        assert data["is_active"] is False

        # PUT update
        put_payload = {"name": "PUT Form Name", "description": "New Description", "is_active": True}
        resp_put = c.put(f"/api/cms/v2/sites/{cms_site.site_key}/forms/{form.id}", json=put_payload, headers=h)
        assert resp_put.status_code == 200
        data_put = resp_put.json()
        assert data_put["name"] == "PUT Form Name"
        assert data_put["description"] == "New Description"

    def test_delete_form(self, admin_client, cms_site, db_session):
        c, h = admin_client
        form = models.CmsForm(
            site_id=cms_site.id,
            name="To Delete Form",
            fields=[],
        )
        db_session.add(form)
        db_session.commit()

        resp = c.delete(f"/api/cms/v2/sites/{cms_site.site_key}/forms/{form.id}", headers=h)
        assert resp.status_code == 204

        # Confirm deletion
        get_resp = c.get(f"/api/cms/v2/sites/{cms_site.site_key}/forms/{form.id}", headers=h)
        assert get_resp.status_code == 404


class TestCmsFormsPublicAndSubmissionsApi:
    def test_submit_public_form_success(self, client, cms_site, db_session):
        form = models.CmsForm(
            site_id=cms_site.id,
            name="Public Contact Form",
            success_message="¡Gracias por tu mensaje!",
            notify_emails=["notify@ccf.org"],
            is_active=True,
        )
        db_session.add(form)
        db_session.commit()

        submission_payload = {
            "data": {
                "nombre": "Juan Pérez",
                "email": "juan@example.com",
                "mensaje": "Hola, quisiera solicitar información.",
            }
        }
        resp = client.post(f"/api/cms/v2/public/forms/{form.id}/submit", json=submission_payload)
        assert resp.status_code == 200, resp.text
        res_data = resp.json()
        assert res_data["success"] is True
        assert res_data["message"] == "¡Gracias por tu mensaje!"
        assert "submission_id" in res_data

        # Verify recorded submission via DB query
        sub = db_session.query(models.CmsFormSubmission).filter_by(form_id=form.id).first()
        assert sub is not None
        assert sub.data["nombre"] == "Juan Pérez"
        assert sub.data["email"] == "juan@example.com"

    def test_submit_inactive_form_fails(self, client, cms_site, db_session):
        form = models.CmsForm(
            site_id=cms_site.id,
            name="Inactive Form",
            is_active=False,
        )
        db_session.add(form)
        db_session.commit()

        resp = client.post(f"/api/cms/v2/public/forms/{form.id}/submit", json={"data": {"msg": "test"}})
        assert resp.status_code == 404

    def test_list_form_submissions(self, admin_client, cms_site, db_session):
        c, h = admin_client
        form = models.CmsForm(
            site_id=cms_site.id,
            name="Submissions Form",
            is_active=True,
        )
        db_session.add(form)
        db_session.commit()

        # Add two submissions
        sub1 = models.CmsFormSubmission(form_id=form.id, data={"name": "Alice"}, ip_address="127.0.0.1")
        sub2 = models.CmsFormSubmission(form_id=form.id, data={"name": "Bob"}, ip_address="192.168.1.1")
        db_session.add_all([sub1, sub2])
        db_session.commit()

        resp = c.get(f"/api/cms/v2/sites/{cms_site.site_key}/forms/{form.id}/submissions?page=1&page_size=10", headers=h)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["total"] == 2
        assert data["page"] == 1
        assert data["page_size"] == 10
        assert len(data["items"]) == 2
        names = [item["data"]["name"] for item in data["items"]]
        assert "Alice" in names
        assert "Bob" in names
