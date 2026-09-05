import os
import logging
from pathlib import Path
from fastapi import APIRouter
from sqlalchemy import text
from app.db.database import DB_AVAILABLE, engine
from app.services.ai_extractor import USE_MOCK_EXTRACTOR
from app.services.storage import get_storage_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    System health check returning status of database, storage, and AI components.
    """
    db_status = "disabled"
    db_details = "Database persistence not enabled"
    
    if DB_AVAILABLE and engine is not None:
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            db_status = "connected"
            db_details = str(engine.url)
        except Exception as e:
            db_status = "error"
            db_details = str(e)
            logger.error(f"Health check DB error: {e}")

    # Verify storage service
    storage_status = "available"
    storage_path = None
    try:
        storage = get_storage_service()
        storage_path = storage.get_file_path("")
    except Exception as se:
        storage_status = f"error: {str(se)}"

    overall_healthy = (db_status in ("connected", "disabled")) and (storage_status == "available")

    return {
        "status": "healthy" if overall_healthy else "degraded",
        "database": {
            "status": db_status,
            "details": db_details,
        },
        "storage": {
            "status": storage_status,
            "type": os.getenv("STORAGE_TYPE", "local"),
            "path": storage_path,
        },
        "ai_extractor": {
            "mode": "mock" if USE_MOCK_EXTRACTOR else "ocr",
        },
        "version": "1.0.0",
    }
