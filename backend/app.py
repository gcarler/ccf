from contextlib import asynccontextmanager
import logging
import os
import time

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.api import (
    academy,
    agenda,
    admin,
    agents,
    analytics,
    assets,
    auth,
    cms,
    cms_v2,
    community,
    content,
    crm,
    dashboard,
    donations,
    evangelism,
    finance,
    governance,
    graph,
    messaging,
    prayer,
    projects,
    public,
    spiritual_life,
    support,
    system,
    workspace,
)
from backend.core.config import get_settings
from backend.core.security_headers import mount_security_headers


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CCF-Core")

settings = get_settings()

ROUTER_REGISTRY = [
    (auth.router, "/api/auth", ["auth"]),
    (agenda.router, "/api", ["agenda"]),
    (projects.router, "/api/projects", ["projects"]),
    (academy.router, "/api/academy", ["academy"]),
    (crm.router, "/api/crm", ["crm"]),
    (evangelism.router, "/api/evangelism", ["evangelism"]),
    (public.router, "/api/public", ["public"]),
    (workspace.router, "/api/workspace", ["workspace"]),
    (system.router, "/api/system", ["system"]),
    (cms.router, "/api", None),
    (cms_v2.router, "/api", None),
    (content.router, "/api", None),
    (agents.router, "/api", None),
    (agents.analytics_router, "/api/agents", None),
    (admin.router, "/api/admin", ["admin"]),
    (assets.router, "/api", None),
    (finance.router, "/api", ["finance"]),
    (donations.router, "/api", ["donations"]),
    (governance.router, "/api", ["governance"]),
    (messaging.router, "/api", ["messaging"]),
    (support.router, "/api/support", ["support"]),
    (spiritual_life.router, "/api", ["spiritual_life"]),
    (graph.router, "/api", ["graph"]),
    (community.router, "/api", ["community"]),
    (prayer.router, "/api/prayer", ["prayer"]),
    (analytics.router, "/api", ["analytics"]),
    (dashboard.router, "/api", ["dashboard"]),
]


def _run_data_migrations() -> None:
    """Migrate existing JSON-blob testimonials/announcements into dedicated tables."""
    import json

    from sqlalchemy import text

    from backend.core.database import SessionLocal

    db = SessionLocal()
    try:
        # Migrate testimonials
        existing = db.execute(
            text("SELECT COUNT(*) FROM testimonials")
        ).scalar() or 0
        if existing == 0:
            page = db.execute(
                text("SELECT content FROM page_contents WHERE page_key = 'faro_testimonials_feed'")
            ).fetchone()
            if page and page[0]:
                try:
                    items = json.loads(page[0])
                    if isinstance(items, list):
                        for item in items:
                            if not isinstance(item, dict):
                                continue
                            db.execute(
                                text(
                                    "INSERT INTO testimonials (id, content, emotion, media_type, media_url, image_url, video_url, podcast_url, is_approved, show_on_home, author_id, created_at) "
                                    "VALUES (:id, :content, :emotion, :media_type, :media_url, :image_url, :video_url, :podcast_url, :is_approved, :show_on_home, :author_id, :created_at)"
                                ),
                                {
                                    "id": item.get("id"),
                                    "content": item.get("content", ""),
                                    "emotion": item.get("emotion", "Gratitud"),
                                    "media_type": item.get("media_type", "text"),
                                    "media_url": item.get("media_url"),
                                    "image_url": item.get("image_url"),
                                    "video_url": item.get("video_url"),
                                    "podcast_url": item.get("podcast_url"),
                                    "is_approved": 1 if item.get("is_approved") else 0,
                                    "show_on_home": 1 if item.get("show_on_home") else 0,
                                    "author_id": item.get("author_id"),
                                    "created_at": item.get("created_at"),
                                },
                            )
                        db.commit()
                        logger.info("Migrated %d testimonials from JSON to dedicated table.", len(items))
                except (json.JSONDecodeError, Exception) as exc:
                    logger.warning("Could not migrate testimonials: %s", exc)

        # Migrate announcements
        existing = db.execute(
            text("SELECT COUNT(*) FROM announcements")
        ).scalar() or 0
        if existing == 0:
            page = db.execute(
                text("SELECT content FROM page_contents WHERE page_key = 'faro_announcements_feed'")
            ).fetchone()
            if page and page[0]:
                try:
                    items = json.loads(page[0])
                    if isinstance(items, list):
                        for item in items:
                            if not isinstance(item, dict):
                                continue
                            db.execute(
                                text(
                                    "INSERT INTO announcements (id, title, content, category, is_featured, created_at) "
                                    "VALUES (:id, :title, :content, :category, :is_featured, :created_at)"
                                ),
                                {
                                    "id": item.get("id"),
                                    "title": item.get("title", ""),
                                    "content": item.get("content", ""),
                                    "category": item.get("category", "General"),
                                    "is_featured": 1 if item.get("is_active") else 0,
                                    "created_at": item.get("created_at"),
                                },
                            )
                        db.commit()
                        logger.info("Migrated %d announcements from JSON to dedicated table.", len(items))
                except (json.JSONDecodeError, Exception) as exc:
                    logger.warning("Could not migrate announcements: %s", exc)
    except Exception as exc:
        logger.error("Data migration error: %s", exc)
    finally:
        db.close()


def _run_startup_migrations() -> None:
    """Apply startup schema patches only when explicitly enabled."""
    from sqlalchemy import text

    from backend.core.database import SessionLocal

    db = SessionLocal()
    try:
        # SQLite-safe migrations: ALTER TABLE without IF NOT EXISTS
        migrations = [
            # Add category column to crm_tasks if missing
            "ALTER TABLE crm_tasks ADD COLUMN category VARCHAR(100) DEFAULT 'Pastoral'",
            "UPDATE crm_tasks SET status = 'pending' WHERE status = 'todo'",
            "UPDATE crm_tasks SET priority = 'medium' WHERE priority = 'normal'",
            # Add fixed_date column to crm_events if missing
            "ALTER TABLE crm_events ADD COLUMN fixed_date DATETIME",
            (
                "CREATE TABLE IF NOT EXISTS support_tickets ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, subject VARCHAR(200) NOT NULL, "
                "description TEXT, status VARCHAR(20) DEFAULT 'open', created_at DATETIME, updated_at DATETIME, "
                "FOREIGN KEY(user_id) REFERENCES users(id))"
            ),
            (
                "CREATE TABLE IF NOT EXISTS spiritual_milestones ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, person_id INTEGER NOT NULL, type VARCHAR(100) NOT NULL, "
                "event_date DATE NOT NULL, minister_id INTEGER, notes TEXT, created_at DATETIME, "
                "FOREIGN KEY(minister_id) REFERENCES users(id))"
            ),
            (
                "CREATE TABLE IF NOT EXISTS community_board_cards ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, column_id VARCHAR(50), title VARCHAR(200) NOT NULL, "
                "body TEXT, position INTEGER DEFAULT 0, created_at DATETIME)"
            ),
            (
                "CREATE TABLE IF NOT EXISTS funds ("
                "fund_id INTEGER PRIMARY KEY AUTOINCREMENT, name VARCHAR(120) NOT NULL, "
                "description TEXT, is_public BOOLEAN DEFAULT 0, current_balance FLOAT DEFAULT 0.0, "
                "target_amount FLOAT, created_at DATETIME)"
            ),
            (
                "CREATE TABLE IF NOT EXISTS member_roles ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, member_id INTEGER NOT NULL, role_id INTEGER NOT NULL, "
                "created_at DATETIME, FOREIGN KEY(member_id) REFERENCES members(id), "
                "FOREIGN KEY(role_id) REFERENCES role_definitions(id))"
            ),
            (
                "INSERT INTO cms_sites (site_key, name, base_path, is_active, created_at, updated_at) "
                "SELECT 'faro', 'FARO', '/faro', true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP "
                "WHERE NOT EXISTS (SELECT 1 FROM cms_sites WHERE site_key = 'faro')"
            ),
            (
                "INSERT INTO cms_menus (site_id, menu_key, name, is_active, created_at, updated_at) "
                "SELECT id, 'main', 'Menu principal', true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP "
                "FROM cms_sites WHERE site_key = 'faro' AND NOT EXISTS "
                "(SELECT 1 FROM cms_menus m WHERE m.site_id = cms_sites.id AND m.menu_key = 'main')"
            ),
            # CMS media columns
            "ALTER TABLE cms_media_items ADD COLUMN filename VARCHAR(255)",
            "ALTER TABLE cms_media_items ADD COLUMN mime_type VARCHAR(120)",
            "ALTER TABLE cms_media_items ADD COLUMN file_size INTEGER DEFAULT 0",
            # CMS testimonial media columns
            "ALTER TABLE testimonials ADD COLUMN media_type VARCHAR(30) DEFAULT 'text'",
            "ALTER TABLE testimonials ADD COLUMN media_url VARCHAR(500)",
            "ALTER TABLE testimonials ADD COLUMN image_url VARCHAR(500)",
            "ALTER TABLE testimonials ADD COLUMN video_url VARCHAR(500)",
            "ALTER TABLE testimonials ADD COLUMN podcast_url VARCHAR(500)",
            # CMS section type column
            "ALTER TABLE cms_sections ADD COLUMN section_type VARCHAR(50)",
            # Dedicated announcements / testimonials tables
            (
                "CREATE TABLE IF NOT EXISTS announcements ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, title VARCHAR(200) NOT NULL, "
                "content TEXT NOT NULL, category VARCHAR(100) DEFAULT 'General', "
                "image_url VARCHAR(500), is_featured BOOLEAN DEFAULT 0, "
                "published_at DATETIME, created_at DATETIME)"
            ),
            (
                "CREATE TABLE IF NOT EXISTS testimonials ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, content TEXT NOT NULL, "
                "emotion VARCHAR(50) DEFAULT 'Gratitud', media_type VARCHAR(30) DEFAULT 'text', "
                "media_url VARCHAR(500), image_url VARCHAR(500), video_url VARCHAR(500), podcast_url VARCHAR(500), "
                "is_approved BOOLEAN DEFAULT 0, "
                "show_on_home BOOLEAN DEFAULT 0, author_id INTEGER, created_at DATETIME, "
                "FOREIGN KEY(author_id) REFERENCES users(id))"
            ),
            "DROP VIEW IF EXISTS view_user_workload",
            (
                "CREATE VIEW view_user_workload AS "
                "SELECT "
                "u.id AS user_id, "
                "u.username AS full_name, "
                "u.username, "
                "COUNT(t.id) AS total_tasks, "
                "SUM(CASE WHEN t.status IN ('todo','in_progress','review') THEN 1 ELSE 0 END) AS open_tasks, "
                "SUM(CASE WHEN t.priority = 'urgent' AND t.status != 'done' THEN 1 ELSE 0 END) AS critical_tasks, "
                "SUM(CASE WHEN t.due_date < datetime('now') AND t.status != 'done' THEN 1 ELSE 0 END) AS overdue_tasks "
                "FROM users u "
                "LEFT JOIN project_tasks t ON t.assignee_id = u.id "
                "GROUP BY u.id, u.username"
            ),
        ]
        for sql in migrations:
            try:
                db.execute(text(sql))
            except Exception as exc:
                logger.warning("Startup schema fix skipped for %s: %s", sql[:60], exc)
        db.commit()
        logger.info("Startup schema fixes applied.")
    except Exception as exc:
        logger.error("Startup schema fix error: %s", exc)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        os.makedirs(settings.uploads_dir, exist_ok=True)
    except PermissionError:
        logger.warning("Unable to create uploads directory %s; continuing without it", settings.uploads_dir)
    if settings.run_startup_schema_fixes:
        _run_startup_migrations()
        _run_data_migrations()
    yield


app = FastAPI(
    title="CCF Mesh API",
    description="Sistema de Inteligencia Ministerial El Faro",
    version="3.0.0-PRO",
    lifespan=lifespan,
)

mount_security_headers(app)


@app.middleware("http")
async def quality_assurance_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    response.headers["X-Process-Time"] = str(time.time() - start_time)
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled request error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Error interno en el servidor ministerial"},
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials="*" not in settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/api/static", StaticFiles(directory=settings.uploads_dir, check_dir=False), name="static")

for router, prefix, tags in ROUTER_REGISTRY:
    include_kwargs = {"prefix": prefix}
    if tags:
        include_kwargs["tags"] = tags
    app.include_router(router, **include_kwargs)


@app.get("/")
def read_root():
    return {
        "status": "online",
        "message": "CCF Mesh API is running",
        "ministerio": "CCF El Faro",
        "engine": "Optimus 3.0-Quality",
        "uptime": True,
    }


@app.get("/healthz")
def health_check():
    return {"status": "ok", "version": "3.0.0-PRO"}
