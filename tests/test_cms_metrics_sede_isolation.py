"""Axioma 3 — Fase 5b: Scope isolation tests for CMS metrics + agent analytics.

Cubre dos leaks de datos User-Generated agregados cross-sede
identificados en el audit:

  1. ``GET /api/cms/metrics`` (cms.py)
     Pre-fix: contaba ``testimonials`` / ``announcements`` /
     ``CmsMediaItem`` cross-sede. Un admin de sede_a veía el total
     agregado de UGC de sede_b en su dashboard admin.

  2. ``GET /api/agents/analytics/summary`` (agents.py)
     Pre-fix: ``pending_testimonials = crud.list_testimonials(db) if
     not is_approved`` iteraba sobre TODOS los testimonials del
     platform. Same leak.

Post-fix: ambos endpoints pre-filtran UGC via los helpers
``_scope_cms_*_by_user_sede`` importados desde
``backend.api._cms_helpers``. Staff con sede ve sólo counts de su
sede. Superadmin (sin sede) sigue viendo globales (compat legacy).

Site-faro content (CmsPage / CmsSection) sigue siendo
global por diseño: es site público, no UGC.

Mirrors ``tests/test_cms_sede_isolation.py`` fixture style.
"""

from __future__ import annotations

import uuid as _uuid

from backend import models
from tests.conftest import auth_headers, seed_admin

# ── Helpers ────────────────────────────────────────────────────────────────


def _seed_two_sedes(db_session):
    admin_a, persona_a, sede_a = seed_admin(
        db_session, email="cmsMetricsA@example.com", password="testpass123"
    )
    admin_b, persona_b, sede_b = seed_admin(
        db_session, email="cmsMetricsB@example.com", password="testpass123"
    )
    assert sede_a.id != sede_b.id
    return (admin_a, persona_a, sede_a), (admin_b, persona_b, sede_b)


def _persona_in(db, sede_id, email_suffix):
    p = models.Persona(
        id=_uuid.uuid4(),
        first_name=f"User-{email_suffix}",
        last_name="Test",
        email=f"{email_suffix}-{_uuid.uuid4().hex[:8]}@example.com",
        sede_id=sede_id,
        estado_vital="ACTIVO",
    )
    db.add(p)
    db.flush()
    return p


def _seed_testimonial_in_sede(db, author_persona, sede_id, content):
    t = models.Testimonial(
        id=_uuid.uuid4(),
        content=content,
        author_persona_id=author_persona.id if author_persona else None,
        sede_id=sede_id,
        status="pending",
        is_approved=False,
    )
    db.add(t)
    db.flush()
    return t


def _seed_announcement_in_sede(db, persona, sede_id, title, content):
    a = models.Announcement(
        id=_uuid.uuid4(),
        title=title,
        content=content,
        sede_id=sede_id,
        created_by_persona_id=persona.id,
        status="published",
    )
    db.add(a)
    db.flush()
    return a


def _seed_media_in_sede(db, persona, sede_id, url, mime_type="image/png"):
    m = models.CmsMediaItem(
        id=_uuid.uuid4(),
        url=url,
        section="hero",
        mime_type=mime_type,
        created_by_persona_id=persona.id if persona else None,
        sede_id=sede_id,
        status="active",
    )
    db.add(m)
    db.flush()
    return m


# ════════════════════════════════════════════════════════════════════════════
# 1) /api/cms/metrics — scope UGC counts by sede
# ════════════════════════════════════════════════════════════════════════════


def test_content_metrics_overview_scopes_testimonials_by_sede(client, db_session):
    """Axioma 3: admin A sólo ve counts de testimonios de su sede.

    Pre-fix el endpoint contaba TODOS los testimonios del platform,
    incluyendo los de sede_b — leak cross-sede en el dashboard admin.
    Endpoint: GET /api/cms/metrics (antes /api/cms/content/metrics/overview).
    """
    (admin_a, persona_a, sede_a), (_, persona_b, sede_b) = _seed_two_sedes(db_session)
    _seed_testimonial_in_sede(
        db_session, persona_a, sede_a.id, "t-a 1 — local sede_a"
    )
    _seed_testimonial_in_sede(
        db_session, persona_a, sede_a.id, "t-a 2 — local sede_a"
    )
    _seed_testimonial_in_sede(
        db_session, persona_b, sede_b.id, "t-b 1 — cross-sede leak"
    )
    _seed_testimonial_in_sede(
        db_session, persona_b, sede_b.id, "t-b 2 — cross-sede leak"
    )
    db_session.commit()

    headers_a = auth_headers(client, email="cmsMetricsA@example.com")
    resp = client.get("/api/cms/metrics", headers=headers_a)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # Sede_a: 2 testimonios locales
    assert body["testimonials_total"] == 2, (
        f"LEAK: admin A ve testimonials_total={body['testimonials_total']}, "
        f"debería ser 2 (sólo sede_a). Body={body}"
    )


def test_content_metrics_overview_scopes_announcements_by_sede(
    client, db_session
):
    """Axioma 3: announcements_total acotado por sede del staff."""
    (admin_a, persona_a, sede_a), (_, persona_b, sede_b) = _seed_two_sedes(db_session)
    _seed_announcement_in_sede(
        db_session, persona_a, sede_a.id, "a-a-1", "local sede_a"
    )
    _seed_announcement_in_sede(
        db_session, persona_b, sede_b.id, "a-b-1", "cross-sede leak"
    )
    _seed_announcement_in_sede(
        db_session, persona_b, sede_b.id, "a-b-2", "cross-sede leak"
    )
    db_session.commit()

    headers_a = auth_headers(client, email="cmsMetricsA@example.com")
    resp = client.get("/api/cms/metrics", headers=headers_a)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["announcements_total"] == 1, (
        f"LEAK: announcements_total={body['announcements_total']} cross-sede"
    )


def test_content_metrics_overview_scopes_media_by_sede(client, db_session):
    """Axioma 3: media_total se acota por sede del staff."""
    (admin_a, persona_a, sede_a), (_, persona_b, sede_b) = _seed_two_sedes(db_session)
    _seed_media_in_sede(
        db_session, persona_a, sede_a.id, "https://cdn.example.com/local-a.png"
    )
    _seed_media_in_sede(
        db_session, persona_b, sede_b.id, "https://cdn.example.com/cross-b.png"
    )
    _seed_media_in_sede(
        db_session, persona_b, sede_b.id, "https://cdn.example.com/cross-b2.jpg"
    )
    db_session.commit()

    headers_a = auth_headers(client, email="cmsMetricsA@example.com")
    resp = client.get("/api/cms/metrics", headers=headers_a)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # media_total: sede_a=1 (1 imagen), sede_b=2 (1 png + 1 jpg). Si leak,
    # retornaría 3.
    assert body["media_total"] == 1, (
        f"LEAK: media_total={body['media_total']} debe ser 1 (sólo sede_a)"
    )
    assert body["media_images"] == 1, (
        f"LEAK: media_images={body['media_images']} debe ser 1"
    )


def test_content_metrics_overview_superadmin_sees_all(
    client, db_session, monkeypatch
):
    """Back-compat: superadmin (actor sin sede) ve totales globales.

    Patcheamos ``_actor_sede_or_none`` en el módulo ``_shared`` (no el
    package) para que ``_scope_cms_*_by_user_sede`` aplique la rama
    superadmin.
    """
    from backend.api._cms_helpers import _shared as _cms_shared_module

    monkeypatch.setattr(
        _cms_shared_module,
        "_actor_sede_or_none",
        lambda db, current_user: None,
    )

    (admin_a, persona_a, sede_a), (_, persona_b, sede_b) = _seed_two_sedes(db_session)
    _seed_testimonial_in_sede(
        db_session, persona_a, sede_a.id, "global-a"
    )
    _seed_testimonial_in_sede(
        db_session, persona_b, sede_b.id, "global-b"
    )
    db_session.commit()

    headers_a = auth_headers(client, email="cmsMetricsA@example.com")
    resp = client.get("/api/cms/metrics", headers=headers_a)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # Superadmin ve 2 testimonios (sede_a + sede_b).
    assert body["testimonials_total"] == 2, (
        f"Superadmin debe ver 2 testimonials; got {body['testimonials_total']}"
    )


# ════════════════════════════════════════════════════════════════════════════
# 2) /api/agents/analytics/summary pending_testimonials — scope
# ════════════════════════════════════════════════════════════════════════════


def test_agents_analytics_summary_pending_testimonials_scoped_by_sede(
    client, db_session
):
    """Axioma 3: ``pending_testimonials`` se acota por sede del staff.

    Pre-fix: ``crud.list_testimonials(db)`` itera TODOS los
    testimonios del platform, sumando el leak como ``pending``.
    """
    (admin_a, persona_a, sede_a), (_, persona_b, sede_b) = _seed_two_sedes(db_session)
    # sede_a: 1 pending, 1 approved
    t_a_pending = _seed_testimonial_in_sede(
        db_session, persona_a, sede_a.id, "a-pending"
    )
    t_a_pending.is_approved = False
    t_a_approved = _seed_testimonial_in_sede(
        db_session, persona_a, sede_a.id, "a-approved"
    )
    t_a_approved.is_approved = True
    # sede_b: 2 pending (NO deben contar para admin A)
    _seed_testimonial_in_sede(db_session, persona_b, sede_b.id, "b-pending-1")
    _seed_testimonial_in_sede(db_session, persona_b, sede_b.id, "b-pending-2")
    db_session.commit()

    headers_a = auth_headers(client, email="cmsMetricsA@example.com")
    resp = client.get("/api/agents/analytics/summary", headers=headers_a)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["pending_testimonials"] == 1, (
        f"LEAK: pending_testimonials={body['pending_testimonials']} debe "
        f"ser 1 (sólo sede_a); got body={body}"
    )


def test_agents_analytics_summary_superadmin_sees_all_pending(
    client, db_session, monkeypatch
):
    """Back-compat: superadmin ve TODOS los pending cross-sede.

    Patcher en ``_actor_sede_or_none`` (NO en ``get_user_sede_id``
    directamente) porque el helper que consume ``pending_testimonials``
    pasa por ``_actor_sede_or_none`` (en ``backend.api._cms_helpers._shared``),
    que internamente invoca ``get_user_sede_id``. Patchar el helper de
    orden superior garantiza la rama superadmin sin tener que monkeypatch
    el lookup DB detrás. Mismo patrón que
    ``test_cms_pastoral_team_list_allows_both_for_superadmin`` en
    ``test_cms_sede_isolation.py``.
    """
    from backend.api._cms_helpers import _shared as _cms_shared_module

    monkeypatch.setattr(
        _cms_shared_module,
        "_actor_sede_or_none",
        lambda db, current_user: None,
    )

    (admin_a, persona_a, sede_a), (_, persona_b, sede_b) = _seed_two_sedes(db_session)
    _seed_testimonial_in_sede(db_session, persona_a, sede_a.id, "global-pending-a")
    _seed_testimonial_in_sede(db_session, persona_b, sede_b.id, "global-pending-b")
    _seed_testimonial_in_sede(db_session, persona_b, sede_b.id, "global-pending-b2")
    db_session.commit()

    headers_a = auth_headers(client, email="cmsMetricsA@example.com")
    resp = client.get("/api/agents/analytics/summary", headers=headers_a)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["pending_testimonials"] == 3, (
        f"Superadmin debe ver 3 pending global; got {body['pending_testimonials']}"
    )


def test_agents_analytics_summary_pending_testimonials_unaffected_when_zero(
    client, db_session
):
    """Sanity: cuando no hay pendientes cross-sede ni locales, retorn 0.

    Fixture: ningún testimonio en ninguna sede.
    """
    (admin_a, _, _), (_, _, _) = _seed_two_sedes(db_session)
    db_session.commit()

    headers_a = auth_headers(client, email="cmsMetricsA@example.com")
    resp = client.get("/api/agents/analytics/summary", headers=headers_a)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["pending_testimonials"] == 0
