"""F-07 (errorescms.md): endpoint historico de CmsSeoSnapshot por site.

Antes solo existia el CRUD ``capture_daily_seo_snapshots`` (cron que
persiste rows por dia) y el aggregator ``get_seo_trend`` que devuelve
series agregadas en un dict, no listado de rows crudos. F-07 cierra
con el endpoint ``GET /cms/v2/sites/{site_key}/seo-snapshots`` que
expone el listado paginado de snapshots historicos por site.

Tests:
  1) CRUD-direct: list_seo_snapshots retorna rows ordenados DESC por fecha
  2) CRUD-direct: paginacion con skip/limit respeta total
  3) CRUD-direct: filtrado por site_id (no filtra otros sites)
  4) CRUD-direct: site sin snapshots retorna lista vacia
  5) API: endpoint 200 con site existente
  6) API: endpoint 404 con site inexistente
  7) API: paginacion expone total/skip/limit
  8) Schema: CmsSeoSnapshotRead roundtrip desde ORM
"""
from __future__ import annotations

import datetime as dt
import uuid as _uuid

from backend import models
from backend.crud.cms import list_seo_snapshots
from tests.conftest import auth_headers, seed_admin


def _seed(db_session, email):
    return seed_admin(db_session, email=email, password="testpass123")


def _seed_site(db_session, site_key, sede_id=None):
    """Crea un site CMS global. base_path unico por site_key (UNIQUE en DB)."""
    s = models.CmsSite(
        id=_uuid.uuid4(),
        site_key=site_key,
        name=f"Site {site_key}",
        base_path=f"/{site_key}",
        is_active=True,
        sede_id=sede_id,
    )
    db_session.add(s)
    db_session.flush()
    return s


def _add_snapshot(db_session, site, captured_date, score=80, total=10):
    snap = models.CmsSeoSnapshot(
        id=_uuid.uuid4(),
        site_id=site.id,
        sede_id=site.sede_id,
        captured_date=captured_date,
        captured_at=dt.datetime.now(dt.timezone.utc),
        average_score=score,
        total_pages=total,
        pages_with_errors=1,
        critical_issues=0,
        by_severity_json={"warning": 2},
    )
    db_session.add(snap)
    db_session.flush()
    return snap


# ── CRUD-direct (sin HTTP stack) ───────────────────────────────────


class TestF07ListSeoSnapshotsCRUD:
    def test_list_returns_rows_ordered_desc(self, db_session):
        admin, _, sede = _seed(db_session, "cmsF07desc@example.com")
        site = _seed_site(db_session, "f07desc", sede_id=sede.id)

        _add_snapshot(db_session, site, dt.date(2026, 7, 1), score=70)
        _add_snapshot(db_session, site, dt.date(2026, 7, 3), score=90)
        _add_snapshot(db_session, site, dt.date(2026, 7, 2), score=80)

        rows, total = list_seo_snapshots(db_session, site_id=site.id)
        assert total == 3
        # Ordenados DESC por captured_date
        assert [r.captured_date for r in rows] == [
            dt.date(2026, 7, 3),
            dt.date(2026, 7, 2),
            dt.date(2026, 7, 1),
        ]

    def test_pagination_respects_total(self, db_session):
        admin, _, sede = _seed(db_session, "cmsF07pag@example.com")
        site = _seed_site(db_session, "f07pag", sede_id=sede.id)

        for d in [dt.date(2026, 6, 1), dt.date(2026, 6, 2), dt.date(2026, 6, 3)]:
            _add_snapshot(db_session, site, d)

        rows, total = list_seo_snapshots(db_session, site_id=site.id, limit=2, offset=0)
        assert total == 3
        assert len(rows) == 2

        rows_page2, total2 = list_seo_snapshots(db_session, site_id=site.id, limit=2, offset=2)
        assert total2 == 3
        assert len(rows_page2) == 1

    def test_filter_by_site_id_excludes_other_sites(self, db_session):
        admin, _, sede = _seed(db_session, "cmsF07filt@example.com")
        site_a = _seed_site(db_session, "f07a", sede_id=sede.id)
        site_b = _seed_site(db_session, "f07b", sede_id=sede.id)

        _add_snapshot(db_session, site_a, dt.date(2026, 7, 1), score=50)
        _add_snapshot(db_session, site_b, dt.date(2026, 7, 1), score=99)

        rows_a, total_a = list_seo_snapshots(db_session, site_id=site_a.id)
        assert total_a == 1
        assert rows_a[0].site_id == site_a.id

        rows_b, total_b = list_seo_snapshots(db_session, site_id=site_b.id)
        assert total_b == 1
        assert rows_b[0].site_id == site_b.id

    def test_empty_when_no_snapshots(self, db_session):
        admin, _, sede = _seed(db_session, "cmsF07empty@example.com")
        site = _seed_site(db_session, "f07empty", sede_id=sede.id)

        rows, total = list_seo_snapshots(db_session, site_id=site.id)
        assert total == 0
        assert rows == []


# ── API endpoints ─────────────────────────────────────────────────


class TestF07SeoSnapshotsEndpoint:
    def test_returns_200_for_existing_site(self, client, db_session):
        admin, _, sede = _seed(db_session, "cmsF07ep@example.com")
        # Admin tiene sede; el site que crearemos tendra sede_id asignado.
        site = _seed_site(db_session, "f07ep", sede_id=sede.id)

        headers = auth_headers(client, email="cmsF07ep@example.com")
        resp = client.get(f"/api/cms/v2/sites/{site.site_key}/seo-snapshots", headers=headers)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)

    def test_404_for_nonexistent_site(self, client, db_session):
        admin, _, _ = _seed(db_session, "cmsF07404@example.com")
        headers = auth_headers(client, email="cmsF07404@example.com")
        resp = client.get(
            "/api/cms/v2/sites/nonexistent-site-f07/seo-snapshots",
            headers=headers,
        )
        assert resp.status_code == 404

    def test_pagination_params_respected(self, client, db_session):
        admin, _, sede = _seed(db_session, "cmsF07qp@example.com")
        site = _seed_site(db_session, "f07qp", sede_id=sede.id)

        headers = auth_headers(client, email="cmsF07qp@example.com")
        resp = client.get(
            f"/api/cms/v2/sites/{site.site_key}/seo-snapshots?skip=0&limit=10",
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["skip"] == 0
        assert data["limit"] == 10


# ── Schema-level ──────────────────────────────────────────────────


class TestF07Schema:
    def test_seo_snapshot_read_roundtrips_from_orm(self):
        from backend import models
        from backend.schemas import CmsSeoSnapshotRead

        fake = models.CmsSeoSnapshot(
            id=_uuid.uuid4(),
            site_id=_uuid.uuid4(),
            sede_id=None,
            captured_date=dt.date(2026, 7, 23),
            captured_at=dt.datetime.now(dt.timezone.utc),
            average_score=85,
            total_pages=12,
            pages_with_errors=3,
            critical_issues=1,
            by_severity_json={"warning": 2, "error": 1},
        )
        read = CmsSeoSnapshotRead.model_validate(fake, from_attributes=True)
        assert read.average_score == 85
        assert read.total_pages == 12
        assert read.pages_with_errors == 3
        assert read.critical_issues == 1
        assert read.by_severity_json == {"warning": 2, "error": 1}
