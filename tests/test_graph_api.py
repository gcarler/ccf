import uuid
from datetime import datetime, timezone

import pytest
from backend import models
from backend.core.security import get_password_hash


def _seed_sede(db_session):
    sede = models.Sede(
        id=uuid.uuid4(), nombre="Test Sede", ciudad="Bogota", es_activa=True
    )
    db_session.add(sede)
    db_session.commit()
    db_session.refresh(sede)
    return sede


def _seed_admin(db_session, email="test@example.com", password="testpass123"):
    user = models.User(
        username=email.split("@")[0],
        email=email,
        password_hash=get_password_hash(password),
        role="admin",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    sede = _seed_sede(db_session)

    persona = models.Persona(
        id=uuid.uuid4(),
        user_id=user.id,
        first_name="Test",
        last_name="User",
        email=email,
        sede_id=sede.id,
    )
    db_session.add(persona)
    db_session.commit()
    return user, persona, sede


def _auth_headers(client, email="test@example.com", password="testpass123"):
    resp = client.post(
        "/api/auth/login",
        data={"username": email, "password": password, "grant_type": "password"},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.xfail(
    reason="build_graph_snapshot references missing models.AssetItem", strict=False
)
def test_graph_snapshot(client, db_session):
    _seed_admin(db_session)
    headers = _auth_headers(client)
    resp = client.get("/api/graph/snapshot", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "nodes" in data
    assert "edges" in data
    assert "meta" in data


@pytest.mark.xfail(
    reason="build_graph_snapshot references missing models.AssetItem", strict=False
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


@pytest.mark.xfail(
    reason="build_graph_snapshot references missing models.AssetItem", strict=False
)
def test_graph_snapshot_with_types(client, db_session):
    _seed_admin(db_session)
    headers = _auth_headers(client)
    resp = client.get("/api/graph/snapshot?types=persona", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "nodes" in data


@pytest.mark.xfail(
    reason="build_graph_snapshot references missing models.AssetItem", strict=False
)
def test_graph_connections(client, db_session):
    admin, persona, sede = _seed_admin(db_session)
    headers = _auth_headers(client)

    resp = client.get("/api/graph/snapshot?limit=10", headers=headers)
    assert resp.status_code == 200
    nodes = resp.json()["nodes"]

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


@pytest.mark.xfail(
    reason="build_graph_snapshot references missing models.AssetItem", strict=False
)
def test_graph_connections_404(client, db_session):
    _seed_admin(db_session)
    headers = _auth_headers(client)
    resp = client.get("/api/graph/connections/nonexistent-id", headers=headers)
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Node not found"
