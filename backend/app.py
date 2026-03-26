from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend import crud
from backend.api import (
    academy,
    agents as agents_router,
    analytics as analytics_router,
    auth as auth_router,
    crm,
    governance,
    messaging,
    system,
    prayer,
    support,
    donations,
    projects,
    community,
    finance,
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
        }
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
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    uploads_dir = settings.uploads_dir
    os.makedirs(uploads_dir, exist_ok=True)
    app.mount("/static", StaticFiles(directory=uploads_dir), name="static")

    # Routers - Explicitly using the router object from each module
    app.include_router(system.router)
    app.include_router(auth_router.router, tags=["auth"])
    app.include_router(academy.router, tags=["academy"])
    app.include_router(analytics_router.router, tags=["analytics"])
    app.include_router(crm.router, prefix="/crm", tags=["crm"])
    app.include_router(messaging.router, tags=["messaging"])
    app.include_router(agents_router.router, tags=["agents"])
    app.include_router(prayer.router, prefix="/prayer", tags=["prayer"])
    app.include_router(support.router, prefix="/support", tags=["support"])
    app.include_router(donations.router)
    app.include_router(finance.router)
    app.include_router(projects.router)
    app.include_router(community.router)
    app.include_router(governance.router)

    if settings.enable_otel:
        configure_telemetry(app, engine)
    mount_security_headers(app)

    @app.on_event("startup")
    def on_startup() -> None:
        # Prevent database initialization if we are in a test environment
        # to avoid connection issues with production Postgres
        if os.getenv("ENV") == "test" or settings.environment == "test":
            log.info("Test environment detected. Skipping production startup tasks.")
            return
            
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        try:
            crud.seed_courses_if_empty(db)
            crud.seed_public_content_if_empty(db)
            crud.ensure_page_content_defaults(db)
            create_stored_procedures(db)
        finally:
            db.close()

    return app


app = create_application()
