"""Unit and integration tests for R2 Newsletter / Email Marketing Module (Milestone 2).

Verifies:
  - Admin CRUD endpoints for newsletters: GET/POST/GET_ID/PATCH/DELETE/SEND on /api/cms/v2/sites/{site_key}/newsletters
  - Admin CRUD endpoints for subscribers: GET/POST/GET_ID/PATCH/DELETE/IMPORT on /api/cms/v2/sites/{site_key}/subscribers
  - Public endpoints: POST /api/cms/v2/public/subscribe, POST /api/cms/v2/public/unsubscribe
  - Error handling (404 NewsletterNotFoundError, SubscriberNotFoundError)
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
        site_key="faro_newsletter",
        name="El Faro Newsletter",
        base_path="/faro_newsletter",
        is_active=True,
    )
    db_session.add(site)
    db_session.commit()
    return site


class TestCmsNewsletterAdminApi:
    def test_create_newsletter(self, admin_client, cms_site):
        c, h = admin_client
        payload = {
            "name": "Boletín Semanal",
            "subject": "Noticias de la Comunidad CCF",
            "content_html": "<h1>Bienvenidos a CCF</h1><p>Esta semana tenemos grandes eventos.</p>",
            "status": "draft",
        }
        resp = c.post(f"/api/cms/v2/sites/{cms_site.site_key}/newsletters", json=payload, headers=h)
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["name"] == "Boletín Semanal"
        assert data["subject"] == "Noticias de la Comunidad CCF"
        assert "<h1>Bienvenidos a CCF</h1>" in data["content_html"]
        assert data["status"] == "draft"
        assert data["recipient_count"] == 0
        assert "id" in data

    def test_list_newsletters(self, admin_client, cms_site, db_session):
        c, h = admin_client
        n1 = models.CmsNewsletter(
            site_id=cms_site.id,
            name="Boletín 1",
            subject="Asunto 1",
            content_html="<p>1</p>",
            status="draft",
        )
        n2 = models.CmsNewsletter(
            site_id=cms_site.id,
            name="Boletín 2",
            subject="Asunto 2",
            content_html="<p>2</p>",
            status="sent",
        )
        db_session.add_all([n1, n2])
        db_session.commit()

        resp = c.get(f"/api/cms/v2/sites/{cms_site.site_key}/newsletters", headers=h)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 2

    def test_get_newsletter_by_id(self, admin_client, cms_site, db_session):
        c, h = admin_client
        n = models.CmsNewsletter(
            site_id=cms_site.id,
            name="Boletín Unico",
            subject="Unico Asunto",
            content_html="<p>Unico</p>",
        )
        db_session.add(n)
        db_session.commit()

        resp = c.get(f"/api/cms/v2/sites/{cms_site.site_key}/newsletters/{n.id}", headers=h)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(n.id)
        assert data["name"] == "Boletín Unico"

    def test_patch_newsletter(self, admin_client, cms_site, db_session):
        c, h = admin_client
        n = models.CmsNewsletter(
            site_id=cms_site.id,
            name="Boletín Draft",
            subject="Asunto Original",
            content_html="<p>Original</p>",
            status="draft",
        )
        db_session.add(n)
        db_session.commit()

        patch_payload = {
            "name": "Boletín Editado",
            "subject": "Nuevo Asunto",
            "status": "scheduled",
        }
        resp = c.patch(
            f"/api/cms/v2/sites/{cms_site.site_key}/newsletters/{n.id}",
            json=patch_payload,
            headers=h,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Boletín Editado"
        assert data["subject"] == "Nuevo Asunto"
        assert data["status"] == "scheduled"

    def test_delete_newsletter(self, admin_client, cms_site, db_session):
        c, h = admin_client
        n = models.CmsNewsletter(
            site_id=cms_site.id,
            name="A Borrar",
            subject="Subject",
            content_html="<p>Delete</p>",
        )
        db_session.add(n)
        db_session.commit()

        resp = c.delete(f"/api/cms/v2/sites/{cms_site.site_key}/newsletters/{n.id}", headers=h)
        assert resp.status_code == 200
        assert resp.json()["success"] is True

        resp_get = c.get(f"/api/cms/v2/sites/{cms_site.site_key}/newsletters/{n.id}", headers=h)
        assert resp_get.status_code == 404

    def test_send_newsletter(self, admin_client, cms_site, db_session):
        c, h = admin_client
        # Add two active subscribers and one inactive subscriber
        s1 = models.CmsSubscriber(site_id=cms_site.id, email="sub1@test.com", is_active=True)
        s2 = models.CmsSubscriber(site_id=cms_site.id, email="sub2@test.com", is_active=True)
        s3 = models.CmsSubscriber(site_id=cms_site.id, email="sub3@test.com", is_active=False)
        n = models.CmsNewsletter(
            site_id=cms_site.id,
            name="Boletín a Enviar",
            subject="Suscripción Especial",
            content_html="<p>Contenido especial</p>",
            status="draft",
        )
        db_session.add_all([s1, s2, s3, n])
        db_session.commit()

        resp = c.post(
            f"/api/cms/v2/sites/{cms_site.site_key}/newsletters/{n.id}/send",
            headers=h,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "sent"
        assert data["recipient_count"] == 2
        assert data["sent_at"] is not None

    def test_newsletter_not_found(self, admin_client, cms_site):
        c, h = admin_client
        fake_id = _uuid.uuid4()
        resp = c.get(f"/api/cms/v2/sites/{cms_site.site_key}/newsletters/{fake_id}", headers=h)
        assert resp.status_code == 404


class TestCmsSubscribersAdminApi:
    def test_create_subscriber(self, admin_client, cms_site):
        c, h = admin_client
        payload = {
            "email": "nuevo@comunidad.org",
            "name": "Nuevo Usuario",
            "is_active": True,
            "source": "manual",
        }
        resp = c.post(f"/api/cms/v2/sites/{cms_site.site_key}/subscribers", json=payload, headers=h)
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["email"] == "nuevo@comunidad.org"
        assert data["name"] == "Nuevo Usuario"
        assert data["is_active"] is True
        assert data["source"] == "manual"
        assert "id" in data

    def test_list_subscribers(self, admin_client, cms_site, db_session):
        c, h = admin_client
        s1 = models.CmsSubscriber(site_id=cms_site.id, email="sub1_list@test.com", is_active=True)
        s2 = models.CmsSubscriber(site_id=cms_site.id, email="sub2_list@test.com", is_active=False)
        db_session.add_all([s1, s2])
        db_session.commit()

        # All subscribers
        resp = c.get(f"/api/cms/v2/sites/{cms_site.site_key}/subscribers", headers=h)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 2

        # Only active subscribers
        resp_active = c.get(f"/api/cms/v2/sites/{cms_site.site_key}/subscribers?only_active=true", headers=h)
        assert resp_active.status_code == 200
        active_data = resp_active.json()
        assert all(s["is_active"] for s in active_data)

    def test_get_subscriber_by_id(self, admin_client, cms_site, db_session):
        c, h = admin_client
        s = models.CmsSubscriber(site_id=cms_site.id, email="get_id@test.com", name="Get ID")
        db_session.add(s)
        db_session.commit()

        resp = c.get(f"/api/cms/v2/sites/{cms_site.site_key}/subscribers/{s.id}", headers=h)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(s.id)
        assert data["email"] == "get_id@test.com"

    def test_patch_subscriber(self, admin_client, cms_site, db_session):
        c, h = admin_client
        s = models.CmsSubscriber(site_id=cms_site.id, email="active@test.com", is_active=True)
        db_session.add(s)
        db_session.commit()

        resp = c.patch(
            f"/api/cms/v2/sites/{cms_site.site_key}/subscribers/{s.id}",
            json={"is_active": False, "name": "Nombre Actualizado"},
            headers=h,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_active"] is False
        assert data["name"] == "Nombre Actualizado"
        assert data["unsubscribed_at"] is not None

    def test_delete_subscriber(self, admin_client, cms_site, db_session):
        c, h = admin_client
        s = models.CmsSubscriber(site_id=cms_site.id, email="to_delete@test.com")
        db_session.add(s)
        db_session.commit()

        resp = c.delete(f"/api/cms/v2/sites/{cms_site.site_key}/subscribers/{s.id}", headers=h)
        assert resp.status_code == 200
        assert resp.json()["success"] is True

        resp_get = c.get(f"/api/cms/v2/sites/{cms_site.site_key}/subscribers/{s.id}", headers=h)
        assert resp_get.status_code == 404

    def test_import_subscribers(self, admin_client, cms_site):
        c, h = admin_client
        import_payload = {
            "csv_content": "import1@test.com, Import Uno\nimport2@test.com, Import Dos\nimport3@test.com",
        }
        resp = c.post(
            f"/api/cms/v2/sites/{cms_site.site_key}/subscribers/import",
            json=import_payload,
            headers=h,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["imported_count"] == 3
        assert data["total_subscribers"] >= 3

    def test_subscriber_not_found(self, admin_client, cms_site):
        c, h = admin_client
        fake_id = _uuid.uuid4()
        resp = c.get(f"/api/cms/v2/sites/{cms_site.site_key}/subscribers/{fake_id}", headers=h)
        assert resp.status_code == 404


class TestCmsNewsletterPublicApi:
    def test_public_subscribe(self, client, cms_site):
        payload = {
            "site_key": cms_site.site_key,
            "email": "public_user@test.com",
            "name": "Public User",
        }
        resp = client.post("/api/cms/v2/public/subscribe", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "subscriber_id" in data

    def test_public_unsubscribe(self, client, cms_site, db_session):
        s = models.CmsSubscriber(
            site_id=cms_site.id,
            email="unsub_user@test.com",
            is_active=True,
        )
        db_session.add(s)
        db_session.commit()

        payload = {
            "site_key": cms_site.site_key,
            "email": "unsub_user@test.com",
        }
        resp = client.post("/api/cms/v2/public/unsubscribe", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

        db_session.refresh(s)
        assert s.is_active is False
