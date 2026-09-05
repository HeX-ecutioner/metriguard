from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import inspect, health
from app.db.database import Base, engine
import app.db.models


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
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

app.include_router(health.router)
app.include_router(health.router, prefix="/api/v1")
app.include_router(inspect.router, prefix="/api/v1")


@app.get("/")
def read_root():
    return {"status": "ok", "message": "Metriguard API is running"}
