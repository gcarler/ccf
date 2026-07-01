"""Cron-friendly scheduler that publishes CMS pages whose scheduled_at has passed.

Usage:
    python -m backend.scheduler              # runs once, logs to stdout
    python -m backend.scheduler --dry-run    # preview without publishing

Designed for crontab (every minute):
    * * * * * cd /root/ccf && .venv/bin/python -m backend.scheduler >> /root/ccf/logs/scheduler.log 2>&1
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timezone
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


def _find_scheduled_pages(db_session) -> list[Any]:
    """Find all pages with status='scheduled' whose scheduled_at <= now."""
    from backend import models

    now = datetime.now(timezone.utc).isoformat()
    rows = (
        db_session.query(models.CmsPage)
        .filter(models.CmsPage.status == "scheduled")
        .all()
    )
    due: list[Any] = []
    for page in rows:
        seo = page.seo_json or {}
        raw = seo.get("_scheduled_at")
        if not raw:
            continue
        try:
            scheduled = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if scheduled <= datetime.now(timezone.utc):
                due.append(page)
        except (ValueError, TypeError):
            log.warning("Page %s (%s) has invalid _scheduled_at: %r", page.id, page.slug, raw)
            continue
    return due


def _publish_page(db_session, page, dry_run: bool) -> bool:
    """Publish a single scheduled page. Returns True on success."""
    from backend.crud.cms import transition_cms_page_status

    slug = page.slug or "(no slug)"
    if dry_run:
        log.info("[DRY-RUN] Would publish page %s (%s)", page.id, slug)
        return True

    try:
        # user_id=None because this is an automated action (system)
        result = transition_cms_page_status(
            db_session, page, action="publish", user_id=None,
            notes="Auto-published by scheduler",
        )
        if result:
            log.info("Published page %s (%s)", page.id, slug)
            return True
        log.error("Failed to publish page %s (%s) — transition returned None", page.id, slug)
        return False
    except Exception as exc:
        log.error("Error publishing page %s (%s): %s", page.id, slug, exc)
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="CMS scheduled-publishing worker")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be published")
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
        due = _find_scheduled_pages(session)

        if not due:
            log.info("No due pages found")
            return 0

        log.info("Found %d due page(s)", len(due))
        success = 0
        for page in due:
            if _publish_page(session, page, dry_run=args.dry_run):
                success += 1

        if not args.dry_run:
            session.commit()

        log.info("Done: %d/%d published", success, len(due))
        return 0 if success == len(due) else 1
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
