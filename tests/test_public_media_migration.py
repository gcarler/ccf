from scripts.migrate_public_images_to_cms import (
    is_content_image,
    replace_image_urls,
    source_tag,
    source_url,
)


def test_system_assets_are_not_editorial_content_images():
    assert not is_content_image("favicon.ico")
    assert not is_content_image("og-default.png")
    assert not is_content_image("icons/icon-192x192.png")
    assert is_content_image("images/convenccion/IMG_6813.webp")


def test_source_url_and_tag_are_stable_for_idempotent_migration():
    assert source_url("images/convenccion/IMG_6813.webp") == "/images/convenccion/IMG_6813.webp"
    assert source_tag("images/convenccion/IMG_6813.webp") == (
        "public-source:images/convenccion/IMG_6813.webp"
    )


def test_replace_image_urls_walks_nested_sections_and_serialized_json():
    old = "/images/convenccion/IMG_6813.webp"
    new = "/api/static/cms/public-site/hero.webp"
    payload = {
        "bg_image": old,
        "items": [{"url": old, "alt": "Comunidad"}],
        "content": '{"image_url": "/images/convenccion/IMG_6813.webp"}',
    }

    updated, count = replace_image_urls(payload, {old: new})

    assert count == 3
    assert updated["bg_image"] == new
    assert updated["items"][0]["url"] == new
    # JSON stored as a string is intentionally treated as an opaque string;
    # the URL still gets replaced without changing the surrounding format.
    assert new in updated["content"]
