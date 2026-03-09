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
    cms,
    crm,
    governance,
    messaging,
    system,
)
from backend.core.config import get_settings
from backend.core.database import Base, SessionLocal, engine
from backend.core.telemetry import configure_telemetry
from backend.core.security_headers import mount_security_headers
from backend.database_scripts import create_stored_procedures


settings = get_settings()


def create_application() -> FastAPI:
    app = FastAPI(title="CCF Platform API", version="2.0.0")

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

    # Routers
    app.include_router(system.router)
    app.include_router(auth_router.router, tags=["auth"])
    app.include_router(academy.router, tags=["academy"])
    app.include_router(cms.router, tags=["cms"])
    app.include_router(analytics_router.router, tags=["analytics"])
    app.include_router(crm.router, tags=["crm"])
    app.include_router(messaging.router, tags=["messaging"])
    app.include_router(agents_router.router, tags=["agents"])
    app.include_router(governance.router)

    if settings.enable_otel:
        configure_telemetry(app, engine)
    mount_security_headers(app)

    @app.on_event("startup")
    def on_startup() -> None:
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        try:
            crud.seed_courses_if_empty(db)
            create_stored_procedures(db)
        finally:
            db.close()

    return app


app = create_application()
