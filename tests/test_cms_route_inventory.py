"""Runtime inventory contract for the separated CMS v1/v2 routers."""

from __future__ import annotations

from collections import Counter

from backend.app import app


def _mounted_methods_and_paths() -> list[tuple[str, str]]:
    return [
        (method, route.path)
        for route in app.routes
        if getattr(route, "path", "").startswith("/api/cms")
        for method in (getattr(route, "methods", set()) or set())
    ]


def test_cms_route_inventory_has_no_duplicate_method_path_pairs():
    mounted = Counter(_mounted_methods_and_paths())
    duplicates = {pair: count for pair, count in mounted.items() if count > 1}
    assert not duplicates, f"CMS duplicate method/path routes mounted: {duplicates}"


def test_cms_v1_mount_contains_only_media_and_metrics_surface():
    mounted = set(_mounted_methods_and_paths())

    assert ("GET", "/api/cms/media") in mounted
    assert ("POST", "/api/cms/media") in mounted
    assert ("POST", "/api/cms/media/cleanup") in mounted
    assert ("GET", "/api/cms/metrics") in mounted

    legacy_prefixes = (
        "/api/cms/testimonials",
        "/api/cms/announcements",
        "/api/admin/testimonials",
        "/api/admin/announcements",
    )
    assert not any(path.startswith(legacy) for _, path in mounted for legacy in legacy_prefixes)


def test_cms_v2_mount_remains_separate_from_v1_media_routes():
    mounted = set(_mounted_methods_and_paths())

    assert ("POST", "/api/cms/v2/images/optimize") in mounted
    assert ("GET", "/api/cms/v2/section-types") in mounted
    assert not any(path == "/api/cms/v2/media" for _, path in mounted)
