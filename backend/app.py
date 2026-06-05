import logging
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.api import (
    academy,
    academy_core,
    admin,
    agenda,
    agenda_core,
    agents,
    auth_v3,
    analytics,
    auth,
    auth_v2,
    chat,
    cms,
    cms_v2,
    community,
    content,
    crm,
    crm_core,
    dashboard,
    donations,
    evangelism,
    finance,
    governance,
    graph,
    kernel,
    messaging,
    prayer,
    projects,
    proyectos,
    public,
    spiritual_life,
    support,
    system,
    tables,
    workspace,
)
from backend.core.config import get_settings
from backend.core.logging import request_id_middleware
from backend.core.security_headers import mount_security_headers
from backend.middleware.module_isolation import register_module_isolation

logging.basicConfig(level=logging.INFO)  # Fallback; configure_logging() in core/logging overrides
logger = logging.getLogger("CCF-Core")

settings = get_settings()

ROUTER_REGISTRY = [
    (auth_v3.router, "/api", ["Auth v3"]),
    (auth.router, "/api/auth", ["auth"]),
    (auth_v2.router, "/api/auth", ["Auth v2"]),
    (projects.router, "/api/projects", ["projects"]),
    (kernel.router, "/api", ["kernel"]),
    (proyectos.router, "/api", ["Proyectos v2"]),
    (academy.router, "/api/academy", ["academy"]),
    (academy_core.router, "/api", ["Academy v2"]),
    (crm.router, "/api/crm", ["crm"]),
    (crm_core.router, "/api", ["CRM v2"]),
    (agenda.router, "/api", ["agenda"]),
    (agenda_core.router, "/api", ["Agenda v2"]),
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
    (finance.router, "/api", ["finance"]),
    (donations.router, "/api", ["donations"]),
    (governance.router, "/api", ["governance"]),
    (chat.router, "/api", ["chat"]),
    (messaging.router, "/api", ["messaging"]),
    (support.router, "/api/support", ["support"]),
    (spiritual_life.router, "/api", ["spiritual_life"]),
    (graph.router, "/api", ["graph"]),
    (community.router, "/api", ["community"]),
    (prayer.router, "/api/prayer", ["prayer"]),
    (analytics.router, "/api", ["analytics"]),
    (dashboard.router, "/api", ["dashboard"]),
    (tables.router, "/api", ["tables"]),
]


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        os.makedirs(settings.uploads_dir, exist_ok=True)
    except PermissionError:
        logger.warning(
            "Unable to create uploads directory %s; continuing without it",
            settings.uploads_dir,
        )

    env = settings.environment.lower()
    if env in {"test", "testing", "ci"}:
        logger.info("Skipping Alembic migrations during tests.")
        yield
        return
    if settings.run_startup_schema_fixes:
        # Run outstanding Alembic migrations (idempotent, fast when up-to-date)
        # FAIL HARD: if migrations cannot run, the app must not start
        from pathlib import Path

        from alembic import command
        from alembic.config import Config

        alembic_ini = Path(__file__).resolve().parent.parent / "alembic.ini"
        if alembic_ini.exists():
            alembic_cfg = Config(str(alembic_ini))
            alembic_cfg.set_main_option("sqlalchemy.url", settings.database_url)
            command.upgrade(alembic_cfg, "head")
            logger.info("Alembic migrations verified/applied.")
        else:
            logger.error("alembic.ini not found — cannot verify schema. App will not start.")
            raise RuntimeError("alembic.ini not found; database migrations cannot run")
    else:
        logger.info(
            "Startup schema fixes disabled; skipping Alembic migration check on boot."
        )

    # Register all agent tools after the schema is migrated.
    try:
        from backend.services.tool_registry import register_all_tools

        registry = register_all_tools()
        logger.info("Agent tools registered: %d tools", registry.count)
    except Exception as exc:
        logger.warning("Tool registration failed: %s", exc)

    # Register event consumers.
    try:
        from backend.services.event_consumers import register_all_consumers

        consumers = register_all_consumers()
        logger.info("Event consumers registered: %d handlers", len(consumers))
    except Exception as exc:
        logger.warning("Event consumer registration failed: %s", exc)

    # Rebuild knowledge base.
    try:
        from backend.core.database import SessionLocal
        from backend.services.knowledge_base import KnowledgeIndexer

        db = SessionLocal()
        try:
            indexer = KnowledgeIndexer(db)
            stats = indexer.rebuild_all()
            db.commit()
            logger.info("Knowledge base rebuilt: %s", stats)
        finally:
            db.close()
    except Exception as exc:
        logger.warning("KB rebuild failed: %s", exc)

    yield


app = FastAPI(
    title="CCF Mesh API",
    description="Sistema de Inteligencia Ministerial El Faro",
    version="3.0.0-PRO",
    lifespan=lifespan,
)

mount_security_headers(app)

# Request ID tracking — every request gets a unique ID
app.middleware("http")(request_id_middleware)

# Module isolation — if a module fails, it doesn't take down the whole server
register_module_isolation(app)


@app.middleware("http")
async def quality_assurance_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    # X-Process-Time exposed only in local/dev for debugging
    if settings.environment.lower() in {"local", "development", "dev"}:
        response.headers["X-Process-Time"] = str(time.time() - start_time)
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, (StarletteHTTPException, RequestValidationError)):
        raise exc

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

app.mount(
    "/api/static",
    StaticFiles(directory=settings.uploads_dir, check_dir=False),
    name="static",
)

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
