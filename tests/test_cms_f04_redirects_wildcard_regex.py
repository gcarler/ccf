"""F-04 (errorescms.md): CmsRedirect wildcard/regex support.

Antes, ``CmsRedirect.from_path`` solo hacia match exacto contra el path
incoming. No habia forma de configurar redirects genericos como
``/old/*`` → ``/new/``, ni patrones regex para URLs viejas.

Fix: ``match_type`` (exact/wildcard/regex) + ``priority`` Integer.
Helper ``resolve_redirect(db, *, site_key, path)`` aplica matching por
prioridad exact > wildcard > regex.  Endpoint ``GET /resolve-redirect``
expone la capability.

Tests:
  1) CRUD-direct: exact match resuelve
  2) CRUD-direct: wildcard con ``*`` resuelve
  3) CRUD-direct: regex con grupos de captura resuelve y sustituye $1/$2
  4) CRUD-direct: prioridad exact > wildcard > regex (gana el exact)
  5) CRUD-direct: regex invalido se salta defensivamente (no exception)
  6) CRUD-direct: inactivo no matchea
  7) API: POST redirect con match_type invalido -> 422
  8) API: POST redirect con regex invalido -> 422
  9) API: list_redirects expone match_type/priority
  10) API: GET /resolve-redirect retorna 404 cuando no match
"""
from __future__ import annotations

import uuid as _uuid

import pytest

from backend.api.enterprise_cms import resolve_redirect
from backend.models_enterprise import CmsRedirect
from tests.conftest import auth_headers, seed_admin


@pytest.fixture(scope="function")
def authed_client(client, db_session):
    """Client with authenticated admin user (mirror del de test_enterprise_cms)."""
    seed_admin(db_session)  # user admin@example.com
    headers = auth_headers(client)
    return client, headers, None


def _seed(db_session, email="cmsF04@example.com"):
    admin, persona, sede = seed_admin(
        db_session, email=email, password="testpass123"
    )
    return admin, persona, sede


def _make_redirect(
    db_session,
    *,
    site_key="ccf",
    from_path="/old",
    to_path="/new",
    match_type="exact",
    priority=0,
    is_active=True,
    status_code=301,
):
    r = CmsRedirect(
        id=_uuid.uuid4(),
        site_key=site_key,
        from_path=from_path,
        to_path=to_path,
        status_code=status_code,
        is_active=is_active,
        match_type=match_type,
        priority=priority,
    )
    db_session.add(r)
    db_session.flush()
    return r


# ── CRUD-direct (helper resolve_redirect, sin HTTP stack) ─────────


class TestF04ResolveRedirect:
    def test_exact_match_resolves(self, db_session):
        _seed(db_session, email="cmsF04exact@example.com")
        _make_redirect(db_session, from_path="/old-page", to_path="/new-page")

        match = resolve_redirect(db_session, site_key="ccf", path="/old-page")
        assert match is not None
        assert match["to_path"] == "/new-page"
        assert match["match_type"] == "exact"

    def test_wildcard_match_resolves(self, db_session):
        _seed(db_session, email="cmsF04wild@example.com")
        _make_redirect(
            db_session,
            from_path="/blog/*",
            to_path="/noticias/",
            match_type="wildcard",
        )

        match = resolve_redirect(db_session, site_key="ccf", path="/blog/2024/resumen")
        assert match is not None
        assert match["to_path"] == "/noticias/"
        assert match["match_type"] == "wildcard"

    def test_regex_match_with_capture_groups(self, db_session):
        _seed(db_session, email="cmsF04regex@example.com")
        # Regex captura el año y el slug
        _make_redirect(
            db_session,
            from_path=r"^/posts/(\d{4})/(\w+)/?$",
            to_path="/articulos/$1/$2",
            match_type="regex",
        )

        match = resolve_redirect(db_session, site_key="ccf", path="/posts/2024/resumen")
        assert match is not None
        assert match["to_path"] == "/articulos/2024/resumen"
        assert match["match_type"] == "regex"

    def test_priority_exact_beats_wildcard_beats_regex(self, db_session):
        _seed(db_session, email="cmsF04prio@example.com")
        # Tres redirects para el mismo path; el exact debe ganar
        _make_redirect(
            db_session,
            from_path="/page",
            to_path="/from-regex",
            match_type="regex",
            priority=100,  # Aunque más prioritario, regex pierde contra exact
        )
        _make_redirect(
            db_session,
            from_path="/page*",
            to_path="/from-wildcard",
            match_type="wildcard",
            priority=100,
        )
        _make_redirect(
            db_session,
            from_path="/page",
            to_path="/from-exact",
            match_type="exact",
            priority=0,  # Exacto con menor priority sigue ganando
        )

        match = resolve_redirect(db_session, site_key="ccf", path="/page")
        assert match is not None
        assert match["match_type"] == "exact"
        assert match["to_path"] == "/from-exact"

    def test_invalid_regex_skipped_defensively(self, db_session):
        _seed(db_session, email="cmsF04invalid@example.com")
        # Regex roto: ``[`` sin cerrar.  No debe romper resolve_redirect.
        _make_redirect(
            db_session,
            from_path="[unclosed",
            to_path="/unreachable",
            match_type="regex",
        )

        match = resolve_redirect(db_session, site_key="ccf", path="/foo")
        # Ningún match válido → None, no exception
        assert match is None

    def test_inactive_redirect_does_not_match(self, db_session):
        _seed(db_session, email="cmsF04inactive@example.com")
        _make_redirect(
            db_session,
            from_path="/disabled",
            to_path="/enabled",
            is_active=False,
        )

        match = resolve_redirect(db_session, site_key="ccf", path="/disabled")
        assert match is None

    def test_no_redirect_returns_none(self, db_session):
        _seed(db_session, email="cmsF04none@example.com")
        # Sin redirects insertados

        match = resolve_redirect(db_session, site_key="ccf", path="/does-not-exist")
        assert match is None

    def test_priority_within_same_match_type(self, db_session):
        _seed(db_session, email="cmsF04same@example.com")
        # Dos wildcard matches; el de mayor priority debe ganar
        _make_redirect(
            db_session,
            from_path="/docs/**",
            to_path="/low-priority",
            match_type="wildcard",
            priority=5,
        )
        _make_redirect(
            db_session,
            from_path="/docs/*",
            to_path="/high-priority",
            match_type="wildcard",
            priority=10,
        )

        # path "/docs/guide" matchea ambos wildcards; el de mayor priority gana
        # Nota: fnmatch no soporta ** diríasaá*, así que patrones se interpretan literal.
        # "/docs/*" sí matchea "/docs/guide"; "/docs/**" también matchea (como "/docs/")
        match = resolve_redirect(db_session, site_key="ccf", path="/docs/guide")
        assert match is not None
        assert match["to_path"] == "/high-priority"


# ── API-level (endpoint POST/GET validation) ─────────────────────


class TestF04Api:
    def test_post_invalid_match_type_returns_422(self, authed_client):
        client, headers, _ = authed_client
        resp = client.post("/api/cms/v2/redirects", headers=headers, json={
            "site_key": "ccf",
            "from_path": "/test",
            "to_path": "/target",
            "match_type": "invalid-type",  # No permitido
        })
        assert resp.status_code == 422

    def test_post_invalid_regex_returns_422(self, authed_client):
        client, headers, _ = authed_client
        resp = client.post("/api/cms/v2/redirects", headers=headers, json={
            "site_key": "ccf",
            "from_path": "[unclosed-bracket",  # Regex inválido
            "to_path": "/invalid",
            "match_type": "regex",
        })
        assert resp.status_code == 422

    def test_post_valid_regex_returns_200(self, authed_client):
        client, headers, _ = authed_client
        resp = client.post("/api/cms/v2/redirects", headers=headers, json={
            "site_key": "ccf",
            "from_path": r"^/posts/(\d{4})/?$",
            "to_path": "/archive/$1",
            "match_type": "regex",
        })
        assert resp.status_code == 200

    def test_post_valid_wildcard_returns_200(self, authed_client):
        client, headers, _ = authed_client
        resp = client.post("/api/cms/v2/redirects", headers=headers, json={
            "site_key": "ccf",
            "from_path": "/legacy/*",
            "to_path": "/modern/",
            "match_type": "wildcard",
        })
        assert resp.status_code == 200

    def test_list_redirects_exposes_match_type_and_priority(self, authed_client):
        client, headers, _ = authed_client
        # Crear un redirect exacto (default)
        client.post("/api/cms/v2/redirects", headers=headers, json={
            "site_key": "ccf",
            "from_path": "/list-test",
            "to_path": "/list-target",
        })

        resp = client.get("/api/cms/v2/redirects?site_key=ccf", headers=headers)
        assert resp.status_code == 200
        items = resp.json()
        assert isinstance(items, list)
        matching = [r for r in items if r["from_path"] == "/list-test"]
        assert matching, "redirect listado debe contener el redirect recién creado"
        r = matching[0]
        assert "match_type" in r
        assert "priority" in r
        assert r["match_type"] == "exact"
        assert r["priority"] == 0


# ── API resolve-redirect endpoint (147) ──────────────────────────


class TestF04ResolveEndpoint:
    def test_resolve_returns_match(self, authed_client):
        client, headers, _ = authed_client
        client.post("/api/cms/v2/redirects", headers=headers, json={
            "site_key": "ccf",
            "from_path": "/resolve-me",
            "to_path": "/resolved",
            "match_type": "exact",
        })

        resp = client.get(
            "/api/cms/v2/resolve-redirect?site_key=ccf&path=/resolve-me",
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["to_path"] == "/resolved"
        assert data["match_type"] == "exact"

    def test_resolve_no_match_returns_404(self, authed_client):
        client, headers, _ = authed_client
        resp = client.get(
            "/api/cms/v2/resolve-redirect?site_key=ccf&path=/no-redirects-here",
            headers=headers,
        )
        assert resp.status_code == 404

    def test_resolve_regex_with_capture(self, authed_client):
        client, headers, _ = authed_client
        client.post("/api/cms/v2/redirects", headers=headers, json={
            "site_key": "ccf",
            "from_path": r"^/p/(.*)$",
            "to_path": "/post/$1",
            "match_type": "regex",
        })

        resp = client.get(
            "/api/cms/v2/resolve-redirect?site_key=ccf&path=/p/hola-mundo",
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["to_path"] == "/post/hola-mundo"
