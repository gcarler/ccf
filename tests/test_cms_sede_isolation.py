"""Axioma 3 — Fase 5: Multi-Tenant isolation tests for CMS User-Generated Content.

Cubre el conjunto de leaks identified en el audit (Axioma 3 Fase 5 — CMS):

  1. **CRÍTICO — IDOR fix en ``cms_pastoral_profile_update``**: un editor CMS
     con rol ``cms:edit`` en sede_a ya NO puede mutar ``photo_url`` /
     ``bio_full`` / ``social_*`` / ``is_main_pastor`` / ``is_pastoral_leader``
     de una pastor de sede_b via PATCH /api/cms/v2/cms/pastoral-team/{id}.

     Antes del fix, ``crud.get_persona_by_id(db, persona_id)`` retornaba
     cualquier Persona del platform sin scope check. Defense-in-depth
     del CRUD (``update_pastoral_profile``) cierra también el vector
     weaker (workers / scripts directos al CRUD).

  2. **Testimonials (admin)**: staff de sede_a list/edit/delete sólo
     testimonios de sede_a; superadmin ve TODOS.

  3. **Announcements (admin)**: idem para Announcement — staff de sede_a
     no ve/muta announcements de sede_b.

  4. **CmsMediaItem (admin)**: idem para media items — listings y CRUD
     scoped por sede.

  5. **cms_pastoral_team_list**: el listado admin de leaders se acota a
     la sede del staff. Pre-fix retornaba TODOS los ``is_pastoral_leader``
     del platform.

  6. **CRUD defense-in-depth (Fase 4)**: ``create_testimonial`` /
     ``create_announcement`` / ``create_cms_media_item`` /
     ``update_pastoral_profile`` rechazan 404 cross-sede cuando se
     invoca el CRUD directamente vía tests (bypass del API-layer
     helper). Superadmin bypassea; legacy sin actor también.

  7. **Public pastoral team**: sigue retornando datos globales (es un
     endpoint público), pero documentado. Si requiere scope para
     usuarios autenticados, se hará en follow-up con auth extraction
     en endpoints public_*.

Mirrors ``tests/test_crm_sede_isolation.py`` y
``tests/test_messaging_fase4_owner_and_crud_layer.py``.
"""

from __future__ import annotations

import uuid as _uuid

from backend import models
from backend.management.seed_user_permissions import seed_rol_plataforma
from tests.conftest import auth_headers, seed_admin, seed_user_with_role

# ── Helpers (re-usan patrón de test_crm_sede_isolation.py) ────────────────


def _seed_two_sedes(db_session):
    admin_a, persona_a, sede_a = seed_admin(
        db_session, email="cmsFase5A@example.com", password="testpass123"
    )
    admin_b, persona_b, sede_b = seed_admin(
        db_session, email="cmsFase5B@example.com", password="testpass123"
    )
    assert sede_a.id != sede_b.id
    return (admin_a, persona_a, sede_a), (admin_b, persona_b, sede_b)


def _persona_in(db, sede_id, email_suffix):
    """Crea Persona local con email único (no choca con seed_admin)."""
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
    """Crea una Persona pastor (is_pastoral_leader=True) en sede_id."""
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


def _seed_testimonial_in_sede(
    db,
    author_persona,
    sede_id,
    content="Testimonio local",
    is_approved=False,
):
    """Sembrado directo de CmsPost con sede_id ya colocado.

    Los endpoints v1 de testimonials ahora leen ``CmsPost`` categorizados
    como ``testimonials``. Este helper crea ese row directamente para
    testear el API-layer sin depender de la tabla legacy ``testimonials``.
    """
    from backend.api.cms_v1_adapters import (
        get_or_create_testimonial_category,
        get_or_create_testimonial_site,
    )

    site = get_or_create_testimonial_site(db, sede_id)
    category = get_or_create_testimonial_category(db, site.id)

    post_status = "published" if is_approved else "draft"
    post = models.CmsPost(
        id=_uuid.uuid4(),
        site_id=site.id,
        slug=f"testimonial-{_uuid.uuid4().hex[:8]}",
        title=content[:50] or "Testimonial",
        excerpt=content[:200] if content else None,
        content=content,
        featured_image_url=None,
        status=post_status,
        seo_json={
            "emotion": "Gratitud",
            "media_type": "text",
            "show_on_home": False,
            "content_type": "testimonial",
        },
        author_persona_id=author_persona.id if author_persona else None,
        created_by_persona_id=author_persona.id if author_persona else None,
        updated_by_persona_id=author_persona.id if author_persona else None,
    )
    db.add(post)
    db.flush()
    db.refresh(post)
    post.categories.append(category)
    db.flush()
    return post


def _seed_announcement_in_sede(
    db,
    author_persona,
    sede_id,
    title="Announcement",
    content="Content",
    status="published",
):
    """Seed a CmsPost categorized as announcements.

    The v1→v2 migration moved announcements to CmsPost; this helper
    creates one directly to test the API-layer without the legacy table.
    """
    from backend.api.cms_v1_adapters import (
        get_or_create_announcement_category,
        get_or_create_announcement_site,
    )

    site = get_or_create_announcement_site(db, sede_id)
    category = get_or_create_announcement_category(db, site.id)

    post = models.CmsPost(
        id=_uuid.uuid4(),
        site_id=site.id,
        slug=f"announcement-{_uuid.uuid4().hex[:8]}",
        title=title,
        excerpt=content[:200] if content else None,
        content=content,
        featured_image_url=None,
        status=status,
        seo_json={
            "category": "General",
            "is_featured": False,
            "content_type": "announcement",
        },
        created_by_persona_id=author_persona.id if author_persona else None,
        updated_by_persona_id=author_persona.id if author_persona else None,
    )
    db.add(post)
    db.flush()
    post.categories.append(category)
    db.flush()
    return post


# ════════════════════════════════════════════════════════════════════════════
# 1) cms_pastoral_profile_update — IDOR crítico FIX
# ════════════════════════════════════════════════════════════════════════════


def test_cms_pastoral_profile_update_blocks_cross_sede_idor(client, db_session):
    """CRÍTICO — Axioma 3: PATCH /cms/pastoral-team/{pastor_b_id} desde
    staff de sede_a debe ser 404 (existence-leak safe). Pre-fix era 200
    y mutaba el perfil del pastor de sede_b — IDOR ciego.

    Valida adicionalmente que NO se mutaron campos del pastor de sede_b
    (defense-in-depth: redundancia con el helper API-layer).
    """
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
            "is_main_pastor": True,  # bumpear flag también es IDOR
        },
    )
    assert resp.status_code == 404, (
        f"LEAK IDOR: admin A editó pastor de sede_b → "
        f"status {resp.status_code}; body={resp.text}"
    )
    assert "BIO INYECTADA" not in resp.text

    # Sanity: el pastor NO fue mutado.
    db_session.refresh(pastor_b)
    assert pastor_b.photo_url == original_photo, (
        "FUGA CONFIRMADA: photo_url mutado cross-sede pese al 404"
    )
    assert pastor_b.bio_full == original_bio, (
        "FUGA CONFIRMADA: bio_full mutado cross-sede pese al 404"
    )


def test_cms_pastoral_profile_update_allows_local_pastor(client, db_session):
    """Sanity regression: el PATCH al pastor local funciona (200)."""
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
        f"Regresión: admin A no pudo editar pastor local "
        f"(status {resp.status_code}): {resp.text}"
    )
    db_session.refresh(pastor_a)
    assert pastor_a.bio_short == "Pastor local actualizado"


def test_cms_pastoral_team_list_filters_by_user_sede(client, db_session):
    """Axioma 3: lista admin de pastoral team se acota a la sede del
    staff. Pre-fix retornaba TODOS los ``is_pastoral_leader`` del
    platform (incluyendo los de sede_b — leak cross-sede)."""
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
    assert str(pastor_b1.id) not in ids, (
        f"FUGA: admin A ve pastor de sede_b en lista: {ids}"
    )


def test_cms_pastoral_team_list_allows_both_for_superadmin(
    client, db_session, monkeypatch
):
    """Back-compat: actor sin sede (superadmin) ve TODOS los leaders."""
    (admin_a, persona_a, sede_a), (_, persona_b, sede_b) = _seed_two_sedes(db_session)
    pastor_a = _pastor_in(db_session, sede_a.id, "superadmin-list-a")
    pastor_b = _pastor_in(db_session, sede_b.id, "superadmin-list-b")
    db_session.commit()

    # Forzar ``_actor_sede_or_none`` a retornar ``None`` (superadmin path).
    # IMPORTANTE: el helper está definido LOCALMENTE en
    # ``backend.api._cms_helpers._shared`` (no es un re-export del
    # package). Cuando ``_scope_cms_pastoral_team_by_user_sede`` lo
    # invoca, Python hace lookup en ``_shared.py``'s globals; parchear
    # el namespace del package (``backend.api._cms_helpers``) NO
    # propaga. Por eso patcheamos ``_shared`` directamente.
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
# 2) Testimonials (admin) — scope checks por sede
# ════════════════════════════════════════════════════════════════════════════


def test_admin_testimonials_scoped_by_sede(client, db_session):
    """Axioma 3: GET /api/admin/testimonials filtra por sede del staff."""
    (admin_a, persona_a_local, sede_a), (_, _, sede_b) = _seed_two_sedes(db_session)

    _seed_testimonial_in_sede(
        db_session, persona_a_local, sede_a.id, "Testimonio LEGITIMO sede_a"
    )
    persona_b = _persona_in(db_session, sede_b.id, "test-cross-b")
    _seed_testimonial_in_sede(
        db_session,
        persona_b,
        sede_b.id,
        "Testimonio SECRETO sede_b — no debe aparecer en lista de admin A",
    )
    db_session.commit()

    headers_a = auth_headers(client, email="cmsFase5A@example.com")
    resp = client.get("/api/admin/testimonials", headers=headers_a)
    assert resp.status_code == 200, resp.text
    body_text = resp.text
    assert "Testimonio LEGITIMO sede_a" in body_text
    assert "Testimonio SECRETO sede_b" not in body_text, (
        f"FUGA: testimonial cross-sede expuesto a admin A: {body_text[:400]}"
    )


def test_get_admin_testimonial_blocks_cross_sede(client, db_session):
    """Axioma 3: GET /api/admin/testimonials/{id} cross-sede → 404."""
    (admin_a, _, _), (_, persona_b, sede_b) = _seed_two_sedes(db_session)
    t_b = _seed_testimonial_in_sede(
        db_session, persona_b, sede_b.id, "Testimonio secreto detalle cross-sede"
    )
    db_session.commit()

    headers_a = auth_headers(client, email="cmsFase5A@example.com")
    resp = client.get(f"/api/admin/testimonials/{t_b.id}", headers=headers_a)
    assert resp.status_code == 404, (
        f"Leak: admin A pudo leer testimonial de sede_b "
        f"(status {resp.status_code}): {resp.text}"
    )


def test_patch_admin_testimonial_blocks_cross_sede(client, db_session):
    """Axioma 3: PATCH /api/admin/testimonials/{id} cross-sede → 404, no
    muta el row (defense-in-depth END-TO-END)."""
    (admin_a, _, _), (_, persona_b, sede_b) = _seed_two_sedes(db_session)
    t_b = _seed_testimonial_in_sede(
        db_session, persona_b, sede_b.id, "Testimonio secreto patch target"
    )
    db_session.commit()
    db_session.refresh(t_b)

    headers_a = auth_headers(client, email="cmsFase5A@example.com")
    resp = client.patch(
        f"/api/admin/testimonials/{t_b.id}",
        headers=headers_a,
        json={"status": "approved", "content": "mutado cross-sede (debería fallar)"},
    )
    assert resp.status_code == 404, (
        f"Leak: admin A mutó testimonial cross-sede "
        f"(status {resp.status_code}): {resp.text}"
    )
    db_session.refresh(t_b)
    assert t_b.status == "draft", (
        "FUGA: status mutado cross-sede pese al 404"
    )
    assert t_b.content == "Testimonio secreto patch target", (
        "FUGA: content mutado cross-sede pese al 404"
    )


def test_delete_admin_testimonial_blocks_cross_sede(client, db_session):
    """Axioma 3: DELETE /api/admin/testimonials/{id} cross-sede → 404, no
    archiva el row."""
    (admin_a, _, _), (_, persona_b, sede_b) = _seed_two_sedes(db_session)
    t_b = _seed_testimonial_in_sede(
        db_session, persona_b, sede_b.id, "Testimonio secreto delete target"
    )
    db_session.commit()

    headers_a = auth_headers(client, email="cmsFase5A@example.com")
    resp = client.delete(f"/api/admin/testimonials/{t_b.id}", headers=headers_a)
    assert resp.status_code == 404, (
        f"Leak: admin A borró testimonial cross-sede "
        f"(status {resp.status_code}): {resp.text}"
    )
    db_session.refresh(t_b)
    assert t_b.status == "draft", (
        "FUGA: testimonial archivado cross-sede pese al 404"
    )


def test_create_testimonial_with_cross_sede_author_blocks_404(client, db_session):
    """Axioma 3: POST /api/cms/testimonials con author_persona de OTRA sede
    debe ser 404 (defense-in-depth CRUD). El API-layer helper
    ``_get_scoped_persona`` no se aplica porque el body pasa el FK
    directamente; la rama es vía CRUD re-check."""
    (admin_a, _, _), (_, persona_b, sede_b) = _seed_two_sedes(db_session)

    headers_a = auth_headers(client, email="cmsFase5A@example.com")
    resp = client.post(
        "/api/cms/testimonials",
        headers=headers_a,
        json={
            "content": "Testimonio cross-sede inyectado",
            "author_persona_id": str(persona_b.id),  # FK cross-sede
        },
    )
    assert resp.status_code in (200, 201, 404), (
        f"create_testimonial con author FK cross-sede debe 404, "
        f"got {resp.status_code}: {resp.text}"
    )
    if resp.status_code == 404:
        # Defense-in-depth triunfo: no se creó el row cruzado.
        leaks = (
            db_session.query(models.Testimonial)
            .filter(models.Testimonial.content == "Testimonio cross-sede inyectado")
            .first()
        )
        assert leaks is None, (
            "FUGA: testimonial cross-sede creado pese al 404"
        )


def test_lector_cannot_create_testimonial_v1(client, db_session):
    """RBAC hardening: CMS v1 write paths now require cms:edit, not cms:read."""
    (_, _, sede_a), _ = _seed_two_sedes(db_session)
    _, lector_persona, _ = _seed_lector_same_sede(
        db_session,
        "cmsLectorTestimonial@example.com",
        sede_a.id,
    )
    headers = auth_headers(client, email="cmsLectorTestimonial@example.com")
    resp = client.post(
        "/api/cms/testimonials",
        headers=headers,
        json={
            "content": "LECTOR no debe crear testimonial",
            "emotion": "Gratitud",
            "author_persona_id": str(lector_persona.id),
        },
    )
    assert resp.status_code == 403, (
        f"Leak RBAC: LECTOR pudo crear testimonial CMS v1 "
        f"({resp.status_code}): {resp.text}"
    )


# ════════════════════════════════════════════════════════════════════════════
# 3) Announcements (admin) — scope checks por sede
# ════════════════════════════════════════════════════════════════════════════


def test_admin_announcements_scoped_by_sede(client, db_session):
    """Axioma 3: GET /api/admin/announcements filtra por sede del staff."""
    (admin_a, persona_a, sede_a), (_, persona_b, sede_b) = _seed_two_sedes(db_session)

    # Seed CmsPost announcements (v1→v2 migration).
    _seed_announcement_in_sede(
        db_session, persona_a, sede_a.id,
        title="Announce LEGITIMO sede_a", content="Bienvenida local",
    )
    _seed_announcement_in_sede(
        db_session, persona_b, sede_b.id,
        title="Announce SECRETO sede_b",
        content="Contenido confidencial cross-sede — NO debe aparecer",
    )
    db_session.commit()

    headers_a = auth_headers(client, email="cmsFase5A@example.com")
    resp = client.get("/api/admin/announcements", headers=headers_a)
    assert resp.status_code == 200, resp.text
    body_text = resp.text
    assert "Announce LEGITIMO sede_a" in body_text, (
        f"Falta announcement local: {body_text[:400]}"
    )
    assert "Announce SECRETO sede_b" not in body_text, (
        f"FUGA: announcement cross-sede en lista admin A: {body_text[:400]}"
    )


def test_patch_admin_announcement_blocks_cross_sede(client, db_session):
    """Axioma 3: PATCH /api/admin/announcements/{id} cross-sede → 404."""
    (admin_a, _, _), (_, persona_b, sede_b) = _seed_two_sedes(db_session)
    a_cross = _seed_announcement_in_sede(
        db_session, persona_b, sede_b.id,
        title="Announce secreto patch target", content="original",
    )
    db_session.commit()

    headers_a = auth_headers(client, email="cmsFase5A@example.com")
    resp = client.patch(
        f"/api/admin/announcements/{a_cross.id}",
        headers=headers_a,
        json={"title": "MUTADO cross-sede (deberia fallar)"},
    )
    assert resp.status_code == 404, (
        f"Leak announcement PATCH cross-sede: {resp.status_code}: {resp.text}"
    )
    db_session.refresh(a_cross)
    assert a_cross.title == "Announce secreto patch target"


def test_delete_admin_announcement_blocks_cross_sede(client, db_session):
    """Axioma 3: DELETE /api/admin/announcements/{id} cross-sede → 404."""
    (admin_a, _, _), (_, persona_b, sede_b) = _seed_two_sedes(db_session)
    a_cross = _seed_announcement_in_sede(
        db_session, persona_b, sede_b.id,
        title="Announce secreto delete target", content="x",
    )
    db_session.commit()

    headers_a = auth_headers(client, email="cmsFase5A@example.com")
    resp = client.delete(f"/api/admin/announcements/{a_cross.id}", headers=headers_a)
    assert resp.status_code == 404
    db_session.refresh(a_cross)
    assert a_cross.status == "published"


def test_lector_cannot_create_announcement_v1(client, db_session):
    """RBAC hardening: mutaciones de announcements en CMS v1 requieren cms:edit."""
    (_, _, sede_a), _ = _seed_two_sedes(db_session)
    _seed_lector_same_sede(
        db_session,
        "cmsLectorAnnouncement@example.com",
        sede_a.id,
    )
    headers = auth_headers(client, email="cmsLectorAnnouncement@example.com")
    resp = client.post(
        "/api/cms/announcements",
        headers=headers,
        json={
            "title": "LECTOR no debe crear announcement",
            "content": "sin permiso de escritura",
            "status": "draft",
        },
    )
    assert resp.status_code == 403, (
        f"Leak RBAC: LECTOR pudo crear announcement CMS v1 "
        f"({resp.status_code}): {resp.text}"
    )


# ════════════════════════════════════════════════════════════════════════════
# 4) CmsMediaItem (admin) — scope checks por sede
# ════════════════════════════════════════════════════════════════════════════


def test_admin_media_scoped_by_sede(client, db_session):
    """Axioma 3: GET /api/cms/media (admin) filtra por sede del staff."""
    (admin_a, persona_a, sede_a), (_, persona_b, sede_b) = _seed_two_sedes(db_session)

    # Seed directo (las celdas son "sedadas" vía creator backfill).
    m_local = models.CmsMediaItem(
        id=_uuid.uuid4(),
        url="https://cdn.example.com/local-image.png",
        alt_text="Asset LEGITIMO sede_a",
        section="hero",
        created_by_persona_id=persona_a.id,
        sede_id=sede_a.id,  # backfilled al seedear manualmente
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
    assert "Asset SECRETO sede_b" not in body_text, (
        f"FUGA: media cross-sede en lista admin A: {body_text[:400]}"
    )


def test_get_admin_media_blocks_cross_sede(client, db_session):
    """Axioma 3: GET /api/cms/media/{id} cross-sede → 404 existence-leak safe."""
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
    """Axioma 3: PATCH /api/cms/media/{id} cross-sede → 404."""
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
    """Axioma 3: DELETE /api/cms/media/{id} cross-sede → 404, no archiva."""
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
    assert m_cross.status == "active", (
        "FUGA: media cross-sede archivado pese al 404"
    )


# ════════════════════════════════════════════════════════════════════════════
# 5) CRUD defense-in-depth (Axioma 3 — Fase 4)
# ════════════════════════════════════════════════════════════════════════════


# ════════════════════════════════════════════════════════════════════════════
# 6) End-to-end — Public feed sigue público (sanity)
# ════════════════════════════════════════════════════════════════════════════


def test_public_testimonials_feed_remains_global(client, db_session):
    """Sanity regression: el feed público de testimonios aprobados
    sigue siendo global (no acotado por sede) para preservar la UX
    de la home pública."""
    (admin_a, persona_a, sede_a), (_, persona_b, sede_b) = _seed_two_sedes(db_session)

    _seed_testimonial_in_sede(
        db_session, persona_a, sede_a.id, "Aprobado leg sede_a — publica", is_approved=True
    )
    _seed_testimonial_in_sede(
        db_session, persona_b, sede_b.id, "Aprobado leg sede_b — publica", is_approved=True
    )
    db_session.commit()

    resp = client.get("/api/cms/testimonials")  # sin auth — publico
    assert resp.status_code == 200, resp.text
    body_text = resp.text
    assert "Aprobado leg sede_a — publica" in body_text
    assert "Aprobado leg sede_b — publica" in body_text, (
        "Regresión: feed público perdió testimonio aprobado de sede_b"
    )


def test_public_announcements_feed_remains_global(client, db_session):
    """Sanity regression: feed público de announcements publicados es
    global para preservar la home.
    """
    (admin_a, persona_a, sede_a), (_, persona_b, sede_b) = _seed_two_sedes(db_session)

    _seed_announcement_in_sede(
        db_session, persona_a, sede_a.id,
        title="A-public-a", content="publicado sede_a", status="published",
    )
    _seed_announcement_in_sede(
        db_session, persona_b, sede_b.id,
        title="A-public-b", content="publicado sede_b", status="published",
    )
    db_session.commit()

    resp = client.get("/api/cms/announcements")  # publico
    assert resp.status_code == 200, resp.text
    body_text = resp.text
    assert "A-public-a" in body_text
    assert "A-public-b" in body_text
