from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings, ensure_directories
from app.api import inspect, health, inspections
from app.db.database import Base, engine
import app.db.models


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure directories (data, storage/uploads, storage/reports) exist
    ensure_directories()
    # Initialize SQLite database schema
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Metriguard API",
    description="Legal Metrology Compliance Inspection Platform",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS with typed settings
cors_origins = settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else [settings.CORS_ORIGINS]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(health.router, prefix="/api/v1")
app.include_router(inspect.router, prefix="/api/v1")
app.include_router(inspections.router, prefix="/api/v1")


@app.get("/")
def read_root():
    return {"status": "ok", "message": "Metriguard API is running"}
