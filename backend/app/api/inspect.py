import json
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from app.models.schemas import InspectionResponse
from app.services.ai_extractor import extract_information
from app.services.rule_engine import evaluate_compliance
from app.db.database import get_db, DB_AVAILABLE
from app.db.models import InspectionRecord

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/inspect", response_model=InspectionResponse)
async def inspect_package(
    file: UploadFile = File(...),
    db_session = Depends(get_db)
):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File provided is not an image.")
    
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty image file provided.")
    
    # Step 1: AI Extracts visible declarations
    try:
        extracted_data = extract_information(content)
    except Exception as e:
        logger.error(f"Error during AI extraction: {e}")
        raise HTTPException(status_code=500, detail=f"Error during AI extraction: {str(e)}")

    # Step 2: Deterministic Rule Engine evaluates compliance
    try:
        inspection_result = evaluate_compliance(extracted_data)
    except Exception as e:
        logger.error(f"Error during compliance evaluation: {e}")
        raise HTTPException(status_code=500, detail=f"Error during compliance evaluation: {str(e)}")

    # Step 3: (Optional) Store inspection record to DB if available
    if DB_AVAILABLE and db_session is not None:
        try:
            record = InspectionRecord(
                status=inspection_result.status,
                confidence_score=inspection_result.confidence_score,
                extracted_texts_json=json.dumps(inspection_result.extracted_texts),
                violations_json=json.dumps([v.model_dump() for v in inspection_result.violations]),
            )
            db_session.add(record)
            await db_session.commit()
        except Exception as db_err:
            logger.warning(f"Could not persist inspection record to DB: {db_err}")

    return inspection_result
