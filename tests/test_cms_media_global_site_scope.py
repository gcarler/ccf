"""Axioma 3 — CMS media scope bypass for global CmsSites.

Regression coverage for the fix where ``_scope_cms_media_by_user_sede`` skips
the sede filter when at least one active ``CmsSite`` has ``sede_id=None``
(a cross-sede editorial site such as ``ccf``). The media library is a shared
editorial resource in that scenario, so editors from any sede must be able to
browse and attach media regardless of the ``sede_id`` stamped on each item.

Contrast with ``test_cms_sede_isolation.py``: when NO global site exists, the
strict per-sede scope is preserved.
"""

from __future__ import annotations

import uuid as _uuid

from backend import models
from tests.conftest import auth_headers, seed_admin


def _seed_global_site(db_session, site_key="ccf"):
    """Seed an active CmsSite with sede_id=None (global editorial site)."""
    site = models.CmsSite(
        id=_uuid.uuid4(),
        site_key=site_key,
        name=site_key.upper(),
        base_path=f"/{site_key}-test",
        is_active=True,
        sede_id=None,
    )
    db_session.add(site)
    db_session.commit()
    return site


def test_media_listing_is_global_when_global_site_exists(client, db_session):
    """Admin of sede_a sees media from sede_b when a global CmsSite exists."""
    admin_a, persona_a, sede_a = seed_admin(
        db_session, email="mediaGlobalA@example.com", password="testpass123"
    )
    # Seed a second sede + media in it (admin_a's persona is in sede_a)
    sede_b = models.Sede(id=_uuid.uuid4(), nombre="Sede B", ciudad="B", es_activa=True)
    db_session.add(sede_b)
    persona_b = models.Persona(
        id=_uuid.uuid4(),
        first_name="PersonaB",
        last_name="Test",
        email=f"persona-b-{_uuid.uuid4().hex[:8]}@example.com",
        sede_id=sede_b.id,
        estado_vital="ACTIVO",
    )
    db_session.add(persona_b)
    _seed_global_site(db_session)

    m_local = models.CmsMediaItem(
        id=_uuid.uuid4(),
        url="https://cdn.example.com/local.png",
        alt_text="Asset sede_a",
        section="hero",
        created_by_persona_id=persona_a.id,
        sede_id=sede_a.id,
    )
    m_cross = models.CmsMediaItem(
        id=_uuid.uuid4(),
        url="https://cdn.example.com/cross.png",
        alt_text="Asset sede_b",
        section="hero",
        created_by_persona_id=persona_b.id,
        sede_id=sede_b.id,
    )
    db_session.add_all([m_local, m_cross])
    db_session.commit()

    headers_a = auth_headers(client, email="mediaGlobalA@example.com")
    resp = client.get("/api/cms/media", headers=headers_a)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] >= 2, f"Expected global media visibility, got total={body['total']}"
    alt_texts = {item["alt_text"] for item in body["items"]}
    assert "Asset sede_a" in alt_texts
    assert "Asset sede_b" in alt_texts, (
        "Global-site bypass failed: admin_a should see sede_b media when a global CmsSite exists"
    )


def test_media_get_is_global_when_global_site_exists(client, db_session):
    """Admin of sede_a can GET a cross-sede media item when a global site exists."""
    admin_a, persona_a, sede_a = seed_admin(
        db_session, email="mediaGetA@example.com", password="testpass123"
    )
    sede_b = models.Sede(id=_uuid.uuid4(), nombre="Sede B2", ciudad="C", es_activa=True)
    db_session.add(sede_b)
    persona_b = models.Persona(
        id=_uuid.uuid4(),
        first_name="PersonaB2",
        last_name="Test",
        email=f"persona-b2-{_uuid.uuid4().hex[:8]}@example.com",
        sede_id=sede_b.id,
        estado_vital="ACTIVO",
    )
    db_session.add(persona_b)
    _seed_global_site(db_session)

    m_cross = models.CmsMediaItem(
        id=_uuid.uuid4(),
        url="https://cdn.example.com/cross-get.png",
        alt_text="Cross get with global site",
        section="hero",
        created_by_persona_id=persona_b.id,
        sede_id=sede_b.id,
    )
    db_session.add(m_cross)
    db_session.commit()

    headers_a = auth_headers(client, email="mediaGetA@example.com")
    resp = client.get(f"/api/cms/media/{m_cross.id}", headers=headers_a)
    assert resp.status_code == 200, resp.text
    assert resp.json()["alt_text"] == "Cross get with global site"
