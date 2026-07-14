from __future__ import annotations

import datetime as dt
import sqlite3

from sqlalchemy import ARRAY, create_engine
from sqlalchemy.dialects.postgresql import CITEXT, JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import get_settings

settings = get_settings()

if settings.database_url.startswith("sqlite"):
    # Python 3.12 changed sqlite3's implicit datetime adapters.
    # Register explicit ISO-8601 adapters so SQLite test runs keep the
    # same behavior without relying on the built-in defaults.
    sqlite3.register_adapter(dt.date, lambda value: value.isoformat())
    sqlite3.register_adapter(dt.datetime, lambda value: value.isoformat())

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


@compiles(CITEXT, "sqlite")
def compile_citext_sqlite(element, compiler, **kw):
    return "TEXT"


@compiles(ARRAY, "sqlite")
def compile_array_sqlite(element, compiler, **kw):
    return "TEXT"


@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(element, compiler, **kw):
    return "JSON"


def get_db():
    """Yield one transactional SQLAlchemy session per request."""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
