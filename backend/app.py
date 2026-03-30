from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from backend.api import auth, projects, academy, crm, workspace, system, cms, content
from backend.core.config import get_settings
from backend.core.database import engine, Base
from backend.services.automation_engine import engine as automation_engine

settings = get_settings()

# Inicializar Base de Datos (SQLite)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="CCF Mesh API",
    description="Sistema de Inteligencia Ministerial El Faro",
    version="3.0.0-PRO"
)

# Configuración CORS Pro
cors_origins = settings.cors_origins or ["*"]
if "*" in cors_origins:
    cors_origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Servir archivos estáticos (Evidencias/Adjuntos)
uploads_dir = settings.uploads_dir
if not os.path.exists(uploads_dir):
    os.makedirs(uploads_dir)
app.mount("/api/static", StaticFiles(directory=uploads_dir), name="static")

# Ciclo de Vida: Automatización
@app.on_event("startup")
async def startup_event():
    # El motor de automatización despierta aquí
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
        "engine": "Optimus 3.0",
        "active_automation": True
    }
