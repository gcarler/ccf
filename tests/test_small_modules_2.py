"""
Tests for remaining small modules: community, donations, graph.
"""

from __future__ import annotations

import uuid

import pytest

from backend import models
from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin


def _ok(status):
    return status in (200, 201, 204)


@pytest.fixture
def full(client, db_session):
    admin, _, _ = _seed_admin(db_session, email="small2@test.com")
    headers = _auth_headers(client, email="small2@test.com", password="testpass123")
    return {"c": client, "h": headers, "s": db_session.query(models.Sede).first()}


class TestCommunity:
    def test_cards_list(self, full):
        assert _ok(full["c"].get("/api/community/cards", headers=full["h"]).status_code)

    def test_grupos_list(self, full):
        assert _ok(full["c"].get("/api/community/grupos", headers=full["h"]).status_code)

    def test_events_list(self, full):
        assert _ok(full["c"].get("/api/community/events", headers=full["h"]).status_code)

    def test_create_card(self, full, db_session):
        c, h, s = full["c"], full["h"], full["s"]
        p = models.Persona(id=uuid.uuid4(), first_name="T", last_name="U", sede_id=s.id)
        db_session.add(p)
        db_session.commit()
        assert _ok(
            c.post(
                "/api/community/cards", json={"title": "Card", "content": "Hi", "column_id": "col1"}, headers=h
            ).status_code
        )

    def test_create_grupo(self, full):
        assert _ok(
            full["c"]
            .post("/api/community/grupos", json={"name": f"CG-{uuid.uuid4().hex[:6]}"}, headers=full["h"])
            .status_code
        )


class TestDonations:
    def test_list(self, full):
        assert _ok(full["c"].get("/api/donations", headers=full["h"]).status_code)

    def test_summary(self, full):
        assert _ok(full["c"].get("/api/donations/summary", headers=full["h"]).status_code)


class TestGraph:
    def test_snapshot(self, full):
        assert _ok(full["c"].get("/api/graph/snapshot", headers=full["h"]).status_code)


class TestWiki:
    def test_get_page_not_found(self, full):
        assert full["c"].get("/api/wiki/nonexistent", headers=full["h"]).status_code == 404

    def test_get_content_not_found(self, full):
        assert full["c"].get("/api/cms/content/nonexistent", headers=full["h"]).status_code == 404
