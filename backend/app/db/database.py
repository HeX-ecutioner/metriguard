import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Ensure backend/data directory exists
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BACKEND_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_DB_FILE = (DATA_DIR / "metriguard.db").as_posix()
DEFAULT_DB_URL = f"sqlite+aiosqlite:///{DEFAULT_DB_FILE}"

DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DB_URL)

DB_AVAILABLE = False
engine = None
AsyncSessionLocal = None

try:
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    from sqlalchemy.orm import declarative_base

    Base = declarative_base()
    engine = create_async_engine(DATABASE_URL, echo=False)
    AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    DB_AVAILABLE = True
except ImportError:
    class Base:
        pass
    logger.info("SQLAlchemy or aiosqlite not installed; database persistence will be disabled.")


async def get_db():
    if not DB_AVAILABLE or AsyncSessionLocal is None:
        yield None
        return
    async with AsyncSessionLocal() as session:
        yield session

