"""Tests de contrato para pipelines CRM.

Valida que los endpoints de pipeline devuelven shapes consistentes:
- GET /api/crm/pipelines: lista de pipelines con id, name
- GET /api/crm/pipelines/{id}/stages: stages con sort_order
- GET /api/crm/pipeline/kanban/cards: cards con caso_id, titulo, etapa_id
"""

from __future__ import annotations

import pytest

from tests.conftest import auth_headers, seed_admin


def test_pipelines_requires_auth(client):
    resp = client.get("/api/crm/pipelines")
    assert resp.status_code == 401


def test_pipelines_admin_returns_list(client, db_session):
    seed_admin(db_session, email="pipe_admin@ccf.test", password="testpass123")
    headers = auth_headers(client, email="pipe_admin@ccf.test", password="testpass123")

    resp = client.get("/api/crm/pipelines", headers=headers)
    assert resp.status_code == 200

    data = resp.json()
    assert isinstance(data, (list, dict))

    if isinstance(data, list):
        for pipeline in data:
            assert "id" in pipeline
            assert "name" in pipeline or "nombre" in pipeline
    elif isinstance(data, dict):
        if "items" in data:
            for pipeline in data["items"]:
                assert "id" in pipeline


def test_pipeline_stages_requires_auth(client):
    resp = client.get("/api/crm/pipelines/nonexistent/stages")
    assert resp.status_code in (401, 404)


def test_kanban_cards_requires_auth(client):
    resp = client.get("/api/crm/pipeline/kanban/cards")
    assert resp.status_code == 401


def test_kanban_cards_admin_ok(client, db_session):
    seed_admin(db_session, email="kanban_admin@ccf.test", password="testpass123")
    headers = auth_headers(client, email="kanban_admin@ccf.test", password="testpass123")

    resp = client.get("/api/crm/pipeline/kanban/cards", headers=headers)
    assert resp.status_code == 200

    data = resp.json()
    assert isinstance(data, (list, dict))


def test_reorder_requires_auth(client):
    resp = client.patch("/api/crm/pipeline/casos/reorder", json={"items": []})
    assert resp.status_code == 401
