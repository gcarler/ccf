"""Cron-friendly scheduler for CMS scheduled publish + auto-archive.

Usage:
    python -m backend.scheduler              # runs once, logs to stdout
    python -m backend.scheduler --dry-run    # preview without publishing

Designed for crontab (every minute):
    * * * * * cd /root/ccf && .venv/bin/python -m backend.scheduler >> /root/ccf/logs/scheduler.log 2>&1

Behavior (2026-07-06 refactor):
  - ``CmsPage.publish_at`` + ``status='scheduled'`` → transiciona a
    ``published`` cuando llega el momento.
  - ``CmsPage.expires_at`` + ``status='published'`` → transiciona a
    ``archived`` cuando llega el momento.
  - ``CmsPost.expires_at`` + ``status='published'`` → transiciona a
    ``archived`` (posts no tienen ``scheduled`` como estado intermedio
    porque ``published_at`` opera como publish).

El cruft legacy ``seo_json['_scheduled_at']`` (eliminado por la migration
``20260706_0001_cms_schedule``) ya no se lee aquí.

Cada transición se registra en ``CmsPublishLog`` con
``actor_persona_id=None`` por convención (automatización). El heartbeat
final loggea counts para visibilidad operacional y métricas básicas.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Any

# Ensure the project root is on sys.path so imports resolve when running as -m
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

log = logging.getLogger("ccf.scheduler")


def _setup_logging() -> None:
    level = logging.INFO
    fmt = "%(asctime)s [%(levelname)s] %(message)s"
    logging.basicConfig(stream=sys.stdout, level=level, format=fmt, datefmt="%Y-%m-%d %H:%M:%S")


def _load_settings() -> Any:
    """Load settings without starting the full FastAPI app.

    Uses pydantic-settings from the project config, but avoids
    importing main.py (which starts uvicorn hooks).
    """
    from backend.core.config import get_settings
    return get_settings()


def _get_db_session(settings: Any):
    """Build a standalone DB session (not tied to a request)."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    url = settings.database_url
    if url.startswith("sqlite"):
        engine = create_engine(url, connect_args={"check_same_thread": False})
    else:
        engine = create_engine(url)
    return Session(engine), engine


def _run_scheduling_pass(db_session, dry_run: bool) -> dict[str, int | dict]:
    """Delega a ``crud.process_due_content`` + ``capture_daily_seo_snapshots``
    + ``cleanup_old_publish_logs``.

    La capa CRUD centraliza las queries + transiciones + audit logging;
    esta función es un orquestador thin que sólo materializa el contexto
    standalone (sin request) e imprime un heartbeat legible.

    Returns a dict shaped like::

        {
          "pages_published": int, "pages_archived": int, "posts_archived": int,
          "seo": {"snapshots": int, "skipped": int, "sites_visited": int},
          "publish_logs_purged": int,
        }

    El dict anidado ``seo`` se separa del flat-list de counts
    scheduler para que el short-circuit ``all(value == 0)`` de
    ``main()`` no considere ruido a las snapshots idempotentes (el
    día siguiente a uno con captura, ``skipped`` vale N>0 y un flat
    check lo consideraría "trabajo realizado").

    F-08 (errorescms.md): ``publish_logs_purged`` purga logs de
    auditoria operacional con más de 90 días (default). El cron de
    cada minuto lo corre (idempotente: si no hay logs viejos,
    retorna 0 sin afectar métricas).

    F-10 (errorescms.md): ``orphan_media_archived`` archiva media items
    activos de cada sede que no esten referenciados por ninguna seccion
    de los sites de esa sede.  Cron-suave: opcional via env
    ``CMS_ORPHAN_MEDIA_CLEANUP=1`` (default off para no introducir
    mutaciones adicionales en el cron de cada minuto sin opt-in).
    """
    from backend.crud.cms import (
        capture_daily_seo_snapshots,
        cleanup_old_publish_logs,
        cleanup_orphan_cms_media_scheduled,
        process_due_content,
    )

    counts = process_due_content(db_session, dry_run=dry_run)
    snapshot_counts = capture_daily_seo_snapshots(
        db_session, dry_run=dry_run
    )
    # F-08: limpieza periodica de CmsPublishLog (retention 90 dias default)
    publish_logs_purged = cleanup_old_publish_logs(
        db_session, dry_run=dry_run
    )
    if not dry_run:
        db_session.commit()
    counts["seo"] = {
        "snapshots": snapshot_counts["snapshots_count"],
        "skipped": snapshot_counts["skipped_count"],
        "sites_visited": snapshot_counts["sites_captured"],
    }
    counts["publish_logs_purged"] = publish_logs_purged

    # F-10: cleanup de media items huerfanos por sede (opt-in via env).
    # Default OFF: el cron de cada minuto no debe introducir mutaciones
    # adicionales sin opt-in explicito del operador.  El endpoint API
    # (``DELETE /cms/media/cleanup``) es la via primaria para limpiar.
    orphan_media_archived = _maybe_run_orphan_media_cleanup(
        db_session, dry_run=dry_run
    )
    counts["orphan_media_archived"] = orphan_media_archived
    return counts


def _maybe_run_orphan_media_cleanup(db_session, *, dry_run: bool) -> int:
    """F-10 (errorescms.md): archiva media huerfano por sede, opt-in.

    El cleanup itera cada ``Sede``, recolecta los ``referenced_ids`` de
    las secciones activas de sus sites via ``collect_section_media_ids``
    (helper del paquete ``api._cms_helpers``), y archiva los items
    activos no referenciados via ``cleanup_orphan_cms_media_scheduled``.

    Opt-in: si ``CMS_ORPHAN_MEDIA_CLEANUP`` no esta en ``1``/``true``,
    retorna 0 sin tocar la DB.  Esto evita que un cron de cada minuto
    mute media sin consentimiento del operador; el endpoint API sigue
    siendo la via primaria.
    """
    import os

    from backend import models

    if os.environ.get("CMS_ORPHAN_MEDIA_CLEANUP", "").lower() not in ("1", "true", "yes"):
        return 0

    from backend.api._cms_helpers import collect_section_media_ids
    from backend.crud.cms import cleanup_orphan_cms_media_scheduled

    total = 0
    sedes = db_session.query(models.Sede).all()
    for sede in sedes:
        sites = (
            db_session.query(models.CmsSite)
            .filter(models.CmsSite.sede_id == sede.id)
            .all()
        )
        referenced_ids: set[str] = set()
        for site in sites:
            sections = (
                db_session.query(models.CmsSection)
                .join(models.CmsPage, models.CmsPage.id == models.CmsSection.page_id)
                .filter(models.CmsPage.site_id == site.id)
                .filter(models.CmsSection.status != "archived")
                .filter(models.CmsSection.deleted_at.is_(None))
                .all()
            )
            for mid in collect_section_media_ids(sections):
                referenced_ids.add(mid)
        total += cleanup_orphan_cms_media_scheduled(
            db_session,
            sede_id=sede.id,
            referenced_media_ids=referenced_ids,
            dry_run=dry_run,
            permanent=False,
        )
    return total


def main() -> int:
    parser = argparse.ArgumentParser(description="CMS scheduled-publishing + auto-archive worker")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be published/archived")
    args = parser.parse_args()

    _setup_logging()
    log.info("Scheduler started (dry_run=%s)", args.dry_run)

    try:
        settings = _load_settings()
    except Exception as exc:
        log.error("Failed to load settings: %s", exc)
        return 1

    session = None
    try:
        session, engine = _get_db_session(settings)
        counts = _run_scheduling_pass(session, dry_run=args.dry_run)

        # Quiet check: solo se considera "trabajo realizado" si al menos
        # uno de los counts planos o el sub-conteo ``seo.snapshots`` es
        # positivo. ``seo.skipped`` es idempotente (el día siguiente a
        # una captura) y no debe disparar el heartbeat ni cada minuto.
        # ``publish_logs_purged`` (F-08) se incluye para evitar heartbeat
        # silencioso cuando el scheduler purga muchos logs viejos.
        # ``orphan_media_archived`` (F-10) se incluye idem.
        seo = counts.get("seo") or {}
        work_done = (
            counts.get("pages_published", 0) > 0
            or counts.get("pages_archived", 0) > 0
            or counts.get("posts_archived", 0) > 0
            or seo.get("snapshots", 0) > 0
            or counts.get("publish_logs_purged", 0) > 0
            or counts.get("orphan_media_archived", 0) > 0
        )
        if not work_done:
            log.info("No due content found")
            return 0

        log.info(
            "Scheduler run: pages_published=%d pages_archived=%d "
            "posts_archived=%d seo_snapshots=%d publish_logs_purged=%d "
            "orphan_media_archived=%d",
            counts["pages_published"],
            counts["pages_archived"],
            counts["posts_archived"],
            seo.get("snapshots", 0),
            counts.get("publish_logs_purged", 0),
            counts.get("orphan_media_archived", 0),
        )
        return 0
    except Exception as exc:
        log.error("Unhandled error: %s", exc)
        if session:
            session.rollback()
        return 1
    finally:
        if session:
            session.close()
        if "engine" in locals():
            engine.dispose()


if __name__ == "__main__":
    sys.exit(main())
