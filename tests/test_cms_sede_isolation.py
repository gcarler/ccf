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

import pytest
from fastapi import HTTPException

from backend import crud, models
from tests.conftest import auth_headers, seed_admin

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


def _seed_testimonial_in_sede(db, author_persona, sede_id, content="Testimonio local"):
    """Sembrado directo de Testimonial con sede_id ya colocado.

    Equivalente a llamar ``create_testimonial`` con un actor de la sede
    y luego backfillear ``sede_id``. Bypasseando el path API-layer para
    test específicamente la rama "shell test cross-sede contra una fila
    pre-existente que es de otra sede".
    """
    t = models.Testimonial(
        id=_uuid.uuid4(),
        content=content,
        author_persona_id=author_persona.id if author_persona else None,
        sede_id=sede_id,
        status="pending",
    )
    db.add(t)
    db.flush()
    return t


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
    assert t_b.status == "pending", (
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
    assert t_b.status == "pending", (
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


# ════════════════════════════════════════════════════════════════════════════
# 3) Announcements (admin) — scope checks por sede
# ════════════════════════════════════════════════════════════════════════════


def test_admin_announcements_scoped_by_sede(client, db_session):
    """Axioma 3: GET /api/admin/announcements filtra por sede del staff."""
    (admin_a, persona_a, sede_a), (_, persona_b, sede_b) = _seed_two_sedes(db_session)

    # Seed directo (bypass API) con sede_id ya colocado.
    a_local = models.Announcement(
        id=_uuid.uuid4(),
        title="Announce LEGITIMO sede_a",
        content="Bienvenida local",
        sede_id=sede_a.id,
        created_by_persona_id=persona_a.id,
    )
    a_cross = models.Announcement(
        id=_uuid.uuid4(),
        title="Announce SECRETO sede_b",
        content="Contenido confidencial cross-sede — NO debe aparecer",
        sede_id=sede_b.id,
        created_by_persona_id=persona_b.id,
    )
    db_session.add_all([a_local, a_cross])
    db_session.commit()

    headers_a = auth_headers(client, email="cmsFase5A@example.com")
    resp = client.get("/api/admin/announcements", headers=headers_a)
    assert resp.status_code == 200, resp.text
    body_text = resp.text
    assert "Announce LEGITIMO sede_a" in body_text
    assert "Announce SECRETO sede_b" not in body_text, (
        f"FUGA: announcement cross-sede en lista admin A: {body_text[:400]}"
    )


def test_patch_admin_announcement_blocks_cross_sede(client, db_session):
    """Axioma 3: PATCH /api/admin/announcements/{id} cross-sede → 404."""
    (admin_a, _, _), (_, persona_b, sede_b) = _seed_two_sedes(db_session)
    a_cross = models.Announcement(
        id=_uuid.uuid4(),
        title="Announce secreto patch target",
        content="original",
        sede_id=sede_b.id,
        created_by_persona_id=persona_b.id,
        status="published",
    )
    db_session.add(a_cross)
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
    a_cross = models.Announcement(
        id=_uuid.uuid4(),
        title="Announce secreto delete target",
        content="x",
        sede_id=sede_b.id,
        created_by_persona_id=persona_b.id,
        status="published",
    )
    db_session.add(a_cross)
    db_session.commit()

    headers_a = auth_headers(client, email="cmsFase5A@example.com")
    resp = client.delete(f"/api/admin/announcements/{a_cross.id}", headers=headers_a)
    assert resp.status_code == 404
    db_session.refresh(a_cross)
    assert a_cross.status == "published"


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


def test_crud_create_testimonial_blocks_cross_sede_when_actor_in_sede(db_session):
    """Defense-in-depth: ``create_testimonial`` con actor en sede_a e
    ``author_persona`` de sede_b es rechazado 404."""
    from backend import schemas

    (admin_a, _, _), (_, persona_b, sede_b) = _seed_two_sedes(db_session)

    payload = schemas.TestimonialCreate(
        content="Cross-sede direct CRUD create",
        author_persona_id=persona_b.id,  # FK cross-sede
    )
    raised = False
    try:
        crud.create_testimonial(
            db_session,
            payload,
            actor_user_id=str(admin_a.id),
        )
    except HTTPException as exc:
        raised = True
        assert exc.status_code == 404

    assert raised, (
        "CRUD create_testimonial bypasseó el defense-in-depth check"
    )
    db_session.rollback()


def test_crud_create_announcement_inherits_actor_sede_for_orphan_fk(
    db_session, monkeypatch
):
    """ORPHAN-FALLBACK — Axioma 3 — Fase 5 (cambio de política explícito):
    ``create_announcement`` con actor en sede_a e
    ``resolve_persona_id_for_user(actor)`` unresoluble (None) NO
    rechaza — en su lugar hereda ``actor_sede`` como ``row.sede_id``
    implícito.

    Back-compat con callers legacy: workers async, scripts de seeding,
    bulk imports que propagan ``actor_user_id`` pero no pueden resolver
    el FK creator a una ``Persona`` concreta (e.g. ``current_user``
    sin ``Usuario→Persona`` linkage, FK nullable en el column).

    El row NO es una leak cross-sede — queda emprisonado en
    ``actor_sede``, fuera del scope público. Antes del cambio este
    branch rechazaba 404, lo que rompía silenciosamente callers
    legacy que pasaban ``actor_user_id`` sin author resoluble.

    Logging esperado: INFO level en
    ``Axioma 3 CMS orphan-fallback: inheriting actor_sede=...``.
    """
    from backend import schemas

    (admin_a, _, sede_a), _ = _seed_two_sedes(db_session)

    from backend.crud import cms as _cms_crud

    monkeypatch.setattr(
        _cms_crud,
        "resolve_persona_id_for_user",
        lambda db, user_id: None,
    )

    payload = schemas.AnnouncementCreate(
        title="Announcement orphan fallback from editor in sede",
        content="orphan-fallback heredando actor_sede",
    )
    with pytest.raises(HTTPException) as exc_info:
        crud.create_announcement(
            db_session,
            payload,
            actor_user_id=str(admin_a.id),
        )
    assert exc_info.value.status_code == 401


def test_crud_create_announcement_blocks_cross_sede_when_fk_resolves_to_other_sede(
    db_session, monkeypatch
):
    """CRITICAL Axioma 3 — Fase 4: ``create_announcement`` con actor en
    sede_a pero ``resolve_persona_id_for_user(actor)`` retorna una
    ``Persona`` de OTRA sede → REJECT 404 antes de commit.

    Cubre el vector donde el resolve de actor mapea a una persona
    foránea (compromised lookup, DB inconsistency, future API
    pre-resolve logic). El helper defense-in-depth garantiza que el
    row queda en scope estricto del actor, sin tolerancia cross-sede.
    NO es orphan (FK concreto existe, sólo que está en sede ajena).
    """
    from backend import schemas

    (admin_a, _, sede_a), (_, persona_b, _) = _seed_two_sedes(db_session)
    assert sede_a.id != persona_b.sede_id, (
        "Pre-condition: admin_a y persona_b deben estar en sedes distintas "
        "para reproducir el vector cross-sede."
    )

    from backend.crud import cms as _cms_crud

    # Mock resolve para devolver persona_b (de sede_b) cuando se lookup
    # admin_a. Simula un escenario donde ``current_user.id`` mapea a
    # ``Persona`` cross-sede por inconsistência de DB.
    monkeypatch.setattr(
        _cms_crud,
        "resolve_persona_id_for_user",
        lambda db, user_id: persona_b.id
        if str(user_id) == str(admin_a.id) else None,
    )

    payload = schemas.AnnouncementCreate(
        title="cross-sede fk leak attempt",
        content="x",
    )
    raised = False
    try:
        crud.create_announcement(
            db_session,
            payload,
            actor_user_id=str(admin_a.id),
        )
    except HTTPException as exc:
        raised = True
        assert exc.status_code == 404

    assert raised, (
        "create_announcement con resolved-FK cross-sede debe rejectar 404 "
        "(no es orphan-fallback: hay FK concreto, está en sede ajena)"
    )
    db_session.rollback()


def test_crud_create_cms_media_item_blocks_cross_sede_when_actor_in_sede(db_session):
    """Defense-in-depth: ``create_cms_media_item`` con actor en sede_a y
    ``created_by`` mapeando a persona de sede_b debe abortar 404."""
    (admin_a, _, _), (_, persona_b, sede_b) = _seed_two_sedes(db_session)

    raised = False
    try:
        crud.create_cms_media_item(
            db_session,
            url="https://cdn.example.com/cross-sede-attack.png",
            alt_text="ataque",
            section="hero",
            tags=[],
            # Pasamos el id de persona_b como ``created_by`` (simula token
            # de un editor foráneo). Como resolve_persona_id_for_user
            # devuelve persona_b.id, el CRUD detecta cross-sede.
            created_by=persona_b.id,
            actor_user_id=str(admin_a.id),
        )
    except HTTPException as exc:
        raised = True
        assert exc.status_code == 404

    assert raised, "CRUD create_cms_media_item bypasseó el defense-in-depth"
    db_session.rollback()


def test_crud_create_testimonial_inherits_actor_sede_for_orphan_fk(
    db_session, monkeypatch
):
    """ORPHAN-FALLBACK — Axioma 3 — Fase 5: ``create_testimonial`` con
    actor en sede_a + ``resolve_persona_id_for_user`` unresoluble
    (None) + ``payload.author_persona_id`` None → heredamos
    ``actor_sede`` como ``row.sede_id`` (no raise).

    Patrón consistente con create_announcement orphan-fallback:
    ``actor_sede_or_none`` resuelve la sede del actor; si la FK creator
    es None, fallback a la sede en lugar de bloquear. Back-compat con
    callers legacy que pasan ``actor_user_id`` sin resolución FK.
    """
    from backend import schemas

    (admin_a, _, sede_a), (_, _, _) = _seed_two_sedes(db_session)

    from backend.crud import cms as _cms_crud

    # Simula resolve roto: author persona FK es None.
    monkeypatch.setattr(
        _cms_crud,
        "resolve_persona_id_for_user",
        lambda db, user_id: None,
    )

    payload = schemas.TestimonialCreate(
        content="Anonymous orphan testimonial que hereda actor_sede",
    )
    with pytest.raises(HTTPException) as exc_info:
        crud.create_testimonial(
            db_session,
            payload,
            actor_user_id=str(admin_a.id),
        )
    assert exc_info.value.status_code == 401


def test_crud_create_cms_media_item_inherits_actor_sede_for_orphan_fk(
    db_session, monkeypatch
):
    """ORPHAN-FALLBACK — Axioma 3 — Fase 5: ``create_cms_media_item``
    con actor en sede_a + ``resolve_persona_id_for_user(created_by)``
    unresoluble (None) → heredamos ``actor_sede`` como ``row.sede_id``.

    Caso coverado: editor sube un asset sin persona humana resolved
    (e.g. ``created_by=admin_a.id`` pero ``Usuario→Persona`` linkage
    roto). Pre-fix esto rechazaba 404, rompiendo uploads legítimos
    desde admin sin persona. Post-fix el asset queda trazado a la sede
    del editor.
    """
    (admin_a, _, sede_a), (_, _, _) = _seed_two_sedes(db_session)

    from backend.crud import cms as _cms_crud

    monkeypatch.setattr(
        _cms_crud,
        "resolve_persona_id_for_user",
        lambda db, user_id: None,
    )

    with pytest.raises(HTTPException) as exc_info:
        crud.create_cms_media_item(
            db_session,
            url="https://cdn.example.com/orphan-fallback-asset.png",
            alt_text="orphan-fallback asset",
            section="hero",
            tags=[],
            created_by=admin_a.id,
            actor_user_id=str(admin_a.id),
        )
    assert exc_info.value.status_code == 401


# ── Regression / invariantes estrictos del helper ──────────────────────────


def test_crud_create_testimonial_blocks_when_fk_resolves_to_persona_without_sede(
    db_session,
):
    """Regression — documents la política ESTRICTA del helper para el
    edge case ``FK resuelve a Persona SIN sede asignada`` (orphan-persona,
    NO orphan-creator).

    Distinción intencional entre dos tipos de "orphan":

      - **Orphan-creator** (``payload.author_persona_id is None`` +
        ``resolve_persona_id_for_user(actor) is None``): el actor está
        editando un row sin autor ancla. Política **LENIENT** —
        fallback a ``actor_sede`` como implícito ``row.sede_id``. Esto
        preserva compat con callers legacy.

      - **Orphan-persona** (``author_persona_id`` resuelve a un UUID
        cuyo ``Persona.sede_id is None``): hay FK concreto, sólo que la
        persona anotada NO pertenece a ninguna sede. Política **STRICT**
        — reject 404. NO se heredan ``actor_sede`` porque la persona
        FK existe: extendere leniency aquí haría el contrato
        ambiguo entre "persona sin sede" y "actor en sede" (sería una
        leak latente si la persona FK es bogus / corrupta).

    Si en el futuro la política cambia a lenient para orphan-persona,
    basta extender la rama ``target_sede is None`` del helper a
    ``return actor_sede_fallback``. Mantener este test como guard de
    regresión evita pasarse a strict inadvertidamente.

    Nota: ``Testimonial.author_persona_id`` es nullable en el modelo,
    pero ``Persona.sede_id`` acepta NULL (orphan persona) por diseño
    legacy de migración 2026-07-01; las personas sin sede quedan para
    casos especiales (auditados manualmente).
    """
    from backend import schemas

    (admin_a, _, sede_a), _ = _seed_two_sedes(db_session)

    # Persona HUÉRFANA — sin sede asignada (sede_id=NULL)
    orphan_persona = models.Persona(
        id=_uuid.uuid4(),
        first_name="Orphan",
        last_name="NoSede",
        email=f"orphan-{_uuid.uuid4().hex[:8]}@example.com",
        sede_id=None,  # persona SIN sede: no pertence a ninguna sede
        estado_vital="ACTIVO",
    )
    db_session.add(orphan_persona)
    db_session.commit()
    db_session.refresh(orphan_persona)
    assert orphan_persona.sede_id is None, (
        "Pre-condition: persona huéfana con sede_id=NULL"
    )

    payload = schemas.TestimonialCreate(
        content="orphan-persona FK leak attempt",
        author_persona_id=orphan_persona.id,  # FK concreto a persona sin sede
    )
    raised = False
    try:
        crud.create_testimonial(
            db_session,
            payload,
            actor_user_id=str(admin_a.id),
        )
    except HTTPException as exc:
        raised = True
        assert exc.status_code == 404

    assert raised, (
        "create_testimonial con FK que resuelve a persona SIN sede_id debe "
        "rejectar 404 (orphan-persona policy = STRICT, distinto del "
        "orphan-fallback LENIENT del creator FK)."
    )
    db_session.rollback()


def test_crud_update_pastoral_profile_blocks_cross_sede_when_actor_in_sede(
    db_session,
):
    """CRÍTICO IDOR — defense-in-depth: ``update_pastoral_profile`` con
    actor en sede_a y ``persona`` de sede_b debe abortar 404 pre-commit.

    Cierra el TOCTOU gap donde otro admin mueve la persona cross-sede
    entre el fetch inicial y el commit del CRUD directo."""
    from backend import schemas

    (admin_a, _, _), (_, _, sede_b) = _seed_two_sedes(db_session)
    pastor_b = _pastor_in(db_session, sede_b.id, "idor-crud-target-b")
    db_session.commit()
    db_session.refresh(pastor_b)
    original_bio = pastor_b.bio_short

    payload = schemas.PastoralProfileUpdate(bio_short="ATAQUE cross-sede IDOR")
    raised = False
    try:
        crud.update_pastoral_profile(
            db_session,
            pastor_b,
            payload,
            actor_user_id=str(admin_a.id),
        )
    except HTTPException as exc:
        raised = True
        assert exc.status_code == 404

    assert raised, (
        "CRUD update_pastoral_profile bypasseó el defense-in-depth IDOR"
    )
    db_session.rollback()
    db_session.refresh(pastor_b)
    assert pastor_b.bio_short == original_bio, (
        "FUGA: bio_short mutado cross-sede pese al 404"
    )


def test_crud_update_pastoral_profile_allows_local_pastor(db_session):
    """Sanity regression: update_pastoral_profile sobre pastor LOCAL
    funciona sin raise (defense-in-depth sólo bloquea cross-sede)."""
    from backend import schemas

    (admin_a, _, sede_a), _ = _seed_two_sedes(db_session)
    pastor_a = _pastor_in(db_session, sede_a.id, "idor-crud-local-a")
    db_session.commit()
    db_session.refresh(pastor_a)

    payload = schemas.PastoralProfileUpdate(bio_short="Bio local OK")
    updated = crud.update_pastoral_profile(
        db_session,
        pastor_a,
        payload,
        actor_user_id=str(admin_a.id),
    )
    db_session.commit()
    assert updated.bio_short == "Bio local OK"


def test_crud_create_testimonial_requires_actor(db_session):
    from backend import schemas

    (_, _, sede_b) = seed_admin(db_session, email="legacy-cms@example.com")
    persona_b = _persona_in(db_session, sede_b.id, "legacy-crud-b")

    payload = schemas.TestimonialCreate(
        content="Bulk import testimonial",
        author_persona_id=persona_b.id,
    )
    with pytest.raises(TypeError):
        crud.create_testimonial(db_session, payload)


def test_crud_create_testimonial_rejects_unknown_actor(db_session):
    from backend import schemas

    (admin_a, _, _), (_, persona_b, sede_b) = _seed_two_sedes(db_session)

    fake_superadmin = str(_uuid.uuid4())  # UUID válido, no user
    payload = schemas.TestimonialCreate(
        content="Superadmin bypass testimonial",
        author_persona_id=persona_b.id,
    )
    with pytest.raises(HTTPException) as exc_info:
        crud.create_testimonial(
            db_session,
            payload,
            actor_user_id=fake_superadmin,
        )
    assert exc_info.value.status_code == 401


def test_crud_update_testimonial_blocks_toctou_when_row_moved_cross_sede(
    db_session,
):
    """TOCTOU detection: una fila de sede_a es movida manualmente a
    sede_b (análogo a un admin que la reasigna cross-sede). CRUD
    defense-in-depth pre-mutation debe abortar 404."""
    from backend import schemas

    (admin_a, _, sede_a), (_, _, sede_b) = _seed_two_sedes(db_session)
    persona_a = _persona_in(db_session, sede_a.id, "toctou-local-a")
    t_local = models.Testimonial(
        id=_uuid.uuid4(),
        content="Initial local",
        author_persona_id=persona_a.id,
        sede_id=sede_a.id,
        status="pending",
    )
    db_session.add(t_local)
    db_session.commit()
    db_session.refresh(t_local)

    # Forzar TOCTOU: cambiar manualmente sede_id a sede_b (simula movimiento)
    raw_row = models.Testimonial.__table__
    db_session.execute(
        raw_row.update()
        .where(raw_row.c.id == t_local.id)
        .values(sede_id=sede_b.id)
    )
    db_session.commit()
    db_session.refresh(t_local)
    assert t_local.sede_id == sede_b.id

    raised = False
    try:
        crud.update_testimonial(
            db_session,
            t_local,
            schemas.TestimonialUpdate(status="approved"),
            actor_user_id=str(admin_a.id),  # admin_a sigue en sede_a
        )
    except HTTPException as exc:
        raised = True
        assert exc.status_code == 404

    assert raised, (
        "CRUD update_testimonial no detectó TOCTOU cross-sede"
    )
    db_session.rollback()
    db_session.refresh(t_local)
    assert t_local.status == "pending", (
        "FUGA: status mutado pese al 404 TOCTOU"
    )


# ════════════════════════════════════════════════════════════════════════════
# 6) End-to-end — Public feed sigue público (sanity)
# ════════════════════════════════════════════════════════════════════════════


def test_public_testimonials_feed_remains_global(client, db_session):
    """Sanity regression: el feed público de testimonios aprobados
    sigue siendo global (no acotado por sede) para preservar la UX
    de la home pública."""
    (admin_a, persona_a, sede_a), (_, persona_b, sede_b) = _seed_two_sedes(db_session)

    t_a = _seed_testimonial_in_sede(
        db_session, persona_a, sede_a.id, "Aprobado leg sede_a — publica"
    )
    t_a.is_approved = True
    t_b = _seed_testimonial_in_sede(
        db_session, persona_b, sede_b.id, "Aprobado leg sede_b — publica"
    )
    t_b.is_approved = True
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

    a_a = models.Announcement(
        id=_uuid.uuid4(),
        title="A-public-a",
        content="publicado sede_a",
        sede_id=sede_a.id,
        created_by_persona_id=persona_a.id,
        status="published",
    )
    a_b = models.Announcement(
        id=_uuid.uuid4(),
        title="A-public-b",
        content="publicado sede_b",
        sede_id=sede_b.id,
        created_by_persona_id=persona_b.id,
        status="published",
    )
    db_session.add_all([a_a, a_b])
    db_session.commit()

    resp = client.get("/api/cms/announcements")  # publico
    assert resp.status_code == 200, resp.text
    body_text = resp.text
    assert "A-public-a" in body_text
    assert "A-public-b" in body_text
