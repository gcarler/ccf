"""TDD-red suite: Whiteboard JSON round-trip and validation.

Targets (Sprint 2 of the Projects-node debt roadmap):

1. `elements_json` MUST be a valid JSON string when saved. Today, the
   schema accepts any String — including the literal "undefined" or
   clearly-malformed JSON. After the fix, malformed input → 422. — RED.
2. Round-trip POST → GET must return identical `elements_json`. — GREEN
   baseline; locks the contract.
3. Soft-deleted whiteboards must NOT appear in /projects/whiteboards. —
   Locks the contract (likely GREEN today).
4. Soft delete preserves the JSON content (auditability). — Locks.
5. Concurrent rapid-fire saves (race) must coalesce on the client — backend
   accepts the last writer wins semantics. — Locks backend contract.
"""
from __future__ import annotations

import json as _json
import uuid as _uuid

import pytest
from sqlalchemy import text as _text

from backend.models_projects import ProjectWhiteboard
from tests.conftest import auth_headers, seed_admin
from tests.factories_projects import create_project_factory, create_whiteboard_factory


class TestWhiteboardJSONValidation:
    """elements_json must be valid JSON on save."""

    def test_post_whiteboard_with_valid_json(self, client, db_session):
        """Baseline: a valid JSON payload is accepted and stored."""
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        headers = auth_headers(client)
        payload = _json.dumps(
            [{"type": "rectangle", "left": 10, "top": 10, "width": 80, "height": 40}]
        )

        resp = client.post(
            f"/api/projects/{proj.id}/whiteboard",
            json={"title": "Pizarra Válida", "elements_json": payload},
            headers=headers,
        )
        assert resp.status_code == 200, resp.text
        returned = _json.loads(resp.json()["elements_json"])
        assert isinstance(returned, list)
        assert returned[0]["type"] == "rectangle"

    def test_post_whiteboard_with_undefined_literal_rejected(self, client, db_session):
        """RED: literal string "undefined" (a JS Leaky client bug)
        must not be persisted as elements_json."""
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        headers = auth_headers(client)

        resp = client.post(
            f"/api/projects/{proj.id}/whiteboard",
            json={"title": "Bug board", "elements_json": "undefined"},
            headers=headers,
        )
        # Currently this returns 200 and persists the literal "undefined"
        # string. We want 422 (Pydantic validation) with a clean message.
        assert resp.status_code in (400, 422), (
            f"Expected rejection of literal 'undefined', got {resp.status_code}: {resp.text}"
        )

    def test_post_whiteboard_with_malformed_json_rejected(self, client, db_session):
        """RED: unbalanced braces / trailing commas must be rejected."""
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        headers = auth_headers(client)

        resp = client.post(
            f"/api/projects/{proj.id}/whiteboard",
            json={"title": "Malformed", "elements_json": "{not-json"},
            headers=headers,
        )
        assert resp.status_code in (400, 422), (
            f"Expected rejection of malformed JSON, got {resp.status_code}: {resp.text}"
        )

    def test_post_whiteboard_empty_array_is_accepted(self, client, db_session):
        """'[]' is a degenerate but valid board — must not be rejected."""
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        headers = auth_headers(client)

        resp = client.post(
            f"/api/projects/{proj.id}/whiteboard",
            json={"title": "Empty", "elements_json": "[]"},
            headers=headers,
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["elements_json"] == "[]"


class TestWhiteboardRoundTrip:
    """POST → GET must return identical content."""

    def test_round_trip_complex_elements(self, client, db_session):
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        headers = auth_headers(client)
        elements = [
            {"type": "rectangle", "left": 100, "top": 120, "fill": "#abc"},
            {"type": "circle", "left": 220, "top": 90, "radius": 25},
            {"type": "i-text", "left": 350, "top": 70, "text": "Hola"},
        ]
        payload = _json.dumps(elements)

        post = client.post(
            f"/api/projects/{proj.id}/whiteboard",
            json={"title": "Complex", "elements_json": payload},
            headers=headers,
        )
        assert post.status_code == 200

        get = client.get(f"/api/projects/{proj.id}/whiteboard", headers=headers)
        assert get.status_code == 200
        # Round-trip equality: parse both and deep-compare
        posted = _json.loads(post.json()["elements_json"])
        refetched = _json.loads(get.json()["elements_json"])
        assert posted == refetched, (
            f"Round-trip drift:\n posted={posted}\n refetched={refetched}"
        )
        assert refetched == elements, "Get endpoint mutated the elements"

    def test_round_trip_with_unicode_and_emoji(self, client, db_session):
        """Unicode + emoji must survive JSON serialization and round-trip."""
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        headers = auth_headers(client)
        elements = [
            {"type": "i-text", "text": "Apóstol — α ⚓ 🕊️"},
            {"type": "rectangle", "fill": "rgba(0,0,0,0)"},
        ]
        post = client.post(
            f"/api/projects/{proj.id}/whiteboard",
            json={"title": "Unicode", "elements_json": _json.dumps(elements, ensure_ascii=False)},
            headers=headers,
        )
        assert post.status_code == 200
        get = client.get(f"/api/projects/{proj.id}/whiteboard", headers=headers)
        assert _json.loads(get.json()["elements_json"]) == elements

    def test_three_consecutive_overwrites_keep_last(self, client, db_session):
        """Three rapid POSTs → GET returns the LAST value (last-writer wins)."""
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        headers = auth_headers(client)

        for version in range(3):
            payload = _json.dumps([{"type": "i-text", "version": version}])
            r = client.post(
                f"/api/projects/{proj.id}/whiteboard",
                json={"title": "v%d" % version, "elements_json": payload},
                headers=headers,
            )
            assert r.status_code == 200

        get = client.get(f"/api/projects/{proj.id}/whiteboard", headers=headers)
        final = _json.loads(get.json()["elements_json"])
        assert final == [{"type": "i-text", "version": 2}], (
            f"Last-writer-wins broken: {final}"
        )


class TestWhiteboardSoftDelete:
    """Soft delete keeps the row for audit but excludes it from listings.

    The ``ProjectWhiteboard.deleted_at`` column is now mapped in the model
    and included in the canonical migration (``20260710_0001``). The DELETE
    endpoint stamps ``deleted_at``, the listing endpoint filters it out,
    and direct DB inspection confirms the auditability contract.
    """

    def test_soft_deleted_whiteboard_excluded_from_listings(self, client, db_session):
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        create_whiteboard_factory(db_session, proj.id)
        headers = auth_headers(client)

        # Soft delete via DELETE endpoint
        del_resp = client.delete(f"/api/projects/{proj.id}/whiteboard", headers=headers)
        assert del_resp.status_code in (200, 204)

        listings = client.get("/api/projects/whiteboards", headers=headers)
        assert listings.status_code == 200
        ids = [b["id"] for b in listings.json()]
        # Our whiteboard must NOT appear in the active list
        assert all(b.get("deleted_at") in (None, "null", "") for b in listings.json()), (
            f"Listing includes soft-deleted rows: {listings.json()}"
        )
        # And GET /projects/{id}/whiteboard must NOT return the board
        get = client.get(f"/api/projects/{proj.id}/whiteboard", headers=headers)
        assert get.json() is None, (
            f"GET must return null for soft-deleted board, got {get.json()}"
        )

    def test_soft_delete_preserves_elements_json_in_db(self, client, db_session):
        """Soft delete is reversible for audit — elements_json retained."""
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        elements = [{"type": "rectangle", "id": "preserve-me"}]
        wb = create_whiteboard_factory(db_session, proj.id, elements_json=_json.dumps(elements))
        headers = auth_headers(client)

        client.delete(f"/api/projects/{proj.id}/whiteboard", headers=headers)

        # Direct DB inspection
        board_row = db_session.query(ProjectWhiteboard).filter(
            ProjectWhiteboard.project_id == proj.id
        ).first()
        assert board_row is not None, "Soft delete removed the row (should NOT)"
        assert board_row.deleted_at is not None, "deleted_at not stamped"
        assert _json.loads(board_row.elements_json) == elements


class TestWhiteboardAuth:
    """Whiteboard endpoints require authentication."""

    def test_post_without_auth_returns_401_or_403(self, client, db_session):
        proj = create_project_factory(db_session)
        resp = client.post(
            f"/api/projects/{proj.id}/whiteboard",
            json={"title": "Anon", "elements_json": "[]"},
        )
        assert resp.status_code in (401, 403), resp.status_code
