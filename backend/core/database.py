from __future__ import annotations

import logging

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker,
                                    create_async_engine)
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import get_settings

log = logging.getLogger(__name__)
settings = get_settings()

# ── Síncrono (existente) ──────────────────────────────────────────────
_pool_kwargs = {}
if not settings.database_url.startswith("sqlite"):
    _pool_kwargs["pool_size"] = 10
    _pool_kwargs["max_overflow"] = 20

engine = create_engine(
    settings.database_url,
    future=True,
    pool_pre_ping=True,
    **_pool_kwargs,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

Base = declarative_base()


# Compilación de CITEXT para SQLite (entornos de pruebas)
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import CITEXT

@compiles(CITEXT, "sqlite")
def compile_citext_sqlite(element, compiler, **kw):
    return "TEXT"


from sqlalchemy import ARRAY

@compiles(ARRAY, "sqlite")
def compile_array_sqlite(element, compiler, **kw):
    return "TEXT"


from sqlalchemy.dialects.postgresql import JSONB

@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(element, compiler, **kw):
    return "JSON"






def get_db():
    """Generador de sesiones síncronas para FastAPI (inyección de dependencias)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Asíncrono (migración progresiva) ──────────────────────────────────
# Para usar async en un endpoint:
#   1. Cambia `def` → `async def`
#   2. Usa `Depends(get_db_async)` en vez de `Depends(get_db)`
#   3. Las queries usan `await db.execute(...)` con `select()` de SQLAlchemy 2.0
#   4. CRUD async está disponible en `backend/crud/async_.py`

_async_url: str | None = None
async_engine = None
AsyncSessionLocal = None


def _build_async_url(sync_url: str) -> str:
    """Convierte una URL sync a su equivalente async.

    Ej: ``postgresql+psycopg2://...`` → ``postgresql+asyncpg://...``
    """
    if sync_url.startswith("sqlite"):
        return sync_url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    if "+" in sync_url:
        scheme, rest = sync_url.split("+", 1)
        driver = rest.split("://")[0]
        return sync_url.replace(f"+{driver}", "+asyncpg", 1)
    # Si no tiene driver explícito, asumimos postgresql
    return sync_url.replace("://", "+asyncpg://", 1)


def get_async_engine():
    """Inicializa (bajo demanda) el engine asíncrono.

    Usa ``asyncpg`` para PostgreSQL o ``aiosqlite`` para SQLite.
    """
    global _async_url, async_engine, AsyncSessionLocal

    if async_engine is not None:
        return async_engine

    _async_url = _build_async_url(settings.database_url)
    try:
        async_engine = create_async_engine(
            _async_url,
            future=True,
            pool_pre_ping=True,
            echo=False,
        )
        AsyncSessionLocal = async_sessionmaker(
            bind=async_engine,
            class_=AsyncSession,
            autoflush=False,
            autocommit=False,
        )
        log.info("Async SQLAlchemy engine initialized (%s)", _async_url.split("://")[0])
    except Exception as exc:
        log.warning("Could not initialize async engine: %s", exc)
        async_engine = None

    return async_engine


async def get_db_async():
    """Dependency async: sesión asíncrona para FastAPI.

    Uso:
        @router.get("/items")
        async def list_items(db: AsyncSession = Depends(get_db_async)):
            ...
    """
    engine = get_async_engine()
    if engine is None:
        # Fallback: arranca sync engine en executor si async no está disponible
        log.warning(
            "Async engine not available; use sync `get_db` instead of `get_db_async`"
        )
        raise RuntimeError(
            "Async database engine not available. "
            "Install asyncpg (PostgreSQL) or aiosqlite (SQLite) and check DATABASE_URL."
        )

    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
