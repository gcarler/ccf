"""CMS UGC v1 endpoints + posts-by-category — regresiones.

Cubre:
- Axioma 3: los endpoints v1 de solo lectura (`/api/cms/announcements`,
  `/api/cms/testimonials`) filtran por sede del actor a nivel de query
  (antes de paginar). Un actor de sede A nunca ve filas de sede B.
- Paginación: `limit`/`skip` se aplican DESPUÉS del filtro por sede.
- B1: `POST`/`PATCH /api/cms/v2/sites/{key}/posts-by-category` exigen
  body (422 con body ausente, no 500).
- B2: la lectura de `posts-by-category` se rige por `cms:read` (un LECTOR
  puede listar; el assert editorial quedó solo en mutaciones).
"""

import uuid
from datetime import datetime, timedelta, timezone

from backend import models
from tests.conftest import auth_headers, seed_user_with_role


def _seed_sede(db_session, nombre="Sede Test", ciudad="Bogota"):
    sede = models.Sede(id=uuid.uuid4(), nombre=nombre, ciudad=ciudad, es_activa=True)
    db_session.add(sede)
    db_session.flush()
    return sede


def _seed_ugc_rows(db_session, sede, prefix, n_announcements=2, n_testimonials=2, base_time=None):
    """Seed Announcement + Testimonial rows for a sede; returns (ann_ids, test_ids)."""
    from backend.models_crm import Persona

    persona = Persona(
        id=uuid.uuid4(),
        first_name=f"Author {prefix}",
        last_name="UGC",
        email=f"{prefix}-ugc@example.com",
        sede_id=sede.id,
    )
    db_session.add(persona)
    db_session.flush()

    now = base_time or datetime.now(timezone.utc)
    ann_ids = []
    for i in range(n_announcements):
        ann = models.Announcement(
            title=f"{prefix} anuncio {i}",
            content=f"Contenido {i}",
            status="published",
            is_active=True,
            created_by_persona_id=persona.id,
            sede_id=sede.id,
            created_at=now - timedelta(minutes=i),
            published_at=now - timedelta(minutes=i),
        )
        db_session.add(ann)
        db_session.flush()
        ann_ids.append(ann.id)

    test_ids = []
    for i in range(n_testimonials):
        t = models.Testimonial(
            content=f"{prefix} testimonio {i}",
            status="approved",
            is_approved=True,
            author_persona_id=persona.id,
            sede_id=sede.id,
            created_at=now - timedelta(minutes=i),
        )
        db_session.add(t)
        db_session.flush()
        test_ids.append(t.id)

    db_session.commit()
    return ann_ids, test_ids


def _seed_user(db_session, sede, email, role_name="GESTOR", permisos=None):
    return seed_user_with_role(
        db_session,
        role_name=role_name,
        email=email,
        password="testpass123",
        sede_id=sede.id,
        permisos=permisos,
    )


def _seed_site(db_session, sede, key_suffix):
    site = models.CmsSite(
        id=uuid.uuid4(),
        site_key=f"ugc-site-{key_suffix}",
        name="UGC Site",
        base_path=f"/{key_suffix}",
        is_active=True,
        sede_id=sede.id,
    )
    db_session.add(site)
    db_session.commit()
    return site


# ── Axioma 3 — scope por sede (v1 read endpoints) ─────────────────────────────


def test_v1_announcements_scope_by_sede(client, db_session):
    sede_a = _seed_sede(db_session, "Sede A", "Bogota")
    sede_b = _seed_sede(db_session, "Sede B", "Medellin")
    ann_a, _ = _seed_ugc_rows(db_session, sede_a, "a")
    ann_b, _ = _seed_ugc_rows(db_session, sede_b, "b")

    _seed_user(db_session, sede_a, "ugc-a@example.com", permisos={"cms:read": "allow"})
    headers = auth_headers(client, email="ugc-a@example.com")

    resp = client.get("/api/cms/announcements", headers=headers)
    assert resp.status_code == 200, f"expected 200, got {resp.status_code}: {resp.text}"
    items = resp.json()
    assert {i["id"] for i in items} == {str(a) for a in ann_a}, "FUGA: anuncios de otra sede"
    assert not any(i["id"] in {str(a) for a in ann_b} for i in items), "FUGA: anuncios de sede B"

    # La sede B no ve los anuncios de A.
    _seed_user(db_session, sede_b, "ugc-b@example.com", permisos={"cms:read": "allow"})
    headers_b = auth_headers(client, email="ugc-b@example.com")
    resp_b = client.get("/api/cms/announcements", headers=headers_b)
    assert resp_b.status_code == 200
    assert {i["id"] for i in resp_b.json()} == {str(a) for a in ann_b}


def test_v1_testimonials_scope_by_sede(client, db_session):
    sede_a = _seed_sede(db_session, "Sede A", "Bogota")
    sede_b = _seed_sede(db_session, "Sede B", "Medellin")
    _, test_a = _seed_ugc_rows(db_session, sede_a, "a")
    _, test_b = _seed_ugc_rows(db_session, sede_b, "b")

    _seed_user(db_session, sede_a, "ugc-a@example.com", permisos={"cms:read": "allow"})
    headers = auth_headers(client, email="ugc-a@example.com")

    resp = client.get("/api/cms/testimonials", headers=headers)
    assert resp.status_code == 200, f"expected 200, got {resp.status_code}: {resp.text}"
    items = resp.json()
    assert {i["id"] for i in items} == {str(t) for t in test_a}, "FUGA: testimonios de otra sede"
    assert not any(i["id"] in {str(t) for t in test_b} for i in items), "FUGA: testimonios de sede B"


def test_v1_announcements_filter_before_pagination(client, db_session):
    """El filtro por sede se aplica ANTES de paginar: con limit menor al total
    de la propia sede, nunca aparecen filas de otra sede."""
    sede_a = _seed_sede(db_session, "Sede A", "Bogota")
    sede_b = _seed_sede(db_session, "Sede B", "Medellin")
    base = datetime(2026, 8, 1, 12, 0, 0, tzinfo=timezone.utc)
    ann_a, _ = _seed_ugc_rows(db_session, sede_a, "a", n_announcements=3, n_testimonials=1, base_time=base)
    ann_b, _ = _seed_ugc_rows(db_session, sede_b, "b", n_announcements=3, n_testimonials=1, base_time=base)

    _seed_user(db_session, sede_a, "ugc-a@example.com", permisos={"cms:read": "allow"})
    headers = auth_headers(client, email="ugc-a@example.com")

    # created_at desc: a0 (más reciente) primero → con limit=2 solo a0 y a1.
    resp = client.get("/api/cms/announcements?limit=2", headers=headers)
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 2
    expected = {str(ann_a[0]), str(ann_a[1])}
    assert {i["id"] for i in items} == expected, f"paginación rota: {items}"
    assert not any(i["id"] in {str(a) for a in ann_b} for i in items), "FUGA: filas de sede B en página de A"

    # skip=2 → solo a2 (la tercera de A), nunca de B.
    resp2 = client.get("/api/cms/announcements?limit=2&skip=2", headers=headers)
    assert resp2.status_code == 200
    items2 = resp2.json()
    assert [i["id"] for i in items2] == [str(ann_a[2])], f"skip roto: {items2}"


# ── B1 — body requerido en posts-by-category (no 500) ─────────────────────────


def test_posts_by_category_create_requires_body(client, db_session):
    sede = _seed_sede(db_session)
    site = _seed_site(db_session, sede, "b1")
    _seed_user(db_session, sede, "b1@example.com", permisos={"cms:read": "allow", "cms:edit": "allow"})
    headers = auth_headers(client, email="b1@example.com")

    resp = client.post(
        f"/api/cms/v2/sites/{site.site_key}/posts-by-category?category=testimonials",
        headers=headers,
    )
    assert resp.status_code == 422, f"sin body debe ser 422, got {resp.status_code}: {resp.text}"


def test_posts_by_category_patch_requires_body(client, db_session):
    sede = _seed_sede(db_session)
    site = _seed_site(db_session, sede, "b1-patch")
    _seed_user(db_session, sede, "b1p@example.com", permisos={"cms:read": "allow", "cms:edit": "allow"})
    headers = auth_headers(client, email="b1p@example.com")

    resp = client.patch(
        f"/api/cms/v2/sites/{site.site_key}/posts-by-category/no-such-slug?category=announcements",
        headers=headers,
    )
    assert resp.status_code == 422, f"sin body debe ser 422 (validación antes de 404), got {resp.status_code}: {resp.text}"


# ── B2 — LECTOR con cms:read puede listar posts-by-category ──────────────────


def test_posts_by_category_list_lector_read_access(client, db_session):
    sede = _seed_sede(db_session)
    site = _seed_site(db_session, sede, "lector")
    _seed_user(db_session, sede, "lector@example.com", role_name="LECTOR", permisos={"cms:read": "allow"})
    headers = auth_headers(client, email="lector@example.com")

    resp = client.get(
        f"/api/cms/v2/sites/{site.site_key}/posts-by-category?category=testimonials",
        headers=headers,
    )
    assert resp.status_code == 200, f"LECTOR con cms:read debe listar, got {resp.status_code}: {resp.text}"
    assert resp.json()["items"] == []

    # El mismo LECTOR NO puede crear (mutación exige cms:edit + rol editorial).
    resp_create = client.post(
        f"/api/cms/v2/sites/{site.site_key}/posts-by-category?category=testimonials",
        headers=headers,
        json={"title": "Nope", "content": "x", "status": "draft"},
    )
    assert resp_create.status_code == 403, f"LECTOR no debe crear, got {resp_create.status_code}: {resp_create.text}"
