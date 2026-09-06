import logging
from sqlite3 import Connection as SQLite3Connection
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings, ensure_directories

logger = logging.getLogger(__name__)

# Ensure runtime directories (data/, storage/, etc.) exist
ensure_directories()

DATABASE_URL = settings.get_resolved_database_url()
is_sqlite = DATABASE_URL.startswith("sqlite")

connect_args = {"check_same_thread": False} if is_sqlite else {}

# Create SQLAlchemy engine without global open connection
engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=False
)

# Configure SQLite pragma for foreign key enforcement
if is_sqlite:
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        if isinstance(dbapi_connection, SQLite3Connection):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

# Session factory for creating scoped, isolated database sessions
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()
DB_AVAILABLE = True


def get_db():
    """
    FastAPI dependency yielding an isolated, request-scoped database session.
    Guarantees session cleanup via try/finally block without holding global connections.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
