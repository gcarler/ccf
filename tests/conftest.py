from __future__ import annotations

import os
import uuid as _uuid

os.environ.setdefault("ENV", "test")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# ── SQLite UUID adapter (MUST be before any model import) ──────────────
# SQLite no soporta UUID nativamente. El bind_processor de Uuid espera
# un objeto uuid.UUID y llama .hex. Parcheamos el processor para que
# también acepte strings (lo que ocurre en comparaciones como
# UUIDColumn == string_param en SQLite).
import sqlalchemy.types as _satypes
import uuid as _uuid

_sqlite_uuid_patched = False


def _patch_sqlite_uuid():
    global _sqlite_uuid_patched
    if _sqlite_uuid_patched:
        return
    _orig_bind = _satypes.Uuid.bind_processor

    def _patched_bind(self, dialect):
        proc = _orig_bind(self, dialect)
        if dialect.name != "sqlite" or proc is None:
            return proc

        def _safe_process(value):
            if isinstance(value, str):
                if len(value) == 36 and value.count("-") == 4:
                    try:
                        value = _uuid.UUID(value)
                    except (ValueError, AttributeError):
                        return value
                else:
                    # Non-UUID string on SQLite — can't call .hex, pass raw
                    return value
            return proc(value)
        return _safe_process

    _satypes.Uuid.bind_processor = _patched_bind
    _sqlite_uuid_patched = True


_patch_sqlite_uuid()

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
    from backend.models_identity import User

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
    legacy_user = User(
        username=email.split("@")[0],
        email=email,
        password_hash=get_password_hash(password),
        role="admin",
        is_active=True,
    )
    db_session.add(legacy_user)
    db_session.commit()
    user.legacy_user = legacy_user
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


def auth_headers_legacy(email="admin@example.com"):
    """JWT para endpoints legacy que dependen de models.User.id entero."""
    from backend.auth import create_access_token, normalize_role
    from backend.models_identity import User

    db = TestingSessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        assert user is not None, f"Legacy user not found for {email}"
        token = create_access_token({"sub": str(user.id), "role": normalize_role(user.role)})
        return {"Authorization": f"Bearer {token}"}
    finally:
        db.close()


def seed_user_with_role_v2(db_session, role_name="member", email="user@example.com", password="testpass123"):
    """Crea un usuario v2 (auth_users) con rol específico en RolPlataforma.

    Retorna (user, persona, sede).
    Útil para tests que necesitan usuarios no-admin con roles personalizados.
    """
    from backend import models as _models
    from backend.models_auth import Usuario, RolPlataforma
    from backend.models_crm import Persona
    from backend.core.security import get_password_hash
    from backend.models_identity import User

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
    legacy_user = User(
        username=email.split("@")[0],
        email=email,
        password_hash=get_password_hash(password),
        role=role_name,
        is_active=True,
    )
    db_session.add(legacy_user)
    db_session.commit()
    user.legacy_user = legacy_user
    return user, persona, sede
