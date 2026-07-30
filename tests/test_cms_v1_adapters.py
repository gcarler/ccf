"""Unit tests for the v1→v2 CMS testimonial adapters."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

from backend import schemas
from backend.api.cms_v1_adapters import (
    _is_approved_from_status,
    _post_status_from_testimonial,
    _testimonial_status_from_post,
    post_to_testimonial_read,
)
from backend.api.cms_v1_adapters import (
    testimonial_create_to_post_create as create_to_post,
)
from backend.api.cms_v1_adapters import (
    testimonial_update_to_post_update as update_to_post,
)


class TestStatusMapping:
    def test_is_approved_from_published(self):
        assert _is_approved_from_status("published") is True
        assert _is_approved_from_status("draft") is False
        assert _is_approved_from_status("archived") is False

    def test_testimonial_status_from_post(self):
        assert _testimonial_status_from_post("published") == "approved"
        assert _testimonial_status_from_post("archived") == "archived"
        assert _testimonial_status_from_post("draft") == "pending"
        assert _testimonial_status_from_post("in_review") == "pending"

    def test_post_status_from_testimonial(self):
        assert _post_status_from_testimonial(is_approved=True, status="approved") == "published"
        assert _post_status_from_testimonial(is_approved=False, status="pending") == "draft"
        assert _post_status_from_testimonial(is_approved=True, status="archived") == "archived"
        assert _post_status_from_testimonial(is_approved=False, status="archived") == "archived"


class TestPostToTestimonialRead:
    def test_maps_published_post_to_approved_testimonial(self):
        site = MagicMock()
        site.sede_id = uuid.uuid4()
        post = MagicMock()
        post.id = uuid.uuid4()
        post.content = "Great experience"
        post.status = "published"
        post.featured_image_url = "https://example.com/img.png"
        post.seo_json = {
            "emotion": "Alegría",
            "media_type": "image",
            "media_url": "https://example.com/media.mp4",
            "video_url": "https://example.com/video.mp4",
            "podcast_url": "https://example.com/podcast.mp3",
            "show_on_home": True,
        }
        post.author_persona_id = uuid.uuid4()
        post.site = site
        post.created_at = "2026-07-29T00:00:00+00:00"

        read = post_to_testimonial_read(post)

        assert read.content == "Great experience"
        assert read.is_approved is True
        assert read.status == "approved"
        assert read.emotion == "Alegría"
        assert read.media_type == "image"
        assert read.image_url == "https://example.com/img.png"
        assert read.show_on_home is True
        assert read.sede_id == site.sede_id

    def test_default_emotion_and_media_type(self):
        post = MagicMock()
        post.id = uuid.uuid4()
        post.content = "x"
        post.status = "draft"
        post.featured_image_url = None
        post.seo_json = {}
        post.author_persona_id = None
        post.site = None
        post.created_at = "2026-07-29T00:00:00+00:00"

        read = post_to_testimonial_read(post)
        assert read.emotion == "Gratitud"
        assert read.media_type == "text"
        assert read.sede_id is None


class TestTestimonialCreateToPostCreate:
    def test_creates_published_post_when_approved(self):
        payload = schemas.TestimonialCreate(
            content="Approved testimony",
            emotion="Fe",
            media_type="text",
            is_approved=True,
            show_on_home=True,
            image_url="https://example.com/hero.png",
        )
        site_id = uuid.uuid4()

        post_create = create_to_post(payload, site_id, uuid.uuid4())

        assert post_create.status == "published"
        assert post_create.content == "Approved testimony"
        assert post_create.featured_image_url == "https://example.com/hero.png"
        assert post_create.seo_json["emotion"] == "Fe"
        assert post_create.seo_json["show_on_home"] is True
        assert post_create.slug.startswith("testimonial-")

    def test_creates_draft_post_when_not_approved(self):
        payload = schemas.TestimonialCreate(
            content="Pending testimony",
            is_approved=False,
        )
        site_id = uuid.uuid4()

        post_create = create_to_post(payload, site_id, None)

        assert post_create.status == "draft"


class TestTestimonialUpdateToPostUpdate:
    def test_preserves_status_when_no_status_fields_provided(self):
        payload = schemas.TestimonialUpdate(content="Updated content")
        update = update_to_post(payload, "published", {"emotion": "Fe"})

        assert update.content == "Updated content"
        assert update.status is None
        assert update.seo_json["emotion"] == "Fe"

    def test_changes_status_with_is_approved(self):
        payload = schemas.TestimonialUpdate(is_approved=True)
        update = update_to_post(payload, "draft", {})
        assert update.status == "published"

    def test_changes_status_with_legacy_status(self):
        payload = schemas.TestimonialUpdate(status="archived")
        update = update_to_post(payload, "published", {})
        assert update.status == "archived"

    def test_merges_seo_json(self):
        payload = schemas.TestimonialUpdate(
            emotion="Alegría",
            media_url="https://x.com/a.mp4",
            show_on_home=True,
        )
        update = update_to_post(payload, "draft", {"media_type": "video"})
        assert update.seo_json["emotion"] == "Alegría"
        assert update.seo_json["media_type"] == "video"
        assert update.seo_json["media_url"] == "https://x.com/a.mp4"
        assert update.seo_json["show_on_home"] is True
