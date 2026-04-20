from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import time
import logging
import os

from backend.api import auth, projects, academy, crm, workspace, system, cms, content, agents, admin, finance, donations, governance, messaging, support, spiritual_life, graph, cms_v2
from backend.core.config import get_settings
from backend.core.database import engine, Base
from backend.services.automation_engine import engine as automation_engine

# Configuración de Logging Ministerial
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CCF-Core")

settings = get_settings()
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="CCF Mesh API",
    description="Sistema de Inteligencia Ministerial El Faro",
    version="3.0.0-PRO"
)

# 1. Calidad: Middleware de Rendimiento y Seguridad
@app.middleware("http")
async def quality_assurance_middleware(request: Request, call_next):
    start_time = time.time()
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        return response
    except Exception as e:
        logger.error(f"CRITICAL ERROR: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Error interno en el servidor ministerial", "trace": str(e)}
        )

# 2. Configuración CORS Total para Desarrollo (Calidad de Conexión)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Permitir todos los orígenes en desarrollo para asegurar conexión
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Servir archivos estáticos
uploads_dir = settings.uploads_dir
if not os.path.exists(uploads_dir):
    os.makedirs(uploads_dir)
app.mount("/api/static", StaticFiles(directory=uploads_dir), name="static")

@app.on_event("startup")
async def startup_event():
    automation_engine.start()
    # Run safe schema migrations (ADD COLUMN IF NOT EXISTS)
    _run_startup_migrations()

def _run_startup_migrations():
    """Applies incremental schema changes without Alembic."""
    from sqlalchemy import text
    from backend.core.database import SessionLocal
    db = SessionLocal()
    try:
        migrations = [
            # crm_tasks: add category column for pastoral task categorization
            "ALTER TABLE crm_tasks ADD COLUMN IF NOT EXISTS category VARCHAR(100) DEFAULT 'Pastoral'",
            # crm_tasks: normalize old status values for frontend compatibility
            "UPDATE crm_tasks SET status = 'pending' WHERE status = 'todo'",
            "UPDATE crm_tasks SET priority = 'medium' WHERE priority = 'normal'",
            # cms v2 bootstrap: create default FARO site and main menu
            "INSERT INTO cms_sites (site_key, name, base_path, is_active, created_at, updated_at) SELECT 'faro', 'FARO', '/faro', true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP WHERE NOT EXISTS (SELECT 1 FROM cms_sites WHERE site_key = 'faro')",
            "INSERT INTO cms_menus (site_id, menu_key, name, is_active, created_at, updated_at) SELECT id, 'main', 'Menu principal', true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP FROM cms_sites WHERE site_key = 'faro' AND NOT EXISTS (SELECT 1 FROM cms_menus m WHERE m.site_id = cms_sites.id AND m.menu_key = 'main')",
        ]
        for sql in migrations:
            try:
                db.execute(text(sql))
            except Exception as e:
                logger.warning(f"Migration skipped: {sql[:60]}... — {e}")
        db.commit()
        logger.info("✅ Startup migrations applied.")
    except Exception as e:
        logger.error(f"Migration error: {e}")
    finally:
        db.close()

@app.on_event("shutdown")
def shutdown_event():
    automation_engine.stop()

# Montaje de Routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(projects.router, prefix="/api/projects", tags=["projects"])
app.include_router(academy.router, prefix="/api/academy", tags=["academy"])
app.include_router(crm.router, prefix="/api/crm", tags=["crm"])
app.include_router(workspace.router, prefix="/api/workspace", tags=["workspace"])
app.include_router(system.router, prefix="/api/system", tags=["system"])
app.include_router(cms.router, prefix="/api")
app.include_router(cms_v2.router, prefix="/api")
app.include_router(content.router, prefix="/api")
app.include_router(agents.router, prefix="/api")
app.include_router(agents.analytics_router, prefix="/api")
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(finance.router, prefix="/api", tags=["finance"])
app.include_router(donations.router, prefix="/api", tags=["donations"])
app.include_router(governance.router, prefix="/api", tags=["governance"])
app.include_router(messaging.router, prefix="/api", tags=["messaging"])
app.include_router(support.router, prefix="/api/support", tags=["support"])
app.include_router(spiritual_life.router, prefix="/api", tags=["spiritual_life"])
app.include_router(graph.router, prefix="/api", tags=["graph"])


@app.get("/")
def read_root():
    return {
        "status": "online",
        "message": "CCF Mesh API is running",
        "ministerio": "CCF El Faro",
        "engine": "Optimus 3.0-Quality",
        "uptime": True
    }

@app.get("/healthz")
def health_check():
    return {"status": "ok", "version": "3.0.0-PRO"}
