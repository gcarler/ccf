"""Regression tests: pastoral-team mutations invalidate the public cache.

The ``public_pastoral_team`` endpoint is cached with ``@cached_public(ttl=300)``.
Any mutation that changes what it returns (PATCH pastoral profile, the
pastoral sync from the CMS ``pastors`` section, or the publish-time
``update_pastors_section_from_profiles``) MUST invalidate the cache after
commit — otherwise the public site serves stale pastor bios/photos for up
to 5 minutes.

These tests are bidirectional like ``TestPublic*CacheInvalidation`` in
``test_cms_v2_gap_coverage.py``: they would fail if the invalidation call
were removed (the cache entry survives the mutation).
"""

import uuid

import pytest

from backend.core.cache import get_redis as cache_get_redis
from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin


def _ok(status):
    return status in (200, 201, 204)


@pytest.fixture
def full(client, db_session):
    admin, _, _ = _seed_admin(db_session, email="cms_pastoral_cache@test.com")
    headers = _auth_headers(client, email="cms_pastoral_cache@test.com", password="testpass123")
    return {"c": client, "h": headers}


def _pastoral_cache_keys():
    redis = cache_get_redis()
    pattern = "cache:v2:public_pastoral_team:*"
    if hasattr(redis, "scan_iter"):
        return list(redis.scan_iter(pattern))
    return redis.scan_keys(pattern)


class TestPublicPastoralTeamCacheInvalidation:
    def test_pastoral_profile_patch_invalidates_public_cache(self, full, db_session):
        """PATCH /cms/pastoral-team/{id} must purge the public cache."""
        from backend.models_crm import Persona

        c, h = full["c"], full["h"]
        site_key = f"pst-{uuid.uuid4().hex[:6]}"
        resp = c.post(
            "/api/cms/v2/sites",
            json={"site_key": site_key, "name": f"Pastoral Site {site_key}", "base_path": f"/{site_key}"},
            headers=h,
        )
        assert _ok(resp.status_code), f"create_site: {resp.status_code} {resp.text}"

        # Prime the public cache.
        resp = c.get(f"/api/cms/v2/public/sites/{site_key}/pastoral-team")
        assert _ok(resp.status_code)
        assert _pastoral_cache_keys(), "expected a cached public_pastoral_team entry after priming"

        # Mutate a pastoral profile through the admin endpoint (the admin
        # user's own Persona is scoped to the actor, so no cross-sede 404).
        persona = db_session.query(Persona).filter(Persona.email == "cms_pastoral_cache@test.com").first()
        assert persona is not None
        resp = c.patch(
            f"/api/cms/v2/cms/pastoral-team/{persona.id}",
            json={"bio_short": "Bio actualizada", "is_pastoral_published": True},
            headers=h,
        )
        assert _ok(resp.status_code), f"patch_pastoral_profile: {resp.status_code} {resp.text}"

        assert _pastoral_cache_keys() == [], (
            "public_pastoral_team cache was not invalidated after PATCH pastoral profile"
        )

    def test_pastoral_publish_sync_invalidates_public_cache(self, full, db_session):
        """update_pastors_section_from_profiles must purge the public cache."""
        from backend import models
        from backend.crud import cms_pastors_sync

        c, h = full["c"], full["h"]

        # Ensure the canonical ccf site + pastors page + section exist.
        resp = c.post(
            "/api/cms/v2/sites",
            json={"site_key": cms_pastors_sync.SITE_KEY, "name": "CCF", "base_path": "/"},
            headers=h,
        )
        assert _ok(resp.status_code), f"create ccf site: {resp.status_code} {resp.text}"

        site = db_session.query(models.CmsSite).filter(models.CmsSite.site_key == cms_pastors_sync.SITE_KEY).first()
        assert site is not None
        page = db_session.query(models.CmsPage).filter(
            models.CmsPage.site_id == site.id,
            models.CmsPage.slug == cms_pastors_sync.PAGE_SLUG,
        ).first()
        if page is None:
            resp = c.post(
                f"/api/cms/v2/sites/{cms_pastors_sync.SITE_KEY}/pages",
                json={"slug": cms_pastors_sync.PAGE_SLUG, "title": "Pastores", "status": "draft"},
                headers=h,
            )
            assert _ok(resp.status_code), f"create pastors page: {resp.status_code} {resp.text}"
            page = db_session.query(models.CmsPage).filter(
                models.CmsPage.site_id == site.id,
                models.CmsPage.slug == cms_pastors_sync.PAGE_SLUG,
            ).first()
        section = db_session.query(models.CmsSection).filter(
            models.CmsSection.page_id == page.id,
            models.CmsSection.section_key == cms_pastors_sync.SECTION_KEY,
        ).first()
        if section is None:
            resp = c.post(
                f"/api/cms/v2/sites/{cms_pastors_sync.SITE_KEY}/pages/{cms_pastors_sync.PAGE_SLUG}/sections",
                json={
                    "section_key": cms_pastors_sync.SECTION_KEY,
                    "type": "team",
                    "props_json": {"pastors": [{"name": "Pastor Prueba", "role": "Pastor"}]},
                },
                headers=h,
            )
            assert _ok(resp.status_code), f"create pastors section: {resp.status_code} {resp.text}"

        # Prime the public cache.
        resp = c.get(f"/api/cms/v2/public/sites/{cms_pastors_sync.SITE_KEY}/pastoral-team")
        assert _ok(resp.status_code)
        assert _pastoral_cache_keys(), "expected a cached public_pastoral_team entry after priming"

        # The publish-time sync overwrites the section from profiles; the
        # underlying persona fields also feed the public endpoint.
        assert cms_pastors_sync.update_pastors_section_from_profiles(db_session) is True

        assert _pastoral_cache_keys() == [], (
            "public_pastoral_team cache was not invalidated after update_pastors_section_from_profiles"
        )

    def test_sync_pastoral_profiles_invalidates_public_cache(self, full, db_session):
        """sync_pastoral_profiles_from_cms_section must purge the public cache."""
        from backend import models
        from backend.crud import cms_pastors_sync

        c, h = full["c"], full["h"]

        resp = c.post(
            "/api/cms/v2/sites",
            json={"site_key": cms_pastors_sync.SITE_KEY, "name": "CCF", "base_path": "/"},
            headers=h,
        )
        assert _ok(resp.status_code)

        site = db_session.query(models.CmsSite).filter(models.CmsSite.site_key == cms_pastors_sync.SITE_KEY).first()
        page = db_session.query(models.CmsPage).filter(
            models.CmsPage.site_id == site.id,
            models.CmsPage.slug == cms_pastors_sync.PAGE_SLUG,
        ).first()
        if page is None:
            c.post(
                f"/api/cms/v2/sites/{cms_pastors_sync.SITE_KEY}/pages",
                json={"slug": cms_pastors_sync.PAGE_SLUG, "title": "Pastores", "status": "draft"},
                headers=h,
            )
            page = db_session.query(models.CmsPage).filter(
                models.CmsPage.site_id == site.id,
                models.CmsPage.slug == cms_pastors_sync.PAGE_SLUG,
            ).first()
        section = db_session.query(models.CmsSection).filter(
            models.CmsSection.page_id == page.id,
            models.CmsSection.section_key == cms_pastors_sync.SECTION_KEY,
        ).first()
        if section is None:
            c.post(
                f"/api/cms/v2/sites/{cms_pastors_sync.SITE_KEY}/pages/{cms_pastors_sync.PAGE_SLUG}/sections",
                json={
                    "section_key": cms_pastors_sync.SECTION_KEY,
                    "type": "team",
                    "props_json": {},
                },
                headers=h,
            )
            section = db_session.query(models.CmsSection).filter(
                models.CmsSection.page_id == page.id,
                models.CmsSection.section_key == cms_pastors_sync.SECTION_KEY,
            ).first()
        # The sync reads ``props_json["pastors"]`` directly — set it bypassing
        # the section-prop validator (which strips unknown keys).
        assert section is not None
        section.props_json = {"pastors": [{"name": "Pastor Sync", "role": "Pastor"}]}
        db_session.commit()

        resp = c.get(f"/api/cms/v2/public/sites/{cms_pastors_sync.SITE_KEY}/pastoral-team")
        assert _ok(resp.status_code)
        assert _pastoral_cache_keys(), "expected a cached public_pastoral_team entry after priming"

        result = cms_pastors_sync.sync_pastoral_profiles_from_cms_section(db_session)
        assert result["total"] >= 1

        assert _pastoral_cache_keys() == [], (
            "public_pastoral_team cache was not invalidated after sync_pastoral_profiles_from_cms_section"
        )
