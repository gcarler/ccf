"""Regression tests for public-cache key invalidation helpers."""

from __future__ import annotations

from backend.core import cache_v2
from backend.core.cache import MemoryRedis


class _FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.deleted: list[str] = []

    def get(self, key: str):
        return self.values.get(key)

    def delete(self, key: str) -> None:
        self.deleted.append(key)
        self.values.pop(key, None)


class _ScanRedis(_FakeRedis):
    def scan_iter(self, pattern: str):
        prefix = pattern.removesuffix("*")
        return (key for key in list(self.values) if key.startswith(prefix))


def test_build_cache_key_ignores_non_serializable_dependency() -> None:
    class SessionStub:
        pass

    without_dependency = cache_v2._build_cache_key(
        "public_page", ("ccf", "home"), {"skip": 0}
    )
    with_dependency = cache_v2._build_cache_key(
        "public_page", ("ccf", "home"), {"skip": 0, "db": SessionStub()}
    )

    assert with_dependency == without_dependency


def test_exact_public_cache_invalidation_rebuilds_the_same_key(monkeypatch) -> None:
    redis = _FakeRedis()
    monkeypatch.setattr(cache_v2, "get_redis", lambda: redis)
    key = cache_v2._build_cache_key("public_menu", (), {"site_key": "ccf", "menu_key": "main"})
    redis.values[key] = '{"items": []}'

    cache_v2.invalidate_cached_public(
        "public_menu", site_key="ccf", menu_key="main"
    )

    assert redis.deleted == [key]
    assert key not in redis.values


def test_pattern_public_cache_invalidation_uses_scan_iter(monkeypatch) -> None:
    redis = _ScanRedis()
    monkeypatch.setattr(cache_v2, "get_redis", lambda: redis)
    matching = [
        cache_v2._build_cache_key("public_posts_list", (), {"site_key": "ccf", "skip": skip})
        for skip in (0, 50)
    ]
    unrelated = cache_v2._build_cache_key("public_page", (), {"site_key": "ccf", "slug": "home"})
    for key in [*matching, unrelated]:
        redis.values[key] = "{}"

    cache_v2.invalidate_cached_public_pattern("public_posts_list")

    assert set(redis.deleted) == set(matching)
    assert unrelated not in redis.deleted
    assert unrelated in redis.values


def test_pattern_public_cache_invalidation_uses_memory_fallback(monkeypatch) -> None:
    redis = MemoryRedis()
    monkeypatch.setattr(cache_v2, "get_redis", lambda: redis)
    matching = cache_v2._build_cache_key("public_pages_list", (), {"site_key": "ccf"})
    unrelated = cache_v2._build_cache_key("public_post", (), {"site_key": "ccf", "slug": "home"})
    redis.setex(matching, 60, "pages")
    redis.setex(unrelated, 60, "post")

    cache_v2.invalidate_cached_public_pattern("public_pages_list")

    assert redis.get(matching) is None
    assert redis.get(unrelated) == "post"


def test_memory_redis_scan_keys_supports_exact_and_wildcard_patterns() -> None:
    redis = MemoryRedis()
    redis.setex("cache:v2:public_page:1", 60, "page")
    redis.setex("cache:v2:public_page:2", 60, "page")
    redis.setex("cache:v2:public_post:1", 60, "post")

    assert redis.scan_keys("cache:v2:public_page:1") == ["cache:v2:public_page:1"]
    assert set(redis.scan_keys("cache:v2:public_page:*")) == {
        "cache:v2:public_page:1",
        "cache:v2:public_page:2",
    }


def test_nested_non_serializable_values_are_dropped_without_losing_valid_params() -> None:
    class SessionStub:
        pass

    mixed = cache_v2._build_cache_key(
        "fn", ("site",), {"params": {"db": SessionStub(), "limit": 10}}
    )
    valid_only = cache_v2._build_cache_key("fn", ("site",), {"params": {"limit": 10}})
    assert mixed == valid_only
    assert cache_v2._build_cache_key("fn", ("site",), {"params": [SessionStub(), 10]}) == cache_v2._build_cache_key(
        "fn", ("site",), {"params": [10]}
    )
    assert cache_v2._build_cache_key("fn", ("site",), {"params": [SessionStub(), 11]}) != cache_v2._build_cache_key(
        "fn", ("site",), {"params": [10]}
    )


def test_public_cache_invalidation_is_best_effort_on_redis_errors(monkeypatch) -> None:
    class BrokenRedis:
        def delete(self, key: str) -> None:
            raise ConnectionError("redis unavailable")

        def scan_keys(self, pattern: str):
            raise ConnectionError("redis unavailable")

    monkeypatch.setattr(cache_v2, "get_redis", lambda: BrokenRedis())

    cache_v2.invalidate_cached_public("public_page", site_key="ccf", slug="home")
    cache_v2.invalidate_cached_public_pattern("public_pages_list")
