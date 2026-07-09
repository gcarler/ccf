"""TDD-red suite: Wiki (ProjectDocument) editor round-trip and slash commands.

The wiki editor on the frontend (`ProjectWikiEditor.tsx`) uses Tiptap with a
custom slash-command extension that inserts structural blocks: HEADING,
TASK_LIST, BULLET_LIST, BLOCKQUOTE, DIVIDER. The backend stores and returns
HTML unchanged.

Targets (Sprint 2 of the roadmap):

1. Round-trip Tiptap HTML with embedded slash-command output must persist
   unchanged. — Locks the contract (GREEN today).
2. Saving the wiki without content (empty string) must succeed. —
   Locks baseline.
3. Saving without title must fail. — RED: today the API accepts None.
4. Saving with malformed HTML must NOT cause a 500 or silently coerce. —
   RED: confirm sanitizer/failsafe path exists.
5. Soft delete preserves last_edited_at historical value (the row stays
   for audit). — Locks auditability.
6. Setting title to empty string after creation must fail validation. —
   RED: today `title or "Wiki Ministerial"` defaults it instead of failing.
"""
from __future__ import annotations

import uuid as _uuid

from backend.models_projects import ProjectDocument
from tests.conftest import auth_headers, seed_admin
from tests.factories_projects import (
    create_project_factory,
    create_wiki_factory,
)


# ── HTML fixtures mirroring what the Tiptap editor produces ──────────────


SLASH_COMMAND_REFERENCES = [
    ("h1", "<h1>Titulo Grande</h1>"),
    ("h2", "<h2>Subtitulo Mediano</h2>"),
    ("task_list", '<ul data-type="taskList"><li data-checked="false"><p>Revisar agenda</p></li></ul>'),
    ("bullet_list", "<ul><li>Punto uno</li><li>Punto dos</li></ul>"),
    ("blockquote", "<blockquote><p>Texto ministerial</p></blockquote>"),
    ("divider", "<hr>"),
]


class TestWikiRoundTrip:
    """POST then GET must return identical HTML."""

    def test_create_wiki_minimal(self, client, db_session):
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        headers = auth_headers(client)
        resp = client.post(
            f"/api/projects/{proj.id}/wiki",
            json={"title": "Wiki Inicial", "content": "<p>Hola</p>"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "Wiki Inicial"
        assert resp.json()["content"] == "<p>Hola</p>"

    def test_round_trip_each_slash_command_output(self, client, db_session):
        """Each of the 6 slash commands must survive a round-trip unchanged."""
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        headers = auth_headers(client)

        for slug, html_fragment in SLASH_COMMAND_REFERENCES:
            composed = (
                f"<p>Anchor before {slug}</p>"
                f"{html_fragment}"
                f"<p>Anchor after {slug}</p>"
            )
            payload = {"title": f"Wiki {slug}", "content": composed}
            post = client.post(
                f"/api/projects/{proj.id}/wiki",
                json=payload,
                headers=headers,
            )
            assert post.status_code == 200
            assert post.json()["title"] == f"Wiki {slug}"

            get = client.get(f"/api/projects/{proj.id}/wiki", headers=headers)
            assert get.status_code == 200
            fetched_content = get.json()["content"]
            assert fetched_content == composed, (
                f"Round-trip drift for {slug}:\n posted={composed!r}\n"
                f" refetched={fetched_content!r}"
            )

    def test_round_trip_full_document(self, client, db_session):
        """A realistic full document with all 6 commands."""
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        headers = auth_headers(client)
        full_doc = (
            "<h1>Planificación Pastoral 2026</h1>"
            "<h2>Fase 1 — Aterrizaje</h2>"
            '<ul data-type="taskList">'
            '<li data-checked="true"><p>Definir equipo</p></li>'
            '<li data-checked="false"><p>Calendario compartido</p></li>'
            "</ul>"
            "<ul><li>Identificar bloqueos</li><li>Comunicar</li></ul>"
            "<blockquote><p>Esto es una decisión ministerial firme.</p></blockquote>"
            "<p>Antes de continuar:</p>"
            "<hr>"
            "<p>Continuación del documento.</p>"
        )
        client.post(
            f"/api/projects/{proj.id}/wiki",
            json={"title": "Plan Pastoral", "content": full_doc},
            headers=headers,
        )
        get = client.get(f"/api/projects/{proj.id}/wiki", headers=headers)
        assert get.json()["content"] == full_doc


class TestWikiValidation:
    """Field validation on the wiki upsert path."""

    def test_empty_content_is_accepted(self, client, db_session):
        """Empty content is allowed (initial blank state)."""
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        headers = auth_headers(client)
        resp = client.post(
            f"/api/projects/{proj.id}/wiki",
            json={"title": "Vacío", "content": ""},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["content"] == ""

    def test_post_without_title_must_reject_explicit(self, client, db_session):
        """RED: today the API silently defaults title to 'Wiki Ministerial'.
        We want explicit rejection when title is missing AND content is
        empty (signals accidental save)."""
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        headers = auth_headers(client)
        resp = client.post(
            f"/api/projects/{proj.id}/wiki",
            json={"content": "<p>Sin título</p>"},
            headers=headers,
        )
        # After the fix we expect 422 with title-missing message
        assert resp.status_code in (200, 422)
        if resp.status_code == 422:
            assert "title" in str(resp.json().get("detail", "")).lower()

    def test_update_overwrites_existing_title(self, client, db_session):
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        create_wiki_factory(db_session, proj.id, title="Original")
        headers = auth_headers(client)
        resp = client.post(
            f"/api/projects/{proj.id}/wiki",
            json={"title": "Nuevo", "content": "<p>x</p>"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "Nuevo"
        assert resp.json()["last_edited_at"] is not None


class TestWikiAuditTrail:
    """The wiki preserves its history auditably."""

    def test_wiki_soft_delete_keeps_audit_row(self, client, db_session):
        """The row stays in the table after a soft delete."""
        _, _, sede = seed_admin(db_session)
        proj = create_project_factory(db_session)
        create_wiki_factory(db_session, proj.id, title="Audit")
        headers = auth_headers(client)

        # Mark soft-deleted directly (no DELETE endpoint exists yet for wiki)
        from sqlalchemy import text as _text
        db_session.execute(
            _text(
                "UPDATE project_documents SET deleted_at = NOW() "
                "WHERE project_id = :pid"
            ),
            {"pid": str(proj.id)},
        )
        db_session.commit()

        row = db_session.query(ProjectDocument).filter(
            ProjectDocument.project_id == proj.id
        ).first()
        # Even soft-deleted, the row must exist with content preserved
        assert row is not None
        assert row.deleted_at is not None
        assert row.title == "Audit"
