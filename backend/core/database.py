from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from .config import get_settings

settings = get_settings()

# El motor ahora utiliza la URL desde el archivo .env configurado profesionalmente
engine = create_engine(
    settings.database_url,
    future=True,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

Base = declarative_base()

def get_db():
    """Generador de sesiones de base de datos para FastAPI."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
