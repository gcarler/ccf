"""Direct CRUD coverage for CMS newsletter, A/B and scheduling helpers."""

from __future__ import annotations

import datetime as dt
import uuid

from backend import models, schemas
from backend.crud.cms import (
    apply_cms_ab_test_winner,
    create_cms_ab_test,
    create_cms_newsletter,
    create_cms_subscriber,
    find_pages_due_for_archive,
    find_pages_due_for_publish,
    find_posts_due_for_archive,
    get_cms_ab_test,
    get_cms_ab_test_by_id,
    get_cms_ab_test_results,
    get_cms_newsletter,
    get_cms_subscriber,
    get_seo_trend,
    import_cms_subscribers,
    list_cms_ab_tests,
    list_cms_newsletters,
    list_cms_subscribers,
    list_seo_snapshots,
    public_subscribe,
    public_unsubscribe,
    record_cms_ab_test_event,
    send_cms_newsletter,
    update_cms_ab_test,
    update_cms_newsletter,
    update_cms_subscriber,
)

UTC = dt.timezone.utc


def _site(db, key: str = "crud-batch") -> models.CmsSite:
    site = models.CmsSite(
        id=uuid.uuid4(),
        site_key=key,
        name=key,
        base_path=f"/{key}",
        is_active=True,
    )
    db.add(site)
    db.commit()
    db.refresh(site)
    return site


def _page_with_sections(db, site: models.CmsSite):
    page = models.CmsPage(
        id=uuid.uuid4(), site_id=site.id, slug="ab-page", title="AB page", status="published"
    )
    section_a = models.CmsSection(
        id=uuid.uuid4(), page_id=page.id, section_key="a", type="hero", props_json={}, is_visible=True
    )
    section_b = models.CmsSection(
        id=uuid.uuid4(), page_id=page.id, section_key="b", type="hero", props_json={}, is_visible=False
    )
    db.add_all([page, section_a, section_b])
    db.commit()
    return page, section_a, section_b


class TestNewsletterCrudDirect:
    def test_newsletter_lifecycle_and_send_dispatch(self, db_session, monkeypatch):
        site = _site(db_session, "newsletter-direct")
        newsletter = create_cms_newsletter(
            db_session,
            site.id,
            schemas.CmsNewsletterCreate(
                name="N1", subject="S1", content_html="<p>body</p>"
            ),
        )
        fetched = get_cms_newsletter(db_session, site.id, newsletter.id)
        assert fetched is not None and fetched.id == newsletter.id
        assert [item.id for item in list_cms_newsletters(db_session, site.id)] == [newsletter.id]

        updated = update_cms_newsletter(
            db_session,
            newsletter,
            schemas.CmsNewsletterUpdate(name="N2", status="scheduled"),
        )
        assert updated.name == "N2"
        assert updated.status == "scheduled"

        first = create_cms_subscriber(
            db_session,
            site.id,
            schemas.CmsSubscriberCreate(email=" USER@EXAMPLE.COM ", name="User"),
        )
        inactive = create_cms_subscriber(
            db_session,
            site.id,
            schemas.CmsSubscriberCreate(email="inactive@example.com", is_active=False),
        )
        calls: list[str] = []
        monkeypatch.setattr(
            "backend.services.email.send_email",
            lambda **kwargs: calls.append(kwargs["to"]),
        )
        sent = send_cms_newsletter(db_session, newsletter)
        assert sent.status == "sent"
        assert sent.recipient_count == 1
        assert calls == ["user@example.com"]
        assert inactive.is_active is False

    def test_subscriber_search_pagination_import_and_public_flows(self, db_session):
        site = _site(db_session, "subscriber-direct")
        existing = create_cms_subscriber(
            db_session,
            site.id,
            schemas.CmsSubscriberCreate(email="existing@example.com", is_active=False),
        )
        reactivated = create_cms_subscriber(
            db_session,
            site.id,
            schemas.CmsSubscriberCreate(
                email="EXISTING@example.com", name="Reactivated", is_active=True
            ),
        )
        assert reactivated.id == existing.id
        assert reactivated.is_active is True

        created = public_subscribe(db_session, site.id, "new@example.com", "New")
        assert created.is_active is True
        public_subscribe(db_session, site.id, "NEW@example.com", "Renamed")

        imported = import_cms_subscribers(
            db_session,
            site.id,
            schemas.CmsSubscriberImportPayload(
                emails=["emails@example.com", "second@example.com", "  "]
            ),
        )
        assert imported["imported_count"] == 2
        csv_import = import_cms_subscribers(
            db_session,
            site.id,
            schemas.CmsSubscriberImportPayload(
                csv_content="csv@example.com, CSV Name\nnot-an-email\n"
            ),
        )
        assert csv_import["imported_count"] == 1
        item_import = import_cms_subscribers(
            db_session,
            site.id,
            schemas.CmsSubscriberImportPayload(
                subscribers=[schemas.CmsSubscriberImportItem(email="item@example.com", name="Item")]
            ),
        )
        assert item_import["imported_count"] == 1

        items, total = list_cms_subscribers(
            db_session, site.id, page=1, page_size=2, search="example.com", is_active=True
        )
        assert len(items) == 2
        assert total >= 2
        assert get_cms_subscriber(db_session, site.id, created.id) is not None

        updated = update_cms_subscriber(
            db_session, created, schemas.CmsSubscriberUpdate(is_active=False)
        )
        assert updated.unsubscribed_at is not None
        updated = update_cms_subscriber(
            db_session, updated, schemas.CmsSubscriberUpdate(is_active=True)
        )
        assert updated.unsubscribed_at is None

        public_unsubscribe(db_session, "new@example.com", site.id)
        db_session.refresh(updated)
        assert updated.is_active is False
        public_unsubscribe(db_session, "item@example.com")


class TestAbTestCrudDirect:
    def test_lifecycle_results_and_winner_variants(self, db_session):
        site = _site(db_session, "ab-direct")
        page, section_a, section_b = _page_with_sections(db_session, site)
        ab = create_cms_ab_test(
            db_session,
            site.id,
            schemas.CmsAbTestCreate(
                name="AB", page_id=page.id, section_a_id=section_a.id, section_b_id=section_b.id
            ),
        )
        assert get_cms_ab_test(db_session, site.id, ab.id) is not None
        assert get_cms_ab_test_by_id(db_session, ab.id) is not None
        assert len(list_cms_ab_tests(db_session, site.id, page_id=page.id, status="active")) == 1

        update_cms_ab_test(
            db_session, ab, schemas.CmsAbTestUpdate(name="AB updated", status="completed")
        )
        assert ab.ended_at is not None

        # Empty test covers zero denominators and non-significant result.
        empty = get_cms_ab_test_results(db_session, ab.id)
        assert empty.views_a == 0
        assert empty.is_significant is False

        for variant, event_type, count in (
            ("a", "view", 100),
            ("a", "conversion", 1),
            ("a", "click", 10),
            ("b", "view", 100),
            ("b", "conversion", 50),
            ("b", "click", 2),
        ):
            for idx in range(count):
                record_cms_ab_test_event(
                    db_session,
                    ab.id,
                    schemas.CmsAbTestEventCreate(
                        variant=variant, event_type=event_type, visitor_id=f"{variant}-{event_type}-{idx}"
                    ),
                )
        result = get_cms_ab_test_results(db_session, ab.id)
        assert result.views_a == 100
        assert result.views_b == 100
        assert result.conversions_a == 1
        assert result.conversions_b == 50
        assert result.conversion_rate_b > result.conversion_rate_a

        # Explicit A winner, then a separate test using the default winner path.
        applied = apply_cms_ab_test_winner(
            db_session, site.id, ab.id, schemas.CmsAbTestApplyWinner(winner_variant="a")
        )
        assert applied.winner_section_id == section_a.id
        db_session.refresh(section_a)
        db_session.refresh(section_b)
        assert section_a.is_visible is True
        assert section_b.is_visible is False

        other = create_cms_ab_test(
            db_session,
            site.id,
            schemas.CmsAbTestCreate(
                name="AB 2", page_id=page.id, section_a_id=section_a.id, section_b_id=section_b.id
            ),
        )
        applied_default = apply_cms_ab_test_winner(db_session, site.id, other.id)
        assert applied_default.status == "completed"

    def test_ab_filters_deleted_and_missing_winner(self, db_session):
        site = _site(db_session, "ab-edge")
        page, section_a, section_b = _page_with_sections(db_session, site)
        ab = create_cms_ab_test(
            db_session,
            site.id,
            schemas.CmsAbTestCreate(
                name="AB", page_id=page.id, section_a_id=section_a.id, section_b_id=section_b.id
            ),
        )
        ab.status = "paused"
        db_session.commit()
        assert list_cms_ab_tests(db_session, site.id, status="active") == []
        assert len(list_cms_ab_tests(db_session, site.id, status="paused")) == 1
        from backend.crud.cms import delete_cms_ab_test

        assert delete_cms_ab_test(db_session, ab) is True
        assert get_cms_ab_test(db_session, site.id, ab.id) is None


class TestSchedulingCrudDirect:
    def test_due_queries_and_seo_history(self, db_session):
        site = _site(db_session, "schedule-direct")
        past = dt.datetime(2024, 1, 1, tzinfo=UTC)
        future = dt.datetime(2099, 1, 1, tzinfo=UTC)
        page_due = models.CmsPage(
            site_id=site.id, slug="scheduled", title="Scheduled", status="scheduled", publish_at=past
        )
        page_expired = models.CmsPage(
            site_id=site.id, slug="expired", title="Expired", status="published", expires_at=past
        )
        post_expired = models.CmsPost(
            site_id=site.id, slug="expired-post", title="Expired", status="published", expires_at=past
        )
        page_future = models.CmsPage(
            site_id=site.id, slug="future", title="Future", status="scheduled", publish_at=future
        )
        db_session.add_all([page_due, page_expired, post_expired, page_future])
        db_session.commit()

        assert [row.slug for row in find_pages_due_for_publish(db_session, with_for_update=False)] == ["scheduled"]
        assert [row.slug for row in find_pages_due_for_archive(db_session, with_for_update=False)] == ["expired"]
        assert [row.slug for row in find_posts_due_for_archive(db_session, with_for_update=False)] == ["expired-post"]

        snapshot = models.CmsSeoSnapshot(
            site_id=site.id,
            captured_date=dt.date.today(),
            captured_at=dt.datetime.now(UTC),
            average_score=82,
            total_pages=4,
            pages_with_errors=1,
            critical_issues=0,
            by_severity_json={"warning": 1},
        )
        db_session.add(snapshot)
        db_session.commit()
        rows, total = list_seo_snapshots(db_session, site_id=site.id, limit=10)
        assert total == 1
        assert rows[0].average_score == 82
        trend = get_seo_trend(db_session, site_id=site.id, days=1)
        assert trend["series"][0]["average_score"] == 82
        assert get_seo_trend(db_session, site_id=site.id, days=1, sede_id=uuid.uuid4())["series"] == []

    def test_process_due_content_dry_run_and_noop(self, db_session):
        from backend.crud.cms import process_due_content

        site = _site(db_session, "schedule-dry")
        page = models.CmsPage(
            site_id=site.id,
            slug="dry",
            title="Dry",
            status="scheduled",
            publish_at=dt.datetime(2024, 1, 1, tzinfo=UTC),
        )
        db_session.add(page)
        db_session.commit()
        result = process_due_content(db_session, dry_run=True)
        assert result == {"pages_published": 1, "pages_archived": 0, "posts_archived": 0}
        db_session.refresh(page)
        assert page.status == "scheduled"
        assert process_due_content(db_session, dry_run=False)["pages_published"] == 1
        assert process_due_content(db_session, dry_run=False)["pages_published"] == 0
