"""Edge coverage for CMS scheduling branches not exercised by the main flow tests."""

from __future__ import annotations

import datetime as dt
import uuid
from types import SimpleNamespace

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Query

from backend import models
from backend.crud.cms import scheduling
from tests.test_cms_crud_batch_coverage import _site

UTC = dt.timezone.utc


def test_due_queries_apply_for_update_for_postgres_bind(db_session, monkeypatch):
    site = _site(db_session, "schedule-edge-lock")
    past = dt.datetime(2024, 1, 1, tzinfo=UTC)
    db_session.add_all(
        [
            models.CmsPage(
                site_id=site.id,
                slug="scheduled-lock",
                title="Scheduled",
                status="scheduled",
                publish_at=past,
            ),
            models.CmsPage(
                site_id=site.id,
                slug="expired-lock",
                title="Expired",
                status="published",
                expires_at=past,
            ),
            models.CmsPost(
                site_id=site.id,
                slug="expired-post-lock",
                title="Expired post",
                status="published",
                expires_at=past,
            ),
        ]
    )
    db_session.commit()
    real_get_bind = db_session.get_bind
    real_with_for_update = Query.with_for_update
    lock_calls: list[dict] = []

    def capture_lock(query, *args, **kwargs):
        lock_calls.append(kwargs)
        return real_with_for_update(query, *args, **kwargs)

    monkeypatch.setattr(Query, "with_for_update", capture_lock)

    def run_with_postgres_bind(query_fn):
        first_call = True

        def postgres_once(*args, **kwargs):
            nonlocal first_call
            if first_call:
                first_call = False
                return SimpleNamespace(dialect=SimpleNamespace(name="postgresql"))
            return real_get_bind(*args, **kwargs)

        monkeypatch.setattr(db_session, "get_bind", postgres_once)
        result = query_fn(db_session)
        monkeypatch.setattr(db_session, "get_bind", real_get_bind)
        return result

    assert [row.slug for row in run_with_postgres_bind(scheduling.find_pages_due_for_publish)] == ["scheduled-lock"]
    assert [row.slug for row in run_with_postgres_bind(scheduling.find_pages_due_for_archive)] == ["expired-lock"]
    assert [row.slug for row in run_with_postgres_bind(scheduling.find_posts_due_for_archive)] == ["expired-post-lock"]
    assert lock_calls == [{"skip_locked": True}] * 3


def test_process_due_content_dry_run_counts_expired_pages_and_posts(db_session):
    site = _site(db_session, "schedule-edge-dry")
    db_session.add_all(
        [
            models.CmsPage(
                site_id=site.id,
                slug="expired-page",
                title="Expired page",
                status="published",
                expires_at=dt.datetime(2024, 1, 1, tzinfo=UTC),
            ),
            models.CmsPost(
                site_id=site.id,
                slug="expired-post",
                title="Expired post",
                status="published",
                expires_at=dt.datetime(2024, 1, 1, tzinfo=UTC),
            ),
        ]
    )
    db_session.commit()

    result = scheduling.process_due_content(db_session, dry_run=True)

    assert result == {"pages_published": 0, "pages_archived": 1, "posts_archived": 1}
    assert db_session.query(models.CmsPage).filter_by(slug="expired-page").one().status == "published"
    assert db_session.query(models.CmsPost).filter_by(slug="expired-post").one().status == "published"


def test_archive_post_dry_run_is_non_mutating(db_session):
    site = _site(db_session, "schedule-edge-post")
    post = models.CmsPost(
        id=uuid.uuid4(),
        site_id=site.id,
        slug="dry-post",
        title="Dry post",
        status="published",
        expires_at=dt.datetime(2024, 1, 1, tzinfo=UTC),
    )
    db_session.add(post)
    db_session.commit()

    assert scheduling._archive_post_with_audit(db_session, post, dry_run=True) is True

    db_session.refresh(post)
    assert post.status == "published"
    assert db_session.query(models.CmsPublishLog).filter_by(entity_id=str(post.id)).count() == 0


def test_capture_daily_seo_snapshots_counts_unique_conflict_as_skip(db_session, monkeypatch):
    site = _site(db_session, "schedule-edge-integrity")
    db_session.commit()

    def raise_integrity_error(*args, **kwargs):
        raise IntegrityError("duplicate", {}, Exception("duplicate"))

    monkeypatch.setattr(db_session, "flush", raise_integrity_error)

    result = scheduling.capture_daily_seo_snapshots(
        db_session,
        today=dt.date.today(),
    )

    assert result["snapshots_count"] == 0
    assert result["skipped_count"] == 1
    assert result["sites_captured"] == 0
    db_session.rollback()
    assert site.id is not None
