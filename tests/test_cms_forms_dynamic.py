"""Tests del form builder dinámico (plan_de_form_builder, backend).

Cubre:
  - Admin: creación/actualización con tipos nuevos + settings (captcha,
    honeypot, settings_json); validación de ``fields`` al guardar.
  - GET público (CmsFormPublicRead): no expone ``notify_emails``, expone
    ``captcha_site_key`` cuando el captcha está activo, 404 si inactivo.
  - POST /public/forms/{id}/submit/v2: validación server-side (required,
    tipos, opciones, condicionales, campos desconocidos), honeypot silencioso,
    captcha requerido/inválido/válido (mock de siteverify).
  - Unidades de ``services/form_validation.py``.
"""

from __future__ import annotations

import uuid as _uuid

import pytest

from backend import models
from backend.services import form_validation as fv
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
        site_key="faro_dyn_forms",
        name="El Faro Dynamic Forms",
        base_path="/faro_dyn_forms",
        is_active=True,
    )
    db_session.add(site)
    db_session.commit()
    return site


def _form_fields(**overrides):
    fields = [
        {"id": "nombre", "type": "text", "label": "Nombre", "required": True},
        {"id": "correo", "type": "email", "label": "Correo", "required": True},
        {"id": "tipo", "type": "select", "label": "Tipo", "required": True, "options": ["A", "B"]},
    ]
    return overrides.get("fields", fields)


@pytest.fixture
def dyn_form(cms_site, db_session):
    form = models.CmsForm(
        site_id=cms_site.id,
        name="Formulario Dinámico",
        fields=_form_fields(),
        captcha_enabled=False,
        honeypot_enabled=True,
        is_active=True,
    )
    db_session.add(form)
    db_session.commit()
    return form


class TestAdminDynamicFields:
    def test_create_with_new_types_and_settings(self, admin_client, cms_site):
        c, h = admin_client
        payload = {
            "name": "Builder Form",
            "fields": [
                {"id": "edad", "type": "number", "label": "Edad", "required": True, "min_value": 0, "max_value": 120},
                {"id": "nota", "type": "rating", "label": "Nota", "max_value": 5},
                {"id": "nivel", "type": "slider", "label": "Nivel", "min_value": 0, "max_value": 10, "step": 1},
                {"id": "archivo", "type": "file", "label": "Archivo", "max_file_mb": 5, "accept": "image/*"},
                {"id": "sec", "type": "section", "label": "Sección"},
                {"id": "pg", "type": "page", "label": "Paso 2"},
                {"id": "div", "type": "divider", "label": "Separador"},
            ],
            "captcha_enabled": True,
            "captcha_provider": "hcaptcha",
            "honeypot_enabled": False,
            "settings_json": {"layout": "card"},
        }
        resp = c.post(f"/api/cms/v2/sites/{cms_site.site_key}/forms", json=payload, headers=h)
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert len(data["fields"]) == 7
        assert data["captcha_enabled"] is True
        assert data["honeypot_enabled"] is False
        assert data["settings_json"] == {"layout": "card"}

    def test_create_invalid_field_type_422(self, admin_client, cms_site):
        c, h = admin_client
        payload = {"name": "Bad", "fields": [{"id": "x", "type": "youtube", "label": "X"}]}
        resp = c.post(f"/api/cms/v2/sites/{cms_site.site_key}/forms", json=payload, headers=h)
        assert resp.status_code == 422

    def test_create_select_without_options_422(self, admin_client, cms_site):
        c, h = admin_client
        payload = {"name": "Bad", "fields": [{"id": "x", "type": "select", "label": "X"}]}
        resp = c.post(f"/api/cms/v2/sites/{cms_site.site_key}/forms", json=payload, headers=h)
        assert resp.status_code == 422

    def test_create_missing_label_422(self, admin_client, cms_site):
        c, h = admin_client
        payload = {"name": "Bad", "fields": [{"id": "x", "type": "text", "label": ""}]}
        resp = c.post(f"/api/cms/v2/sites/{cms_site.site_key}/forms", json=payload, headers=h)
        assert resp.status_code == 422

    def test_duplicate_field_ids_422(self, admin_client, cms_site):
        c, h = admin_client
        payload = {
            "name": "Dup",
            "fields": [
                {"id": "x", "type": "text", "label": "A"},
                {"id": "x", "type": "text", "label": "B"},
            ],
        }
        resp = c.post(f"/api/cms/v2/sites/{cms_site.site_key}/forms", json=payload, headers=h)
        assert resp.status_code == 422

    def test_update_roundtrips_captcha_settings(self, admin_client, cms_site, dyn_form):
        c, h = admin_client
        resp = c.put(
            f"/api/cms/v2/sites/{cms_site.site_key}/forms/{dyn_form.id}",
            json={"captcha_enabled": True, "honeypot_enabled": False},
            headers=h,
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["captcha_enabled"] is True
        assert data["honeypot_enabled"] is False


class TestPublicGetForm:
    def test_public_get_no_notify_emails(self, client, dyn_form):
        resp = client.get(f"/api/cms/v2/public/forms/{dyn_form.id}")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "notify_emails" not in data
        assert "captcha_site_key" in data
        assert len(data["fields"]) == 3
        assert data["is_active"] is True

    def test_public_get_inactive_404(self, client, cms_site, db_session):
        form = models.CmsForm(site_id=cms_site.id, name="Inactivo", fields=[], is_active=False)
        db_session.add(form)
        db_session.commit()
        resp = client.get(f"/api/cms/v2/public/forms/{form.id}")
        assert resp.status_code == 404

    def test_public_get_captcha_site_key_exposed(self, client, cms_site, db_session, monkeypatch):
        from backend.api.cms_v2 import forms as forms_module

        class _FakeSettings:
            hcaptcha_site_key = "10000000-aaaa-bbbb-cccc-000000000001"

        monkeypatch.setattr(forms_module, "get_settings", lambda: _FakeSettings())
        form = models.CmsForm(site_id=cms_site.id, name="Con captcha", fields=[], captcha_enabled=True)
        db_session.add(form)
        db_session.commit()
        resp = client.get(f"/api/cms/v2/public/forms/{form.id}")
        assert resp.status_code == 200
        assert resp.json()["captcha_site_key"] == "10000000-aaaa-bbbb-cccc-000000000001"


class TestPublicSubmitV2:
    def test_submit_valid(self, client, dyn_form, db_session):
        resp = client.post(
            f"/api/cms/v2/public/forms/{dyn_form.id}/submit/v2",
            json={"data": {"nombre": "Ana", "correo": "ana@x.com", "tipo": "A"}, "captcha_token": None, "_hp": None},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["success"] is True
        sub = db_session.query(models.CmsFormSubmission).filter_by(form_id=dyn_form.id).first()
        assert sub is not None
        assert sub.data["correo"] == "ana@x.com"

    def test_submit_missing_required_422(self, client, dyn_form):
        resp = client.post(
            f"/api/cms/v2/public/forms/{dyn_form.id}/submit/v2",
            json={"data": {"nombre": "Ana"}, "captcha_token": None, "_hp": None},
        )
        assert resp.status_code == 422, resp.text
        assert resp.json()["detail"]["code"] == "REQUIRED_FIELD"

    def test_submit_invalid_email_422(self, client, dyn_form):
        resp = client.post(
            f"/api/cms/v2/public/forms/{dyn_form.id}/submit/v2",
            json={"data": {"nombre": "Ana", "correo": "no-un-email", "tipo": "A"}},
        )
        assert resp.status_code == 422
        assert resp.json()["detail"]["code"] == "INVALID_EMAIL"

    def test_submit_invalid_option_422(self, client, dyn_form):
        resp = client.post(
            f"/api/cms/v2/public/forms/{dyn_form.id}/submit/v2",
            json={"data": {"nombre": "Ana", "correo": "ana@x.com", "tipo": "Z"}},
        )
        assert resp.status_code == 422
        assert resp.json()["detail"]["code"] == "INVALID_OPTION"

    def test_submit_unknown_field_422(self, client, dyn_form):
        resp = client.post(
            f"/api/cms/v2/public/forms/{dyn_form.id}/submit/v2",
            json={"data": {"nombre": "Ana", "correo": "ana@x.com", "tipo": "A", "hacker": "x"}},
        )
        assert resp.status_code == 422
        assert resp.json()["detail"]["code"] == "UNKNOWN_FIELD"

    def test_submit_conditional_hidden_field_rejected(self, client, cms_site, db_session):
        form = models.CmsForm(
            site_id=cms_site.id,
            name="Condicional",
            fields=[
                {"id": "marca", "type": "select", "label": "Marca", "options": ["X", "Y"]},
                {"id": "detalle", "type": "text", "label": "Detalle", "visible_if": {"field_id": "marca", "operator": "eq", "value": "Y"}},
            ],
            is_active=True,
        )
        db_session.add(form)
        db_session.commit()
        resp = client.post(
            f"/api/cms/v2/public/forms/{form.id}/submit/v2",
            json={"data": {"marca": "X", "detalle": "oculto pero enviado"}},
        )
        assert resp.status_code == 422, resp.text
        assert resp.json()["detail"]["code"] == "HIDDEN_FIELD_SENT"

    def test_submit_conditional_valid_when_visible(self, client, cms_site, db_session):
        form = models.CmsForm(
            site_id=cms_site.id,
            name="Condicional ok",
            fields=[
                {"id": "marca", "type": "select", "label": "Marca", "options": ["X", "Y"]},
                {"id": "detalle", "type": "text", "label": "Detalle", "visible_if": {"field_id": "marca", "operator": "eq", "value": "Y"}},
            ],
            is_active=True,
        )
        db_session.add(form)
        db_session.commit()
        resp = client.post(
            f"/api/cms/v2/public/forms/{form.id}/submit/v2",
            json={"data": {"marca": "Y", "detalle": "visible"}},
        )
        assert resp.status_code == 200, resp.text
        sub = db_session.query(models.CmsFormSubmission).filter_by(form_id=form.id).first()
        assert sub.data["detalle"] == "visible"

    def test_submit_honeypot_silent(self, client, dyn_form, db_session):
        resp = client.post(
            f"/api/cms/v2/public/forms/{dyn_form.id}/submit/v2",
            json={"data": {"nombre": "Bot", "correo": "bot@x.com", "tipo": "A"}, "hp": "http://spam"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body.get("spam") is True
        # No se persiste nada.
        assert db_session.query(models.CmsFormSubmission).filter_by(form_id=dyn_form.id).count() == 0

    def test_submit_captcha_required_400(self, client, cms_site, db_session):
        form = models.CmsForm(
            site_id=cms_site.id,
            name="Con captcha",
            fields=[{"id": "x", "type": "text", "label": "X"}],
            captcha_enabled=True,
            is_active=True,
        )
        db_session.add(form)
        db_session.commit()
        resp = client.post(
            f"/api/cms/v2/public/forms/{form.id}/submit/v2",
            json={"data": {"x": "1"}},
        )
        assert resp.status_code == 400
        assert resp.json()["detail"]["code"] == "CAPTCHA_REQUIRED"

    @pytest.mark.parametrize("token,expected", [("bad-token", 400), ("good-token", 200)])
    def test_submit_captcha_verified(self, client, cms_site, db_session, monkeypatch, token, expected):
        from backend.api.cms_v2 import forms as forms_module

        async def _fake_verify(captcha_token, *, remote_ip=None):
            return captcha_token == "good-token"

        monkeypatch.setattr(forms_module, "verify_hcaptcha", _fake_verify)
        form = models.CmsForm(
            site_id=cms_site.id,
            name="Con captcha",
            fields=[{"id": "x", "type": "text", "label": "X"}],
            captcha_enabled=True,
            is_active=True,
        )
        db_session.add(form)
        db_session.commit()
        resp = client.post(
            f"/api/cms/v2/public/forms/{form.id}/submit/v2",
            json={"data": {"x": "1"}, "captcha_token": token},
        )
        assert resp.status_code == expected, resp.text
        if expected == 400:
            assert resp.json()["detail"]["code"] == "CAPTCHA_FAILED"

    def test_submit_number_below_min_422(self, client, cms_site, db_session):
        form = models.CmsForm(
            site_id=cms_site.id,
            name="Nums",
            fields=[{"id": "edad", "type": "number", "label": "Edad", "min_value": 18}],
            is_active=True,
        )
        db_session.add(form)
        db_session.commit()
        resp = client.post(
            f"/api/cms/v2/public/forms/{form.id}/submit/v2",
            json={"data": {"edad": 15}},
        )
        assert resp.status_code == 422
        assert resp.json()["detail"]["code"] == "BELOW_MIN"

    def test_submit_inactive_404(self, client, cms_site, db_session):
        form = models.CmsForm(site_id=cms_site.id, name="Inactivo", fields=[], is_active=False)
        db_session.add(form)
        db_session.commit()
        resp = client.post(f"/api/cms/v2/public/forms/{form.id}/submit/v2", json={"data": {}})
        assert resp.status_code == 404


class TestFormValidationUnit:
    def test_validate_submission_regex(self):
        fields = [{"id": "placa", "type": "text", "label": "Placa", "regex_pattern": r"^[A-Z]{3}\d{3}$", "regex_message": "Formato ABC123"}]
        clean = fv.validate_submission(fields, {"placa": "ABC123"})
        assert clean["placa"] == "ABC123"

    def test_validate_submission_regex_fail(self):
        fields = [{"id": "placa", "type": "text", "label": "Placa", "regex_pattern": r"^[A-Z]{3}\d{3}$"}]
        with pytest.raises(fv.ValidationError) as exc:
            fv.validate_submission(fields, {"placa": "abc"})
        assert exc.value.code == "REGEX_FAIL"

    def test_validate_submission_honeypot_blocks(self):
        with pytest.raises(fv.ValidationError) as exc:
            fv.validate_submission([], {}, honeypot_value="spam", honeypot_enabled=True)
        assert exc.value.code == "HONEYPOT_TRIGGERED"

    def test_validate_submission_select_multiple(self):
        fields = [{"id": "intereses", "type": "select_multiple", "label": "Intereses", "options": ["A", "B", "C"]}]
        clean = fv.validate_submission(fields, {"intereses": ["A", "C"]})
        assert clean["intereses"] == ["A", "C"]

    def test_validate_submission_rating_range(self):
        fields = [{"id": "nota", "type": "rating", "label": "Nota", "min_value": 1, "max_value": 5}]
        with pytest.raises(fv.ValidationError) as exc:
            fv.validate_submission(fields, {"nota": 9})
        assert exc.value.code == "ABOVE_MAX"
