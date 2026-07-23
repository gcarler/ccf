"""F-08 (errorescms.md): limpieza periodica de CmsPublishLog.

La tabla ``cms_publish_logs`` crece indefinidamente: cada transicion de
``CmsPage`` (publish/archive/schedule) y ``CmsPost`` (archive) genera un
row. Sin cleanup, millones de logs antiguos deterioran el rendimiento
de queries de auditoria. F-08 cierra con ``cleanup_old_publish_logs``
CRUD que purga logs con ``created_at < now - retention_days``, llamado
desde el scheduler cron (cada minuto via crontab ``python -m backend.scheduler``).

``CmsPublishLog`` es un log de auditoria operacional (NO pastoral ni
transaccional); hard-delete es seguro aqui (REGLAS.md §6 solo protege
``personas`` y entidades pastorales/transaccionales).

Tests:
  1) CRUD-direct: cleanup borra logs con created_at < cutoff
  2) CRUD-direct: respeta retention_days (90 default)
  3) CRUD-direct: dry_run retorna count sin borrar
  4) CRUD-direct: retention_days custom (e.g. 30 dias)
  5) CRUD-direct: no borra logs recientes (created_at >= cutoff)
  6) Scheduler integration: _run_scheduling_pass retorna publish_logs_purged
"""
from __future__ import annotations

import datetime as dt
import uuid as _uuid

import pytest

from backend import models
from backend.crud.cms import cleanup_old_publish_logs
from backend.scheduler import _run_scheduling_pass
from tests.conftest import seed_admin


def _seed(db_session, email="cmsF08@example.com"):
    return seed_admin(db_session, email=email, password="testpass123")


def _seed_site(db_session, sede_id=None):
    """Crea un site CMS global para asociar publish logs."""
    key = f"f08-site-{_uuid.uuid4().hex[:6]}"
    s = models.CmsSite(
        id=_uuid.uuid4(),
        site_key=key,
        name=f"Site {key}",
        base_path=f"/{key}",
        is_active=True,
        sede_id=sede_id,
    )
    db_session.add(s)
    db_session.flush()
    return s


def _add_publish_log(db_session, site_id, page_id=None, *, created_at, action="publish"):
    """Inserta un CmsPublishLog con timestamp override (para tests)."""
    log = models.CmsPublishLog(
        id=_uuid.uuid4(),
        site_id=site_id,
        page_id=page_id,
        entity_type="page",
        entity_id=str(_uuid.uuid4()),
        action=action,
        from_status="draft",
        to_status="published",
        actor_persona_id=None,
        metadata_json={"source": "test"},
        created_at=created_at,
    )
    db_session.add(log)
    db_session.flush()
    return log


# ── CRUD-direct: cleanup_old_publish_logs ──────────────────────────


NOW = dt.datetime(2026, 7, 23, 12, 0, 0, tzinfo=dt.timezone.utc)


class TestF08CleanupOldPublishLogs:
    def test_purges_logs_older_than_retention(self, db_session):
        admin, _, sede = _seed(db_session, email="cmsF08purge@example.com")
        site = _seed_site(db_session, sede_id=sede.id)

        # Log viejo: 100 dias atras (mas que los 90 default)
        _add_publish_log(
            db_session,
            site_id=site.id,
            created_at=NOW - dt.timedelta(days=100),
        )
        # Log reciente: 10 dias atras (dentro de retention)
        recent_log_id = _add_publish_log(
            db_session,
            site_id=site.id,
            created_at=NOW - dt.timedelta(days=10),
        ).id
        db_session.flush()

        deleted = cleanup_old_publish_logs(
            db_session, retention_days=90, now=NOW
        )
        assert deleted == 1
        # El log reciente debe seguir
        still_there = (
            db_session.query(models.CmsPublishLog)
            .filter(models.CmsPublishLog.id == recent_log_id)
            .first()
        )
        assert still_there is not None

    def test_dry_run_returns_count_without_deleting(self, db_session):
        admin, _, sede = _seed(db_session, email="cmsF08dry@example.com")
        site = _seed_site(db_session, sede_id=sede.id)

        log_id = _add_publish_log(
            db_session,
            site_id=site.id,
            created_at=NOW - dt.timedelta(days=200),
        ).id

        count = cleanup_old_publish_logs(
            db_session, retention_days=90, dry_run=True, now=NOW
        )
        assert count == 1
        # No se borro
        still_there = (
            db_session.query(models.CmsPublishLog)
            .filter(models.CmsPublishLog.id == log_id)
            .first()
        )
        assert still_there is not None

    def test_custom_retention_days(self, db_session):
        admin, _, sede = _seed(db_session, email="cmsF08cust@example.com")
        site = _seed_site(db_session, sede_id=sede.id)

        # Log 45 dias atras — > 30 dias retention pero < 90 dias default
        _add_publish_log(
            db_session,
            site_id=site.id,
            created_at=NOW - dt.timedelta(days=45),
        )

        # Con retention=90: no se borra
        deleted_90 = cleanup_old_publish_logs(
            db_session, retention_days=90, dry_run=True, now=NOW
        )
        assert deleted_90 == 0

        # Con retention=30: se borra
        deleted_30 = cleanup_old_publish_logs(
            db_session, retention_days=30, dry_run=True, now=NOW
        )
        assert deleted_30 == 1

    def test_does_not_purge_recent_logs(self, db_session):
        admin, _, sede = _seed(db_session, email="cmsF08keep@example.com")
        site = _seed_site(db_session, sede_id=sede.id)

        # 3 logs recientes (1, 5, 89 dias atras)
        for days in [1, 5, 89]:
            _add_publish_log(
                db_session,
                site_id=site.id,
                created_at=NOW - dt.timedelta(days=days),
            )

        deleted = cleanup_old_publish_logs(
            db_session, retention_days=90, now=NOW
        )
        assert deleted == 0

    def test_empty_table_returns_zero(self, db_session):
        admin, _, sede = _seed(db_session, email="cmsF08empty@example.com")
        site = _seed_site(db_session, sede_id=sede.id)
        # Sin insertar logs

        deleted = cleanup_old_publish_logs(
            db_session, retention_days=90, now=NOW
        )
        assert deleted == 0

    def test_multiple_logs_purged_in_one_call(self, db_session):
        admin, _, sede = _seed(db_session, email="cmsF08multi@example.com")
        site = _seed_site(db_session, sede_id=sede.id)

        for days in [100, 150, 200, 300]:
            _add_publish_log(
                db_session,
                site_id=site.id,
                created_at=NOW - dt.timedelta(days=days),
            )

        deleted = cleanup_old_publish_logs(
            db_session, retention_days=90, now=NOW
        )
        assert deleted == 4


# ── Scheduler integration ─────────────────────────────────────────


class TestF08SchedulerIntegration:
    def test_scheduler_pass_includes_publish_logs_purged_key(self, db_session):
        """_run_scheduling_pass debe retornar la clave
        ``publish_logs_purged`` en el dict (F-08)."""
        admin, _, sede = _seed(db_session, email="cmsF08sched@example.com")
        # El scheduler declara dry_run=True para no hacer commit;
        # la integracion real con logs viejos requiere sacar dry_run.

        # Insertamos un log viejo para verificar que se cuenta en dry_run
        site = _seed_site(db_session, sede_id=sede.id)
        _add_publish_log(
            db_session,
            site_id=site.id,
            created_at=dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=200),
        )
        db_session.flush()

        counts = _run_scheduling_pass(db_session, dry_run=True)
        assert "publish_logs_purged" in counts
        assert isinstance(counts["publish_logs_purged"], int)
        # dry_run retorna el count de los que se purgarian; debe ser >= 1
        assert counts["publish_logs_purged"] >= 1
