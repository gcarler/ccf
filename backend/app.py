from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import time
import logging
import os

from backend.api import auth, projects, academy, crm, workspace, system, cms, content
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
app.include_router(content.router, prefix="/api")

@app.get("/")
def read_root():
    return {
        "status": "online",
        "ministerio": "CCF El Faro",
        "engine": "Optimus 3.0-Quality",
        "uptime": True
    }
