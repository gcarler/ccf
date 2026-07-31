"""Axioma 3 — Fase 5: Multi-Tenant isolation tests for CMS User-Generated Content.

Cubre el conjunto de leaks identified en el audit (Axioma 3 Fase 5 — CMS):

  1. **CRÍTICO — IDOR fix en ``cms_pastoral_profile_update``**: un editor CMS
     con rol ``cms:edit`` en sede_a YA no puede mutar ``photo_url`` /
     ``bio_full`` / ``social_*`` / ``is_main_pastor`` / ``is_pastoral_leader``
     de una pastor de sede_b via PATCH /api/cms/v2/cms/pastoral-team/{id}.

  2. **CmsMediaItem (admin)**: idem para media items — listings y CRUD
     scoped por sede.

  3. **Public pastoral team**: sigue retornando datos globales (es un
     endpoint público), pero documentado.

NOTE: v1 testimonials/announcements endpoints were removed — the frontend
now consumes the v2 API directly. Correlation tests for those endpoints
are deleted; metrics scope is covered in test_cms_metrics_sede_isolation.py.
"""

from __future__ import annotations

import uuid as _uuid

from backend import models
from backend.management.seed_user_permissions import seed_rol_plataforma
from tests.conftest import auth_headers, seed_admin, seed_user_with_role

# ── Helpers ────────────────────────────────────────────────────────────────


def _seed_two_sedes(db_session):
    admin_a, persona_a, sede_a = seed_admin(db_session, email="cmsFase5A@example.com", password="testpass123")
    admin_b, persona_b, sede_b = seed_admin(db_session, email="cmsFase5B@example.com", password="testpass123")
    assert sede_a.id != sede_b.id
    return (admin_a, persona_a, sede_a), (admin_b, persona_b, sede_b)


def _persona_in(db, sede_id, email_suffix):
    suffix_email = f"{email_suffix}-{_uuid.uuid4().hex[:8]}@example.com"
    p = models.Persona(
        id=_uuid.uuid4(),
        first_name=f"User-{email_suffix}",
        last_name="Test",
        email=suffix_email,
        sede_id=sede_id,
        estado_vital="ACTIVO",
    )
    db.add(p)
    db.flush()
    return p


def _seed_lector_same_sede(db_session, email, sede_id):
    seed_rol_plataforma(db_session)
    return seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email=email,
        password="testpass123",
        sede_id=sede_id,
    )


def _pastor_in(db, sede_id, name_suffix, is_main_pastor=False):
    p = models.Persona(
        id=_uuid.uuid4(),
        first_name=f"Pastor-{name_suffix}",
        last_name="Leader",
        email=f"pastor-{name_suffix}-{_uuid.uuid4().hex[:8]}@example.com",
        sede_id=sede_id,
        estado_vital="ACTIVO",
        is_pastoral_leader=True,
        is_main_pastor=is_main_pastor,
    )
    db.add(p)
    db.flush()
    return p


# ════════════════════════════════════════════════════════════════════════════
# 1) cms_pastoral_profile_update — IDOR crítico FIX
# ════════════════════════════════════════════════════════════════════════════


def test_cms_pastoral_profile_update_blocks_cross_sede_idor(client, db_session):
    (admin_a, _, _), (admin_b, _, sede_b) = _seed_two_sedes(db_session)
    pastor_b = _pastor_in(db_session, sede_b.id, "idor-target-b", is_main_pastor=True)
    db_session.commit()
    db_session.refresh(pastor_b)
    original_photo = pastor_b.photo_url
    original_bio = pastor_b.bio_full

    headers_a = auth_headers(client, email="cmsFase5A@example.com")
    resp = client.patch(
        f"/api/cms/v2/cms/pastoral-team/{pastor_b.id}",
        headers=headers_a,
        json={
            "photo_url": "https://attacker.example.com/hijacked.png",
            "bio_full": "BIO INYECTADA POR ATTACKER cross-sede",
            "is_main_pastor": True,
        },
    )
    assert resp.status_code == 404, (
        f"LEAK IDOR: admin A editó pastor de sede_b → status {resp.status_code}; body={resp.text}"
    )
    assert "BIO INYECTADA" not in resp.text

    db_session.refresh(pastor_b)
    assert pastor_b.photo_url == original_photo
    assert pastor_b.bio_full == original_bio


def test_cms_pastoral_profile_update_allows_local_pastor(client, db_session):
    (admin_a, persona_a, sede_a), _ = _seed_two_sedes(db_session)
    pastor_a = _pastor_in(db_session, sede_a.id, "idor-local-a")
    db_session.commit()
    db_session.refresh(pastor_a)

    headers_a = auth_headers(client, email="cmsFase5A@example.com")
    resp = client.patch(
        f"/api/cms/v2/cms/pastoral-team/{pastor_a.id}",
        headers=headers_a,
        json={"bio_short": "Pastor local actualizado"},
    )
    assert resp.status_code == 200, (
        f"Regresión: admin A no pudo editar pastor local (status {resp.status_code}): {resp.text}"
    )
    db_session.refresh(pastor_a)
    assert pastor_a.bio_short == "Pastor local actualizado"


def test_cms_pastoral_team_list_filters_by_user_sede(client, db_session):
    (admin_a, persona_a, sede_a), (_, persona_b, sede_b) = _seed_two_sedes(db_session)
    pastor_a1 = _pastor_in(db_session, sede_a.id, "list-local-a1")
    pastor_a2 = _pastor_in(db_session, sede_a.id, "list-local-a2")
    pastor_b1 = _pastor_in(db_session, sede_b.id, "list-cross-b1")
    db_session.commit()

    headers_a = auth_headers(client, email="cmsFase5A@example.com")
    resp = client.get("/api/cms/v2/cms/pastoral-team", headers=headers_a)
    assert resp.status_code == 200, resp.text
    ids = {item["id"] for item in resp.json()}
    assert str(pastor_a1.id) in ids
    assert str(pastor_a2.id) in ids
    assert str(pastor_b1.id) not in ids


def test_cms_pastoral_team_list_allows_both_for_superadmin(client, db_session, monkeypatch):
    (admin_a, persona_a, sede_a), (_, persona_b, sede_b) = _seed_two_sedes(db_session)
    pastor_a = _pastor_in(db_session, sede_a.id, "superadmin-list-a")
    pastor_b = _pastor_in(db_session, sede_b.id, "superadmin-list-b")
    db_session.commit()

    from backend.api._cms_helpers import _shared as _cms_shared_module

    monkeypatch.setattr(
        _cms_shared_module,
        "_actor_sede_or_none",
        lambda db, current_user: None,
    )

    headers_a = auth_headers(client, email="cmsFase5A@example.com")
    resp = client.get("/api/cms/v2/cms/pastoral-team", headers=headers_a)
    assert resp.status_code == 200, resp.text
    ids = {item["id"] for item in resp.json()}
    assert str(pastor_a.id) in ids
    assert str(pastor_b.id) in ids


# ════════════════════════════════════════════════════════════════════════════
# 2) CmsMediaItem (admin) — scope checks por sede
# ════════════════════════════════════════════════════════════════════════════


def test_admin_media_scoped_by_sede(client, db_session):
    (admin_a, persona_a, sede_a), (_, persona_b, sede_b) = _seed_two_sedes(db_session)
    m_local = models.CmsMediaItem(
        id=_uuid.uuid4(),
        url="https://cdn.example.com/local-image.png",
        alt_text="Asset LEGITIMO sede_a",
        section="hero",
        created_by_persona_id=persona_a.id,
        sede_id=sede_a.id,
    )
    m_cross = models.CmsMediaItem(
        id=_uuid.uuid4(),
        url="https://cdn.example.com/cross-sede.png",
        alt_text="Asset SECRETO sede_b",
        section="hero",
        created_by_persona_id=persona_b.id,
        sede_id=sede_b.id,
    )
    db_session.add_all([m_local, m_cross])
    db_session.commit()

    headers_a = auth_headers(client, email="cmsFase5A@example.com")
    resp = client.get("/api/cms/media", headers=headers_a)
    assert resp.status_code == 200, resp.text
    body_text = resp.text
    assert "Asset LEGITIMO sede_a" in body_text
    assert "Asset SECRETO sede_b" not in body_text


def test_get_admin_media_blocks_cross_sede(client, db_session):
    (admin_a, _, _), (_, persona_b, sede_b) = _seed_two_sedes(db_session)
    m_cross = models.CmsMediaItem(
        id=_uuid.uuid4(),
        url="https://cdn.example.com/cross-sede2.png",
        alt_text="Cross get-target",
        section="hero",
        created_by_persona_id=persona_b.id,
        sede_id=sede_b.id,
    )
    db_session.add(m_cross)
    db_session.commit()

    headers_a = auth_headers(client, email="cmsFase5A@example.com")
    resp = client.get(f"/api/cms/media/{m_cross.id}", headers=headers_a)
    assert resp.status_code == 404


def test_patch_admin_media_blocks_cross_sede(client, db_session):
    (admin_a, _, _), (_, persona_b, sede_b) = _seed_two_sedes(db_session)
    m_cross = models.CmsMediaItem(
        id=_uuid.uuid4(),
        url="https://cdn.example.com/cross-sede3.png",
        section="hero",
        created_by_persona_id=persona_b.id,
        sede_id=sede_b.id,
    )
    db_session.add(m_cross)
    db_session.commit()

    headers_a = auth_headers(client, email="cmsFase5A@example.com")
    resp = client.patch(
        f"/api/cms/media/{m_cross.id}",
        headers=headers_a,
        json={"alt_text": "MUTADO cross-sede"},
    )
    assert resp.status_code == 404
    db_session.refresh(m_cross)
    assert m_cross.alt_text != "MUTADO cross-sede"


def test_delete_admin_media_blocks_cross_sede(client, db_session):
    (admin_a, _, _), (_, persona_b, sede_b) = _seed_two_sedes(db_session)
    m_cross = models.CmsMediaItem(
        id=_uuid.uuid4(),
        url="https://cdn.example.com/cross-sede4.png",
        section="hero",
        created_by_persona_id=persona_b.id,
        sede_id=sede_b.id,
    )
    db_session.add(m_cross)
    db_session.commit()

    headers_a = auth_headers(client, email="cmsFase5A@example.com")
    resp = client.delete(f"/api/cms/media/{m_cross.id}", headers=headers_a)
    assert resp.status_code == 404
    db_session.refresh(m_cross)
    assert m_cross.status == "active"


# ════════════════════════════════════════════════════════════════════════════
# 3) Public feed (v2 endpoints) — sanity
# ════════════════════════════════════════════════════════════════════════════


def test_public_testimonials_feed_remains_global(client, db_session):
    """Sanity: v2 public testimonials endpoint works (cms/v2/public)."""
    # Seed a minimal site so the endpoint returns valid data
    site = models.CmsSite(
        id=_uuid.uuid4(),
        site_key="ccf",
        name="CCF Test",
        base_path="/ccf-test",
        is_active=True,
        sede_id=None,
    )
    db_session.add(site)
    db_session.flush()
    cat = models.CmsCategory(
        id=_uuid.uuid4(),
        site_id=site.id,
        slug="testimonials",
        name="Testimonials",
        is_active=True,
    )
    db_session.add(cat)
    db_session.commit()

    resp = client.get("/api/cms/v2/public/sites/ccf/posts?category_slug=testimonials")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert isinstance(data, dict), "v2 public endpoint returns PaginatedResponse, not a list"
    assert "items" in data
    assert "total" in data
    assert isinstance(data["items"], list)


def test_public_announcements_feed_remains_global(client, db_session):
    """Sanity: v2 public announcements endpoint works."""
    site = models.CmsSite(
        id=_uuid.uuid4(),
        site_key="ccf",
        name="CCF Test",
        base_path="/ccf-test",
        is_active=True,
        sede_id=None,
    )
    db_session.add(site)
    db_session.flush()
    cat = models.CmsCategory(
        id=_uuid.uuid4(),
        site_id=site.id,
        slug="announcements",
        name="Announcements",
        is_active=True,
    )
    db_session.add(cat)
    db_session.commit()

    resp = client.get("/api/cms/v2/public/sites/ccf/posts?category_slug=announcements")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert isinstance(data, dict), "v2 public endpoint returns PaginatedResponse, not a list"
    assert "items" in data
    assert "total" in data
    assert isinstance(data["items"], list)
