from __future__ import annotations

import asyncio
import os
import uuid as _uuid
import warnings

# Pydantic-settings reads ``ENVIRONMENT`` (not ``ENV``) for the
# ``Settings.environment`` field. Keep this aligned so the validator's
# sqlite/permissive-off branch fires (``env in {local,test,testing,ci}``).
os.environ.setdefault("ENVIRONMENT", "test")

import anyio.to_thread as _anyio_to_thread
import httpx
import pytest

# ── SQLite UUID adapter (MUST be before any model import) ──────────────
# SQLite no soporta UUID nativamente. El bind_processor de Uuid espera
# un objeto uuid.UUID y llama .hex. Parcheamos el processor para que
# también acepte strings (lo que ocurre en comparaciones como
# UUIDColumn == string_param en SQLite).
import sqlalchemy.types as _satypes
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SAWarning
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

_sqlite_uuid_patched = False


def _patch_sqlite_uuid():
    global _sqlite_uuid_patched
    if _sqlite_uuid_patched:
        return
    _orig_bind = _satypes.Uuid.bind_processor
    _orig_result = _satypes.Uuid.result_processor

    def _patched_bind(self, dialect):
        proc = _orig_bind(self, dialect)
        if dialect.name != "sqlite":
            return proc

        # For SQLite, store UUIDs as hyphenated strings.  A 32-char hex
        # string can look like scientific notation (e.g. ...90e1) and
        # SQLite's dynamic typing may coerce it to float on retrieval,
        # which later crashes uuid.UUID(float).  Keeping the dashes
        # prevents that coercion.
        def _safe_process(value):
            if isinstance(value, _uuid.UUID):
                return str(value)
            if isinstance(value, str):
                if len(value) == 36 and value.count("-") == 4:
                    try:
                        return str(_uuid.UUID(value))
                    except (ValueError, AttributeError):
                        return value
                return value
            if isinstance(value, (int, float)):
                # Defensive: if a numeric somehow reaches the bind, do
                # not let it become a float in the database.
                try:
                    return str(_uuid.UUID(int(value)))
                except (ValueError, AttributeError):
                    return str(value)
            if proc is not None:
                return proc(value)
            return value
        return _safe_process

    def _patched_result(self, dialect, coltype):
        proc = _orig_result(self, dialect, coltype) if _orig_result else None
        if dialect.name != "sqlite":
            return proc

        # SQLite may return a float when the stored text looks like
        # scientific notation.  Convert any non-UUID back to UUID safely.
        def _safe_result(value):
            if isinstance(value, _uuid.UUID) or value is None:
                return value
            if isinstance(value, (int, float)):
                try:
                    return _uuid.UUID(int(value))
                except (ValueError, AttributeError):
                    pass
            if isinstance(value, str):
                try:
                    return _uuid.UUID(value)
                except (ValueError, AttributeError):
                    pass
            if proc is not None:
                return proc(value)
            return value
        return _safe_result

    _satypes.Uuid.bind_processor = _patched_bind
    _satypes.Uuid.result_processor = _patched_result
    _sqlite_uuid_patched = True


_patch_sqlite_uuid()


if os.getenv("CCF_TEST_INLINE_SYNC_HANDLERS", "1") != "0":
    async def _run_sync_inline(
        func,
        *args,
        abandon_on_cancel=False,
        cancellable=None,
        limiter=None,
    ):
        return func(*args)

    _anyio_to_thread.run_sync = _run_sync_inline

import backend.models  # noqa: F401 — register all models (including Auth v3) so create_all works
from backend.app import app
from backend.core.database import Base, get_db
from backend.middleware.module_isolation import _circuit_breakers

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


class LocalASGITestClient:
    """Small synchronous test client that avoids Starlette TestClient's portal.

    The installed Starlette/httpx/anyio combination hangs in this sandbox when
    TestClient starts its blocking portal. ASGITransport works correctly when
    driven directly from asyncio.
    """

    def __init__(self, app):
        self.app = app
        self.base_url = "http://testserver"
        self.cookies = httpx.Cookies()

    def request(self, method: str, url: str, **kwargs):
        return asyncio.run(self._request(method, url, **kwargs))

    async def _request(self, method: str, url: str, **kwargs):
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url=self.base_url,
            cookies=self.cookies,
            follow_redirects=True,
        ) as client:
            response = await client.request(method, url, **kwargs)
            self.cookies.update(response.cookies)
            return response

    def get(self, url: str, **kwargs):
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs):
        return self.request("POST", url, **kwargs)

    def put(self, url: str, **kwargs):
        return self.request("PUT", url, **kwargs)

    def patch(self, url: str, **kwargs):
        return self.request("PATCH", url, **kwargs)

    def delete(self, url: str, **kwargs):
        return self.request("DELETE", url, **kwargs)

    def close(self):
        return None


@pytest.fixture(scope="function")
def db_session():
    if engine.dialect.name == "postgresql":
        with engine.connect() as conn:
            conn.execute(text("DROP SCHEMA public CASCADE"))
            conn.execute(text("CREATE SCHEMA public"))
            conn.commit()
        Base.metadata.create_all(bind=engine)
    else:
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message="Can't sort tables for DROP*",
                category=SAWarning,
            )
            Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(db_session):
    test_client = LocalASGITestClient(app)
    try:
        yield test_client
    finally:
        test_client.close()
    app.dependency_overrides = {get_db: override_get_db}


@pytest.fixture(autouse=True)
def _reset_module_circuit_breaker():
    """Reset the module_isolation circuit-breaker state between tests.

    The middleware's ``_circuit_breakers`` is a module-level dict that
    persists across tests in the same Python process. Without this autouse
    fixture, one failing test that opens the circuit (5 raises → 60s
    ``open=True`` window) poisons every subsequent test in the run with
    phantom 503s on the same module — a classic cross-test state leak.

    Production code lives outside this fixture's lifetime (it only runs
    during pytest collection), so clearing here has no impact on the
    real application. We clear BOTH before AND after the test to be
    defensive against leftover keys from a test that mutated the dict
    (e.g., a future test that wants to assert breaker state directly).
    """
    _circuit_breakers.clear()
    yield
    _circuit_breakers.clear()


@pytest.fixture(autouse=True)
def _reset_caches_between_tests():
    """Clear Redis cache and the CMS in-memory cache between tests.

    ``@cached_public(ttl=300)`` on the CMS v2 endpoints caches the JSON
    response under a deterministic key (the SHA-256 of the path args).
    Without this fixture, the first test's response survives across the
    full pytest run with a 300-second TTL — feeds a stale URL pointing
    at a ``CmsMediaItem`` row that the next test's fixture just dropped
    and re-created under a fresh ``uuid4``. The same problem applies to
    ``_system_var_cache`` in ``backend.api.cms_v2`` (a module-level dict
    that never expires). Pattern mirrored from ``_reset_module_circuit_breaker``
    so the two state-leak vectors move in lock-step.

    Implementation notes
    --------------------
    * Imports are deferred into the function body so an unrelated test
      that doesn't import ``backend.core.cache`` (e.g. pure unit tests)
      still works — the autouse fixture must not raise during collection.
    * ``MemoryRedis`` (the default in-test backend, see
      ``backend.core.cache``) exposes neither ``flushdb`` nor ``flushall``
      — we clear its internal ``_store`` and ``_expire`` dicts instead.
      Real Redis supports both ``flushdb`` / ``flushall``; we prefer
      ``flushdb`` to limit blast radius if the test ever runs against a
      shared Redis dev instance.
    * ``_system_var_cache`` is imported lazily so a test that patches
      ``cms_v2`` upstream doesn't AttributeError at fixture-collection
      time. If the module surface changes, the test simply doesn't get
      the cleanup (no false negatives created).
    """
    def _clear_redis():
        try:
            from backend.core.cache import get_redis
        except Exception:
            return  # cache module unavailable — nothing to clear
        try:
            redis_cli = get_redis()
        except Exception:
            return  # no client in this env (e.g. some test stubs it out)
        try:
            if hasattr(redis_cli, "flushdb"):
                redis_cli.flushdb()
            elif hasattr(redis_cli, "_store"):
                redis_cli._store.clear()
                redis_cli._expire.clear()
        except Exception:
            # Best-effort: never let the autouse fixture break a real
            # test failure into an AttributeError / redis-py error.
            pass

    def _clear_cms_inmemory():
        try:
            from backend.api import cms_v2
        except Exception:
            return
        cache = getattr(cms_v2, "_system_var_cache", None)
        if cache is not None and hasattr(cache, "clear"):
            try:
                cache.clear()
            except Exception:
                pass

    _clear_redis()
    _clear_cms_inmemory()
    yield
    _clear_redis()
    _clear_cms_inmemory()


# ── Auth Helper (v2 / auth_users) ─────────────────────────────────────
# All test files that need authenticated endpoints should use these
# helpers instead of the numeric models.User pattern, because the
# /api/auth/login endpoint queries Usuario (auth_users), not User (users).

def seed_admin(db_session, email="admin@example.com", password="testpass123"):
    """Crea un administrador funcional en Auth v3 y su Persona.

    Idempotente: si ya existe un Usuario con este email en la sesión,
    retorna el registro existente y sus relaciones (Persona, Sede) en vez
    de re-insertar. Esto previene el cascade ``IntegrityError: UNIQUE
    constraint failed: auth_users.email`` cuando un test invoca
    ``seed_admin`` más de una vez (intencional o accidentalmente) y deja
    la conexión compartida de ``StaticPool`` en mal estado.
    """
    import uuid as _uuid

    from backend import models as _models
    from backend.core.security import get_password_hash
    from backend.models_auth import RolPlataforma, Usuario
    from backend.models_crm import Persona

    existing_user = (
        db_session.query(Usuario)
        .filter(Usuario.email == email)
        .first()
    )
    if existing_user is not None:
        existing_persona = (
            db_session.query(Persona)
            .filter(Persona.id == existing_user.id)
            .first()
        )
        existing_sede = (
            db_session.query(_models.Sede)
            .filter(_models.Sede.id == existing_user.sede_id)
            .first()
        )
        return existing_user, existing_persona, existing_sede

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
    persona.sede_id = sede.id

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


def auth_headers(client, email="admin@example.com", password="testpass123"):
    """Obtiene headers de autorización usando el endpoint /api/v3/auth/login."""
    resp = client.post(
        "/api/v3/auth/login",
        json={"email": email, "password": password},
    )
    assert resp.status_code == 200, f"Login failed: {resp.status_code} {resp.text}"
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def seed_user_with_role(
    db_session,
    role_name="persona",
    email="user@example.com",
    password="testpass123",
    sede_id=None,
    permisos=None,
):
    """Crea un usuario Auth v3 con un rol de plataforma.

    Retorna (user, persona, sede).
    Util para tests que necesitan usuarios no-admin con roles personalizados.

    Multi-tenant alignment (chat-ws tests gate, 2026):
    cuando ``sede_id`` no se pasa explicitamente, el helper reusa
    CUALQUIER Sede ya visible en la sesion — mismo patron que
    ``_ensure_sede`` en ``tests/factories_projects.py``. Esto evita que
    ``seed_admin`` + ``seed_user_with_role`` (en secuencia) terminen en
    sedes distintas, haciendo que la prueba asuma same-sede mientras
    el setup generaba cross-sede. Resultado: el guard ``_ensure_project``
    del API rechaza con 404 antes de poder llegar al role-check (403).
    Tests que SI requieren cross-sede pueden pasar ``sede_id`` explicito.
    """
    from backend import models as _models
    from backend.core.security import get_password_hash
    from backend.models_auth import RolPlataforma, Usuario
    from backend.models_crm import Persona

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
            permisos=permisos if permisos is not None else {"default": "allow"},
        )
        db_session.add(role)
        db_session.flush()

    # ── Multi-tenant: same-sede by default ───────────────
    if sede_id is None:
        existing_sede = db_session.query(_models.Sede).first()
        if existing_sede is not None:
            sede_id = existing_sede.id
    if sede_id is not None:
        sede = (
            db_session.query(_models.Sede)
            .filter(_models.Sede.id == sede_id)
            .first()
        )
        if sede is None:
            sede = _models.Sede(
                id=sede_id,
                nombre="Sede Test",
                ciudad="Bogota",
                es_activa=True,
            )
            db_session.add(sede)
            db_session.flush()
    else:
        sede = _models.Sede(
            id=_uuid.uuid4(),
            nombre="Sede Test",
            ciudad="Bogota",
            es_activa=True,
        )
        db_session.add(sede)
        db_session.flush()
    persona.sede_id = sede.id

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
