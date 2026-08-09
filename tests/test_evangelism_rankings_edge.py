"""Edge cases for evangelism_rankings.py — TTL cache, month ranges, strategy filters."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from backend import models
from backend.api.evangelism_rankings import (
    _active_groups_query,
    _last_month_range,
    _month_range,
)
from backend.api.evangelism_shared import (
    _TTL_CACHE,
)
from backend.api.evangelism_shared import (
    ttl_cache as _ttl_cache,
)
from backend.models_evangelism import Sede
from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin


@pytest.fixture
def sede(db_session):
    s = db_session.query(Sede).first()
    if not s:
        s = Sede(id=uuid.uuid4(), nombre="Test", ciudad="Test", es_activa=True)
        db_session.add(s)
        db_session.commit()
    return s


def _ok(status):
    return status in (200, 201, 204)


# ── Unit: _month_range ────────────────────────────────────────────────────────


class TestMonthRange:
    def test_normal_month(self):
        start, end = _month_range(2026, 6)
        assert start.month == 6
        assert start.day == 1
        assert end.month == 7
        assert end.day == 1

    def test_december_rollover(self):
        """Line 67: December rolls to next year."""
        start, end = _month_range(2026, 12)
        assert start.month == 12
        assert start.year == 2026
        assert end.month == 1
        assert end.year == 2027


class TestLastMonthRange:
    def test_january_rollover(self):
        """Line 81 verified via _month_range (underlying helper)."""
        start, end = _month_range(2025, 12)
        assert start.month == 12
        assert start.year == 2025
        assert end.month == 1
        assert end.year == 2026

    def test_normal_month(self):
        start, end = _last_month_range()
        now = datetime.now(timezone.utc)
        if now.month != 1:
            assert start.month == now.month - 1
            assert end.month == now.month


# ── Unit: _active_groups_query ────────────────────────────────────────────────


class TestActiveGroupsQuery:
    def test_with_strategy_id(self, db_session, sede):
        """Line 88: filters by strategy_id."""
        p = models.Persona(id=uuid.uuid4(), first_name="SG", last_name="T", sede_id=sede.id)
        db_session.add(p)
        db_session.flush()

        g = models.GrupoEvangelismo(id=uuid.uuid4(), nombre="SG", sede_id=sede.id, lider_persona_id=p.id, activo=True)
        db_session.add(g)
        db_session.commit()

        q = _active_groups_query(db_session, strategy_id=uuid.uuid4(), sede_id=sede.id)
        results = q.all()
        assert len(results) == 0  # no groups with that strategy_id

    def test_without_filters(self, db_session):
        """Line 87-90: no filters."""
        q = _active_groups_query(db_session)
        results = q.all()
        assert isinstance(results, list)


# ── Unit: _ttl_cache ──────────────────────────────────────────────────────────


class TestTTLCache:
    def test_cache_hit(self):
        """Line 46-47: TTL cache returns cached result."""
        call_count = 0

        @_ttl_cache(key_fn=lambda *a, **kw: "test", ttl=60)
        def cached_fn():
            nonlocal call_count
            call_count += 1
            return "result"

        # First call
        r1 = cached_fn()
        assert r1 == "result"
        assert call_count == 1

        # Second call within TTL
        r2 = cached_fn()
        assert r2 == "result"
        assert call_count == 1  # still 1, served from cache

        # Clean up
        _TTL_CACHE.pop("test", None)

    def test_cache_expiry(self):
        """Line 46: expired entry re-runs function."""
        call_count = 0

        @_ttl_cache(key_fn=lambda *a, **kw: "exp_test", ttl=0)
        def cached_fn():
            nonlocal call_count
            call_count += 1
            return f"result_{call_count}"

        r1 = cached_fn()
        r2 = cached_fn()
        assert call_count == 2  # every call re-runs because TTL=0

        _TTL_CACHE.pop("exp_test", None)

    def test_cache_prune(self):
        """Lines 51-54: prune stale entries when cache > 200."""
        # Clear cache
        _TTL_CACHE.clear()

        @_ttl_cache(key_fn=lambda *a, **kw: kw.get("k", "x"), ttl=0)
        def cached_fn(**kw):
            return "x"

        # Fill cache with 201 entries, TTL=0 means they're all stale
        for i in range(201):
            cached_fn(k=f"k{i}")

        # Prune on next call (cache has 201 entries + 1 = 202, triggers prune)
        cached_fn(k="final")

        # Cache should have been pruned
        assert len(_TTL_CACHE) < 200

        _TTL_CACHE.clear()


# ── Integration: rankings with strategy_id filter ─────────────────────────────


@pytest.fixture
def full(client, db_session):
    admin, _, _ = _seed_admin(db_session, email="rnk2@test.com")
    headers = _auth_headers(client, email="rnk2@test.com", password="testpass123")
    sede = db_session.query(models.Sede).first()
    return {"c": client, "h": headers, "s": sede}


class TestRankingsWithStrategy:
    def test_monthly_with_strategy(self, full, db_session):
        """Lines 261, 284, 301, 319: monthly comparison with strategy_id."""
        c, h, s = full["c"], full["h"], full["s"]
        now = datetime.now(timezone.utc)

        p = models.Persona(id=uuid.uuid4(), first_name="S", last_name="T", sede_id=s.id)
        db_session.add(p)
        db_session.flush()

        g = models.GrupoEvangelismo(id=uuid.uuid4(), nombre="SG", sede_id=s.id, lider_persona_id=p.id, activo=True)
        db_session.add(g)
        db_session.flush()

        ses = models.SesionGrupo(id=uuid.uuid4(), grupo_id=g.id, fecha_sesion=now, estado="REALIZADA")
        db_session.add(ses)
        db_session.flush()
        db_session.add(models.Asistencia(id=uuid.uuid4(), sesion_id=ses.id, persona_id=p.id, estado="ASISTIO"))
        db_session.add(
            models.ParticipanteGrupo(
                id=uuid.uuid4(),
                grupo_id=g.id,
                persona_id=p.id,
                rol_base="miembro",
                activo=True,
                fecha_ingreso=now - timedelta(days=5),
            )
        )
        db_session.commit()

        # Test with a non-existent strategy_id — should return data for all groups
        resp = c.get(f"/api/evangelism/rankings/monthly-comparison?strategy_id={uuid.uuid4()}", headers=h)
        assert _ok(resp.status_code), f"monthly strategy: {resp.status_code}"

    def test_leaders_with_strategy(self, full, db_session):
        """Leaders with strategy_id filter."""
        c, h, s = full["c"], full["h"], full["s"]

        p = models.Persona(id=uuid.uuid4(), first_name="Ld", last_name="T", sede_id=s.id)
        db_session.add(p)
        db_session.commit()

        resp = c.get(f"/api/evangelism/rankings/leaders?strategy_id={uuid.uuid4()}", headers=h)
        assert _ok(resp.status_code)

    def test_groups_with_strategy(self, full, db_session):
        """Groups rankings with strategy_id."""
        c, h, s = full["c"], full["h"], full["s"]
        resp = c.get(f"/api/evangelism/rankings/groups?strategy_id={uuid.uuid4()}", headers=h)
        assert _ok(resp.status_code)
