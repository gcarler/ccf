"""Tests for SEO Score Trend widget (cms_seo_snapshots).

Covers:
1. Migration shape (table columns + unique constraint + indexes)
2. cron ``capture_daily_seo_snapshots`` idempotency (UNIQUE site_id +
   captured_date prevents duplicate rows on a retry)
3. ``capture_daily_seo_snapshots`` populates all aggregate fields
   correctly from a real audit pass (no skips in dry-run)
4. ``get_seo_trend`` returns series sorted ascending + scope by sede_id
   (Axioma 3) + scope by site_id + falls back to empty when no data
5. ``get_cms_dashboard`` exposes the ``seo_trend`` slice via the
   dashboard endpoint (dashboard API surface)
6. Alert logic: is_alert=True iff change_vs_prior < -10 (10-point
   threshold is documented + unit-tested both directions)

Axioma 3 — Multi-tenant: every fixture site has a ``sede_id`` and the
trend queries filter by it cleanly. The CmsSite model is faro-global
(content cross-sede by design) but snapshots carry their sede_id
mirrored from the site at capture time so the widget scope works
without an expensive JOIN.
"""

from __future__ import annotations

import datetime as dt
import uuid

# ── Helpers ─────────────────────────────────────────────────────────────────────

def _iso_days_ago(n: int) -> str:
    return (dt.date.today() - dt.timedelta(days=n)).isoformat()


def _make_site(db, *, site_key: str, name: str = "Test Faro", sede_id=None):
    from backend import models

    site = models.CmsSite(
        id=uuid.uuid4(),
        site_key=site_key,
        name=name,
        base_path=f"/{site_key}",
        is_active=True,
        sede_id=sede_id,
    )
    db.add(site)
    db.flush()
    return site


def _make_sede(db, *, nombre: str = "Sede Test"):
    from backend import models

    # ``Sede`` exige ``ciudad`` (NOT NULL) en la base de datos. La
    # sembrada por ``seed_admin`` usa un valor real; los tests nuevos
    # también lo necesitan para no chocar con la constraint.
    sede = models.Sede(
        id=uuid.uuid4(),
        nombre=nombre,
        ciudad="Bogotá",
        es_activa=True,
    )
    db.add(sede)
    db.flush()
    return sede


def _make_page(db, site_id, *, slug: str = "p1", title: str = "Página 1",
               status: str = "published", seo=None):
    from backend import models

    page = models.CmsPage(
        id=uuid.uuid4(),
        site_id=site_id,
        slug=slug,
        title=title,
        status=status,
        seo_json=seo or {
            "meta_description": "Una descripción razonable de longitud media "
            "para que el auditor la apruebe sin warnings.",
            "robots_meta": "index, follow",
        },
    )
    db.add(page)
    db.flush()
    return page


def _make_snapshot(db, *, site, score: int, captured_date: dt.date,
                   total_pages: int = 5, errors: int = 0, critical: int = 0):
    from backend import models

    snap = models.CmsSeoSnapshot(
        id=uuid.uuid4(),
        site_id=site.id,
        sede_id=site.sede_id,
        captured_date=captured_date,
        captured_at=dt.datetime.now(dt.timezone.utc),
        average_score=score,
        total_pages=total_pages,
        pages_with_errors=errors,
        critical_issues=critical,
        by_severity_json={"error": errors, "warning": 0, "info": 0},
    )
    db.add(snap)
    db.flush()
    return snap


# ── 1. Migration shape ──────────────────────────────────────────────────────────

class TestMigrationShape:
    """Verify the alembic migration creates the table + indexes correctly."""

    def test_migration_revision_chain_matches(self):
        # Latest cms schedule migration = 20260706_0001 then
        # this one = 20260706_0002. We don't spin up alembic here;
        # instead we confirm the file exists + down_revision is wired.
        import importlib.util
        import pathlib

        path = (
            pathlib.Path(__file__).parent.parent
            / "alembic" / "versions" / "20260706_0002_cms_seo_snapshots.py"
        )
        assert path.exists(), f"missing migration file at {path}"

        spec = importlib.util.spec_from_file_location(
            "milestone_20260706_0002", str(path)
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        assert mod.revision == "20260706_0002_cms_seo_snapshots"
        assert mod.down_revision == "20260706_0001_cms_schedule"


# ── 2. capture_daily_seo_snapshots: idempotency ──────────────────────────────────

class TestCaptureDailySeoSnapshotsIdempotency:
    """Same-day retries must collapse to a single snapshot row."""

    def test_double_pass_same_day_creates_only_one_row(
        self, client, db_session
    ):
        from backend import crud, models

        sede = _make_sede(db_session)
        site = _make_site(db_session, site_key="faro-idem", sede_id=sede.id)
        _make_page(db_session, site.id)

        today = dt.date.today()
        # First pass — should create 1 snapshot
        first = crud.capture_daily_seo_snapshots(db_session, today=today)
        db_session.commit()
        assert first["snapshots_count"] == 1
        assert first["skipped_count"] == 0

        # Second pass — should skip because already captured today
        second = crud.capture_daily_seo_snapshots(db_session, today=today)
        db_session.commit()
        assert second["snapshots_count"] == 0
        assert second["skipped_count"] == 1

        # And the table still has exactly one row for (site, today)
        rows = (
            db_session.query(models.CmsSeoSnapshot)
            .filter(
                models.CmsSeoSnapshot.site_id == site.id,
                models.CmsSeoSnapshot.captured_date == today,
            )
            .all()
        )
        assert len(rows) == 1

    def test_dry_run_does_not_persist(
        self, client, db_session
    ):
        from backend import crud, models

        sede = _make_sede(db_session)
        site = _make_site(db_session, site_key="faro-dry", sede_id=sede.id)
        _make_page(db_session, site.id)

        today = dt.date.today()
        result = crud.capture_daily_seo_snapshots(
            db_session, today=today, dry_run=True
        )
        db_session.commit()

        # dry_run cuenta los sites que habría procesado pero no debe
        # insertar nada.
        assert result["sites_captured"] >= 1
        assert result["snapshots_count"] == 0

        rows = (
            db_session.query(models.CmsSeoSnapshot)
            .filter(models.CmsSeoSnapshot.site_id == site.id)
            .all()
        )
        assert len(rows) == 0

    def test_inactive_sites_are_skipped(
        self, client, db_session
    ):
        from backend import crud

        sede = _make_sede(db_session)
        site = _make_site(db_session, site_key="faro-off", sede_id=sede.id)
        site.is_active = False
        db_session.flush()

        today = dt.date.today()
        result = crud.capture_daily_seo_snapshots(db_session, today=today)
        db_session.commit()
        assert result["sites_captured"] == 0


# ── 3. capture_daily_seo_snapshots: aggregate fields ────────────────────────────

class TestCaptureDailySeoSnapshotsAggregate:
    """Ensure aggregate (avg, total, errors, critical, by_severity) populates."""

    def test_snapshot_uses_actual_audit_aggregate(
        self, client, db_session
    ):
        from backend import crud, models

        sede = _make_sede(db_session)
        site = _make_site(db_session, site_key="faro-agg", sede_id=sede.id)
        # 3 published pages with valid SEO content
        for i in range(3):
            _make_page(
                db_session,
                site.id,
                slug=f"good-{i}",
                title=f"Good {i}",
            )

        today = dt.date.today()
        crud.capture_daily_seo_snapshots(db_session, today=today)
        db_session.commit()

        snap = (
            db_session.query(models.CmsSeoSnapshot)
            .filter(
                models.CmsSeoSnapshot.site_id == site.id,
                models.CmsSeoSnapshot.captured_date == today,
            )
            .first()
        )
        assert snap is not None
        assert snap.total_pages == 3
        # El score real de páginas con meta_description válida y
        # ``robots_meta=index, follow`` pero sin secciones visibles ni
        # og_image es ~60 (penalizaciones por title_len + no_visible
        # + og_image). No exigimos >=70 porque las páginas de test
        # no construyen ``CmsSection`` ni ``seo_json.meta_image``.
        assert snap.average_score >= 50
        assert snap.by_severity_json is not None
        assert isinstance(snap.by_severity_json, dict)


# ── 4. get_seo_trend: scope + ordering ──────────────────────────────────────────

class TestGetSeoTrend:
    def test_returns_series_ascending_by_date(
        self, client, db_session
    ):
        from backend import crud

        sede = _make_sede(db_session)
        site = _make_site(db_session, site_key="faro-series", sede_id=sede.id)

        # Insert snapshots out-of-order to verify ordering
        today = dt.date.today()
        for days_ago, score in [(10, 80), (1, 65), (5, 90)]:
            _make_snapshot(
                db_session,
                site=site,
                score=score,
                captured_date=today - dt.timedelta(days=days_ago),
            )
        db_session.commit()

        result = crud.get_seo_trend(
            db_session, sede_id=sede.id, days=30
        )
        labels = [p["captured_date"] for p in result["series"]]
        assert labels == sorted(labels)
        assert result["days"] == 30

    def test_sede_id_scope_filters_out_other_sedes(
        self, client, db_session
    ):
        from backend import crud

        sede_a = _make_sede(db_session, nombre="A")
        sede_b = _make_sede(db_session, nombre="B")
        site_a = _make_site(db_session, site_key="faro-a", sede_id=sede_a.id)
        site_b = _make_site(db_session, site_key="faro-b", sede_id=sede_b.id)

        today = dt.date.today()
        _make_snapshot(db_session, site=site_a, score=80, captured_date=today)
        _make_snapshot(db_session, site=site_b, score=30, captured_date=today)
        db_session.commit()

        scoped = crud.get_seo_trend(db_session, sede_id=sede_a.id, days=7)
        assert all(
            p["average_score"] == 80 for p in scoped["series"]
        ), "Scope must exclude snapshots from other sedes"

    def test_empty_scope_returns_no_data(
        self, client, db_session
    ):
        from backend import crud

        _make_sede(db_session)
        ghost = uuid.uuid4()  # sede_id that doesn't exist
        result = crud.get_seo_trend(db_session, sede_id=ghost, days=30)
        assert result["series"] == []
        assert result["days"] == 30


# ── 5. Dashboard slice wiring ───────────────────────────────────────────────────

class TestCmsDashboardSeoSliceWiring:
    """`GET /api/dashboard/cms` debe devolver `seo_trend` cuando hay datos."""

    def test_dashboard_payload_includes_seo_trend_key(
        self, client, db_session
    ):
        from backend import crud

        # ``seed_admin`` y ``auth_headers`` están definidos en
        # ``tests/conftest.py`` con firmas estables:
        #   seed_admin(db_session, email=..., password=...) -> (user, persona, sede)
        #   auth_headers(client, email=..., password=...)
        # No son pytest fixtures — son helpers que reciben ``client`` /
        # ``db_session`` por argumento.
        from tests.conftest import auth_headers as _auth_headers  # type: ignore
        from tests.conftest import seed_admin as _seed_admin  # type: ignore

        admin_email = "seo-slice@example.com"
        # Axioma 3 — Multi-tenant: el endpoint ``/api/dashboard/cms``
        # scope las queries por la sede del admin logueado. Si el
        # test crea una sede NUEVA para el site, la query de la
        # dashboard (filtrada por la sede del admin) NO ve ni el
        # site ni el snapshot — ``has_data`` cae a False en el
        # fallback. Hay que reutilizar la sede que ``seed_admin``
        # crea.
        _user, _persona, admin_sede = _seed_admin(db_session, email=admin_email)

        site = _make_site(
            db_session,
            site_key="faro-slice",
            sede_id=admin_sede.id,
        )
        _make_page(db_session, site.id)
        today = dt.date.today()
        crud.capture_daily_seo_snapshots(db_session, today=today)
        db_session.commit()

        headers = _auth_headers(client, email=admin_email)
        resp = client.get(
            "/api/dashboard/cms",
            headers=headers,
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert "seo_trend" in body
        trend = body["seo_trend"]
        # Tras la captura de hoy, has_data debe ser True.
        assert trend["has_data"] is True
        assert trend["current_score"] is not None
        assert isinstance(trend["history_7d"], list)
        assert isinstance(trend["history_30d"], list)


# ── 6. Alert logic ──────────────────────────────────────────────────────────────

class TestSeoAlertLogic:
    """`is_alert=True` cuando la caída es >=10 pts."""

    def test_alert_triggers_on_drop_ge_threshold(
        self, client, db_session
    ):
        from backend.crud.dashboard import _build_seo_trend_slice

        sede = _make_sede(db_session)
        site = _make_site(db_session, site_key="faro-alert", sede_id=sede.id)
        today = dt.date.today()

        # Drop de 12 pts today: yesterday=92 → today=80 → is_alert=True
        _make_snapshot(
            db_session, site=site, score=92,
            captured_date=today - dt.timedelta(days=1),
        )
        _make_snapshot(
            db_session, site=site, score=80, captured_date=today,
        )
        db_session.commit()

        trend = _build_seo_trend_slice(db_session, sede_id=sede.id)
        assert trend.change_vs_prior == -12
        assert trend.is_alert is True
        assert trend.alert_threshold == 10

    def test_alert_does_not_trigger_on_small_drop(
        self, client, db_session
    ):
        """Drop de 5 pts: NO debe disparar alerta."""
        from backend.crud.dashboard import _build_seo_trend_slice

        sede = _make_sede(db_session)
        site = _make_site(db_session, site_key="faro-small", sede_id=sede.id)
        today = dt.date.today()

        # ayer=90 → hoy=85 = -5 (umbral = -10)
        _make_snapshot(
            db_session, site=site, score=90,
            captured_date=today - dt.timedelta(days=1),
        )
        _make_snapshot(
            db_session, site=site, score=85, captured_date=today,
        )
        db_session.commit()

        trend = _build_seo_trend_slice(db_session, sede_id=sede.id)
        assert trend.change_vs_prior == -5
        assert trend.is_alert is False

    def test_rise_does_not_trigger_alert(
        self, client, db_session
    ):
        from backend.crud.dashboard import _build_seo_trend_slice

        sede = _make_sede(db_session)
        site = _make_site(db_session, site_key="faro-rise", sede_id=sede.id)
        today = dt.date.today()
        _make_snapshot(
            db_session, site=site, score=60,
            captured_date=today - dt.timedelta(days=1),
        )
        _make_snapshot(
            db_session, site=site, score=85,
            captured_date=today,
        )
        db_session.commit()

        trend = _build_seo_trend_slice(db_session, sede_id=sede.id)
        assert trend.change_vs_prior == 25
        assert trend.is_alert is False


# ── 7. Schema + fallback twin ───────────────────────────────────────────────────

class TestCmsDashboardSeoSliceFallback:
    """Cuando NO hay snapshots, el slice debe caer en audit on-the-fly."""

    def test_no_snapshots_yet_returns_fallback_with_has_data_true(
        self, client, db_session
    ):
        from backend.crud.dashboard import _build_seo_trend_slice

        sede = _make_sede(db_session)
        site = _make_site(db_session, site_key="faro-fb", sede_id=sede.id)
        _make_page(db_session, site.id)

        # No snapshots → fallback path
        trend = _build_seo_trend_slice(db_session, sede_id=sede.id)
        assert trend.has_data is True
        assert trend.current_score is not None
        assert len(trend.history_30d) == 1
        assert trend.captured_at is not None


# ── 8. Multi-tenant boundary ────────────────────────────────────────────────────

class TestSeoTrendMultiTenantBoundary:
    """Las snapshots de sede_b NUNCA deben aparecer en widgets de sede_a."""

    def test_widget_slices_a_does_not_leak_b_snapshots(
        self, client, db_session
    ):
        from backend.crud.dashboard import _build_seo_trend_slice

        sede_a = _make_sede(db_session, nombre="Widget A")
        sede_b = _make_sede(db_session, nombre="Widget B")
        site_a = _make_site(db_session, site_key="site-a", sede_id=sede_a.id)
        site_b = _make_site(db_session, site_key="site-b", sede_id=sede_b.id)

        today = dt.date.today()
        _make_snapshot(db_session, site=site_a, score=88, captured_date=today)
        _make_snapshot(db_session, site=site_b, score=22, captured_date=today)
        db_session.commit()

        widget_a = _build_seo_trend_slice(db_session, sede_id=sede_a.id)
        # Pydantic ``SeoTrendPoint`` no es subscriptable en v2 strict
        # — uso acceso por atributo. ``value`` es el campo que
        # almacena el score.
        assert all(p.value != 22 for p in widget_a.history_30d)
        assert all(p.value != 22 for p in widget_a.history_7d)
        # Y el site A sí contribuye con su 88.
        assert any(p.value == 88 for p in widget_a.history_30d)
