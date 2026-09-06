import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings, ensure_directories

logger = logging.getLogger(__name__)

# Ensure data and storage directories exist
ensure_directories()

DATABASE_URL = settings.get_resolved_database_url()
if DATABASE_URL.startswith("sqlite+aiosqlite:"):
    DATABASE_URL = DATABASE_URL.replace("sqlite+aiosqlite:", "sqlite:")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
DB_AVAILABLE = True


def get_db():
    """FastAPI dependency for database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
