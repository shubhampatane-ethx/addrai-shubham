"""
Validation API Endpoints
REFACTORED: Supplier → Entity
Trigger validation, test single address, etc.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from backend.app.core.database import get_db
from backend.app.models.models import ValidationJob, Entity
from backend.app.services.osm_validator import OSMNominatimValidator
from backend.app.core.config import settings
from backend.app.tasks.validation import validate_entities_task
import uuid
from datetime import datetime

router = APIRouter()

class AddressTestRequest(BaseModel):
    entity_name: str = ""
    address1: str
    address2: str = ""
    city: str = ""
    state: str = ""
    zip: str = ""
    country: str = "US"

@router.post("/test")
async def test_address(request: AddressTestRequest):
    """
    Test single address validation (no database storage)
    Demonstrates OSM + USPS formatting
    """
    if not settings.ENABLE_OSM_VALIDATOR:
        raise HTTPException(status_code=503, detail="OSM validator is disabled")

    validator = OSMNominatimValidator()

    address_data = {
        'entity_name': request.entity_name,
        'address1': request.address1,
        'address2': request.address2,
        'city': request.city,
        'state': request.state,
        'zip': request.zip,
        'country': request.country
    }

    result = validator.validate(address_data)

    return {
        "input": address_data,
        "validation_result": result,
        "usps_formatted": result.get('usps_formatted', {}),
        "confidence": result.get('confidence_score', 0.0),
        "entity_info": result.get('entity_info', {})
    }

@router.post("/jobs/{job_id}/start")
async def start_job_validation(
    job_id: str,
    validator: str = "openstreetmap",  # Default to OpenStreetMap (FREE)
    db: Session = Depends(get_db)
):
    """
    Start validation for a job using Celery background task
    
    Args:
        job_id: Job UUID
        validator: Which validator to use
            - "openstreetmap" (default, FREE)
            - "chatgpt" (PAID, requires API key)
            - "both" (OpenStreetMap first, then ChatGPT for low confidence)
    """
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")

    job = db.query(ValidationJob).filter(ValidationJob.job_id == job_uuid).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status not in ['UPLOADED', 'FAILED']:
        raise HTTPException(
            status_code=400,
            detail=f"Job cannot be started. Current status: {job.status}"
        )

    # Get entities count
    entities_count = db.query(Entity).filter(Entity.job_id == job_uuid).count()
    
    if entities_count == 0:
        raise HTTPException(status_code=400, detail="No entities found in job")

    # Validate validator type
    if validator not in ["openstreetmap", "chatgpt", "both"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid validator type. Must be 'openstreetmap', 'chatgpt', or 'both'"
        )

    # For chatgpt, check if it's enabled
    if validator in ["chatgpt", "both"]:
        from backend.app.services.chatgpt_validator import ChatGPTAddressValidator
        chatgpt_validator = ChatGPTAddressValidator()
        if not chatgpt_validator.enabled:
            raise HTTPException(
                status_code=400,
                detail="ChatGPT validator is not enabled. Please configure OpenAI API key in Admin panel."
            )

    # Trigger Celery task
    task = validate_entities_task.delay(str(job_uuid), validator)
    
    # Update job status
    job.status = 'QUEUED'
    job.current_step = 'Validation queued'
    db.commit()
    
    return {
        "message": "Validation started",
        "job_id": str(job.job_id),
        "task_id": task.id,
        "validator_type": validator,
        "status": "queued",
        "total_records": job.total_records,
        "note": "Validation is running in the background. Check job status for progress."
    }
