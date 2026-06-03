from __future__ import annotations

import os
import uuid as _uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app import app
from backend.core.database import Base, get_db
import backend.models  # noqa: F401 — register all models (incl. auth_v2) so create_all works

SQLALCHEMY_DATABASE_URL = (
    os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL") or "sqlite://"
)
database_url = make_url(SQLALCHEMY_DATABASE_URL)

engine_kwargs = {}
if database_url.drivername.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
    if database_url.database in (None, "", ":memory:"):
        engine_kwargs["poolclass"] = StaticPool

engine = create_engine(SQLALCHEMY_DATABASE_URL, **engine_kwargs)


# ── SQLite UUID adapter ──────────────────────────────────────────────────
# SQLite no soporta UUID nativamente. Los tests usan SQLite (:memory:), pero
# muchos modelos tienen UUID(as_uuid=True). En PostgreSQL la comparación
# UUIDColumn == "string" funciona por coerción automática, pero en SQLite
# falla. Este hook convierte strings UUID del bind a objetos uuid.UUID antes
# de ejecutar la sentencia.
@event.listens_for(engine, "before_cursor_execute", retval=True)
def _sqlite_uuid_bind(conn, cursor, statement, parameters, context, executemany):
    if engine.dialect.name != "sqlite":
        return statement, parameters
    if not parameters:
        return statement, parameters
    new_params = []
    for param in parameters:
        if isinstance(param, (list, tuple)):
            # Batch insert — recurse into each element
            new_params.append(
                tuple(
                    _uuid.UUID(p) if isinstance(p, str) and len(p) == 36 and p.count("-") == 4 and _is_uuid_hex(p.replace("-", "")) else p
                    for p in param
                )
            )
        elif isinstance(param, str) and len(param) == 36 and param.count("-") == 4 and _is_uuid_hex(param.replace("-", "")):
            try:
                new_params.append(_uuid.UUID(param))
            except (ValueError, AttributeError):
                new_params.append(param)
        else:
            new_params.append(param)
    return statement, tuple(new_params)


def _is_uuid_hex(hex_str: str) -> bool:
    """Quick check that a 32-char hex string is valid UUID hex."""
    if len(hex_str) != 32:
        return False
    try:
        int(hex_str, 16)
        return True
    except ValueError:
        return False


TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="function")
def db_session():
    if engine.dialect.name == "postgresql":
        with engine.connect() as conn:
            conn.execute(text("DROP SCHEMA public CASCADE"))
            conn.execute(text("CREATE SCHEMA public"))
            conn.commit()
        Base.metadata.create_all(bind=engine)
    else:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(db_session):
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides = {get_db: override_get_db}


# ── Auth Helper (v2 / auth_users) ─────────────────────────────────────
# All test files that need authenticated endpoints should use these
# helpers instead of the legacy models.User pattern, because the
# /api/auth/login endpoint queries Usuario (auth_users), not User (users).

def seed_admin_v2(db_session, email="admin@example.com", password="testpass123"):
    """Crea un admin funcional en auth_users + persona + RolPlataforma."""
    import uuid as _uuid
    from backend import models as _models
    from backend.models_auth import Usuario, RolPlataforma
    from backend.models_crm import Persona
    from backend.core.security import get_password_hash

    persona = Persona(
        id=_uuid.uuid4(),
        first_name="Admin",
        last_name="Test",
        email=email,
    )
    db_session.add(persona)
    db_session.flush()

    role = db_session.query(RolPlataforma).filter(RolPlataforma.nombre == "ADMIN").first()
    if not role:
        role = RolPlataforma(
            id=_uuid.uuid4(),
            nombre="ADMIN",
            permisos={"*": "allow"},
        )
        db_session.add(role)
        db_session.flush()

    sede = _models.Sede(
        id=_uuid.uuid4(),
        nombre="Sede Test",
        ciudad="Bogota",
        es_activa=True,
    )
    db_session.add(sede)
    db_session.flush()

    user = Usuario(
        id=persona.id,
        sede_id=sede.id,
        username=email.split("@")[0],
        email=email,
        password_hash=get_password_hash(password),
        rol_plataforma_id=role.id,
        is_active=True,
        is_email_verified=True,
    )
    db_session.add(user)
    db_session.commit()
    return user, persona, sede


def auth_headers_v2(client, email="admin@example.com", password="testpass123"):
    """Obtiene headers de autorización usando el endpoint /api/auth/login."""
    resp = client.post(
        "/api/auth/login",
        data={"username": email, "password": password, "grant_type": "password"},
    )
    assert resp.status_code == 200, f"Login failed: {resp.status_code} {resp.text}"
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def seed_user_with_role_v2(db_session, role_name="member", email="user@example.com", password="testpass123"):
    """Crea un usuario v2 (auth_users) con rol específico en RolPlataforma.

    Retorna (user, persona, sede).
    Útil para tests que necesitan usuarios no-admin con roles personalizados.
    """
    from backend import models as _models
    from backend.models_auth import Usuario, RolPlataforma
    from backend.models_crm import Persona
    from backend.core.security import get_password_hash

    persona = Persona(
        id=_uuid.uuid4(),
        first_name="User",
        last_name="Test",
        email=email,
    )
    db_session.add(persona)
    db_session.flush()

    role = db_session.query(RolPlataforma).filter(RolPlataforma.nombre == role_name).first()
    if not role:
        role = RolPlataforma(
            id=_uuid.uuid4(),
            nombre=role_name,
            permisos={"default": "allow"},
        )
        db_session.add(role)
        db_session.flush()

    sede = _models.Sede(
        id=_uuid.uuid4(),
        nombre="Sede Test",
        ciudad="Bogota",
        es_activa=True,
    )
    db_session.add(sede)
    db_session.flush()

    user = Usuario(
        id=persona.id,
        sede_id=sede.id,
        username=email.split("@")[0],
        email=email,
        password_hash=get_password_hash(password),
        rol_plataforma_id=role.id,
        is_active=True,
        is_email_verified=True,
    )
    db_session.add(user)
    db_session.commit()
    return user, persona, sede
