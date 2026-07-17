"""Tests RBAC HTTP-level para endpoints CRM.

Valida que cada endpoint devuelve 401 sin token, 403 con rol insuficiente,
y 200/201 con rol válido. Cubre los 3 grupos de guards del módulo:
- require_module_access("crm", "read"/"edit") para personas, pastoral, resources
- require_pastor_or_admin para pipelines, kanban, scenarios
- require_permission("profile:manage") para profile propio
"""

from __future__ import annotations

import uuid as _uuid

import pytest

from tests.conftest import auth_headers, seed_admin


def _seed_role(db_session, nombre, permisos):
    from backend.models_auth import RolPlataforma

    role = db_session.query(RolPlataforma).filter(RolPlataforma.nombre == nombre).first()
    if not role:
        role = RolPlataforma(id=_uuid.uuid4(), nombre=nombre, permisos=permisos)
        db_session.add(role)
        db_session.flush()
    else:
        role.permisos = permisos
        db_session.flush()
    return role


def _seed_user_with_crm_role(db_session, role_name, permisos, email, password="testpass123"):
    from backend import models as _models
    from backend.core.security import get_password_hash
    from backend.models_auth import Usuario
    from backend.models_crm import Persona

    existing = db_session.query(Usuario).filter(Usuario.email == email).first()
    if existing:
        return existing

    persona = Persona(id=_uuid.uuid4(), first_name="User", last_name="Test", email=email)
    db_session.add(persona)
    db_session.flush()

    role = _seed_role(db_session, role_name, permisos)

    sede = db_session.query(_models.Sede).first()
    if sede is None:
        sede = _models.Sede(id=_uuid.uuid4(), nombre="Sede Test", ciudad="Bogota", es_activa=True)
        db_session.add(sede)
        db_session.flush()
    persona.sede_id = sede.id

    user = Usuario(
        id=persona.id,
        sede_id=sede.id,
        username=email.split("@")[0],
        email=email,
        password_hash=get_password_hash(password),
        rol_plataforma_id=role.id,
        is_active=True,
        is_email_verified=True,
    )
    db_session.add(user)
    db_session.commit()
    return user


# ─── CRM permission maps (from seed_user_permissions.py) ─────────────────

CRM_MANAGE = {"crm:manage": "allow", "crm:edit": "allow", "crm:read": "allow", "profile:manage": "allow"}
CRM_EDIT = {"crm:edit": "allow", "crm:read": "allow", "profile:manage": "allow"}
CRM_READ = {"crm:read": "allow", "profile:manage": "allow"}
NO_CRM = {"academy:study": "allow", "profile:manage": "allow"}


# ─── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture()
def admin_h(client, db_session):
    seed_admin(db_session, email="rbac_admin@ccf.test", password="testpass123")
    return auth_headers(client, email="rbac_admin@ccf.test", password="testpass123")


@pytest.fixture()
def gestor_h(client, db_session):
    _seed_user_with_crm_role(db_session, "GESTOR", CRM_MANAGE, "rbac_gestor@ccf.test")
    return auth_headers(client, email="rbac_gestor@ccf.test", password="testpass123")


@pytest.fixture()
def editor_h(client, db_session):
    _seed_user_with_crm_role(db_session, "EDITOR", CRM_EDIT, "rbac_editor@ccf.test")
    return auth_headers(client, email="rbac_editor@ccf.test", password="testpass123")


@pytest.fixture()
def lector_h(client, db_session):
    _seed_user_with_crm_role(db_session, "LECTOR", CRM_READ, "rbac_lector@ccf.test")
    return auth_headers(client, email="rbac_lector@ccf.test", password="testpass123")


@pytest.fixture()
def miembro_h(client, db_session):
    _seed_user_with_crm_role(db_session, "MIEMBRO", NO_CRM, "rbac_miembro@ccf.test")
    return auth_headers(client, email="rbac_miembro@ccf.test", password="testpass123")


# ─── Helpers ──────────────────────────────────────────────────────────────


def _get(c, p, h=None):
    return c.get(p, **({"headers": h} if h else {}))


def _post(c, p, json=None, h=None):
    kw = {"json": json} if json else {}
    if h:
        kw["headers"] = h
    return c.post(p, **kw)


def _patch(c, p, json=None, h=None):
    kw = {"json": json} if json else {}
    if h:
        kw["headers"] = h
    return c.patch(p, **kw)


# ─── GRUPO 1: Personas ───────────────────────────────────────────────────


class TestRBACPersonas:
    def test_401_without_token(self, client):
        assert _get(client, "/api/crm/personas").status_code == 401

    def test_admin_ok(self, client, admin_h):
        assert _get(client, "/api/crm/personas", admin_h).status_code == 200

    def test_gestor_ok(self, client, gestor_h):
        assert _get(client, "/api/crm/personas", gestor_h).status_code == 200

    def test_editor_ok(self, client, editor_h):
        assert _get(client, "/api/crm/personas", editor_h).status_code == 200

    def test_miembro_403(self, client, miembro_h):
        assert _get(client, "/api/crm/personas", miembro_h).status_code == 403

    def test_post_requires_edit(self, client, miembro_h):
        assert _post(client, "/api/crm/personas", json={"first_name": "X"}, h=miembro_h).status_code == 403

    def test_post_editor_ok(self, client, editor_h):
        resp = _post(client, "/api/crm/personas",
                     json={"first_name": "Test", "last_name": "User", "email": "t@ccf.test"}, h=editor_h)
        assert resp.status_code in (200, 201)


# ─── GRUPO 2: Pipeline ───────────────────────────────────────────────────


class TestRBACPipeline:
    def test_401_without_token(self, client):
        assert _get(client, "/api/crm/pipelines").status_code == 401

    def test_admin_ok(self, client, admin_h):
        assert _get(client, "/api/crm/pipelines", admin_h).status_code == 200

    def test_miembro_403(self, client, miembro_h):
        assert _get(client, "/api/crm/pipelines", miembro_h).status_code == 403

    def test_post_miembro_403(self, client, miembro_h):
        assert _post(client, "/api/crm/pipelines", json={"name": "X"}, h=miembro_h).status_code == 403

    def test_post_admin_not_401_403(self, client, admin_h):
        resp = _post(client, "/api/crm/pipelines", json={"name": "Pipeline RBAC"}, h=admin_h)
        assert resp.status_code not in (401, 403), f"Admin should pass RBAC, got {resp.status_code}"


# ─── GRUPO 3: Automations ────────────────────────────────────────────────


class TestRBACAutomations:
    def test_401_without_token(self, client):
        assert _get(client, "/api/crm/automations/palette").status_code == 401

    def test_admin_ok(self, client, admin_h):
        assert _get(client, "/api/crm/automations/palette", admin_h).status_code == 200

    def test_gestor_ok(self, client, gestor_h):
        assert _get(client, "/api/crm/automations/palette", gestor_h).status_code == 200

    def test_editor_ok(self, client, editor_h):
        assert _get(client, "/api/crm/automations/palette", editor_h).status_code == 200

    def test_miembro_403(self, client, miembro_h):
        assert _get(client, "/api/crm/automations/palette", miembro_h).status_code == 403

    def test_flows_requires_edit(self, client, lector_h):
        resp = _post(client, "/api/crm/automations/flows",
                     json={"name": "test", "nodes": [], "edges": []}, h=lector_h)
        assert resp.status_code == 403

    def test_flows_editor_ok(self, client, editor_h):
        resp = _post(client, "/api/crm/automations/flows",
                     json={"name": "test-flow", "nodes": [], "edges": []}, h=editor_h)
        assert resp.status_code in (200, 201)

    def test_validate_path_requires_edit(self, client, lector_h):
        resp = _post(client, "/api/crm/automations/flows/validate-path",
                     json={"nodes": ["n1", "n2", "n3"], "edges": [{"source": "n1", "target": "n2"}, {"source": "n2", "target": "n3"}]},
                     h=lector_h)
        assert resp.status_code == 403


# ─── GRUPO 4: Pastoral ───────────────────────────────────────────────────


class TestRBACPastoral:
    def test_casos_401(self, client):
        assert _get(client, "/api/crm/casos").status_code == 401

    def test_casos_admin_ok(self, client, admin_h):
        assert _get(client, "/api/crm/casos", admin_h).status_code == 200

    def test_tasks_401(self, client):
        assert _get(client, "/api/crm/tasks").status_code == 401

    def test_tasks_miembro_403(self, client, miembro_h):
        assert _get(client, "/api/crm/tasks", miembro_h).status_code == 403

    def test_counseling_admin_ok(self, client, admin_h):
        assert _get(client, "/api/crm/counseling/", admin_h).status_code == 200


# ─── GRUPO 5: Resources ──────────────────────────────────────────────────


class TestRBACResources:
    def test_plantillas_401(self, client):
        assert _get(client, "/api/crm/resources/plantillas").status_code == 401

    def test_plantillas_admin_ok(self, client, admin_h):
        assert _get(client, "/api/crm/resources/plantillas", admin_h).status_code == 200

    def test_plantillas_miembro_403(self, client, miembro_h):
        assert _get(client, "/api/crm/resources/plantillas", miembro_h).status_code == 403

    def test_categorias_editor_ok(self, client, editor_h):
        assert _get(client, "/api/crm/resources/categorias", editor_h).status_code == 200


# ─── GRUPO 6: Profile ────────────────────────────────────────────────────


class TestRBACProfile:
    def test_patch_me_profile_401(self, client):
        assert _patch(client, "/api/crm/personas/me/profile", json={"phone": "123"}).status_code == 401

    def test_patch_me_profile_any_role_ok(self, client, miembro_h):
        resp = _patch(client, "/api/crm/personas/me/profile",
                      json={"phone": "+57 300 000 0000"}, h=miembro_h)
        assert resp.status_code == 200
