from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import get_settings


settings = get_settings()

db_url = settings.database_url
if "sqlite" in db_url or "5432" in db_url:
    db_url = "postgresql+pg8000://postgres:admin123@localhost:5435/ccf_db"

engine = create_engine(
    db_url,
    future=True,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
