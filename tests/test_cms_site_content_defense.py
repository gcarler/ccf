"""Defense-in-depth tests for CmsPost / CmsCategory / CmsTag sede scope.

These entities don't have ``sede_id`` own — they scope via ``site_id`` →
``CmsSite.sede_id``. The API layer already enforces scope via
``_get_scoped_site_or_404``, but the CRUD layer now re-validates via
``_crud_scope_re_check_cms_site_content`` to protect callers non-API
(workers, scripts, tests directos).

Mirrors the pattern of ``test_cms_sede_isolation.py`` for UGC content.
"""
import uuid

import pytest
from fastapi import HTTPException

from backend import crud, models, schemas
from backend.core.security import get_password_hash
from backend.models_auth import Usuario
from tests.conftest import seed_admin as _seed_admin


def _seed_two_sedes(db):
    """Create two admins in two different sedes.

    ``seed_admin`` returns a tuple ``(user, persona, sede)``.
    We create a second sede + user_b for cross-sede testing.
    Returns ``(user_b, user_a, sede_b, sede_a)``.
    """
    user_a, persona_a, sede_a = _seed_admin(db)
    assert sede_a is not None, "seed_admin must produce a sede"

    # Create a second sede + admin in that sede
    sede_b = models.Sede(
        nombre=f"Sede B {uuid.uuid4().hex[:6]}",
        ciudad="Ciudad B",
        es_activa=True,
    )
    db.add(sede_b)
    db.flush()

    persona_b = models.Persona(
        id=uuid.uuid4(),
        first_name="Admin",
        last_name="B",
        email=f"admin_b_{uuid.uuid4().hex[:8]}@test.com",
        sede_id=sede_b.id,
        estado_vital="ACTIVO",
    )
    db.add(persona_b)
    db.flush()

    # Reuse the same rol_plataforma as admin_a if it exists, else create one
    rol = db.query(models.RolPlataforma).filter(
        models.RolPlataforma.nombre == "admin"
    ).first()
    if rol is None:
        rol = models.RolPlataforma(nombre="admin")
        db.add(rol)
        db.flush()

    user_b = Usuario(
        id=persona_b.id,
        sede_id=sede_b.id,
        username=persona_b.email.split("@")[0],
        email=persona_b.email,
        password_hash=get_password_hash("testpass123"),
        rol_plataforma_id=rol.id,
        is_active=True,
        is_email_verified=True,
    )
    db.add(user_b)
    db.commit()

    return user_b, user_a, sede_b, sede_a


def _seed_site_in_sede(db, sede_id, site_key="test-site"):
    """Create a CmsSite scoped to a sede. Returns the site."""
    site = models.CmsSite(
        site_key=f"{site_key}-{uuid.uuid4().hex[:6]}",
        name="Test Site",
        base_path="/test",
        is_active=True,
        sede_id=sede_id,
    )
    db.add(site)
    db.commit()
    db.refresh(site)
    return site


def _seed_category_in_site(db, site_id, slug="test-cat"):
    """Create a CmsCategory in a site. Returns the category."""
    cat = models.CmsCategory(
        site_id=site_id,
        slug=f"{slug}-{uuid.uuid4().hex[:6]}",
        name="Test Category",
        is_active=True,
    )
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


def _seed_tag_in_site(db, site_id, slug="test-tag"):
    """Create a CmsTag in a site. Returns the tag."""
    tag = models.CmsTag(
        site_id=site_id,
        slug=f"{slug}-{uuid.uuid4().hex[:6]}",
        name="Test Tag",
        is_active=True,
    )
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag


def _seed_post_in_site(db, site_id, persona_id, slug="test-post"):
    """Create a CmsPost in a site. Returns the post."""
    post = models.CmsPost(
        site_id=site_id,
        slug=f"{slug}-{uuid.uuid4().hex[:6]}",
        title="Test Post",
        status="draft",
        author_persona_id=persona_id,
        created_by_persona_id=persona_id,
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


def _get_persona_in_sede(db, sede_id):
    """Find or create a Persona in a given sede. Returns the persona."""
    persona = db.query(models.Persona).filter(
        models.Persona.sede_id == sede_id
    ).first()
    if persona is None:
        persona = models.Persona(
            id=uuid.uuid4(),
            first_name="Test",
            last_name="User",
            email=f"user_{uuid.uuid4().hex[:8]}@test.com",
            sede_id=sede_id,
            estado_vital="ACTIVO",
        )
        db.add(persona)
        db.commit()
        db.refresh(persona)
    return persona


# ── CmsCategory defense-in-depth ──────────────────────────────────────────


class TestCategoryDefenseInDepth:
    """CRUD-direct cross-sede scope validation for CmsCategory."""

    def test_create_category_cross_sede_blocked(self, db_session):
        user_b, user_a, sede_b, sede_a = _seed_two_sedes(db_session)
        site_a = _seed_site_in_sede(db_session, sede_a.id, "site-a")

        payload = schemas.CmsCategoryCreate(
            slug="cross-sede-cat",
            name="Cross Sede",
        )
        # admin_b (sede_b) tries to create a category in site_a (sede_a)
        with pytest.raises(HTTPException) as exc_info:
            crud.create_cms_category(
                db_session, site_a.id, payload,
                actor_user_id=str(user_b.id),
            )
        assert exc_info.value.status_code == 404

    def test_create_category_same_sede_ok(self, db_session):
        user_b, user_a, sede_b, sede_a = _seed_two_sedes(db_session)
        site_b = _seed_site_in_sede(db_session, sede_b.id, "site-b")

        payload = schemas.CmsCategoryCreate(
            slug="same-sede-cat",
            name="Same Sede",
        )
        row = crud.create_cms_category(
            db_session, site_b.id, payload,
            actor_user_id=str(user_b.id),
        )
        assert row is not None
        assert row.slug == "same-sede-cat"

    def test_create_category_no_actor_bypasses(self, db_session):
        """Without actor_user_id, no scope check runs (backward compat)."""
        user_b, user_a, sede_b, sede_a = _seed_two_sedes(db_session)
        site_a = _seed_site_in_sede(db_session, sede_a.id, "site-a")

        payload = schemas.CmsCategoryCreate(
            slug="no-actor-cat",
            name="No Actor",
        )
        # No actor_user_id → no check (backward compat for scripts/seeds)
        row = crud.create_cms_category(db_session, site_a.id, payload)
        assert row is not None

    def test_update_category_same_sede_ok(self, db_session):
        user_b, user_a, sede_b, sede_a = _seed_two_sedes(db_session)
        site_b = _seed_site_in_sede(db_session, sede_b.id, "site-b")
        cat_b = _seed_category_in_site(db_session, site_b.id, "cat-b")

        payload = schemas.CmsCategoryUpdate(name="Updated Category")
        row = crud.update_cms_category(
            db_session, cat_b, payload,
            actor_user_id=str(user_b.id),
        )
        assert row is not None
        assert row.name == "Updated Category"

    def test_update_category_cross_sede_blocked(self, db_session):
        user_b, user_a, sede_b, sede_a = _seed_two_sedes(db_session)
        site_a = _seed_site_in_sede(db_session, sede_a.id, "site-a")
        cat_a = _seed_category_in_site(db_session, site_a.id)

        payload = schemas.CmsCategoryUpdate(name="Hacked")
        with pytest.raises(HTTPException) as exc_info:
            crud.update_cms_category(
                db_session, cat_a, payload,
                actor_user_id=str(user_b.id),
            )
        assert exc_info.value.status_code == 404

    def test_delete_category_same_sede_ok(self, db_session):
        user_b, user_a, sede_b, sede_a = _seed_two_sedes(db_session)
        site_b = _seed_site_in_sede(db_session, sede_b.id, "site-b")
        cat_b = _seed_category_in_site(db_session, site_b.id, "cat-b")

        crud.delete_cms_category(
            db_session, cat_b,
            actor_user_id=str(user_b.id),
        )
        # Soft delete — verify is_active is False
        db_session.expire_all()
        refetched = db_session.query(models.CmsCategory).filter_by(id=cat_b.id).first()
        assert refetched is None or getattr(refetched, "is_active", True) is False

    def test_delete_category_cross_sede_blocked(self, db_session):
        user_b, user_a, sede_b, sede_a = _seed_two_sedes(db_session)
        site_a = _seed_site_in_sede(db_session, sede_a.id, "site-a")
        cat_a = _seed_category_in_site(db_session, site_a.id)

        with pytest.raises(HTTPException) as exc_info:
            crud.delete_cms_category(
                db_session, cat_a,
                actor_user_id=str(user_b.id),
            )
        assert exc_info.value.status_code == 404


# ── CmsTag defense-in-depth ───────────────────────────────────────────────


class TestTagDefenseInDepth:
    """CRUD-direct cross-sede scope validation for CmsTag."""

    def test_create_tag_cross_sede_blocked(self, db_session):
        user_b, user_a, sede_b, sede_a = _seed_two_sedes(db_session)
        site_a = _seed_site_in_sede(db_session, sede_a.id, "site-a")

        payload = schemas.CmsTagCreate(slug="cross-tag", name="Cross")
        with pytest.raises(HTTPException) as exc_info:
            crud.create_cms_tag(
                db_session, site_a.id, payload,
                actor_user_id=str(user_b.id),
            )
        assert exc_info.value.status_code == 404

    def test_create_tag_same_sede_ok(self, db_session):
        user_b, user_a, sede_b, sede_a = _seed_two_sedes(db_session)
        site_b = _seed_site_in_sede(db_session, sede_b.id, "site-b")

        payload = schemas.CmsTagCreate(slug="same-sede-tag", name="Same Sede Tag")
        row = crud.create_cms_tag(
            db_session, site_b.id, payload,
            actor_user_id=str(user_b.id),
        )
        assert row is not None
        assert row.name == "Same Sede Tag"

    def test_update_tag_same_sede_ok(self, db_session):
        user_b, user_a, sede_b, sede_a = _seed_two_sedes(db_session)
        site_b = _seed_site_in_sede(db_session, sede_b.id, "site-b")
        tag_b = _seed_tag_in_site(db_session, site_b.id, "tag-b")

        payload = schemas.CmsTagUpdate(name="Updated Tag")
        row = crud.update_cms_tag(
            db_session, tag_b, payload,
            actor_user_id=str(user_b.id),
        )
        assert row is not None
        assert row.name == "Updated Tag"

    def test_update_tag_cross_sede_blocked(self, db_session):
        user_b, user_a, sede_b, sede_a = _seed_two_sedes(db_session)
        site_a = _seed_site_in_sede(db_session, sede_a.id, "site-a")
        tag_a = _seed_tag_in_site(db_session, site_a.id)

        payload = schemas.CmsTagUpdate(name="Hacked")
        with pytest.raises(HTTPException) as exc_info:
            crud.update_cms_tag(
                db_session, tag_a, payload,
                actor_user_id=str(user_b.id),
            )
        assert exc_info.value.status_code == 404

    def test_delete_tag_same_sede_ok(self, db_session):
        user_b, user_a, sede_b, sede_a = _seed_two_sedes(db_session)
        site_b = _seed_site_in_sede(db_session, sede_b.id, "site-b")
        tag_b = _seed_tag_in_site(db_session, site_b.id, "tag-b")

        crud.delete_cms_tag(
            db_session, tag_b,
            actor_user_id=str(user_b.id),
        )
        # Delete should succeed — verify the tag is gone (or soft-deleted)
        db_session.expire_all()
        refetched = db_session.query(models.CmsTag).filter_by(id=tag_b.id).first()
        assert refetched is None or getattr(refetched, "is_active", True) is False

    def test_delete_tag_cross_sede_blocked(self, db_session):
        user_b, user_a, sede_b, sede_a = _seed_two_sedes(db_session)
        site_a = _seed_site_in_sede(db_session, sede_a.id, "site-a")
        tag_a = _seed_tag_in_site(db_session, site_a.id)

        with pytest.raises(HTTPException) as exc_info:
            crud.delete_cms_tag(
                db_session, tag_a,
                actor_user_id=str(user_b.id),
            )
        assert exc_info.value.status_code == 404


# ── CmsPost defense-in-depth ──────────────────────────────────────────────


class TestPostDefenseInDepth:
    """CRUD-direct cross-sede scope validation for CmsPost."""

    def test_create_post_cross_sede_blocked(self, db_session):
        user_b, user_a, sede_b, sede_a = _seed_two_sedes(db_session)
        site_a = _seed_site_in_sede(db_session, sede_a.id, "site-a")
        persona_a = _get_persona_in_sede(db_session, sede_a.id)

        payload = schemas.CmsPostCreate(
            slug="cross-post",
            title="Cross Post",
            status="draft",
        )
        with pytest.raises(HTTPException) as exc_info:
            crud.create_cms_post(
                db_session, site_a.id, payload, persona_a.id,
                actor_user_id=str(user_b.id),
            )
        assert exc_info.value.status_code == 404

    def test_create_post_same_sede_ok(self, db_session):
        user_b, user_a, sede_b, sede_a = _seed_two_sedes(db_session)
        site_b = _seed_site_in_sede(db_session, sede_b.id, "site-b")
        persona_b = _get_persona_in_sede(db_session, sede_b.id)

        payload = schemas.CmsPostCreate(
            slug="same-sede-post",
            title="Same Sede Post",
            status="draft",
        )
        row = crud.create_cms_post(
            db_session, site_b.id, payload, persona_b.id,
            actor_user_id=str(user_b.id),
        )
        assert row is not None
        assert row.title == "Same Sede Post"

    def test_update_post_same_sede_ok(self, db_session):
        user_b, user_a, sede_b, sede_a = _seed_two_sedes(db_session)
        site_b = _seed_site_in_sede(db_session, sede_b.id, "site-b")
        persona_b = _get_persona_in_sede(db_session, sede_b.id)
        post_b = _seed_post_in_site(db_session, site_b.id, persona_b.id, "post-b")

        payload = schemas.CmsPostUpdate(title="Updated Post Title")
        row = crud.update_cms_post(
            db_session, post_b, payload, persona_b.id,
            actor_user_id=str(user_b.id),
        )
        assert row is not None
        assert row.title == "Updated Post Title"

    def test_update_post_cross_sede_blocked(self, db_session):
        user_b, user_a, sede_b, sede_a = _seed_two_sedes(db_session)
        site_a = _seed_site_in_sede(db_session, sede_a.id, "site-a")
        persona_a = _get_persona_in_sede(db_session, sede_a.id)
        post_a = _seed_post_in_site(db_session, site_a.id, persona_a.id)

        payload = schemas.CmsPostUpdate(title="Hacked Title")
        with pytest.raises(HTTPException) as exc_info:
            crud.update_cms_post(
                db_session, post_a, payload, persona_a.id,
                actor_user_id=str(user_b.id),
            )
        assert exc_info.value.status_code == 404

    def test_delete_post_same_sede_ok(self, db_session):
        user_b, user_a, sede_b, sede_a = _seed_two_sedes(db_session)
        site_b = _seed_site_in_sede(db_session, sede_b.id, "site-b")
        persona_b = _get_persona_in_sede(db_session, sede_b.id)
        post_b = _seed_post_in_site(db_session, site_b.id, persona_b.id, "post-b")

        crud.delete_cms_post(
            db_session, post_b,
            actor_user_id=str(user_b.id),
        )
        # Delete should succeed — verify the post is gone (or soft-deleted)
        db_session.expire_all()
        refetched = db_session.query(models.CmsPost).filter_by(id=post_b.id).first()
        assert refetched is None or getattr(refetched, "status", None) == "archived"

    def test_delete_post_cross_sede_blocked(self, db_session):
        user_b, user_a, sede_b, sede_a = _seed_two_sedes(db_session)
        site_a = _seed_site_in_sede(db_session, sede_a.id, "site-a")
        persona_a = _get_persona_in_sede(db_session, sede_a.id)
        post_a = _seed_post_in_site(db_session, site_a.id, persona_a.id)

        with pytest.raises(HTTPException) as exc_info:
            crud.delete_cms_post(
                db_session, post_a,
                actor_user_id=str(user_b.id),
            )
        assert exc_info.value.status_code == 404


# ── Superadmin bypass ─────────────────────────────────────────────────────


class TestSuperadminBypass:
    """Superadmin (no sede) bypasses scope checks — consistent with Axioma 3.

    ``auth_users.sede_id`` is NOT NULL in the current schema, so a user
    with ``sede_id=None`` cannot be persisted in tests. The bypass path
    (``actor_sede is None``) is exercised here by monkeypatching
    ``get_user_sede_id`` to return ``None``, simulating a canonical
    superadministrator without sede.
    """

    def test_superadmin_create_category_no_sede_ok(self, db_session, monkeypatch):
        """Admin without sede bypasses check — even on a site in a different sede.

        Uses user_b (real sede_b) + site_a (sede_a) + mock→None to prove
        the bypass works when the actor's real sede differs from the site's.
        Without the mock this would be a 404 cross-sede block.
        """
        user_b, user_a, sede_b, sede_a = _seed_two_sedes(db_session)
        site_a = _seed_site_in_sede(db_session, sede_a.id, "site-a")

        # Mock get_user_sede_id to return None (superadmin without sede)
        monkeypatch.setattr(
            "backend.crud.crm.get_user_sede_id",
            lambda db, uid: None,
        )

        payload = schemas.CmsCategoryCreate(
            slug="superadmin-cat",
            name="Superadmin Cat",
        )
        row = crud.create_cms_category(
            db_session, site_a.id, payload,
            actor_user_id=str(user_b.id),
        )
        assert row is not None
        assert row.slug == "superadmin-cat"

    def test_superadmin_create_tag_no_sede_ok(self, db_session, monkeypatch):
        """Admin without sede bypasses check for CmsTag (cross-sede + mock)."""
        user_b, user_a, sede_b, sede_a = _seed_two_sedes(db_session)
        site_a = _seed_site_in_sede(db_session, sede_a.id, "site-a")

        monkeypatch.setattr(
            "backend.crud.crm.get_user_sede_id",
            lambda db, uid: None,
        )

        payload = schemas.CmsTagCreate(slug="superadmin-tag", name="Superadmin Tag")
        row = crud.create_cms_tag(
            db_session, site_a.id, payload,
            actor_user_id=str(user_b.id),
        )
        assert row is not None
        assert row.slug == "superadmin-tag"

    def test_superadmin_create_post_no_sede_ok(self, db_session, monkeypatch):
        """Admin without sede bypasses check for CmsPost (cross-sede + mock)."""
        user_b, user_a, sede_b, sede_a = _seed_two_sedes(db_session)
        site_a = _seed_site_in_sede(db_session, sede_a.id, "site-a")
        persona_a = _get_persona_in_sede(db_session, sede_a.id)

        monkeypatch.setattr(
            "backend.crud.crm.get_user_sede_id",
            lambda db, uid: None,
        )

        payload = schemas.CmsPostCreate(
            slug="superadmin-post",
            title="Superadmin Post",
            status="draft",
        )
        row = crud.create_cms_post(
            db_session, site_a.id, payload, persona_a.id,
            actor_user_id=str(user_b.id),
        )
        assert row is not None
        assert row.title == "Superadmin Post"
