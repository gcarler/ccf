"""Test suite for Governance module (Policies, Resolutions, Committees, Signatures)."""

from __future__ import annotations

import pytest

from tests.conftest import auth_headers, seed_admin


def test_governance_stats_endpoint(client, db_session):
    seed_admin(db_session, email="gov_admin@ccf.test", password="testpass123")
    headers = auth_headers(client, email="gov_admin@ccf.test", password="testpass123")

    resp = client.get("/api/governance/stats", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total_policies" in data
    assert "total_resolutions" in data
    assert "total_committees" in data


def test_policy_crud_lifecycle(client, db_session):
    seed_admin(db_session, email="gov_admin@ccf.test", password="testpass123")
    headers = auth_headers(client, email="gov_admin@ccf.test", password="testpass123")

    # 1. Create Policy
    payload = {
        "code": "POL-2026-TEST",
        "title": "Política de Prueba",
        "category": "OPERACIONAL",
        "content": "Contenido de la política de prueba.",
        "status": "BORRADOR",
    }
    resp = client.post("/api/governance/policies", json=payload, headers=headers)
    assert resp.status_code == 201
    policy = resp.json()
    assert policy["code"] == "POL-2026-TEST"
    policy_id = policy["id"]

    # 2. Get Policy
    resp = client.get(f"/api/governance/policies/{policy_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["title"] == "Política de Prueba"

    # 3. Update Policy
    resp = client.patch(
        f"/api/governance/policies/{policy_id}",
        json={"status": "APROBADA", "title": "Política Actualizada"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "APROBADA"

    # 4. List Policies
    resp = client.get("/api/governance/policies", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1

    # 5. Delete Policy
    resp = client.delete(f"/api/governance/policies/{policy_id}", headers=headers)
    assert resp.status_code == 204


def test_resolution_and_signature_lifecycle(client, db_session):
    seed_admin(db_session, email="gov_admin@ccf.test", password="testpass123")
    headers = auth_headers(client, email="gov_admin@ccf.test", password="testpass123")

    # 1. Create Resolution
    payload = {
        "number": "RES-2026-01",
        "title": "Resolución de Nombramiento",
        "summary": "Nombramiento del consejo pastoral.",
        "content": "Por medio de la presente acta se aprueba...",
        "status": "BORRADOR",
    }
    resp = client.post("/api/governance/resolutions", json=payload, headers=headers)
    assert resp.status_code == 201
    res = resp.json()
    res_id = res["id"]

    # 2. Get Resolution
    resp = client.get(f"/api/governance/resolutions/{res_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["number"] == "RES-2026-01"


def test_committee_lifecycle(client, db_session):
    seed_admin(db_session, email="gov_admin@ccf.test", password="testpass123")
    headers = auth_headers(client, email="gov_admin@ccf.test", password="testpass123")

    # 1. Create Committee
    payload = {
        "name": "Comité de Misiones y Evangelismo",
        "description": "Supervisión de proyectos misioneros.",
        "committee_type": "PASTORAL",
        "is_active": True,
    }
    resp = client.post("/api/governance/committees", json=payload, headers=headers)
    assert resp.status_code == 201
    comm = resp.json()
    comm_id = comm["id"]

    # 2. List Committees
    resp = client.get("/api/governance/committees", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1
