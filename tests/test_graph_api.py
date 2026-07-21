import uuid

import pytest

from backend import models
from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin


def _seed_sede(db_session):
    sede = models.Sede(
        id=uuid.uuid4(), nombre="Test Sede", ciudad="Bogota", es_activa=True
    )
    db_session.add(sede)
    db_session.commit()
    db_session.refresh(sede)
    return sede


def test_graph_snapshot(client, db_session):
    _seed_admin(db_session)
    headers = _auth_headers(client)
    resp = client.get("/api/graph/snapshot", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "nodes" in data
    assert "edges" in data
    assert "meta" in data
    # Lock-in del contrato de graceful degradation: cuando AssetItem no
    # está registrado en ``models``, el resolver ``asset`` debe omitir
    # silenciosamente toda la sección (ver ``_asset_nodes`` guard).
    assert all(n["type"] != "asset" for n in data["nodes"]), (
        "asset-type nodes must be omitted when AssetItem is not registered"
    )


def test_graph_snapshot_with_pagination(client, db_session):
    _seed_admin(db_session)
    headers = _auth_headers(client)
    resp = client.get("/api/graph/snapshot?limit=5&offset=0", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "meta" in data
    assert "pagination" in data["meta"]
    assert data["meta"]["pagination"]["limit"] == 5
    assert all(n["type"] != "asset" for n in data["nodes"]), (
        "asset-type nodes must be omitted when AssetItem is not registered"
    )


def test_graph_snapshot_with_types(client, db_session):
    _seed_admin(db_session)
    headers = _auth_headers(client)
    resp = client.get("/api/graph/snapshot?types=persona", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "nodes" in data
    assert all(n["type"] != "asset" for n in data["nodes"]), (
        "asset-type nodes must be omitted when AssetItem is not registered"
    )


def test_graph_connections(client, db_session):
    admin, persona, sede = _seed_admin(db_session)
    headers = _auth_headers(client)

    resp = client.get("/api/graph/snapshot?limit=10", headers=headers)
    assert resp.status_code == 200
    nodes = resp.json()["nodes"]
    assert all(n["type"] != "asset" for n in nodes), (
        "asset-type nodes must be omitted when AssetItem is not registered"
    )

    if nodes:
        node_id = nodes[0]["id"]
        resp2 = client.get(
            f"/api/graph/connections/{node_id}", headers=headers
        )
        assert resp2.status_code == 200
        data = resp2.json()
        assert "node" in data
        assert "incoming" in data
        assert "outgoing" in data
    else:
        resp2 = client.get("/api/graph/connections/dummy-id", headers=headers)
        assert resp2.status_code == 404


def test_graph_connections_404(client, db_session):
    _seed_admin(db_session)
    headers = _auth_headers(client)
    resp = client.get("/api/graph/connections/nonexistent-id", headers=headers)
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Node not found"


# ── PEND-GRAPH-007: hardening de la política sentinel ─────────────────
# Cuando ``get_user_sede_id`` retorna None (usuario sin sede), la vista global
# sólo se permite a roles de plataforma. Estos tests anclan el contrato
# ``DECISION-GRAPH-SENTINEL-001 / PEND-GRAPH-007`` mediante mock del helper de
# sede (el seeding del conftest garantiza siempre sede asignada, por lo que
# mockear es la forma determinística de forzar el caso ``user_sede is None``).


def test_graph_sede_none_non_admin_raises_403(client, db_session):
    """Sin sede + rol no-admin (``Miembro``) ⇒ 403 con detail humano."""
    from unittest.mock import patch

    from tests.conftest import seed_user_with_role

    seed_user_with_role(
        db_session, role_name="Miembro", email="member@example.com"
    )
    headers = _auth_headers(client, email="member@example.com")

    with patch("backend.api.graph.get_user_sede_id", return_value=None):
        resp = client.get("/api/graph/snapshot?limit=1", headers=headers)

    assert resp.status_code == 403
    body = resp.json()
    assert "Vista global" in body["detail"]
    assert "sede" in body["detail"].lower()


def test_graph_sede_none_currently_returns_global(client, db_session):
    """§6.5 (post-hardening PEND-GRAPH-007): admin + sede_id=None ⇒ 200 con vista cross-sede.

    Lockin del comportamiento ``_enforce_graph_rbac`` para roles de
    plataforma: el guard retorna silenciosamente en el early-exit del
    rol-admin, el snapshot cubre todas las sedes. Si un PR futuro endurece
    sin actualizar esta política, este test rompe loudly.
    """
    from unittest.mock import patch

    _seed_admin(db_session)
    headers = _auth_headers(client)

    with patch("backend.api.graph.get_user_sede_id", return_value=None):
        resp = client.get("/api/graph/snapshot?limit=1", headers=headers)

    assert resp.status_code == 200
    data = resp.json()
    assert "nodes" in data
    assert "edges" in data
    assert "meta" in data


def test_graph_sede_none_empty_role_raises_403(client, db_session):
    """Edge case: ``role=""`` y ``rol_plataforma=None`` ⇒ 403 (blank-state).

    Usuario técnicamente válido pero sin ningún rol resoluble también debe
    caer en el path de 403. Esto cubre el caso "el seeding olvidó asignar
    rol_plataforma_id AND role no se setea explícitamente".
    """
    from unittest.mock import patch

    from tests.conftest import seed_user_with_role

    user, _, _ = seed_user_with_role(
        db_session,
        role_name="VOID_ROLE_NOT_IN_ALLOWLIST",
        email="norole@example.com",
    )
    # Forzar el estado vacío que activa el edge case del guard.
    user.role = ""
    user.rol_plataforma = None  # type: ignore[assignment]
    db_session.commit()

    headers = _auth_headers(client, email="norole@example.com")

    with patch("backend.api.graph.get_user_sede_id", return_value=None):
        resp = client.get("/api/graph/snapshot?limit=1", headers=headers)

    assert resp.status_code == 403
    assert "Vista global" in resp.json()["detail"]


def test_graph_sede_valid_filters_correctly(client, db_session):
    """§6.5: admin + sede_id válida ⇒ snapshot acotado a la sede del actor.

    Confirmación de Axioma 3 con el guard activo: el guard retorna
    silenciosamente en el early-exit (``user_sede is not None``); el
    snapshot contiene sólo nodos de la sede asignada por el seed_admin.
    Una validación cross-sede más estricta requiere un fixture con dos
    sedes explícitas (PEND-GRAPH-005a).
    """
    _seed_admin(db_session)
    headers = _auth_headers(client)

    resp = client.get("/api/graph/snapshot?limit=20", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "nodes" in data
    assert "meta" in data
    assert "pagination" in data["meta"]


def test_graph_sede_none_subset_types_still_global(client, db_session):
    """§6.5: admin + sede_id=None + ``?types=course`` ⇒ snapshot cross-sede filtrado.

    Interacción sentinel + pre-filtrado por tipo: el guard permite la vista
    global (admin), el servicio filtra sólo los nodos de tipo ``course``.
    """
    from unittest.mock import patch

    _seed_admin(db_session)
    headers = _auth_headers(client)

    with patch("backend.api.graph.get_user_sede_id", return_value=None):
        resp = client.get(
            "/api/graph/snapshot?types=course&limit=20", headers=headers
        )

    assert resp.status_code == 200
    data = resp.json()
    nodes = data.get("nodes", [])
    if nodes:
        assert all(n["type"] == "course" for n in nodes), (
            "subset filter must only yield nodes whose type matches the query"
        )
    assert "meta" in data
