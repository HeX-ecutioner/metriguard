import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import inspect
from app.db.database import DB_AVAILABLE, Base, engine
import app.db.models  # Register models with Base

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if DB_AVAILABLE and engine is not None:
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables initialized successfully.")
        except Exception as e:
            logger.warning(f"Database table initialization skipped (running offline or DB unavailable): {e}")
    yield


app = FastAPI(
    title="Metriguard API",
    description="Legal Metrology Compliance Inspection Platform",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(inspect.router, prefix="/api/v1")

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Metriguard API is running"}
