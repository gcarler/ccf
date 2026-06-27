from __future__ import annotations

from sqlalchemy import ARRAY, create_engine
from sqlalchemy.dialects.postgresql import CITEXT, JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import get_settings

settings = get_settings()

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
