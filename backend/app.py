from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend import crud
from backend.api import (
    academy,
    agents as agents_router,
    analytics as analytics_router,
    auth as auth_router,
    cms,
    content,
    crm,
    dashboard,
    governance,
    messaging,
    system,
    prayer,
    support,
    donations,
    projects,
    community,
    finance,
    spiritual_life,
    assets,
    graph,
    workspace,
)
from backend.core.config import get_settings
from backend.core.database import Base, SessionLocal, engine
from backend.core.telemetry import configure_telemetry
from backend.core.security_headers import mount_security_headers
from backend.database_scripts import create_stored_procedures


settings = get_settings()


from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
import logging

log = logging.getLogger(__name__)

from backend.services.scheduler import start_background_scheduler
from backend.core.websockets import ws_manager
from fastapi import WebSocket, WebSocketDisconnect


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Base.metadata.create_all(bind=engine)
    yield

def create_application() -> FastAPI:
    app = FastAPI(
        title="CCF MESH Ecosystem API",
        description="""
        API de Alto Rendimiento para el Ecosistema CCF.
        
        **M??dulos Incluidos:**
        * **Academy:** Gesti??n de LMS, Cursos y Certificados.
        * **CRM:** Control de Membres??a, Familias y Consolidaci??n.
        * **Finance:** Treasury, Ofrendas y Donaciones.
        * **Governance:** Auditor??a, RBAC y Configuraci??n.
        """,
        version="2.1.0",
        contact={
            "name": "Soporte T??cnico CCF",
            "url": "https://ccf.la/support",
            "email": "tecnico@ccf.la",
        },
        license_info={
            "name": "CCF Proprietary",
        },
        lifespan=lifespan,
    )

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
        log.error(f"Database error on {request.url.path}: {exc}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Error de base de datos. Por favor contacte al soporte t??cnico.", "type": "database_error"}
        )

    @app.exception_handler(IntegrityError)
    async def integrity_exception_handler(request: Request, exc: IntegrityError):
        return JSONResponse(
            status_code=409,
            content={"detail": "Conflicto de datos: El registro ya existe o viola una restricci??n de integridad.", "type": "integrity_error"}
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        return JSONResponse(
            status_code=400,
            content={"detail": str(exc), "type": "validation_error"}
        )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    uploads_dir = settings.uploads_dir
    os.makedirs(uploads_dir, exist_ok=True)
    app.mount("/static", StaticFiles(directory=uploads_dir), name="static")

    # Routers Ministerial v3.9 (Activos y Sincronizados)
    app.include_router(system.router, prefix="/api/system")
    app.include_router(auth_router.router, prefix="/api", tags=["auth"])
    app.include_router(analytics_router.router, prefix="/api", tags=["analytics"])
    app.include_router(cms.router, prefix="/api")
    app.include_router(content.router, prefix="/api")
    app.include_router(dashboard.router, prefix="/api", tags=["dashboard"])
    app.include_router(crm.router, prefix="/api", tags=["crm"])
    app.include_router(finance.router, prefix="/api")
    app.include_router(spiritual_life.router, prefix="/api")
    app.include_router(assets.router, prefix="/api")
    app.include_router(workspace.router, prefix="/api")
    
    app.include_router(academy.router, prefix="/api/academy", tags=["academy"])
    app.include_router(messaging.router, prefix="/api/messaging", tags=["messaging"])
    app.include_router(agents_router.router, prefix="/api", tags=["agents"])
    app.include_router(prayer.router, prefix="/api/prayer", tags=["prayer"])
    app.include_router(support.router, prefix="/api/support", tags=["support"])
    app.include_router(donations.router, prefix="/api")
    app.include_router(projects.router, prefix="/api/projects", tags=["projects"])
    app.include_router(community.router, prefix="/api")
    app.include_router(governance.router, prefix="/api")
    app.include_router(graph.router, prefix="/api")

    if settings.enable_otel:
        configure_telemetry(app, engine)
    mount_security_headers(app)

    @app.websocket("/ws/{user_id}")
    async def websocket_endpoint(websocket: WebSocket, user_id: str):
        await ws_manager.connect(websocket, user_id)
        try:
            while True:
                data = await websocket.receive_text()
                # Handle incoming messages from client if needed
                await ws_manager.send_personal_message({"type": "ACK", "message": "Received"}, user_id)
        except WebSocketDisconnect:
            ws_manager.disconnect(websocket, user_id)

    # Servicios secundarios desactivados para estabilidad ministerial v3.9
    # start_background_scheduler()
    
    return app


app = create_application()
