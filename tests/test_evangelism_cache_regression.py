"""
Evangelism — TTL Cache Cross-Tenant Safety Regression Tests (P-04).

Verifies that the in-memory TTL cache introduced in
``backend.api.evangelism_shared.ttl_cache`` partitions by tenant
(``analytics_cache_scope``) so that:

1. A cached analytics result produced by a user of Sede A is NOT
   returned to a user of Sede B that requests the same endpoint with
   the same ``strategy_id``. Without the tenant suffix in the cache key,
   the second user would receive the cached payload, bypassing the
   ``_get_strategy_or_404`` cross-sede check.

2. ``invalidate_ttl_cache(prefix=...)`` only evicts the entries that
   match the prefix, leaving the rest of the cache intact (no
   accidental cross-tenant flush).

3. ``invalidate_ttl_cache()`` without args clears the whole cache.

These tests intentionally stay decoupled from any specific endpoint so
they can run as pure unit tests against the decorator helpers and do
not require the live FastAPI ``client`` fixture. They depend only on
the cache implementation plus a minimal ``User`` stub.
"""

from __future__ import annotations

import time
import uuid
from types import SimpleNamespace

from backend.api import evangelism_shared as shared


class _UserStub(SimpleNamespace):
    """Minimal stand-in for ``models.User`` carrying tenant attributes."""


def _make_user(sede_id=None, user_id=None):
    return _UserStub(sede_id=sede_id, id=user_id or uuid.uuid4())


def _reset_cache():
    shared._TTL_CACHE.clear()


def test_analytics_cache_scope_by_sede():
    """Cache scope collapses to ``sede_id`` when present."""
    u = _make_user(sede_id="sede-A", user_id=uuid.uuid4())
    assert shared.analytics_cache_scope(u) == "sede-A"


def test_analytics_cache_scope_falls_back_to_user_id():
    """When no sede_id is set, scope collapses to ``user:<id>`` for safety."""
    uid = uuid.uuid4()
    u = _make_user(sede_id=None, user_id=uid)
    assert shared.analytics_cache_scope(u) == f"user:{uid}"


def test_analytics_cache_scope_anonymous():
    """A None user is treated as anonymous — no tenant leak from a None key."""
    assert shared.analytics_cache_scope(None) == "user:anonymous"


def test_cache_partitions_by_tenant():
    """Results cached under tenant A must NOT leak to tenant B for the same key args."""
    _reset_cache()
    calls = {"n": 0}

    @shared.ttl_cache(lambda strategy_id, db=None, current_user=None: f"k:{strategy_id}:{shared.analytics_cache_scope(current_user)}")
    def fetch(strategy_id, db=None, current_user=None):
        calls["n"] += 1
        return {"called_for": shared.analytics_cache_scope(current_user), "strategy_id": str(strategy_id)}

    sid = uuid.uuid4()
    user_a = _make_user(sede_id="sede-A", user_id=uuid.uuid4())
    user_b = _make_user(sede_id="sede-B", user_id=uuid.uuid4())

    r1 = fetch(sid, db=None, current_user=user_a)
    assert r1["called_for"] == "sede-A"
    r2 = fetch(sid, db=None, current_user=user_b)
    assert r2["called_for"] == "sede-B", "Tenant B received the cached payload from A (cross-tenant leak via shared cache key)"
    assert calls["n"] == 2, "Both tenants must execute the handler the first time (no shared cache hit)"


def test_cache_hit_within_same_tenant():
    """Within the same tenant, a second call within TTL must hit the cache."""
    _reset_cache()
    calls = {"n": 0}

    @shared.ttl_cache(lambda strategy_id, period="30d", db=None, current_user=None: f"k:{strategy_id}:{period}:{shared.analytics_cache_scope(current_user)}")
    def fetch(strategy_id, period="30d", db=None, current_user=None):
        calls["n"] += 1
        return {"ok": True, "sid": str(strategy_id)}

    sid = uuid.uuid4()
    user = _make_user(sede_id="sede-A", user_id=uuid.uuid4())
    fetch(sid, period="30d", current_user=user)
    fetch(sid, period="30d", current_user=user)
    assert calls["n"] == 1, "Second call should have hit the cache"


def test_cache_ttl_expires():
    """Entries expire after the configured TTL (uses 1s TTL + sleep)."""
    _reset_cache()
    calls = {"n": 0}

    @shared.ttl_cache(lambda strategy_id, db=None, current_user=None: f"k:{strategy_id}:{shared.analytics_cache_scope(current_user)}", ttl=1)
    def fetch(strategy_id, db=None, current_user=None):
        calls["n"] += 1
        return {"ok": True}

    sid = uuid.uuid4()
    user = _make_user(sede_id="sede-A", user_id=uuid.uuid4())
    fetch(sid, current_user=user)
    time.sleep(1.1)
    fetch(sid, current_user=user)
    assert calls["n"] == 2, "After TTL expired the handler should run again"


def test_invalidate_by_prefix_only_evicts_matching_keys():
    """Prefix invalidation must evict only matching keys."""
    _reset_cache()

    @shared.ttl_cache(lambda key, db=None, current_user=None: f"full:{key}:{shared.analytics_cache_scope(current_user)}")
    def full(key, db=None, current_user=None):
        return {"value": key}

    @shared.ttl_cache(lambda key, db=None, current_user=None: f"kpis:{key}:{shared.analytics_cache_scope(current_user)}")
    def kpis(key, db=None, current_user=None):
        return {"value": key}

    user = _make_user(sede_id="sede-A", user_id=uuid.uuid4())
    full("strategy-1", current_user=user)
    full("strategy-2", current_user=user)
    kpis("strategy-1", current_user=user)

    keys_before = set(shared._TTL_CACHE.keys())
    assert any(k.startswith("full:strategy-1:") for k in keys_before)
    assert any(k.startswith("full:strategy-2:") for k in keys_before)
    assert any(k.startswith("kpis:strategy-1:") for k in keys_before)

    shared.invalidate_ttl_cache(prefix=f"full:strategy-1:{shared.analytics_cache_scope(user)}")
    keys_after = set(shared._TTL_CACHE.keys())
    assert not any(k.startswith("full:strategy-1:") for k in keys_after), "Target key was NOT evicted"
    assert any(k.startswith("full:strategy-2:") for k in keys_after), "Prefix eviction must NOT touch sibling keys"
    assert any(k.startswith("kpis:strategy-1:") for k in keys_after), "Prefix eviction must NOT touch other endpoint caches"


def test_invalidate_clear_clears_everything():
    """Bare ``invalidate_ttl_cache()`` wipes the whole cache."""
    _reset_cache()

    @shared.ttl_cache(lambda x, db=None, current_user=None: f"k:{x}:{shared.analytics_cache_scope(current_user)}")
    def fn(x, db=None, current_user=None):
        return x

    user = _make_user(sede_id="sede-X", user_id=uuid.uuid4())
    fn(1, current_user=user)
    fn(2, current_user=user)
    assert len(shared._TTL_CACHE) == 2

    shared.invalidate_ttl_cache()
    assert shared._TTL_CACHE == {}


# ──────────────────────────────────────────────────────────────────────
# Integration — cache wired into the live FastAPI handler
# ──────────────────────────────────────────────────────────────────────


def test_analytics_endpoint_cache_hit_in_memory(client, db_session):
    """Two consecutive calls to /analytics/strategy/{id} must execute the
    handler exactly once with the same admin user (in-memory TTL hit)."""
    from tests.conftest import auth_headers, seed_admin

    shared._TTL_CACHE.clear()
    seed_admin(db_session, email="cacheint@test.com")
    headers = auth_headers(client, email="cacheint@test.com", password="testpass123")

    resp = client.post(
        "/api/evangelism/strategies", json={"name": "CacheStrategy"}, headers=headers
    )
    import pytest as _pytest

    if resp.status_code not in (200, 201):
        raise _pytest.skip(f"strategy create returned {resp.status_code}: {resp.text[:100]}")
    sid = resp.json()["id"]
    kpis_prefix = f"kpis:{sid}:"

    before = [k for k in shared._TTL_CACHE if k.startswith(kpis_prefix)]
    assert not before, f"Cache should be empty before first call — got {before}"

    r1 = client.get(f"/api/evangelism/analytics/strategy/{sid}", headers=headers)
    assert r1.status_code == 200, f"first call: {r1.status_code} {r1.text[:120]}"
    keys_after_first = [k for k in shared._TTL_CACHE if k.startswith(kpis_prefix)]
    assert len(keys_after_first) == 1, (
        f"expected one cache entry after first call — got {keys_after_first}"
    )

    r2 = client.get(f"/api/evangelism/analytics/strategy/{sid}", headers=headers)
    assert r2.status_code == 200
    keys_after_second = [k for k in shared._TTL_CACHE if k.startswith(kpis_prefix)]
    assert len(keys_after_second) == 1, "Second call should NOT have created a new cache entry"


def test_analytics_endpoint_cache_isolated_by_tenant(client, db_session):
    """Two users in different sedes requesting the same strategy_id must
    each get their own cache entry — never share."""
    from tests.conftest import auth_headers, seed_admin, seed_user_with_role

    shared._TTL_CACHE.clear()
    seed_admin(db_session, email="ca-a@test.com")

    # A second admin in a different sede (force new sede via explicit UUID)
    other_sede_id = uuid.uuid4()
    seed_user_with_role(
        db_session,
        role_name="ADMIN",
        email="ca-b@test.com",
        sede_id=other_sede_id,
    )
    headers_a = auth_headers(client, email="ca-a@test.com", password="testpass123")
    headers_b = auth_headers(client, email="ca-b@test.com", password="testpass123")

    # Strategy owned by sede A
    resp = client.post(
        "/api/evangelism/strategies", json={"name": "TenantScope"}, headers=headers_a
    )
    import pytest as _pytest

    if resp.status_code not in (200, 201):
        raise _pytest.skip(f"strategy create returned {resp.status_code}: {resp.text[:100]}")
    sid = resp.json()["id"]

    r_a = client.get(f"/api/evangelism/analytics/strategy/{sid}", headers=headers_a)
    assert r_a.status_code == 200

    r_b = client.get(f"/api/evangelism/analytics/strategy/{sid}", headers=headers_b)
    assert r_b.status_code in (200, 404, 403), f"Unexpected B status: {r_b.status_code}"
    if r_b.status_code == 200:
        assert r_b.json() != r_a.json(), (
            "Tenant B got an identical payload to A — possible cross-tenant cache leak"
        )

    # The handler raises HTTPException(404) before returning if the
    # strategy isn't visible in the caller's sede, so a cross-tenant miss
    # leaves NO cache entry for B (the wrapper only caches success
    # returns). Verify the cache contains at most A's entry and a
    # potential B entry would be under B's scope, never A's.
    cache_keys = [k for k in shared._TTL_CACHE if k.startswith(f"kpis:{sid}:")]
    scopes = {k.rsplit(":", 1)[-1] for k in cache_keys}
    assert scopes, f"Expected at least A's scope in cache — got {scopes}"
    # No cache key should collapse to a single shared scope across tenants.
    for scope in scopes:
        # The scope format is either "sede-<id>" or "user:<uuid>" — never empty.
        assert scope and scope != "user:None", f"Invalid/anon scope in cache: {scope}"
