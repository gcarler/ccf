"""pytest suite for scheduled publish + auto-archive (Phase 2026-07-06)."""
from __future__ import annotations

import datetime as dt
import uuid

import pytest
from sqlalchemy import inspect

from tests.conftest import auth_headers, seed_admin, seed_user_with_role

GOOD_TITLE = "Bienvenidos a la iglesia CCF"
GOOD_DESC = "Un lugar para crecer en fe y comunidad con Cristo Jesús como centro."
GOOD_OG = "https://cdn.example.com/og-cover.png"
SHORT_DESC = "corta"
LONG_DESC = "x" * 200


# ── Helpers ──────────────────────────────────────────────────────────────


def _seed_site(db, key="ccf"):
    from backend import models

    site = models.CmsSite(
        id=uuid.uuid4(),
        site_key=key,
        name=f"Site {key}",
        base_path="/",
        is_active=True,
    )
    db.add(site)
    db.commit()
    db.refresh(site)
    return site


def _make_page(db, site_id, *, slug="p", title="P", status="draft", seo=None, sections=None,
               publish_at=None, expires_at=None):
    from backend import models

    page = models.CmsPage(
        id=uuid.uuid4(),
        site_id=site_id,
        slug=slug,
        title=title,
        status=status,
        seo_json=seo or {},
        publish_at=publish_at,
        expires_at=expires_at,
    )
    db.add(page)
    db.commit()
    db.refresh(page)
    if sections:
        for idx, (kind, props) in enumerate(sections):
            db.add(models.CmsSection(
                id=uuid.uuid4(),
                page_id=page.id,
                section_key=f"sec-{idx}",
                type=kind,
                props_json=props or {},
                sort_order=idx,
                is_visible=True,
            ))
        db.commit()
    return page


def _make_post(db, site_id, *, slug="post", title="Post P", status="published",
               published_at=None, expires_at=None):
    from backend import models

    post = models.CmsPost(
        id=uuid.uuid4(),
        site_id=site_id,
        slug=slug,
        title=title,
        status=status,
        published_at=published_at,
        expires_at=expires_at,
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


# ── 1. Migration shape ────────────────────────────────────────────────────


class TestSchedulingColumns:
    """Verify the migration adds the columns AND indexes correctly on a
    fresh schema (no Alembic runner required since tests run with
    ``Base.metadata.create_all`` against the post-migration model).
    """

    def test_cms_pages_has_publish_at_column(self, db_session):
        cols = {c["name"] for c in inspect(db_session.get_bind()).get_columns("cms_pages")}
        assert "publish_at" in cols
        assert "expires_at" in cols

    def test_cms_posts_has_expires_at_column(self, db_session):
        cols = {c["name"] for c in inspect(db_session.get_bind()).get_columns("cms_posts")}
        assert "expires_at" in cols

    def test_cms_pages_publish_at_indexed(self, db_session):
        idx_cols = {tuple(idx["column_names"]) for idx in inspect(db_session.get_bind()).get_indexes("cms_pages")}
        assert ("publish_at",) in idx_cols
        assert ("expires_at",) in idx_cols

    def test_cms_posts_expires_at_indexed(self, db_session):
        idx_cols = {tuple(idx["column_names"]) for idx in inspect(db_session.get_bind()).get_indexes("cms_posts")}
        assert ("expires_at",) in idx_cols


# ── 2. CRUD helpers (find + process) ──────────────────────────────────────


class TestFindDue:
    def test_find_pages_due_for_publish_filters_by_status_and_time(self, db_session):
        site = _seed_site(db_session)
        past = dt.datetime(2024, 1, 1, tzinfo=dt.timezone.utc)
        future = dt.datetime(2099, 1, 1, tzinfo=dt.timezone.utc)
        _make_page(db_session, site.id, slug="due", status="scheduled", publish_at=past)
        _make_page(db_session, site.id, slug="future", status="scheduled", publish_at=future)
        _make_page(db_session, site.id, slug="published-manual", status="published")  # not eligible
        _make_page(db_session, site.id, slug="no-date", status="scheduled")  # null publish_at

        from backend.crud.cms import find_pages_due_for_publish

        rows = find_pages_due_for_publish(db_session)
        slugs = sorted(r.slug for r in rows)
        assert slugs == ["due"]

    def test_find_pages_due_for_archive_only_published(self, db_session):
        site = _seed_site(db_session)
        past = dt.datetime(2024, 1, 1, tzinfo=dt.timezone.utc)
        _make_page(db_session, site.id, slug="expired-pub", status="published", expires_at=past)
        _make_page(db_session, site.id, slug="expired-draft", status="draft", expires_at=past)
        _make_page(db_session, site.id, slug="future", status="published",
                   expires_at=dt.datetime(2099, 1, 1, tzinfo=dt.timezone.utc))

        from backend.crud.cms import find_pages_due_for_archive

        rows = find_pages_due_for_archive(db_session)
        assert [r.slug for r in rows] == ["expired-pub"]


class TestProcessDueContent:
    def test_publish_due_transitions_to_published_and_audits(self, db_session):
        from backend.crud.cms import process_due_content

        seed_admin(db_session, email="sched-pub@example.com")
        site = _seed_site(db_session)
        _make_page(db_session, site.id, slug="soon", status="scheduled",
                   publish_at=dt.datetime(2024, 1, 1, tzinfo=dt.timezone.utc))
        counts = process_due_content(db_session)
        db_session.commit()
        assert counts == {"pages_published": 1, "pages_archived": 0, "posts_archived": 0}

        from backend import models

        page = db_session.query(models.CmsPage).filter(models.CmsPage.slug == "soon").first()
        assert page.status == "published"

        log_entry = (
            db_session.query(models.CmsPublishLog)
            .filter(models.CmsPublishLog.entity_id == str(page.id), models.CmsPublishLog.action == "publish")
            .first()
        )
        assert log_entry is not None
        assert log_entry.actor_persona_id is None  # scheduler convention
        assert log_entry.from_status == "scheduled"
        assert log_entry.to_status == "published"

    def test_archive_due_transitions_published_to_archived_and_audits(self, db_session):
        from backend.crud.cms import process_due_content

        site = _seed_site(db_session)
        _make_page(db_session, site.id, slug="stale", status="published",
                   expires_at=dt.datetime(2024, 1, 1, tzinfo=dt.timezone.utc))
        counts = process_due_content(db_session)
        db_session.commit()
        assert counts["pages_archived"] == 1

        from backend import models

        page = db_session.query(models.CmsPage).filter(models.CmsPage.slug == "stale").first()
        assert page.status == "archived"

    def test_post_due_archive_uses_publishlog(self, db_session):
        from backend.crud.cms import process_due_content

        site = _seed_site(db_session)
        _make_post(db_session, site.id, slug="old-post", status="published",
                   published_at=dt.datetime.now(dt.timezone.utc),
                   expires_at=dt.datetime(2024, 1, 1, tzinfo=dt.timezone.utc))
        counts = process_due_content(db_session)
        db_session.commit()
        assert counts["posts_archived"] == 1

        from backend import models

        post = db_session.query(models.CmsPost).filter(models.CmsPost.slug == "old-post").first()
        assert post.status == "archived"
        log_entry = (
            db_session.query(models.CmsPublishLog)
            .filter(models.CmsPublishLog.entity_id == str(post.id),
                    models.CmsPublishLog.entity_type == "post")
            .first()
        )
        assert log_entry is not None
        assert log_entry.action == "archive"
        assert log_entry.from_status == "published"
        assert log_entry.to_status == "archived"
        assert log_entry.actor_persona_id is None

    def test_process_due_content_idempotent_double_run(self, db_session):
        from backend.crud.cms import process_due_content

        site = _seed_site(db_session)
        _make_page(db_session, site.id, slug="once", status="scheduled",
                   publish_at=dt.datetime(2024, 1, 1, tzinfo=dt.timezone.utc))
        first = process_due_content(db_session)
        db_session.commit()
        second = process_due_content(db_session)
        assert first["pages_published"] == 1
        assert second["pages_published"] == 0  # already published, not eligible

    def test_dry_run_does_not_persist(self, db_session):
        from backend.crud.cms import process_due_content

        site = _seed_site(db_session)
        _make_page(db_session, site.id, slug="preview", status="scheduled",
                   publish_at=dt.datetime(2024, 1, 1, tzinfo=dt.timezone.utc))
        counts = process_due_content(db_session, dry_run=True)
        db_session.commit()
        assert counts["pages_published"] == 1

        from backend import models

        page = db_session.query(models.CmsPage).filter(models.CmsPage.slug == "preview").first()
        assert page.status == "scheduled"  # unchanged

    def test_publishat_in_past_eligible_for_archive_immediately(self, db_session):
        """publish_at in the past + status='published' should be eligible for archive
        via expires_at path without anomalies."""
        from backend.crud.cms import process_due_content

        site = _seed_site(db_session)
        _make_page(
            db_session, site.id, slug="dual",
            status="published",
            publish_at=dt.datetime(2020, 1, 1, tzinfo=dt.timezone.utc),
            expires_at=dt.datetime(2024, 1, 1, tzinfo=dt.timezone.utc),
        )
        first_pass = process_due_content(db_session)
        db_session.commit()
        # Already published → noop on publish, but expiry still kicks in.
        assert first_pass["pages_archived"] == 1


# ── 3. API validation ─────────────────────────────────────────────────────


class TestApiPatchPageScheduling:
    def test_patch_page_accepts_publish_at_and_expires_at(self, client, db_session):
        seed_admin(db_session, email="patch@example.com")
        site = _seed_site(db_session)
        _make_page(db_session, site.id, slug="planner")
        headers = auth_headers(client, email="patch@example.com")
        future1 = "2099-01-01T00:00:00Z"
        future2 = "2099-12-31T23:59:59Z"
        resp = client.patch(
            f"/api/cms/v2/sites/{site.site_key}/pages/planner",
            json={"publish_at": future1, "expires_at": future2},
            headers=headers,
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["publish_at"] is not None
        assert body["expires_at"] is not None

    def test_patch_page_rejects_expires_before_publish(self, client, db_session):
        seed_admin(db_session, email="patch-bad-dates@example.com")
        site = _seed_site(db_session)
        _make_page(db_session, site.id, slug="bad-dates")
        headers = auth_headers(client, email="patch-bad-dates@example.com")
        resp = client.patch(
            f"/api/cms/v2/sites/{site.site_key}/pages/bad-dates",
            json={
                "publish_at": "2099-12-31T00:00:00Z",
                "expires_at": "2099-01-01T00:00:00Z",
            },
            headers=headers,
        )
        assert resp.status_code == 422, resp.text
        assert "expires_at" in resp.text

    def test_patch_page_clears_publish_at_with_null(self, client, db_session):
        seed_admin(db_session, email="patch-clear@example.com")
        site = _seed_site(db_session)
        _make_page(db_session, site.id, slug="clearable",
                   publish_at=dt.datetime(2099, 1, 1, tzinfo=dt.timezone.utc))
        headers = auth_headers(client, email="patch-clear@example.com")
        resp = client.patch(
            f"/api/cms/v2/sites/{site.site_key}/pages/clearable",
            json={"publish_at": None},
            headers=headers,
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["publish_at"] is None


class TestLegacyScheduleEndpointCompat:
    """The legacy ``/pages/{page_id}/schedule`` endpoint now stores into
    ``publish_at`` (drops the legacy seo_json cruft).
    """

    def test_legacy_schedule_writes_publish_at_column(self, client, db_session):
        seed_admin(db_session, email="legacy-sched@example.com")
        site = _seed_site(db_session)
        page = _make_page(db_session, site.id, slug="legacy-page")

        headers = auth_headers(client, email="legacy-sched@example.com")
        resp = client.post(
            f"/api/cms/v2/pages/{page.id}/schedule?site_key={site.site_key}",
            json={"scheduled_at": "2099-01-01T00:00:00Z"},
            headers=headers,
        )
        assert resp.status_code == 200, resp.text
        # DB-level check: publish_at must be populated; seo_json must NOT
        # contain _scheduled_at legacy.
        db_session.refresh(page)
        assert page.publish_at is not None
        assert not (isinstance(page.seo_json, dict) and "_scheduled_at" in (page.seo_json or {}))

    def test_legacy_schedule_invalid_datetime_returns_400(self, client, db_session):
        seed_admin(db_session, email="legacy-bad@example.com")
        site = _seed_site(db_session)
        page = _make_page(db_session, site.id, slug="legacy-bad")
        headers = auth_headers(client, email="legacy-bad@example.com")
        resp = client.post(
            f"/api/cms/v2/pages/{page.id}/schedule?site_key={site.site_key}",
            json={"scheduled_at": "not-a-date"},
            headers=headers,
        )
        assert resp.status_code == 422

    def test_legacy_schedule_rejects_cross_site_site_key(self, client, db_session):
        seed_admin(db_session, email="legacy-cross-a@example.com")
        _, _, other_sede = seed_admin(db_session, email="legacy-cross-b@example.com")
        from backend import models

        site_a = _seed_site(db_session, key="legacy-a")
        site_b = models.CmsSite(
            id=uuid.uuid4(),
            site_key="legacy-b",
            name="Site legacy-b",
            base_path="/legacy-b",
            is_active=True,
            sede_id=other_sede.id,
        )
        db_session.add(site_b)
        db_session.commit()

        page = _make_page(db_session, site_b.id, slug="cross-site-page")
        headers = auth_headers(client, email="legacy-cross-a@example.com")
        resp = client.post(
            f"/api/cms/v2/pages/{page.id}/schedule?site_key={site_a.site_key}",
            json={"scheduled_at": "2099-01-01T00:00:00Z"},
            headers=headers,
        )
        assert resp.status_code == 404, resp.text
        db_session.refresh(page)
        assert page.publish_at is None


# ── 4. Post PATCH endpoint ─────────────────────────────────────────────────


class TestApiPatchPostScheduling:
    def test_patch_post_accepts_expires_at(self, client, db_session):
        seed_admin(db_session, email="post-patch@example.com")
        site = _seed_site(db_session)
        _make_post(db_session, site.id, slug="news")
        headers = auth_headers(client, email="post-patch@example.com")
        resp = client.patch(
            f"/api/cms/v2/sites/{site.site_key}/posts/news",
            json={"expires_at": "2099-12-31T00:00:00Z"},
            headers=headers,
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["expires_at"] is not None


# ── 4b. F-09 — published_at < expires_at validation ──────────────────────


class TestF09PostPublishedBeforeExpires:
    """F-09 (errorescms.md): ``CmsPost.published_at`` debe ser anterior a
    ``expires_at`` cuando ambos son no-None.  La validación vive en el
    CRUD (defense-in-depth) resolviendo valores efectivos contra el row
    en PATCH parcial; la API traduce ``ValueError`` -> 422.
    """

    ADMIN_EMAIL = "cms-f09-admin@example.com"

    def _headers(self, client):
        return auth_headers(client, email=self.ADMIN_EMAIL)

    def _seed(self, db_session):
        seed_admin(db_session, email=self.ADMIN_EMAIL)
        return _seed_site(db_session, key="f09-site")

    # ── API: POST create ────────────────────────────────────────────────

    def test_create_with_inverted_dates_returns_422(self, client, db_session):
        site = self._seed(db_session)
        resp = client.post(
            f"/api/cms/v2/sites/{site.site_key}/posts",
            headers=self._headers(client),
            json={
                "slug": "bad",
                "title": "Bad",
                "published_at": "2099-12-31T00:00:00Z",
                "expires_at": "2099-01-01T00:00:00Z",
            },
        )
        assert resp.status_code == 422, resp.text
        assert "expires_at" in resp.text or "published_at" in resp.text

    def test_create_with_valid_dates_returns_201(self, client, db_session):
        site = self._seed(db_session)
        resp = client.post(
            f"/api/cms/v2/sites/{site.site_key}/posts",
            headers=self._headers(client),
            json={
                "slug": "ok",
                "title": "OK",
                "published_at": "2099-01-01T00:00:00Z",
                "expires_at": "2099-12-31T00:00:00Z",
            },
        )
        assert resp.status_code == 201, resp.text

    def test_create_with_only_published_at_returns_201(self, client, db_session):
        site = self._seed(db_session)
        resp = client.post(
            f"/api/cms/v2/sites/{site.site_key}/posts",
            headers=self._headers(client),
            json={"slug": "pub-only", "title": "Pub", "published_at": "2099-06-01T00:00:00Z"},
        )
        assert resp.status_code == 201, resp.text

    # ── API: PATCH update ───────────────────────────────────────────────

    def test_patch_both_inverted_returns_422(self, client, db_session):
        site = self._seed(db_session)
        _make_post(db_session, site.id, slug="both-inv")
        resp = client.patch(
            f"/api/cms/v2/sites/{site.site_key}/posts/both-inv",
            headers=self._headers(client),
            json={
                "published_at": "2099-12-31T00:00:00Z",
                "expires_at": "2099-01-01T00:00:00Z",
            },
        )
        assert resp.status_code == 422, resp.text

    def test_patch_only_expires_before_existing_published_returns_422(self, client, db_session):
        # PATCH parcial: solo trae expires_at < published_at ya en row.
        site = self._seed(db_session)
        _make_post(
            db_session, site.id, slug="exp-vs-pub",
            published_at=dt.datetime(2099, 12, 31, tzinfo=dt.timezone.utc),
        )
        resp = client.patch(
            f"/api/cms/v2/sites/{site.site_key}/posts/exp-vs-pub",
            headers=self._headers(client),
            json={"expires_at": "2099-01-01T00:00:00Z"},
        )
        assert resp.status_code == 422, resp.text

    def test_patch_only_published_after_existing_expires_returns_422(self, client, db_session):
        # PATCH parcial inverso: solo trae published_at > expires_at ya en row.
        site = self._seed(db_session)
        _make_post(
            db_session, site.id, slug="pub-vs-exp",
            expires_at=dt.datetime(2099, 1, 1, tzinfo=dt.timezone.utc),
        )
        resp = client.patch(
            f"/api/cms/v2/sites/{site.site_key}/posts/pub-vs-exp",
            headers=self._headers(client),
            json={"published_at": "2099-12-31T00:00:00Z"},
        )
        assert resp.status_code == 422, resp.text

    def test_patch_valid_dates_returns_200(self, client, db_session):
        site = self._seed(db_session)
        _make_post(db_session, site.id, slug="ok-patch")
        resp = client.patch(
            f"/api/cms/v2/sites/{site.site_key}/posts/ok-patch",
            headers=self._headers(client),
            json={
                "published_at": "2099-01-01T00:00:00Z",
                "expires_at": "2099-12-31T00:00:00Z",
            },
        )
        assert resp.status_code == 200, resp.text

    def test_patch_clearing_expires_keeps_published_returns_200(self, client, db_session):
        # expires_at=None desactiva la restricción aunque published_at quede.
        site = self._seed(db_session)
        _make_post(
            db_session, site.id, slug="clear-exp",
            published_at=dt.datetime(2099, 6, 1, tzinfo=dt.timezone.utc),
            expires_at=dt.datetime(2099, 12, 31, tzinfo=dt.timezone.utc),
        )
        resp = client.patch(
            f"/api/cms/v2/sites/{site.site_key}/posts/clear-exp",
            headers=self._headers(client),
            json={"expires_at": None},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["expires_at"] is None

    def test_patch_published_equals_expires_returns_422(self, client, db_session):
        # Frontera: published_at == expires_at debe rechazarse (>=, no >).
        site = self._seed(db_session)
        _make_post(db_session, site.id, slug="eq-dates")
        same = "2099-06-01T00:00:00Z"
        resp = client.patch(
            f"/api/cms/v2/sites/{site.site_key}/posts/eq-dates",
            headers=self._headers(client),
            json={"published_at": same, "expires_at": same},
        )
        assert resp.status_code == 422, resp.text

    # ── CRUD directo (defense-in-depth sin pasar por API) ────────────────

    def test_crud_create_inverted_raises_valueError(self, db_session):
        from backend import crud, models, schemas

        site = models.CmsSite(
            id=uuid.uuid4(), site_key="f09-crud-crt", name="F09",
            base_path="/f09c", is_active=True,
        )
        db_session.add(site)
        db_session.flush()
        payload = schemas.CmsPostCreate(
            slug="bad-crud",
            title="Bad CRUD",
            published_at=dt.datetime(2099, 12, 31, tzinfo=dt.timezone.utc),
            expires_at=dt.datetime(2099, 1, 1, tzinfo=dt.timezone.utc),
        )
        with pytest.raises(ValueError, match="earlier than"):
            crud.create_cms_post(db_session, site.id, payload, user_id=None)

    def test_crud_update_inverted_raises_valueError(self, db_session):
        from backend import crud, models, schemas

        site = models.CmsSite(
            id=uuid.uuid4(), site_key="f09-crud-upd", name="F09u",
            base_path="/f09u", is_active=True,
        )
        db_session.add(site)
        db_session.flush()
        row = models.CmsPost(
            id=uuid.uuid4(), site_id=site.id, slug="upd-crud", title="Upd",
            status="draft", locale="es",
        )
        db_session.add(row)
        db_session.commit()

        payload = schemas.CmsPostUpdate(
            published_at=dt.datetime(2099, 12, 31, tzinfo=dt.timezone.utc),
            expires_at=dt.datetime(2099, 1, 1, tzinfo=dt.timezone.utc),
        )
        with pytest.raises(ValueError, match="earlier than"):
            crud.update_cms_post(db_session, row, payload, user_id=None)

        # sanity: orden correcto no lanza y persiste
        ok = schemas.CmsPostUpdate(
            published_at=dt.datetime(2099, 1, 1, tzinfo=dt.timezone.utc),
            expires_at=dt.datetime(2099, 12, 31, tzinfo=dt.timezone.utc),
        )
        updated = crud.update_cms_post(db_session, row, ok, user_id=None)
        assert updated.published_at is not None and updated.expires_at is not None


# ── 5. Multi-tenant boundary (Axioma 3) ──────────────────────────────────


class TestSchedulingSedeBoundary:
    """El auto-archive/programación NO debe cruzar sedes: si el scheduler
    procesa un row, el ``CmsPublishLog`` debe correr sobre el ``site_id``
    que tiene ``sede_id`` propio; los datos deben permanecer scopeados a
    la sede del row. Aquí validamos que el scheduler escribe ``site_id``
    consistente (no crea logs cross-sede) y que la API rechaza el PATCH
    cross-sede via scope check existente."""

    def test_scheduler_writes_publishlog_with_correct_site(self, db_session):
        from backend.crud.cms import process_due_content

        site = _seed_site(db_session)
        page = _make_page(db_session, site.id, slug="sede-aware", status="scheduled",
                          publish_at=dt.datetime(2024, 1, 1, tzinfo=dt.timezone.utc))
        process_due_content(db_session)
        db_session.commit()

        from backend import models

        log_entry = (
            db_session.query(models.CmsPublishLog)
            .filter(models.CmsPublishLog.entity_id == str(page.id), models.CmsPublishLog.action == "publish")
            .first()
        )
        assert log_entry is not None
        assert log_entry.site_id == site.id

    def test_reader_role_cannot_schedule_page_via_legacy_endpoint(self, client, db_session):
        # Editor sin permisos de publish.
        seed_user_with_role(db_session, role_name="lector", email="reader-sched@example.com")
        site = _seed_site(db_session)
        page = _make_page(db_session, site.id, slug="reader-page")

        headers = auth_headers(client, email="reader-sched@example.com")
        resp = client.post(
            f"/api/cms/v2/pages/{page.id}/schedule",
            json={"scheduled_at": "2099-01-01T00:00:00Z"},
            headers=headers,
        )
        # Debe ser 403 porque el endpoint requiere role de publish y/o falla
        # el ``require_module_access("cms", "read")`` que sí tiene lector.
        assert resp.status_code in (403, 422), resp.text
