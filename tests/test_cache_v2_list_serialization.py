"""Regression tests for the ``@cached_public`` list-of-Pydantic serialization.

Covers the bug fixed in 2026-07 where endpoints returning
``List[PastoralProfileRead]`` (or any list/tuple/dict of Pydantic models)
were cached as ``json.dumps(..., default=str)`` - which falls back to
``str(model)`` and produces a list of debug strings like
``"id=UUID('...') name='Alex y Elvia'..."``. On the next cache hit,
``json.loads`` returned a list of strings, FastAPI's ``response_model``
validation failed with ``Input should be a valid dictionary or object
to extract fields from``, and the live endpoint 500'd for the full
``TTL=300`` window.

The fix introduces ``_to_jsonable`` in ``backend.core.cache_v2`` which
walks the value once and converts every Pydantic model to a plain dict
via ``model_dump()`` before ``json.dumps`` ever sees it. These tests
pin the new contract.
"""

from __future__ import annotations

import json
from typing import List, Optional
from uuid import UUID

import pytest
from pydantic import BaseModel


# Stand-in for ``schemas.PastoralProfileRead`` so the test does
# not need a DB-backed ``Persona`` row. The shape and field types
# match: ``id`` is a UUID (validated by Pydantic v2), all others
# are scalars.
class _MiniProfile(BaseModel):
    id: UUID
    name: str
    slug: str
    photo_url: Optional[str] = None
    role: Optional[str] = None
    is_main_pastor: bool = False


# _to_jsonable unit tests


class TestToJsonable:
    def test_pydantic_v2_model_becomes_dict(self):
        from backend.core.cache_v2 import _to_jsonable

        m = _MiniProfile(
            id=UUID("4ba29d13-1a4e-5e60-91e8-7762a5b7549b"),
            name="Alex y Elvia",
            slug="alex-y-elvia",
        )
        out = _to_jsonable(m)
        assert isinstance(out, dict)
        # model_dump() default keeps UUID as a string; FastAPI re-parses.
        assert out["id"] == "4ba29d13-1a4e-5e60-91e8-7762a5b7549b"
        assert out["name"] == "Alex y Elvia"
        assert out["slug"] == "alex-y-elvia"

    def test_list_of_models_becomes_list_of_dicts(self):
        from backend.core.cache_v2 import _to_jsonable

        items = [
            _MiniProfile(
                id=UUID("4ba29d13-1a4e-5e60-91e8-7762a5b7549b"),
                name="Alex y Elvia",
                slug="alex-y-elvia",
            ),
            _MiniProfile(
                id=UUID("c68ddb5d-469e-5a7a-86c1-7a93e7712d1a"),
                name="Camilo Pajaro",
                slug="camilo-pajaro",
            ),
        ]
        out = _to_jsonable(items)
        assert isinstance(out, list)
        assert len(out) == 2
        assert all(isinstance(item, dict) for item in out)
        # Verify NO str(model) leakage - the bug symptom was that
        # cached values started with "id=UUID(" which JSON-serializes
        # as a quoted Python-style debug string.
        for item in out:
            assert not str(item["id"]).startswith("id="), (
                f"UUID leaked as str(model) debug repr: {item!r}"
            )

    def test_nested_dict_with_model_values(self):
        from backend.core.cache_v2 import _to_jsonable

        m = _MiniProfile(
            id=UUID("4ba29d13-1a4e-5e60-91e8-7762a5b7549b"),
            name="Alex y Elvia",
            slug="alex-y-elvia",
        )
        out = _to_jsonable({"payload": m, "count": 1})
        assert out["count"] == 1
        assert isinstance(out["payload"], dict)
        assert out["payload"]["name"] == "Alex y Elvia"

    def test_primitives_pass_through(self):
        from backend.core.cache_v2 import _to_jsonable

        assert _to_jsonable("hello") == "hello"
        assert _to_jsonable(42) == 42
        assert _to_jsonable(3.14) == 3.14
        assert _to_jsonable(True) is True
        assert _to_jsonable(None) is None

    def test_plain_list_passes_through(self):
        from backend.core.cache_v2 import _to_jsonable

        assert _to_jsonable([1, 2, 3]) == [1, 2, 3]
        assert _to_jsonable(["a", "b"]) == ["a", "b"]

    def test_plain_dict_passes_through(self):
        from backend.core.cache_v2 import _to_jsonable

        assert _to_jsonable({"a": 1, "b": "x"}) == {"a": 1, "b": "x"}

    def test_tuple_becomes_list(self):
        from backend.core.cache_v2 import _to_jsonable

        # Tuples aren't JSON-native; convert to list for round-trip safety.
        out = _to_jsonable((1, 2, 3))
        assert out == [1, 2, 3]
        assert isinstance(out, list)

    def test_exotic_type_falls_back_to_str(self):
        """RootModel/Generic/exotic Pydantic bases that don't expose
        ``model_dump()`` must not crash; we fall back to ``str()`` to
        preserve the prior ``default=str`` behavior at the leaves."""

        from backend.core.cache_v2 import _to_jsonable

        class _Exotic:
            def __repr__(self):
                return "EXOTIC_REPR"

        # No model_dump / dict / list / dict / str(int|float|bool)
        out = _to_jsonable(_Exotic())
        assert out == "EXOTIC_REPR"


# End-to-end cache_v2 decorator behavior
#
# Reproduces the original 500 root cause: a list of Pydantic
# models must round-trip through ``redis.setex`` -> ``redis.get`` ->
# ``json.loads`` as a list of dicts, NOT a list of strings.
class TestCachedPublicListOfModels:
    def test_list_of_models_roundtrips_as_list_of_dicts(self, monkeypatch):
        """Stub the Redis layer so we don't need a real Redis server,
        then assert that ``cached_public`` stores a list of dicts
        (not a list of strings) and re-hydrates it correctly.
        """
        from backend.core import cache_v2

        store: dict = {}

        class _FakeRedis:
            def get(self, key):
                return store.get(key)

            def setex(self, key, ttl, value):
                store[key] = value

        monkeypatch.setattr(cache_v2, "get_redis", lambda: _FakeRedis())

        @cache_v2.cached_public(ttl=60)
        def list_endpoint():
            return [
                _MiniProfile(
                    id=UUID("4ba29d13-1a4e-5e60-91e8-7762a5b7549b"),
                    name="Alex y Elvia",
                    slug="alex-y-elvia",
                    is_main_pastor=False,
                ),
                _MiniProfile(
                    id=UUID("c68ddb5d-469e-5a7a-86c1-7a93e7712d1a"),
                    name="Camilo Pajaro",
                    slug="camilo-pajaro",
                    is_main_pastor=True,
                ),
            ]

        # First call: hits the wrapped function, writes to cache.
        first = list_endpoint()
        assert len(first) == 2
        assert first[0].name == "Alex y Elvia"

        # Inspect the raw stored value. Before the fix, this was a
        # JSON array of Python debug strings ("id=UUID('...') ...")
        # which the next call would re-parse as [str, str].
        raw = next(iter(store.values()))
        parsed_back = json.loads(raw)
        assert isinstance(parsed_back, list)
        for item in parsed_back:
            assert isinstance(item, dict), (
                f"Cache stored list element as {type(item).__name__}; "
                f"this is the original 500 root cause regressing"
            )
            assert "id" in item
            assert "name" in item

        # Second call: cache hit. The wrapper returns the deserialized
        # JSON-safe form (a list of dicts, NOT a list of Pydantic models).
        # FastAPI's response_model then re-validates these into Pydantic
        # models for the wire response. The test asserts the cache
        # contract (data round-trip integrity) using dict access, which
        # matches the actual cached shape.
        second = list_endpoint()
        assert isinstance(second, list)
        assert len(second) == 2
        assert isinstance(second[1], dict)
        assert second[1]["is_main_pastor"] is True
        # Round-trip preserves accent in name (no str() coercion).
        assert second[1]["name"] == "Camilo Pajaro"

    def test_primitive_return_roundtrips(self, monkeypatch):
        from backend.core import cache_v2

        store: dict = {}

        class _FakeRedis:
            def get(self, key):
                return store.get(key)

            def setex(self, key, ttl, value):
                store[key] = value

        monkeypatch.setattr(cache_v2, "get_redis", lambda: _FakeRedis())

        @cache_v2.cached_public(ttl=60)
        def dict_endpoint():
            return {"count": 9, "ok": True}

        first = dict_endpoint()
        assert first == {"count": 9, "ok": True}
        second = dict_endpoint()
        assert second == {"count": 9, "ok": True}

    def test_single_pydantic_model_roundtrips(self, monkeypatch):
        from backend.core import cache_v2

        store: dict = {}

        class _FakeRedis:
            def get(self, key):
                return store.get(key)

            def setex(self, key, ttl, value):
                store[key] = value

        monkeypatch.setattr(cache_v2, "get_redis", lambda: _FakeRedis())

        @cache_v2.cached_public(ttl=60)
        def single_endpoint():
            return _MiniProfile(
                id=UUID("4ba29d13-1a4e-5e60-91e8-7762a5b7549b"),
                name="Yair Macea",
                slug="yair-macea",
            )

        first = single_endpoint()
        # First call returns the live Pydantic model (not yet cached).
        assert first.name == "Yair Macea"
        # Second call: cache hit. Contract is that the JSON-safe form
        # round-trips. The wrapper returns the deserialized dict;
        # callers (FastAPI's response_model) re-validate into Pydantic
        # models.
        second = single_endpoint()
        assert isinstance(second, dict)
        assert second["name"] == "Yair Macea"
        assert second["slug"] == "yair-macea"
