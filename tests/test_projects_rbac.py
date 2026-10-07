"""RBAC tests for the Projects module (cierre de PEND-RBAC-001).

Doc de referencia: ``docs/ESTADO_PROYECTOS.md`` (PEND-RBAC-001).

Matriz de roles verificada contra ``backend.core.permissions.DEFAULT_ROLES``:

    * ``Administrador`` (admin usuario seeded via ``seed_admin``):
      bypass total en ``require_permission`` (regla ``role in {"admin",
      "administrador"}`` → 200/201/204/404, nunca 403).
    * ``Gestor``: permisos ``projects:read + projects:edit + projects:manage``
      (definidos en ``DEFAULT_ROLES["Gestor"]["permissions"]``).
    * ``Editor``: permisos ``projects:read + projects:edit`` (sin
      ``projects:manage``).
    * ``Miembro``: SOLO ``academy:study + profile:manage``. NO tiene acceso al
      módulo projects en ninguna variante — baseline actual documentado.

Cobertura: rutas representativas de lectura y escritura/mutación,
parametrizadas sobre los roles canónicos, más casos directos de política. La
suite se ejecuta completa como gate; el inventario OpenAPI no se presenta como
equivalente a una prueba por rol. Cubre además:

    * Jerarquía ``manage → edit → read`` (Gestor/Editor pueden
      delegaciones de nivel inferior).
    * ``PUT /projects/{id}/phases`` (cierre ``PEND-QUALITY-PHASES-RBAC-001``):
      decorador ``require_module_access("projects", "manage")`` desde
      ``2026-07-16``. Editor (sin ``projects:manage``) recibe 403,
      alineado con el docstring del endpoint ("Solo administradores y
      gestores pueden modificar fases").

Ejecutar: ``cd /root/ccf && ./venv/bin/python -m pytest tests/test_projects_rbac.py -v``.
"""

from __future__ import annotations

import re
import uuid as _uuid

import pytest
from fastapi import status

from backend.app import app
from scripts.audit_projects_api_contracts import declared_guards, route_inventory
from tests.conftest import auth_headers, seed_admin, seed_user_with_role

# ── Helpers ────────────────────────────────────────────────────────────────


def _ensure_role_with_default_perms(db_session, role_name_canonical: str) -> str:
    """Crea/actualiza un ``RolPlataforma`` con los permisos canónicos.

    Toma el nombre canónico (``"Administrador"``, ``"Gestor"``,
    ``"Editor"``, ``"Miembro"``) — NO el alias ``"admin"`` — para
    coincidir con los nombres que aparecen en ``DEFAULT_ROLES``. Rellena
    ``permisos`` con un mapping ``{perm_key: "allow"}`` por cada permiso
    declarado en la matriz, de modo que ``require_permission`` no confunda el
    rol con un bucket vacío.

    Retorna el nombre canónico resuelto (útil para ``seed_user_with_role``
    que compara por ``.nombre``).
    """
    from backend.core.permissions import DEFAULT_ROLES, normalize_role
    from backend.models_auth import RolPlataforma

    canonical = normalize_role(role_name_canonical)
    target = next(
        (role_def for role_def in DEFAULT_ROLES if normalize_role(role_def["name"]) == canonical),
        None,
    )
    if target is None:
        raise ValueError(
            f"Role '{role_name_canonical}' not in DEFAULT_ROLES (known: {[r['name'] for r in DEFAULT_ROLES]})"
        )

    perm_dict = {p: "allow" for p in target["permissions"]}

    existing = db_session.query(RolPlataforma).filter(RolPlataforma.nombre == target["name"]).first()
    if existing is None:
        existing = RolPlataforma(
            id=_uuid.uuid4(),
            nombre=target["name"],
            permisos=perm_dict,
        )
        db_session.add(existing)
        db_session.flush()
    else:
        existing.permisos = perm_dict
        db_session.flush()
    return target["name"]


def _seed_role_user(db_session, role_canonical: str, email: str):
    """Crea un Usuario con el ``RolPlataforma`` alineado a ``DEFAULT_ROLES``.

    En lugar del stub ``permisos={"default": "allow"}`` que usa el
    helper genérico ``seed_user_with_role``, esta función primero carga el
    rol canónico con permisos correctos vía
    ``_ensure_role_with_default_perms`` y luego reutiliza
    ``seed_user_with_role`` para crear la Persona/Sede/Usuario.
    """
    role_name = _ensure_role_with_default_perms(db_session, role_canonical)
    return seed_user_with_role(
        db_session,
        role_name=role_name,
        email=email,
    )


# ── Endpoint matrices ──────────────────────────────────────────────────────

# UUID sintácticamente válido pero inexistente. Garantiza que el RBAC se evalúa
# antes que cualquier búsqueda en BD, así nunca obtendremos 404 sin haber
# pasado por ``require_module_access``.
# UUID FIJO (no uuid4()): pytest-xdist lanza un proceso por worker y cada uno
# generaría un valor distinto en los parametrize de módulo → "Different tests
# were collected between gwN and gwM". Valor constante ⇒ colección idéntica.
FAKE = "00000000-0000-4000-8000-0000000000fa"
FAKE_COMMENT = "00000000-0000-4000-8000-0000000000fc"
FAKE_TASK = "00000000-0000-4000-8000-0000000000fd"

# (method, path)
_READ_ENDPOINTS = [
    ("GET", "/api/projects"),
    ("GET", "/api/projects/assignee-candidates"),
    ("GET", f"/api/projects/assignee-candidates/{FAKE}"),
    ("GET", "/api/projects/page"),
    ("GET", "/api/projects/summary-page"),
    ("GET", "/api/projects/summary"),
    ("GET", "/api/projects/workload"),
    ("GET", "/api/projects/activities"),
    ("GET", "/api/projects/inbox"),
    ("GET", "/api/projects/whiteboards"),
    ("GET", "/api/projects/tasks"),
    ("GET", "/api/projects/tasks/page"),
    ("GET", f"/api/projects/{FAKE}/favorites"),
    ("GET", f"/api/projects/{FAKE}"),
    ("GET", f"/api/projects/{FAKE}/phases"),
    ("GET", f"/api/projects/{FAKE}/wiki"),
    ("GET", f"/api/projects/{FAKE}/whiteboard"),
    ("GET", f"/api/projects/tasks/{FAKE}"),
    ("GET", f"/api/projects/{FAKE}/milestones"),
    ("GET", f"/api/projects/{FAKE}/messages"),
    ("GET", f"/api/projects/{FAKE}/export/executive-data"),
    ("GET", f"/api/projects/{FAKE}/export/summary-pdf"),
    ("GET", f"/api/projects/{FAKE}/export/tasks-csv"),
    ("GET", f"/api/projects/{FAKE}/export/expenses-csv"),
    ("GET", "/api/projects/templates"),
    ("GET", f"/api/projects/templates/{FAKE}"),
    ("GET", f"/api/projects/{FAKE}/advanced-indicators"),
    ("GET", f"/api/projects/{FAKE}/advanced-indicators/{FAKE_TASK}"),
    ("GET", f"/api/projects/{FAKE}/analytics"),
    ("GET", f"/api/projects/{FAKE}/automations"),
    ("GET", f"/api/projects/{FAKE}/automations/{FAKE_TASK}"),
    ("GET", f"/api/projects/{FAKE}/baseline"),
    ("GET", f"/api/projects/{FAKE}/baselines"),
    ("GET", f"/api/projects/{FAKE}/budget-summary"),
    ("GET", f"/api/projects/{FAKE}/critical-path"),
    ("GET", f"/api/projects/{FAKE}/dependencies"),
    ("GET", f"/api/projects/{FAKE}/expenses"),
    ("GET", f"/api/projects/{FAKE}/expenses/{FAKE_TASK}"),
    ("GET", f"/api/projects/{FAKE}/files"),
    ("GET", f"/api/projects/{FAKE}/files/summary"),
    ("GET", f"/api/projects/{FAKE}/indicators/{FAKE_TASK}/records"),
    ("GET", f"/api/projects/{FAKE}/kpis"),
    ("GET", f"/api/projects/{FAKE}/risks"),
    ("GET", f"/api/projects/{FAKE}/risks-summary"),
    ("GET", f"/api/projects/{FAKE}/risks/{FAKE_TASK}"),
    ("GET", f"/api/projects/{FAKE}/tasks"),
    ("GET", f"/api/projects/{FAKE}/tasks/{FAKE_TASK}/supplies"),
    ("GET", f"/api/projects/{FAKE}/tasks/{FAKE_TASK}/time-logs"),
    ("GET", f"/api/projects/{FAKE}/team"),
    ("GET", f"/api/projects/{FAKE}/time-logs"),
    ("GET", f"/api/projects/{FAKE}/time-tracking-summary"),
    ("GET", f"/api/projects/{FAKE}/workload"),
    # Comentarios: ruta flat ``/comments`` (lista global con filtros).
    ("GET", "/api/projects/comments"),
]

# Endpoints where Miembro should receive 403 (module-level access denied)
_READ_ENDPOINTS_MIEMBRO_403 = [
    ("GET", "/api/projects"),
    ("GET", "/api/projects/assignee-candidates"),
    ("GET", f"/api/projects/assignee-candidates/{FAKE}"),
    ("GET", "/api/projects/page"),
    ("GET", "/api/projects/summary-page"),
    ("GET", "/api/projects/summary"),
    ("GET", "/api/projects/workload"),
    ("GET", "/api/projects/activities"),
    ("GET", "/api/projects/inbox"),
    ("GET", "/api/projects/whiteboards"),
    ("GET", "/api/projects/tasks"),
    ("GET", "/api/projects/tasks/page"),
    ("GET", f"/api/projects/{FAKE}/favorites"),
    ("GET", "/api/projects/comments"),
    ("GET", "/api/projects/templates"),
    ("GET", f"/api/projects/templates/{FAKE}"),
    ("GET", f"/api/projects/{FAKE}/advanced-indicators"),
    ("GET", f"/api/projects/{FAKE}/advanced-indicators/{FAKE_TASK}"),
    ("GET", f"/api/projects/{FAKE}/automations"),
    ("GET", f"/api/projects/{FAKE}/automations/{FAKE_TASK}"),
    ("GET", f"/api/projects/{FAKE}/baseline"),
    ("GET", f"/api/projects/{FAKE}/baselines"),
    ("GET", f"/api/projects/{FAKE}/budget-summary"),
    ("GET", f"/api/projects/{FAKE}/critical-path"),
    ("GET", f"/api/projects/{FAKE}/dependencies"),
    ("GET", f"/api/projects/{FAKE}/expenses"),
    ("GET", f"/api/projects/{FAKE}/expenses/{FAKE_TASK}"),
    ("GET", f"/api/projects/{FAKE}/files"),
    ("GET", f"/api/projects/{FAKE}/files/summary"),
    ("GET", f"/api/projects/{FAKE}/indicators/{FAKE_TASK}/records"),
    ("GET", f"/api/projects/{FAKE}/kpis"),
    ("GET", f"/api/projects/{FAKE}/risks"),
    ("GET", f"/api/projects/{FAKE}/risks-summary"),
    ("GET", f"/api/projects/{FAKE}/risks/{FAKE_TASK}"),
    ("GET", f"/api/projects/{FAKE}/tasks"),
    ("GET", f"/api/projects/{FAKE}/tasks/{FAKE_TASK}/time-logs"),
    ("GET", f"/api/projects/{FAKE}/time-logs"),
    ("GET", f"/api/projects/{FAKE}/time-tracking-summary"),
    ("GET", f"/api/projects/{FAKE}/workload"),
]

# Endpoints protected by require_project_access with a project/task ID:
# Axioma 3 requires 404 for non-existent or out-of-scope resources.
_READ_ENDPOINTS_MIEMBRO_404 = [
    ("GET", f"/api/projects/{FAKE}"),
    ("GET", f"/api/projects/{FAKE}/phases"),
    ("GET", f"/api/projects/{FAKE}/wiki"),
    ("GET", f"/api/projects/{FAKE}/whiteboard"),
    ("GET", f"/api/projects/tasks/{FAKE}"),
    ("GET", f"/api/projects/{FAKE}/analytics"),
    ("GET", f"/api/projects/{FAKE}/tasks/{FAKE_TASK}/supplies"),
    ("GET", f"/api/projects/{FAKE}/team"),
]

# Endpoints scoped to a project ID but still protected by
# require_module_access (not require_project_access), so Miembro keeps
# receiving 403.
_READ_ENDPOINTS_MIEMBRO_403_PROJECT_SCOPED = [
    ("GET", f"/api/projects/{FAKE}/milestones"),
    ("GET", f"/api/projects/{FAKE}/messages"),
    ("GET", f"/api/projects/{FAKE}/export/executive-data"),
    ("GET", f"/api/projects/{FAKE}/export/summary-pdf"),
    ("GET", f"/api/projects/{FAKE}/export/tasks-csv"),
    ("GET", f"/api/projects/{FAKE}/export/expenses-csv"),
]

# (method, path, json_payload or None)
_EDIT_ENDPOINTS = [
    ("POST", "/api/projects", {"title": "Test", "description": "desc"}),
    ("POST", f"/api/projects/{FAKE}/tasks", {"title": "T", "status": "todo", "priority": "medium"}),
    ("PUT", f"/api/projects/{FAKE}/phases", []),
    ("POST", f"/api/projects/{FAKE}/wiki", {"title": "W", "content": "c"}),
    ("POST", f"/api/projects/{FAKE}/whiteboard", {"elements_json": "[]"}),
    ("DELETE", f"/api/projects/{FAKE}/whiteboard", None),
    ("PATCH", f"/api/projects/tasks/{FAKE}", {"title": "Updated"}),
    ("POST", f"/api/projects/inbox/{FAKE}/read", None),
    # Comentarios: patrón nested ``/{project_id}/comments`` Y flat
    # ``/comments`` (sub-rutas PATCH/DELETE operan sobre ``cid``).
    ("POST", "/api/projects/comments", {"project_id": FAKE, "content": "c"}),
    ("POST", f"/api/projects/{FAKE}/comments", {"content": "c"}),
    ("PATCH", f"/api/projects/comments/{FAKE_COMMENT}", {"content": "u"}),
    ("DELETE", f"/api/projects/comments/{FAKE_COMMENT}", None),
    # DELETE de proyecto (note: usa ``academy:manage``, NO ``projects:edit``
    # — asimetría documentada en ``TestPermissionHierarchy``).
    ("DELETE", f"/api/projects/{FAKE}", None),
    ("POST", f"/api/projects/{FAKE}/messages", {"content": "msg"}),
    ("DELETE", f"/api/projects/{FAKE}/tasks/{FAKE_TASK}", None),
    ("POST", f"/api/projects/{FAKE}/tasks/{FAKE_TASK}/toggle-favorite", None),
]

# Endpoints where Miembro should receive 403 (module-level access denied)
_EDIT_ENDPOINTS_MIEMBRO_403 = [
    ("POST", "/api/projects", {"title": "Test", "description": "desc"}),
    ("POST", f"/api/projects/inbox/{FAKE}/read", None),
    ("POST", "/api/projects/comments", {"project_id": FAKE, "content": "c"}),
    ("PATCH", f"/api/projects/comments/{FAKE_COMMENT}", {"content": "u"}),
    ("DELETE", f"/api/projects/comments/{FAKE_COMMENT}", None),
    ("DELETE", f"/api/projects/{FAKE}", None),
    ("POST", f"/api/projects/{FAKE}/messages", {"content": "msg"}),
    ("DELETE", f"/api/projects/{FAKE}/tasks/{FAKE_TASK}", None),
    ("POST", f"/api/projects/{FAKE}/tasks/{FAKE_TASK}/toggle-favorite", None),
]

# Endpoints protected by require_project_access with a project/task ID:
# Axioma 3 requires 404 for non-existent or out-of-scope resources.
_EDIT_ENDPOINTS_MIEMBRO_404 = [
    ("POST", f"/api/projects/{FAKE}/tasks", {"title": "T", "status": "todo", "priority": "medium"}),
    ("POST", f"/api/projects/{FAKE}/wiki", {"title": "W", "content": "c"}),
    ("POST", f"/api/projects/{FAKE}/whiteboard", {"elements_json": "[]"}),
    ("DELETE", f"/api/projects/{FAKE}/whiteboard", None),
    ("PATCH", f"/api/projects/tasks/{FAKE}", {"title": "Updated"}),
]


def _normalize_route(path: str) -> str:
    return re.sub(
        r"\{[^}]+\}|[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
        "{id}",
        path,
    )


def test_read_rbac_matrix_covers_every_openapi_get_route():
    operations = route_inventory(app.openapi())
    get_routes = {(method, _normalize_route(path)) for method, path, _ in operations if method == "GET"}
    allowed_routes = {(method, _normalize_route(path)) for method, path in _READ_ENDPOINTS}
    member_403_routes = {
        (method, _normalize_route(path))
        for method, path in _READ_ENDPOINTS_MIEMBRO_403 + _READ_ENDPOINTS_MIEMBRO_403_PROJECT_SCOPED
    }
    member_404_routes = {(method, _normalize_route(path)) for method, path in _READ_ENDPOINTS_MIEMBRO_404}
    guards = declared_guards()

    assert allowed_routes == get_routes, (
        f"Editor/Gestor read RBAC coverage differs from OpenAPI; "
        f"missing={sorted(get_routes - allowed_routes)}, stale={sorted(allowed_routes - get_routes)}"
    )
    assert member_403_routes | member_404_routes == get_routes, (
        f"Miembro read RBAC coverage differs from OpenAPI; "
        f"missing={sorted(get_routes - (member_403_routes | member_404_routes))}, "
        f"stale={sorted((member_403_routes | member_404_routes) - get_routes)}"
    )
    assert not member_403_routes & member_404_routes, "Member read routes cannot expect both 403 and 404"

    for method, route in get_routes:
        matching_path = next(
            path
            for candidate_method, path, _ in operations
            if candidate_method == method and _normalize_route(path) == route
        )
        guard = guards[(method, matching_path)]
        if guard == "projects:read":
            expected_routes = member_403_routes
        elif guard == "project access: read":
            expected_routes = member_404_routes
        else:
            pytest.fail(f"Unexpected read guard for {method} {matching_path}: {guard}")
        assert (method, route) in expected_routes, (
            f"Miembro expectation for {method} {matching_path} disagrees with declared guard {guard}"
        )


_MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
_MUTATION_GUARDS = declared_guards()
_MUTATING_ROUTE_CASES = [
    (
        method,
        re.sub(r"\{[^}]+\}", FAKE, path),
        _MUTATION_GUARDS[(method, path)],
    )
    for method, path, _ in route_inventory(app.openapi())
    if method in _MUTATING_METHODS
]
_AUTHORIZED_MUTATION_STATUSES = {
    status.HTTP_200_OK,
    status.HTTP_201_CREATED,
    status.HTTP_202_ACCEPTED,
    status.HTTP_204_NO_CONTENT,
    status.HTTP_400_BAD_REQUEST,
    status.HTTP_404_NOT_FOUND,
    status.HTTP_409_CONFLICT,
    status.HTTP_422_UNPROCESSABLE_CONTENT,
}


def test_mutating_route_guards_match_role_policy_without_persisting(client, db_session, role_headers):
    """Exercise every mutating route with absent resources and bodies.

    Missing bodies prevent creation endpoints from persisting data; fake UUID
    path parameters keep resource-scoped calls in the not-found path. The
    assertion verifies that authorization is still evaluated consistently
    before an operation is accepted or rejected for resource/input reasons.
    """
    from backend import models_projects

    project_models = {
        model.__name__: model
        for model in vars(models_projects).values()
        if isinstance(model, type)
        and model.__module__ == models_projects.__name__
        and hasattr(model, "__table__")
    }
    before_counts = {name: db_session.query(model).count() for name, model in project_models.items()}
    assert _MUTATING_ROUTE_CASES, "Projects OpenAPI must contain mutating routes"

    for method, path, guard in _MUTATING_ROUTE_CASES:
        for role in ("admin", "gestor"):
            response = _issue(client, method, path, None, role_headers[role])
            assert response.status_code in _AUTHORIZED_MUTATION_STATUSES, (
                f"{role} recibió HTTP {response.status_code} en {method} {path} "
                f"(guard {guard}): {response.text}"
            )

        editor_response = _issue(client, method, path, None, role_headers["editor"])
        if guard in {"academy:manage", "projects:manage"}:
            assert editor_response.status_code == status.HTTP_403_FORBIDDEN, (
                f"Editor debe quedar bloqueado por {guard} en {method} {path}; "
                f"recibió {editor_response.status_code}: {editor_response.text}"
            )
        else:
            assert editor_response.status_code in _AUTHORIZED_MUTATION_STATUSES, (
                f"Editor recibió HTTP {editor_response.status_code} en {method} {path} "
                f"(guard {guard}): {editor_response.text}"
            )

        member_response = _issue(client, method, path, None, role_headers["miembro"])
        if guard in {"project access: edit", "project access: manage"}:
            expected_member_status = status.HTTP_404_NOT_FOUND
        elif guard in {"projects:edit", "projects:read", "projects:manage", "academy:manage"}:
            expected_member_status = status.HTTP_403_FORBIDDEN
        else:
            pytest.fail(f"Unexpected mutating guard for {method} {path}: {guard}")
        assert member_response.status_code == expected_member_status, (
            f"Miembro recibió HTTP {member_response.status_code} en {method} {path} "
            f"(guard {guard}; esperado {expected_member_status}): {member_response.text}"
        )

    after_counts = {name: db_session.query(model).count() for name, model in project_models.items()}
    assert after_counts == before_counts, "RBAC probes with absent bodies/resources must not persist project data"


def _issue(client, method: str, path: str, payload, headers):
    """Wrapper para emitir requests con payload opcional."""
    if payload is None:
        return client.request(method, path, headers=headers)
    return client.request(method, path, json=payload, headers=headers)


def _assert_read_allowed(resp, role: str, method: str, path: str) -> None:
    assert resp.status_code in {status.HTTP_200_OK, status.HTTP_404_NOT_FOUND}, (
        f"{role} recibió una respuesta inesperada en {method} {path}: "
        f"HTTP {resp.status_code}: {resp.text}"
    )


# ── Fixture: 4 roles con sus headers ya listos ─────────────────────────────


@pytest.fixture
def role_headers(client, db_session):
    """Retorna dict {role_canonical: headers} para los 4 roles."""
    headers = {}

    # Admin — usa el factory existente (``RolPlataforma("ADMIN")`` con
    # ``permisos={"*": "allow"}``), bypass completo en ``require_permission``.
    seed_admin(db_session)
    headers["admin"] = auth_headers(client)

    for role_key in ("gestor", "editor", "miembro"):
        email = f"{role_key}@rbac.test"
        _seed_role_user(db_session, role_key, email)
        headers[role_key] = auth_headers(client, email=email)

    return headers


# ── Tests — Administrador (bypass total) ──────────────────────────────────


class TestAdministradorBypass:
    """El bypass de admin en ``require_permission`` debe cubrir TODA la API
    de ``/api/projects/*``. Si admin recibe 403 en algún endpoint, hay un
    bug crítico (probablemente el endpoint usa ``require_admin`` por
    equivocación o una Depends rota)."""

    @pytest.mark.parametrize("method, path", _READ_ENDPOINTS)
    def test_admin_read_never_403(self, client, role_headers, method, path):
        resp = _issue(client, method, path, None, role_headers["admin"])
        _assert_read_allowed(resp, "Admin", method, path)

    @pytest.mark.parametrize("method, path, payload", _EDIT_ENDPOINTS)
    def test_admin_write_never_403(self, client, role_headers, method, path, payload):
        resp = _issue(client, method, path, payload, role_headers["admin"])
        assert resp.status_code != status.HTTP_403_FORBIDDEN, (
            f"Admin bloqueado por RBAC en {method} {path}: {resp.text}"
        )


# ── Tests — Gestor (projects:manage) ──────────────────────────────────────


class TestGestorManage:
    """Gestor tiene ``projects:read + projects:edit + projects:manage`` y
    debe comportarse como admin en el módulo (no recibe 403)."""

    @pytest.mark.parametrize("method, path", _READ_ENDPOINTS)
    def test_gestor_read_never_403(self, client, role_headers, method, path):
        resp = _issue(client, method, path, None, role_headers["gestor"])
        _assert_read_allowed(resp, "Gestor", method, path)

    @pytest.mark.parametrize("method, path, payload", _EDIT_ENDPOINTS)
    def test_gestor_write_never_403(self, client, role_headers, method, path, payload):
        resp = _issue(client, method, path, payload, role_headers["gestor"])
        assert resp.status_code != status.HTTP_403_FORBIDDEN, (
            f"Gestor bloqueado por RBAC en {method} {path}: {resp.text}"
        )


# ── Tests — Editor (projects:read + projects:edit, sin manage) ────────────


class TestEditorReadEdit:
    """Editor tiene ``projects:read + projects:edit``; por jerarquía
    ``edit → read`` se mantiene, pero NO tiene ``projects:manage``.

    ``PUT /projects/{id}/phases`` está protegido con ``projects:manage``
    desde el cierre de ``PEND-QUALITY-PHASES-RBAC-001`` (2026-07-16), por
    lo que Editor recibe **403** en ese endpoint específico
    (alineado con el docstring del endpoint)."""

    @pytest.mark.parametrize("method, path", _READ_ENDPOINTS)
    def test_editor_read_passess_rbac(self, client, role_headers, method, path):
        resp = _issue(client, method, path, None, role_headers["editor"])
        _assert_read_allowed(resp, "Editor", method, path)

    def test_editor_write_some_endpoints_pass(self, client, role_headers):
        """Editor puede ``POST/PATCH`` end-points protegidos con ``projects:edit``.
        Aquí validamos un sub-set representativo (no la matriz completa)
        porque el behavior exacto depende de cada endpoint."""
        editorial_set = [
            ("POST", "/api/projects", {"title": "E", "description": ""}),
            ("PATCH", f"/api/projects/tasks/{FAKE}", {"title": "OK"}),
            ("POST", f"/api/projects/inbox/{FAKE}/read", None),
        ]
        for method, path, payload in editorial_set:
            resp = _issue(client, method, path, payload, role_headers["editor"])
            assert resp.status_code != status.HTTP_403_FORBIDDEN, f"Editor bloqueado en {method} {path}: {resp.text}"

    def test_editor_can_create_task_but_miembro_cannot_on_same_project(self, client, db_session, role_headers):
        from backend.models_auth import Usuario
        from backend.models_projects import ProjectActivityLog, ProjectTask

        project_response = client.post(
            "/api/projects",
            json={"title": "Proyecto RBAC tarea real", "status": "planning"},
            headers=role_headers["admin"],
        )
        assert project_response.status_code == status.HTTP_201_CREATED, project_response.text
        project_id = project_response.json()["id"]

        editor = db_session.query(Usuario).filter_by(email="editor@rbac.test").one()
        create_payload = {"title": "Tarea autorizada del Editor", "status": "todo", "priority": "high"}
        editor_response = client.post(
            f"/api/projects/{project_id}/tasks",
            json=create_payload,
            headers=role_headers["editor"],
        )
        assert editor_response.status_code == status.HTTP_201_CREATED, editor_response.text
        task_id = editor_response.json()["id"]
        assert editor_response.json()["project_id"] == project_id
        task = db_session.query(ProjectTask).filter_by(id=task_id).one()
        assert str(task.project_id) == project_id

        editor_activity = (
            db_session.query(ProjectActivityLog)
            .filter_by(project_id=project_id, action_type="task_created")
            .one()
        )
        assert editor_activity.persona_id == editor.id, "La bitácora debe atribuir la mutación al actor canónico"

        task_count_before_denial = db_session.query(ProjectTask).filter_by(project_id=project_id).count()
        activity_count_before_denial = db_session.query(ProjectActivityLog).filter_by(project_id=project_id).count()
        member_response = client.post(
            f"/api/projects/{project_id}/tasks",
            json={"title": "Tarea que no debe persistir", "status": "todo", "priority": "medium"},
            headers=role_headers["miembro"],
        )
        assert member_response.status_code == status.HTTP_403_FORBIDDEN, member_response.text
        assert db_session.query(ProjectTask).filter_by(project_id=project_id).count() == task_count_before_denial
        assert db_session.query(ProjectActivityLog).filter_by(project_id=project_id).count() == activity_count_before_denial

    def test_read_only_actor_can_toggle_only_own_favorite_for_task_in_project(self, client, db_session):
        from backend.models_projects import ProjectUserFavorite
        from tests.factories_projects import create_project_factory, create_task_factory

        _, _, sede = seed_admin(db_session, email="favorite-owner@test.com")
        project = create_project_factory(db_session, sede_id=sede.id)
        other_project = create_project_factory(db_session, sede_id=sede.id)
        task = create_task_factory(db_session, project.id)
        foreign_task = create_task_factory(db_session, other_project.id)
        reader, persona, _ = seed_user_with_role(
            db_session,
            role_name="ProjectsReader",
            email="projects-reader@test.com",
            sede_id=sede.id,
            permisos={"projects:read": "allow"},
        )
        headers = auth_headers(client, email=reader.email)

        mismatched_task = client.post(
            f"/api/projects/{project.id}/tasks/{foreign_task.id}/toggle-favorite",
            headers=headers,
        )
        assert mismatched_task.status_code == status.HTTP_400_BAD_REQUEST
        assert db_session.query(ProjectUserFavorite).filter_by(persona_id=persona.id).count() == 0

        added = client.post(
            f"/api/projects/{project.id}/tasks/{task.id}/toggle-favorite",
            headers=headers,
        )
        assert added.status_code == status.HTTP_200_OK, added.text
        assert added.json()["is_favorite"] is True
        assert db_session.query(ProjectUserFavorite).filter_by(persona_id=persona.id).one().entity_id == task.id

        listed = client.get(f"/api/projects/{project.id}/favorites", headers=headers)
        assert listed.status_code == status.HTTP_200_OK
        assert listed.json() == [str(task.id)]

        removed = client.post(
            f"/api/projects/{project.id}/tasks/{task.id}/toggle-favorite",
            headers=headers,
        )
        assert removed.status_code == status.HTTP_200_OK, removed.text
        assert removed.json()["is_favorite"] is False
        assert db_session.query(ProjectUserFavorite).filter_by(persona_id=persona.id).count() == 0


# ── Tests — Miembro baseline (PEND-RBAC-001) ──────────────────────────────


class TestMiembroBaseline:
    """Documenta el baseline actual PEND-RBAC-001: ``Miembro`` no tiene
    permisos ``projects:*`` y por tanto recibe **403** en los endpoints
    de módulo (sin project_id/task_id específico). En endpoints con
    ``project_id`` o ``task_id`` el contrato Axioma 3 exige 404 cuando
    el recurso no existe o no pertenece a la sede del actor, incluso
    para Miembro (existence-leak safe)."""

    @pytest.mark.parametrize(
        "method, path",
        _READ_ENDPOINTS_MIEMBRO_403 + _READ_ENDPOINTS_MIEMBRO_403_PROJECT_SCOPED,
    )
    def test_miembro_read_returns_403(self, client, role_headers, method, path):
        resp = _issue(client, method, path, None, role_headers["miembro"])
        assert resp.status_code == status.HTTP_403_FORBIDDEN, (
            f"Miembro NO bloqueado por RBAC en {method} {path} — regresión de baseline PEND-RBAC-001: {resp.text}"
        )

    @pytest.mark.parametrize("method, path", _READ_ENDPOINTS_MIEMBRO_404)
    def test_miembro_read_returns_404(self, client, role_headers, method, path):
        resp = _issue(client, method, path, None, role_headers["miembro"])
        assert resp.status_code == status.HTTP_404_NOT_FOUND, (
            f"Miembro debería recibir 404 (Axioma 3) en {method} {path} — recibió {resp.status_code}: {resp.text}"
        )

    @pytest.mark.parametrize("method, path, payload", _EDIT_ENDPOINTS_MIEMBRO_403)
    def test_miembro_write_returns_403(self, client, role_headers, method, path, payload):
        resp = _issue(client, method, path, payload, role_headers["miembro"])
        assert resp.status_code == status.HTTP_403_FORBIDDEN, f"Miembro NO bloqueado en {method} {path}: {resp.text}"

    @pytest.mark.parametrize("method, path, payload", _EDIT_ENDPOINTS_MIEMBRO_404)
    def test_miembro_write_returns_404(self, client, role_headers, method, path, payload):
        resp = _issue(client, method, path, payload, role_headers["miembro"])
        assert resp.status_code == status.HTTP_404_NOT_FOUND, (
            f"Miembro debería recibir 404 (Axioma 3) en {method} {path} — recibió {resp.status_code}: {resp.text}"
        )


# ── Tests — Jerarquía manage → edit → read ────────────────────────────────


class TestPermissionHierarchy:
    """Garantiza que la regla de jerarquía documentada en
    ``backend/core/permissions.py::_has_permission`` (``manage > edit >
    read``) se respeta efectivamente."""

    def test_gestor_can_use_read_endpoints(self, client, role_headers):
        resp = client.get("/api/projects/summary", headers=role_headers["gestor"])
        assert resp.status_code != status.HTTP_403_FORBIDDEN

    def test_gestor_can_modify_phases(self, client, role_headers):
        """``PUT /projects/{id}/phases`` usa ``projects:manage`` desde el
        cierre de ``PEND-QUALITY-PHASES-RBAC-001`` (2026-07-16). Gestor
        tiene ``projects:manage`` directamente, sin necesidad de jerarquía.
        Si en el futuro se cambia la decoración, este test debe
        actualizarse."""
        resp = client.put(f"/api/projects/{FAKE}/phases", json=[], headers=role_headers["gestor"])
        assert resp.status_code != status.HTTP_403_FORBIDDEN

    def test_delete_project_requires_academy_manage_per_policy(self, client, db_session, role_headers):
        """**Asimetría confirmada**: ``DELETE /projects/{id}`` usa
        ``require_staff_or_admin`` (= ``require_permission("academy:manage")``),
        NO ``projects:edit`` como su primo ``PATCH /projects/{id}``.

        Por tanto, Editor (que SÍ tiene ``projects:edit``) recibe **403**
        en DELETE, aunque pase la PATCH del mismo recurso. Esta asimetría
        fue descubierta durante el cierre de ``PEND-RBAC-001`` y queda
        documentada aquí como baseline. Si en el futuro se decide alinear
        DELETE con el resto de la matriz (a ``projects:edit`` o
        ``projects:manage``), este test debe actualizarse."""
        from backend.models_projects import Project

        created = client.post(
            "/api/projects",
            json={"title": "Proyecto protegido por política de borrado", "status": "planning"},
            headers=role_headers["admin"],
        )
        assert created.status_code == status.HTTP_201_CREATED, created.text
        project_id = created.json()["id"]
        project = db_session.query(Project).filter(Project.id == project_id).one()

        editor_response = client.delete(f"/api/projects/{project_id}", headers=role_headers["editor"])
        assert editor_response.status_code == status.HTTP_403_FORBIDDEN, (
            f"Editor no debe borrar un proyecto existente con solo projects:edit; "
            f"recibió {editor_response.status_code}: {editor_response.text}"
        )
        db_session.refresh(project)
        assert project.deleted_at is None, "El rechazo RBAC no debe modificar el proyecto"

        manager_response = client.delete(f"/api/projects/{project_id}", headers=role_headers["gestor"])
        assert manager_response.status_code == status.HTTP_200_OK, manager_response.text
        db_session.refresh(project)
        assert project.deleted_at is not None, "Gestor autorizado debe aplicar soft delete"


# ── Tests — Gaps documentados (regresión consciente) ───────────────────────


class TestPermissionGranularityGaps:
    """Gaps conscientes del sistema actual. Cada test documenta un caso
    y fija el baseline del comportamiento esperado. Si en el futuro se
    cambia la decoración de un endpoint, el test correspondiente debe
    actualizarse."""

    def test_editor_blocked_from_put_phases(self, client, role_headers):
        """Cierre de ``PEND-QUALITY-PHASES-RBAC-001`` (2026-07-16):
        ``PUT /projects/{id}/phases`` está protegido con
        ``require_project_access("manage")``. Para un project_id
        inexistente, Editor (sin ``projects:manage``) recibe **404**
        (Axioma 3 / existence-leak safe). Para un proyecto existente en
        su sede recibe **403** (ver
        ``test_editor_blocked_from_put_phases_existing_project``)."""
        resp = client.put(
            f"/api/projects/{FAKE}/phases",
            json=[{"name": "P", "slug": "todo", "color": "#000"}],
            headers=role_headers["editor"],
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND, (
            f"PUT /phases roto: editor recibió {resp.status_code}, "
            f"se esperaba 404 (Axioma 3) para project_id inexistente."
        )

    def test_editor_blocked_from_put_phases_existing_project(self, client, role_headers):
        """Editor recibe 403 en PUT /phases para un proyecto existente en su sede."""
        payload = {"title": "Proyecto Fases", "description": "Test", "status": "planning", "color": "#3b82f6"}
        create_resp = client.post("/api/projects", json=payload, headers=role_headers["admin"])
        assert create_resp.status_code == status.HTTP_201_CREATED
        project_id = create_resp.json()["id"]

        resp = client.put(
            f"/api/projects/{project_id}/phases",
            json=[{"name": "P", "slug": "todo", "color": "#000"}],
            headers=role_headers["editor"],
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN, (
            f"PUT /phases roto: editor recibió {resp.status_code}, "
            f"se esperaba 403 (projects:manage) para proyecto existente en su sede."
        )

    def test_miembro_blocked_from_put_phases_existing_project(self, client, role_headers):
        """Miembro recibe 403 en PUT /phases para un proyecto existente en su sede."""
        payload = {"title": "Proyecto Fases Miembro", "description": "Test", "status": "planning", "color": "#3b82f6"}
        create_resp = client.post("/api/projects", json=payload, headers=role_headers["admin"])
        assert create_resp.status_code == status.HTTP_201_CREATED
        project_id = create_resp.json()["id"]

        resp = client.put(
            f"/api/projects/{project_id}/phases",
            json=[{"name": "P", "slug": "todo", "color": "#000"}],
            headers=role_headers["miembro"],
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN, (
            f"PUT /phases roto: miembro recibió {resp.status_code}, "
            f"se esperaba 403 (projects:manage) para proyecto existente en su sede."
        )


# ── Tests — Cobertura de los códigos 200 esperados (smoke) ─────────────────


class TestAdminAllowedReads:
    """Cobertura mínima: admin realmente ve datos cuando el endpoint requiere
    mismo actor / sesión válida. Si 401/403/422 aparecen, esto detecta
    que el token de admin no es válido."""

    def test_admin_can_list_projects(self, client, role_headers):
        resp = client.get("/api/projects", headers=role_headers["admin"])
        # Lista vacía sin proyectos seedeados, pero la respuesta es 200.
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json() == []

    def test_admin_can_list_summary(self, client, role_headers):
        resp = client.get("/api/projects/summary", headers=role_headers["admin"])
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json() == []

    def test_admin_can_list_workload(self, client, role_headers):
        resp = client.get("/api/projects/workload", headers=role_headers["admin"])
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json() == []

    def test_admin_can_list_activities(self, client, role_headers):
        resp = client.get("/api/projects/activities", headers=role_headers["admin"])
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json() == []

    def test_admin_can_list_inbox(self, client, role_headers):
        resp = client.get("/api/projects/inbox", headers=role_headers["admin"])
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json() == []

    def test_admin_can_see_whiteboards_list(self, client, role_headers):
        resp = client.get("/api/projects/whiteboards", headers=role_headers["admin"])
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json() == []
