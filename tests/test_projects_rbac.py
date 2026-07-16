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

Cobertura: 12 endpoints de lectura × 10 endpoints de escritura/mutación,
parametrizados sobre las 4 roles canónicas. Cubre además:

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

import uuid as _uuid

import pytest
from fastapi import status

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
        (
            role_def
            for role_def in DEFAULT_ROLES
            if normalize_role(role_def["name"]) == canonical
        ),
        None,
    )
    if target is None:
        raise ValueError(
            f"Role '{role_name_canonical}' not in DEFAULT_ROLES (known: "
            f"{[r['name'] for r in DEFAULT_ROLES]})"
        )

    perm_dict = {p: "allow" for p in target["permissions"]}

    existing = (
        db_session.query(RolPlataforma)
        .filter(RolPlataforma.nombre == target["name"])
        .first()
    )
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
FAKE = str(_uuid.uuid4())

# (method, path)
_READ_ENDPOINTS = [
    ("GET", "/api/projects"),
    ("GET", "/api/projects/summary"),
    ("GET", "/api/projects/workload"),
    ("GET", "/api/projects/activities"),
    ("GET", "/api/projects/inbox"),
    ("GET", "/api/projects/whiteboards"),
    ("GET", "/api/projects/tasks"),
    ("GET", f"/api/projects/{FAKE}"),
    ("GET", f"/api/projects/{FAKE}/phases"),
    ("GET", f"/api/projects/{FAKE}/wiki"),
    ("GET", f"/api/projects/{FAKE}/whiteboard"),
    ("GET", f"/api/projects/tasks/{FAKE}"),
    ("GET", f"/api/projects/{FAKE}/milestones"),
    ("GET", f"/api/projects/{FAKE}/messages"),
    # Comentarios: ruta flat ``/comments`` (lista global con filtros).
    ("GET", "/api/projects/comments"),
]

# (method, path, json_payload or None)
_EDIT_ENDPOINTS = [
    ("POST", "/api/projects", {"title": "Test", "description": "desc"}),
    ("POST", f"/api/projects/{FAKE}/tasks",
     {"title": "T", "status": "todo", "priority": "medium"}),
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
    ("PATCH", f"/api/projects/comments/{_uuid.uuid4()}", {"content": "u"}),
    ("DELETE", f"/api/projects/comments/{_uuid.uuid4()}", None),
    # DELETE de proyecto (note: usa ``academy:manage``, NO ``projects:edit``
    # — asimetría documentada en ``TestPermissionHierarchy``).
    ("DELETE", f"/api/projects/{FAKE}", None),
    ("POST", f"/api/projects/{FAKE}/messages", {"content": "msg"}),
    ("DELETE", f"/api/projects/{FAKE}/tasks/{_uuid.uuid4()}", None),
]


def _issue(client, method: str, path: str, payload, headers):
    """Wrapper para emitir requests con payload opcional."""
    if payload is None:
        return client.request(method, path, headers=headers)
    return client.request(method, path, json=payload, headers=headers)


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
        assert resp.status_code != status.HTTP_403_FORBIDDEN, (
            f"Admin bloqueado por RBAC en {method} {path}: {resp.text}"
        )

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
        assert resp.status_code != status.HTTP_403_FORBIDDEN, (
            f"Gestor bloqueado por RBAC en {method} {path}: {resp.text}"
        )

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
        assert resp.status_code != status.HTTP_403_FORBIDDEN, (
            f"Editor (projects:edit incluye read por jerarquía) bloqueado en "
            f"{method} {path}: {resp.text}"
        )

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
            assert resp.status_code != status.HTTP_403_FORBIDDEN, (
                f"Editor bloqueado en {method} {path}: {resp.text}"
            )


# ── Tests — Miembro baseline (PEND-RBAC-001) ──────────────────────────────


class TestMiembroBaseline:
    """Documenta el baseline actual PEND-RBAC-001: ``Miembro`` no tiene
    permisos ``projects:*`` y por tanto recibe **403** en TODA la API
    del módulo. Cualquier cambio futuro que añada acceso granular a
    Miembro romperá estos tests y obligará a un debate explícito sobre
    el modelo de permisos."""

    @pytest.mark.parametrize("method, path", _READ_ENDPOINTS)
    def test_miembro_read_returns_403(self, client, role_headers, method, path):
        resp = _issue(client, method, path, None, role_headers["miembro"])
        assert resp.status_code == status.HTTP_403_FORBIDDEN, (
            f"Miembro NO bloqueado por RBAC en {method} {path} — "
            f"regresión de baseline PEND-RBAC-001: {resp.text}"
        )

    @pytest.mark.parametrize("method, path, payload", _EDIT_ENDPOINTS)
    def test_miembro_write_returns_403(self, client, role_headers, method, path, payload):
        resp = _issue(client, method, path, payload, role_headers["miembro"])
        assert resp.status_code == status.HTTP_403_FORBIDDEN, (
            f"Miembro NO bloqueado en {method} {path}: {resp.text}"
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
        resp = client.put(
            f"/api/projects/{FAKE}/phases", json=[], headers=role_headers["gestor"]
        )
        assert resp.status_code != status.HTTP_403_FORBIDDEN

    def test_delete_project_requires_academy_manage_per_policy(self, client, role_headers):
        """**Asimetría confirmada**: ``DELETE /projects/{id}`` usa
        ``require_staff_or_admin`` (= ``require_permission("academy:manage")``),
        NO ``projects:edit`` como su primo ``PATCH /projects/{id}``.

        Por tanto, Editor (que SÍ tiene ``projects:edit``) recibe **403**
        en DELETE, aunque pase la PATCH del mismo recurso. Esta asimetría
        fue descubierta durante el cierre de ``PEND-RBAC-001`` y queda
        documentada aquí como baseline. Si en el futuro se decide alinear
        DELETE con el resto de la matriz (a ``projects:edit`` o
        ``projects:manage``), este test debe actualizarse."""
        resp = client.delete(
            f"/api/projects/{FAKE}", headers=role_headers["editor"]
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN, (
            f"Asimetría DELETE/projects rota: editor recibió "
            f"{resp.status_code}, se esperaba 403 (academy:manage). "
            f"Ajustar este test o el decorador del endpoint."
        )


# ── Tests — Gaps documentados (regresión consciente) ───────────────────────


class TestPermissionGranularityGaps:
    """Gaps conscientes del sistema actual. Cada test documenta un caso
    y fija el baseline del comportamiento esperado. Si en el futuro se
    cambia la decoración de un endpoint, el test correspondiente debe
    actualizarse."""

    def test_editor_blocked_from_put_phases(self, client, role_headers):
        """Cierre de ``PEND-QUALITY-PHASES-RBAC-001`` (2026-07-16):
        ``PUT /projects/{id}/phases`` está protegido con
        ``require_module_access("projects", "manage")``. Editor (que solo
        tiene ``projects:edit``) recibe **403**, alineado con el docstring
        del endpoint ("Solo administradores y gestores pueden modificar
        fases"). Gestor (con ``projects:manage``) sigue pasando
        (ver ``test_gestor_can_modify_phases``). Si en el futuro se cambia
        la decoración, este test debe actualizarse."""
        resp = client.put(
            f"/api/projects/{FAKE}/phases",
            json=[{"name": "P", "slug": "todo", "color": "#000"}],
            headers=role_headers["editor"],
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN, (
            f"PUT /phases roto: editor recibió {resp.status_code}, "
            f"se esperaba 403 (projects:manage)."
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
