import os
import logging

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://metry_user:metry_password@localhost:5432/metriguard")

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
    logger.info("SQLAlchemy or asyncpg not installed; database persistence will be disabled.")


async def get_db():
    if not DB_AVAILABLE or AsyncSessionLocal is None:
        yield None
        return
    async with AsyncSessionLocal() as session:
        yield session

